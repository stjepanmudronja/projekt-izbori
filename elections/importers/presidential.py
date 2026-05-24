import csv
from pathlib import Path
from .base import BaseImporter
from .name_utils import clean_candidate_name, strip_diacritics


# Layout used by 2014/2019/2024: 13 geography columns (0-12), candidates start at 13.
LAYOUT_STANDARD = {
    'county_code': 0, 'county_name': 1,
    'muni_type': 2, 'muni_name': 3,
    'ps_number': 4, 'ps_name': 5, 'ps_location': 6, 'ps_address': 7,
    'registered': 8, 'cast': 9, 'valid': 11, 'invalid': 12,
    'first_candidate': 13,
}

# Layout used by 2009: only 8 geography columns, no muni-type / station name /
# station location / station address. Candidates start at 8.
LAYOUT_2009 = {
    'county_code': 0, 'county_name': 1,
    'muni_type': None, 'muni_name': 2,
    'ps_number': 3, 'ps_name': None, 'ps_location': None, 'ps_address': None,
    'registered': 4, 'cast': 5, 'valid': 6, 'invalid': 7,
    'first_candidate': 8,
}


class PresidentialImporter(BaseImporter):
    """Import presidential election results from CSV files.

    File format: semicolon-delimited, optionally with a leading title row.
    Round 1 typically has interleaved ``%`` / ``(%)`` columns; round 2 may or
    may not. Each year may differ in encoding, title-row count, and column
    layout (the 2009 files use a stripped-down 8-column geography section,
    everyone else uses the 13-column standard).
    """

    BASE_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_predsjednicki_izbori_2024')

    YEARS = {
        2024: {
            'dir': BASE_DIR,
            'encoding': 'utf-8-sig',
            'title_rows': 1,
            'name': 'Predsjednički izbori 2024',
            'files': {1: 'rezultati_1krug.csv', 2: 'rezultati_2krug.csv'},
            'layout': LAYOUT_STANDARD,
            'county_lookup_by_name': False,
        },
        2019: {
            'dir': BASE_DIR / '2019',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2019',
            'files': {1: 'rezultati_bm(1).csv', 2: 'rezultati_bm(2).csv'},
            'layout': LAYOUT_STANDARD,
            'county_lookup_by_name': False,
        },
        2014: {
            'dir': BASE_DIR / '2014',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2014',
            'files': {
                1: '1_krug/2014_Predsjednik_1_krug_rezultati_po_birackim_mjestima_rezultati.csv',
                2: '2_krug/2014_Predsjednik_2_krug_rezultati_po_birackim_mjestima_rezultati.csv',
            },
            'layout': LAYOUT_STANDARD,
            'county_lookup_by_name': False,
        },
        2009: {
            'dir': BASE_DIR / '2009',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2009',
            'files': {
                1: '1_krug/rezultati_po_bm_1krug_RH.csv',
                2: '2_krug/rezultati_po_bm_2krug_Rezultati.csv',
            },
            'layout': LAYOUT_2009,
            # 2009's župan-codes are unreliable (e.g. some Karlovačka rows
            # carry code 3 instead of 4). Match by county name and fall back
            # to the file's code only if no name match exists.
            'county_lookup_by_name': True,
        },
        2005: {
            'dir': BASE_DIR / '2005' / 'CSV',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2005',
            'files': {
                1: 'Rezultati_po_BM_-_1krug.csv',
                2: 'Rezultati_po_BM_-_2krug.csv',
            },
            # Same 8-column geography section as 2009; the difference is that
            # 2005 omits the `%` columns entirely (one column per candidate).
            'layout': LAYOUT_2009,
            'county_lookup_by_name': False,
        },
    }

    def __init__(self, stdout=None, years=None):
        super().__init__(stdout=stdout)
        self.years = years if years else list(self.YEARS.keys())
        # Built lazily on first by-name lookup.
        self._county_by_normalized_name = None

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
                self._import_round(election, round_num, filepath, cfg)

        self.flush_all()

    @staticmethod
    def _normalize_county_name(raw):
        """Normalize a county name for cross-year lookup."""
        s = (raw or '').strip().upper()
        s = strip_diacritics(s)
        # Drop the "ŽUPANIJA" suffix that some files include and others omit
        # (e.g. "ZAGREBAČKA" vs "ZAGREBAČKA ŽUPANIJA").
        s = s.replace('ZUPANIJA', '').strip()
        return ' '.join(s.split())

    def _resolve_county_by_name(self, name, fallback_code):
        """Look up an existing County row by name; fall back to code-based create."""
        from elections.models import County
        if self._county_by_normalized_name is None:
            self._county_by_normalized_name = {
                self._normalize_county_name(c.name): c
                for c in County.objects.all()
            }
        norm = self._normalize_county_name(name)
        cached = self._county_by_normalized_name.get(norm)
        if cached:
            self._county_cache[cached.code] = cached
            return cached
        # Unknown name — fall back to the standard code-based path (which will
        # create a new County row keyed on the file's code).
        return self.get_or_create_county(fallback_code, name)

    def _import_round(self, election, round_num, filepath, cfg):
        election_round = self.get_or_create_round(election, round_num)
        encoding = cfg['encoding']
        title_rows = cfg['title_rows']
        layout = cfg['layout']
        first_cand = layout['first_candidate']

        with open(filepath, encoding=encoding) as f:
            reader = csv.reader(f, delimiter=';')
            for _ in range(title_rows):
                next(reader)
            header = next(reader)

        # 2009 uses "%" as the percent-column header; later years use "(%)".
        def is_pct_header(h):
            s = (h or '').strip()
            return s == '%' or s == '(%)'

        candidate_names = []
        has_pct_cols = any(is_pct_header(h) for h in header[first_cand:])
        col = first_cand
        while col < len(header):
            name = clean_candidate_name(header[col])
            if name and not is_pct_header(name):
                # Uppercase to match the convention used by other years (the
                # 2005 file is the odd one out with mixed-case names; this
                # also keeps Person.normalized_name lookups consistent).
                candidate_names.append((col, name.upper()))
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
            min_cols = first_cand
            for row in reader:
                if len(row) < min_cols:
                    continue

                county_code = row[layout['county_code']].strip()
                county_name = row[layout['county_name']].strip()
                muni_name = row[layout['muni_name']].strip()
                ps_number = row[layout['ps_number']].strip()
                # Skip rows without basic geography (occasional blank rows).
                if not county_name or not muni_name or not ps_number:
                    continue

                muni_type = row[layout['muni_type']].strip() if layout['muni_type'] is not None else ''
                ps_name = row[layout['ps_name']].strip() if layout['ps_name'] is not None else ''
                ps_location = row[layout['ps_location']].strip() if layout['ps_location'] is not None else ''
                ps_address = row[layout['ps_address']].strip() if layout['ps_address'] is not None else ''

                registered = self.parse_int(row[layout['registered']])
                cast = self.parse_int(row[layout['cast']])
                valid = self.parse_int(row[layout['valid']])
                invalid = self.parse_int(row[layout['invalid']])

                if cfg.get('county_lookup_by_name'):
                    county = self._resolve_county_by_name(county_name, county_code)
                else:
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
