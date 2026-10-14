import httpx
import pytest
from maslak_monitor.sms import NetgsmSender


def sender(handler):
 client=httpx.Client(transport=httpx.MockTransport(handler))
 return NetgsmSender('user','secret','TEST',client=client)

def test_netgsm_acceptance_has_provider_id_and_correct_payload():
 def reply(request):
  import json
  assert request.method=='POST'
  assert request.url == 'https://api.netgsm.com.tr/sms/rest/v2/send'
  assert 'secret' not in str(request.url)
  data=json.loads(request.content)
  assert data['messages']==[{'msg':'test message','no':'5551111111'}]
  assert data['msgheader']=='TEST' and data['iysfilter']=='0'
  assert request.headers['Authorization'].startswith('Basic ')
  return httpx.Response(200,json={'code':'00','jobid':'1234','description':'queued'})
 result=sender(reply).send('5551111111','test message')
 assert (result.status,result.provider_id)==('accepted','1234')

@pytest.mark.parametrize('code',['20','30','40','50','51','70','80','85'])
def test_explicit_provider_rejections_are_retryable_without_duplicate(code):
 result=sender(lambda r:httpx.Response(200,json={'code':code,'description':'error'})).send('5551111111','message')
 assert result.status=='rejected'

@pytest.mark.parametrize('response',[httpx.Response(503,text='oops'),httpx.Response(200,json={'code':'00'}),httpx.Response(200,json={'code':'100'}),httpx.Response(200,text='not json')])
def test_ambiguous_response_never_claims_rejection_or_acceptance(response):
 assert sender(lambda r:response).send('5551111111','message').status=='unknown'

def test_network_timeout_is_unknown():
 def timeout(request): raise httpx.ReadTimeout('contains credentials',request=request)
 assert sender(timeout).send('5551111111','message').status=='unknown'
