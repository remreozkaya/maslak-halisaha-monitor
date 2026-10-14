"""Authenticated SSL SMTP with per-recipient sends and conservative ambiguity handling."""
from email.message import EmailMessage
from hashlib import sha256
import smtplib
import ssl
from .sms import SendResult


class SmtpSender:
    def __init__(self,user,password,host='smtp.gmail.com',port=465,*,factory=None):
        self._user=user
        self._password=password
        self._host=host
        self._port=port
        self._factory=factory or smtplib.SMTP_SSL

    def close(self):
        pass  # Each message owns its short-lived SMTP connection.

    def send(self,recipient: str,message: str) -> SendResult:
        msg=EmailMessage()
        msg['From']=self._user
        msg['To']=recipient
        msg['Subject']='Maslak Halı Saha — rezervasyon bildirimi'
        digest=sha256((recipient+'\n'+message).encode()).hexdigest()
        msg['Message-ID']=f'<maslak-{digest}@{self._user.split("@")[-1]}>'
        msg.set_content(message)
        connection=None
        transmitting=False
        try:
            connection=self._factory(self._host,self._port,context=ssl.create_default_context(),timeout=20)
            connection.login(self._user,self._password)
            transmitting=True
            refused=connection.send_message(msg,from_addr=self._user,to_addrs=[recipient])
            return SendResult('rejected') if refused else SendResult('accepted',msg['Message-ID'])
        except (smtplib.SMTPSenderRefused,smtplib.SMTPRecipientsRefused,smtplib.SMTPDataError,smtplib.SMTPAuthenticationError):
            return SendResult('rejected')
        except (smtplib.SMTPException,OSError):
            return SendResult('unknown' if transmitting else 'rejected')
        finally:
            if connection:
                try:
                    connection.close()
                except (smtplib.SMTPException,OSError):
                    pass
