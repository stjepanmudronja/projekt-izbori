"""Populate polling dates for every election and round.

The frontend badge shows a full date when one is stored and silently falls
back to the bare year when it isn't, so a missing date is invisible rather
than broken — which is why most years only ever showed "2016".

Dates are recorded per round, because rounds sit weeks apart and a runoff can
land in the next calendar year (2019 presidential: 22 Dec 2019, runoff
5 Jan 2020). `Election.date` holds the first round, for callers that only
have the election.
"""
from datetime import date
from django.core.management.base import BaseCommand
from elections.models import Election, ElectionRound


# (election_type slug, year) -> {round_number: date}
ELECTION_DATES = {
    ('presidential', 1992): {1: date(1992, 8, 2)},
    ('presidential', 1997): {1: date(1997, 6, 15)},
    ('presidential', 2000): {1: date(2000, 1, 24), 2: date(2000, 2, 7)},
    ('presidential', 2005): {1: date(2005, 1, 2), 2: date(2005, 1, 16)},
    ('presidential', 2009): {1: date(2009, 12, 27), 2: date(2010, 1, 10)},
    ('presidential', 2014): {1: date(2014, 12, 28), 2: date(2015, 1, 11)},
    ('presidential', 2019): {1: date(2019, 12, 22), 2: date(2020, 1, 5)},
    ('presidential', 2024): {1: date(2024, 12, 29), 2: date(2025, 1, 12)},

    ('sabor', 2011): {1: date(2011, 12, 4)},
    ('sabor', 2015): {1: date(2015, 11, 8)},
    ('sabor', 2016): {1: date(2016, 9, 11)},
    ('sabor', 2020): {1: date(2020, 7, 5)},
    ('sabor', 2024): {1: date(2024, 4, 17)},

    ('eu_parliament', 2013): {1: date(2013, 4, 14)},
    ('eu_parliament', 2014): {1: date(2014, 5, 25)},
    ('eu_parliament', 2019): {1: date(2019, 5, 26)},
    ('eu_parliament', 2024): {1: date(2024, 6, 9)},
}

# Every lokalni type shares one polling day; the runoff for executive offices
# (mayor, prefect) is two weeks later. Councils are decided in one round.
LOCAL_DATES = {2025: {1: date(2025, 5, 18), 2: date(2025, 6, 1)}}


class Command(BaseCommand):
    help = 'Set polling dates on elections and their rounds'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change without writing')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        elections_set = rounds_set = 0
        missing = []

        for election in Election.objects.select_related('election_type').order_by(
                'election_type__slug', 'year'):
            slug = election.election_type.slug
            by_round = ELECTION_DATES.get((slug, election.year))
            if by_round is None and slug.startswith('local'):
                by_round = LOCAL_DATES.get(election.year)
            if by_round is None:
                missing.append(f'{slug} {election.year}')
                continue

            first = by_round.get(1)
            if first and election.date != first:
                self.stdout.write(f'  {slug} {election.year}: election date -> {first}')
                if not dry_run:
                    election.date = first
                    election.save(update_fields=['date'])
                elections_set += 1

            for round_obj in ElectionRound.objects.filter(election=election).order_by('round_number'):
                want = by_round.get(round_obj.round_number)
                if want is None:
                    missing.append(f'{slug} {election.year} round {round_obj.round_number}')
                    continue
                if round_obj.date != want:
                    self.stdout.write(
                        f'  {slug} {election.year} round {round_obj.round_number} -> {want}')
                    if not dry_run:
                        round_obj.date = want
                        round_obj.save(update_fields=['date'])
                    rounds_set += 1

        if missing:
            self.stdout.write(self.style.WARNING(
                f'\nNo date on record for: {", ".join(missing)}'))
        action = 'Would set' if dry_run else 'Set'
        self.stdout.write(self.style.SUCCESS(
            f'{action} {elections_set} election date(s) and {rounds_set} round date(s)'))
