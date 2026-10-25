"""Import the 1997 lokalni izbori (13 April 1997) from DIP's scanned reports.

The parsing, OCR checks and repairs live in `local_1997_parse.py`; this
stores what it returns. 1997 used a mixed system, so each body yields two
kinds of contest:

- **the list part**, stored as every later year stores a council or assembly
  (`Local2009Importer._import_contest`): one `000` pseudo station per
  municipality (county assemblies on the `<ŽUPANIJA> (SAŽETAK)` station),
  list names folded across the report by `local_2001_parse.canonicalize`,
  valid votes = the lists' sum (no valid figure is printed);
- **the single-member wards** ("izborne jedinice"), under their own election
  types — `local_council_ward` and `local_county_assembly_ward` — so ward
  votes never add into a list total. Each ward is an ElectoralDistrict
  numbered `place_pk * 100 + ward` with its printed electorate (assembly wards
  only) on the district's display columns, as 1992/1995 do; each candidate is
  a Candidacy on a list named "NAME (PARTY)". Wards carry no TurnoutData, so
  Izlaznost never sees them. An unopposed candidate (no count printed) gets
  no result row.
"""
import re
from pathlib import Path

from .local import LocalImporter
from .local_2001_parse import canonicalize
from .local_2009 import Local2009Importer, DISPLAY
from .local_1997_parse import ROMAN_OF, _tokens, choose_name, fold, parse_report
from .name_utils import clean_candidate_name

WARD_TYPES = {
    'muni': ('local_council_ward', 'Vijeće — izborne jedinice'),
    'county': ('local_county_assembly_ward', 'Županijska skupština — izborne jedinice'),
}


# Općine of 1997 that later merged into a neighbour and so have no row from
# any later year: created here, in their county.
FORMER_MUNICIPALITIES = {'TENJA': 'TENJA', 'MIRKOVCI': 'MIRKOVCI', 'ORLIĆ': 'ORLIĆ'}


class Local1997Importer(Local2009Importer):

    year = 1997

    def _municipality(self, county, unit):
        if unit in FORMER_MUNICIPALITIES:
            key = (county.pk, unit)
            if key not in self.matched:
                self.matched[key] = self.get_or_create_municipality(
                    county, FORMER_MUNICIPALITIES[unit], 'općina')
            return self.matched[key]
        return super()._municipality(county, unit)

    def run(self):
        folder = LocalImporter.DATA_DIR / '1997' / 'ocr'
        contests, problems, notes = parse_report(folder)
        for n in notes:
            self.log(f'  note: {n}')
        if problems:
            raise RuntimeError('1997 report does not reconcile:\n  ' + '\n  '.join(problems))
        canonicalize([c for _code, c in contests])
        n = sum(1 for _c, c in contests for w in c['wards'] for x in w['candidates'] if x.get('crop_name'))
        self.log(f'{n} ward candidates have a second (name-column) reading' if n else
                 'No names.tsv: ward names use the page reading only')
        self._names = self._name_dictionary()
        n_wards = sum(len(c['wards']) for _code, c in contests)
        self.log(f'Parsed {len(contests)} bodies and {n_wards} wards, all reconciling')

        for code, c in contests:
            if c['entries']:
                self._import_contest(code, c)
            self._import_wards(code, c)
        self.flush_all()
        live = self._live_municipalities()
        got = set(m.pk for m in self.matched.values())
        self.log(f'Matched {len(got)} municipalities; {len(live - got)} with 2013 results got none')

    def create_turnout(self, election_round, polling_station, registered, cast, valid, invalid):
        # A figure the report leaves blank is stored as 0; a body printing
        # none at all (Berek, Hercegovac) gets no turnout row.
        if registered is None and cast is None and invalid is None:
            return
        return super().create_turnout(election_round, polling_station, registered or 0, cast or 0,
                                      valid or 0, invalid or 0)

    def _namesake(self, name, label):
        from elections.models import Person
        from .name_utils import normalize_person_name, parse_person_name
        first, last = parse_person_name(name)
        person, _ = Person.objects.get_or_create(
            normalized_name=normalize_person_name(name), disambiguation=label,
            defaults={'first_name': first, 'last_name': last})
        return person

    def _name_dictionary(self):
        """First and last name words of every Person on record, with their
        diacritics — what `choose_name` prefers between two readings."""
        from elections.models import Person
        first, last = set(), set()
        for f, l in Person.objects.values_list('first_name', 'last_name'):
            first.update(w.upper() for w in (f or '').split())
            last.update(w.upper() for w in re.split(r'[\s-]+', l or '') if w)
        return first, last

    def _name(self, ward, cand):
        if ward.get('manual'):
            return cand['name']
        first, last = self._names
        name = choose_name(cand['name'], cand.get('crop_name'), first, last)
        if len(name.split(',')[0].split()) < 2 and fold(cand.get('party', '')).startswith('nk '):
            name = cand['party'][3:].strip()        # an independent's label repeats the name
        # The winner's name is printed a third time, on the "Izabran(a) je" line.
        win = ward.get('winner_name') or ''
        if win and fold(_tokens(win) and ' '.join(_tokens(win)) or '') != fold(name.split(',')[0]):
            words = _tokens(win)
            if cand is max(ward['candidates'], key=lambda x: x['votes'] or -1) and words and \
                    words[0].upper() in first and words[-1].upper() in last and \
                    not (name.split()[0].upper() in first and name.split(',')[0].split()[-1].upper() in last):
                name = ' '.join(words)
        return name

    def _import_wards(self, code, c):
        if not c['wards']:
            return
        slug, name = WARD_TYPES[c['level']]
        election_type = self.get_or_create_election_type(slug, name, parent_slug='local')
        election = self.get_or_create_election(election_type, self.year, f'{name} {self.year}')
        election_round = self.get_or_create_round(election, 1)
        station, number, place = self._place(code, c)
        # Vinkovci's wards I-II were on pages missing from the scan.
        for i, ward in enumerate(c['wards'], 1 + c.get('ward_offset', 0)):
            district = self.get_or_create_district(
                election, number * 100 + i, f'{place}, {ROMAN_OF[i]}. izborna jedinica')
            fig = ward.get('figures') or {}
            if fig and district.registered_voters is None:
                district.registered_voters = fig.get('registered')
                district.ballots_cast = fig.get('cast')
                district.invalid_ballots = fig.get('invalid')
                district.save(update_fields=['registered_voters', 'ballots_cast', 'invalid_ballots'])
            seen = set()
            for cand in ward['candidates']:
                # A title follows a comma ("Anto Beljan, upr. pravnik"); the
                # person is what precedes it.
                person_name = clean_candidate_name(self._name(ward, cand).split(',')[0].upper())
                label = f"{person_name} ({cand['party']})" if cand['party'] else person_name
                el_list = self.get_or_create_electoral_list(election_round, label, district)
                if person_name in seen:
                    # Two candidates of one name in one ward (Generalski Stol
                    # III's two Jure Katićs): different people, the second
                    # labelled by place and party.
                    person = self._namesake(person_name, f"{place}, 1997. ({cand['party']})")
                else:
                    person = self.get_or_create_person(person_name)
                seen.add(person_name)
                candidacy = self.get_or_create_candidacy(person, el_list, 1)
                if cand['votes'] is not None:
                    self.create_candidate_result(candidacy, station, cand['votes'])
                    self.create_list_result(el_list, station, cand['votes'])
