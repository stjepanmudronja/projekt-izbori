import difflib
import re
import sys
from django.db import transaction
from elections.models import (
    County, Municipality, PollingStation,
    ElectionType, Election, ElectionRound, ElectoralDistrict,
    Person, Party, ElectoralList, Candidacy,
    TurnoutData, ListResult, CandidateResult,
)
from .name_utils import (
    normalize_person_name, parse_person_name, normalize_municipality_name, split_birth_year,
    place_key, strip_diacritics,
)


BATCH_SIZE = 5000


def same_place(row, name, location='', address=''):
    """Whether a stored station is the place a source row names: the same
    building and address where both give one, else the same name (2017's
    exports name only the settlement or mjesni odbor)."""
    if (location or address) and (row.location or row.address):
        if address and row.address:
            if similar_names(address, row.address):
                return True       # same address, building renamed ("ZGRADA GRADSKE UPRAVE" / "UČILIŠTE OTOK")
            # Same building and station under a changed address ("LEPAJCI 22" / "LEPAJCI 4").
            return (bool(location and row.location) and similar_names(location, row.location, numerals=False)
                    and similar_names(name, row.name))
        return similar_names(f'{location} {address}', f'{row.location} {row.address}', numerals=False)
    return similar_names(name, row.name)


_NUMERAL = re.compile(r'^(\d+|[IVXL]+)$')


def similar_names(a, b, numerals=True):
    """Two spellings of one station name: "PULA" / "PULA-POLA, ...",
    "MO LUTVINKA" / "MJESNI ODBOR LUTVINKA", "DUBROVNIK" / "DUBROVNIK G.K.
    MONTOVJERNA". Numbers and Roman numerals must agree, or "KUPINEČKI
    KRALJEVEC I" would be "... II"; for a building (`numerals=False`) a Roman
    numeral only tells its stations apart ("GIMNAZIJA I") and is dropped."""
    def tokens(s):
        s = strip_diacritics((s or '').upper())
        s = re.sub(r'\bM\.?\s*O\.?(?=\s)', 'MJESNI ODBOR', s)
        return re.findall(r'[A-Z0-9]+', s)
    ta, tb = tokens(a), tokens(b)
    if not numerals:
        roman = re.compile(r'^[IVX]+$')
        ta, tb = [t for t in ta if not roman.match(t)], [t for t in tb if not roman.match(t)]
    if not ta or not tb:
        return False
    if {t for t in ta if _NUMERAL.match(t)} != {t for t in tb if _NUMERAL.match(t)}:
        return False
    ka, kb = ''.join(ta), ''.join(tb)
    if ka == kb or (min(len(ka), len(kb)) >= 5 and (ka in kb or kb in ka)):
        return True
    return difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.85


def station_for_place(municipality, number, name, location='', address='', rows=None):
    """The station row a source row belongs to, matched on its place.

    A station is one place under one number: when DIP gives a number to a
    different place than in another year, that is another row, so a station's
    history never mixes two places (the views add up every row of a place,
    whatever its number). A row from a source naming no place (presidential
    2000-2009, Sabor 2000-2011 exports with a bare number) joins the number's
    only row, and goes to an unnamed row when the number has meant more than
    one place, since nothing says which. Blank descriptive fields of a matched
    row are filled in, never overwritten.
    """
    if rows is None:
        rows = list(PollingStation.objects.filter(municipality=municipality, number=number).order_by('id'))
    blank = lambda r: not place_key(r.name, r.location, r.address)
    if place_key(name, location, address):
        obj = next((r for r in rows if same_place(r, name, location, address)), None)
        if obj is None and len(rows) == 1 and blank(rows[0]):
            obj = rows[0]      # a bare-number row, named now
    elif len(rows) == 1:
        obj = rows[0]
    else:
        obj = next((r for r in rows if blank(r)), None)
    if obj is None:
        # A place already stored under another number keeps that row's
        # spelling, so the views can group a place's rows on an exact key. A
        # row naming only its station takes the building of the station of
        # that name, when the name points to just one.
        built = [r for r in PollingStation.objects.filter(municipality=municipality)
                 if r.location or r.address]
        if location or address:
            twin = next((r for r in built
                         if place_key('', r.location, r.address) == place_key('', location, address)), None)
            twin = twin or next((r for r in built if same_place(r, name, location, address)), None)
            if twin:
                location, address = twin.location, twin.address
        elif name:
            seen = ({(r.location, r.address) for r in built if place_key(r.name) == place_key(name)}
                    or {(r.location, r.address) for r in built if similar_names(name, r.name)})
            if len(seen) == 1:
                location, address = seen.pop()
        return PollingStation.objects.create(
            municipality=municipality, number=number, name=name, location=location, address=address)
    fill = {f: v for f, v in (('name', name), ('location', location), ('address', address))
            if v and not getattr(obj, f)}
    if fill:
        for f, v in fill.items():
            setattr(obj, f, v)
        obj.save(update_fields=list(fill))
    return obj


