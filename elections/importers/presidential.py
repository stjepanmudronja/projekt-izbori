import csv
from pathlib import Path
from .base import BaseImporter


class PresidentialImporter(BaseImporter):
    """Import presidential election results from CSV files.

    File format: semicolon-delimited.
    Optional title row(s) followed by a header row with geography + candidate
    columns. Round 1 typically has interleaved ``(%)`` columns; round 2 does
    not.

    Geography columns (0-12):
        0: Rbr.županije, 1: Županija, 2: Oznaka Gr/Op/Dr,
        3: Grad/općina/država, 4: Rbr BM, 5: Naziv BM,
        6: Lokacija BM, 7: Adresa BM, 8: Ukupno birača,
        9: Glasovalo birača, 10: Glasovalo birača (po listićima),
        11: Važeći listići, 12: Nevažeći listići

    Then pairs/singles per candidate. Each year may differ in encoding and
    whether a title row precedes the header — see ``YEARS``.
    """

    BASE_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_predsjednicki_izbori_2024')

    YEARS = {
        2024: {
            'dir': BASE_DIR,
            'encoding': 'utf-8-sig',
            'title_rows': 1,
            'name': 'Predsjednički izbori 2024',
            'files': {1: 'rezultati_1krug.csv', 2: 'rezultati_2krug.csv'},
        },
        2019: {
            'dir': BASE_DIR / '2019',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2019',
            'files': {1: 'rezultati_bm(1).csv', 2: 'rezultati_bm(2).csv'},
        },
    }

    def __init__(self, stdout=None, years=None):
        super().__init__(stdout=stdout)
        self.years = years if years else list(self.YEARS.keys())

    def run(self):
        election_type = self.get_or_create_election_type('presidential', 'Predsjednički izbori')

        for year in self.years:
            cfg = self.YEARS.get(year)
            if not cfg:
                self.log(f"Unknown year {year}, skipping (configured: {list(self.YEARS)})")
                continue
            election = self.get_or_create_election(election_type, year, cfg['name'])
            for round_num, filename in cfg['files'].items():
                filepath = cfg['dir'] / filename
                if not filepath.exists():
                    self.log(f"File not found: {filepath}, skipping {year} round {round_num}")
                    continue
                self.log(f"Importing presidential {year} round {round_num} from {filename}...")
                self._import_round(election, round_num, filepath, cfg['encoding'], cfg['title_rows'])

        self.flush_all()

    def _import_round(self, election, round_num, filepath, encoding, title_rows):
        election_round = self.get_or_create_round(election, round_num)

        with open(filepath, encoding=encoding) as f:
            reader = csv.reader(f, delimiter=';')
            for _ in range(title_rows):
                next(reader)
            header = next(reader)

        candidate_names = []
        has_pct_cols = '(%)' in [h.strip() for h in header[13:]]
        col = 13
        while col < len(header):
            name = header[col].strip()
            if name and name != '(%)':
                candidate_names.append((col, name))
            col += 2 if has_pct_cols else 1

        self.log(f"  Found {len(candidate_names)} candidates: {[n for _, n in candidate_names]}")

        lists_and_candidacies = []
        for position, (col_idx, name) in enumerate(candidate_names, 1):
            el_list = self.get_or_create_electoral_list(election_round, name)
            person = self.get_or_create_person(name)
            candidacy = self.get_or_create_candidacy(person, el_list, 1)
            lists_and_candidacies.append((col_idx, el_list, candidacy))

        with open(filepath, encoding=encoding) as f:
            reader = csv.reader(f, delimiter=';')
            for _ in range(title_rows + 1):
                next(reader)

            row_count = 0
            for row in reader:
                if len(row) < 13:
                    continue

                county_code = row[0].strip()
                county_name = row[1].strip()
                muni_type = row[2].strip()
                muni_name = row[3].strip()
                ps_number = row[4].strip()
                ps_name = row[5].strip()
                ps_location = row[6].strip()
                ps_address = row[7].strip()

                registered = self.parse_int(row[8])
                cast = self.parse_int(row[9])
                valid = self.parse_int(row[11])
                invalid = self.parse_int(row[12])

                county = self.get_or_create_county(county_code, county_name)
                municipality = self.get_or_create_municipality(county, muni_name, muni_type)
                polling_station = self.get_or_create_polling_station(
                    municipality, ps_number, ps_name, ps_location, ps_address
                )

                self.create_turnout(election_round, polling_station, registered, cast, valid, invalid)

                for col_idx, el_list, candidacy in lists_and_candidacies:
                    votes = self.parse_int(row[col_idx]) if col_idx < len(row) else 0
                    self.create_list_result(el_list, polling_station, votes)
                    self.create_candidate_result(candidacy, polling_station, votes)

                row_count += 1

        self.flush_all()
        self.log(f"  Imported {row_count} polling station rows for round {round_num}")
