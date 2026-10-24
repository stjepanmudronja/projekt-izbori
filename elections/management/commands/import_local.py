from django.core.management.base import BaseCommand
from django.db.models import Count

from elections.importers.local import LocalImporter, YEAR_ROUNDS
from elections.importers.local_2001 import Local2001Importer
from elections.importers.local_2005 import Local2005Importer
from elections.importers.local_2009 import Local2009Importer
from elections.models import Election, Person


class Command(BaseCommand):
    help = 'Import local election results from Excel files'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=2025, choices=sorted([*YEAR_ROUNDS, 2009, 2005, 2001]))
        parser.add_argument('--wipe', action='store_true',
                            help="Delete that year's local elections first, then import from scratch")

    def handle(self, *args, **options):
        year = options['year']
        touched = set()
        if options['wipe']:
            elections = Election.objects.filter(election_type__slug__startswith='local', year=year)
            # Remember who stood, so rows left with nothing can go afterwards.
            touched = set(Person.objects.filter(
                candidacies__electoral_list__election_round__election__in=elections,
            ).values_list('pk', flat=True))
            count, _ = elections.delete()
            self.stdout.write(f'Wiped local {year}: {count} rows')

        if year in (2001, 2005, 2009):
            # PDF report only, no Excel: see local_2009.py / local_2005.py / local_2001.py.
            pdf_importer = {2001: Local2001Importer, 2005: Local2005Importer, 2009: Local2009Importer}
            pdf_importer[year](stdout=self.stdout).run()
        else:
            LocalImporter(year=year, stdout=self.stdout).run()

        if touched:
            empty = (Person.objects.filter(pk__in=touched)
                     .annotate(c=Count('candidacies'), m=Count('parliament_memberships'))
                     .filter(c=0, m=0))
            n = empty.count()
            empty.delete()
            self.stdout.write(f'Removed {n} person row(s) left without candidacies')
        self.stdout.write(self.style.SUCCESS(f'Local elections {year} import complete.'))
