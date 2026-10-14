from datetime import datetime
from types import SimpleNamespace
from dataclasses import replace
from maslak_monitor import github_runner
from maslak_monitor.config import Settings

class Clock:
    @staticmethod
    def now(tz): return datetime.fromisoformat('2026-10-16T10:05:00+03:00')

class Probe:
    def __init__(self,settings): pass
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def check_week(self,week): return []

def test_outside_window_needs_no_secrets_or_browser(monkeypatch):
    monkeypatch.setattr(github_runner,'window_at',lambda now:None)
    monkeypatch.setattr(github_runner.Settings,'from_env',lambda:(_ for _ in ()).throw(AssertionError()))
    assert github_runner.main()==0

def test_dry_run_with_closed_week_needs_no_remote_state(monkeypatch):
    monkeypatch.setattr(github_runner,'datetime',Clock)
    monkeypatch.setattr(github_runner.Settings,'from_env',lambda:Settings('user','secret'))
    monkeypatch.setattr(github_runner,'SiteProbe',Probe)
    assert github_runner.main()==0

def test_missing_remote_state_stops_before_browser_or_smtp(monkeypatch):
    monkeypatch.setattr(github_runner,'datetime',Clock)
    monkeypatch.setattr(github_runner.Settings,'from_env',lambda:replace(Settings('user','secret'),dry_run=False))
    assert github_runner.main()==1