class BaseImporter:
    """Shared logic for all election data importers."""

    def __init__(self, stdout=None):
        self.stdout = stdout or sys.stdout
        # Caches to avoid repeated DB lookups
        self._county_cache = {}
        self._municipality_cache = {}
        self._polling_station_cache = {}
        self._person_cache = {}
        # Bulk insert buffers.
        # Turnout uses a dict so that the same (election_round, polling_station)
        # encountered in multiple source files (e.g. Sabor "posebna"/"inozemstvo"
        # stations that appear in every district file) is summed instead of
        # dropped by the unique constraint.
        self._turnout_buffer = {}
        self._list_result_buffer = []
        self._candidate_result_buffer = []
        # Remap mode (`rekey_stations`): the import runs without writing a
        # result, recording for every result row which place it was reported
        # at, as (round id, municipality id, number, name, location, address).
        self.remap = None
        self._remap_fakes = {}

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
        # Match on a prefix-/hyphen-normalized key so the same place isn't split
        # into separate rows when source files name it "DUGO SELO" in one year
        # and "GRAD DUGO SELO" in another. See normalize_municipalities command.
        norm = normalize_municipality_name(name)
        key = (county.id, norm)
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
            # Reuse an existing row for this place under any name variant.
            existing = next(
                (m for m in Municipality.objects.filter(county=county)
                 if normalize_municipality_name(m.name) == norm),
                None,
            )
            if existing is None:
                existing = Municipality.objects.create(
                    county=county, name=name, type=normalized_type,
                )
            self._municipality_cache[key] = existing
        return self._municipality_cache[key]

    def get_or_create_polling_station(self, municipality, number, name, location='', address=''):
        number = str(number).zfill(3)
        if self.remap is not None:
            return self._remap_station(municipality, number, name, location, address)
        key = (municipality.id, number, name, location, address)
        if key not in self._polling_station_cache:
            self._polling_station_cache[key] = station_for_place(
                municipality, number, name, location, address)
        return self._polling_station_cache[key]

    def _remap_station(self, municipality, number, name, location, address):
        """An unsaved stand-in carrying the source row's place; its id is
        negative and stable per place, for code that keys on it."""
        key = (municipality.id, number, name, location, address)
        if key not in self._remap_fakes:
            fake = PollingStation(municipality=municipality, number=number,
                                  name=name, location=location, address=address)
            fake.id = -1 - len(self._remap_fakes)
            self._remap_fakes[key] = fake
        return self._remap_fakes[key]

    def _remap_record(self, round_id, station):
        self.remap.add((round_id, station.municipality_id, station.number,
                        station.name, station.location, station.address))

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
        if self.remap is not None:
            return Person(first_name=full_name)          # remap mode: nothing written
        # A birth-year suffix ("rođ. 1962.") is DIP telling namesakes apart:
        # it becomes the person's label, and the name stays searchable.
        bare, label = split_birth_year(full_name.strip())
        normalized = normalize_person_name(bare)
        key = (normalized, label) if label else normalized
        if key not in self._person_cache:
            first_name, last_name = parse_person_name(bare)
            # Unlabelled names match only the unlabelled row: a labelled one is
            # a namesake that `split_persons` carved off, and must not catch
            # new candidacies.
            person = Person.objects.filter(
                normalized_name=normalized, disambiguation=label).first()
            if person is None:
                person = Person.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    normalized_name=normalized,
                    disambiguation=label,
                )
            self._person_cache[key] = person
        return self._person_cache[key]

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
        if self.remap is not None:
            return Candidacy(electoral_list=electoral_list, position_on_list=position)
        # On a re-import the candidacy may already hang off a namesake that
        # `split_persons` moved it to; keep it there rather than create a twin.
        existing = Candidacy.objects.filter(
            electoral_list=electoral_list, position_on_list=position,
            person__normalized_name=person.normalized_name).first()
        if existing:
            return existing
        obj, _ = Candidacy.objects.get_or_create(
            person=person,
            electoral_list=electoral_list,
            position_on_list=position,
        )
        return obj

    # --- Result helpers (buffered bulk insert) ---

    def create_turnout(self, election_round, polling_station, registered, cast, valid, invalid):
        if self.remap is not None:
            return self._remap_record(election_round.id, polling_station)
        key = (election_round.id, polling_station.id)
        existing = self._turnout_buffer.get(key)
        if existing is None:
            self._turnout_buffer[key] = TurnoutData(
                election_round=election_round,
                polling_station=polling_station,
                registered_voters=registered,
                ballots_cast=cast,
                valid_ballots=valid,
                invalid_ballots=invalid,
            )
        else:
            existing.registered_voters += registered
            existing.ballots_cast += cast
            existing.valid_ballots += valid
            existing.invalid_ballots += invalid

    def create_list_result(self, electoral_list, polling_station, votes):
        if self.remap is not None:
            return self._remap_record(electoral_list.election_round_id, polling_station)
        self._list_result_buffer.append(ListResult(
            electoral_list=electoral_list,
            polling_station=polling_station,
            votes=votes,
        ))
        if len(self._list_result_buffer) >= BATCH_SIZE:
            self._flush_list_results()

    def create_candidate_result(self, candidacy, polling_station, votes):
        if self.remap is not None:
            return       # its list result is recorded for the same station
        self._candidate_result_buffer.append(CandidateResult(
            candidacy=candidacy,
            polling_station=polling_station,
            votes=votes,
        ))
        if len(self._candidate_result_buffer) >= BATCH_SIZE:
            self._flush_candidate_results()

    def _flush_turnout(self):
        if self.remap is not None:
            return
        if self._turnout_buffer:
            TurnoutData.objects.bulk_create(
                list(self._turnout_buffer.values()),
                update_conflicts=True,
                unique_fields=['election_round', 'polling_station'],
                update_fields=['registered_voters', 'ballots_cast', 'valid_ballots', 'invalid_ballots'],
            )

    def _flush_list_results(self):
        if self.remap is not None:
            return
        if self._list_result_buffer:
            ListResult.objects.bulk_create(self._list_result_buffer, ignore_conflicts=True)
            self._list_result_buffer = []

    def _flush_candidate_results(self):
        if self.remap is not None:
            return
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
