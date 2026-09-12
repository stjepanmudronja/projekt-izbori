"""Import the 2003 Sabor election.

2003 is a third export dialect, closer to 2007/2011 than to 2015+ but not the
same as either, so this subclasses `SaborLegacyImporter` and replaces the parts
that differ:

  * **A three-row header block** — labels, then a row numbering the result
    columns 1..N, then a blank spacer — where the legacy years have one row.
  * **A fixed six-column geo block** (`Grad/ općina` or `Država`, `Broj
    biračkog mjesta`, then the four turnout counts) and **no station name,
    location or address at all** — those stay blank unless another year's
    import fills them in, the same as 2007.
  * **List labels read `PARTY …, HOLDER - Nositelj liste`**, holder last,
    where 2007/2011 write `PARTY …, Nositelj liste: HOLDER`. In the mješovita
    files the comma before the holder is a real newline inside a quoted cell
    instead, which is why every file is read with `newline=''`.
  * **Subtotals are pivot-table rows** — `BISTRA Total`, `Grand Total` — rather
    than 2007's `UKUPNO ZA I. IJ`.
  * **Aggregate files are named `… sumari grad_općina` / `… sumari po
    državama`** and would double-count a district; they are also rejected
    structurally, since the "po BM" file of the same district is byte-identical
    apart from the header.

Mixed polling stations (mješovita) are the substantive difference. A mixed
station serves voters registered in more than one electoral district, so DIP
reports it once per district, each file carrying only that district's votes —
summing turnout across the files is therefore correct, exactly as for the
abroad stations of 2015+. The per-district "po BM" file folds the whole mixed
set into a **single** `DIJASPORA I MJEŠOVITA` row, and the matching
`Mješovita BM za IJxx` file breaks the identical total into its ~281 stations,
so the aggregate row is dropped and the per-station file imported instead.

This is why `files/…/2003/rezultati/Rezultati po BM redovita/` is not the
directory used: its "po BM" files are byte-identical to the ones in
`Rezultati po BM redovita+mjeçovita/`, which additionally ships the mješovita
breakdown. Reading the smaller folder would lose every mixed-station vote —
about 43k of them.

Seats: districts I-X return 14 each, district XII 8 across its six minority
sub-districts, and diaspora district XI returned **4** in 2003 under the
votes-per-seat conversion that also gave it 5 in 2007 (see
DIASPORA_SEATS_BY_YEAR in app.py). Total 152.
"""
import re
from pathlib import Path

from .name_utils import clean_candidate_name, looks_like_person_name
from .sabor_legacy import SaborLegacyImporter


# Pivot subtotals: "BISTRA Total", "Albanija Total", "Grand Total". No Croatian
# municipality or country name ends in the English word "Total".
_TOTAL_ROW_RE = re.compile(r'\bTotal$', re.IGNORECASE)

# The one-row fold of every mixed station, already broken out per station in
# the district's "Mješovita BM" file. District V writes it with two spaces.
_MIXED_AGGREGATE_RE = re.compile(r'^DIJASPORA\s+I\s+MJEŠOVITA$', re.IGNORECASE)

# Trailing marker on every list-name cell; what precedes it is
# "<party/coalition parts…>, <list holder>".
_NOSITELJ_TAIL_RE = re.compile(r'\s*-\s*Nositelj\s+liste\s*$', re.IGNORECASE)

# A mixed station named for the Croatian town it stands in: "MJEŠOVITO - SPLIT"
# (mixed-district station), "PRIVR.UPIS-DUBROVNIK" (temporary registration),
# "RASELJNI - VUKOVAR" and "BJELOVAR-PROGNANICI V." (displaced persons).
# Resolving the town keeps those votes with the municipality they were cast in;
# the remaining ~108 labels are consulates and émigré clubs abroad.
#
# Getting RASELJNI in here matters for more than tidiness: its six stations are
# all numbered 1, so leaving them in the shared abroad municipality collapsed
# them onto one another and onto the Albanian embassy, and ListResult's
# ignore_conflicts silently dropped the losers' votes.
_MIXED_TOWN_RES = (
    re.compile(r'^MJEŠOVIT[OA]\s*-\s*(.+)$', re.IGNORECASE),
    re.compile(r'^PRIVR\.?\s*UPIS\s*-\s*(.+)$', re.IGNORECASE),
    re.compile(r'^RASELJN[IO]\s*-\s*(.+)$', re.IGNORECASE),
    re.compile(r'^(.+?)\s*-\s*PROGNAN\w*\.?\b.*$', re.IGNORECASE),
)

