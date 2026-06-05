from django.core.management.base import BaseCommand
from elections.importers.eu_parliament import EUParliamentImporter


class Command(BaseCommand):
    help = 'Import EU Parliament election results from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year', type=int, default=2024,
            help='Election year to import (matches the {year}/CSV/ subdirectory). Default: 2024.',
        )

    def handle(self, *args, year, **options):
        importer = EUParliamentImporter(year=year, stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS(f'EU Parliament {year} import complete.'))
