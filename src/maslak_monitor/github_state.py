"""Encrypted durable state on a dedicated GitHub branch; fail closed on loss."""
import base64
import re
import httpx
from cryptography.fernet import Fernet, InvalidToken
from .store import Store

class StateError(RuntimeError):
    pass

class GithubState:
    def __init__(self, repository, token, key, client=None):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
            raise ValueError('Invalid repository')
        self.cipher=Fernet(key)
        self.url=f'https://api.github.com/repos/{repository}/contents/state.enc'
        self.client=client or httpx.Client(timeout=30,follow_redirects=False)
        self.headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json',
                      'X-GitHub-Api-Version':'2022-11-28'}
        self.sha=None

    def load(self):
        try:
            response=self.client.get(self.url,params={'ref':'monitor-state'},headers=self.headers)
            if response.status_code!=200:
                raise StateError('Remote state unavailable; refusing to reset notification history')
            data=response.json()
            result=self.cipher.decrypt(base64.b64decode(data['content']))
            self.sha=data['sha']
            return result
        except (httpx.HTTPError,InvalidToken,ValueError,KeyError,TypeError) as exc:
            raise StateError('Remote state could not be authenticated or loaded') from None

    def save(self, snapshot):
        payload={'message':'Persist encrypted monitor state','branch':'monitor-state',
                 'content':base64.b64encode(self.cipher.encrypt(snapshot)).decode()}
        if self.sha is not None:
            payload['sha']=self.sha
        try:
            response=self.client.put(self.url,json=payload,headers=self.headers)
            if response.status_code not in (200,201):
                raise StateError('Remote state write failed; notification stopped')
            self.sha=response.json()['content']['sha']
        except (httpx.HTTPError,ValueError,KeyError,TypeError):
            raise StateError('Remote state write unconfirmed; notification stopped') from None

    def initialize(self):
        # Explicit one-time provisioning only. Normal jobs never create missing state.
        response=self.client.get(self.url,params={'ref':'monitor-state'},headers=self.headers)
        if response.status_code!=404:
            raise StateError('State initialization requires an absent file')
        with Store(':memory:') as db:
            self.save(db.db.serialize())

    def close(self):
        self.client.close()

class RemoteStore(Store):
    def __init__(self, remote):
        super().__init__(':memory:')
        self.remote=remote
        try:
            self.db.deserialize(remote.load())
        except Exception:
            self.db.close()
            raise
        self.snapshot=self.db.serialize()

    def checkpoint(self):
        snapshot=self.db.serialize()
        if snapshot!=self.snapshot:
            self.remote.save(snapshot)
            self.snapshot=snapshot

    def record_opening(self,*args):
        super().record_opening(*args)
        self.checkpoint()

    def claim_recipient(self,*args):
        claimed=super().claim_recipient(*args)
        # Must finish remote commit before caller can send an email.
        self.checkpoint()
        return claimed

    def finish_recipient(self,*args):
        super().finish_recipient(*args)
        self.checkpoint()

    def recover_interrupted(self):
        super().recover_interrupted()
        self.checkpoint()
