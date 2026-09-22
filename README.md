# ♟ Turnuva Rehberim

Türkiye'deki 81 ilin TSF turnuvaları ve yurt dışındaki açık turnuvalar, tek sitede, kendiliğinden güncellenen bir takvimde.

## Nasıl çalışıyor?

GitHub Actions günde 3 kez (TR saatiyle 06:00, 14:00, 20:00) şunları yapar:

1. `scripts/tsf_il_tarayici.py`: 81 ilin TSF sayfasını (ana sayfa, turnuva haberleri, etkinlik takvimi, duyuru detayları) tarar → `data/tr_tarama.json`
2. `scripts/yurtdisi_tarayici.py`: MyChess.events site haritasından sadece yeni ya da değişmiş turnuvaları okur → `data/yd_tarama.json`
3. `scripts/birlestir.py`: Hepsini `data/manuel.json` ile birleştirir, kopyaları ayıklar, yeni turnuvaları işaretler, tarihi geçenleri arşive taşır → `data/turnuvalar.json` ve `feed.xml`
4. Siteyi GitHub Pages'te yeniden yayınlar.

## Elle turnuva eklemek / düzeltmek

`data/manuel.json` dosyasını GitHub'da açıp kalem simgesiyle düzenle ve kaydet. Site birkaç dakika içinde güncellenir. Elle girilen kayıt, taramada bulunan aynı turnuvanın önüne geçer.

## Telegram bildirimi (isteğe bağlı)

1. Telegram'da @BotFather'a `/newbot` yaz, verdiği token'ı al.
2. Botuna bir mesaj at, sonra `https://api.telegram.org/bot<TOKEN>/getUpdates` adresinden `chat.id` değerini bul.
3. GitHub'da repo → Settings → Secrets and variables → Actions → New repository secret:
   `TELEGRAM_TOKEN` ve `TELEGRAM_CHAT`.

Yeni turnuva eklendiğinde ya da turnuvalar arşive taşındığında Telegram'dan mesaj gelir.

## Kaynaklar

TSF il temsilcilikleri (tsf.org.tr) ve MyChess.events. Tarayıcılar robots.txt kurallarına uyar, istekler arasında bekler ve sadece herkese açık duyuruları okur. Kesin bilgi her zaman turnuva yönergesindedir.
