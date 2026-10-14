Ücretsiz GitHub Actions seçeneği ve çalışma sınırları için [GITHUB_SETUP.md](GITHUB_SETUP.md).

# Güncel sürüm: e-posta (0.2.0)

Kullanıcı sunucu ve bildirim bütçesini 0 olarak belirledi ve e-posta kanalını seçti. Güncel kurulum için **[EMAIL_SETUP.md](EMAIL_SETUP.md)** dosyasını izleyin. `.env.example` artık e-posta kanalını seçer; ücretli SMS yapılandırması kullanılmaz. `--test-email` ve SMTP SSL gönderimi eklendi. Önceki SMS açıklaması uyumluluk referansı olarak aşağıda korunmuştur.

Gönderici/alıcılar özel yerel `.env` dosyasına tanımlandı; SMTP yetkisi ve ücretsiz sunucu hesabı eksik. Canlı otomasyon çalışmıyor. Yerel testler 80 geçti; Yerel Docker imajı oluşturuldu; ağ kapalıyken Chromium, SQLite yazma, root olmayan kullanıcı ve imaja sır dosyası dahil edilmemesi doğrulandı.

---

# Maslak Halı Saha bildirim otomasyonu

Her hafta İstanbul saatine göre cuma 10.00–pazartesi 10.00 arasında Maslak Halı Saha'nın takip eden pazartesi–pazar seanslarını 120 saniyede bir kontrol eder. İlk satın alınabilir seans bulununca iki numaraya birer SMS gönderir. Rezervasyon ve ödeme yapmaz.

**Teslim durumu:** Kod ve yerel testler hazırlanmıştır. Sunucuya kurulmamıştır. SMS hesabı/iki alıcı numarası sağlanmamıştır. İTÜ'ye sunucu IP'sinden giriş ve gerçek SMS teslimi test edilmemiştir. Açık seansın satın alma düğmesi canlı görülmediğinden varsayılan gönderim kapalıdır.

## Çalışma şekli

- Cuma 16 Ekim 2026 10.00–pazartesi 19 Ekim 10.00 penceresi, 19–25 Ekim'i takip eder. Pazartesi sabahı hedef değişmez.
- Gelecek haftanın takvimde etkinleşmesi tek başına bildirim değildir. Seans satırındaki görünür, etkin ve tanınan satın alma düğmesi gerekir.
- Pencere dışında site sorgusu yapılmaz. Son kontrol pazartesi 10.00'a planlanır; işletim sistemi gecikmesi için yalnızca bu kontrolün başlangıcına en çok bir saniye tolerans vardır.
- Başarılı kontroller arasındaki süre 120 saniyedir; tespit gecikmesine sayfa yükleme ve SMS teslim süresi eklenir. Kesinti durumunda süre uzayabilir.
- İlk açılış kalıcı kaydedilir; o hafta site kontrolü durur. Sağlayıcının açıkça reddettiği alıcı için en fazla üç deneme yapılır. Kabul edilen ve sonucu belirsiz alıcı yeniden gönderilmez.
- SQLite dosyası kalıcı Docker biriminde tutulur. Bu birimi silmek bildirim geçmişini siler ve yeniden SMS'e yol açabilir.

## Kurulum için gerekenler

1. Sürekli açık bir Linux sunucusu ve SSH erişimi. Docker Engine ve Compose v2 yüklü olmalı. Başlangıç için 2 GB RAM önerilir; gerçek tarayıcı kullanımı izlenmelidir. Sunucu sağlayıcısı bu paket tarafından seçilmez veya satın alınmaz.
2. Netgsm SMS hesabı: API kullanıcısı ve erişim izni, onaylı gönderici başlığı, kullanılabilir SMS paketi. Resmi açıklama: https://bilgibankasi.netgsm.com.tr/sms/toplu-sms/api-ile-sms
3. Bildirim alacak iki farklı Türkiye cep telefonu numarası.
4. İTÜ kullanıcı adı ve şifresinin sunucuda ortam değişkenlerine tanımlanması.

Gerçek sırları bu README'ye veya kaynak koda yazmayın. Paket bunları içermez. Sunucuyu ve SMS hesabını hazırlamak için sağlayıcının hesap açma/ödeme adımlarını hesabın sahibi tamamlamalıdır.

## Sunucuda adımlar

Paketi açıp `maslak-monitor` dizinine girin:

```sh
cp .env.example .env
chmod 600 .env
nano .env
```

İTÜ bilgilerinizi doldurun. Şifreyi tek tırnak içine alın; şifre tek tırnak içeriyorsa Docker Compose ortam dosyası kurallarına göre kaçış kullanın. `DRY_RUN=true` ve `PURCHASE_SELECTOR_VERIFIED=false` kalsın. SMS bilgileri kuru kontrolde boş kalabilir.

```sh
docker compose build
docker compose run --rm monitor python -m maslak_monitor --probe-week 2026-10-19 --dry-run
```

`--probe-week` manuel, yalnızca okuyan bir teşhis komutudur; tarih pazartesi olmalıdır. Gerçek kurulumda takip etmek istediğiniz haftanın pazartesisini yazın. Bu komut zaman penceresi dışında da çalışır ve SMS göndermez. `available: []` seçilebilir günlerde tanınan açık seans olmadığını gösterir. Hata kodu 1 alınırsa giriş, ek doğrulama veya sayfa yapısı incelenmelidir; hata kapalı hafta diye yorumlanmaz.

