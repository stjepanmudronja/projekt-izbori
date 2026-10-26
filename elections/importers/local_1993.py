"""Import the 1993 lokalni izbori (7 February 1993) from DIP's scanned reports.

The parsing, OCR checks and second readings live in `local_1993_parse.py`;
storage is 1997's (`Local1997Importer`), since 1993 used the same mixed
system: each council and county assembly's list part as every later year
stores it, and its single-member wards under the `local_council_ward` /
`local_county_assembly_ward` types, one ElectoralDistrict per ward numbered
`place_pk * 100 + ward`, its printed electorate on the district's display
columns. Unlike 1997, the 1993 report prints a turnout line for every full
ward, council wards included.

Many općine print only each ward's winner and party ("I  Emil Badurina
HDZ"): those wards hold one candidacy with no result row, which the wards
view tells apart from an unopposed candidate by the missing electorate.
Wards marked "Nisu održani izbori" (not held: occupied territory) are not
stored, and keep their numbers free.

Two counties of 1993 no longer exist under their names: XIII
Zadarsko-kninska and XV Šibenska. Their assemblies are filed under the
counties holding their codes today, Zadarska (13) and Šibensko-kninska (15).
Municipalities are filed where they are today (`_municipality`): the 1997
redrawing moved a dozen between counties.
"""
import re

from .local import LocalImporter
from .local_2001_parse import canonicalize
from .local_2009_parse import list_name
from .local_1997 import Local1997Importer, WARD_TYPES
from .local_2009 import DISPLAY, _words
from .local_1997_parse import ROMAN_OF, clean_party
from .local_1993_parse import parse_report
from .name_utils import clean_candidate_name

# 1993 names of places renamed since, and OCR's D for Đ / Č for Ć.
ALIASES_1993 = {
    'DONJA PUŠĆA': 'PUŠĆA', 'HRAŠČINA': 'HRAŠĆINA', 'LJUBEŠČICA': 'LJUBEŠĆICA',
    'IVANIĆ-GRADA': 'IVANIĆ-GRAD', 'DEZANOVAC': 'DEŽANOVAC', 'DURDEVAC': 'ĐURĐEVAC',
    'DURDENOVAC': 'ĐURĐENOVAC', 'DAKOVA': 'ĐAKOVO', 'DAKOVAČKA SATNICA': 'SATNICA ĐAKOVAČKA',
    'JAKSIĆ': 'JAKŠIĆ', 'MALINSKA': 'MALINSKA-DUBAŠNICA', 'PODRAVSKA SLATINA': 'SLATINA',
    'DONJE VILJEVO': 'VILJEVO', 'OKLAJ': 'PROMINA', 'DONJI MUĆ': 'MUĆ', 'DONJI PROLOŽAC': 'PROLOŽAC',
    'KAŠTELANSKA ZAGORA': 'LEĆEVICA', 'SVET VINČENAT': 'SVETVINČENAT',
    'SVETI LOVREČ PAZENATIČKI': 'SVETI LOVREČ', 'TITOVA KORENICA': 'PLITVIČKA JEZERA',
    'VRGINMOST': 'GVOZD', 'KNINA': 'KNIN',
}

# Općine of 1993 later merged into a neighbour, with the county their
# territory lies in today.
FORMER_1993 = {
    'HRUŠEVEC KUPLJENSKI': '01', 'SOŠICE': '01',
    'DIVUŠA': '03', 'GORNJI KLASNIĆ': '03', 'JABUKOVAC': '03', 'UTOLICA': '03', 'MEČENČANI': '03',
    'SKAKAVAC': '04', 'SMOLJANAC': '09', 'ŠLJIVOŠEVCI': '14',
    'LISIČIĆ': '13', 'KRUŠEVO': '13', 'SMILČIĆ': '13',
}

# The two kotari (Glina, Knin), special districts of the 1992 law for the
# Serb-majority areas, abolished in 1997. Each is stored as a municipality of
# type `kotar` in the county that holds its seat today: Knin is in
# Šibensko-kninska, though 1993 reports the kotar under Zadarsko-kninska.
DISPLAY = {**DISPLAY, 'local_kotar_assembly': 'Kotarska skupština'}
KOTAR_COUNTY = {'KOTAR GLINA': '03', 'KOTAR KNIN': '15'}
WARD_TYPES = {**WARD_TYPES, 'kotar': WARD_TYPES['muni']}


