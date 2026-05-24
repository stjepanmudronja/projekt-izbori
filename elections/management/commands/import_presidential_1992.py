from datetime import date

from django.core.management.base import BaseCommand

from elections.importers.base import BaseImporter
from elections.importers.name_utils import clean_candidate_name


# Source: scanned summary from DIP / Izborno povjerenstvo RH ("Izvješće o
# službenim rezultatima za izbor predsjednika — sva biračka mjesta u
# tuzemstvu i inozemstvu"). 1992 is summary-only.
SUMMARY = {
    'year': 1992,
    'date': date(1992, 8, 2),
    'name': 'Predsjednički izbori 1992',
    'registered': 3575032,
    'cast': 2677764,
    'valid': 2627061,    # cast - invalid (also matches sum of candidate votes)
    'invalid': 50703,
    'candidates': [
        ('Dražen Budiša', 585535),
        ('Dr. Ivan Cesar', 43134),
        ('Dr. Savka Dabčević Kučar', 161242),
        ('Silvije Degen', 108979),
        ('Dobroslav Paraga', 144695),
        ('Dr. Franjo Tuđman', 1519100),
        ('Dr. Marko Veselica', 45593),
        ('Dr. Antun Vujić', 18783),
    ],
}

# Same synthetic geography as 1997 (code 99 is filtered out of the
# scope-picker dropdown by /api/counties).
SYNTH_COUNTY_CODE = '99'
SYNTH_COUNTY_NAME = 'REPUBLIKA HRVATSKA (sažetak)'
SYNTH_MUNI_NAME = 'REPUBLIKA HRVATSKA'
SYNTH_PS_NUMBER = '001'


class _Importer(BaseImporter):
    def run(self):
        election_type = self.get_or_create_election_type('presidential', 'Predsjednički izbori')
        election = self.get_or_create_election(
            election_type, SUMMARY['year'], SUMMARY['name'], date=SUMMARY['date']
        )
        round_obj = self.get_or_create_round(election, 1)

        county = self.get_or_create_county(SYNTH_COUNTY_CODE, SYNTH_COUNTY_NAME)
        muni = self.get_or_create_municipality(county, SYNTH_MUNI_NAME, 'sažetak')
        station = self.get_or_create_polling_station(
            muni, SYNTH_PS_NUMBER, SYNTH_COUNTY_NAME, '', ''
        )

        self.create_turnout(
            round_obj, station,
            SUMMARY['registered'], SUMMARY['cast'],
            SUMMARY['valid'], SUMMARY['invalid'],
        )

        for position, (raw_name, votes) in enumerate(SUMMARY['candidates'], 1):
            name = clean_candidate_name(raw_name).upper()
            el_list = self.get_or_create_electoral_list(round_obj, name)
            person = self.get_or_create_person(name)
            candidacy = self.get_or_create_candidacy(person, el_list, 1)
            self.create_list_result(el_list, station, votes)
            self.create_candidate_result(candidacy, station, votes)
            self.log(f"  {name}: {votes:,} votes")

        self.flush_all()


class Command(BaseCommand):
    help = 'Import 1992 presidential election summary (national totals only)'

    def handle(self, *args, **options):
        importer = _Importer(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS(
            f"Imported {SUMMARY['name']}: {len(SUMMARY['candidates'])} candidates, "
            f"valid={SUMMARY['valid']:,}, invalid={SUMMARY['invalid']:,}."
        ))
