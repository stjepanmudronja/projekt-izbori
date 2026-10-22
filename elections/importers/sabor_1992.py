"""Import the 1992 election to the Zastupnički dom of the Sabor.

The same chamber as every other `sabor` year, but — like 1995, and differently
from it — a mixed system the generic importers cannot express:

  * **60 seats on one countrywide list**, D'Hondt with a 3% threshold. The
    report gives that list's vote broken down by unit, so unlike 1995 the list
    vote is stored per unit (one pseudo station each), plus the abroad
    committees and a residual for the ballots outside the regular electorate —
    see `LIST_RESIDUAL` in the data module for why that row exists.
  * **60 single-member districts** decided by plurality, one round.
  * **4 special units** for the smaller minorities, one seat each.
  * **13 + 1 members taken from the lists**, not elected separately: the Serb
    community's census share, and one more to reach the 5 seats guaranteed to
    the smaller minorities. Their names come from the report.

Nothing is allocated here: the report names all 138 members, so they are
stored as ParliamentMember rows — linked to their Candidacy where they won a
personal contest — and `sabor_seat_winner_candidacy_ids()` reads those rather
than running D'Hondt over data shaped nothing like a 14-seat district.

District numbering inside this election:

    1-60     the single-member districts I-LX
    65       the countrywide list ("Državna lista")
    121-124  the four special minority units (report units 61-64), following
             the 121+ convention that marks minority districts elsewhere

**Turnout is stored once, nationally.** The 64 contests and the list ballot
count the same voters again, and the per-unit list rolls do not even sum to the
national roll, so a single TurnoutData row carries the report's national
figures. The per-unit figures live in `sabor_1992_data` and are served from
there by the 1992 view. No per-station data exists, so everything hangs off
pseudo stations under county `99 REPUBLIKA HRVATSKA (sažetak)`.
"""
from collections import Counter
from datetime import date

from .base import BaseImporter
from .sabor_1992_data import (
    LISTS, NATIONAL, SERB_SEATS, EXTRA_MINORITY_SEAT, DISTRICTS, MINORITY_UNITS,
    LIST_BY_UNIT, LIST_ABROAD, LIST_RESIDUAL, ROMAN, person_name,
)

NATIONAL_DISTRICT = 65
MINORITY_DISTRICT_OFFSET = 60

SYNTH_COUNTY_CODE = '99'
SYNTH_COUNTY_NAME = 'REPUBLIKA HRVATSKA (sažetak)'

