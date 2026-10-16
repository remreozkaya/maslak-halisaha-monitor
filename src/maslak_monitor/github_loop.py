"""Five-minute polling within a runner, with a bounded workflow handoff.

GitHub cron is a fallback/start trigger, not the clock for individual checks.
Notification claims remain serialized by the workflow concurrency group.
"""
import argparse
from datetime import datetime
import logging
import math
import os
import re
import signal
import subprocess
import sys
import time

import httpx
from .schedule import ISTANBUL, window_at

LOG = logging.getLogger('maslak-monitor')
INTERVAL = 300
MAX_CHECKS = 61  # Five hours plus the initial check; below the six-hour job limit.


def check_once():
    process = subprocess.Popen(
        [sys.executable, '-m', 'maslak_monitor.github_runner'],
        start_new_session=True,
    )
    try:
        return process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        # Kill the browser descendants too, and retry on the next scheduled tick.
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        LOG.error('status=check_timeout')
        return 1


def dispatch_successor(client=None):
    repository = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    owned = client is None
    client = client or httpx.Client(timeout=30, follow_redirects=False)
    try:
        for attempt in range(3):
            try:
                response = client.post(
                    f'https://api.github.com/repos/{repository}/actions/workflows/monitor.yml/dispatches',
                    headers={
                        'Authorization': f"Bearer {os.environ['GITHUB_TOKEN']}",
                        'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28',
                    },
                    json={'ref': 'main', 'inputs': {'mode': 'monitor'}},
                )
                if response.status_code == 204:
                    LOG.warning('status=successor_queued')
                    return
                if response.status_code < 500 and response.status_code != 429:
                    break
            except httpx.HTTPError:
                pass
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
        raise RuntimeError('Workflow handoff failed')
    finally:
        if owned:
            client.close()


def run_loop(checks=MAX_CHECKS):
    if not 1 <= checks <= MAX_CHECKS:
        raise ValueError('Checks must be between 1 and 61')
    start = time.monotonic()
    due = start
    failed = False
    for tick in range(checks):
        now = datetime.now(ISTANBUL)
        window = window_at(now)
        delay = max(0, due - time.monotonic())
        if window and now < window.end:
            delay = min(delay, (window.end - now).total_seconds())
        time.sleep(delay)
        now = datetime.now(ISTANBUL)
        window = window_at(now)
        if window is None:
            LOG.warning('status=outside_window tick=%s', tick + 1)
        else:
            LOG.warning('check_started_at=%s tick=%s interval_seconds=300', now.isoformat(), tick + 1)
            try:
                result = check_once()
            except Exception as exc:
                LOG.error('check_failed_type=%s', type(exc).__name__)
                result = 1
            failed = failed or result != 0
            LOG.warning('check_finished_at=%s exit_code=%s', datetime.now(ISTANBUL).isoformat(), result)
        # Anchor to starts, not completion times; skip missed ticks without bursts.
        due = start + (math.floor((time.monotonic() - start) / INTERVAL) + 1) * INTERVAL
    # Keep the clock alive between windows too; next Friday must not depend on cron.
    # This does not access the ITU site or send email outside the approved window.
    if os.environ.get('DRY_RUN', 'true').lower() == 'false':
        try:
            dispatch_successor()
        except Exception as exc:
            LOG.error('handoff_failed_type=%s', type(exc).__name__)
            return 1
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checks', type=int, default=MAX_CHECKS, choices=range(1, MAX_CHECKS + 1))
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format='%(message)s')
    return run_loop(checks=args.checks)


if __name__ == '__main__':
    raise SystemExit(main())
