from django.core.management.base import BaseCommand

from elections.importers.sabor_1990 import CHAMBERS, Sabor1990Importer


class Command(BaseCommand):
    help = ('Import the 1990 Sabor: the Društveno-političko vijeće (dpv) and the '
            'Vijeće općina (vo). The Vijeće udruženog rada is not transcribed yet '
            '— see elections/importers/sabor_1990.py.')

    def add_arguments(self, parser):
        parser.add_argument('--chamber', choices=[*CHAMBERS, 'all'], default='all',
                            help='Which chamber to import (default: all)')
        parser.add_argument('--district', type=int, default=None,
                            help='Only import one unit')

    def handle(self, *args, **options):
        chambers = list(CHAMBERS) if options['chamber'] == 'all' else [options['chamber']]
        for chamber in chambers:
            Sabor1990Importer(chamber, stdout=self.stdout).run(
                only_district=options.get('district'))
        self.stdout.write(self.style.SUCCESS(f"Sabor 1990 ({', '.join(chambers)}) import complete."))
