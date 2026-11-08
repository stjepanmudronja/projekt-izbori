"""Import the 2009 lokalni izbori from DIP's per-county PDF report.

2009 has no Excel export: DIP published one "Informacija o rezultatima
izbora" PDF per county (`2009/i_06_NN_0000.pdf`, NN = county code), with
one section per contest and **no per-station breakdown**. The PDFs carry a
text layer, dumped to `2009/text/*.txt` by `tools/pdf_text`; the parsing
lives in `local_2009_parse.py`, which checks every section on its own.

Stored the way the Excel years store their results, so every lokalni view
reads 2009 like any other year:

- one pseudo polling station `000` per municipality, holding that
  municipality's figures for each of its contests (council, načelnik /
  gradonačelnik), so municipality and county views aggregate honestly;
- county contests (županijska skupština, župan) on the county's existing
  `<ŽUPANIJA> (SAŽETAK)` pseudo-municipality — the one the Županijski dom
  import created — so they sit inside the county but in no municipality;
- executive candidates' lists scoped to their race through an
  ElectoralDistrict numbered by the Municipality (or County) pk, exactly as
  `LocalImporter._race_district` does; council lists shared by name;
- three rounds: 17 May, the 31 May runoff, and 14 June 2009, when
  Zlatar-Bistrica and Udbina repeated a runoff that had ended in a tie.

2009 was the first year mayors and župani were elected directly. Their
deputies ran on the candidate's ticket rather than in a vote of their own,
so they are not stored; nor are elected council members, which no other
year records either.
"""
import os
import re
from pathlib import Path

from .base import BaseImporter
from .local import LocalImporter, SHEET_TYPE_MAP
from .local_2009_parse import parse_text, check, list_name
from .name_utils import clean_candidate_name, normalize_municipality_name

YEAR = 2009

# Display names per slug, as the Excel importer names the elections.
DISPLAY = {slug: name for slug, name, _ in SHEET_TYPE_MAP.values()}

# Headings the stem match cannot reach: a genitive that drops a vowel
# (OZALJ -> OZLJA), 2005's former name of Martijanec and spaced hyphen in
# Kaštelir-Labinci (which would otherwise read as a bilingual " - "), and
# 2001's ć for č and bare "VINODOLSKA".
UNIT_ALIASES = {'OZLJA': 'OZALJ', 'DONJI MARTIJANEC': 'MARTIJANEC',
                'KAŠTELIR - LABINCI': 'KAŠTELIR-LABINCI',
                'BUDINŠĆINA': 'BUDINŠČINA', 'KONJŠĆINA': 'KONJŠČINA',
                'VINODOLSKA': 'VINODOLSKA OPĆINA',
                # 1997: names since reordered, and OCR's D for Đ / l for I.
                'HUM BREZNIČKI': 'BREZNIČKI HUM', 'MOSLAVINA PODRAVSKA': 'PODRAVSKA MOSLAVINA',
                'SVETA NEDJELJA': 'SVETA NEDELJA', 'DURMANEC': 'ĐURMANEC', 'SVETI DURD': 'SVETI ĐURĐ',
                'ĐURDEVCA': 'ĐURĐEVAC', 'DELEKOVEC': 'ĐELEKOVEC', 'DULOVAC': 'ĐULOVAC',
                'VELIKI GRDEVAC': 'VELIKI GRĐEVAC', 'ČADAVICA': 'ČAĐAVICA', 'ĐURDENOVAC': 'ĐURĐENOVAC',
                'SATNICA DAKOVAČKA': 'SATNICA ĐAKOVAČKA', 'LVANKOVO': 'IVANKOVO'}


def _words(name):
    name = UNIT_ALIASES.get(name, name)
    # Bilingual Istrian names ("POREČ - PARENZO") and bracketed
    # disambiguators ("OTOKA (VINKOVCI)") match on their Croatian base.
    base = re.sub(r'\s*\(.*\)', '', name.split(' - ')[0])
    return re.split(r'[\s-]+', normalize_municipality_name(base).strip())


