"""Import the 1995 election to the Zastupnički dom of the Sabor.

Same chamber as 2000 onward — so this lands under the ordinary `sabor`
ElectionType and its year sits in the normal Sabor year list — but a different
electoral system from every other year in the database, and one that no
existing importer can express:

  * **Four separate contests, not one.** 80 seats on a single countrywide
    proportional list, 12 from the diaspora "posebne liste", 28 from
    single-member plurality districts, and 7 from 5 national-minority units.
    `DISTRICTS` here therefore means something different from `DISTRICTS`
    anywhere else: 28 seats-of-one, not 10 multi-member constituencies.
  * **No D'Hondt to run.** The report states the seats and names the members,
    so nothing is allocated. The single-member districts are decided by a plain
    plurality, and the proportional seats come from the source — which matters
    because the generic Sabor allocator assumes 14 seats per district and would
    invent a completely different parliament from this data.
  * **No per-station data exists.** DIP published one set of figures per
    contest and nothing below it, so each contest gets a single pseudo polling
    station under the synthetic county `99 REPUBLIKA HRVATSKA (sažetak)`, the
    same device `import_presidential_1997` uses. Per-station, per-municipality
    and per-county views are therefore legitimately empty for 1995, and county
    `99` must not be summed alongside the real counties.

District numbering inside this election:

    1-28     the single-member districts, in the report's Roman order
    29       the countrywide list ("Državna lista")
    30       the diaspora lists ("Posebne liste")
    121-125  the five national-minority units, following the 121+ convention
             that marks minority districts everywhere else in the schema

Candidates in the 28 districts and the 5 minority units are real named
candidates with real vote counts, so each gets an ElectoralList (named for the
party or coalition that nominated them), a Candidacy and a CandidateResult —
which is what puts them in cross-election politician search. The 80 + 12
proportional members have no personal vote to record and are stored only as
ParliamentMember rows, exactly like the 2003/2007/2011 rosters. All 127 members
get a ParliamentMember row; the 35 elected personally also carry a link to
their Candidacy.

See `sabor_1995_data.py` for the transcription and the checks it satisfies.
"""
from collections import Counter
from datetime import date

from .base import BaseImporter
from .name_utils import clean_candidate_name
from .sabor_1995_data import NATIONAL, DIASPORA, DISTRICTS, MINORITY_UNITS

ROMAN = [
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
    'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII',
]

NATIONAL_DISTRICT = 29
DIASPORA_DISTRICT = 30
MINORITY_DISTRICT_BASE = 120

SYNTH_COUNTY_CODE = '99'
SYNTH_COUNTY_NAME = 'REPUBLIKA HRVATSKA (sažetak)'