class Sabor1992Importer(BaseImporter):
    YEARS = (1992,)

    def __init__(self, year=1992, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year

    def run(self, only_district=None):
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(
            election_type, self.year, f'Parlamentarni izbori {self.year}',
            date=date(1992, 8, 2))
        er = self.get_or_create_round(election, 1)
        self.county = self.get_or_create_county(SYNTH_COUNTY_CODE, SYNTH_COUNTY_NAME)

        members = 0
        if only_district in (None, NATIONAL_DISTRICT):
            members += self._import_national(election, er)

        for number, entry in sorted(DISTRICTS.items()):
            if only_district is not None and number != only_district:
                continue
            label = f"{ROMAN[number - 1]}. izborna jedinica - {entry['name']}"
            members += self._import_race(election, er, entry, number, label)

        for unit, entry in sorted(MINORITY_UNITS.items()):
            dnum = unit + MINORITY_DISTRICT_OFFSET
            if only_district is not None and dnum != only_district:
                continue
            label = f"{unit - 60}. posebna izborna jedinica - {entry['minority']}"
            members += self._import_race(election, er, entry, dnum, label, minority=True)

        self.flush_all()
        self.log(f'Parlamentarni izbori {self.year}: {members} members recorded '
                 f'({len(DISTRICTS)} single-member districts, '
                 f'{len(MINORITY_UNITS)} minority units, {len(LIST_BY_UNIT)} list units)')

    def get_or_create_person(self, full_name):
        """Hyphen-tolerant, like `set_sabor_members._find_person`.

        The report writes "Dabčević-Kučar" where earlier imports stored
        "Dabčević Kučar". `merge_person_aliases` folds that split, but an
        exact-key lookup on the next re-import would create the hyphenated row
        again — and a second ParliamentMember with it.
        """
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

    # ---- geography ------------------------------------------------------

    def _station_for(self, label):
        """One pseudo station per contest or list unit — nothing finer exists."""
        muni = self.get_or_create_municipality(
            self.county, f'{label.upper()} (SAŽETAK)', 'sažetak')
        return self.get_or_create_polling_station(muni, '001', label, 'sažetak', '')

    # ---- the countrywide list -------------------------------------------

    def _import_national(self, election, er):
        district = self.get_or_create_district(election, NATIONAL_DISTRICT, 'Državna lista')
        lists = [self.get_or_create_electoral_list(er, name, district) for name in LISTS]

        total = self._station_for('Državna lista - ukupno')
        self.create_turnout(er, total, NATIONAL['registered'], NATIONAL['cast'],
                            NATIONAL['valid'], NATIONAL['invalid'])

        rows = []
        for unit, (_reg, _cast, _inv, votes) in sorted(LIST_BY_UNIT.items()):
            if unit <= 60:
                label = f"Državna lista - {ROMAN[unit - 1]}. IJ {DISTRICTS[unit]['name']}"
            else:
                label = f"Državna lista - {unit - 60}. posebna IJ {MINORITY_UNITS[unit]['name']}"
            rows.append((label, votes))
        rows.append(('Državna lista - inozemstvo', LIST_ABROAD[3]))
        rows.append(('Državna lista - izvan redovitog biračkog tijela', LIST_RESIDUAL[2]))

        for label, votes in rows:
            station = self._station_for(label)
            for el, v in zip(lists, votes):
                self.create_list_result(el, station, v)

        n = 0
        for idx, _seats, names in NATIONAL['seats_by_list']:
            for raw in names:
                self._record_member(election, raw, LISTS[idx], district)
                n += 1
        for idx, names in SERB_SEATS:
            for raw in names:
                self._record_member(election, raw, LISTS[idx], district, minority=True,
                                    note='srpska nacionalna zajednica (čl. 26. st. 1.)')
                n += 1
        idx, raw, community = EXTRA_MINORITY_SEAT
        self._record_member(election, raw, LISTS[idx], district, minority=True,
                            note=f'{community} zajednica (čl. 26. st. 2.)')
        return n + 1

    # ---- candidate contests (60 districts, 4 minority units) ------------

    def _import_race(self, election, er, entry, number, label, minority=False):
        district = self.get_or_create_district(election, number, label)
        # The contest's own electorate, kept on the district rather than in
        # TurnoutData (see below) so the results view can read it back.
        district.registered_voters = entry['registered']
        district.ballots_cast = entry['cast']
        district.invalid_ballots = entry['invalid']
        district.save(update_fields=['registered_voters', 'ballots_cast', 'invalid_ballots'])
        station = self._station_for(label)
        # No turnout row: the national one already counts these voters.
        names = self._list_names(entry['candidates'])
        n = 0
        for raw_name, party, votes in entry['candidates']:
            el = self.get_or_create_electoral_list(er, names[raw_name], district)
            person = self.get_or_create_person(person_name(raw_name))
            candidacy = self.get_or_create_candidacy(person, el, 1)
            self.create_list_result(el, station, votes)
            self.create_candidate_result(candidacy, station, votes)
            if raw_name == entry['winner']:
                self._record_member(election, raw_name, party, district,
                                    candidacy=candidacy, minority=minority)
                n += 1
        return n

    @staticmethod
    def _list_names(candidates):
        """Candidate name -> stored list name: the nominating party, with the
        candidate appended where a label repeats (several independents per
        district), as sabor_1995 does."""
        counts = Counter(party for _n, party, _v in candidates)
        return {raw: (f'{party} - {person_name(raw)}' if counts[party] > 1 else party)
                for raw, party, _v in candidates}

    # ---- members --------------------------------------------------------

    def _record_member(self, election, raw_name, party, district,
                       candidacy=None, minority=False, note=''):
        from elections.models import ParliamentMember
        person = self.get_or_create_person(person_name(raw_name))
        ParliamentMember.objects.update_or_create(
            election=election, person=person,
            defaults={'party': party, 'minority': minority,
                      'district': district, 'candidacy': candidacy, 'note': note},
        )
