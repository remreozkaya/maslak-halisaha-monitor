from email.message import EmailMessage
import smtplib
import pytest
from maslak_monitor.email_sender import SmtpSender
from maslak_monitor.config import Settings

BASE={'ITU_USERNAME':'sample-user','ITU_PASSWORD':'sample-secret','NOTIFICATION_CHANNEL':'email',
      'EMAIL_RECIPIENTS':'first@example.com,second@example.com'}

def test_email_mode_does_not_require_sms_credentials():
 s=Settings.from_env(BASE)
 assert s.channel=='email' and s.recipients==('first@example.com','second@example.com')
 assert s.dry_run

def test_live_email_requires_smtp_auth_and_verified_purchase():
 data=BASE | {'DRY_RUN':'false','SMTP_USER':'sender@gmail.com','SMTP_PASSWORD':'app-secret'}
 with pytest.raises(ValueError,match='PURCHASE_SELECTOR_VERIFIED'): Settings.from_env(data)
 s=Settings.from_env(data|{'PURCHASE_SELECTOR_VERIFIED':'true'})
 assert 'app-secret' not in repr(s)

@pytest.mark.parametrize('extra',[{'EMAIL_RECIPIENTS':'first@example.com,first@example.com'},
 {'EMAIL_RECIPIENTS':'one@example.com'}, {'EMAIL_RECIPIENTS':'bad\r\nBcc: x@example.com,second@example.com'},
 {'SMTP_PORT':'0'}, {'NOTIFICATION_CHANNEL':'unknown'}, {'SMTP_USER':'sender@example.com\r\nBcc: e@example.com'}])
def test_invalid_email_configuration_refused(extra):
 with pytest.raises(ValueError): Settings.from_env(BASE|extra)

class Connection:
 def __init__(self,login_error=None,send_error=None,refused=None):
  self.login_error=login_error; self.send_error=send_error; self.refused=refused or {}; self.messages=[]
 def login(self,user,password):
  assert user=='sender@gmail.com' and password=='app-secret'
  if self.login_error: raise self.login_error
 def send_message(self,msg,from_addr,to_addrs):
  assert from_addr=='sender@gmail.com' and to_addrs==['first@example.com']
  self.messages.append(msg)
  if self.send_error: raise self.send_error
  return self.refused
 def close(self): pass


def sender(connection):
 def factory(host,port,**options):
  assert host=='smtp.gmail.com' and port==465
  assert options['context'].check_hostname
  return connection
 return SmtpSender('sender@gmail.com','app-secret',factory=factory)

def test_email_accepted_only_after_smtp_acceptance_with_trace_id():
 connection=Connection()
 result=sender(connection).send('first@example.com','Maslak Hali Saha: 2026-10-19 haftasinda seans acildi.')
 assert result.status=='accepted' and result.provider_id
 msg=connection.messages[0]
 assert isinstance(msg,EmailMessage)
 assert msg['To']=='first@example.com'
 assert '2026-10-19' in msg.get_content()
 assert msg['Message-ID']==result.provider_id

@pytest.mark.parametrize('error',[smtplib.SMTPRecipientsRefused({'first@example.com':(550,b'refused')}),smtplib.SMTPDataError(550,b'refused')])
def test_definite_smtp_rejection_can_retry(error):
 assert sender(Connection(send_error=error)).send('first@example.com','hello').status=='rejected'

def test_disconnect_after_data_is_unknown_and_not_retryable():
 assert sender(Connection(send_error=smtplib.SMTPServerDisconnected('lost'))).send('first@example.com','hello').status=='unknown'

def test_login_failure_is_definite_rejection_no_message_sent():
 connection=Connection(login_error=smtplib.SMTPAuthenticationError(535,b'auth failed'))
 assert sender(connection).send('first@example.com','hello').status=='rejected'
 assert connection.messages==[]

def test_quit_failure_does_not_hide_accepted_message():
 class BrokenClose(Connection):
  def close(self): raise OSError('socket closed')
 assert sender(BrokenClose()).send('first@example.com','hello').status=='accepted'

def test_email_channel_uses_smtp_sender_instead_of_sms(monkeypatch):
 from maslak_monitor import main as service
 monkeypatch.setattr(smtplib,'SMTP_SSL',lambda *a,**kw:Connection())
 settings=Settings.from_env(BASE|{'DRY_RUN':'false','SMTP_USER':'sender@gmail.com','SMTP_PASSWORD':'app-secret','PURCHASE_SELECTOR_VERIFIED':'true'})
 transport=service.make_sender(settings)
 assert transport.send('first@example.com','test mail').status=='accepted'


def test_test_email_command_sends_two_messages_without_querying_site(monkeypatch,tmp_path):
 from maslak_monitor import main as service
 for key,value in (BASE|{'SMTP_USER':'sender@gmail.com','SMTP_PASSWORD':'app-secret','DATA_DIR':str(tmp_path)}).items():
  monkeypatch.setenv(key,value)
 messages=[]
 class MailConnection(Connection):
  def send_message(self,msg,from_addr,to_addrs):
   messages.append((msg['To'],msg.get_content()))
   return {}
 monkeypatch.setattr(smtplib,'SMTP_SSL',lambda *a,**kw:MailConnection())
 monkeypatch.setattr(service,'SiteProbe',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Site must not be queried')))
 assert service.main(['--test-email'])==0
 assert {r for r,_ in messages}=={'first@example.com','second@example.com'}
 assert all('TEST' in body for _,body in messages)

def test_explicit_sender_rejection_is_retryable_not_unknown():
 error=smtplib.SMTPSenderRefused(451,b'Temporary sender rejection','sender@gmail.com')
 assert sender(Connection(send_error=error)).send('first@example.com','hello').status=='rejected'
