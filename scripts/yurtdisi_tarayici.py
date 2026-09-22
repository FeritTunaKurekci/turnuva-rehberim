# Yurt disi turnuva tarayicisi - Turnuva Rehberim
# Kaynak: mychess.events (dunya genelindeki acik turnuvalar).
# Site haritasindaki (sitemap) "son degisiklik" tarihine bakar; sadece YENI ya da DEGISMIS
# turnuva sayfalarini okur. Boylece siteye yuk bindirmez. robots.txt'e uyar.
import json, re, time, datetime, os, sys
import xml.etree.ElementTree as ET
from urllib import robotparser
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

UA = "TurnuvaRehberim/0.4 (kisisel turnuva takvimi; github.com)"
KOK = "https://mychess.events"
CIKTI = "data/yd_tarama.json"
BEKLE = 2.0
MAX_SAYFA = int(os.environ.get("YD_MAX_SAYFA", "250"))   # bir calismada en fazla kac turnuva sayfasi
BUGUN = datetime.date.today()

# Ingilizce ulke adi -> (kod, Turkce ad, flagcdn bayrak kodu)
ULKE = {
 "spain": ("ES", "İspanya", "es"), "sweden": ("SE", "İsveç", "se"), "england": ("EN", "İngiltere", "gb-eng"),
 "united kingdom": ("EN", "İngiltere", "gb-eng"), "uk": ("EN", "İngiltere", "gb-eng"), "scotland": ("SCT", "İskoçya", "gb-sct"),
 "wales": ("WLS", "Galler", "gb-wls"), "germany": ("DE", "Almanya", "de"), "italy": ("IT", "İtalya", "it"),
 "netherlands": ("NL", "Hollanda", "nl"), "the netherlands": ("NL", "Hollanda", "nl"), "czech republic": ("CZ", "Çekya", "cz"),
 "czechia": ("CZ", "Çekya", "cz"), "iceland": ("IS", "İzlanda", "is"), "switzerland": ("CH", "İsviçre", "ch"),
 "georgia": ("GE", "Gürcistan", "ge"), "greece": ("GR", "Yunanistan", "gr"), "france": ("FR", "Fransa", "fr"),
 "portugal": ("PT", "Portekiz", "pt"), "austria": ("AT", "Avusturya", "at"), "hungary": ("HU", "Macaristan", "hu"),
 "poland": ("PL", "Polonya", "pl"), "serbia": ("RS", "Sırbistan", "rs"), "croatia": ("HR", "Hırvatistan", "hr"),
 "slovenia": ("SI", "Slovenya", "si"), "bosnia and herzegovina": ("BA", "Bosna-Hersek", "ba"),
 "montenegro": ("ME", "Karadağ", "me"), "north macedonia": ("MK", "Kuzey Makedonya", "mk"), "albania": ("AL", "Arnavutluk", "al"),
 "bulgaria": ("BG", "Bulgaristan", "bg"), "romania": ("RO", "Romanya", "ro"), "moldova": ("MD", "Moldova", "md"),
 "ukraine": ("UA", "Ukrayna", "ua"), "slovakia": ("SK", "Slovakya", "sk"), "denmark": ("DK", "Danimarka", "dk"),
 "norway": ("NO", "Norveç", "no"), "finland": ("FI", "Finlandiya", "fi"), "estonia": ("EE", "Estonya", "ee"),
 "latvia": ("LV", "Letonya", "lv"), "lithuania": ("LT", "Litvanya", "lt"), "belgium": ("BE", "Belçika", "be"),
 "luxembourg": ("LU", "Lüksemburg", "lu"), "ireland": ("IE", "İrlanda", "ie"), "malta": ("MT", "Malta", "mt"),
 "cyprus": ("CY", "Kıbrıs", "cy"), "armenia": ("AM", "Ermenistan", "am"), "azerbaijan": ("AZ", "Azerbaycan", "az"),
 "kazakhstan": ("KZ", "Kazakistan", "kz"), "uzbekistan": ("UZ", "Özbekistan", "uz"), "united arab emirates": ("AE", "BAE", "ae"),
 "uae": ("AE", "BAE", "ae"), "qatar": ("QA", "Katar", "qa"), "israel": ("IL", "İsrail", "il"), "egypt": ("EG", "Mısır", "eg"),
 "morocco": ("MA", "Fas", "ma"), "tunisia": ("TN", "Tunus", "tn"), "usa": ("US", "ABD", "us"), "united states": ("US", "ABD", "us"),
 "canada": ("CA", "Kanada", "ca"), "mexico": ("MX", "Meksika", "mx"), "brazil": ("BR", "Brezilya", "br"),
 "argentina": ("AR", "Arjantin", "ar"), "india": ("IN", "Hindistan", "in"), "thailand": ("TH", "Tayland", "th"),
 "singapore": ("SG", "Singapur", "sg"), "malaysia": ("MY", "Malezya", "my"), "indonesia": ("ID", "Endonezya", "id"),
 "philippines": ("PH", "Filipinler", "ph"), "australia": ("AU", "Avustralya", "au"), "new zealand": ("NZ", "Yeni Zelanda", "nz"),
 "japan": ("JP", "Japonya", "jp"), "china": ("CN", "Çin", "cn"), "south africa": ("ZA", "Güney Afrika", "za"),
 "andorra": ("AD", "Andorra", "ad"), "monaco": ("MC", "Monako", "mc"), "liechtenstein": ("LI", "Lihtenştayn", "li"),
 "san marino": ("SM", "San Marino", "sm"), "gibraltar": ("GI", "Cebelitarık", "gi"), "isle of man": ("IM", "Man Adası", "im"),
 "kosovo": ("XK", "Kosova", "xk"), "belarus": ("BY", "Belarus", "by"), "mongolia": ("MN", "Moğolistan", "mn"),
 "vietnam": ("VN", "Vietnam", "vn"), "sri lanka": ("LK", "Sri Lanka", "lk"), "nepal": ("NP", "Nepal", "np"),
 "chile": ("CL", "Şili", "cl"), "colombia": ("CO", "Kolombiya", "co"), "peru": ("PE", "Peru", "pe"), "cuba": ("CU", "Küba", "cu"),
 "turkey": ("TR", "Türkiye", "tr"), "türkiye": ("TR", "Türkiye", "tr"),
}

