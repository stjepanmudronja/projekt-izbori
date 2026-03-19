from django.core.management.base import BaseCommand
from elections.importers.presidential import PresidentialImporter


class Command(BaseCommand):
    help = 'Import presidential election results from CSV files'

    def handle(self, *args, **options):
        importer = PresidentialImporter(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS('Presidential import complete.'))
