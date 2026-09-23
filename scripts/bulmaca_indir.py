# Lichess bulmaca veritabani -> data/bulmaca/*.json
# Kaynak: https://database.lichess.org/#puzzles  (CC0 lisansli, serbestce kullanilabilir)
# ~6 milyon bulmacadan reyting araligina gore ornekleme yapar; site bu kucuk dosyalari okur.
# Ayda bir yeter: dosya 25 gunden yeniyse indirmeyi atlar (BULMACA_ZORLA=1 ile zorlanir).
import csv, io, json, os, random, datetime, sys

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
UA = "TurnuvaRehberim/0.5 (kisisel turnuva rehberi; github.com)"
KLASOR = "data/bulmaca"
KOVA = 100                 # reyting kovasi genisligi
ALT, UST = 600, 2800       # toplanacak reyting araligi
KOVA_HEDEF = int(os.environ.get("BULMACA_KOVA", "350"))   # her kovada kac bulmaca
MIN_POP = 70               # begeni esigi (kotu bulmacalari eler)
BUGUN = datetime.date.today()

def gerekli_mi():
    if os.environ.get("BULMACA_ZORLA"):
        return True
    try:
        meta = json.load(open(f"{KLASOR}/meta.json", encoding="utf-8"))
        return (BUGUN - datetime.date.fromisoformat(meta["indirme"])).days >= 25
    except (OSError, ValueError, KeyError):
        return True

def kova(r):
    return max(ALT, min(UST - KOVA, (int(r) // KOVA) * KOVA))

def main():
    if not gerekli_mi():
        print("Bulmacalar guncel, indirme atlandi."); return
    try:
        import requests, zstandard
    except ImportError:
        print("zstandard/requests eksik: pip install requests zstandard"); return

    print("Bulmaca veritabani indiriliyor (yaklasik 300 MB, birkac dakika)…")
    r = requests.get(URL, headers={"User-Agent": UA}, stream=True, timeout=600)
    r.raise_for_status()
    dctx = zstandard.ZstdDecompressor()
    akis = io.TextIOWrapper(dctx.stream_reader(r.raw), encoding="utf-8", errors="replace")
    okuyucu = csv.DictReader(akis)

    rnd = random.Random(20260923)
    kovalar, sayac, toplam = {}, {}, 0
    for s in okuyucu:
        try:
            rey = int(s["Rating"]); pop = int(s["Popularity"])
        except (KeyError, ValueError):
            continue
        if rey < ALT or rey >= UST or pop < MIN_POP:
            continue
        k = kova(rey)
        sayac[k] = sayac.get(k, 0) + 1
        liste = kovalar.setdefault(k, [])
        kayit = [s["PuzzleId"], s["FEN"], s["Moves"], rey, s.get("Themes", ""), s.get("GameUrl", "")]
        if len(liste) < KOVA_HEDEF:                      # rezervuar ornekleme: havuzun tamamindan adil secim
            liste.append(kayit)
        else:
            j = rnd.randrange(sayac[k])
            if j < KOVA_HEDEF:
                liste[j] = kayit
        toplam += 1
        if toplam % 500000 == 0:
            print(f"  {toplam} bulmaca tarandi…")

    if toplam < 1000:
        raise SystemExit(f"Beklenenden az bulmaca ({toplam}); dosya bicimi degismis olabilir.")

    os.makedirs(KLASOR, exist_ok=True)
    for f in os.listdir(KLASOR):
        if f.startswith("b") and f.endswith(".json"):
            os.remove(os.path.join(KLASOR, f))
    for k, liste in sorted(kovalar.items()):
        liste.sort(key=lambda x: x[3])
        with open(f"{KLASOR}/b{k}.json", "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, separators=(",", ":"))
    json.dump({"indirme": BUGUN.isoformat(), "kaynak": URL, "lisans": "CC0",
               "kova": KOVA, "alt": ALT, "ust": UST,
               "adet": sum(len(v) for v in kovalar.values()), "tarandi": toplam},
              open(f"{KLASOR}/meta.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{sum(len(v) for v in kovalar.values())} bulmaca {len(kovalar)} dosyaya yazildi "
          f"({toplam} bulmaca tarandi).")

if __name__ == "__main__":
    main()