# Municipality that holds the mixed stations naming no Croatian town: mostly
# consulates and émigré clubs, plus a couple of domestic labels too vague to
# place ("PROGNANICI V. IJ"). Filed under inozemstvo because that is where all
# but a handful of them are.
_MIXED_ABROAD_MUNI = 'MJEŠOVITA BIRAČKA MJESTA'

# 2003 spellings of municipalities the rest of the database knows under another
# name. Both are this export's own quirk, not a general rule, so they are
# listed rather than derived: districts VII and VIII distinguish the two Sveta
# Nedelja municipalities by spelling alone ("NEDJELJA" for the Zagreb one,
# "NEDELJA" for the Istrian), and DIP's canonical name for Martijanec carries
# no "Donji".
_MUNI_ALIASES = {
    'SVETA NEDJELJA': 'SVETA NEDELJA',
    'DONJI MARTIJANEC': 'MARTIJANEC',
}

# "V.GORICA", "D.MIHOLJAC" — an initial abbreviating the first word. Expanded
# by matching municipalities that begin with that letter and end with the rest,
# which picks VELIKA GORICA over MARIJA GORICA without a hard-coded table.
_ABBREV_RE = re.compile(r'^([A-ZŠĐČĆŽ])\.\s*(.+)$', re.IGNORECASE)

# Words that mark a label as a mixed-station pseudo-place rather than a
# municipality. One label is only that — "PROGNANICI V. IJ" names no town at
# all — and it carries 1579 votes in district V, so it has to land somewhere
# instead of being dropped as an unresolved municipality.
_MIXED_KEYWORDS = ('MJEŠOVIT', 'PRIVR.UPIS', 'PRIVR. UPIS', 'RASELJN', 'PROGNAN')

# District XII columns are "kandidat: X, zamjenik: Y, PROPOSER" — and, where a
# candidate stood without a deputy, just "kandidat: X, PROPOSER".
_KANDIDAT_2003_RE = re.compile(r'^\s*kandidat\s*:\s*(.*)$', re.IGNORECASE | re.DOTALL)
_ZAMJENIK_SPLIT_RE = re.compile(r',\s*zamjenik\s*:', re.IGNORECASE)


