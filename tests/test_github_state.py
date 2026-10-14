import base64
from datetime import date
import httpx
import pytest
from cryptography.fernet import Fernet
from maslak_monitor.github_state import GithubState, RemoteStore, StateError
from maslak_monitor.site import Slot

WEEK=date(2026,10,19)

class Remote:
    def __init__(self):
        self.content=None
        self.sha=None
        self.fail=False
        self.calls=0
    def handle(self,request):
        import json
        if request.method=='GET':
            if self.content is None:
                return httpx.Response(404)
            return httpx.Response(200,json={'sha':self.sha,'content':self.content})
        self.calls+=1
        if self.fail:
            return httpx.Response(409)
        body=json.loads(request.content)
        assert body.get('sha')==self.sha
        assert body['branch']=='monitor-state'
        self.content=body['content']
        self.sha=str(self.calls)
        return httpx.Response(201,json={'content':{'sha':self.sha}})

@pytest.fixture
def setup():
    remote=Remote()
    key=Fernet.generate_key()
    client=httpx.Client(transport=httpx.MockTransport(remote.handle))
    return remote,key,client

def state(setup):
    remote,key,client=setup
    return GithubState('owner/repo','token',key,client=client)

def test_state_requires_bootstrap_and_never_resets_missing(setup):
    with pytest.raises(StateError):
        with RemoteStore(state(setup)): pass

def bootstrap(setup):
    state(setup).initialize()

def test_roundtrip_encrypts_recipient_and_persists_claim_before_return(setup):
    bootstrap(setup)
    with RemoteStore(state(setup)) as db:
        db.record_opening(WEEK,[Slot(WEEK,'20:00')])
        assert db.claim_recipient(WEEK,'recipient@example.com')
        snapshot=state(setup).load()
        import sqlite3
        copy=sqlite3.connect(':memory:')
        copy.deserialize(snapshot)
        assert copy.execute('select status from recipients').fetchone()[0]=='sending'
        copy.close()
        db.finish_recipient(WEEK,'recipient@example.com','accepted',None)
    ciphertext=base64.b64decode(setup[0].content)
    assert b'recipient@example.com' not in ciphertext
    with RemoteStore(state(setup)) as db:
        assert db.opening(WEEK)==[Slot(WEEK,'20:00')]
        assert not db.claim_recipient(WEEK,'recipient@example.com')

def test_remote_failure_prevents_send_claim_success(setup):
    bootstrap(setup)
    with RemoteStore(state(setup)) as db:
        setup[0].fail=True
        with pytest.raises(StateError):
            db.claim_recipient(WEEK,'recipient@example.com')

def test_crashed_claim_recovers_unknown_and_cannot_resend(setup):
    bootstrap(setup)
    with RemoteStore(state(setup)) as db:
        db.claim_recipient(WEEK,'recipient@example.com')
    with RemoteStore(state(setup)) as db:
        db.recover_interrupted()
        assert db.recipient_state(WEEK,'recipient@example.com')=='unknown'
        assert not db.claim_recipient(WEEK,'recipient@example.com')

def test_no_writes_for_unchanged_state(setup):
    bootstrap(setup)
    with RemoteStore(state(setup)) as db:
        db.recover_interrupted()
        assert db.opening(WEEK) is None
    assert setup[0].calls==1

def test_corrupted_ciphertext_fails_closed(setup):
    bootstrap(setup)
    setup[0].content=base64.b64encode(b'corrupt').decode()
    with pytest.raises(StateError):
        state(setup).load()

def test_wrong_key_fails_closed(setup):
    bootstrap(setup)
    with pytest.raises(StateError):
        GithubState('owner/repo','token',Fernet.generate_key(),client=setup[2]).load()

def test_bootstrap_cannot_overwrite_existing_state(setup):
    bootstrap(setup)
    with pytest.raises(StateError): state(setup).initialize()

def test_committed_claim_with_lost_response_never_resends(setup):
    bootstrap(setup)
    remote,key,client=setup
    normal=remote.handle
    def lost_response(request):
        response=normal(request)
        if request.method=='PUT':
            raise httpx.ReadTimeout('response lost',request=request)
        return response
    client=httpx.Client(transport=httpx.MockTransport(lost_response))
    durable=GithubState('owner/repo','token',key,client=client)
    with RemoteStore(durable) as db:
        with pytest.raises(StateError): db.claim_recipient(WEEK,'recipient@example.com')
    with RemoteStore(state(setup)) as db:
        db.recover_interrupted()
        assert db.recipient_state(WEEK,'recipient@example.com')=='unknown'
        assert not db.claim_recipient(WEEK,'recipient@example.com')

def test_stale_sha_prevents_second_worker_claim(setup):
    bootstrap(setup)
    remote,key,client=setup
    first=RemoteStore(state(setup))
    second=RemoteStore(state(setup))
    with first,second:
        assert first.claim_recipient(WEEK,'recipient@example.com')
        def conflict(request):
            import json
            if request.method=='PUT' and json.loads(request.content).get('sha')!=remote.sha:
                return httpx.Response(409)
            return remote.handle(request)
        second.remote.client=httpx.Client(transport=httpx.MockTransport(conflict))
        with pytest.raises(StateError): second.claim_recipient(WEEK,'recipient@example.com')

def test_failed_finish_after_acceptance_prevents_repeat(setup):
    bootstrap(setup)
    with RemoteStore(state(setup)) as db:
        db.claim_recipient(WEEK,'recipient@example.com')
        setup[0].fail=True
        with pytest.raises(StateError): db.finish_recipient(WEEK,'recipient@example.com','accepted',None)
    setup[0].fail=False
    with RemoteStore(state(setup)) as db:
        db.recover_interrupted()
        assert not db.claim_recipient(WEEK,'recipient@example.com')
