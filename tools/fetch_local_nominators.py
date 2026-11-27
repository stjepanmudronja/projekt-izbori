"""Download who nominated each mayor, načelnik and župan candidate, 2013-2025.

    python tools/fetch_local_nominators.py [--year 2025] [--delay 0.4]

The results files we import (Rezultati_lokalni_izbori/<year>/) print only the
candidate's name. DIP's results archive (izbori.hr/arhiva-izbora) serves one
file per race whose every candidate carries "stranke" — the nominating
parties, or "KANDIDAT GRUPE BIRAČA" — and, from 2021, their full names. This
fetches round 1 of every race (round 1 has every candidate):
- župan: r_15_<county>_0000_000
- načelnik / gradonačelnik: r_17_<county>_<town>_000 (Grad Zagreb's
  gradonačelnik is filed with the župani: r_15_21_0000_000)
into files/Rezultati_lokalni_izbori/<year>/predlagatelji/. The towns and their
county codes come from the archive's own code list (its lokalni-<year>-dao.js).
2013 and 2017 are CSV, 2021 and 2025 JSON. Files already there are skipped,
so a broken run can simply be re-run.
"""
import argparse
import re
import time
import urllib.request
from pathlib import Path

BASE = 'https://www.izbori.hr/arhiva-izbora/'
ROOT = Path(__file__).resolve().parent.parent / 'files' / 'Rezultati_lokalni_izbori'
YEARS = (2013, 2017, 2021, 2025)
HEADERS = {'User-Agent': 'projekt-izbori-fetch/1.0'}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def races(year):
    """[(filename)] for every župan and municipal executive race of a year."""
    dao = get(f'{BASE}app/dao/lokalni/lokalni-{year}-dao.js').decode('utf-8-sig', errors='replace')
    block = dao[dao.index('var gradOpcina'):dao.index('var vrsta', dao.index('var gradOpcina'))]
    towns = re.findall(r'"code":\s*"(\d{4})",\s*"label":\s*"[^"]*",\s*"codetop":\s*"(\d\d)"', block)
    ext = 'csv' if year <= 2017 else 'json'
    names = [f'r_15_{c:02d}_0000_000.{ext}' for c in range(1, 21)]
    for code, county in towns:
        if code in ('1333', '0021'):        # Grad Zagreb: its gradonačelnik is filed with the župani
            names.append(f'r_15_21_0000_000.{ext}')
        else:
            names.append(f'r_17_{county}_{code}_000.{ext}')
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, choices=YEARS)
    ap.add_argument('--delay', type=float, default=0.4)
    args = ap.parse_args()
    for year in ([args.year] if args.year else YEARS):
        out = ROOT / str(year) / 'predlagatelji'
        out.mkdir(parents=True, exist_ok=True)
        names = races(year)
        got = missing = 0
        for name in names:
            target = out / name
            if target.exists():
                continue
            try:
                target.write_bytes(get(f'{BASE}data/lokalni/{year}/rezultati/1/{name}'))
                got += 1
            except Exception as e:                       # 404: no such race that year
                missing += 1
                print(f'{year} {name}: {e}')
            time.sleep(args.delay)
        print(f'{year}: {len(names)} races, {got} downloaded, {missing} missing')


if __name__ == '__main__':
    main()
