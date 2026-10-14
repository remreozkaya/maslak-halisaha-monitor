# Doğrulama — GitHub takvim sürümü 0.3.0

99 test geçti. Kapsam: İstanbul zaman aralığı ve hedef hafta, Maslak seçimi, kapalı/görünmeyen günler, seçilebilir günün dolu seanslara rağmen bildirim koşulu olması, SMTP kabul/ret/belirsizlik, alıcı başına kalıcı kayıt, şifreleme, yanıtı kaybolan kayıt, çakışan kayıt, gönderim sonrası kayıt hatası ve tekrar bildirim önleme.

Gmail yerel ve GitHub sunucusu testlerinde iki e-postayı kabul etti. Kullanıcı yerel testin teslim alındığını doğruladı. GitHub'da ilk salt-okunur İTÜ kontrolü başarılı oldu; 19–25 Ekim 2026 haftası henüz kapalıydı. Son takvim modu kontrolü ve GitHub iş anahtarıyla şifreli geçmiş okuma başarılı oldu; pozitif Maslak haftası açılışı henüz gözlenmedi.

Ücretsiz standart GitHub Actions runner kullanılır. Beş dakikada bir planlanan işler gecikebilir veya atlanabilir. 60 günlük depo hareketsizliğinde zamanlama otomatik devre dışı kalabilir. Bu sınırlar kabul edilerek seçildi; kesintisiz/anlık çalışma garantisi yoktur.

Kaynak yayımlanmadan özel yapılandırmadaki hesaplar, alıcı adresleri ve şifreler tarandı. Kişisel `.env`, durum veritabanı ve ekran görüntüleri yayımlanmadı. Açık depoda yalnızca kod ve şifreli durum dosyası bulunur. Anahtar GitHub Secrets ve özel yerel `.env` içinde tutulur.
