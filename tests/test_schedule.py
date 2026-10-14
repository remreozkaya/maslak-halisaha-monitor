from datetime import date, datetime, timezone
import pytest
from maslak_monitor.schedule import window_at, next_window

@pytest.mark.parametrize('stamp,week', [
 ('2026-10-16T09:59:00+03:00',None),
 ('2026-10-16T10:00:00+03:00','2026-10-19'),
 ('2026-10-17T12:00:00+03:00','2026-10-19'),
 ('2026-10-18T23:59:00+03:00','2026-10-19'),
 ('2026-10-19T09:59:00+03:00','2026-10-19'),
 ('2026-10-19T10:00:00+03:00','2026-10-19'),
 ('2026-10-19T10:00:01+03:00',None),
 ('2026-10-20T10:00:00+03:00',None),
 ('2026-12-31T10:00:00+03:00',None),
 ('2027-01-01T10:00:00+03:00','2027-01-04'),
 ('2026-10-16T07:00:00+00:00','2026-10-19'),
])
def test_window_boundaries_and_fixed_target(stamp,week):
 w = window_at(datetime.fromisoformat(stamp))
 assert (w.week_start.isoformat() if w else None) == week
 if w:
  assert w.start.weekday() == 4
  assert w.end.weekday() == 0
  assert w.start.hour == w.end.hour == 10

def test_next_window_after_monday_close():
 w = next_window(datetime.fromisoformat('2026-10-19T10:00:01+03:00'))
 assert w.start.isoformat() == '2026-10-23T10:00:00+03:00'
 assert w.week_start == date(2026,10,26)

def test_naive_datetime_rejected():
 with pytest.raises(ValueError): window_at(datetime(2026,10,16,10))