RE_DMY = re.compile(r"(\d{2})-(\d{2})-(\d{4})(?:\s*[–-]\s*(\d{2})-(\d{2})-(\d{4}))?")

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
        print("  robots.txt izin vermiyor:", url); return None
    try:
        r = oturum.get(url, timeout=25); time.sleep(BEKLE)
    except requests.RequestException as e:
        print("  hata:", url, e); return None
    return r.text if r.status_code == 200 else None

def site_haritasi(oturum):
    """(url, lastmod) listesi. Once Yoast/RankMath, sonra WordPress'in kendi haritasi."""
    for index in (f"{KOK}/sitemap_index.xml", f"{KOK}/wp-sitemap.xml", f"{KOK}/sitemap.xml"):
        xml = getir(oturum, index)
        if not xml or "<" not in xml: continue
        try: kok = ET.fromstring(xml.encode("utf-8"))
        except ET.ParseError: continue
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        alt = [l.text for l in kok.findall(".//s:sitemap/s:loc", ns)]
        haritalar = [u for u in alt if "event" in u] or ([index] if kok.findall(".//s:url", ns) else [])
        sonuc = []
        for h in haritalar:
            x = xml if h == index else getir(oturum, h)
            if not x: continue
            try: k = ET.fromstring(x.encode("utf-8"))
            except ET.ParseError: continue
            for u in k.findall(".//s:url", ns):
                loc = u.findtext("s:loc", default="", namespaces=ns)
                if "/event/" in loc:
                    sonuc.append((loc, u.findtext("s:lastmod", default="", namespaces=ns)))
        if sonuc:
            return sonuc
    return []

