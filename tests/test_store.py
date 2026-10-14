from datetime import date
from concurrent.futures import ThreadPoolExecutor
from maslak_monitor.store import Store
from maslak_monitor.site import Slot

WEEK=date(2026,10,19)
PHONE='5551111111'

def test_reopening_keeps_accepted_recipient_and_opening(tmp_path):
 path=tmp_path/'state.db'
 with Store(path) as db:
  db.record_opening(WEEK,[Slot(WEEK,'20:00')])
  assert db.claim_recipient(WEEK,PHONE)
  db.finish_recipient(WEEK,PHONE,'accepted','id-1')
 with Store(path) as db:
  assert not db.claim_recipient(WEEK,PHONE)
  assert db.opening(WEEK)==[Slot(WEEK,'20:00')]
  assert db.claim_recipient(date(2026,10,26),PHONE)

def test_unknown_and_interrupted_send_never_blindly_retries(tmp_path):
 with Store(tmp_path/'state.db') as db:
  assert db.claim_recipient(WEEK,PHONE)
  db.recover_interrupted()
  assert db.recipient_state(WEEK,PHONE)=='unknown'
  assert not db.claim_recipient(WEEK,PHONE)

def test_atomic_claim_across_connections(tmp_path):
 path=tmp_path/'state.db'
 with Store(path): pass
 def claim(_):
  with Store(path) as db: return db.claim_recipient(WEEK,PHONE)
 with ThreadPoolExecutor(max_workers=2) as pool:
  assert sorted(pool.map(claim,range(2))) == [False,True]

def test_rejected_recipient_capped_at_three_attempts_and_independent(tmp_path):
 with Store(tmp_path/'state.db') as db:
  for _ in range(3):
   assert db.claim_recipient(WEEK,PHONE)
   db.finish_recipient(WEEK,PHONE,'rejected',None)
  assert not db.claim_recipient(WEEK,PHONE)
  assert db.claim_recipient(WEEK,'5552222222')
