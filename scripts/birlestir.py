# Birlestirici - Turnuva Rehberim
# manuel.json + TSF taramasi + yurt disi taramasi -> data/turnuvalar.json (sitenin okudugu tek dosya)
# - Ayni turnuvanin kopyalarini ayiklar (elle girilen kayit her zaman onceliklidir)
# - Her turnuvanin ilk goruldugu gunu tutar -> sitede "Yeni" etiketi ve bildirim
# - Tarihi gecenleri "oynandi" olarak arsive tasir (1 yil saklar)
# - Tarihi degisen turnuvayi isaretler
# - feed.xml (RSS) uretir; TELEGRAM_TOKEN + TELEGRAM_CHAT tanimliysa Telegram'a bildirim atar
import json, os, re, datetime, hashlib
from xml.sax.saxutils import escape

BUGUN = datetime.date.fromisoformat(os.environ["BUGUN"]) if os.environ.get("BUGUN") else datetime.date.today()
BUGUN_S = BUGUN.isoformat()
SITE_URL = os.environ.get("SITE_URL", "")

def oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return varsayilan

def tr_kucuk(s):
    return (s or "").replace("İ", "i").replace("I", "ı").lower().replace(chr(775), "")

DOLGU = {"satranç", "satranc", "turnuvası", "turnuvasi", "turnuva", "chess", "open", "the", "and", "tournament",
         "festival", "international", "uluslararası", "açık", "2026", "2027", "2028"}
def kelimeler(ad):
    return {w for w in re.findall(r"[a-zçğıöşü0-9]+", tr_kucuk(ad)) if len(w) >= 4 and w not in DOLGU}

def benzer(a, b):
    ka, kb = kelimeler(a["name"]), kelimeler(b["name"])
    if not ka or not kb:
        return False
    return len(ka & kb) / len(ka | kb) >= 0.3

def gun(s):
    return datetime.date.fromisoformat(s)

def anahtar(t):
    ad = re.sub(r"[^a-zçğıöşü0-9]+", "", tr_kucuk(t["name"]))[:60]
    return f'{t["c"]}|{t.get("il", "")}|{ad}'

def kimlik(t):
    return hashlib.sha1(f'{anahtar(t)}|{t["start"][:7]}'.encode()).hexdigest()[:12]

