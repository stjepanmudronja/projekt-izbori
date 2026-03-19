import sys
from django.db import transaction
from elections.models import (
    County, Municipality, PollingStation,
    ElectionType, Election, ElectionRound, ElectoralDistrict,
    Person, Party, ElectoralList, Candidacy,
    TurnoutData, ListResult, CandidateResult,
)
from .name_utils import normalize_person_name, parse_person_name


BATCH_SIZE = 5000


class BaseImporter:
    """Shared logic for all election data importers."""

    def __init__(self, stdout=None):
        self.stdout = stdout or sys.stdout
        # Caches to avoid repeated DB lookups
        self._county_cache = {}
        self._municipality_cache = {}
        self._polling_station_cache = {}
        self._person_cache = {}
        # Bulk insert buffers
        self._turnout_buffer = []
        self._list_result_buffer = []
        self._candidate_result_buffer = []

    def log(self, msg):
        self.stdout.write(f"{msg}\n")

    # --- Geography helpers ---

    def get_or_create_county(self, code, name):
        code = str(code).zfill(2)
        key = code
        if key not in self._county_cache:
            obj, _ = County.objects.get_or_create(code=code, defaults={'name': name})
            self._county_cache[key] = obj
        return self._county_cache[key]

    def get_or_create_municipality(self, county, name, mtype):
        key = (county.id, name)
        if key not in self._municipality_cache:
            # Normalize type
            mtype_lower = mtype.lower().strip()
            type_map = {
                'grad': 'grad',
                'općina': 'općina',
                'opcina': 'općina',
                'op ina': 'općina',
                'država': 'država',
                'drzava': 'država',
                'dr ava': 'država',
            }
            normalized_type = type_map.get(mtype_lower, mtype_lower)
            obj, _ = Municipality.objects.get_or_create(
                county=county, name=name,
                defaults={'type': normalized_type}
            )
            self._municipality_cache[key] = obj
        return self._municipality_cache[key]

    def get_or_create_polling_station(self, municipality, number, name, location='', address=''):
        number = str(number).zfill(3)
        key = (municipality.id, number)
        if key not in self._polling_station_cache:
            obj, _ = PollingStation.objects.get_or_create(
                municipality=municipality, number=number,
                defaults={'name': name, 'location': location, 'address': address}
            )
            self._polling_station_cache[key] = obj
        return self._polling_station_cache[key]

    # --- Election helpers ---

    def get_or_create_election_type(self, slug, name, parent_slug=None):
        parent = None
        if parent_slug:
            parent, _ = ElectionType.objects.get_or_create(
                slug=parent_slug, defaults={'name': parent_slug.replace('_', ' ').title()}
            )
        obj, _ = ElectionType.objects.get_or_create(slug=slug, defaults={'name': name, 'parent': parent})
        return obj

    def get_or_create_election(self, election_type, year, name, date=None):
        obj, _ = Election.objects.get_or_create(
            election_type=election_type, year=year, name=name,
            defaults={'date': date}
        )
        return obj

    def get_or_create_round(self, election, round_number):
        obj, _ = ElectionRound.objects.get_or_create(
            election=election, round_number=round_number
        )
        return obj

    def get_or_create_district(self, election, number, name):
        obj, _ = ElectoralDistrict.objects.get_or_create(
            election=election, number=number, defaults={'name': name}
        )
        return obj

    # --- Participant helpers ---

    def get_or_create_person(self, full_name):
        normalized = normalize_person_name(full_name)
        if normalized not in self._person_cache:
            first_name, last_name = parse_person_name(full_name.strip())
            try:
                person = Person.objects.get(normalized_name=normalized)
            except Person.DoesNotExist:
                person = Person.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    normalized_name=normalized,
                )
            self._person_cache[normalized] = person
        return self._person_cache[normalized]

    def get_or_create_party(self, name, short_name=''):
        obj, _ = Party.objects.get_or_create(name=name, defaults={'short_name': short_name})
        return obj

    def get_or_create_electoral_list(self, election_round, name, district=None):
        obj, created = ElectoralList.objects.get_or_create(
            election_round=election_round,
            district=district,
            name=name,
        )
        return obj

    def get_or_create_candidacy(self, person, electoral_list, position):
        obj, _ = Candidacy.objects.get_or_create(
            person=person,
            electoral_list=electoral_list,
            position_on_list=position,
        )
        return obj

    # --- Result helpers (buffered bulk insert) ---

    def create_turnout(self, election_round, polling_station, registered, cast, valid, invalid):
        self._turnout_buffer.append(TurnoutData(
            election_round=election_round,
            polling_station=polling_station,
            registered_voters=registered,
            ballots_cast=cast,
            valid_ballots=valid,
            invalid_ballots=invalid,
        ))
        if len(self._turnout_buffer) >= BATCH_SIZE:
            self._flush_turnout()

    def create_list_result(self, electoral_list, polling_station, votes):
        self._list_result_buffer.append(ListResult(
            electoral_list=electoral_list,
            polling_station=polling_station,
            votes=votes,
        ))
        if len(self._list_result_buffer) >= BATCH_SIZE:
            self._flush_list_results()

    def create_candidate_result(self, candidacy, polling_station, votes):
        self._candidate_result_buffer.append(CandidateResult(
            candidacy=candidacy,
            polling_station=polling_station,
            votes=votes,
        ))
        if len(self._candidate_result_buffer) >= BATCH_SIZE:
            self._flush_candidate_results()

    def _flush_turnout(self):
        if self._turnout_buffer:
            TurnoutData.objects.bulk_create(self._turnout_buffer, ignore_conflicts=True)
            self._turnout_buffer = []

    def _flush_list_results(self):
        if self._list_result_buffer:
            ListResult.objects.bulk_create(self._list_result_buffer, ignore_conflicts=True)
            self._list_result_buffer = []

    def _flush_candidate_results(self):
        if self._candidate_result_buffer:
            CandidateResult.objects.bulk_create(self._candidate_result_buffer, ignore_conflicts=True)
            self._candidate_result_buffer = []

    def flush_all(self):
        """Flush all buffered results to the database."""
        self._flush_turnout()
        self._flush_list_results()
        self._flush_candidate_results()

    # --- Parsing helpers ---

    @staticmethod
    def parse_int(value):
        """Parse an integer, handling Croatian number formatting."""
        if value is None:
            return 0
        s = str(value).strip()
        if s == '' or s == '-':
            return 0
        # Remove dots used as thousands separators
        s = s.replace('.', '')
        # Replace comma with dot for decimal (then truncate)
        s = s.replace(',', '.')
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0
