# GitHub Actions kurulumu

Bildirim koşulu: Maslak takviminde hedef haftanın en az bir günü seçilebilir hale geldiğinde e-posta gönderilir. Boş seans veya etkin satın alma düğmesi aranmaz. Bu, kullanıcının son talebidir.

Standart Linux runner kullanan açık depolarda bu çalışma ücretsizdir. Bilgisayarınızın açık olması gerekmez. Ücretli runner veya ücretli sunucu kullanılmaz.

## Çalışma zamanı

Europe/Istanbul saatine göre cuma 10.00–pazartesi 10.00 arasında aktif runner içinde 300 saniyede bir kontrol yapılır. Her oturum en fazla 61 zamanlayıcı turu (yaklaşık beş saat) çalışır; bitmeden `workflow_dispatch` ile sıradaki oturumu başlatır. Aynı anda yalnızca bir canlı oturum çalışır. Site kontrolü en fazla 240 saniye sürer; zaman aşımı sonraki turu durdurmaz. Kontrol süresi beş dakikalık aralığa eklenmez.

Zamanlayıcı hafta içi de oturum devrini sürdürür, ancak izin verilen cuma–pazartesi aralığı dışında İTÜ sitesine girmez ve e-posta göndermez. Böylece sonraki cuma başlangıcı için yeni bir cron tetiklemesi gerekmez. Mevcut beş dakikalık cron yalnızca ilk başlatma/yedek kurtarma içindir; her kontrol için cron beklenmez.

GitHub kesintisi, runner kapanması veya oturum devrinin gecikmesi yine boşluk oluşturabilir; katı gerçek zaman garantisi yoktur. Ancak cron tetiklemelerinin saatlerce gelmemesi aktif oturumdaki beş dakikalık kontrolleri durdurmaz. `check_started_at`, `check_finished_at` ve `successor_queued` kayıtları gerçek kontrol/devretme zamanlarını gösterir. Workflow için `contents: write` şifreli geçmişi, `actions: write` ise sonraki oturumu başlatmayı sağlar.

Açık depolarda 60 gün depo etkinliği olmazsa zamanlama otomatik kapatılabilir. Actions sayfasından yeniden etkinleştirilmelidir. Başarılı seans bildirimleri şifreli durum dalına kayıt yazar, fakat uzun süre açılış olmaması veya sürekli hata alınması halinde bununla yetinilemez.

## Güvenli yapılandırma

Repository Secrets: `ITU_USERNAME`, `ITU_PASSWORD`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECIPIENTS` (virgülle ayrılmış iki veya üç adres), `STATE_ENCRYPTION_KEY` (Fernet anahtarı).

Workflow `AVAILABILITY_MODE=calendar` kullanır. Takvim gününün `flatpickr-day` olması, görünür olması ve `flatpickr-disabled` olmaması aranır. Geçerli giriş ve Maslak seçimi her kontrolde yapılır. `PURCHASE_SELECTOR_VERIFIED` ayarı yalnızca ayrı `purchase` modunda gereklidir; satın alma modu etkinleştirilmedi.

`monitor-state` dalındaki `state.enc`, anahtarla şifrelenmiş SQLite geçmişidir. Alıcılar ve seans kayıtları düz metin yayımlanmaz. Bu dalı veya anahtarı silmeyin; geçmiş kaybolursa uygulama otomatik sıfırlamaz ve hata verir. Yeniden sıfırlamak tekrar bildirimlere neden olabilir.

Gönderim talebi önce GitHub'a kaydedilir. SMTP kabulü sonrası sonuç kaydedilir. Belirsiz sonuç veya yarıda kalan talep tekrar gönderilmez; böyle bir durumda bildirim kaçabilir ve iş başarısız görünür. Kesin ret en fazla üç kez denenir. Aynı haftada kabul edilen alıcıya yeniden bildirim gönderilmez.

## İlk doğrulama

1. Kişisel `.env` dosyası yüklenmeden kod yayımlanır.
2. Secrets eklenir; `monitor-state` dalı ve ilk şifreli boş kayıt yalnızca kurulumda oluşturulur.
3. `test-email` modu her alıcıya açıkça TEST etiketli e-posta gönderir.
4. `probe-week` modu (haftanın pazartesi tarihini seçerek) zaman aralığı dışında da yalnızca sayfayı inceler; bildirim göndermez.
5. Takvim modu cuma penceresinde canlı çalışır; aynı hafta için alıcı başına bir bildirim gönderilir.

Actions `workflow_dispatch` modları: `dry-run` (zaman penceresinde kontrol, e-posta yok), `monitor` (canlı kontrol), `test-email`, `probe-week`. Başarısız iş bildirimi için GitHub hesabınızın Actions e-posta bildirim ayarları kullanılabilir.

`monitor` artık sürekli oturum zincirini başlatır. `checks` girdisi 1–61 arasında oturum uzunluğunu sınırlar; normal değer 61'dir. Devredilen oturumlar normal 61 tur kullanır. Salt okunur tanılama işleri canlı oturumun kilidini beklemez. Otomasyonu durdurmak için workflow'u devre dışı bırakın ve çalışan canlı işi iptal edin; yalnızca işi iptal etmek cron'un yeniden başlatmasını engellemez.

Resmî belgeler: [GitHub fiyatlandırma](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [zamanlama sınırları](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
