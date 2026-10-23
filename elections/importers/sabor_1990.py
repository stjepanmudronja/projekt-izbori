"""Import the 1990 elections to the Društveno-političko vijeće and the Vijeće
općina of the Sabor.

Both chambers share one shape, so one importer serves both, picked by
`chamber` ('dpv' or 'vo'); everything below is said of the DPV and holds for
the Vijeće općina (`sabor_vo`, 115 units) too, except where noted.

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
figure. The one exception is the Vijeće općina's city-wide Zagreb unit, whose
voters also voted in their own Zagreb općina; units listed in the data
module's `OVERLAPPING_UNITS` keep their electorate on the ElectoralDistrict
instead, as 1992/1995 do. There is still no per-station data, so each unit is one pseudo station
under county `99 REPUBLIKA HRVATSKA (sažetak)`. Valid ballots are taken as the
sum of the candidates, which can fall short of `cast - invalid` — see the data
module for why the report's own figures leave that gap.

The winner of each unit is stored as a ParliamentMember linked to the Candidacy
of the deciding round; `sabor_seat_winner_candidacy_ids()` reads those rows for
this chamber instead of running D'Hondt.
"""
from collections import Counter
from datetime import date

from . import sabor_1990_dpv_data, sabor_1990_vo_data
from .base import BaseImporter
from .sabor_1990_dpv_data import party_label, person_name

CHAMBERS = {'dpv': sabor_1990_dpv_data, 'vo': sabor_1990_vo_data}

ROUND_DATES = {1: date(1990, 4, 22), 2: date(1990, 5, 6)}

SYNTH_COUNTY_CODE = '99'
SYNTH_COUNTY_NAME = 'REPUBLIKA HRVATSKA (sažetak)'


class Sabor1990Importer(BaseImporter):
    YEARS = (1990,)

    def __init__(self, chamber='dpv', year=1990, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year
        self.data = CHAMBERS[chamber]

    def run(self, only_district=None):
        data = self.data
        etype = self.get_or_create_election_type(data.ELECTION_TYPE_SLUG, data.ELECTION_TYPE_NAME)
        election = self.get_or_create_election(
            etype, self.year, f'{data.ELECTION_TYPE_NAME} {self.year}', date=ROUND_DATES[1])
        rounds = {n: self.get_or_create_round(election, n) for n in ROUND_DATES}
        self.county = self.get_or_create_county(SYNTH_COUNTY_CODE, SYNTH_COUNTY_NAME)

        members = 0
        for number, unit in sorted(data.DISTRICTS.items()):
            if only_district is not None and number != only_district:
                continue
            members += self._import_unit(election, rounds, number, unit)

        self.flush_all()
        runoffs = sum(1 for u in data.DISTRICTS.values() if len(u['rounds']) > 1)
        self.log(f'{data.ELECTION_TYPE_NAME} {self.year}: {members} members recorded '
                 f'({len(data.DISTRICTS)} units, {runoffs} decided in round 2)')

    def _import_unit(self, election, rounds, number, unit):
        label = f"{number}. izborna jedinica - {unit['name']}"
        district = self.get_or_create_district(election, number, label)
        muni = self.get_or_create_municipality(
            self.county, f'{label.upper()} (SAŽETAK)', 'sažetak')
        station = self.get_or_create_polling_station(muni, '001', label, 'sažetak', '')

        # A unit whose voters are counted elsewhere too (the Vijeće općina's
        # city-wide Zagreb unit) keeps its electorate on the district only, as
        # 1992/1995 do, so turnout totals never count those voters twice.
        overlapping = number in getattr(self.data, 'OVERLAPPING_UNITS', ())
        if overlapping:
            if len(unit['rounds']) != 1:
                raise ValueError(f'unit {number}: an overlapping unit must have one round')
            rnd = unit['rounds'][0]
            district.registered_voters = rnd['registered']
            district.ballots_cast = rnd['cast']
            district.invalid_ballots = rnd['invalid']
            district.save(update_fields=['registered_voters', 'ballots_cast', 'invalid_ballots'])

        deciding = None
        for round_no, rnd in enumerate(unit['rounds'], 1):
            er = rounds[round_no]
            valid = sum(v for _n, _res, _p, v in rnd['candidates'])
            if not overlapping:
                self.create_turnout(er, station, rnd['registered'], rnd['cast'],
                                    valid, rnd['invalid'])
            names = self._list_names(rnd['candidates'])
            for raw, residence, party, votes in rnd['candidates']:
                el = self.get_or_create_electoral_list(er, names[raw], district)
                person = self.get_or_create_person(person_name(raw))
                candidacy = self.get_or_create_candidacy(person, el, 1)
                if candidacy.residence != residence:
                    candidacy.residence = residence
                    candidacy.save(update_fields=['residence'])
                self.create_list_result(el, station, votes)
                self.create_candidate_result(candidacy, station, votes)
                if raw == unit['winner'] and round_no == len(unit['rounds']):
                    deciding = (candidacy, party)

        if deciding is None:
            raise ValueError(f"unit {number}: winner {unit['winner']!r} not in its last round")
        candidacy, party = deciding
        self._record_member(election, unit['winner'], party_label(party), district, candidacy)
        return 1

    def _list_names(self, candidates):
        """Candidate -> stored list name: the nominating party, with the
        candidate appended where a label repeats in the same round (two HDZ
        candidates stood in several units, and independents often)."""
        counts = Counter(party for _n, _r, party, _v in candidates)
        out = {}
        for raw, _res, party, _v in candidates:
            parties = self.data.PARTIES
            label = parties[party] if party in parties else party_label(party)
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
                     .filter(loose=normalized.replace('-', ' '), disambiguation='').first())
            if loose:
                self._person_cache[normalized] = loose
        return super().get_or_create_person(full_name)

    def _record_member(self, election, raw_name, party, district, candidacy):
        from elections.models import ParliamentMember
        # The candidacy's person, which may be a namesake `split_persons`
        # carved off; looking the name up again would find the catch-all row.
        person = (candidacy.person if candidacy is not None
                  else self.get_or_create_person(person_name(raw_name)))
        ParliamentMember.objects.update_or_create(
            election=election, person=person,
            defaults={'party': party, 'minority': False, 'district': district,
                      'candidacy': candidacy, 'note': ''},
        )
