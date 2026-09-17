"""Import the 1997 election to the Županijski dom — the Sabor's upper house.

This is a **different chamber** from every other year in the database. The
Županijski dom existed from 1993 to 2001, sat alongside the Zastupnički dom
that `sabor.py` / `sabor_legacy.py` / `sabor_2003.py` / `sabor_2000.py` import,
and is gone: the 2001 constitutional amendments abolished it. So it gets its
own ElectionType rather than joining "Parlamentarni izbori", and its seats
never mix into a Zastupnički dom total.

How it differs, and what that means for the model:

  * **Counties are the electoral districts.** Each of the 21 counties returned
    exactly 3 members (63 in all), regardless of size — Lika-Senj's 47,839
    voters elected as many as Zagreb's 671,548. Districts are therefore created
    per county, numbered by the county's own code.
  * **There is no per-station data.** The DIP report publishes one set of
    figures per county and nothing below it, so each county gets a single
    pseudo polling station in a `<county> (sažetak)` municipality — the same
    device `import_presidential_1997` uses for its national summary, but one
    per county rather than one for the country, which keeps county-level
    aggregation honest.
  * **Seats are stated, not computed.** The report names the members each list
    returned, so no allocation is run: seats come from the source and the 63
    members are recorded as ParliamentMember rows against this election.
  * Every list ran a **holder** (nositelj) and every elected member a
    **zamjenik**. Holders are appended to a repeated list name the way
    `sabor_legacy` does, which matters because eight counties ran a list called
    only "Nezavisna županijska lista".

The data is a hand transcription of a scanned report; see
`zupanijski_dom_1997_data.py` for its provenance and the checks it satisfies.
"""
from .base import BaseImporter
from .name_utils import clean_candidate_name
from .zupanijski_dom_1997_data import COUNTIES

ELECTION_TYPE_SLUG = 'sabor_zupanijski'
ELECTION_TYPE_NAME = 'Županijski dom Sabora'
SEATS_PER_COUNTY = 3


class ZupanijskiDomImporter(BaseImporter):
    YEARS = (1997,)

    def __init__(self, year=1997, stdout=None):
        super().__init__(stdout=stdout)
        self.year = year

    def run(self, only_district=None):
        from datetime import date
        election_type = self.get_or_create_election_type(
            ELECTION_TYPE_SLUG, ELECTION_TYPE_NAME)
        election = self.get_or_create_election(
            election_type, self.year, f'{ELECTION_TYPE_NAME} {self.year}',
            date=date(1997, 4, 13))
        election_round = self.get_or_create_round(election, 1)

        members = seats = lists = 0
        for entry in COUNTIES:
            number = int(entry['code'])
            if only_district is not None and number != only_district:
                continue
            lists += self._import_county(election, election_round, entry)
            seats += sum(s['n'] for s in entry['seats'])
            members += self._record_members(election, entry)

        self.flush_all()
        self.log(f'{ELECTION_TYPE_NAME} {self.year}: {lists} lists across '
                 f'{len(COUNTIES)} counties, {seats} seats, {members} members recorded')

    # ---- votes ----------------------------------------------------------

    def _import_county(self, election, election_round, entry):
        county = self.get_or_create_county(entry['code'], entry['name'].upper())
        # One pseudo station per county: the report has no finer breakdown.
        muni = self.get_or_create_municipality(
            county, f"{entry['name'].upper()} (SAŽETAK)", 'sažetak')
        station = self.get_or_create_polling_station(
            muni, '001', entry['name'], 'sažetak županije', '')
        district = self.get_or_create_district(
            election, int(entry['code']), entry['name'])

        self.create_turnout(
            election_round, station, entry['registered'], entry['voted'],
            entry['valid_total'], entry['invalid'])

        names = self._list_names(entry['lists'])
        for item in entry['lists']:
            el = self.get_or_create_electoral_list(
                election_round, names[item['n']], district)
            self.create_list_result(el, station, item['votes'])
        return len(entry['lists'])

    @staticmethod
    def _list_names(items):
        """Column number -> stored list name.

        Coalition members are joined the way every other year stores them. A
        base name that repeats within the county is disambiguated by its
        holder, exactly as `sabor_legacy._list_names` does for the several
        "NEOVISNA LISTA" entries of 2007 and 2011 — here it is "Nezavisna
        županijska lista", which Šibenik-Knin alone ran twice.
        """
        from collections import Counter
        base = {i['n']: ', '.join(i['parties']) for i in items}
        counts = Counter(base.values())
        out = {}
        for item in items:
            name = base[item['n']]
            if counts[name] > 1 and item['holder']:
                name = f"{name} - {clean_candidate_name(item['holder'])}"
            out[item['n']] = name
        return out

    # ---- members --------------------------------------------------------

    def _record_members(self, election, entry):
        """Store the county's 3 members as ParliamentMember rows.

        `district` ties each to the county that elected them and `party` holds
        the full list name, matching how the 2003 Sabor roster is stored.
        """
        from elections.models import ParliamentMember, ElectoralDistrict
        district = ElectoralDistrict.objects.filter(
            election=election, number=int(entry['code'])).first()
        n = 0
        for seat in entry['seats']:
            for member in seat['elected']:
                name = clean_candidate_name(member['name']).upper()
                if not name:
                    continue
                person = self.get_or_create_person(name)
                deputy = clean_candidate_name(member['deputy']).upper()
                ParliamentMember.objects.update_or_create(
                    election=election, person=person,
                    defaults={'party': seat['list'], 'minority': False,
                              'district': district,
                              'note': f'zamjenik: {deputy}' if deputy else ''},
                )
                n += 1
        return n