def main():
    manuel = oku("data/manuel.json", {}).get("turnuvalar", [])
    tr = oku("data/tr_tarama.json", {})
    yd = oku("data/yd_tarama.json", {})
    onceki_dosya = oku("data/turnuvalar.json", {})
    onceki = {t["id"]: t for t in onceki_dosya.get("turnuvalar", []) if "id" in t}
    ilk_kurulum = onceki_dosya.get("ilk_kurulum") or BUGUN_S

    # 1) Elle girilenler her zaman var
    liste = [dict(t, kaynak="manuel") for t in manuel]

    # 2) Taramalardan gelenler: elle girilmis bir kaydin kopyasiysa alma
    def kopya_mi(t):
        for m in liste:
            if m["c"] != t["c"]:
                continue
            if t["c"] == "TR" and m.get("il") != t.get("il") and t.get("il") != "Türkiye geneli":
                continue
            fark = abs((gun(m["start"]) - gun(t["start"])).days)
            if fark <= 2 and (benzer(m, t) or (m["start"] == t["start"] and m["end"] == t["end"])):
                return True
        return False

    for t in tr.get("turnuvalar", []) + yd.get("turnuvalar", []):
        if not t.get("start") or not t.get("end") or not t.get("name"):
            continue
        if not kopya_mi(t):
            liste.append(t)

    # 3) Onceki kayitlarla eslestir: ilk gorulme, tarih degisikligi
    sonuc = {}
    for t in liste:
        t = dict(t)
        t["id"] = kimlik(t)
        eski = onceki.get(t["id"])
        if not eski:
            # ayni turnuva farkli tarihle daha once var miydi?
            ayni = [o for o in onceki.values() if anahtar(o) == anahtar(t) and o["end"] >= BUGUN_S]
            eski = ayni[0] if ayni else None
        if eski and (eski["start"] != t["start"] or eski["end"] != t["end"]):
            t["tarih_degisti"] = f'{eski["start"]} → {t["start"]}'
        t["ilk_gorulme"] = eski.get("ilk_gorulme", BUGUN_S) if eski else BUGUN_S
        t["son_gorulme"] = BUGUN_S
        if eski and eski.get("tarih_degisti") and "tarih_degisti" not in t:
            t["tarih_degisti"] = eski["tarih_degisti"]
        sonuc[t["id"]] = t

    # 4) Bu calismada kaynaklarda gorunmeyen ama hala gelecekteki eski kayitlari koru
    #    (TSF ana sayfasindan dusen duyuru, turnuva iptal olmadikca gecerlidir).
    #    Arsivdekileri de 1 yil sakla.
    arsiv_siniri = (BUGUN - datetime.timedelta(days=365)).isoformat()
    anahtarlar = {anahtar(t) for t in sonuc.values()}
    for o in onceki.values():
        if o["id"] in sonuc or o["end"] < arsiv_siniri:
            continue
        if o["end"] >= BUGUN_S and anahtar(o) in anahtarlar:
            continue      # ayni turnuvanin guncel (tarihi degismis) hali zaten var
        if o.get("kaynak") == "manuel" and o["end"] >= BUGUN_S:
            continue      # manuel.json'dan silinmis, gercekten kaldirilmis
        sonuc[o["id"]] = o

    # 5) Durum: yaklasan / suruyor / oynandi
    yeni_arsiv = []
    for t in sonuc.values():
        if t["end"] < BUGUN_S:
            if t.get("durum") != "oynandi":
                t["oynandi_tarihi"] = BUGUN_S
                if onceki.get(t["id"], {}).get("durum") in ("yaklasan", "suruyor"):
                    yeni_arsiv.append(t)
            t["durum"] = "oynandi"
        elif t["start"] <= BUGUN_S:
            t["durum"] = "suruyor"
        else:
            t["durum"] = "yaklasan"

    turnuvalar = sorted(sonuc.values(), key=lambda t: (t["start"], t["name"]))
    yeniler = [t for t in turnuvalar if t["ilk_gorulme"] == BUGUN_S and t["id"] not in onceki
               and onceki and t["durum"] != "oynandi"]

    cikti = {
        "guncelleme": datetime.datetime.now().isoformat(timespec="minutes"),
        "ilk_kurulum": ilk_kurulum,
        "kaynaklar": {
            "tsf": {"tarama": tr.get("taranma"), "il_sayisi": sum(1 for r in tr.get("iller", []) if r.get("durum") == "ok")},
            "yurtdisi": {"tarama": yd.get("taranma"), "kaynak": yd.get("kaynak")},
        },
        "iller": [{"il": r["il"], "durum": r["durum"]} for r in tr.get("iller", [])],
        "turnuvalar": turnuvalar,
    }
    with open("data/turnuvalar.json", "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=1)

    rss(turnuvalar)
    telegram(yeniler, yeni_arsiv)
    yak = sum(1 for t in turnuvalar if t["durum"] != "oynandi")
    print(f"{len(turnuvalar)} kayit: {yak} yaklasan/suren, {len(turnuvalar) - yak} arsivde. "
          f"Bu calismada {len(yeniler)} yeni, {len(yeni_arsiv)} arsive tasindi.")

def rss(turnuvalar):
    son = sorted([t for t in turnuvalar if t["durum"] != "oynandi"], key=lambda t: t["ilk_gorulme"], reverse=True)[:60]
    ogeler = "".join(
        f"<item><title>{escape(t['name'])} ({escape(t.get('ulke') or t['c'])}, {t['start']})</title>"
        f"<link>{escape(t.get('url') or SITE_URL)}</link><guid isPermaLink=\"false\">{t['id']}</guid>"
        f"<pubDate>{datetime.date.fromisoformat(t['ilk_gorulme']).strftime('%a, %d %b %Y 06:00:00 +0300')}</pubDate>"
        f"<description>{escape((t.get('city') or t.get('il') or '') + ' · ' + t['start'] + ' – ' + t['end'])}</description></item>"
        for t in son)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           f'<title>Turnuva Rehberim: yeni turnuvalar</title><link>{escape(SITE_URL)}</link>'
           f'<description>Türkiye ve yurt dışındaki yeni satranç turnuvaları</description>{ogeler}</channel></rss>')
    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(xml)

def telegram(yeniler, yeni_arsiv):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT")
    if not token or not chat or not (yeniler or yeni_arsiv):
        return
    import requests
    satir = []
    if yeniler:
        satir.append(f"♟ {len(yeniler)} yeni turnuva eklendi:")
        for t in yeniler[:25]:
            satir.append(f"• {t['start']}  {t.get('ulke') or t['c']}{' / ' + t['il'] if t.get('il') else ''}: {t['name'][:70]}")
        if len(yeniler) > 25:
            satir.append(f"… ve {len(yeniler) - 25} tane daha")
    if yeni_arsiv:
        satir.append(f"\n🏁 {len(yeni_arsiv)} turnuva oynandı, arşive taşındı.")
    if SITE_URL:
        satir.append(SITE_URL)
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": "\n".join(satir)[:4000], "disable_web_page_preview": "true"}, timeout=20)
    except Exception as e:
        print("Telegram gonderilemedi:", e)

if __name__ == "__main__":
    main()
