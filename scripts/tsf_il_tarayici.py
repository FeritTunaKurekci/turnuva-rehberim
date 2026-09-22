# TSF 81 il tarayicisi v0.3 - Turnuva Rehberim
# Her ilin TSF sitesinde: ana sayfa + turnuva/etkinlik liste sayfalari + duyuru detay sayfalari.
# Yaklasan turnuvalari turnuvalar_tr.json dosyasina yazar. robots.txt'e uyar.
import json, re, time, datetime, sys, os
from urllib import robotparser
from urllib.parse import urljoin, urlparse, parse_qs, quote
import requests
from bs4 import BeautifulSoup

UA = "TurnuvaRehberim/0.4 (kisisel turnuva takvimi; github.com)"
CIKTI = sys.argv[sys.argv.index("--cikti") + 1] if "--cikti" in sys.argv else "turnuvalar_tr.json"
BEKLE = 1.5          # istekler arasi bekleme (sn)
MAX_LISTE = 5        # il basina en fazla kac liste sayfasi
MAX_DETAY = 18       # il basina en fazla kac duyuru detay sayfasi

ILLER = ("Adana,Adıyaman,Afyonkarahisar,Ağrı,Aksaray,Amasya,Ankara,Antalya,Ardahan,Artvin,Aydın,"
 "Balıkesir,Bartın,Batman,Bayburt,Bilecik,Bingöl,Bitlis,Bolu,Burdur,Bursa,Çanakkale,Çankırı,Çorum,"
 "Denizli,Diyarbakır,Düzce,Edirne,Elazığ,Erzincan,Erzurum,Eskişehir,Gaziantep,Giresun,Gümüşhane,"
 "Hakkari,Hatay,Iğdır,Isparta,İstanbul,İzmir,Kahramanmaraş,Karabük,Karaman,Kars,Kastamonu,Kayseri,"
 "Kilis,Kırıkkale,Kırklareli,Kırşehir,Kocaeli,Konya,Kütahya,Malatya,Manisa,Mardin,Mersin,Muğla,Muş,"
 "Nevşehir,Niğde,Ordu,Osmaniye,Rize,Sakarya,Samsun,Siirt,Sinop,Sivas,Şanlıurfa,Şırnak,Tekirdağ,"
 "Tokat,Trabzon,Tunceli,Uşak,Van,Yalova,Yozgat,Zonguldak").split(",")

ALTERNATIF = {
    "Afyonkarahisar": ["afyon", "afyonkarahisar"],
    "Kahramanmaraş": ["kahramanmaras", "kmaras", "maras"],
    "Şanlıurfa": ["sanliurfa", "urfa"],
    "Mersin": ["mersin", "icel"],
}

def tr_kucuk(s):
    return s.replace("İ", "i").replace("I", "ı").lower().replace(chr(775), "")

def slug(ad):
    t = tr_kucuk(ad)
    for a, b in zip("çğıöşü", "cgiosu"):
        t = t.replace(a, b)
    return t

BUGUN = datetime.date.today()
AYLAR = {"ocak":1,"şubat":2,"subat":2,"mart":3,"nisan":4,"mayıs":5,"mayis":5,"haziran":6,
         "temmuz":7,"ağustos":8,"agustos":8,"eylül":9,"eylul":9,"ekim":10,"kasım":11,"kasim":11,
         "aralık":12,"aralik":12}
