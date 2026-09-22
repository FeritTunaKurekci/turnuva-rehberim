# FIDE reyting listesi -> Turkiye oyunculari (data/fide/tur_<harf>.json)
# FIDE listesi ayda bir guncellenir; bu betik 6 gunde bir indirir (FIDE_ZORLA=1 ile her zaman).
# Kaynak: https://ratings.fide.com/download_lists.phtml (birlesik STD/RPD/BLZ TXT listesi)
import io, os, re, json, zipfile, datetime, unicodedata
from urllib import robotparser
import requests

URL = "https://ratings.fide.com/download/players_list.zip"
UA = "TurnuvaRehberim/0.4 (kisisel turnuva takvimi; github.com)"
KLASOR = "data/fide"
FED = os.environ.get("FIDE_FED", "TUR")
BUGUN = datetime.date.today()

KOLONLAR = ["ID Number", "Name", "Fed", "Sex", "Tit", "WTit", "OTit", "FOA",
            "SRtng", "SGm", "SK", "RRtng", "RGm", "Rk", "BRtng", "BGm", "BK", "B-day", "Flag"]

def katla(s):
    s = (s or "").replace("İ", "i").replace("I", "ı").lower()
    for a, b in zip("çğıöşü", "cgiosu"):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

def gerekli_mi():
    if os.environ.get("FIDE_ZORLA"):
        return True
    try:
        meta = json.load(open(f"{KLASOR}/meta.json", encoding="utf-8"))
        return (BUGUN - datetime.date.fromisoformat(meta["indirme"])).days >= 6
    except (OSError, ValueError, KeyError):
        return True

def kolon_baslari(baslik):
    konum, bas = 0, []
    for ad in KOLONLAR:
        i = baslik.find(ad, konum)
        if i < 0:
            raise ValueError(f"Baslikta '{ad}' bulunamadi: {baslik[:120]}")
        bas.append(i); konum = i + len(ad)
    return bas

def sayi(s):
    s = s.strip()
    return int(s) if s.isdigit() else 0

def satir_coz(satir, bas):
    alan = {}
    for k, ad in enumerate(KOLONLAR):
        son = bas[k + 1] if k + 1 < len(bas) else len(satir)
        alan[ad] = satir[bas[k]:son].strip()
    return alan

def main():
    if not gerekli_mi():
        print("FIDE listesi guncel (6 gunden yeni), indirme atlandi."); return
    rp = robotparser.RobotFileParser(); rp.set_url("https://ratings.fide.com/robots.txt")
    try:
        rp.read()
        if not rp.can_fetch(UA, URL):
            print("robots.txt FIDE listesinin indirilmesine izin vermiyor, atlandi."); return
    except Exception:
        pass
    print("FIDE listesi indiriliyor…")
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=180)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    uye = next(n for n in z.namelist() if n.lower().endswith(".txt"))
    ham = z.read(uye)
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError:
        metin = ham.decode("latin-1")
    satirlar = metin.splitlines()
    bas = kolon_baslari(satirlar[0])
    parca = {}
    adet = 0
    for s in satirlar[1:]:
        if len(s) < bas[3]:
            continue
        a = satir_coz(s, bas)
        if a["Fed"] != FED:
            continue
        std, rpd, blz = sayi(a["SRtng"]), sayi(a["RRtng"]), sayi(a["BRtng"])
        if not (std or rpd or blz):
            continue
        ad = a["Name"]
        soyad = katla(ad.split(",")[0]).strip()
        harf = soyad[:1] if soyad[:1].isalpha() else "_"
        kayit = [sayi(a["ID Number"]), ad, a["Tit"] or a["WTit"], std, rpd, blz, sayi(a["B-day"]), a["Sex"], sayi(a["SK"])]
        parca.setdefault(harf, []).append(kayit)
        adet += 1
    if adet < 500:
        raise SystemExit(f"Beklenenden az oyuncu ({adet}); dosya bicimi degismis olabilir, eski veri korunuyor.")
    os.makedirs(KLASOR, exist_ok=True)
    for f in os.listdir(KLASOR):
        if f.startswith("tur_") and f.endswith(".json"):
            os.remove(os.path.join(KLASOR, f))
    for harf, liste in parca.items():
        liste.sort(key=lambda k: -max(k[3], k[4], k[5]))
        with open(f"{KLASOR}/tur_{harf}.json", "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, separators=(",", ":"))
    tarih = datetime.date(*z.getinfo(uye).date_time[:3]).isoformat()
    json.dump({"indirme": BUGUN.isoformat(), "liste_tarihi": tarih, "federasyon": FED, "adet": adet},
              open(f"{KLASOR}/meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{adet} {FED} oyuncusu {len(parca)} dosyaya yazildi (liste tarihi {tarih}).")

if __name__ == "__main__":
    main()
