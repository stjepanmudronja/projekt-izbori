from django.core.management.base import BaseCommand
from elections.importers.sabor import SaborImporter


class Command(BaseCommand):
    help = 'Import Sabor (parliamentary) election results from CSV files'

    def handle(self, *args, **options):
        importer = SaborImporter(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS('Sabor import complete.'))
