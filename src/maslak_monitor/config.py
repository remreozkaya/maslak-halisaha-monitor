"""Settings are read only from the process environment."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import re


def _bool(value: str) -> bool:
    if value.lower() not in ('true', 'false'):
        raise ValueError('Boolean settings must be true or false')
    return value.lower() == 'true'


def normalize_phone(value: str) -> str:
    number = re.sub(r'[\s()+-]', '', value)
    if number.startswith('90') and len(number) == 12:
        number = number[2:]
    elif number.startswith('0') and len(number) == 11:
        number = number[1:]
    if not re.fullmatch(r'5\d{9}', number):
        raise ValueError('SMS_RECIPIENTS requires Turkish mobile numbers')
    return number


def normalize_email(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value):
        raise ValueError('A valid single email address is required')
    return value.casefold()


@dataclass(frozen=True)
class Settings:
    username: str = field(repr=False)
    password: str = field(repr=False)
    dry_run: bool = True
    interval: int = 120
    data_dir: Path = Path('data')
    recipients: tuple[str, ...] = field(default=(), repr=False)
    sms_user: str = field(default='', repr=False)
    sms_password: str = field(default='', repr=False)
    sms_header: str = ''
    purchase_text: str = 'Satın Al'
    selector_verified: bool = False
    channel: str = 'sms'
    smtp_user: str = field(default='', repr=False)
    smtp_password: str = field(default='', repr=False)
    smtp_host: str = 'smtp.gmail.com'
    smtp_port: int = 465

    @classmethod
    def from_env(cls, env=None):
        env = os.environ if env is None else env
        user, password = env.get('ITU_USERNAME', ''), env.get('ITU_PASSWORD', '')
        if not user or not password:
            raise ValueError('ITU_USERNAME and ITU_PASSWORD required')
        try:
            interval = int(env.get('CHECK_INTERVAL', '120'))
        except ValueError:
            raise ValueError('CHECK_INTERVAL must be a positive integer') from None
        if interval <= 0:
            raise ValueError('CHECK_INTERVAL must be positive')
        dry = _bool(env.get('DRY_RUN', 'true'))
        verified = _bool(env.get('PURCHASE_SELECTOR_VERIFIED', 'false'))
        channel = env.get('NOTIFICATION_CHANNEL', 'sms').lower()
        if channel not in ('sms', 'email'):
            raise ValueError('NOTIFICATION_CHANNEL must be sms or email')
        smtp_user = env.get('SMTP_USER', '')
        if smtp_user:
            smtp_user = normalize_email(smtp_user)
        smtp_password = env.get('SMTP_PASSWORD', '')
        smtp_host = env.get('SMTP_HOST', 'smtp.gmail.com')
        if not smtp_host or any(c.isspace() for c in smtp_host):
            raise ValueError('SMTP_HOST must be a host name')
        try:
            smtp_port = int(env.get('SMTP_PORT', '465'))
        except ValueError:
            raise ValueError('SMTP_PORT must be a TCP port') from None
        if not 1 <= smtp_port <= 65535:
            raise ValueError('SMTP_PORT must be a TCP port')
        raw = env.get('EMAIL_RECIPIENTS' if channel == 'email' else 'SMS_RECIPIENTS', '')
        normalize = normalize_email if channel == 'email' else normalize_phone
        numbers = tuple(normalize(n.strip()) for n in raw.split(',')) if raw else ()
        if numbers and (len(numbers) != 2 or len(set(numbers)) != 2):
            raise ValueError('Exactly two distinct notification recipients required')
        sms_user = env.get('NETGSM_USERCODE', '')
        sms_pass = env.get('NETGSM_PASSWORD', '')
        header = env.get('NETGSM_HEADER', '')
        purchase = env.get('PURCHASE_BUTTON_TEXT', 'Satın Al').strip()
        if not purchase:
            raise ValueError('PURCHASE_BUTTON_TEXT required')
        if not dry:
            if channel == 'email' and (len(numbers) != 2 or not smtp_user or not smtp_password):
                raise ValueError('Two EMAIL_RECIPIENTS and SMTP_USER/SMTP_PASSWORD required')
            if channel == 'sms' and (len(numbers) != 2 or not sms_user or not sms_pass or not 3 <= len(header) <= 11):
                raise ValueError('Two SMS_RECIPIENTS and Netgsm credentials/header required')
            if not verified:
                raise ValueError('PURCHASE_SELECTOR_VERIFIED must be true before live notifications')
        return cls(user, password, dry, interval, Path(env.get('DATA_DIR', 'data')),
                   numbers, sms_user, sms_pass, header, purchase, verified,
                   channel, smtp_user, smtp_password, smtp_host, smtp_port)