def _stem_match(a, b):
    """Word by word, two names that differ only in their case ending."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y:
            continue
        shorter = min(len(x), len(y))
        if shorter <= 2 or len(os.path.commonprefix([x, y])) < shorter - 2:
            return False
    return True


class Local2009Importer(BaseImporter):
    """Also the base of `Local2005Importer`, which reads the same report
    shape for an earlier year and overrides only `year` and `_parse`."""

    year = YEAR
    text_glob = 'i_06_*.txt'
    display = DISPLAY
    # Store each council list's nositelj liste (`ListHolder`): the 2001,
    # 2005 and 2009 reports print one for every list. Before 2009 the body
    # chose the executive, and the leading list's holder is the nearest the
    # result comes to naming one. The 1993 / 1997 scans are off (see there).
    store_holders = True

    def _county_code(self, path):
        return path.stem.split('_')[2]

    def __init__(self, stdout=None):
        super().__init__(stdout=stdout)
        self.matched = {}

    def _parse(self, code, text):
        """[(contest, problems)] for one county's text dump."""
        return [(c, check(c)) for c in parse_text(text)[1]]

    def run(self):
        text_dir = LocalImporter.DATA_DIR / str(self.year) / 'text'
        files = sorted(text_dir.glob(self.text_glob))
        if not files:
            raise RuntimeError(
                f'No text dumps in {text_dir}. Build tools/pdf_text '
                '(swiftc -O tools/pdf_text.swift -o tools/pdf_text) and run it '
                f'on each {self.year}/*.pdf into that folder.')
        contests = []
        for path in files:
            code = self._county_code(path)
            for c, problems in self._parse(code, path.read_text()):
                if problems:
                    raise RuntimeError(f'{path.name} {c["slug"]} r{c["round"]} '
                                       f'{c["unit"]}: {"; ".join(problems)}')
                contests.append((code, c))
        self.log(f'Parsed {len(contests)} contests from {len(files)} files, all reconciling')

        for code, c in contests:
            self._import_contest(code, c)
        self.flush_all()

        live = self._live_municipalities()
        missing = live - set(m.pk for m in self.matched.values())
        self.log(f'Matched {len(set(m.pk for m in self.matched.values()))} municipalities'
                 + (f'; {len(missing)} with 2013 results got none' if missing else ''))

    # ---- geography -----------------------------------------------------

    def _live_municipalities(self):
        from elections.models import TurnoutData
        return set(TurnoutData.objects.filter(
            election_round__election__year=2013,
            election_round__election__election_type__slug__startswith='local',
        ).values_list('polling_station__municipality', flat=True))

    def _municipality(self, county, unit):
        """The existing municipality a heading names. Towns are printed in
        the genitive ("GRADA SISKA"), općine mostly not; the candidate with
        the longest shared prefix among same-length stem matches wins, and
        a tie or no match aborts rather than guess."""
        key = (county.pk, unit)
        if key in self.matched:
            return self.matched[key]
        from elections.models import Municipality
        if not hasattr(self, '_live'):
            self._live = self._live_municipalities()
        munis = [m for m in Municipality.objects.filter(county=county) if m.pk in self._live]
        w = _words(unit)
        hits = [m for m in munis if _words(m.name) == w]
        if not hits:
            scored = [(sum(len(os.path.commonprefix([a, b])) for a, b in zip(_words(m.name), w)), m)
                      for m in munis if _stem_match(_words(m.name), w)]
            best = max((s for s, _ in scored), default=None)
            hits = [m for s, m in scored if s == best]
        if len(hits) != 1:
            raise RuntimeError(f'County {county.code}: "{unit}" matches '
                               f'{[m.name for m in hits] or "nothing"}')
        self.matched[key] = hits[0]
        return hits[0]

    def _place(self, code, c):
        """(station, district number, district name) for one contest."""
        county = self.get_or_create_county(code, '')
        if c['level'] == 'county':
            muni = self.get_or_create_municipality(county, f'{county.name} (SAŽETAK)', 'sažetak')
            station = self.get_or_create_polling_station(
                muni, '001', county.name, 'sažetak županije', '')
            return station, county.pk, county.name
        # Zagreb's two contests are headed "… GRADA ZAGREBA" with no unit.
        muni = self._municipality(county, c['unit'] or 'ZAGREB')
        station = self.get_or_create_polling_station(muni, '000', muni.name, 'sažetak', '')
        return station, muni.pk, muni.name

    # ---- results -------------------------------------------------------

    def _import_contest(self, code, c):
        slug = c['slug']
        election_type = self.get_or_create_election_type(slug, self.display[slug], parent_slug='local')
        election = self.get_or_create_election(election_type, self.year, f'{self.display[slug]} {self.year}')
        election_round = self.get_or_create_round(election, c['round'])
        station, number, name = self._place(code, c)

        self.create_turnout(election_round, station, c['registered'], c['cast'],
                            c['valid'], c['invalid'])

        executive = 'name' in c['entries'][0]
        district = self.get_or_create_district(election, number, name) if executive else None
        for e in c['entries']:
            if executive:
                el_list = self.get_or_create_electoral_list(election_round, e['name'], district)
                # "OŽIĆ - BEBEK": the report spaces the hyphen of a double
                # surname, which no other year does.
                person = self.get_or_create_person(
                    clean_candidate_name(re.sub(r'\s+-\s+', '-', e['name'])))
                candidacy = self.get_or_create_candidacy(person, el_list, 1)
                self.create_candidate_result(candidacy, station, e['votes'])
            else:
                el_list = self.get_or_create_electoral_list(election_round, list_name(e))
                if self.store_holders and e.get('holder'):
                    self._store_holder(el_list, station.municipality, e['holder'])
            # 1997 prints a few lists with no count; they stand, unscored.
            if e.get('votes') is not None:
                self.create_list_result(el_list, station, e['votes'])

    def _store_holder(self, el_list, municipality, printed):
        """One list's leader in one municipality. The person is what precedes
        a title's comma ("ANTE RIZVAN, dipl. ing."); a title printed first
        (", dipl. oec. BRANKO MUČNJAK") is dropped from the front."""
        from elections.models import ListHolder
        name = re.sub(r'^\s*,\s*(?:[a-zčćšžđ]+[.,]\s*)+', '', printed)
        name = re.sub(r'\s+-\s+', '-', name.split(',')[0].strip())
        # The report prints names in capitals and titles without a comma in
        # lower case or with dots ("MILIVOJ DUJMOVIĆ dr.med.", "Prim. NINO
        # ŠIKIĆ", "ING.STROJARSTVA"); a father's name ("pok. ANTE"), a
        # nickname in brackets and "ML." are not the person's name either.
        bare = re.sub(r'\s*\([^)]*\)|-?"[^"]*"|\bpok\.\s*\S+|\bzv\.\s*\S+', ' ', name, flags=re.I)  # "zv. VICKO"
        # A surname's stray dot goes ("LOŽAR. prof."); "DR.", "ML." and an
        # initial ("L.") are too short to be one and are dropped below.
        words = [w[:-1] if w.endswith('.') and len(w) > 4 else w for w in bare.split()]
        words = [w for w in words if '.' not in w and w == w.upper() and re.search(r'[A-ZČĆŠŽĐ]', w)]
        if len(words) >= 2:
            name = ' '.join(words)
        else:                           # as printed ("MANSOUR EL.BAHTITY", "Tomislav Lunka")
            name = name.upper()
        name = clean_candidate_name(self._holder_order(name, municipality))
        person = self.get_or_create_person(name)
        self._restore_marks(person, name)
        ListHolder.objects.update_or_create(
            electoral_list=el_list, municipality=municipality,
            defaults={'person': person, 'printed_name': printed})

    def _restore_marks(self, person, name):
        """Give a matched person the report's diacritics where its stored
        spelling is the same name with marks lost — mostly the 1993 / 1997
        OCR ("KRUNOSLAV SPANIĆ" -> "ŠPANIĆ", "ANDELKO" -> "ANĐELKO"). Only
        added marks: where the two disagree (č for ć, "TONČI" / "TONĆI"),
        nothing says which is right and the stored one stands."""
        from .name_utils import parse_person_name, strip_diacritics
        stored = f'{person.first_name} {person.last_name}'
        if stored == name or len(stored) != len(name) or not person.pk:
            return
        if any(s != n and s != strip_diacritics(n) for s, n in zip(stored, name)):
            return
        person.first_name, person.last_name = parse_person_name(name)
        person.save(update_fields=['first_name', 'last_name'])

    def _holder_order(self, name, municipality):
        """A leader's name in first-name-first order; overridden where a
        report prints some surname-first (2001)."""
        return name
