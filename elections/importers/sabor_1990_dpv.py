"""Import the 1990 election to the Društveno-političko vijeće of the Sabor.

The 1990 Sabor had three chambers, elected separately; this is the
"socio-political council" every adult voted for. It gets its own ElectionType
(`sabor_dpv`), for the same reason the Županijski dom does: it is a different
chamber from the Zastupnički dom of 1992 onward, and its 80 seats must never
join a 151-seat total.

The system is the simplest in the database: **80 single-member units, two-round
majority**. A candidate with a majority in round 1 was elected; otherwise the
vote was repeated two weeks later and the round-2 leader elected. So each unit
is a district (1-80) with one or two rounds, and each round's candidates get an
ElectoralList named for their nominating party, a Candidacy and a
CandidateResult — which is what puts them in cross-election search.

**Turnout is stored per unit per round.** Unlike 1992 and 1995, the units
partition the electorate exactly once, so summing them gives the national
figure. There is still no per-station data, so each unit is one pseudo station
under county `99 REPUBLIKA HRVATSKA (sažetak)`. Valid ballots are taken as the
sum of the candidates, which can fall short of `cast - invalid` — see the data
module for why the report's own figures leave that gap.

The winner of each unit is stored as a ParliamentMember linked to the Candidacy
of the deciding round; `sabor_seat_winner_candidacy_ids()` reads those rows for
this chamber instead of running D'Hondt.
"""
from collections import Counter
from datetime import date

from .base import BaseImporter
from .sabor_1990_dpv_data import (
    DISTRICTS, PARTIES, ELECTION_TYPE_SLUG, ELECTION_TYPE_NAME, party_label, person_name,
)

ROUND_DATES = {1: date(1990, 4, 22), 2: date(1990, 5, 6)}

SYNTH_COUNTY_CODE = '99'
SYNTH_COUNTY_NAME = 'REPUBLIKA HRVATSKA (sažetak)'


class Sabor1990DpvImporter(BaseImporter):
    YEARS = (1990,)

    def __init__(self, year=1990, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year

    def run(self, only_district=None):
        etype = self.get_or_create_election_type(ELECTION_TYPE_SLUG, ELECTION_TYPE_NAME)
        election = self.get_or_create_election(
            etype, self.year, f'{ELECTION_TYPE_NAME} {self.year}', date=ROUND_DATES[1])
        rounds = {n: self.get_or_create_round(election, n) for n in ROUND_DATES}
        self.county = self.get_or_create_county(SYNTH_COUNTY_CODE, SYNTH_COUNTY_NAME)

        members = 0
        for number, unit in sorted(DISTRICTS.items()):
            if only_district is not None and number != only_district:
                continue
            members += self._import_unit(election, rounds, number, unit)

        self.flush_all()
        runoffs = sum(1 for u in DISTRICTS.values() if len(u['rounds']) > 1)
        self.log(f'{ELECTION_TYPE_NAME} {self.year}: {members} members recorded '
                 f'({len(DISTRICTS)} units, {runoffs} decided in round 2)')

    def _import_unit(self, election, rounds, number, unit):
        label = f"{number}. izborna jedinica - {unit['name']}"
        district = self.get_or_create_district(election, number, label)
        muni = self.get_or_create_municipality(
            self.county, f'{label.upper()} (SAŽETAK)', 'sažetak')
        station = self.get_or_create_polling_station(muni, '001', label, 'sažetak', '')

        deciding = None
        for round_no, rnd in enumerate(unit['rounds'], 1):
            er = rounds[round_no]
            valid = sum(v for _n, _res, _p, v in rnd['candidates'])
            self.create_turnout(er, station, rnd['registered'], rnd['cast'],
                                valid, rnd['invalid'])
            names = self._list_names(rnd['candidates'])
            for raw, _residence, party, votes in rnd['candidates']:
                el = self.get_or_create_electoral_list(er, names[raw], district)
                person = self.get_or_create_person(person_name(raw))
                candidacy = self.get_or_create_candidacy(person, el, 1)
                self.create_list_result(el, station, votes)
                self.create_candidate_result(candidacy, station, votes)
                if raw == unit['winner'] and round_no == len(unit['rounds']):
                    deciding = (candidacy, party)

        if deciding is None:
            raise ValueError(f"unit {number}: winner {unit['winner']!r} not in its last round")
        candidacy, party = deciding
        self._record_member(election, unit['winner'], party_label(party), district, candidacy)
        return 1

    @staticmethod
    def _list_names(candidates):
        """Candidate -> stored list name: the nominating party, with the
        candidate appended where a label repeats in the same round (two HDZ
        candidates stood in several units, and independents often)."""
        counts = Counter(party for _n, _r, party, _v in candidates)
        out = {}
        for raw, _res, party, _v in candidates:
            label = PARTIES[party] if party in PARTIES else party_label(party)
            out[raw] = f'{label} - {person_name(raw)}' if counts[party] > 1 else label
        return out

    def get_or_create_person(self, full_name):
        """Hyphen-tolerant, as in `Sabor1992Importer`: a re-import must not
        recreate a hyphen spelling `merge_person_aliases` already folded."""
        from django.db.models import Value
        from django.db.models.functions import Replace
        from elections.models import Person
        from .name_utils import normalize_person_name

        normalized = normalize_person_name(full_name)
        if normalized not in self._person_cache and '-' in normalized:
            loose = (Person.objects
                     .annotate(loose=Replace('normalized_name', Value('-'), Value(' ')))
                     .filter(loose=normalized.replace('-', ' ')).first())
            if loose:
                self._person_cache[normalized] = loose
        return super().get_or_create_person(full_name)

    def _record_member(self, election, raw_name, party, district, candidacy):
        from elections.models import ParliamentMember
        person = self.get_or_create_person(person_name(raw_name))
        ParliamentMember.objects.update_or_create(
            election=election, person=person,
            defaults={'party': party, 'minority': False, 'district': district,
                      'candidacy': candidacy, 'note': ''},
        )
