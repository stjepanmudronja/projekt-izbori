import csv
from pathlib import Path
from .base import BaseImporter
from .name_utils import clean_candidate_name, looks_like_person_name


class SaborImporter(BaseImporter):
    """Import Sabor (parliamentary) election results.

    File format: windows-1250 encoded, semicolon-delimited.
    No title row — header is row 1.

    Districts 1-10: groups of 15 columns per list (1 list votes + 14 candidate votes).
    District 11 (diaspora): variable-width list groups (parties may nominate <14 candidates).
    District 12 (minorities): individual candidates only (1 column per candidate).

    Files per district:
        XX_DD_rezultati.csv — main results
        XX_DD_rezultati_inozemstvo.csv — diaspora results
        XX_DD_rezultati_posebna.csv — special polling stations

    Per-year files live under `{BASE_DIR}/{year}/CSV/`; pass `year=YYYY` to
    `SaborImporter(year=YYYY)` (defaults to 2024). The shape has been stable
    across 2020 and 2024 so no per-year layout config is needed yet.
    """

    BASE_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/rezultati_sabor_2024')
    CANDIDATES_PER_LIST = 14
    COLS_PER_LIST = 15  # 1 list + 14 candidates
    GEO_COLS = 15  # columns 0-14

    # Minority sub-districts in district XII.
    # Keys: file prefix. Values: (sub-district number, seats, name).
    MINORITY_SUBDISTRICTS = {
        '13': (121, 3, 'XII. IJ - Srpska nacionalna manjina'),
        '23': (122, 1, 'XII. IJ - Mađarska nacionalna manjina'),
        '33': (123, 1, 'XII. IJ - Talijanska nacionalna manjina'),
        '43': (124, 1, 'XII. IJ - Češka i slovačka nacionalna manjina'),
        '53': (125, 1, 'XII. IJ - Romska, rusinska, ukrajinska i dr.'),
        '63': (126, 1, 'XII. IJ - Albanska, bošnjačka, crnogorska i dr.'),
    }

    # Words that reliably identify a column as a list (party/coalition) name,
    # used only for variable-width parsing (district 11).
    LIST_KEYWORDS = {
        'HDZ', 'SDP', 'DP', 'HSS', 'HSP', 'MOST', 'HKS', 'IDS', 'HNS', 'HSLS',
        'SDSS', 'BDSH', 'OIP', 'FOKUS', 'AUTOHTONA', 'CENTAR', 'MOŽEMO',
        'STRANKA', 'PLATFORMA', 'REPUBLIKA', 'POKRET', 'KOALICIJA', 'SAVEZ',
        'UNIJA', 'FORUM', 'DOMOVINSKI', 'HRVATSKA', 'HRVATSKI', 'HRVATSKO',
        'HRVATSKE', 'DEMOKRATSKA', 'DEMOKRATSKI', 'ZAJEDNICA', 'BILO',
        'POLITIČKA', 'LIBERALNA', 'SELJAČKA', 'SOCIJALDEMOKRATSKA',
        'NARODNA', 'NARODNI', 'PRAVA', 'LIJEVI', 'DESNI', 'ODLUČNOST',
        'PRAVEDNOST', 'ZELENA', 'NOVA', 'PRAVDA', 'RIJEKA', 'RDS',
    }

    def __init__(self, year=2024, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year
        self.data_dir = self.BASE_DIR / str(year) / 'CSV'

    def run(self, only_district=None):
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(election_type, self.year, f'Parlamentarni izbori {self.year}')
        election_round = self.get_or_create_round(election, 1)

        # Import districts 1-11
        for district_num in range(1, 12):
            if only_district is not None and district_num != only_district:
                continue
            self._import_district(election, election_round, district_num)

        # Import district 12 (special — individual candidates)
        if only_district is None or only_district == 12:
            self._import_district_12(election, election_round)

        self.flush_all()

    def _get_files_for_district(self, district_num):
        """Find all CSV files for a given district number.

        Two filename conventions exist across years:
          2020/2024: `XX_DD_rezultati*.csv` — district in the 2nd field (e.g. 02_01)
          2016:      `DDD_00_rezultati*.csv` — district in the 1st field (e.g. 001_00);
                     district 12's minority sub-districts are 012_13 … 012_63.
        The 2016 fields are effectively swapped, so fall back to a first-field
        glob when the standard second-field pattern finds nothing.
        """
        files = sorted(self.data_dir.glob(f'*_{district_num:02d}_rezultati*.csv'))
        if not files:
            files = sorted(self.data_dir.glob(f'{district_num:03d}_*_rezultati*.csv'))
        return files

    def _import_district(self, election, election_round, district_num):
        district_name = f"{self._roman(district_num)}. IZBORNA JEDINICA"
        district = self.get_or_create_district(election, district_num, district_name)

        files = self._get_files_for_district(district_num)
        if not files:
            self.log(f"No files found for district {district_num}")
            return

        # Parse header from the first (main) file to get list/candidate structure.
        # District 11 (diaspora) uses variable-width list groups; others use fixed 15.
        header = self._read_header(files[0])
        if district_num == 11:
            totals = self._column_totals(files, len(header))
            lists_info = self._parse_list_groups_variable(header, col_totals=totals)
        else:
            lists_info = self._parse_list_groups(header)
        self.log(f"District {district_num}: {len(lists_info)} lists, {len(files)} files")

        # Create electoral lists and candidacies. Each entry stores the column
        # offset of the list's vote column so variable-width layouts work.
        list_data = []
        for list_name, candidates, list_col in lists_info:
            el_list = self.get_or_create_electoral_list(election_round, list_name, district)
            candidacies = []
            for pos, cand_name in enumerate(candidates, 1):
                person = self.get_or_create_person(cand_name)
                candidacy = self.get_or_create_candidacy(person, el_list, pos)
                candidacies.append(candidacy)
            list_data.append((el_list, candidacies, list_col))

        # Import all files for this district
        for filepath in files:
            self._import_file(election_round, district, filepath, list_data)

    def _import_district_12(self, election, election_round):
        files = self._get_files_for_district(12)
        if not files:
            self.log("No files found for district 12")
            return

        # District 12 has 6 minority sub-districts (13_12, 23_12, …63_12),
        # each with different candidates and separate seat allocations.
        # Create a separate ElectoralDistrict per sub-district.
        from collections import defaultdict
        groups = defaultdict(list)
        for fp in files:
            # Sub-district code is the 1st field in 2020/2024 (13_12) but the
            # 2nd in 2016 (012_13); pick whichever field is a known sub-district.
            parts = fp.name.split('_')
            prefix = next((p for p in parts[:2] if p in self.MINORITY_SUBDISTRICTS), parts[0])
            groups[prefix].append(fp)

        total_candidates = 0
        for prefix in sorted(groups):
            sub_info = self.MINORITY_SUBDISTRICTS.get(prefix)
            if not sub_info:
                self.log(f"Unknown minority sub-district prefix: {prefix}")
                continue
            sub_number, sub_seats, sub_name = sub_info
            district = self.get_or_create_district(election, sub_number, sub_name)

            group_files = sorted(groups[prefix])
            header = self._read_header(group_files[0])
            candidate_names = [
                clean_candidate_name(h) for h in header[self.GEO_COLS:] if h.strip()
            ]
            total_candidates += len(candidate_names)

            # Each candidate gets their own electoral list (for uniformity)
            list_data = []
            for cand_name in candidate_names:
                el_list = self.get_or_create_electoral_list(election_round, cand_name, district)
                person = self.get_or_create_person(cand_name)
                candidacy = self.get_or_create_candidacy(person, el_list, 1)
                list_data.append((el_list, [candidacy]))

            for filepath in group_files:
                self._import_file_d12(election_round, district, filepath, list_data)

        self.log(f"District 12: {total_candidates} individual candidates across {len(groups)} sub-districts, {len(files)} files")

    def _read_header(self, filepath):
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            return next(reader)

    def _parse_list_groups(self, header):
        """Parse header into groups of (list_name, [candidate_names], list_col).

        Starting from column 15, every 15 columns is one group:
        col 0: list name, cols 1-14: candidate names. Candidate names pass
        through `clean_candidate_name` so academic-title noise doesn't split
        the same person across years in cross-election search.
        """
        groups = []
        col = self.GEO_COLS
        while col + self.COLS_PER_LIST <= len(header):
            list_name = header[col].strip()
            candidates = [
                clean_candidate_name(header[col + 1 + i])
                for i in range(self.CANDIDATES_PER_LIST)
            ]
            groups.append((list_name, candidates, col))
            col += self.COLS_PER_LIST
        return groups

    @classmethod
    def _is_list_name(cls, text):
        """Heuristic: does this column header look like a party/list name
        rather than a personal candidate name?"""
        if not text:
            return False
        # Unambiguous party/coalition punctuation, which personal names (even
        # with a hyphenated surname — no surrounding spaces) never carry.
        if ' - ' in text or '!' in text or '"' in text:
            return True
        # Known party/coalition keywords.
        tokens = text.replace('.', '').replace('!', '').split()
        for tok in tokens:
            if tok in cls.LIST_KEYWORDS:
                return True
        # A bare comma is *not* enough on its own: older CSVs (2015, 2016) put
        # academic titles in candidate columns ("IVANA BUNTIĆ, mag. iur."),
        # which would otherwise be read as lists and shatter the district-11
        # groups. Fall back to shape — anything that isn't a personal name here
        # is a list, so a single-token party like "MOST" still reads as one.
        return not looks_like_person_name(text)

    def _column_totals(self, files, ncols):
        """Sum every result column across all of a district's files."""
        totals = [0] * ncols
        for filepath in files:
            with open(filepath, encoding='windows-1250') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)
                for row in reader:
                    for col in range(self.GEO_COLS, min(len(row), ncols)):
                        totals[col] += self.parse_int(row[col])
        return totals

    def _repair_list_cols(self, list_cols, totals, ncols):
        """Insert list boundaries the name heuristic missed.

        A preferential vote is only countable for the list it was cast on, so
        a list's candidate votes can never outnumber the list's own votes.
        Where a group breaks that, a party whose name reads like a person's
        (2016 district 11 has "AKCIJA MLADIH") is sitting inside it, and the
        column where the running candidate total overruns the list total is
        exactly where that party starts. Splitting only groups that actually
        violate keeps the heuristic's correct boundaries intact.
        """
        repaired = []
        queue = list(list_cols)
        while queue:
            col = queue.pop(0)
            repaired.append(col)
            end = queue[0] if queue else ncols
            running = 0
            for c in range(col + 1, end):
                running += totals[c]
                if running > totals[col]:
                    self.log(
                        f"  list boundary recovered at column {c} "
                        f"({totals[col]} list votes < {running} preferential)"
                    )
                    queue.insert(0, c)
                    break
        return repaired

    def _parse_list_groups_variable(self, header, col_totals=None):
        """Parse header with variable-width list groups (used for district 11).

        Detects list-header columns by pattern; all columns between two list
        headers are that list's candidates. When `col_totals` is supplied the
        boundaries are validated against the vote counts and any the name
        heuristic missed are recovered. Returns
        [(list_name, [candidate_names], list_col), ...].
        """
        list_cols = [
            col for col in range(self.GEO_COLS, len(header))
            if self._is_list_name(header[col].strip())
        ]
        if col_totals:
            list_cols = self._repair_list_cols(list_cols, col_totals, len(header))
        groups = []
        for i, list_col in enumerate(list_cols):
            list_name = header[list_col].strip()
            end = list_cols[i + 1] if i + 1 < len(list_cols) else len(header)
            candidates = [
                clean_candidate_name(header[c]) for c in range(list_col + 1, end)
                if header[c].strip()
            ]
            groups.append((list_name, candidates, list_col))
        return groups

    def _import_file(self, election_round, district, filepath, list_data):
        # Posebna (mobile) and inozemstvo (abroad) files reuse the number series
        # 001-0NN, which collides with main-file stations in the same municipality
        # label (e.g. in Sabor data, "ZAGREB - VI. IZBORNA JEDINICA" muni contains
        # both regular station 006 = ČEHI and mobile station 006 = DOM 85). Without
        # a prefix the importer merges unrelated physical stations into one row.
        num_prefix = self._station_number_prefix(filepath)

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
                    municipality, f'{num_prefix}{ps_number}', ps_name, ps_location, ps_address
                )

                self.create_turnout(election_round, polling_station, registered, cast, valid, invalid)

                for el_list, candidacies, list_col in list_data:
                    list_votes = self.parse_int(row[list_col]) if list_col < len(row) else 0
                    self.create_list_result(el_list, polling_station, list_votes)

                    for i, candidacy in enumerate(candidacies):
                        cand_col = list_col + 1 + i
                        votes = self.parse_int(row[cand_col]) if cand_col < len(row) else 0
                        self.create_candidate_result(candidacy, polling_station, votes)

                row_count += 1

        self.flush_all()
        self.log(f"  {filepath.name}: {row_count} rows")

    def _import_file_d12(self, election_round, district, filepath, list_data):
        """Import district 12 minority results.

        IMPORTANT: Skip turnout creation here. These CSV files contain
        minority-specific turnout (e.g. reg=0, cast=2) which is a subset
                of the station's total turnout. Real turnout is already set
        by the district 1-10 import for the same polling stations.
        """
        num_prefix = self._station_number_prefix(filepath)

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

                county = self.get_or_create_county(county_code, county_name)
                municipality = self.get_or_create_municipality(county, muni_name, muni_type)
                polling_station = self.get_or_create_polling_station(
                    municipality, f'{num_prefix}{ps_number}', ps_name, ps_location, ps_address
                )

                # Skip turnout — d12 files have minority-only voter counts, not station totals

                for idx, (el_list, candidacies) in enumerate(list_data):
                    col = self.GEO_COLS + idx
                    votes = self.parse_int(row[col]) if col < len(row) else 0
                    self.create_list_result(el_list, polling_station, votes)
                    self.create_candidate_result(candidacies[0], polling_station, votes)

                row_count += 1

        self.flush_all()
        self.log(f"  {filepath.name}: {row_count} rows")

    @staticmethod
    def _station_number_prefix(filepath):
        """Return a prefix to apply to polling-station numbers so that
        posebna/inozemstvo station #006 doesn't collide with a main-file
        station #006 in the same municipality."""
        name = filepath.name
        if '_posebna' in name:
            return 'P'
        if '_inozemstvo' in name:
            return 'I'
        return ''

    @staticmethod
    def _roman(n):
        vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        result = ''
        for val, numeral in vals:
            while n >= val:
                result += numeral
                n -= val
        return result
