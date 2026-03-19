import csv
from pathlib import Path
from .base import BaseImporter


class EUParliamentImporter(BaseImporter):
    """Import EU Parliament election results.

    File format: windows-1250 encoded, semicolon-delimited.
    No title row — header is row 1.

    Geography columns (0-12): same as sabor but without district columns.
    Then groups of 13 columns per list (1 list votes + 12 candidate votes).
    Coalition names may contain literal newlines.
    """

    DATA_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_eu_parlamet_2024/CSV')
    CANDIDATES_PER_LIST = 12
    COLS_PER_LIST = 13  # 1 list + 12 candidates
    GEO_COLS = 13  # columns 0-12

    def run(self):
        election_type = self.get_or_create_election_type('eu_parliament', 'Izbori za Europski parlament')
        election = self.get_or_create_election(election_type, 2024, 'Izbori za Europski parlament 2024')
        election_round = self.get_or_create_round(election, 1)

        filepath = self.DATA_DIR / 'rezultati_eupa.csv'
        if not filepath.exists():
            self.log(f"File not found: {filepath}")
            return

        # Parse header
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            header = next(reader)

        # Parse list groups
        lists_info = self._parse_list_groups(header)
        self.log(f"Found {len(lists_info)} electoral lists")

        # Create electoral lists and candidacies
        list_data = []
        for list_name, candidates in lists_info:
            el_list = self.get_or_create_electoral_list(election_round, list_name)
            candidacies = []
            for pos, cand_name in enumerate(candidates, 1):
                person = self.get_or_create_person(cand_name)
                candidacy = self.get_or_create_candidacy(person, el_list, pos)
                candidacies.append(candidacy)
            list_data.append((el_list, candidacies))

        # Import data rows
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # skip header

            row_count = 0
            for row in reader:
                if len(row) < self.GEO_COLS:
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

                col = self.GEO_COLS
                for el_list, candidacies in list_data:
                    list_votes = self.parse_int(row[col]) if col < len(row) else 0
                    self.create_list_result(el_list, polling_station, list_votes)

                    for i, candidacy in enumerate(candidacies):
                        cand_col = col + 1 + i
                        votes = self.parse_int(row[cand_col]) if cand_col < len(row) else 0
                        self.create_candidate_result(candidacy, polling_station, votes)

                    col += self.COLS_PER_LIST

                row_count += 1

        self.flush_all()
        self.log(f"Imported {row_count} polling station rows")

    def _parse_list_groups(self, header):
        """Parse header into groups of (list_name, [candidate_names])."""
        groups = []
        col = self.GEO_COLS
        while col + self.COLS_PER_LIST <= len(header):
            list_name = header[col].strip()
            candidates = [header[col + 1 + i].strip() for i in range(self.CANDIDATES_PER_LIST)]
            groups.append((list_name, candidates))
            col += self.COLS_PER_LIST
        return groups
