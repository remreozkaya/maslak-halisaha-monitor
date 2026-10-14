import pytest
from maslak_monitor.config import Settings

BASE = {'ITU_USERNAME':'sample-user','ITU_PASSWORD':'sample-secret'}

def test_dry_run_needs_no_sms_credentials():
 s = Settings.from_env(BASE)
 assert s.dry_run and s.interval == 120
 assert 'sample-secret' not in repr(s)

@pytest.mark.parametrize('extra', [
 {'CHECK_INTERVAL':'0'}, {'CHECK_INTERVAL':'nan'}, {'DRY_RUN':'maybe'},
 {'DRY_RUN':'false'},
 {'SMS_RECIPIENTS':'+905551111111,05551111111'},
 {'SMS_RECIPIENTS':'invalid,also-invalid'},
])
def test_invalid_configuration_refused(extra):
 with pytest.raises(ValueError): Settings.from_env(BASE | extra)

def test_live_mode_requires_verification():
 data = BASE | {'DRY_RUN':'false','SMS_RECIPIENTS':'05551111111,05552222222',
 'NETGSM_USERCODE':'test','NETGSM_PASSWORD':'secret','NETGSM_HEADER':'TEST'}
 with pytest.raises(ValueError,match='PURCHASE_SELECTOR_VERIFIED'): Settings.from_env(data)
 s = Settings.from_env(data | {'PURCHASE_SELECTOR_VERIFIED':'true'})
 assert s.recipients == ('5551111111','5552222222')
 assert 'secret' not in repr(s)
