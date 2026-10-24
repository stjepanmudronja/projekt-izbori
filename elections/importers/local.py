import hashlib
import openpyxl
from pathlib import Path
from .base import BaseImporter
from .name_utils import clean_candidate_name


# Map sheet names to election type slugs. Keys are normalised by
# `classify_sheet`, which folds the 2021 spellings onto 2025's.
SHEET_TYPE_MAP = {
    'općinsko vijeće': ('local_municipal_council', 'Općinsko vijeće', True),
    'načelnik': ('local_mayor', 'Načelnik', False),
    'gradsko vijeće': ('local_city_council', 'Gradsko vijeće', True),
    'gradonačelnik': ('local_city_mayor', 'Gradonačelnik', False),
    'županijska skupština': ('local_county_assembly', 'Županijska skupština', True),
    'župan': ('local_county_prefect', 'Župan', False),
    'skupština grada zagreba': ('local_city_council', 'Gradsko vijeće', True),
    'gradonačelnik grada zagreba': ('local_city_mayor', 'Gradonačelnik', False),
}

# Partial match for zamjenik sheets
ZAMJENIK_PATTERNS = [
    ('zamjenik načelnika', 'local_deputy_mayor', 'Zamjenik načelnika', False),
    ('zamjenik gradonačelnika', 'local_deputy_city_mayor', 'Zamjenik gradonačelnika', False),
    ('zamjenik župana', 'local_deputy_county_prefect', 'Zamjenik župana', False),
]

# Executive offices of a whole county; every other candidate race is one
# municipality's.
COUNTY_LEVEL = {'local_county_prefect', 'local_deputy_county_prefect'}

GEO_COLS = 13  # columns 0-12

# Per-year source layout: round number -> folder under the year's directory.
# 2021 also ships CSV copies of every workbook, which are not read; its third
# round is the single repeat mayoral vote in Kraljevec na Sutli (13 June 2021),
# held because no candidate of the three in its round-2 runoff won a majority.
# 2017 shares 2021's layout; its round-2 Zagreb folder holds the city workbook
# twice (Excel/21.xlsx and ZUP_21/21.xlsx, byte-identical), so files are
# de-duplicated by content.
YEAR_ROUNDS = {
    2025: {1: 'krug-1', 2: 'krug-2'},
    2017: {1: 'rezultati1krug', 2: 'rezultati2krug'},
    2021: {1: '1_krug_rezultati', 2: '2_krug_rezultati', 3: '3_krug_rezultati'},
}


def classify_sheet(sheet_name):
    """Return (slug, display_name, is_list_election) for a sheet name.

    2021 names the sheets differently from 2025 — "općinska vijeće" (sic),
    "župani", and plural "zamjenici … iz redova" — so they are folded onto the
    2025 spelling first.
    """
    lower = ' '.join(sheet_name.lower().split())
    lower = (lower.replace('općinska vijeće', 'općinsko vijeće')
                  .replace('zamjenici ', 'zamjenik '))
    if lower == 'župani':
        lower = 'župan'
    if lower in SHEET_TYPE_MAP:
        return SHEET_TYPE_MAP[lower]
    for prefix, slug, name, is_list in ZAMJENIK_PATTERNS:
        if lower.startswith(prefix):
            return (slug, name, is_list)
    return None


