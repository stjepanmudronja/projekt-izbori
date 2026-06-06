import csv
from pathlib import Path
from .base import BaseImporter
from .name_utils import clean_candidate_name


# Per-year file layout. Older elections (2014) carry six extra geo columns
# (Rbr GČ / Naziv GČ / Rbr MO / Naziv MO / Rbr IJ / Naziv IJ) that we don't
# import; they sit between muni and polling-station columns. List shape also
# differs: 2014 had 11 seats so each list has 11 candidates; from 2019 each
# list has 12 candidates. Adding a new year = a new entry here.
YEAR_CONFIG = {
    2024: {
        'rel_path': '2024/CSV/rezultati_eupa.csv',
        'encoding': 'windows-1250',
        'geo_cols': 13,
        'candidates_per_list': 12,
        'col': {
            'county_code': 0, 'county_name': 1,
            'muni_type': 2,  'muni_name': 3,
            'ps_number': 4,  'ps_name': 5, 'ps_location': 6, 'ps_address': 7,
            'registered': 8, 'cast': 9, 'valid': 11, 'invalid': 12,
        },
    },
    2019: {
        'rel_path': '2019/CSV/rezultati_eupa.csv',
        'encoding': 'windows-1250',
        'geo_cols': 13,
        'candidates_per_list': 12,
        'col': {
            'county_code': 0, 'county_name': 1,
            'muni_type': 2,  'muni_name': 3,
            'ps_number': 4,  'ps_name': 5, 'ps_location': 6, 'ps_address': 7,
            'registered': 8, 'cast': 9, 'valid': 11, 'invalid': 12,
        },
    },
    2013: {
        # Croatia's first EP election (held April 2013, just after EU accession;
        # 12 seats for the partial term ending 2014). Same shape as 2019/2024 —
        # 13 geo cols + 12 candidates/list — but the file lives directly under
        # `2013/` and a few list-name cells carry a trailing `\xa0` no-break
        # space which str.strip() removes for free.
        'rel_path': '2013/EUP2013_rezultati_po_BM_Work.csv',
        'encoding': 'windows-1250',
        'geo_cols': 13,
        'candidates_per_list': 12,
        'col': {
            'county_code': 0, 'county_name': 1,
            'muni_type': 2,  'muni_name': 3,
            'ps_number': 4,  'ps_name': 5, 'ps_location': 6, 'ps_address': 7,
            'registered': 8, 'cast': 9, 'valid': 11, 'invalid': 12,
        },
    },
    2014: {
        'rel_path': '2014/rezultati_eupa_interno_rezultati_eupa.csv',
        'encoding': 'windows-1250',
        'geo_cols': 19,
        'candidates_per_list': 11,
        'col': {
            'county_code': 0, 'county_name': 1,
            'muni_type': 2,  'muni_name': 3,
            # 4-9: Rbr GČ, Naziv GČ, Rbr MO, Naziv MO, Rbr IJ, Naziv IJ — skipped
            'ps_number': 10, 'ps_name': 11, 'ps_location': 12, 'ps_address': 13,
            'registered': 14, 'cast': 15, 'valid': 17, 'invalid': 18,
        },
    },
}


class EUParliamentImporter(BaseImporter):
    """Import EU Parliament election results.

    File format: windows-1250 encoded, semicolon-delimited. Header is row 1.
    Geography block sits at the front, then groups of `1 list-name + N
    candidate-names` columns. Per-year shape (column offsets, candidate count,
    file path) lives in `YEAR_CONFIG` — adding a new election year means
    adding a new entry there. Coalition names may contain literal newlines.
    """

    BASE_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_eu_parlamet_2024')

    def __init__(self, year=2024, stdout=None):
        super().__init__(stdout=stdout)
        if year not in YEAR_CONFIG:
            raise ValueError(f'No YEAR_CONFIG entry for {year}')
        self.year = year
        self.cfg = YEAR_CONFIG[year]
        self.candidates_per_list = self.cfg['candidates_per_list']
        self.cols_per_list = self.candidates_per_list + 1
        self.geo_cols = self.cfg['geo_cols']
        self.cidx = self.cfg['col']

    def run(self):
        election_type = self.get_or_create_election_type('eu_parliament', 'Izbori za Europski parlament')
        election = self.get_or_create_election(election_type, self.year, f'Izbori za Europski parlament {self.year}')
        election_round = self.get_or_create_round(election, 1)

        filepath = self.BASE_DIR / self.cfg['rel_path']
        if not filepath.exists():
            self.log(f"File not found: {filepath}")
            return

        # Parse header
        with open(filepath, encoding=self.cfg['encoding']) as f:
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
        c = self.cidx
        with open(filepath, encoding=self.cfg['encoding']) as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)  # skip header

            row_count = 0
            for row in reader:
                if len(row) < self.geo_cols:
                    continue

                county_code = row[c['county_code']].strip()
                county_name = row[c['county_name']].strip()
                muni_type = row[c['muni_type']].strip()
                muni_name = row[c['muni_name']].strip()
                ps_number = row[c['ps_number']].strip()
                ps_name = row[c['ps_name']].strip()
                ps_location = row[c['ps_location']].strip()
                ps_address = row[c['ps_address']].strip()

                registered = self.parse_int(row[c['registered']])
                cast = self.parse_int(row[c['cast']])
                valid = self.parse_int(row[c['valid']])
                invalid = self.parse_int(row[c['invalid']])

                county = self.get_or_create_county(county_code, county_name)
                municipality = self.get_or_create_municipality(county, muni_name, muni_type)
                polling_station = self.get_or_create_polling_station(
                    municipality, ps_number, ps_name, ps_location, ps_address
                )

                self.create_turnout(election_round, polling_station, registered, cast, valid, invalid)

                col = self.geo_cols
                for el_list, candidacies in list_data:
                    list_votes = self.parse_int(row[col]) if col < len(row) else 0
                    self.create_list_result(el_list, polling_station, list_votes)

                    for i, candidacy in enumerate(candidacies):
                        cand_col = col + 1 + i
                        votes = self.parse_int(row[cand_col]) if cand_col < len(row) else 0
                        self.create_candidate_result(candidacy, polling_station, votes)

                    col += self.cols_per_list

                row_count += 1

        self.flush_all()
        self.log(f"Imported {row_count} polling station rows")

    def _parse_list_groups(self, header):
        """Parse header into groups of (list_name, [candidate_names]). Each
        candidate name passes through `clean_candidate_name` so academic
        titles like "mr.sc. " / ", dipl.iur." (common in 2014 CSVs) don't
        end up as part of the Person record's stored name — that previously
        produced duplicates like "MR.SC. ANDREJ PLENKOVIC" alongside the
        cleanly-named "ANDREJ PLENKOVIC" from later years.
        """
        groups = []
        col = self.geo_cols
        while col + self.cols_per_list <= len(header):
            list_name = header[col].strip()
            candidates = [
                clean_candidate_name(header[col + 1 + i])
                for i in range(self.candidates_per_list)
            ]
            groups.append((list_name, candidates))
            col += self.cols_per_list
        return groups