def liste_sayfasi(oturum):
    """Site haritasi yoksa yedek: 'Upcoming tournaments' sayfasindaki linkler."""
    html = getir(oturum, f"{KOK}/all-chess-tournaments/") or ""
    soup = BeautifulSoup(html, "html.parser")
    return sorted({(a["href"].split("?")[0], "") for a in soup.find_all("a", href=True) if "/event/" in a["href"]})

def sinir_bul(metin):
    """'U2200', 'Sub 2000', '1800+', 'Supra 1800', '2000-2199' gibi ifadelerden (min, max)."""
    m = metin.lower()
    lo = hi = None
    r = re.search(r"(?<!\d)(\d{4})\s*[–-]\s*(\d{4})(?!\d)", m)
    if r:
        a, b = sorted((int(r.group(1)), int(r.group(2))))
        if 1000 <= a <= 2800 and 1000 <= b <= 2900 and not (1990 <= a <= 2035 and 1990 <= b <= 2035 and "rat" not in m and "elo" not in m):
            return a, b
    r = re.search(r"(?:\bu|under|below|sub|less than|<)\s*-?\s*(\d{4})", m) or re.search(r"\bs(\d{4})\b", m)
    if r and 1000 <= int(r.group(1)) <= 2900: hi = int(r.group(1)) - 1
    r = re.search(r"(?:up to|max(?:imum)?\.?|≤|<=)\s*(\d{4})", m)
    if r and 1000 <= int(r.group(1)) <= 2900: hi = int(r.group(1))
    r = (re.search(r"(\d{4})\s*(?:\+|and above|or above|or more|or higher|and over|and higher)", m)
         or re.search(r"(?:supra|over|above|≥|>=|min(?:imum)?\.?|at least)\s*(\d{4})", m))
    if r and 1000 <= int(r.group(1)) <= 2900: lo = int(r.group(1))
    return lo, hi

def gruplari_bul(soup, baslik):
    gruplar = []
    for h in soup.find_all(["h2", "h3"]):
        if re.search(r"section|group", h.get_text(), re.I):
            tablo = h.find_next("table")
            if not tablo: break
            for tr in tablo.find_all("tr")[1:]:
                hucre = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if not hucre or not hucre[0]: continue
                ad = re.sub(r"^[^\w]+", "", hucre[0]).strip()[:40]
                aciklama = " ".join(hucre[1:])
                if re.search(r"invitation|invited|closed|round robin|norm group", aciklama + " " + ad, re.I) and not re.search(r"open", ad, re.I):
                    gruplar.append({"n": ad, "inv": True}); continue
                lo, hi = sinir_bul(ad + " " + aciklama)
                gruplar.append({"n": ad, "min": lo, "max": hi})
            break
    if not gruplar:
        lo, hi = sinir_bul(baslik)
        gruplar = [{"n": "Açık", "min": lo, "max": hi}]
    return gruplar[:8]

def ulke_bul(konum, metin):
    parca = [p.strip() for p in konum.split(",") if p.strip()]
    if parca and parca[-1].lower() in ULKE:
        sehir = re.sub(r"^\d{3,6}\s*", "", parca[-2]) if len(parca) > 1 else ""
        return ULKE[parca[-1].lower()], sehir
    bas = metin[:2500].lower()
    for ad, bilgi in sorted(ULKE.items(), key=lambda x: -len(x[0])):
        if len(ad) > 3 and re.search(rf"\b{re.escape(ad)}\b", bas):
            return bilgi, (parca[-1] if parca else "")
    return None, ""