class Sabor1995Importer(BaseImporter):
    YEARS = (1995,)

    def __init__(self, year=1995, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year

    def run(self, only_district=None):
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(
            election_type, self.year, f'Parlamentarni izbori {self.year}',
            date=date(1995, 10, 29))
        er = self.get_or_create_round(election, 1)
        self.county = self.get_or_create_county(SYNTH_COUNTY_CODE, SYNTH_COUNTY_NAME)

        members = 0
        if only_district in (None, NATIONAL_DISTRICT):
            members += self._import_proportional(
                election, er, NATIONAL, NATIONAL_DISTRICT, 'Državna lista')
        if only_district in (None, DIASPORA_DISTRICT):
            members += self._import_proportional(
                election, er, DIASPORA, DIASPORA_DISTRICT, 'Posebne liste - dijaspora')

        for number, entry in sorted(DISTRICTS.items()):
            if only_district is not None and number != only_district:
                continue
            members += self._import_race(
                election, er, entry, number, f'{ROMAN[number - 1]}. izborna jedinica',
                [entry['winner']])

        for number, unit in sorted(MINORITY_UNITS.items()):
            dnum = MINORITY_DISTRICT_BASE + number
            if only_district is not None and dnum != only_district:
                continue
            label = f"{number}. posebna izborna jedinica - {unit['minority']}"
            members += self._import_race(
                election, er, unit, dnum, label, unit['winners'], minority=True)

        self.flush_all()
        self.log(f'Parlamentarni izbori {self.year}: {members} members recorded '
                 f'({len(DISTRICTS)} single-member districts, '
                 f'{len(MINORITY_UNITS)} minority units)')

    # ---- geography ------------------------------------------------------

    def _station_for(self, label):
        """One pseudo station per contest — there is no finer breakdown."""
        muni = self.get_or_create_municipality(
            self.county, f'{label.upper()} (SAŽETAK)', 'sažetak')
        return self.get_or_create_polling_station(muni, '001', label, 'sažetak', '')

    # ---- proportional contests (national list, diaspora) ----------------

    def _import_proportional(self, election, er, data, number, label):
        district = self.get_or_create_district(election, number, label)
        station = self._station_for(label)
        self.create_turnout(er, station, data['registered'], data['cast'],
                            data['valid'], data['invalid'])
        for name, votes, _pct in data['lists']:
            el = self.get_or_create_electoral_list(er, name, district)
            self.create_list_result(el, station, votes)

        n = 0
        for list_name, _seats, names in data['seats_by_list']:
            for raw in names:
                self._record_member(election, raw, list_name, district)
                n += 1
        return n

    # ---- candidate contests (28 districts, 5 minority units) ------------

    def _import_race(self, election, er, entry, number, label, winners, minority=False):
        district = self.get_or_create_district(election, number, label)
        station = self._station_for(label)
        # No turnout row on purpose: the same voters are counted again here.
        # A domestic elector cast a district ballot *and* a national-list one,
        # and a minority elector a unit ballot on top of that, so summing all
        # 35 contests would report a 7.8-million electorate. Districts 29 and
        # 30 alone partition the roll exactly once, so every national, county
        # and municipality aggregate stays right without special-casing 1995 —
        # the same reasoning that makes sabor.py skip district 12's turnout.
        # The per-district figures live in `sabor_1995_data` and are served
        # from there by the 1995 view.
        names = self._list_names(entry['candidates'])
        winner_set = set(winners)
        n = 0
        for raw_name, party, votes, _pct in entry['candidates']:
            el = self.get_or_create_electoral_list(er, names[raw_name], district)
            person = self.get_or_create_person(clean_candidate_name(raw_name).upper())
            candidacy = self.get_or_create_candidacy(person, el, 1)
            self.create_list_result(el, station, votes)
            self.create_candidate_result(candidacy, station, votes)
            if raw_name in winner_set:
                self._record_member(election, raw_name, party, district,
                                    candidacy=candidacy, minority=minority)
                n += 1
        return n

    @staticmethod
    def _list_names(candidates):
        """Candidate name -> stored list name.

        Each candidate stands on their own list, named for the party or
        coalition that nominated them. Several run as "Nezavisni kandidat" in
        the same district (three of them in district XXVII), so a repeated name
        takes the candidate's own as a suffix — the same disambiguation
        `sabor_legacy` applies to its many "NEOVISNA LISTA" entries.
        """
        counts = Counter(party for _n, party, _v, _p in candidates)
        out = {}
        for raw_name, party, _votes, _pct in candidates:
            name = party
            if counts[party] > 1:
                name = f'{party} - {clean_candidate_name(raw_name).upper()}'
            out[raw_name] = name
        return out

    # ---- members --------------------------------------------------------

    def _record_member(self, election, raw_name, party, district,
                       candidacy=None, minority=False):
        from elections.models import ParliamentMember
        name = clean_candidate_name(raw_name).upper()
        person = self.get_or_create_person(name)
        ParliamentMember.objects.update_or_create(
            election=election, person=person,
            defaults={'party': party, 'minority': minority,
                      'district': district, 'candidacy': candidacy, 'note': ''},
        )
