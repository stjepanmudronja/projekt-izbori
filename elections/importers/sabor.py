import csv
from pathlib import Path
from .base import BaseImporter


class SaborImporter(BaseImporter):
    """Import Sabor (parliamentary) election results.

    File format: windows-1250 encoded, semicolon-delimited.
    No title row — header is row 1.

    Districts 1-11: groups of 15 columns per list (1 list votes + 14 candidate votes).
    District 12: individual candidates only (1 column per candidate, no list grouping).

    Files per district:
        XX_DD_rezultati.csv — main results
        XX_DD_rezultati_inozemstvo.csv — diaspora results
        XX_DD_rezultati_posebna.csv — special polling stations
    """

    DATA_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/rezultati_sabor_2024/CSV')
    CANDIDATES_PER_LIST = 14
    COLS_PER_LIST = 15  # 1 list + 14 candidates
    GEO_COLS = 15  # columns 0-14

    def run(self):
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(election_type, 2024, 'Parlamentarni izbori 2024')
        election_round = self.get_or_create_round(election, 1)

        # Import districts 1-11
        for district_num in range(1, 12):
            self._import_district(election, election_round, district_num)

        # Import district 12 (special — individual candidates)
        self._import_district_12(election, election_round)

        self.flush_all()

    def _get_files_for_district(self, district_num):
        """Find all CSV files for a given district number."""
        files = []
        for path in sorted(self.DATA_DIR.glob(f'*_{district_num:02d}_rezultati*.csv')):
            files.append(path)
        return files

    def _import_district(self, election, election_round, district_num):
        district_name = f"{self._roman(district_num)}. IZBORNA JEDINICA"
        district = self.get_or_create_district(election, district_num, district_name)

        files = self._get_files_for_district(district_num)
        if not files:
            self.log(f"No files found for district {district_num}")
            return

        # Parse header from the first (main) file to get list/candidate structure
        header = self._read_header(files[0])
        lists_info = self._parse_list_groups(header)
        self.log(f"District {district_num}: {len(lists_info)} lists, {len(files)} files")

        # Create electoral lists and candidacies
        list_data = []
        for list_name, candidates in lists_info:
            el_list = self.get_or_create_electoral_list(election_round, list_name, district)
            candidacies = []
            for pos, cand_name in enumerate(candidates, 1):
                person = self.get_or_create_person(cand_name)
                candidacy = self.get_or_create_candidacy(person, el_list, pos)
                candidacies.append(candidacy)
            list_data.append((el_list, candidacies))

        # Import all files for this district
        for filepath in files:
            self._import_file(election_round, district, filepath, list_data)

    def _import_district_12(self, election, election_round):
        district = self.get_or_create_district(election, 12, 'XII. IZBORNA JEDINICA')
        files = self._get_files_for_district(12)
        if not files:
            self.log("No files found for district 12")
            return

        # All district 12 files should have same candidates
        header = self._read_header(files[0])
        candidate_names = [h.strip() for h in header[self.GEO_COLS:] if h.strip()]
        self.log(f"District 12: {len(candidate_names)} individual candidates, {len(files)} files")

        # Each candidate gets their own electoral list (for uniformity)
        list_data = []
        for cand_name in candidate_names:
            el_list = self.get_or_create_electoral_list(election_round, cand_name, district)
            person = self.get_or_create_person(cand_name)
            candidacy = self.get_or_create_candidacy(person, el_list, 1)
            list_data.append((el_list, [candidacy]))

        for filepath in files:
            self._import_file_d12(election_round, district, filepath, list_data)

    def _read_header(self, filepath):
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            return next(reader)

    def _parse_list_groups(self, header):
        """Parse header into groups of (list_name, [candidate_names]).

        Starting from column 15, every 15 columns is one group:
        col 0: list name, cols 1-14: candidate names.
        """
        groups = []
        col = self.GEO_COLS
        while col + self.COLS_PER_LIST <= len(header):
            list_name = header[col].strip()
            candidates = [header[col + 1 + i].strip() for i in range(self.CANDIDATES_PER_LIST)]
            groups.append((list_name, candidates))
            col += self.COLS_PER_LIST
        return groups

    def _import_file(self, election_round, district, filepath, list_data):
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # skip header

            row_count = 0
            for row in reader:
                if len(row) < self.GEO_COLS:
                    continue

                county_code = row[2].strip()
                county_name = row[3].strip()
                muni_type = row[4].strip()
                muni_name = row[5].strip()
                ps_number = row[6].strip()
                ps_name = row[7].strip()
                ps_location = row[8].strip()
                ps_address = row[9].strip()

                registered = self.parse_int(row[10])
                cast = self.parse_int(row[11])
                valid = self.parse_int(row[13])
                invalid = self.parse_int(row[14])

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
        self.log(f"  {filepath.name}: {row_count} rows")

    def _import_file_d12(self, election_round, district, filepath, list_data):
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # skip header

            row_count = 0
            for row in reader:
                if len(row) < self.GEO_COLS:
                    continue

                county_code = row[2].strip()
                county_name = row[3].strip()
                muni_type = row[4].strip()
                muni_name = row[5].strip()
                ps_number = row[6].strip()
                ps_name = row[7].strip()
                ps_location = row[8].strip()
                ps_address = row[9].strip()

                registered = self.parse_int(row[10])
                cast = self.parse_int(row[11])
                valid = self.parse_int(row[13])
                invalid = self.parse_int(row[14])

                county = self.get_or_create_county(county_code, county_name)
                municipality = self.get_or_create_municipality(county, muni_name, muni_type)
                polling_station = self.get_or_create_polling_station(
                    municipality, ps_number, ps_name, ps_location, ps_address
                )

                self.create_turnout(election_round, polling_station, registered, cast, valid, invalid)

                for idx, (el_list, candidacies) in enumerate(list_data):
                    col = self.GEO_COLS + idx
                    votes = self.parse_int(row[col]) if col < len(row) else 0
                    self.create_list_result(el_list, polling_station, votes)
                    self.create_candidate_result(candidacies[0], polling_station, votes)

                row_count += 1

        self.flush_all()
        self.log(f"  {filepath.name}: {row_count} rows")

    @staticmethod
    def _roman(n):
        vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        result = ''
        for val, numeral in vals:
            while n >= val:
                result += numeral
                n -= val
        return result
