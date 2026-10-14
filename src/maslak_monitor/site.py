"""Normal browser UI only; never clicks a purchase control."""
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlsplit

URL = 'https://kampuskart.itu.edu.tr/SosyalTesis/OdemeDiger'
MONTHS = ('Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık')
EN_MONTHS = ('January','February','March','April','May','June','July','August','September','October','November','December')

class ProbeError(RuntimeError):
    pass

class AuthRequired(ProbeError):
    pass

@dataclass(frozen=True)
class Slot:
    day: date
    label: str


def classify_rows(day: date, rows: list[dict], purchase_text: str) -> list[Slot]:
    if not rows:
        raise ProbeError('Session table empty or not loaded')
    result = []
    for row in rows:
        if not row.get('label') or not row.get('controls'):
            raise ProbeError('Session row structure unknown')
        for control in row['controls']:
            if not control['visible'] or control['disabled']:
                continue
            if control['text'].strip().casefold() != purchase_text.casefold():
                raise ProbeError('Enabled session control is not recognized')
            result.append(Slot(day, row['label']))
    return result


class SiteProbe:
    def __init__(self, settings, *, page=None):
        self.settings = settings
        self.page = page
        self._playwright = None
        self._browser = None

    def __enter__(self):
        if self.page is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch()
            self.page = self._browser.new_page(locale='tr-TR')
        self.page.set_default_timeout(15000)
        return self

    def __exit__(self, *args):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _login_if_needed(self):
        page = self.page
        if page.locator('#btn_cookie_ok').is_visible():
            page.locator('#btn_cookie_ok').click()
        if '/User/Login' in page.url:
            page.locator('a[href="/User/LoginITU"]').click()
            page.wait_for_url(lambda value: urlsplit(value).hostname == 'girisv3.itu.edu.tr' or
                              (urlsplit(value).hostname == 'kampuskart.itu.edu.tr' and
                               '/User/Login' not in urlsplit(value).path),
                              wait_until='networkidle',timeout=30000)
        if urlsplit(page.url).hostname == 'girisv3.itu.edu.tr':
            user = page.locator('input[type="text"]:visible')
            password = page.locator('input[type="password"]:visible')
            if user.count() != 1 or password.count() != 1:
                raise AuthRequired('Login form changed or additional verification needed')
            user.fill(self.settings.username)
            password.fill(self.settings.password)
            page.locator('#ContentPlaceHolder1_btnLogin').click()
            page.wait_for_url('https://kampuskart.itu.edu.tr/**',timeout=30000)
            page.goto(URL,wait_until='networkidle')
        if urlsplit(page.url).hostname != 'kampuskart.itu.edu.tr' or '/User/Login' in page.url:
            raise AuthRequired('ITU login required; verification may need operator action')

    def _remember_rows(self):
        # Retain identities, not text: adjacent days may contain identical session text.
        self.page.evaluate("() => { window.__maslakOldRows = [...document.querySelectorAll('#tblSeanslar tbody tr')]; }")

    def _read_rows(self, day):
        rows = self.page.locator('#tblSeanslar tbody tr').evaluate_all('''rows => rows.map(row => ({
            label: row.querySelector('td')?.innerText.trim() || '',
            controls: [...row.querySelectorAll('button,a,input[type="button"],input[type="submit"]')].map(el => ({
                text: (el.innerText || el.value || '').trim(),
                disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('disabled'),
                visible: el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden'
            }))
        }))''')
        text = self.settings.purchase_text if self.settings else 'Satın Al'
        return classify_rows(day, rows, text)

    def inspect_day(self, day: date) -> list[Slot]:
        page = self.page
        calendar = page.locator('.flatpickr-calendar.open')
        if not calendar.count():
            page.locator('#btnTarih').click()
        labels = [f'{months[day.month-1]} {day.day}, {day.year}' for months in (MONTHS,EN_MONTHS)]
        target = None
        for _ in range(3):
            for label in labels:
                candidate = page.locator('.flatpickr-calendar.open').get_by_label(label,exact=True)
                if candidate.count():
                    target = candidate
                    break
            if target:
                break
            # The target can be in the next month; disabled calendar navigation is respected.
            nxt = page.locator('.flatpickr-calendar.open .flatpickr-next-month:not(.flatpickr-disabled)')
            if not nxt.count() or not nxt.is_visible():
                raise ProbeError('Target dates absent and calendar navigation unavailable')
            nxt.click()
        if target is None:
            raise ProbeError('Target date absent from calendar')
        if 'flatpickr-disabled' in (target.get_attribute('class') or ''):
            return []
        if page.locator('#txtTarih').input_value() == day.isoformat():
            # Valid only immediately after a completed fresh page load/site selection.
            return self._read_rows(day)
        self._remember_rows()
        origin = urlsplit(page.url).netloc
        try:
            with page.expect_response(lambda r: urlsplit(r.url).netloc == origin and
                                      r.request.resource_type in ('xhr','fetch'),timeout=15000) as pending:
                target.click()
            response = pending.value
            if not response.ok:
                raise ProbeError('Date refresh failed')
            response.finished()
            page.wait_for_function('''expected =>
                document.querySelector('#txtTarih')?.value === expected &&
                window.__maslakOldRows?.length > 0 &&
                window.__maslakOldRows.every(row => !row.isConnected) &&
                document.querySelectorAll('#tblSeanslar tbody tr').length > 0
            ''',arg=day.isoformat(),timeout=15000)
            page.wait_for_load_state('networkidle')
            if urlsplit(page.url).netloc != origin:
                raise AuthRequired('Session lost during date refresh')
            return self._read_rows(day)
        except ProbeError:
            raise
        except Exception:
            raise ProbeError('Date refresh could not be verified') from None

    def check_week(self, week_start: date) -> list[Slot]:
        if self.page is None:
            raise ProbeError('Browser not started')
        try:
            self.page.goto(URL,wait_until='networkidle')
            self._login_if_needed()
            if self.page.locator('#btn_cookie_ok').is_visible():
                self.page.locator('#btn_cookie_ok').click()
            self.page.locator('#cmbUst').select_option(label='Halı Saha')
            self.page.locator('#cmbAlt').get_by_role('option',name='Maslak Halı Saha',exact=True).wait_for(state='attached')
            self.page.locator('#cmbAlt').select_option(label='Maslak Halı Saha')
            self.page.wait_for_load_state('networkidle')
            for offset in range(7):
                found = self.inspect_day(week_start + timedelta(days=offset))
                if found:
                    return found
            return []
        except ProbeError:
            raise
        except Exception:
            raise ProbeError('Site inspection failed; check authentication and DOM') from None