def turnuva_oku(html, url, lastmod):
    soup = BeautifulSoup(html, "html.parser")
    og = soup.find("meta", property="og:title")
    baslik = (og["content"] if og and og.get("content") else (soup.title.string if soup.title else "")).strip()
    if re.search(r"\bonline\b", baslik, re.I):
        return None
    metin = soup.get_text("\n", strip=True)
    i = metin.find("Quick Info")
    m = RE_DMY.search(metin, i if i >= 0 else 0) or RE_DMY.search(metin)
    if not m:
        return None
    try:
        s = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        e = datetime.date(int(m.group(6)), int(m.group(5)), int(m.group(4))) if m.group(4) else s
    except ValueError:
        return None
    if e < s or (e - s).days > 70:
        return None
    konum = ""
    k = re.search(r"📍\s*\**\s*(.+)", metin[i:] if i >= 0 else metin)
    if k: konum = k.group(1).strip()
    ulke, sehir = ulke_bul(konum, metin)
    if not ulke or ulke[0] == "TR":
        return None      # ulke bulunamadi ya da Turkiye (TSF taramasi zaten kapsiyor)
    kod, ulke_ad, bayrak = ulke
    odul = re.search(r"Prize Fund \(approx\.\)\s*-?\s*\**\s*\$?\s*([\d.,]+)", metin)
    cr = next((a["href"] for a in soup.find_all("a", href=True) if "chess-results.com" in a["href"]), "")
    resmi = ""
    r = re.search(r"Official Tournament Page[^\n]*\n?\s*(https?://\S+)", metin)
    if r: resmi = r.group(1).rstrip("|>) ")
    tempo = re.search(r"Time Control\s*\n\s*([^\n]*\d[^\n]{3,80})", metin)
    return {
        "c": kod, "ulke": ulke_ad, "bayrak": bayrak, "name": baslik[:160], "city": sehir or konum[:60],
        "start": s.isoformat(), "end": e.isoformat(), "status": "a", "kaynak": "mychess",
        "sections": gruplari_bul(soup, baslik),
        "prize": f"≈ ${odul.group(1)}" if odul else None, "tc": tempo.group(1).strip() if tempo else None,
        "url": resmi or url, "src": url, "cr": cr, "kayit_kapali": "Registrations have closed" in metin,
        "lastmod": lastmod,
    }

def main():
    oturum = requests.Session(); oturum.headers["User-Agent"] = UA
    try:
        onceki = json.load(open(CIKTI, encoding="utf-8"))
    except (OSError, ValueError):
        onceki = {"turnuvalar": []}
    kayitlar = {t["src"]: t for t in onceki.get("turnuvalar", []) if t.get("src")}
    liste = site_haritasi(oturum) or liste_sayfasi(oturum)
    print(f"Site haritasinda {len(liste)} turnuva sayfasi var.")
    yillar = (str(BUGUN.year), str(BUGUN.year + 1))
    aday = [(u, lm) for u, lm in liste
            if any(y in u for y in yillar) and (u not in kayitlar or (lm and lm != kayitlar[u].get("lastmod")))]
    aday.sort(key=lambda x: x[1] or "", reverse=True)
    print(f"Yeni ya da degismis: {len(aday)} (bu calismada en fazla {MAX_SAYFA})")
    okunan = 0
    for u, lm in aday[:MAX_SAYFA]:
        html = getir(oturum, u); okunan += 1
        if not html: continue
        t = turnuva_oku(html, u, lm)
        if t:
            eski = kayitlar.get(u)
            kayitlar[u] = t
            print(("  degisti: " if eski else "  yeni:    ") + f"{t['start']}  {t['ulke']:12} {t['name'][:60]}")
    sinir = (BUGUN - datetime.timedelta(days=400)).isoformat()
    son = sorted((t for t in kayitlar.values() if t["end"] >= sinir), key=lambda t: t["start"])
    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    json.dump({"taranma": datetime.datetime.now().isoformat(timespec="minutes"), "kaynak": KOK,
               "okunan_sayfa": okunan, "turnuvalar": son}, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    gelecek = sum(1 for t in son if t["end"] >= BUGUN.isoformat())
    print(f"BITTI: {okunan} sayfa okundu, toplam {len(son)} kayit ({gelecek} yaklasan) -> {CIKTI}")

if __name__ == "__main__":
    main()
