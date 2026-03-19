import csv
from pathlib import Path
from .base import BaseImporter


class PresidentialImporter(BaseImporter):
    """Import presidential election results from CSV files.

    File format: UTF-8 BOM, semicolon-delimited.
    Row 1: title row (skip).
    Row 2: header with geography + candidate columns (name, %).
    Row 3+: data rows.

    Geography columns (0-12):
        0: Rbr.županije, 1: Županija, 2: Oznaka Gr/Op/Dr,
        3: Grad/općina/država, 4: Rbr BM, 5: Naziv BM,
        6: Lokacija BM, 7: Adresa BM, 8: Ukupno birača,
        9: Glasovalo birača, 10: Glasovalo birača (po listićima),
        11: Važeći listići, 12: Nevažeći listići

    Then pairs: candidate_name, (%) repeated for each candidate.
    """

    DATA_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_predsjednicki_izbori_2024')
    FILES = {
        1: 'rezultati_1krug.csv',
        2: 'rezultati_2krug.csv',
    }

    def run(self):
        election_type = self.get_or_create_election_type('presidential', 'Predsjednički izbori')
        election = self.get_or_create_election(election_type, 2024, 'Predsjednički izbori 2024')

        for round_num, filename in self.FILES.items():
            filepath = self.DATA_DIR / filename
            if not filepath.exists():
                self.log(f"File not found: {filepath}, skipping round {round_num}")
                continue
            self.log(f"Importing presidential round {round_num} from {filename}...")
            self._import_round(election, round_num, filepath)
        self.flush_all()

    def _import_round(self, election, round_num, filepath):
        election_round = self.get_or_create_round(election, round_num)

        with open(filepath, encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            # Row 1: title row — skip
            next(reader)
            # Row 2: header row
            header = next(reader)

        # Parse candidate names from header (columns 13 onwards).
        # Round 1 has (name, %) pairs; round 2 has just name columns.
        candidate_names = []
        has_pct_cols = '(%)' in [h.strip() for h in header[13:]]
        col = 13
        while col < len(header):
            name = header[col].strip()
            if name and name != '(%)':
                candidate_names.append((col, name))
            col += 2 if has_pct_cols else 1

        self.log(f"  Found {len(candidate_names)} candidates: {[n for _, n in candidate_names]}")

        # Create electoral lists and candidacies for each candidate
        lists_and_candidacies = []
        for position, (col_idx, name) in enumerate(candidate_names, 1):
            el_list = self.get_or_create_electoral_list(election_round, name)
            person = self.get_or_create_person(name)
            candidacy = self.get_or_create_candidacy(person, el_list, 1)
            lists_and_candidacies.append((col_idx, el_list, candidacy))

        # Now process data rows
        with open(filepath, encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # skip title
            next(reader)  # skip header

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
