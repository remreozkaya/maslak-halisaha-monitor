# Güncel doğrulama — e-posta 0.2.0

- Tam test çalıştırması: **80 passed in 5.93s**, çıkış kodu 0.
- SMTP SSL kabul, açık ret, bağlantı kaybı, kimlik doğrulama hatası ve bağlantı kapatma hataları test edildi.
- `--test-email` iki ayrı alıcıya gönderim yapıyor ve siteyi sorgulamıyor: sahte SMTP bağlantısıyla doğrulandı.
- Python 0.2.0 wheel oluşturma, tüm kaynakların sözdizimi ve CLI yardım çıktısı: başarılı.
- Docker Compose yapılandırması: başarılı.
- Yerel Docker imajı derlemesi: sonraki denemede başarılı (0.2.0, Linux ARM64/Python3.12). Ağ kapalı çalışma testi geçti: Chromium çalışıyor, SQLite yazılabilir, kullanıcı root değil ve /app/.env imajda yok.
- Canlı Gmail gönderimi: SMTP uygulama parolası olmadığı için yapılmadı.
- Sunucu: Oracle Cloud hesabı olmadığı için açılmadı; ücretli hizmet oluşturulmadı.
- Kullanıcının tercihleri: sunucu 0, bildirim 0 bütçe; SMS yerine e-posta.
- Gerçek hesap bilgileri yalnızca özel `.env` içindedir; örnek dosya, ZIP ve Docker bağlamı bunları içermez.

SMTP kabulü e-postanın gelen kutusuna teslim edildiğini kanıtlamaz. Yeni bildirim kanalı da belirsiz gönderimi tekrar denemez. Bağımsız incelemede bulunan SMTP MAIL FROM ret sınıflandırması başarısız regresyon testiyle doğrulanıp düzeltildi; 80 testin tamamı geçti. Canlı seans düğmesi, sunucudan giriş, e-posta teslimi ve sağlık takibi etkinleştirme öncesi doğrulanmalıdır.

Aşağıdaki kayıt önceki SMS sürümünün doğrulama geçmişidir.

---

# Doğrulama kaydı — 13 Ekim 2026

Kod sürümü: 0.1.0. Python 3.13.7 ile test edildi; paket Python >=3.12 ister.

- Tam test çalıştırması: **63 passed in 5.93s**, çıkış kodu 0.
- Python wheel oluşturma ve sanal ortama kurulum: başarılı.
- `compileall -q src`: başarılı.
- Komut satırı `--help`: başarılı.
- `MONITOR_ENV_FILE=.env.example docker compose config --quiet`: başarılı.
- Docker imajı oluşturma/başlatma: yapılmadı; yerel Docker daemon çalışmıyor.
- Sunucu kurulumu: yapılmadı; sunucu erişimi sağlanmadı.
- Canlı SMS kabulü/teslimi: yapılmadı; SMS hesabı ve iki alıcı numarası sağlanmadı.
- İlk incelemede İTÜ hesabına normal tarayıcıyla giriş ve Maslak Halı Saha seçimi başarılıydı. 19–25 Ekim takvim günleri devre dışıydı. Bu, bağımsız kodun sunucudan giriş yapabileceğini kanıtlamaz.

## Test kapsamı

13 zamanlama testi; 8 yapılandırma testi; 14 seans/tarih/giriş testi; 4 kalıcı durum testi; 14 SMS protokol/sonuç testi; 10 servis/sağlık/kilit testi.

Yerel Chromium örnekleri, geciken tablo yenilenmesini, dolu/satın alınamaz seansları, çerez penceresini, ilk açık günün ardından diğer günün hata vermesini kapsar. SMS istekleri gerçek hizmete gönderilmeden sahte HTTP taşıyıcısıyla test edilir. Test fixture'larında eşleşmeyen ağ istekleri engellenir.

Bağımsız incelemede üç önemli hata bulundu: çerez penceresinin girişe engel olması, eski tablonun yeni tarih için kabul edilmesi ve sonraki gün hatasının ilk açılışı kaybettirmesi. Üçü de önce başarısız regresyon testiyle yeniden üretildi, sonra düzeltildi. Son tam test çalıştırması yeşildir. Ertelenmiş küçük inceleme bulgusu yoktur.

## Uygulama kararları ve etkileri

1. Git deposu olmadığı ve sistem Git'i Xcode lisansı nedeniyle çalışmadığı için Git commit/geçmişi oluşturulmadı. Yerel ilerleme kaydı tutuldu; bunun maliyeti Git tabanlı değişiklik geçmişinin olmamasıdır.
2. Son pazartesi 10.00 kontrolü için en çok bir saniye işletim sistemi zamanlama toleransı vardır. Diğer pencere dışı kontroller yapılmaz; son sorgu en çok bir saniye geç başlayabilir.
3. SMS teslim raporu/sonucu belirsiz gönderimlerin uzlaştırılması manuel yapılır. Sağlayıcının gönderim kimliği alınmışsa saklanır; bilinmeyen sonuç tekrar gönderilmez. Bunun maliyeti belirsiz/başarısız teslimin operatörce incelenmesidir.
4. Yeni günün verisini doğrulamak için eski seans satırı düğümlerinin değişmesi gerekir. Site satırları yerinde güncellemeye geçerse kontrol hata verir; uyarlama yapılana kadar tespit kaçabilir. Bu seçim eski veriden yanlış SMS gönderilmesini önler.
5. Bağımsız inceleme canlı düğme yapısı/giriş, sağlayıcı teslimi, sunucu dağıtımı ve Docker çalıştırmasını değerlendirmedi. Bunlar doğrulanmamış kurulum şartları olarak korunur; canlı ortam uyarlaması gerekebilir.

Sırlar kaynak koda eklenmedi. Varsayılan `DRY_RUN=true`; satın alma düğmesi doğrulanmadan canlı gönderim etkinleşmez. Sürekli sağlık bildirim kanalının kurulması dağıtım aşamasında tamamlanmalıdır.
