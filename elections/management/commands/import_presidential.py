from django.core.management.base import BaseCommand
from elections.importers.presidential import PresidentialImporter


class Command(BaseCommand):
    help = 'Import presidential election results from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year', type=int, nargs='*',
            help='Years to import (default: all configured). Example: --year 2019 2024',
        )

    def handle(self, *args, **options):
        years = options.get('year') or None
        importer = PresidentialImporter(stdout=self.stdout, years=years)
        importer.run()
        self.stdout.write(self.style.SUCCESS('Presidential import complete.'))
