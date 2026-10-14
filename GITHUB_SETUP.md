# GitHub Actions kurulumu

Standart Linux runner kullanan açık depolarda bu çalışma ücretsizdir. Bilgisayarınızın açık olması gerekmez. Ücretli runner veya ücretli sunucu kullanılmaz.

## Çalışma zamanı

Europe/Istanbul saatine göre cuma 10.00–pazartesi 10.00 arasında beş dakikada bir planlanır. GitHub işleri geciktirebilir veya atlayabilir; beş dakikada çalışma ve anlık bildirim garantisi yoktur. Pazartesi 10.00 işi geç başlarsa zaman aralığı dışında kaldığından kontrol yapmaz.

Açık depolarda 60 gün depo etkinliği olmazsa zamanlama otomatik kapatılabilir. Actions sayfasından yeniden etkinleştirilmelidir. Başarılı seans bildirimleri şifreli durum dalına kayıt yazar, fakat uzun süre açılış olmaması veya sürekli hata alınması halinde bununla yetinilemez.

## Güvenli yapılandırma

Repository Secrets: `ITU_USERNAME`, `ITU_PASSWORD`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECIPIENTS` (virgülle ayrılmış iki adres), `STATE_ENCRYPTION_KEY` (Fernet anahtarı).

Repository Variables: `PURCHASE_BUTTON_TEXT` ve `PURCHASE_SELECTOR_VERIFIED`. Gerçek satın alınabilir seansın etkin düğmesi görülüp metni doğrulanmadan `PURCHASE_SELECTOR_VERIFIED=true` yapılmaz. Varsayılan `false` güvenlik kontrolü, canlı bildirimi durdurur.

`monitor-state` dalındaki `state.enc`, anahtarla şifrelenmiş SQLite geçmişidir. Alıcılar ve seans kayıtları düz metin yayımlanmaz. Bu dalı veya anahtarı silmeyin; geçmiş kaybolursa uygulama otomatik sıfırlamaz ve hata verir. Yeniden sıfırlamak tekrar bildirimlere neden olabilir.

Gönderim talebi önce GitHub'a kaydedilir. SMTP kabulü sonrası sonuç kaydedilir. Belirsiz sonuç veya yarıda kalan talep tekrar gönderilmez; böyle bir durumda bildirim kaçabilir ve iş başarısız görünür. Kesin ret en fazla üç kez denenir. Aynı haftada kabul edilen alıcıya yeniden bildirim gönderilmez.

## İlk doğrulama

1. Kişisel `.env` dosyası yüklenmeden kod yayımlanır.
2. Secrets eklenir; `monitor-state` dalı ve ilk şifreli boş kayıt yalnızca kurulumda oluşturulur.
3. `test-email` modu iki açıkça TEST etiketli e-posta gönderir.
4. `probe-week` modu (haftanın pazartesi tarihini seçerek) zaman aralığı dışında da yalnızca sayfayı inceler; bildirim göndermez.
5. Etkin satın alma düğmesi doğrulanınca değişkenler kaydedilir. İş cuma penceresinde canlı çalışır.

Actions `workflow_dispatch` modları: `dry-run` (zaman penceresinde kontrol, e-posta yok), `monitor` (canlı kontrol), `test-email`, `probe-week`. Başarısız iş bildirimi için GitHub hesabınızın Actions e-posta bildirim ayarları kullanılabilir.

Resmî belgeler: [GitHub fiyatlandırma](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [zamanlama sınırları](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
