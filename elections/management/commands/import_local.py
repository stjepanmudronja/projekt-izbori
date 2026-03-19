from django.core.management.base import BaseCommand
from elections.importers.local import LocalImporter


class Command(BaseCommand):
    help = 'Import local election results from Excel files'

    def handle(self, *args, **options):
        importer = LocalImporter(stdout=self.stdout)
        importer.run()
        self.stdout.write(self.style.SUCCESS('Local elections import complete.'))
