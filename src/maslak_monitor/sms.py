"""Netgsm JSON POST. Acceptance and delivery are different states."""
from dataclasses import dataclass
import httpx

@dataclass(frozen=True)
class SendResult:
    status: str
    provider_id: str | None = None


class NetgsmSender:
    def __init__(self,usercode,password,header,*,client=None):
        self._auth = httpx.BasicAuth(usercode,password)
        self._header = header
        self._owned = client is None
        self._client = client or httpx.Client(timeout=20,follow_redirects=False)

    def close(self):
        if self._owned: self._client.close()

    def send(self,recipient: str,message: str) -> SendResult:
        try:
            response=self._client.post('https://api.netgsm.com.tr/sms/rest/v2/send',
                auth=self._auth,json={'msgheader':self._header,
                'messages':[{'msg':message,'no':recipient}],
                'encoding':'TR','iysfilter':'0'})
            if response.status_code != 200:
                return SendResult('unknown')
            data=response.json()
            if not isinstance(data,dict): return SendResult('unknown')
            code=data.get('code')
            job=data.get('jobid')
            if code=='00' and isinstance(job,str) and job:
                return SendResult('accepted',job)
            # Provider-documented definite rejections; system errors stay ambiguous.
            if code in {'20','30','40','41','50','51','70','80','85'}:
                return SendResult('rejected')
            return SendResult('unknown',job if isinstance(job,str) else None)
        except (httpx.HTTPError,ValueError):
            return SendResult('unknown')
