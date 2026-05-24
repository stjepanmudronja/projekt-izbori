from datetime import date

from django.core.management.base import BaseCommand

from elections.importers.base import BaseImporter
from elections.importers.name_utils import clean_candidate_name


# Source: DIP / Izborno povjerenstvo RH, Klasa 013-01/97-01/04 (24.6.1997).
# 1997 results are only available as a printed/scanned summary PDF — there's
# no per-station export from DIP — so we store just the national totals.
SUMMARY = {
    'year': 1997,
    'date': date(1997, 6, 15),
    'name': 'Predsjednički izbori 1997',
    'registered': 4061479,
    'cast': 2218448,
    'valid': 2178792,
    'invalid': 39656,
    'candidates': [
        # PDF lists candidates in alphabetical-ish order; positions don't
        # matter — rank is computed from vote counts at query time.
        ('Vladimir Gotovac', 382630),
        ('Dr. Zdravko Tomac', 458172),
        ('Dr. Franjo Tuđman', 1337990),
    ],
}

# Synthetic geography for summary-only years. Code 99 keeps it out of the
# real-county dropdowns (the Flask app filters codes < 90).
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
    help = 'Import 1997 presidential election summary (national totals only)'

    def handle(self, *args, **options):
        importer = _Importer(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS(
            f"Imported {SUMMARY['name']}: {len(SUMMARY['candidates'])} candidates, "
            f"valid={SUMMARY['valid']:,}, invalid={SUMMARY['invalid']:,}."
        ))
