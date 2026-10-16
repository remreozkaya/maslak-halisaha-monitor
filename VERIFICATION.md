# Doğrulama — GitHub takvim sürümü 0.3.0

## 16 Ekim 2026 — beş dakikalık zamanlayıcı düzeltmesi

115 test geçti. GitHub cron ayarı doğru ve etkin olmasına rağmen yaklaşık yedi saatte yalnızca bir planlı iş oluştu. Her kontrolü cron tetiklemesine bağlamak yerine, runner içinde 300 saniyelik zamanlayıcı ve yaklaşık beş saatte bir `workflow_dispatch` ile oturum devri eklendi. Hafta içi zamanlayıcı çalışır ancak İTÜ kontrolü ve bildirim yalnızca cuma 10.00–pazartesi 10.00 aralığındadır. Eski cron yedek kurtarma olarak korundu.

Dağıtılan değişiklik: `9eb5b3007ba105dcbb52460851e824202e3c201f`. Gerçek canlı doğrulama işi `38911017295` başarılı oldu. Kontroller İstanbul saatine göre 16:51:30.423047 ve 16:56:30.423061'de başladı (300.000014 saniye arayla). İkisi de `status=not_open available_count=0`, çıkış kodu 0 döndürdü. 16:56:43'te `successor_queued` kaydı yazıldı; sonraki `38911797506` işi otomatik oluşup çalışmaya başladı. Test e-postası gönderilmedi. Oturum devri, hata sonrası devam, pencere sınırları, cuma başlangıcı ve kuru çalışmada canlı devrin engellenmesi test edildi.

Bu düzenleme aktif runner içindeki beş dakikalık kontrolü cron gecikmesinden ayırır. GitHub/runner/API kesintileri ve başarısız iş kurulumu hâlâ boşluk oluşturabilir; katı gerçek zaman garantisi verilmez.

## Önceki kurulum doğrulaması

99 test geçti. Kapsam: İstanbul zaman aralığı ve hedef hafta, Maslak seçimi, kapalı/görünmeyen günler, seçilebilir günün dolu seanslara rağmen bildirim koşulu olması, SMTP kabul/ret/belirsizlik, alıcı başına kalıcı kayıt, şifreleme, yanıtı kaybolan kayıt, çakışan kayıt, gönderim sonrası kayıt hatası ve tekrar bildirim önleme.

Gmail yerel ve GitHub sunucusu testlerinde iki e-postayı kabul etti. Kullanıcı yerel testin teslim alındığını doğruladı. GitHub'da ilk salt-okunur İTÜ kontrolü başarılı oldu; 19–25 Ekim 2026 haftası henüz kapalıydı. Son takvim modu kontrolü ve GitHub iş anahtarıyla şifreli geçmiş okuma başarılı oldu; pozitif Maslak haftası açılışı henüz gözlenmedi.

Ücretsiz standart GitHub Actions runner kullanılır. Beş dakikada bir planlanan işler gecikebilir veya atlanabilir. 60 günlük depo hareketsizliğinde zamanlama otomatik devre dışı kalabilir. Bu sınırlar kabul edilerek seçildi; kesintisiz/anlık çalışma garantisi yoktur.

Kaynak yayımlanmadan özel yapılandırmadaki hesaplar, alıcı adresleri ve şifreler tarandı. Kişisel `.env`, durum veritabanı ve ekran görüntüleri yayımlanmadı. Açık depoda yalnızca kod ve şifreli durum dosyası bulunur. Anahtar GitHub Secrets ve özel yerel `.env` içinde tutulur.
