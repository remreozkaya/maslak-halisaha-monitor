from datetime import datetime, timedelta
import httpx
import pytest
from maslak_monitor import github_loop


class Clock:
    def __init__(self, start='2026-10-16T17:00:00+03:00'):
        self.start = datetime.fromisoformat(start)
        self.elapsed = 0

    def now(self, tz):
        return self.start + timedelta(seconds=self.elapsed)

    def monotonic(self):
        return self.elapsed

    def sleep(self, seconds):
        self.elapsed += seconds


def setup_clock(monkeypatch, clock):
    monkeypatch.setattr(github_loop, 'datetime', clock)
    monkeypatch.setattr(github_loop.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(github_loop.time, 'sleep', clock.sleep)
    monkeypatch.setenv('DRY_RUN', 'false')


def test_checks_start_300_seconds_apart_without_accumulating_check_duration(monkeypatch):
    clock = Clock()
    setup_clock(monkeypatch, clock)
    starts = []
    handoffs = []

    def check():
        starts.append(clock.elapsed)
        clock.elapsed += 12
        return 0

    monkeypatch.setattr(github_loop, 'check_once', check)
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: handoffs.append(clock.elapsed))
    assert github_loop.run_loop(checks=3) == 0
    assert starts == [0, 300, 600]
    assert handoffs == [612]


def test_failed_check_does_not_stop_next_check_or_handoff(monkeypatch):
    clock = Clock()
    setup_clock(monkeypatch, clock)
    starts = []
    handoffs = []

    def check():
        starts.append(clock.elapsed)
        return int(len(starts) == 1)

    monkeypatch.setattr(github_loop, 'check_once', check)
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: handoffs.append(True))
    assert github_loop.run_loop(checks=2) == 1
    assert starts == [0, 300]
    assert handoffs == [True]


def test_monday_window_end_stops_site_checks_but_keeps_clock_alive(monkeypatch):
    clock = Clock('2026-10-19T09:58:00+03:00')
    setup_clock(monkeypatch, clock)
    starts = []
    monkeypatch.setattr(github_loop, 'check_once', lambda: starts.append(clock.elapsed) or 0)
    handoffs = []
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: handoffs.append(True))
    assert github_loop.run_loop(checks=3) == 0
    assert starts == [0, 120]
    assert handoffs == [True]


def test_slow_check_skips_missed_ticks_instead_of_bursting(monkeypatch):
    clock = Clock()
    setup_clock(monkeypatch, clock)
    starts = []

    def check():
        starts.append(clock.elapsed)
        clock.elapsed += 340
        return 0

    monkeypatch.setattr(github_loop, 'check_once', check)
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: None)
    assert github_loop.run_loop(checks=2) == 0
    assert starts == [0, 600]


def test_outside_window_does_not_access_site_credentials_but_preserves_successor(monkeypatch):
    clock = Clock('2026-10-20T12:00:00+03:00')
    setup_clock(monkeypatch, clock)
    monkeypatch.setattr(github_loop, 'check_once', lambda: pytest.fail('outside window check'))
    handoffs = []
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: handoffs.append(clock.elapsed))
    assert github_loop.run_loop(checks=3) == 0
    assert handoffs == [600]


def test_idle_worker_enters_friday_window_without_a_new_cron_event(monkeypatch):
    clock = Clock('2026-10-16T09:55:00+03:00')
    setup_clock(monkeypatch, clock)
    starts = []
    monkeypatch.setattr(github_loop, 'check_once', lambda: starts.append(clock.elapsed) or 0)
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: None)
    assert github_loop.run_loop(checks=3) == 0
    assert starts == [300, 600]


def test_dry_run_never_dispatches_live_successor(monkeypatch):
    setup_clock(monkeypatch, Clock())
    monkeypatch.setenv('DRY_RUN', 'true')
    monkeypatch.setattr(github_loop, 'check_once', lambda: 0)
    monkeypatch.setattr(github_loop, 'dispatch_successor', lambda: pytest.fail('dry run live handoff'))
    assert github_loop.run_loop(checks=2) == 0


def test_successor_uses_workflow_dispatch_and_normal_monitor_not_email_test(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.setenv('GITHUB_TOKEN', 'private-token')
    requests = []

    def handle(request):
        import json
        requests.append(request)
        assert request.method == 'POST'
        assert str(request.url) == 'https://api.github.com/repos/owner/repo/actions/workflows/monitor.yml/dispatches'
        assert request.headers['Authorization'] == 'Bearer private-token'
        assert json.loads(request.content) == {'ref': 'main', 'inputs': {'mode': 'monitor'}}
        return httpx.Response(204)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        github_loop.dispatch_successor(client=client)
    assert len(requests) == 1


def test_handoff_retries_definite_server_failure(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.setenv('GITHUB_TOKEN', 'private-token')
    monkeypatch.setattr(github_loop.time, 'sleep', lambda seconds: None)
    statuses = iter([503, 204])
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(next(statuses)))) as client:
        github_loop.dispatch_successor(client=client)
    with pytest.raises(StopIteration):
        next(statuses)


def test_handoff_failure_is_not_reported_as_success(monkeypatch):
    setup_clock(monkeypatch, Clock())
    monkeypatch.setattr(github_loop, 'check_once', lambda: 0)

    def fail():
        raise RuntimeError('handoff unavailable')

    monkeypatch.setattr(github_loop, 'dispatch_successor', fail)
    assert github_loop.run_loop(checks=1) == 1


@pytest.mark.parametrize('checks', [0, -1, 62])
def test_invalid_session_length_is_rejected(checks):
    with pytest.raises(ValueError):
        github_loop.run_loop(checks=checks)