```sh
docker compose up -d
docker compose logs --tail 50 monitor
docker compose ps
```

Bu aşamada servis yalnızca kuru kontrol yapar. Arızanın sessiz kalmaması için `docker compose ps` sağlığını veya aşağıdaki sağlık komutunun çıkış kodunu dış bir sunucu izleme hizmetine bağlayın. Sağlık kontrolü tek başına SMS/e-posta göndermez ve Docker `unhealthy` işareti tek başına container'ı yeniden başlatmaz.

## SMS etkinleştirme

`.env` içinde `SMS_RECIPIENTS=0555...,0555...`, `NETGSM_USERCODE`, `NETGSM_PASSWORD`, `NETGSM_HEADER` alanlarını doldurun. Numara biçimleri `5XXXXXXXXX`, `05XXXXXXXXX` veya `+905XXXXXXXXX` kabul edilir.

Bir açık seansı normal tarayıcıda gözleyin. Satın alma düğmesinin **tam görünen metnini** `PURCHASE_BUTTON_TEXT` olarak yazın. Varsayılan `Satın Al` yalnızca bir adaydır; canlı açık seans üzerinde doğrulanmamıştır. Eşleşmeyen etkin düğmede sistem hata verir. Doğrulamadan `PURCHASE_SELECTOR_VERIFIED=true` yapmayın.

Kontrol edilen iki numaraya açıkça etiketlenmiş birer test SMS'i gönderin:

```sh
docker compose stop monitor
docker compose run --rm monitor python -m maslak_monitor --test-sms
```

Bu komut her çalıştırıldığında iki test SMS'i denemesi yapar; sağlayıcınız ücretlendirebilir. Test için canlı seans düğmesi doğrulaması aranmaz ve test, gerçek haftanın bildirim durumunu kaydetmez. Kabul sayısının 2/2 olması sağlayıcının isteği kabul ettiğini gösterir; telefona teslim edildiğini ayrıca doğrulayın.

Giriş, düğme, iki telefona teslim ve sağlık takibi doğrulandıktan sonra `.env` içinde `DRY_RUN=false` ve `PURCHASE_SELECTOR_VERIFIED=true` yapın:

```sh
docker compose up -d --force-recreate
```

Çalışan container `.env` değişikliğini otomatik almaz; yeniden oluşturma gerekir. Alıcıları bir haftanın açılışı kaydedildikten sonra değiştirmeyin; yeni numara o hafta yeni alıcı sayılır.

## İzleme ve bakım

```sh
docker compose exec monitor python -m maslak_monitor --check-health
docker compose logs --tail 100 monitor
docker compose stop monitor
```

Sağlık komutu taze heartbeat ve hatasız durum için 0, arıza/eskimiş heartbeat için 1 döndürür. `health.json` durum, son heartbeat, son başarılı kontrol ve yalnızca hata türünü içerir. Günlüklere şifre, API anahtarı ve alıcı numarası yazılmaz. Başarı durumu değiştiğinde günlük çıkar; açılmamış haftaya her kontrolde mesaj yazılmaz.

Hata durumları:

- `ProbeError` / `AuthRequired`: İTÜ girişi, CAPTCHA/ek doğrulama, site erişimi veya sayfa değişikliği incelenmeli. Sistem bunları aşmaz.
- `SmsRejected`: API yetkisi, başlık ve bakiye kontrol edilmeli. Deneme üst sınırı alıcı/hafta başına üçtür.
- `SmsUnknown`: Sağlayıcının kabul edip etmediği bilinmiyor. Yeni SMS otomatik gönderilmez. Netgsm raporlarından ve `state.db` içindeki varsa `provider_id` ile kontrol edin. Kimlik alınmadan zaman aşımı olduysa API üzerinden kesin sorgulama mümkün olmayabilir; sağlayıcının panelinde saat/alıcı ile inceleyin. Sonucu doğrulamadan veritabanını sıfırlamayın.

İleti raporu manuel incelenir; otomatik teslim raporu sorgulaması bu sürümde bulunmaz. Kabul edilen SMS'in teslim başarısızlığı ikinci otomatik SMS oluşturmaz. Sunucu sağlık bildirim kanalı hesap/kurulum bilgileri sağlandığında ayrıca bağlanmalıdır.

## Yerel geliştirme ve test

```sh
python3 -m venv .venv
.venv/bin/pip install '.[test]'
.venv/bin/python -m playwright install chromium --only-shell
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src
```

Python 3.12 veya üstü gerekir. Yerel doğrulama Python 3.13 ile yapılmıştır. Tarayıcı testleri sahte domain/HTTP yanıtlarını kullanır; İTÜ hesabına girmez ve SMS göndermez. API testleri gerçek Netgsm JSON POST sözleşmesini sahte HTTP taşıyıcısıyla doğrular. Docker imajı ve Python Playwright paketi aynı 1.63.0 sürümündedir.

Resmi kaynaklar:

- Playwright Docker: https://playwright.dev/python/docs/docker
- Netgsm gönderim/yanıt sözleşmesi: https://www.netgsm.com.tr/dokuman/