class Local1993Importer(Local1997Importer):

    year = 1993
    display = DISPLAY

    def run(self):
        folder = LocalImporter.DATA_DIR / '1993' / 'ocr'
        contests, problems, notes = parse_report(folder)
        for n in notes:
            self.log(f'  note: {n}')
        if problems:
            raise RuntimeError('1993 report does not reconcile:\n  ' + '\n  '.join(problems))
        canonicalize([c for _code, c in contests])
        # Lobor and Kali print two independent lists under one bare name;
        # numbered by printed position they stay two lists, where one shared
        # name would fold the second's votes into the first and lose them.
        for _code, c in contests:
            names = [list_name(e) for e in c['entries']]
            for n, e in enumerate(c['entries'], 1):
                if names.count(list_name(e)) > 1 and not e['holder']:
                    e['holder'] = f'lista {n}.'
        self._names = self._name_dictionary()
        n_wards = sum(len(c['wards']) for _code, c in contests)
        self.log(f'Parsed {len(contests)} bodies and {n_wards} wards, all reconciling '
                 f'({sum(c["not_held"] for _k, c in contests)} wards not held)')
        # Two bodies of one place means a heading matched the wrong place.
        seen = {}
        for code, c in contests:
            if c['level'] == 'muni':
                muni = self._municipality(self.get_or_create_county(code, ''), c['unit'] or 'ZAGREB')
                if muni.pk in seen and seen[muni.pk] != (code, c['slug']):
                    raise RuntimeError(f'{c["unit"]} and {seen[muni.pk]} both match {muni.name}')
                seen[muni.pk] = (code, c['slug'])
        for code, c in contests:
            if c['entries']:
                self._import_contest(code, c)
            self._import_wards(code, c)
        self.flush_all()
        got = set(m.pk for m in self.matched.values())
        self.log(f'Matched {len(got)} municipalities')

    def _municipality(self, county, unit):
        """The municipality a 1993 heading names: under its later name
        (`ALIASES_1993`), in the report's county, else — since county lines
        moved in 1997 (Vojnić, Vrginmost and Lasinja went from
        Sisačko-moslavačka to Karlovačka, Našice from Požeško-slavonska to
        Osječko-baranjska, Udbina and Donji Lapac from Zadarsko-kninska to
        Ličko-senjska) — the one place of that name anywhere in Croatia.
        An općina later merged into a neighbour is created in today's
        county (`FORMER_1993`)."""
        key = (county.pk, unit)
        if key in self.matched:
            return self.matched[key]
        name = ALIASES_1993.get(unit, unit)
        if name in FORMER_1993:
            home = self.get_or_create_county(FORMER_1993[name], '')
            self.matched[key] = self.get_or_create_municipality(home, name, 'općina')
            return self.matched[key]
        # An exact name first, in the county and then anywhere: the stem
        # match would take PAG for PERUŠIĆ (Pag moved to Zadarska in 1997).
        from elections.models import Municipality
        if not hasattr(self, '_live'):
            self._live = self._live_municipalities()
        live = [m for m in Municipality.objects.filter(pk__in=self._live)]
        exact = [m for m in live if _words(m.name) == _words(name)]
        exact = [m for m in exact if m.county_id == county.pk] or exact
        if len(exact) == 1:
            self.matched[key] = exact[0]
            return exact[0]
        try:
            muni = Local1997Importer._municipality(self, county, name)
        except RuntimeError:
            from elections.models import County
            hits = []
            for other in County.objects.exclude(pk=county.pk).filter(code__regex=r'^(0[1-9]|1[0-9]|2[01])$'):
                try:
                    hits.append(Local1997Importer._municipality(self, other, name))
                except RuntimeError:
                    pass
            # An exact name beats a stem match (KRIŽ, not KRK or KRŠAN).
            exact = [m for m in hits if _words(m.name) == _words(name)]
            hits = exact or hits
            if len(hits) != 1:
                raise RuntimeError(f'County {county.code}: "{unit}" matches '
                                   f'{[m.name for m in hits] or "nothing"} anywhere')
            muni = hits[0]
        self.matched[key] = muni
        return muni

    def _place(self, code, c):
        if c['level'] == 'kotar':
            county = self.get_or_create_county(KOTAR_COUNTY[c['unit']], '')
            muni = self.get_or_create_municipality(county, c['unit'], 'kotar')
            self.matched[(county.pk, c['unit'])] = muni
            station = self.get_or_create_polling_station(muni, '000', muni.name, 'sažetak', '')
            return station, muni.pk, muni.name
        return super()._place(code, c)

    def _import_wards(self, code, c):
        if not c['wards']:
            return
        slug, name = WARD_TYPES[c['level']]
        election_type = self.get_or_create_election_type(slug, name, parent_slug='local')
        election = self.get_or_create_election(election_type, self.year, f'{name} {self.year}')
        election_round = self.get_or_create_round(election, 1)
        station, number, place = self._place(code, c)
        for ward in c['wards']:
            i = ward['number']
            district = self.get_or_create_district(
                election, number * 100 + i, f'{place}, {ROMAN_OF[i]}. izborna jedinica')
            fig = ward.get('figures') or {}
            if {'registered', 'cast'} <= fig.keys() and district.registered_voters is None:
                district.registered_voters = fig['registered']
                district.ballots_cast = fig['cast']
                district.invalid_ballots = fig.get('invalid')     # Buzet XII leaves it blank
                district.save(update_fields=['registered_voters', 'ballots_cast', 'invalid_ballots'])
            seen = set()
            for cand in ward['candidates']:
                person_name = clean_candidate_name(self._name(ward, cand).split(',')[0].upper())
                if len(person_name.split()) < 2:
                    raise RuntimeError(f'{place} ward {i}: no full name for {cand}')
                party = cand['party']
                label = f'{person_name} ({party})' if party else person_name
                el_list = self.get_or_create_electoral_list(election_round, label, district)
                if person_name in seen:
                    person = self._namesake(person_name, f'{place}, 1993. ({party})')
                else:
                    person = self.get_or_create_person(person_name)
                seen.add(person_name)
                candidacy = self.get_or_create_candidacy(person, el_list, 1)
                if cand['votes'] is not None:
                    self.create_candidate_result(candidacy, station, cand['votes'])
                    self.create_list_result(el_list, station, cand['votes'])
