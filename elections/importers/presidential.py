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

# Layout used by 2005 / 2009: only 8 geography columns, no muni-type / station
# name / station location / station address. Candidates start at 8.
LAYOUT_2009 = {
    'county_code': 0, 'county_name': 1,
    'muni_type': None, 'muni_name': 2,
    'ps_number': 3, 'ps_name': None, 'ps_location': None, 'ps_address': None,
    'registered': 4, 'cast': 5, 'valid': 6, 'invalid': 7,
    'first_candidate': 8,
}

# 2000 RH (homeland) layout: no county CODE, only county NAME; muni_type
# (GRAD / OPĆINA) and muni_name in separate columns.
LAYOUT_2000_RH = {
    'county_code': None, 'county_name': 0,
    'muni_type': 1, 'muni_name': 2,
    'ps_number': 3, 'ps_name': None, 'ps_location': None, 'ps_address': None,
    'registered': 4, 'cast': 5, 'valid': 6, 'invalid': 7,
    'first_candidate': 8,
}

# 2000 inozemstvo layout: one row per country (no BM number), aggregated.
# Used together with county_override='inozemstvo' and synthetic ps_number.
LAYOUT_2000_INO = {
    'county_code': None, 'county_name': None,
    'muni_type': None, 'muni_name': 0,
    'ps_number': None, 'ps_name': None, 'ps_location': None, 'ps_address': None,
    'registered': 1, 'cast': 2, 'valid': 3, 'invalid': 4,
    'first_candidate': 5,
}


class PresidentialImporter(BaseImporter):
    """Import presidential election results from CSV files.

    File format: semicolon-delimited, optionally with a leading title row.
    Round 1 typically has interleaved ``%`` / ``(%)`` columns; round 2 may or
    may not. Each year may differ in encoding, title-row count, and column
    layout. From 2000 onward DIP's CSV exports converged to one file per
    round; older formats split RH and inozemstvo into separate files, hence
    `file_specs` (a list of {filename, layout, county_override} per round).
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
        2000: {
            'dir': BASE_DIR / '2000' / 'CSV',
            'encoding': 'windows-1250',
            'title_rows': 0,
            'name': 'Predsjednički izbori 2000',
            # 2000 splits RH and inozemstvo into separate files per round and
            # has no county code (county is named outright); inozemstvo rows
            # are aggregated per country (no BM number) so we synthesize one.
            'file_specs': {
                1: [
                    {'filename': 'Predsjednik 2000 po BM - 1. krug_Prvi krug RH.csv',
                     'layout': LAYOUT_2000_RH},
                    {'filename': 'Predsjednik 2000 po BM - 1. krug_Prvi krug inozemstvo.csv',
                     'layout': LAYOUT_2000_INO, 'county_override': 'inozemstvo'},
                ],
                2: [
                    {'filename': 'Predsjednik 2000 po BM - 2. krug_Drugi krug RH.csv',
                     'layout': LAYOUT_2000_RH},
                    {'filename': 'Predsjednik 2000 po BM - 2. krug_Drugi krug inozemstvo.csv',
                     'layout': LAYOUT_2000_INO, 'county_override': 'inozemstvo'},
                ],
            },
            'county_lookup_by_name': True,
        },
    }

    def __init__(self, stdout=None, years=None):
        super().__init__(stdout=stdout)
        self.years = years if years else list(self.YEARS.keys())
        self._county_by_normalized_name = None

    def run(self):
        election_type = self.get_or_create_election_type('presidential', 'Predsjednički izbori')

        for year in self.years:
            cfg = self.YEARS.get(year)
            if not cfg:
                self.log(f"Unknown year {year}, skipping (configured: {list(self.YEARS)})")
                continue
            election = self.get_or_create_election(election_type, year, cfg['name'])
            for round_num, specs in self._round_specs(cfg).items():
                round_obj = self.get_or_create_round(election, round_num)
                for spec in specs:
                    filepath = cfg['dir'] / spec['filename']
                    if not filepath.exists():
                        self.log(f"File not found: {filepath}, skipping")
                        continue
                    self.log(f"Importing presidential {year} round {round_num} from {spec['filename']}...")
                    self._import_file(round_obj, filepath, cfg, spec)

        self.flush_all()

    @staticmethod
    def _round_specs(cfg):
        """Normalize either `files` (filename per round) or `file_specs` (list)."""
        if 'file_specs' in cfg:
            return cfg['file_specs']
        return {rn: [{'filename': fn, 'layout': cfg['layout']}]
                for rn, fn in cfg.get('files', {}).items()}

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
        return self.get_or_create_county(fallback_code, name)

    def _import_file(self, election_round, filepath, cfg, spec):
        encoding = cfg['encoding']
        title_rows = cfg['title_rows']
        layout = spec['layout']
        county_override = spec.get('county_override')
        first_cand = layout['first_candidate']

        with open(filepath, encoding=encoding) as f:
            reader = csv.reader(f, delimiter=';')
            for _ in range(title_rows):
                next(reader)
            header = next(reader)

        def is_pct_header(h):
            s = (h or '').strip()
            return s == '%' or s == '(%)'

        candidate_names = []
        has_pct_cols = any(is_pct_header(h) for h in header[first_cand:])
        col = first_cand
        while col < len(header):
            name = clean_candidate_name(header[col])
            if name and not is_pct_header(name):
                # Uppercase to keep Person.normalized_name lookups consistent
                # across years that ship mixed-case (2000, 2005) vs all-caps
                # (2009+) headers.
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
            override_county_obj = None
            for row in reader:
                if len(row) < min_cols:
                    continue

                muni_name_col = layout.get('muni_name')
                muni_name = row[muni_name_col].strip() if muni_name_col is not None else ''
                if not muni_name:
                    continue

                county_code = row[layout['county_code']].strip() if layout['county_code'] is not None else ''
                county_name = row[layout['county_name']].strip() if layout['county_name'] is not None else ''

                if county_override is not None:
                    if override_county_obj is None:
                        override_county_obj = self._resolve_county_by_name(county_override, '00')
                    county = override_county_obj
                elif cfg.get('county_lookup_by_name'):
                    if not county_name:
                        continue
                    county = self._resolve_county_by_name(county_name, county_code)
                else:
                    if not county_code:
                        continue
                    county = self.get_or_create_county(county_code, county_name)

                muni_type = row[layout['muni_type']].strip() if layout['muni_type'] is not None else ''
                # 2000 inozemstvo (one row per country, aggregated): no BM
                # number — synthesize a single station per country.
                ps_number = (row[layout['ps_number']].strip()
                             if layout['ps_number'] is not None else '001')
                if not ps_number:
                    continue
                ps_name = row[layout['ps_name']].strip() if layout['ps_name'] is not None else ''
                ps_location = row[layout['ps_location']].strip() if layout['ps_location'] is not None else ''
                ps_address = row[layout['ps_address']].strip() if layout['ps_address'] is not None else ''

                registered = self.parse_int(row[layout['registered']])
                cast = self.parse_int(row[layout['cast']])
                valid = self.parse_int(row[layout['valid']])
                invalid = self.parse_int(row[layout['invalid']])

                # Default muni type for inozemstvo countries.
                if county_override == 'inozemstvo' and not muni_type:
                    muni_type = 'država'

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
        self.log(f"  Imported {row_count} polling station rows")
