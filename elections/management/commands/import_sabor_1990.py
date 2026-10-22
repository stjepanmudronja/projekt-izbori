from django.core.management.base import BaseCommand

from elections.importers.sabor_1990_dpv import Sabor1990DpvImporter


class Command(BaseCommand):
    help = ('Import the 1990 Sabor. Only the Društveno-političko vijeće is '
            'transcribed so far — see elections/importers/sabor_1990_dpv.py.')

    def add_arguments(self, parser):
        parser.add_argument('--district', type=int, default=None,
                            help='Only import one unit (1-80)')

    def handle(self, *args, **options):
        Sabor1990DpvImporter(stdout=self.stdout).run(only_district=options.get('district'))
        self.stdout.write(self.style.SUCCESS('Sabor 1990 (Društveno-političko vijeće) import complete.'))