class Sabor2003Importer(SaborLegacyImporter):
    YEARS = (2003,)
    HEADER_ROWS = 3

    # nm-suffix here is the "IJ12-N" number DIP uses in the 2003 filenames.
    MINORITY_SUBDISTRICTS = {
        '1': (121, 3, 'XII. IJ - Srpska nacionalna manjina'),
        '2': (122, 1, 'XII. IJ - Mađarska nacionalna manjina'),
        '3': (123, 1, 'XII. IJ - Talijanska nacionalna manjina'),
        '4': (124, 1, 'XII. IJ - Češka i slovačka nacionalna manjina'),
        '5': (125, 1, 'XII. IJ - Romska, rusinska, ukrajinska i dr.'),
        '6': (126, 1, 'XII. IJ - Albanska, bošnjačka, crnogorska i dr.'),
    }

    def __init__(self, year=2003, stdout=None):
        super().__init__(year=year, stdout=stdout)
        self._in_mixed_file = False
        self._split_stations = 0
        # raw municipality label -> the municipality districts I-XI resolved it
        # to, or None once two districts disagree. Lets the nationwide district
        # XII files reuse 2003's own disambiguation (see _resolve_municipality).
        self._name_from_districts = {}
        # (municipality, station number) -> how many rows of the current file
        # have claimed it.
        self._file_stations = {}
        self.data_dir = (self.BASE_DIR / str(year) / 'rezultati'
                         / 'Rezultati po BM redovita+mjeçovita' / 'CSV')

    # ---- file discovery ----------------------------------------------

    @staticmethod
    def _norm_filename(fp):
        """Lowercased, whitespace-collapsed name. DIP's 2003 filenames carry
        stray double spaces ("Mjeçovita BM  za IJ07") and the folder was zipped
        with a DOS codepage, so the Croatian letters arrive mojibaked and only
        the ASCII around them can be matched on."""
        return re.sub(r'\s+', ' ', fp.name.lower())

    def _files_for(self, district_tag):
        """Result files for `IJ01` / `IJ12-3`, aggregates excluded.

        The tag must not be preceded by a letter or digit nor followed by a
        digit, which keeps `IJ01` off `IJ10` and `IJ12-1` off `IJ12-10`. `\b`
        will not do: every filename writes the tag after an underscore
        ("...jedinica_IJ01 po BM"), and `_` is a word character, so there is no
        word boundary in front of it.
        """
        tag = district_tag.lower()
        out = []
        for fp in sorted(self.data_dir.glob('*.csv')):
            name = self._norm_filename(fp)
            if not re.search(rf'(?<![a-z0-9]){re.escape(tag)}(?![0-9])', name):
                continue
            if 'sumari' in name:      # per-muni / per-country totals
                continue
            out.append(fp)
        return out

    @staticmethod
    def _is_main_file(filepath):
        """The regular-stations file — carries the full list roster."""
        return 'po bm' in re.sub(r'\s+', ' ', filepath.name.lower())

    @classmethod
    def _station_prefix(cls, filepath):
        return 'M' if 'ovita bm' in cls._norm_filename(filepath) else ''

    # ---- header parsing ----------------------------------------------

    def _parse_header(self, header):
        """2003's geo block is a fixed six columns, so it is located by label
        rather than measured."""
        low = [re.sub(r'\s+', ' ', (h or '').strip().lower()) for h in header]

        def find(*labels):
            for lab in labels:
                if lab in low:
                    return low.index(lab)
            return None

        invalid = find('nevažećih listića')
        muni = find('grad/ općina', 'grad/općina', 'grad / općina')
        foreign = find('država')
        if invalid is None or (muni is None and foreign is None):
            return None
        return {
            'muni': muni if muni is not None else foreign,
            'is_foreign': muni is None,
            'home_district': None,   # 2003 files carry no home-district column
            'number': find('broj biračkog mjesta'),
            'name': None, 'location': None, 'address': None,
            'registered': find('broj birača'),
            # Ten of the files head this column "Glasovalo birača (po
            # listićima)" and eight just "Glasovalo birača".
            'cast': find('glasovalo birača (po listićima)', 'glasovalo birača'),
            'valid': find('važećih listića'),
            'invalid': invalid,
            'first_result': invalid + 1,
        }

    @staticmethod
    def _split_list_label(raw):
        """('HDZ …', 'IVO SANADER') from 'HDZ … , dr.sc. IVO SANADER - Nositelj liste'.

        The holder comes last here, and both it and the party names may contain
        commas — a coalition lists each member party, and a holder may carry an
        academic title before ("dr.sc. MATE GRANIĆ") or after ("ANTE LEDIĆ,
        dipl.ing.") the name. So rather than splitting on a fixed comma, the
        shortest trailing run of comma-separated fields that reads as a person
        is taken as the holder; everything before it is the list.
        """
        text = _NOSITELJ_TAIL_RE.sub('', (raw or '').replace('\n', ', ').strip())
        parts = [p.strip() for p in text.split(',')]
        whole = ' '.join(text.split()).strip(' ,-')
        for take in range(1, min(len(parts), 4) + 1):
            candidate = ', '.join(parts[-take:])
            if not looks_like_person_name(candidate):
                continue
            base = ' '.join(', '.join(parts[:-take]).split()).strip(' ,-')
            # An empty base means the whole label was eaten as a name — which
            # is what "NEOVISNA LISTA" does, being two plain words. Keep the
            # label as the list name rather than storing a nameless list whose
            # votes then go nowhere.
            if not base:
                return whole, ''
            return base, clean_candidate_name(candidate)
        return whole, ''

    # ---- row filtering -------------------------------------------------

    @staticmethod
    def _is_summary_row(raw_name):
        """Pivot subtotal, or the one-row fold of the mixed stations that the
        district's own Mješovita file breaks out per station."""
        name = (raw_name or '').strip()
        return bool(_TOTAL_ROW_RE.search(name)
                    or _MIXED_AGGREGATE_RE.match(' '.join(name.split())))

    # ---- geography -----------------------------------------------------

    def _resolve_municipality(self, raw_name, district_num, is_foreign):
        """Mixed stations are labelled by station, not municipality.

        A label naming a Croatian town resolves to that town so the votes stay
        with the place they were cast; consulates and émigré clubs have no town
        to resolve and are collected under one municipality in inozemstvo,
        keeping 108 club names out of the county list.

        Order matters. Deciding "not a municipality" by asking the index first
        is wrong, because the index holds the *bilingual* Istrian names later
        years import — BALE is stored as "BALE - VALLE" — so BALE, BRTONIGLA,
        BUJE and their neighbours all looked unknown and were filed abroad. The
        inherited resolver knows to fall back to a unique prefix match, so it
        runs first and the abroad bucket only catches what it genuinely cannot
        place, and only in a mixed file.
        """
        name = _MUNI_ALIASES.get((raw_name or '').strip(), (raw_name or '').strip())
        for pattern in _MIXED_TOWN_RES:
            m = pattern.match(name)
            if m:
                town = self._resolve_town(m.group(1).strip(), district_num)
                if town is not None:
                    return town
                break

        if district_num is None:
            # A district XII file: nationwide, and with no home-district column
            # to break ties on a repeated place name. 2003's own district files
            # already made that choice — district V writes "OTOK (VINKOVCI)"
            # and district IX plain "OTOK" — so reuse it rather than guessing.
            learned = self._name_from_districts.get(name)
            if learned is not None:
                return learned

        muni = super()._resolve_municipality(name, district_num, is_foreign)

        if muni is None and self._is_mixed_pseudo_place(name):
            # A mixed-station label naming no resolvable town. Without this it
            # would be dropped as an unresolved municipality, taking its votes
            # with it, even in a regular district file.
            self._unresolved.pop(name, None)
            county = self.get_or_create_county('00', 'inozemstvo')
            return self.get_or_create_municipality(county, _MIXED_ABROAD_MUNI, 'država')

        if muni is not None and district_num is not None and not self._in_mixed_file:
            prev = self._name_from_districts.get(name, muni)
            self._name_from_districts[name] = (
                muni if prev is not None and prev.id == muni.id else None)

        if muni is not None or not self._in_mixed_file:
            return muni

        # A consulate or émigré club: no town to place it in.
        self._unresolved.pop(name, None)
        county = self.get_or_create_county('00', 'inozemstvo')
        return self.get_or_create_municipality(county, _MIXED_ABROAD_MUNI, 'država')

    @staticmethod
    def _is_mixed_pseudo_place(name):
        return any(k in name.upper() for k in _MIXED_KEYWORDS)

    @staticmethod
    def _clean_minority_candidate(raw):
        """The candidate out of "kandidat: X, zamjenik: Y, PROPOSER".

        The deputy is optional in 2003, so the proposer can follow the
        candidate directly and a fixed split would keep it — which is how
        "ZDENKA ČUHNIL HRVATSKA SELJAČKA STRANKA -HSS" ended up stored as a
        person. Both the name and the proposer may themselves contain commas
        (a title before or after the name, a coalition of proposers), so the
        shortest leading run of comma-separated fields that reads as a person
        is taken, the same way list holders are split.
        """
        m = _KANDIDAT_2003_RE.match((raw or '').strip())
        text = (m.group(1) if m else (raw or '')).replace('\n', ', ')
        text = _ZAMJENIK_SPLIT_RE.split(text, maxsplit=1)[0]
        parts = [p.strip() for p in text.split(',')]
        for take in range(1, min(len(parts), 3) + 1):
            candidate = clean_candidate_name(', '.join(parts[:take]))
            if looks_like_person_name(candidate):
                return candidate
        return clean_candidate_name(text)

    def _resolve_town(self, town, district_num):
        """Resolve the town named inside a mixed-station label, expanding an
        initial-dot abbreviation if the plain name does not match."""
        muni = super()._resolve_municipality(
            _MUNI_ALIASES.get(town, town), district_num, False)
        if muni is not None:
            return muni
        m = _ABBREV_RE.match(town)
        if not m:
            return None
        initial, rest = m.group(1).upper(), self._muni_key(m.group(2))
        hits = [mu for key, ms in self._muni_index.items()
                if key.startswith(initial) and key.endswith(rest) for mu in ms]
        self._unresolved.pop(town, None)
        return hits[0] if len(hits) == 1 else None

    # `_resolve_municipality` needs to know whether the row it is placing came
    # from a mixed-station file, which only the caller knows.
    def _import_file(self, election_round, district, filepath, list_objs, district_num):
        self._in_mixed_file = self._station_prefix(filepath) == 'M'
        self._file_stations = {}
        return super()._import_file(
            election_round, district, filepath, list_objs, district_num)

    def _import_file_d12(self, election_round, filepath, entries):
        self._in_mixed_file = self._station_prefix(filepath) == 'M'
        self._file_stations = {}
        return super()._import_file_d12(election_round, filepath, entries)

    def _station_for(self, row, info, muni, prefix):
        """2003 publishes no station name, location or address.

        Two rows of one file can still land on the same municipality and
        station number: Croatia has two NOVIGRADs and two PRIVLAKAs written
        identically, and the district XII files name neither a county nor a
        home district, so nothing separates them. Rather than let the second
        row collide — ListResult's ignore_conflicts would drop its votes
        without a word — the later claimant gets a letter suffix. The votes are
        then kept and counted nationally, which is what the minority seats are
        decided on; only the municipality attribution stays uncertain, and
        `run()` reports how many stations this affected.
        """
        i = info['number']
        number = row[i].strip() if i is not None and i < len(row) else ''
        key = (muni.id, f'{prefix}{number.zfill(3)}')
        # Counted per row, not per distinct label: Croatia's two NOVIGRADs and
        # two PRIVLAKAs are written identically, so the label cannot tell the
        # second station from the first — only the fact that the key has
        # already been claimed in this file can.
        rank = self._file_stations.get(key, 0)
        self._file_stations[key] = rank + 1
        self._split_stations += (rank > 0)
        # Stable across the six XII files: they list the same rows in the same
        # order, so a given label always takes the same rank.
        suffix = '' if rank == 0 else chr(ord('A') + rank - 1)
        return self.get_or_create_polling_station(
            muni, f'{key[1]}{suffix}', '', '', '')

    # ---- district XII ---------------------------------------------------

    def _import_district_12(self, election, election_round):
        total = 0
        for tag, (sub_number, _seats, sub_name) in self.MINORITY_SUBDISTRICTS.items():
            files = self._files_for(f'IJ12-{tag}')
            if not files:
                self.log(f'No files found for district 12 sub-district {tag}')
                continue
            district = self.get_or_create_district(election, sub_number, sub_name)

            main = next((f for f in files if self._is_main_file(f)), files[0])
            info = self._parse_header(self._read_header(main))
            cols = self._result_columns(self._read_header(main), info['first_result'])

            entries = {}
            for _, raw in cols:
                name = self._clean_minority_candidate(raw)
                if name and name not in entries:
                    el = self.get_or_create_electoral_list(election_round, name, district)
                    person = self.get_or_create_person(name)
                    entries[name] = (el, self.get_or_create_candidacy(person, el, 1))
            total += len(entries)
            self.log(f'District 12-{tag}: {len(entries)} candidates, {len(files)} files')

            for fp in files:
                self._import_file_d12(election_round, fp, entries)
        self.log(f'District 12: {total} candidates across '
                 f'{len(self.MINORITY_SUBDISTRICTS)} sub-districts')

    def run(self, only_district=None):
        self._split_stations = 0
        super().run(only_district=only_district)
        if self._split_stations:
            self.log(f'{self._split_stations} polling station(s) shared a municipality '
                     f'and number with a differently-named place and were kept apart '
                     f'with a letter suffix; their votes are counted, their '
                     f'municipality is a guess.')

    # ---- districts I-XI --------------------------------------------------

    def _import_district(self, election, election_round, district_num):
        files = self._files_for(f'IJ{district_num:02d}')
        if not files:
            self.log(f'No files found for district {district_num}')
            return
        roman = self._roman(district_num)
        district = self.get_or_create_district(
            election, district_num, f'{roman}. IZBORNA JEDINICA')

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
