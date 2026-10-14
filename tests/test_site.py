from datetime import date
import pytest
from maslak_monitor.site import ProbeError, Slot, classify_rows, SiteProbe

DAY = date(2026,10,19)

def row(text='Satın Al', disabled=False, visible=True):
 return {'label':'20:00-21:00','controls':[{'text':text,'disabled':disabled,'visible':visible}]}

@pytest.mark.parametrize('item', [row('[Mesaj_Dolu]',True), row('[Mesaj_SatinAlinamaz]',True), row(visible=False)])
def test_closed_or_hidden_controls_do_not_alert(item):
 assert classify_rows(DAY,[item],'Satın Al') == []

def test_only_recognized_visible_enabled_purchase_alerts():
 assert classify_rows(DAY,[row()],'Satın Al') == [Slot(DAY,'20:00-21:00')]

@pytest.mark.parametrize('items', [[],[row('Bilinmeyen')],[{'label':'','controls':[]}],[{'label':'x','controls':[]}]] )
def test_incomplete_and_unknown_table_is_error(items):
 with pytest.raises(ProbeError): classify_rows(DAY,items,'Satın Al')

@pytest.fixture
def page():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser = p.chromium.launch()
  page = browser.new_page()
  page.route('**/*',lambda route:route.abort())
  yield page
  browser.close()

HTML = '''<input id="txtTarih" readonly value="2026-10-13">
<button id="btnTarih">Takvim</button>
<div class="flatpickr-calendar open"><span class="flatpickr-day" aria-label="Ekim 19, 2026" onclick="loadDay()">19</span>
<span class="flatpickr-day flatpickr-disabled" aria-label="Ekim 20, 2026">20</span></div>
<table id="tblSeanslar"><tbody><tr><td>OLD</td><td>960</td><td><button>Satın Al</button></td></tr></tbody></table>
<script>async function loadDay(){document.querySelector('#txtTarih').value='2026-10-19';
let r=await fetch('/sessions'); await r.text(); setTimeout(()=>{document.querySelector('#tblSeanslar tbody').innerHTML='<tr><td>20:00-21:00</td><td>960</td><td><button disabled>[Mesaj_Dolu]</button></td></tr>';},100);}</script>'''

def test_date_change_waits_for_new_table_not_old_available_row(page):
 page.route('https://fixture.test/**',lambda route: route.fulfill(body='ok' if route.request.url.endswith('/sessions') else HTML,content_type='text/html; charset=utf-8'))
 page.goto('https://fixture.test/')
 probe = SiteProbe(None,page=page)
 assert probe.inspect_day(DAY) == []

def test_disabled_date_does_not_trigger_query(page):
 page.set_content(HTML)
 assert SiteProbe(None,page=page).inspect_day(date(2026,10,20)) == []

def test_failed_refresh_is_error_not_opening(page):
 page.route('https://fixture.test/**',lambda route: route.fulfill(status=500 if route.request.url.endswith('/sessions') else 200,body=HTML,content_type='text/html; charset=utf-8'))
 page.goto('https://fixture.test/')
 with pytest.raises(ProbeError): SiteProbe(None,page=page).inspect_day(DAY)

def test_first_verified_opening_survives_later_date_failure(page):
 from maslak_monitor.config import Settings
 html=HTML.replace('value="2026-10-13"','value="2026-10-19"').replace(
  'class="flatpickr-day flatpickr-disabled" aria-label="Ekim 20, 2026"',
  'class="flatpickr-day" aria-label="Ekim 20, 2026" onclick="fetch(\'/broken\')"')
 html='<select id="cmbUst"><option>Halı Saha</option></select><select id="cmbAlt"><option>Maslak Halı Saha</option></select>'+html
 page.route('https://kampuskart.itu.edu.tr/**',lambda route:route.fulfill(
  status=500 if route.request.url.endswith('/broken') else 200,body=html,content_type='text/html; charset=utf-8'))
 assert SiteProbe(Settings('user','secret'),page=page).check_week(DAY)==[Slot(DAY,'OLD')]

def test_cookie_overlay_dismissed_before_login_link(page):
 from maslak_monitor.config import Settings
 login='''<a href="/User/LoginITU" onclick="event.preventDefault();location.href='/'">GİRİŞ</a><div id="cookie" style="position:fixed;inset:0;background:white;z-index:9999">
 <button id="btn_cookie_ok" onclick="document.querySelector('#cookie').remove()">Close</button></div>'''
 def route_request(route):
  route.fulfill(body=login if route.request.url.endswith('/User/Login') else '<h1>Welcome</h1>',content_type='text/html; charset=utf-8')
 page.route('https://kampuskart.itu.edu.tr/**',route_request)
 page.goto('https://kampuskart.itu.edu.tr/User/Login')
 page.set_default_timeout(500)
 probe=SiteProbe(Settings('user','secret'),page=page)
 probe._login_if_needed()
 assert page.url=='https://kampuskart.itu.edu.tr/'

def test_loading_class_is_not_proof_of_fresh_rows(page):
 html=HTML.replace("let r=await fetch('/sessions'); await r.text(); setTimeout", "document.querySelector('#tblSeanslar').classList.add('loading'); let r=await fetch('/sessions'); await r.text(); setTimeout").replace('},100);','},2000);')
 page.route('https://fixture.test/**',lambda route:route.fulfill(body='ok' if route.request.url.endswith('/sessions') else html,content_type='text/html; charset=utf-8'))
 page.goto('https://fixture.test/')
 assert SiteProbe(None,page=page).inspect_day(DAY)==[]
