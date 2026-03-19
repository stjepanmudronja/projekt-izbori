from django.core.management.base import BaseCommand
from elections.importers.eu_parliament import EUParliamentImporter


class Command(BaseCommand):
    help = 'Import EU Parliament election results from CSV files'

    def handle(self, *args, **options):
        importer = EUParliamentImporter(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS('EU Parliament import complete.'))