class LocalImporter(BaseImporter):
    """Import local election results from Excel files.

    Each file has 2-4 sheets, each sheet is a different election subtype. The
    header row is the one starting "Rbr.županije" — 2025 puts a title row
    above it, 2021 does not.

    For council elections (vijeće/skupština): columns from 13 onward are list names.
    For executive elections (načelnik/gradonačelnik/župan): columns from 13 are
    candidate names, and each candidate's list is scoped to its municipality
    (county, for župan) through an ElectoralDistrict. Without that, every
    candidate of one name in a round shared one list and one Candidacy — two
    Milan Kneževićs ran for načelnik in different municipalities in 2025.
    Council lists stay shared across municipalities; results are per station,
    so every view scopes them by station anyway.
    """

    DATA_DIR = Path('/Users/stjepanmudronja/Documents/projekt_izbori/files/Rezultati_lokalni_izbori_2025')

    def __init__(self, year=2025, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year

    def run(self):
        for round_num, round_dir in YEAR_ROUNDS[self.year].items():
            round_path = self.DATA_DIR / str(self.year) / round_dir
            if not round_path.exists():
                continue
            self.log(f"Importing local elections {self.year} round {round_num}...")
            # "~$…" files are Excel lock files left beside an open workbook.
            files, seen = [], set()
            for p in sorted(round_path.rglob('*.xlsx')):
                if p.name.startswith('~$'):
                    continue
                digest = hashlib.md5(p.read_bytes()).hexdigest()
                if digest in seen:
                    self.log(f"  Skipping {p.relative_to(round_path)}: duplicate of an earlier file")
                    continue
                seen.add(digest)
                files.append(p)
            self.log(f"  Found {len(files)} files")
            for i, filepath in enumerate(files):
                self._import_file(filepath, round_num)
                if (i + 1) % 50 == 0:
                    self.log(f"  Processed {i + 1}/{len(files)} files")
            self.log(f"  Round {round_num} complete: {len(files)} files")

    def _import_file(self, filepath, round_num):
        try:
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        except Exception as e:
            self.log(f"  ERROR opening {filepath.name}: {e}")
            return

        for sheet_name in wb.sheetnames:
            info = classify_sheet(sheet_name)
            if info is None:
                self.log(f"  Unknown sheet type '{sheet_name}' in {filepath.name}, skipping")
                continue

            slug, display_name, is_list_election = info
            ws = wb[sheet_name]
            self._import_sheet(ws, filepath, round_num, slug, display_name, is_list_election)

        # Once per file, not per sheet: a file holding two minorities' deputy
        # elections (Serb and Italian zamjenik župana, say) reports the same
        # stations twice, each with that minority's own electorate. Buffered,
        # the two add up; flushed in between, the second upsert overwrote the
        # first, and list votes came out above valid ballots.
        self.flush_all()
        wb.close()

    def _import_sheet(self, ws, filepath, round_num, slug, display_name, is_list_election):
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        header_at = next((i for i, r in enumerate(rows[:5])
                          if r and str(r[0] or '').strip().startswith('Rbr')), None)
        if header_at is None:
            self.log(f"  No header row in '{ws.title}' of {filepath.name}, skipping")
            return
        header = rows[header_at]
        data = [r for r in rows[header_at + 1:] if len(r) >= GEO_COLS and r[0] is not None]
        if not data:
            return

        election_type = self.get_or_create_election_type(slug, display_name, parent_slug='local')
        election = self.get_or_create_election(election_type, self.year, f'{display_name} {self.year}')
        election_round = self.get_or_create_round(election, round_num)

        # Get list/candidate names from column 13 onward
        entry_names = []
        for i in range(GEO_COLS, len(header)):
            name = header[i]
            if name is not None:
                name = str(name).strip()
                if name:
                    entry_names.append((i, name))

        if not entry_names:
            return

        district = None
        if not is_list_election:
            district = self._race_district(election, slug, data[0])

        # Create electoral lists (and candidacies for executive elections)
        list_data = []
        for col_idx, name in entry_names:
            el_list = self.get_or_create_electoral_list(election_round, name, district)
            candidacy = None
            if not is_list_election:
                # Executive election: each entry is a candidate
                person = self.get_or_create_person(clean_candidate_name(name))
                candidacy = self.get_or_create_candidacy(person, el_list, 1)
            list_data.append((col_idx, el_list, candidacy))

        for row in data:
            polling_station = self._station(row)
            registered = self.parse_int(row[8])
            cast = self.parse_int(row[9])
            valid = self.parse_int(row[11])
            invalid = self.parse_int(row[12])

            self.create_turnout(election_round, polling_station, registered, cast, valid, invalid)

            for col_idx, el_list, candidacy in list_data:
                votes = self.parse_int(row[col_idx]) if col_idx < len(row) else 0
                self.create_list_result(el_list, polling_station, votes)
                if candidacy:
                    self.create_candidate_result(candidacy, polling_station, votes)

    def _geo(self, row):
        county = self.get_or_create_county(str(row[0]).strip(), str(row[1] or '').strip())
        municipality = self.get_or_create_municipality(
            county, str(row[3] or '').strip(), str(row[2] or '').strip())
        return county, municipality

    def _station(self, row):
        _county, municipality = self._geo(row)
        return self.get_or_create_polling_station(
            municipality,
            str(row[4] or '').strip(), str(row[5] or '').strip(),
            str(row[6] or '').strip(), str(row[7] or '').strip(),
        )

    def _race_district(self, election, slug, row):
        """The municipality (or county) a candidate race belongs to, as a
        district of its election, numbered by that row's primary key."""
        county, municipality = self._geo(row)
        if slug in COUNTY_LEVEL:
            return self.get_or_create_district(election, county.pk, county.name)
        return self.get_or_create_district(election, municipality.pk, municipality.name)
