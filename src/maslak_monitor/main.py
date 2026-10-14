"""CLI and single-worker orchestration."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import fcntl
import json
import logging
import os
from pathlib import Path
import time
from .config import Settings
from .schedule import ISTANBUL, window_at, next_window
from .site import SiteProbe, URL
from .sms import NetgsmSender, SendResult
from .email_sender import SmtpSender
from .store import Store

LOG = logging.getLogger('maslak-monitor')

@dataclass(frozen=True)
class CheckResult:
    status: str
    count: int = 0


def run_once(now,settings,probe,store,sender,dry_run) -> CheckResult:
    window=window_at(now)
    if window is None:
        return CheckResult('outside_window')
    week=window.week_start
    slots=None if dry_run else store.opening(week)
    if slots is None:
        slots=probe.check_week(week)
        if not slots:
            return CheckResult('not_open')
        if dry_run:
            return CheckResult('opened_dry_run',len(slots))
        store.record_opening(week,slots)
    message=f'Maslak Hali Saha: {week} haftasinda rezervasyona acik seans bulundu. {URL}'
    for recipient in settings.recipients:
        if not store.claim_recipient(week,recipient):
            continue
        try:
            result=sender.send(recipient,message)
        except Exception:
            result=SendResult('unknown')
        store.finish_recipient(week,recipient,result.status,result.provider_id)
    states=[store.recipient_state(week,r) for r in settings.recipients]
    if 'unknown' in states or 'sending' in states:
        return CheckResult(settings.channel+'_unknown',len(slots))
    if not states or any(s!='accepted' for s in states):
        return CheckResult(settings.channel+'_rejected',len(slots))
    return CheckResult('notified',len(slots))


@contextmanager
def process_lock(directory: Path):
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (directory/'monitor.lock').open('a') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Monitor already running') from None
        try:
            yield
        finally:
            fcntl.flock(handle,fcntl.LOCK_UN)


def write_health(directory,now,status,error_type,last_success):
    payload={'heartbeat':now.isoformat(),'status':status,'error_type':error_type,
             'last_success':last_success.isoformat() if last_success else None}
    temp=directory/'health.tmp'
    temp.write_text(json.dumps(payload),encoding='utf-8')
    temp.replace(directory/'health.json')


def check_health(directory,now) -> int:
    try:
        data=json.loads((directory/'health.json').read_text())
        heartbeat=datetime.fromisoformat(data['heartbeat'])
        age=(now-heartbeat).total_seconds()
        return int(age < 0 or age > 120 or bool(data['error_type']))
    except (OSError,ValueError,KeyError,TypeError):
        return 1


def next_tick(now,last_tick,interval,end):
    if now >= end:
        return end
    steps=max(1,int((now-last_tick).total_seconds()//interval)+1)
    return min(last_tick+timedelta(seconds=steps*interval),end)


def scheduled_check_time(actual,due):
    if window_at(actual):
        return actual
    # Only the already scheduled final Monday 10:00 check gets a 1s jitter allowance.
    window=window_at(due)
    if window and due==window.end and 0 <= (actual-due).total_seconds() <= 1:
        return due
    return actual


def _wait_until(due,directory,status,error,last_success):
    while True:
        now=datetime.now(ISTANBUL)
        remaining=(due-now).total_seconds()
        if remaining <= 0:
            return
        write_health(directory,now,status,error,last_success)
        time.sleep(min(30,remaining))


def monitor(settings,probe,store,sender,once=False):
    due=datetime.now(ISTANBUL)
    failures=0
    last_success=None
    previous=None
    while True:
        actual=datetime.now(ISTANBUL)
        tick=scheduled_check_time(actual,due)
        error=None
        try:
            result=run_once(tick,settings,probe,store,sender,settings.dry_run)
            status=result.status
            error='NotificationUnknown' if status.endswith('_unknown') else 'NotificationRejected' if status.endswith('_rejected') else None
            if status != 'outside_window':
                last_success=datetime.now(ISTANBUL)
            failures=0
        except Exception as exc:
            status='error'
            error=type(exc).__name__
            failures+=1
        now=datetime.now(ISTANBUL)
        write_health(settings.data_dir,now,status,error,last_success)
        if (status,error) != previous:
            LOG.warning('status=%s error_type=%s',status,error or 'none')
            previous=(status,error)
        if once:
            return 1 if error else 0
        window=window_at(tick)
        if window and tick < window.end and now < window.end:
            interval=min(900,settings.interval*2**min(failures,3)) if failures else settings.interval
            due=next_tick(now,tick,interval,window.end)
        else:
            # After the final check or a completed notification, wait for next Friday.
            after=max(now,tick+timedelta(microseconds=1))
            due=next_window(after).start
        if status=='notified':
            due=next_window(window.end+timedelta(seconds=1)).start
        _wait_until(due,settings.data_dir,status,error,last_success)


def make_sender(settings):
    if settings.dry_run:
        return None
    if settings.channel == 'email':
        return SmtpSender(settings.smtp_user,settings.smtp_password,settings.smtp_host,settings.smtp_port)
    return NetgsmSender(settings.sms_user,settings.sms_password,settings.sms_header)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Maslak Hali Saha weekly monitor')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--once',action='store_true',help='One scheduled-window check')
    mode.add_argument('--probe-week',type=date.fromisoformat,help='Read-only diagnostic week (YYYY-MM-DD Monday)')
    mode.add_argument('--test-email',action='store_true',help='Send a labelled test email to each configured recipient')
    mode.add_argument('--test-sms',action='store_true',help='Send one clearly labelled test SMS to each configured recipient')
    mode.add_argument('--check-health',action='store_true',help='Exit 0 if worker heartbeat is healthy')
    parser.add_argument('--dry-run',action='store_true',help='Override environment; never sends notifications')
    args=parser.parse_args(argv)
    os.umask(0o077)
    logging.basicConfig(level=logging.WARNING,format='%(asctime)s %(message)s')
    if args.check_health:
        return check_health(Path(os.environ.get('DATA_DIR','data')),datetime.now(ISTANBUL))
    if args.dry_run and (args.test_sms or args.test_email):
        parser.error('Test sending cannot be combined with --dry-run')
    env=dict(os.environ)
    if args.dry_run or args.probe_week:
        env['DRY_RUN']='true'
    if args.test_sms:
        env.update(DRY_RUN='false',PURCHASE_SELECTOR_VERIFIED='true',NOTIFICATION_CHANNEL='sms')
    if args.test_email:
        env.update(DRY_RUN='false',PURCHASE_SELECTOR_VERIFIED='true',NOTIFICATION_CHANNEL='email')
    try:
        settings=Settings.from_env(env)
        with process_lock(settings.data_dir), Store(settings.data_dir/'state.db') as store:
            if not settings.dry_run:
                store.recover_interrupted()
            sender=make_sender(settings)
            try:
                if args.test_sms or args.test_email:
                    states=[sender.send(r,'TEST: Maslak Hali Saha bildirim sistemi baglanti testi.').status for r in settings.recipients]
                    LOG.warning('test_notification_channel=%s accepted=%s/2',settings.channel,states.count('accepted'))
                    return 0 if states==['accepted','accepted'] else 1
                with SiteProbe(settings) as probe:
                    if args.probe_week:
                        if args.probe_week.weekday()!=0:
                            raise ValueError('--probe-week requires a Monday')
                        slots=probe.check_week(args.probe_week)
                        print(json.dumps({'week':args.probe_week.isoformat(),'available':[
                            {'day':s.day.isoformat(),'session':s.label} for s in slots]},ensure_ascii=False))
                        return 0
                    return monitor(settings,probe,store,sender,args.once)
            finally:
                if sender: sender.close()
    except KeyboardInterrupt:
        return 0
    except ValueError as exc:
        LOG.error('configuration_error: %s',str(exc))
        return 2
    except Exception as exc:
        LOG.error('startup_error_type=%s',type(exc).__name__)
        return 1
