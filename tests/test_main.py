from dataclasses import replace
from datetime import datetime, date, timedelta
import json
import pytest
from maslak_monitor.config import Settings
from maslak_monitor.main import run_once, process_lock, write_health, check_health, next_tick
from maslak_monitor.store import Store
from maslak_monitor.site import Slot, ProbeError
from maslak_monitor.sms import SendResult

NOW=datetime.fromisoformat('2026-10-16T10:00:00+03:00')
WEEK=date(2026,10,19)

class Probe:
 def __init__(self,slots): self.slots=slots
 def check_week(self,week):
  assert week==WEEK
  return self.slots

class NoCall:
 def check_week(self,week): raise AssertionError('Unexpected site query')
 def send(self,*a): raise AssertionError('Unexpected SMS')

class Sender:
 def send(self,recipient,message):
  assert '2026-10-19' in message
  return SendResult('accepted','sample-id') if recipient=='5551111111' else SendResult('rejected')

@pytest.fixture
def settings(tmp_path):
 return replace(Settings('user','secret'),data_dir=tmp_path,recipients=('5551111111','5552222222'))

def test_outside_window_does_not_query_site(settings):
 with Store(settings.data_dir/'state.db') as db:
  result=run_once(NOW-timedelta(seconds=1),settings,NoCall(),db,NoCall(),True)
 assert result.status=='outside_window'

def test_dry_run_does_not_send_or_write_opening(settings):
 with Store(settings.data_dir/'state.db') as db:
  result=run_once(NOW,settings,Probe([Slot(WEEK,'20:00')]),db,NoCall(),True)
  assert result.status=='opened_dry_run'
  assert db.opening(WEEK) is None

def test_closed_week_does_not_write_opening(settings):
 with Store(settings.data_dir/'state.db') as db:
  assert run_once(NOW,settings,Probe([]),db,NoCall(),True).status=='not_open'
  assert db.opening(WEEK) is None

def test_live_result_persists_and_retries_only_failed_recipient(settings):
 with Store(settings.data_dir/'state.db') as db:
  first=run_once(NOW,settings,Probe([Slot(WEEK,'20:00')]),db,Sender(),False)
  assert first.status=='sms_rejected'
  assert db.recipient_state(WEEK,'5551111111')=='accepted'
  assert db.recipient_state(WEEK,'5552222222')=='rejected'
  second=run_once(NOW+timedelta(seconds=120),settings,NoCall(),db,Sender(),False)
  assert second.status=='sms_rejected'

@pytest.mark.parametrize('status',['unknown','accepted'])
def test_no_duplicate_after_restart_or_ambiguous_send(settings,status):
 with Store(settings.data_dir/'state.db') as db:
  db.record_opening(WEEK,[Slot(WEEK,'20:00')])
  for number in settings.recipients:
   db.claim_recipient(WEEK,number)
   db.finish_recipient(WEEK,number,status,None)
 with Store(settings.data_dir/'state.db') as db:
  result=run_once(NOW,settings,NoCall(),db,NoCall(),False)
  assert result.status==('sms_unknown' if status=='unknown' else 'notified')

def test_sender_exception_marks_unknown_but_other_recipient_still_processed(settings):
 class Mixed:
  def send(self,recipient,message):
   if recipient=='5551111111': raise RuntimeError('must not reach logs')
   return SendResult('accepted','id')
 with Store(settings.data_dir/'state.db') as db:
  assert run_once(NOW,settings,Probe([Slot(WEEK,'20:00')]),db,Mixed(),False).status=='sms_unknown'
  assert db.recipient_state(WEEK,'5552222222')=='accepted'

def test_process_lock_rejects_second_worker(tmp_path):
 with process_lock(tmp_path):
  with pytest.raises(RuntimeError,match='already running'):
   with process_lock(tmp_path): pass

def test_health_distinguishes_stale_and_errors(tmp_path):
 write_health(tmp_path,NOW,'not_open',None,None)
 assert check_health(tmp_path,NOW)==0
 assert check_health(tmp_path,NOW+timedelta(seconds=121))==1
 write_health(tmp_path,NOW,'sms_unknown','SmsUnknown',None)
 assert check_health(tmp_path,NOW)==1

def test_scheduler_caps_at_final_boundary_and_accounts_for_query_time():
 assert next_tick(NOW+timedelta(seconds=35),NOW,120,NOW+timedelta(days=3))==NOW+timedelta(seconds=120)
 end=NOW+timedelta(days=3)
 assert next_tick(end-timedelta(seconds=10),end-timedelta(seconds=20),120,end)==end

def test_three_recipients_get_one_notification_each_per_week(settings):
 settings=replace(settings,channel='email',availability_mode='calendar',recipients=('one@example.com','two@example.com','three@example.com'))
 sent=[]
 class MailSender:
  def send(self,recipient,message):
   sent.append(recipient)
   return SendResult('accepted')
 with Store(settings.data_dir/'state.db') as db:
  assert run_once(NOW,settings,Probe([Slot(WEEK,'selectable')]),db,MailSender(),False).status=='notified'
  assert run_once(NOW+timedelta(minutes=5),settings,NoCall(),db,NoCall(),False).status=='notified'
 assert sent==list(settings.recipients)