AY_DESEN = "|".join(sorted(AYLAR, key=len, reverse=True))
RE_IKI_AY = re.compile(r"(\d{1,2})\s+(" + AY_DESEN + r")\s*(20\d\d)?\s*[-–]\s*(\d{1,2})\s+(" + AY_DESEN + r")\s*(20\d\d)?")
RE_AY = re.compile(r"(\d{1,2})(?:\s*[-–/]\s*(\d{1,2}))?\s+(" + AY_DESEN + r")(?![a-zçğıöşü])\s*(20\d\d)?")
RE_SAYI = re.compile(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?[./](\d{1,2})[./](20\d\d)")
RE_UST = re.compile(r"(\d{4})\s*(?:ve|ile)?\s*(?:üstü|üzeri|uzeri|ustu|\+)")
RE_ARA = re.compile(r"(\d{4})\s*(?:ile|-|–)\s*(\d{4})")
RE_ALT = re.compile(r"(\d{4})\s*(?:ve)?\s*(?:altı|altında|alti|altinda)")
RE_TURNUVA = re.compile(r"turnuva|şenli|kupa|birinciliğ|açık|open|şampiyona", re.I)
RE_LISTE = re.compile(r"turnuva haber|turnuvalar|etkinlik takvim|etkinlik|duyuru|haberler|açık turnuva|ilçe turnuva|faaliyet")

def gun(y, a, g):
    """Yil yoksa: bu yil gecmisse ve 150 gun icinde gelecek yila denk geliyorsa gelecek yil; yoksa None."""
    if y:
        return datetime.date(int(y), a, int(g))
    d = datetime.date(BUGUN.year, a, int(g))
    if d >= BUGUN - datetime.timedelta(days=5):
        return d
    d2 = datetime.date(BUGUN.year + 1, a, int(g))
    return d2 if (d2 - BUGUN).days <= 150 else None

def tarih_adaylari(metin):
    """Metindeki tum tarihleri (bas, bit, konum, yil_var) olarak dondurur."""
    out = []
    for m in RE_IKI_AY.finditer(metin):
        g1, a1, y1, g2, a2, y2 = m.groups()
        try:
            a1n, a2n = AYLAR[a1], AYLAR[a2]
            yil = y2 or y1
            e = gun(yil, a2n, g2)
            if not e: continue
            s = datetime.date(e.year - (1 if a1n > a2n else 0), a1n, int(g1))
            out.append((s, e, m.start(), m.end(), bool(yil)))
        except (KeyError, ValueError):
            pass
    for m in RE_AY.finditer(metin):
        g1, g2, ay, yil = m.groups()
        try:
            s = gun(yil, AYLAR[ay], g1); e = gun(yil, AYLAR[ay], g2 or g1)
            if s and e: out.append((s, e, m.start(), m.end(), bool(yil)))
        except (KeyError, ValueError):
            pass
    for m in RE_SAYI.finditer(metin):
        g1, g2, ay, yil = m.groups()
        try:
            s = datetime.date(int(yil), int(ay), int(g1)); e = datetime.date(int(yil), int(ay), int(g2 or g1))
            out.append((s, e, m.start(), m.end(), True))
        except ValueError:
            pass
    return out

def tarih_bul(metin):
    """Turnuva tarihini secer: 'tarihlerinde/Turnuva Tarihi' yanindakilere oncelik, 'kayit/itibaren' yanindakilere ceza."""
    metin = tr_kucuk(metin)
    en_iyi, en_puan = None, -99
    for s, e, bas, bit, yil_var in tarih_adaylari(metin):
        once, sonra = metin[max(0, bas - 35):bas], metin[bit:bit + 40]
        puan = 0
        if re.search(r"tarih", sonra) or re.search(r"tarih[a-zı]*\s*[:\-]?\s*$", once): puan += 3
        yakin = metin[max(0, bas - 18):bas] + " " + metin[bit:bit + 30]
        if re.search(r"kayıt|kayit|itibaren|son gün|son başvuru|başvuru", yakin): puan -= 3
        if re.search(r"yayın|güncelle|oluştur", once): puan -= 3
        if yil_var: puan += 1
        if e < s or (e - s).days > 20: puan -= 5
        puan -= bas / 5000.0   # esitlikte once gelen kazansin
        if puan > en_puan:
            en_iyi, en_puan = (s, e), puan
    return en_iyi if en_puan > -3 else None

def kategori_bul(metin):
    ham, metin = metin, tr_kucuk(metin)
    kat = set()
    for a, b in RE_ARA.findall(metin):
        lo, hi = sorted((int(a), int(b)))
        if 1000 <= lo <= 2800 and 50 <= hi - lo < 1000 and not (1900 <= lo <= 2100 and 2000 <= hi <= 2100):
            kat.add((lo, hi))
    kat |= {(int(x), None) for x in RE_UST.findall(metin) if 1000 <= int(x) <= 2800 and not 1990 <= int(x) <= 2030}
    kat |= {(None, int(x)) for x in RE_ALT.findall(metin) if 900 < int(x) <= 2800 and not 1990 <= int(x) <= 2030}
    sirali = sorted(kat, key=lambda k: (k[0] if k[0] is not None else -1, k[1] or 9999), reverse=True)
    harf = "ABCDEFGH"
    bolum = [{"n": f"{harf[i]} Kategorisi", "min": lo, "max": hi} for i, (lo, hi) in enumerate(sirali[:8])]
    tur = "ELO" if re.search(r"\bELO\b", ham) else ("UKD" if re.search(r"\bUKD\b", ham) else None)
    return bolum, tur

_robots = {}
def izinli(url):
    host = urlparse(url).netloc
    if host not in _robots:
        rp = robotparser.RobotFileParser(); rp.set_url(f"https://{host}/robots.txt")
        try: rp.read()
        except Exception: rp = None
        _robots[host] = rp
    rp = _robots[host]
    return True if rp is None else rp.can_fetch(UA, url)

def getir(oturum, url):
    if not izinli(url):
        return None
    try:
        r = oturum.get(url, timeout=20)
        time.sleep(BEKLE)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def ayni_site(url, host):
    h = urlparse(url).netloc.replace("www.", "")
    return h == host.replace("www.", "")

def bloklar(soup):
    """(baslik, metin, link) adaylari: basliklar ve 'turnuva' gecen linkler."""
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        baslik = h.get_text(" ", strip=True)
        if not RE_TURNUVA.search(baslik): continue
        govde = []
        for k in h.find_next_siblings(limit=4):
            if k.name in ("h1", "h2", "h3", "h4"): break
            govde.append(k.get_text(" ", strip=True)[:700])
        a = h.find("a")
        yield baslik, baslik + " " + " ".join(govde), (a.get("href") if a else None)
    for a in soup.find_all("a"):
        baslik = a.get_text(" ", strip=True)
        if len(baslik) < 15 or not RE_TURNUVA.search(baslik): continue
        ust = a.find_parent(["li", "tr", "article", "p"])
        metin = ust.get_text(" ", strip=True)[:600] if ust else baslik
        yield baslik, baslik + " " + metin, a.get("href")

def ana_metin(html):
    soup = BeautifulSoup(html, "html.parser")
    for sec in [".item-page", "article", ".blog", "#content", ".content", "main"]:
        el = soup.select_one(sec)
        if el and len(el.get_text(strip=True)) > 80:
            return el.get_text(" ", strip=True)[:5000]
    return soup.body.get_text(" ", strip=True)[:5000] if soup.body else ""

def ics_oku(metin, il):
    out = []
    for ev in metin.split("BEGIN:VEVENT")[1:]:
        def al(k):
            m = re.search(rf"^{k}[^:\n]*:(.+)$", ev, re.M)
            return m.group(1).strip() if m else ""
        try:
            s = datetime.datetime.strptime(al("DTSTART")[:8], "%Y%m%d").date()
            e = datetime.datetime.strptime((al("DTEND") or al("DTSTART"))[:8], "%Y%m%d").date()
        except ValueError:
            continue
        if e > s and len(al("DTEND")) == 8: e -= datetime.timedelta(days=1)  # tum gun etkinlik
        if e < BUGUN or (s - BUGUN).days > 400: continue
        out.append((al("SUMMARY").replace("\\,", ","), s, e, al("DESCRIPTION")[:600]))
    return out

def kayit(il, baslik, s, e, metin, link, kaynak):
    kat, tur = kategori_bul(metin)
    yas = bool(re.search(r"yaş\s*(?:altı|kategori|grubu)|\d+\s*yaş", tr_kucuk(metin)))
    bolum = list(kat)
    if yas: bolum.append({"n": "Yaş kategorileri", "age": True})
    if not bolum: bolum = [{"n": "Genel", "min": None, "max": None}]
    return {"c": "TR", "ulke": "Türkiye", "bayrak": "tr", "il": il, "name": re.sub(r"\s+", " ", baslik)[:160], "start": s.isoformat(), "end": e.isoformat(),
            "status": "a", "reyting_turu": tur, "sections": bolum, "url": link, "kaynak": kaynak,
            "kaynak_metin": re.sub(r"\s+", " ", metin)[:500]}

def il_tara(il, oturum):
    # 1) ilin sitesini bul
    host, ana = None, None
    for s in ALTERNATIF.get(il, [slug(il)]):
        for h in (f"{s}.tsf.org.tr", f"www.{s}.tsf.org.tr"):
            html = getir(oturum, f"https://{h}/")
            if html and "tsf" in html.lower():
                host, ana = h, html; break
        if host: break
    if not host:
        return {"il": il, "durum": "ulasilamadi", "host": None, "sayfa": 0, "turnuvalar": []}
    kok = f"https://{host}/"
    sayfalar = [(kok, ana)]
    # 2) liste sayfalari (Turnuva Haberleri, Etkinlik Takvimi...)
    soup = BeautifulSoup(ana, "html.parser")
    listeler = []
    for a in soup.find_all("a", href=True):
        u = urljoin(kok, a["href"]).split("#")[0]
        if ayni_site(u, host) and RE_LISTE.search(tr_kucuk(a.get_text(" ", strip=True))) and u not in listeler and u.rstrip("/") != kok.rstrip("/"):
            listeler.append(u)
    for u in listeler[:MAX_LISTE]:
        html = getir(oturum, u)
        if html: sayfalar.append((u, html))
    # 3) iframe'ler (takvimler) - Google Takvim ise ICS'ini oku
    turnuvalar, gorulen = [], set()
    for u, html in list(sayfalar):
        for fr in BeautifulSoup(html, "html.parser").find_all("iframe", src=True):
            src = urljoin(u, fr["src"])
            if "calendar.google.com" in src:
                for cid in parse_qs(urlparse(src).query).get("src", []):
                    ics = getir(oturum, f"https://calendar.google.com/calendar/ical/{quote(cid)}/public/basic.ics")
                    for ad, s, e, acik in ics_oku(ics or "", il):
                        if (ad, s) in gorulen: continue
                        gorulen.add((ad, s)); turnuvalar.append(kayit(il, ad, s, e, ad + " " + acik, src, "takvim"))
            elif ".tsf.org.tr" in src or "tsf.org.tr" in urlparse(src).netloc:
                h2 = getir(oturum, src)
                if h2: sayfalar.append((src, h2))
    # 4) adaylari topla, gerekirse detay sayfasina gir
    adaylar, linkler = [], set()
    for u, html in sayfalar:
        for baslik, metin, link in bloklar(BeautifulSoup(html, "html.parser")):
            tam = urljoin(u, link) if link else u
            if tam in linkler and link: continue
            linkler.add(tam)
            adaylar.append((baslik, metin, tam))
    detay = 0
    for baslik, metin, link in adaylar:
        t = tarih_bul(baslik) or tarih_bul(metin)
        if t and t[1] < BUGUN: continue                      # gecmis
        if ayni_site(link, host) and link.rstrip("/") != kok.rstrip("/") and detay < MAX_DETAY:
            html = getir(oturum, link); detay += 1
            if html:
                dm = ana_metin(html)
                t = tarih_bul(baslik) or tarih_bul(dm) or t
                metin = baslik + " " + dm
        if not t or t[1] < BUGUN or (t[0] - BUGUN).days > 400: continue
        anahtar = (tr_kucuk(baslik)[:50], t[0])
        if anahtar in gorulen: continue
        gorulen.add(anahtar)
        turnuvalar.append(kayit(il, baslik, t[0], t[1], metin, link, "site"))
    return {"il": il, "durum": "ok", "host": host, "sayfa": len(sayfalar) + detay, "turnuvalar": turnuvalar}

def ortaklari_ayikla(hepsi):
    """4+ ilde birden gorunen ayni duyuru, sitelerin ortak kenar cubugudur: tek kayit, 'Turkiye geneli'."""
    say = {}
    for t in hepsi:
        k = (re.sub(r"\W+", "", tr_kucuk(t["name"]))[:50], t["start"])
        say.setdefault(k, set()).add(t["il"])
    sonuc, eklenen = [], set()
    for t in hepsi:
        k = (re.sub(r"\W+", "", tr_kucuk(t["name"]))[:50], t["start"])
        if len(say[k]) >= 4:
            if k in eklenen: continue
            eklenen.add(k); t = dict(t, il="Türkiye geneli")
        sonuc.append(t)
    return sonuc

def main():
    oturum = requests.Session()
    oturum.headers["User-Agent"] = UA
    rapor, hepsi = [], []
    def kaydet(son=False):
        veri = ortaklari_ayikla(hepsi) if son else hepsi
        os.makedirs(os.path.dirname(CIKTI) or ".", exist_ok=True)
        with open(CIKTI, "w", encoding="utf-8") as f:
            json.dump({"taranma": datetime.datetime.now().isoformat(timespec="minutes"), "surum": "0.4",
                       "iller": rapor, "turnuvalar": veri}, f, ensure_ascii=False, indent=1)
        return veri
    bas = time.time()
    for no, il in enumerate(ILLER, 1):
        try:
            s = il_tara(il, oturum)
        except Exception as e:
            s = {"il": il, "durum": "hata", "host": None, "sayfa": 0, "turnuvalar": []}
            print(f"   ! {il}: {type(e).__name__}: {e}")
        rapor.append({"il": il, "durum": s["durum"], "host": s["host"], "adet": len(s["turnuvalar"])})
        hepsi += s["turnuvalar"]
        dk = (time.time() - bas) / 60
        print(f"{no:2}/81  {il:15} {s['durum']:11} {s['sayfa']:3} sayfa  {len(s['turnuvalar']):3} turnuva   ({dk:.0f}. dk)")
        kaydet()
    son = kaydet(son=True)
    genel = sum(1 for t in son if t["il"] == "Türkiye geneli")
    print(f"\nBITTI: {len(son)} yaklasan turnuva ({genel} tanesi birden cok ilde gorunen ortak duyuru) -> {CIKTI}")
    print("Tarih araligi:", BUGUN.isoformat(), "->", (BUGUN + datetime.timedelta(days=400)).isoformat())
    print("Ulasilamayan iller:", ", ".join(r["il"] for r in rapor if r["durum"] != "ok") or "yok")

if __name__ == "__main__":
    main()
