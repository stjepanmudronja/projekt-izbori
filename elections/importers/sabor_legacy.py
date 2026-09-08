"""Import the pre-preferential Sabor elections (2007 and 2011).

Both years predate preferential voting, so DIP published a different export
than 2015 onward and `sabor.py` cannot read either of them:

  * **No candidate columns.** Districts I-XI carry one column per list and
    nothing else, so those districts produce ListResult rows only. Only
    district XII (minorities) names individuals, one column per candidate.
  * **No county columns.** 2015+ files carry `Rbr.županije` / `Županija`;
    these years give only the town/municipality name, so the county has to be
    recovered by matching that name against municipalities already imported
    from other years (see `_resolve_municipality`).
  * **Geo width varies per file type** rather than being a fixed 15, so the
    header is measured at read time instead of hard-coded.
  * **Verbose filenames**, e.g. `01_I_izborna_jedinica_REDOVITA_BM.csv`, and
    an extra `rezultati/` directory level.

Files per district (windows-1250, semicolon-delimited); 2007 and 2011 ship the
same set under different spellings, so everything matched on a filename here is
matched case-insensitively:

    ..._REDOVITA_BM / ..._Redovita_BM         regular stations
    ..._POSEBNA_BM / ..._Posebna_BM           mobile/special stations
    ..._BM_INOZEMSTVO / ..._BM_u_inozemstvu   embassy stations for that district
    ..._Gradovi-opcine                        PER-MUNICIPALITY AGGREGATE - skipped

District XI adds the diaspora-voting-inside-Croatia file (`DIJASPORA_U_RH` in
2011, `BM_u_RH` in 2007) and a per-country aggregate (`DRZAVE` / `Drzave`) that
is likewise skipped. Importing either aggregate would double-count every vote in
the district — 2007 makes that trap easy to fall into, since one of its files is
misspelled `Grdovi-opcine`, which is why aggregates are also rejected
structurally on their header (see `_is_aggregate`).

The 2007 header block is its own dialect: seven leading columns naming the
station only by `Redni broj biračkog mjesta` (no name/location/address at all,
so those stay blank unless a later year's import fills them in), and district
XII prefixing it with a bare `Izborna jedinica`. `_parse_header` accepts either
year's labels.
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from .base import BaseImporter
from .name_utils import clean_candidate_name, normalize_municipality_name


# Header labels that mark the municipality/country column. DIP is inconsistent
# about case and singular/plural across districts (district VII alone uses
# "Grad / Općine" with a capital O).
_MUNI_HEADERS = {'grad / općine', 'grad / općina', 'grad/općine', 'grad/općina'}
_FOREIGN_HEADERS = {'država'}

# The per-municipality / per-country aggregates count a whole town in one row
# and head that row's station column "Broj biračkih mjesta" (how many stations
# it covers) where a real station file says "Redni broj biračkog mjesta". That
# difference is the reliable aggregate tell — 2007 ships one of them misspelled
# (`04_IV_..._Grdovi-opcine.csv`), so a filename check alone would let it
# through and double-count district IV.
_STATION_NUMBER_HEADERS = ('bm rbr', 'redni broj biračkog mjesta')
_AGGREGATE_NUMBER_HEADER = 'broj biračkih mjesta'

# 2007 appends per-district subtotals to the bottom of every station file
# ("POSEBNA BM ZA I. IJ", "UKUPNO ZA I. IJ", a bare "UKUPNO"). They are rows in
# the same shape as a real station and would double-count the district if let
# through — no municipality is called UKUPNO or ends in a bare "IJ".
_SUMMARY_ROW_RE = re.compile(r'^UKUPNO\b|\bIJ\.?$', re.IGNORECASE)

# "OTOK (VINKOVCI)": 2007 tells repeated place names apart by naming a nearby
# town in brackets. Every other year stores the plain name, so the bracketed
# hint is resolved to its own municipality and used as a county filter.
_PAREN_HINT_RE = re.compile(r'^(.*?)\s*\(([^)]+)\)\s*$')

# ", Nositelj liste: IME PREZIME" is appended to every list name. Dropping it
# keeps the stored list name comparable with the other years, which matters for
# the coalition grouping that keys on the text before the first comma.
_NOSITELJ_SPLIT_RE = re.compile(r'\s*,?\s*Nositelj\s+liste\s*:\s*',
                                re.IGNORECASE | re.DOTALL)

# District XII columns read "Kandidat: X, Zamjenik: Y, Predlagatelj: Z" — only
# the candidate is the person standing.
_KANDIDAT_RE = re.compile(
    r'^\s*Kandidat\s*:\s*(.*?)\s*(?:,\s*(?:Zamjenik|Predlagatelj)\s*:.*)?$',
    re.IGNORECASE | re.DOTALL)


class SaborLegacyImporter(BaseImporter):
    BASE_DIR = Path(
        '/Users/stjepanmudronja/Documents/projekt_izbori/files/rezultati_sabor_2024'
    )
    YEARS = (2007, 2011)

    # nm-suffix in the filename -> (sub-district number, seats, name).
    # Same numbering as sabor.py so a minority seat lines up across years.
    MINORITY_SUBDISTRICTS = {
        'nm1': (121, 3, 'XII. IJ - Srpska nacionalna manjina'),
        'nm2': (122, 1, 'XII. IJ - Mađarska nacionalna manjina'),
        'nm3': (123, 1, 'XII. IJ - Talijanska nacionalna manjina'),
        'nm4': (124, 1, 'XII. IJ - Češka i slovačka nacionalna manjina'),
        'nm5': (125, 1, 'XII. IJ - Romska, rusinska, ukrajinska i dr.'),
        'nm6': (126, 1, 'XII. IJ - Albanska, bošnjačka, crnogorska i dr.'),
    }

    def __init__(self, year=2011, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year
        self.data_dir = self.BASE_DIR / str(year) / 'rezultati' / 'CSV'
        self._muni_index = None
        self._district_counties = None
        self._unresolved = defaultdict(int)

    # ---- entry point -------------------------------------------------

    def run(self, only_district=None):
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(
            election_type, self.year, f'Parlamentarni izbori {self.year}')
        election_round = self.get_or_create_round(election, 1)

        self._build_muni_index()

        for district_num in range(1, 12):
            if only_district is not None and district_num != only_district:
                continue
            self._import_district(election, election_round, district_num)

        if only_district is None or only_district == 12:
            self._import_district_12(election, election_round)

        self.flush_all()
        if self._unresolved:
            self.log('Municipality names that could not be resolved to a county:')
            for name, n in sorted(self._unresolved.items(), key=lambda kv: -kv[1]):
                self.log(f'  {name!r} ({n} rows)')

    # ---- geography ---------------------------------------------------

    def _build_muni_index(self):
        """Index existing municipalities by normalized name.

        These years have no county column, so the county is recovered from
        municipalities already imported by other election years. Croatia has a
        handful of repeated place names (OTOK, PRIVLAKA, SVETA NEDELJA), which
        is why the index keeps every match and `_resolve_municipality` breaks
        ties using the electoral district.
        """
        from elections.models import Municipality
        self._muni_index = defaultdict(list)
        for m in Municipality.objects.select_related('county').all():
            self._muni_index[self._muni_key(m.name)].append(m)

        # district number -> set of county ids, learned from the years that do
        # record the county. Used only to disambiguate repeated place names.
        from elections.models import ElectoralList, ListResult
        self._district_counties = defaultdict(set)
        # Main stations only. Mobile and embassy stations carry a letter
        # prefix on their number (see `_station_prefix`) and sit anywhere in
        # the country regardless of the district whose file lists them, so
        # counting them makes every district look like all 22 counties and the
        # tie-break stops narrowing anything.
        rows = (ListResult.objects
                .filter(electoral_list__election_round__election__election_type__slug='sabor',
                        electoral_list__district__number__lte=11)
                .exclude(polling_station__number__regex=r'^[A-Z]')
                # ...and only from the years that record the county. A legacy
                # year resolved by this very map would otherwise teach it its
                # own guesses: 2011 put OTOK in district IX under Vukovar-
                # Srijem, which then made district IX look like it contains
                # both OTOKs and left the name ambiguous forever.
                .exclude(electoral_list__election_round__election__year__in=self.YEARS)
                .values_list('electoral_list__district__number',
                             'polling_station__municipality__county_id')
                .distinct())
        for dnum, cid in rows:
            if dnum and cid:
                self._district_counties[dnum].add(cid)
        self.log(f'Indexed {len(self._muni_index)} municipality names for county lookup')

    @staticmethod
    def _muni_key(name):
        """Normalized key. Extends the shared helper by also collapsing space
        around commas, since 2011 writes "ZAGREB-CENTAR,ZAPAD" where other
        years write "ZAGREB-CENTAR, ZAPAD"."""
        return normalize_municipality_name((name or '').replace(',', ', '))

    def _resolve_municipality(self, raw_name, district_num, is_foreign):
        if is_foreign:
            county = self.get_or_create_county('00', 'inozemstvo')
            return self.get_or_create_municipality(county, raw_name, 'država')

        key = self._muni_key(raw_name)
        matches = self._muni_index.get(key, []) or self._match_bracketed(raw_name)

        if len(matches) > 1 and district_num:
            # Repeated place name: keep only the ones whose county actually
            # votes in this district.
            allowed = self._district_counties.get(district_num, set())
            narrowed = [m for m in matches if m.county_id in allowed]
            if narrowed:
                matches = narrowed

        if not matches:
            # 2011 truncates a couple of long bilingual names
            # ("KAŠTELIR-LABINCI - CASTELLIERE-S. D"), so fall back to a unique
            # prefix match before giving up.
            pref = [ms for k, ms in self._muni_index.items() if k.startswith(key)]
            flat = [m for ms in pref for m in ms]
            if len(flat) == 1:
                matches = flat

        if not matches:
            self._unresolved[raw_name] += 1
            return None
        return matches[0]

    def _match_bracketed(self, raw_name):
        """Resolve "OTOK (VINKOVCI)" — base name, county taken from the town
        named in brackets. Empty list when the name has no brackets or the hint
        does not pin down a county."""
        m = _PAREN_HINT_RE.match((raw_name or '').strip())
        if not m:
            return []
        base, hint = m.group(1), m.group(2)
        counties = {h.county_id
                    for h in self._muni_index.get(self._muni_key(hint), [])}
        return [c for c in self._muni_index.get(self._muni_key(base), [])
                if c.county_id in counties]

    @staticmethod
    def _is_summary_row(raw_name):
        """True for 2007's per-district subtotal rows (see _SUMMARY_ROW_RE)."""
        return bool(_SUMMARY_ROW_RE.search((raw_name or '').strip()))

    # ---- file discovery ----------------------------------------------

    def _files_for(self, prefix):
        """Result files for a district prefix, aggregates excluded."""
        out = []
        for fp in sorted(self.data_dir.glob(f'{prefix}_*.csv')):
            name = fp.name.lower()
            # per-municipality / per-country totals; would double-count.
            # "opcine" also catches 2007's misspelled "Grdovi-opcine".
            if 'opcine' in name or 'drzave' in name:
                continue
            out.append(fp)
        return out

    @staticmethod
    def _is_main_file(filepath):
        """The regular-stations file — widest roster, always present."""
        return 'redovita' in filepath.name.lower()

    @staticmethod
    def _station_prefix(filepath):
        """Keep same-numbered stations from different file types apart, the way
        sabor.py does for the later years."""
        n = filepath.name.lower()
        if 'posebna' in n:
            return 'P'
        # BM_INOZEMSTVO (2011) / BM_u_inozemstvu (2007) — the stem is all the
        # two spellings share.
        if 'inozemst' in n:
            return 'I'
        # diaspora voting inside Croatia: DIJASPORA_U_RH (2011) / BM_u_RH (2007)
        if 'dijaspora_u_rh' in n or 'bm_u_rh' in n:
            return 'D'
        return ''

    # ---- header parsing ----------------------------------------------

    def _parse_header(self, header):
        """Measure one file's geo block and locate the columns we need.

        Returns a dict of column indices plus `first_result`, the first column
        holding votes. Widths differ per file type (8, 11 or 12 leading
        columns), so nothing here may be hard-coded.
        """
        low = [(h or '').strip().lower() for h in header]

        def find(*labels):
            for lab in labels:
                if lab in low:
                    return low.index(lab)
            return None

        invalid = find('listići nevažeći')
        if invalid is None or self._is_aggregate(low):
            return None
        muni = next((i for i, h in enumerate(low) if h in _MUNI_HEADERS), None)
        foreign_col = next((i for i, h in enumerate(low) if h in _FOREIGN_HEADERS), None)
        if muni is None and foreign_col is None:
            return None
        return {
            'muni': muni if muni is not None else foreign_col,
            'is_foreign': muni is None,
            # 2011 spells the minority files' home-district column
            # "Izborna jedinica grada / općine"; 2007 just "Izborna jedinica".
            'home_district': find('izborna jedinica grada / općine',
                                  'izborna jedinica'),
            'number': find(*_STATION_NUMBER_HEADERS),
            'name': find('bm naziv'),
            'location': find('bm lokacija'),
            'address': find('bm adresa'),
            'registered': find('ukupno birača'),
            'cast': find('glasovalo ukupno'),
            'valid': find('listići važeći'),
            'invalid': invalid,
            'first_result': invalid + 1,
        }

    @staticmethod
    def _is_aggregate(low_header):
        """True for a per-municipality / per-country totals file."""
        return (_AGGREGATE_NUMBER_HEADER in low_header
                and not any(h in low_header for h in _STATION_NUMBER_HEADERS))

    @staticmethod
    def _split_list_label(raw):
        """('HDZ …', 'IVO SANADER') from 'HDZ …, Nositelj liste: IVO SANADER'."""
        parts = _NOSITELJ_SPLIT_RE.split((raw or '').strip(), maxsplit=1)
        base = ' '.join(parts[0].split()).strip(' ,')
        holder = ' '.join(parts[1].split()).strip(' ,') if len(parts) > 1 else ''
        return base, holder

    @classmethod
    def _list_names(cls, cols):
        """Map result-column index -> the list name to store.

        Independent lists are every one of them literally called
        "NEOVISNA LISTA" and are told apart *only* by their nositelj — district
        I alone runs six, including Milan Bandić's and Ivan Grubišić's (the
        latter took 2 seats). Dropping the suffix unconditionally would collapse
        them into a single list and silently pool their votes, so the holder is
        appended whenever a base name repeats. The resulting
        "NEOVISNA LISTA - IVAN GRUBIŠIĆ" matches how DIP labels independents in
        later years, which keeps cross-year matching working.
        """
        parsed = {i: cls._split_list_label(raw) for i, raw in cols}
        counts = Counter(base for base, _ in parsed.values())
        names = {}
        for i, (base, holder) in parsed.items():
            names[i] = (f'{base} - {clean_candidate_name(holder)}'
                        if counts[base] > 1 and holder else base)
        return names

    @staticmethod
    def _clean_minority_candidate(raw):
        m = _KANDIDAT_RE.match((raw or '').strip())
        return clean_candidate_name(m.group(1) if m else raw)

    def _result_columns(self, header, first_result):
        """(column index, raw label) for every non-empty result column.

        Every file carries a run of blank trailing columns; those are dropped.
        """
        return [(i, header[i].strip())
                for i in range(first_result, len(header)) if header[i].strip()]

    # ---- districts I-XI ----------------------------------------------

    def _import_district(self, election, election_round, district_num):
        roman = self._roman(district_num)
        files = self._files_for(f'{district_num:02d}_{roman}')
        if not files:
            self.log(f'No files found for district {district_num}')
            return

        district = self.get_or_create_district(
            election, district_num, f'{roman}. IZBORNA JEDINICA')

        # Take the list roster from the regular-stations file: it is the widest
        # and always present.
        main = next((f for f in files if self._is_main_file(f)), files[0])
        header = self._read_header(main)
        info = self._parse_header(header)
        cols = self._result_columns(header, info['first_result'])

        list_objs = {}
        for name in self._list_names(cols).values():
            if name and name not in list_objs:
                list_objs[name] = self.get_or_create_electoral_list(
                    election_round, name, district)
        self.log(f'District {district_num}: {len(list_objs)} lists, {len(files)} files')

        for fp in files:
            self._import_file(election_round, district, fp, list_objs, district_num)

    def _import_file(self, election_round, district, filepath, list_objs, district_num):
        header = self._read_header(filepath)
        info = self._parse_header(header)
        if not info:
            self.log(f'  {filepath.name}: unrecognised header, skipped')
            return
        cols = self._result_columns(header, info['first_result'])
        # Names are recomputed from this file's own header: the three file types
        # repeat the roster with slightly different spacing, and the collision
        # rule must see the same column set that it is naming.
        names = self._list_names(cols)
        prefix = self._station_prefix(filepath)
        unknown = {n for n in names.values() if n and n not in list_objs}
        if unknown:
            self.log(f'  {filepath.name}: {len(unknown)} list(s) absent from the '
                     f'district roster, e.g. {sorted(unknown)[:2]}')

        rows = skipped = 0
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)
            for row in reader:
                if len(row) <= info['invalid']:
                    continue
                raw_muni = row[info['muni']].strip()
                if not raw_muni:
                    continue  # blank spacer row
                if self._is_summary_row(raw_muni):
                    continue  # 2007 district subtotal; would double-count
                muni = self._resolve_municipality(raw_muni, district_num, info['is_foreign'])
                if muni is None:
                    skipped += 1
                    continue
                station = self._station_for(row, info, muni, prefix)

                self.create_turnout(
                    election_round, station,
                    self.parse_int(row[info['registered']]),
                    self.parse_int(row[info['cast']]),
                    self.parse_int(row[info['valid']]),
                    self.parse_int(row[info['invalid']]),
                )
                for idx in names:
                    el = list_objs.get(names[idx])
                    if el is None or idx >= len(row):
                        continue
                    self.create_list_result(el, station, self.parse_int(row[idx]))
                rows += 1

        self.flush_all()
        extra = f', {skipped} rows skipped (unresolved municipality)' if skipped else ''
        self.log(f'  {filepath.name}: {rows} rows{extra}')

    def _station_for(self, row, info, muni, prefix):
        def cell(key):
            i = info[key]
            return row[i].strip() if i is not None and i < len(row) else ''
        # 2011 writes bare station numbers ("1"), 2015+ writes them already
        # padded ("001"). Pad before prefixing so the two years agree on
        # "I001" — appending first would leave "I1", which BaseImporter's
        # zfill(3) then mangles into "0I1" and splits the same embassy station
        # into a separate row per year.
        number = f"{prefix}{cell('number').zfill(3)}"
        return self.get_or_create_polling_station(
            muni, number, cell('name'), cell('location'), cell('address'))

    # ---- district XII -------------------------------------------------

    def _import_district_12(self, election, election_round):
        total = 0
        for nm, (sub_number, _seats, sub_name) in self.MINORITY_SUBDISTRICTS.items():
            files = self._files_for(f'12_XII_{nm}')
            if not files:
                self.log(f'No files found for district 12 {nm}')
                continue
            district = self.get_or_create_district(election, sub_number, sub_name)

            main = next((f for f in files if self._is_main_file(f)), files[0])
            header = self._read_header(main)
            info = self._parse_header(header)
            cols = self._result_columns(header, info['first_result'])

            entries = {}
            for _, raw in cols:
                name = self._clean_minority_candidate(raw)
                if name and name not in entries:
                    el = self.get_or_create_electoral_list(election_round, name, district)
                    person = self.get_or_create_person(name)
                    entries[name] = (el, self.get_or_create_candidacy(person, el, 1))
            total += len(entries)

            for fp in files:
                self._import_file_d12(election_round, fp, entries)
        self.log(f'District 12: {total} candidates across '
                 f'{len(self.MINORITY_SUBDISTRICTS)} sub-districts')

    def _import_file_d12(self, election_round, filepath, entries):
        """District XII rows report minority-only voter counts, a subset of each
        station's total, so turnout is deliberately not written here — it comes
        from districts I-XI, exactly as in sabor.py."""
        header = self._read_header(filepath)
        info = self._parse_header(header)
        if not info:
            self.log(f'  {filepath.name}: unrecognised header, skipped')
            return
        cols = self._result_columns(header, info['first_result'])
        prefix = self._station_prefix(filepath)

        rows = skipped = 0
        with open(filepath, encoding='windows-1250') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader)
            for row in reader:
                if len(row) <= info['invalid']:
                    continue
                raw_muni = row[info['muni']].strip()
                if not raw_muni or self._is_summary_row(raw_muni):
                    continue
                # The nm files span the whole country, so the district hint for
                # repeated place names comes from the row's own home-district
                # column rather than the file.
                hint = None
                hd = info['home_district']
                if hd is not None and hd < len(row):
                    hint = self.parse_int(row[hd]) or None
                muni = self._resolve_municipality(raw_muni, hint, info['is_foreign'])
                if muni is None:
                    skipped += 1
                    continue
                station = self._station_for(row, info, muni, prefix)

                for idx, raw in cols:
                    name = self._clean_minority_candidate(raw)
                    entry = entries.get(name)
                    if entry is None or idx >= len(row):
                        continue
                    el, candidacy = entry
                    votes = self.parse_int(row[idx])
                    self.create_list_result(el, station, votes)
                    self.create_candidate_result(candidacy, station, votes)
                rows += 1

        self.flush_all()
        extra = f', {skipped} rows skipped (unresolved municipality)' if skipped else ''
        self.log(f'  {filepath.name}: {rows} rows{extra}')

    # ---- helpers -------------------------------------------------------

    def _read_header(self, filepath):
        with open(filepath, encoding='windows-1250') as f:
            return next(csv.reader(f, delimiter=';'))

    @staticmethod
    def _roman(n):
        vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        out = ''
        for val, numeral in vals:
            while n >= val:
                out += numeral
                n -= val
        return out
