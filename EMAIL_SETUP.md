# Ücretsiz e-posta sürümü — kalan kurulum

Sunucu ve bildirim bütçesi 0 olarak belirlenmiştir. Bu sürüm SMS yerine e-posta kullanır. Mevcut Gmail hesabından düşük sayıdaki haftalık bildirimler gönderilecek; ayrıca ücretli e-posta paketi satın alınmaz.

Gönderici ve iki alıcı özel `.env` dosyasına tanımlandı. Gerçek gönderim kapalıdır. SMTP parolası eksiktir. `.env` ZIP'e, Docker imajına ve Git'e dahil edilmez.

## 1. Gmail gönderim yetkisi

Gönderici hesabı: kullanıcının seçtiği Gmail hesabı; tam adres özel `.env` içindedir.

Google hesabınızda iki adımlı doğrulama açık olmalıdır. Şu sayfada yalnızca bu otomasyon için uygulama parolası oluşturun:

https://myaccount.google.com/apppasswords

Uygulama parolasını sohbet mesajına göndermeyin. Yerel `outputs/maslak-monitor/.env` dosyasındaki `SMTP_PASSWORD` alanına girin. Bu, normal Google hesap parolanız değildir. Uygulama parolası seçeneği hesabınızda yoksa OAuth ile giriş gerekecektir; mevcut SMTP sürümü OAuth akışını içermez.

Hesap parolası, yeni uygulama parolası oluşturma ve ek doğrulama adımlarını hesabın sahibi tamamlamalıdır. Otomasyon yalnızca gönderim yapar; gelen kutusunu okumaz. Ancak Gmail uygulama parolası sadece iki alıcıya kısıtlanan bir izin değildir; Gmail tarafından tanımlanan hesap erişimi sağlar.

Resmi açıklama: https://support.google.com/accounts/answer/185833

## 2. Ücretsiz sunucu hesabı

Oracle Cloud Always Free kayıt bağlantısı:

https://signup.cloud.oracle.com/

Oracle hesap açarken kimlik/iletişim ve banka kartı doğrulaması ister. Geçici kart provizyonu uygulanabilir; Oracle bunun gerçek bir ücret olmadığını belirtir. Hesap oluşturma ve sözleşme/kart doğrulamasını hesabın sahibi tamamlamalıdır. Bu çalışma hiçbir abonelik veya kaynak satın almamıştır.

Resmi koşullar: https://www.oracle.com/cloud/free/faq/

Hesap açıldıktan sonra yalnızca Always Free uygunluğu açıkça gösterilen kaynaklar kullanılacak. 30 günlük deneme kredisine bağlı ücretli kaynak veya ücretli hesaba yükseltme yapılmayacak. Hedef: Ubuntu Always Free A1 VM, 1 OCPU/2 GB RAM, 50 GB önyükleme diski; hesabın tüm mevcut kaynakları birlikte ücretsiz kotada kalmalı.

Ücretsiz VM kapasitesi tükenmiş olabilir. Oracle düşük kullanımda VM'yi geri alabilir; bu otomasyon sürekli çalışacağı garantisiyle sunulamaz. SSH erişimi ve anahtar yerel olarak ayarlandıktan sonra paket sunucuya aktarılabilir. Kalıcı SQLite birimi korunmalıdır; silinmesi aynı hafta tekrar bildirim göndermeye yol açabilir.

Resmi kaynak: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

## Sunucu erişimi hazır olduğunda yapılacaklar

1. Paket aktarılır; sırlar yalnızca özel `.env` içinde tutulur.
2. Docker kurulumu/imajı ve sunucudan İTÜ girişi doğrulanır.
3. `docker compose run --rm monitor python -m maslak_monitor --probe-week 2026-10-19 --dry-run` ile okumaya dayalı kontrol yapılır. Gerçek kurulumda takip edilecek haftanın pazartesisi kullanılır.
4. Açık seans düğmesinin görünen metni normal UI üzerinden doğrulanır. Kapalı tarihleri zorla açma, seans satın alma veya ödeme yapılmaz.
5. Her iki alıcıya `--test-email` komutuyla birer açıkça etiketlenmiş test e-postası gönderilir. SMTP kabulü teslim garantisi değildir; iki gelen kutusunda/spam klasöründe teslim doğrulanır.
6. Gerçek gönderim ve sağlık izlemesi etkinleştirilir. İlk açılışta iki ayrı ileti gönderilir; bir alıcının hatası diğerinin kabul edilen iletisini yeniden göndertmez.

## Komutlar

```sh
docker compose build
docker compose run --rm monitor python -m maslak_monitor --test-email
docker compose up -d --force-recreate
docker compose exec monitor python -m maslak_monitor --check-health
```

`--test-email` komutu her çalıştırıldığında iki ayrı test ileti denemesi yapar; gerçek haftanın bildirim kaydını değiştirmez. Varsayılan `DRY_RUN=true` normal izleyicinin e-posta göndermesini engeller. Test komutu açıkça gönderim yapmak içindir ve kendi SMTP yetkisini gerektirir.

Zamanlama: Europe/Istanbul, cuma 10.00–pazartesi 10.00, 120 saniye aralık. Son kontrolün işletim sistemi toleransı en çok bir saniyedir. SMTP bağlantısı aktarım sırasında koparsa sonuç belirsiz sayılır ve tekrar ileti gönderilmez; bu durum elle incelenir.
