from django.core.management.base import BaseCommand

from elections.importers.zupanijski_dom import ZupanijskiDomImporter


class Command(BaseCommand):
    help = ('Import a Županijski dom (upper house) election. '
            'The chamber held two: 1993 and 1997 — see '
            'elections/importers/zupanijski_dom.py.')

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=1997,
                            help='Election year: 1993 or 1997.')
        parser.add_argument('--district', type=int, default=None,
                            help='Only import one county, by its 2-char county code as an int (1-21)')

    def handle(self, *args, year, **options):
        if year not in ZupanijskiDomImporter.YEARS:
            self.stderr.write(self.style.ERROR(
                f'No Županijski dom data for {year}; have '
                f'{list(ZupanijskiDomImporter.YEARS)}.'))
            return
        importer = ZupanijskiDomImporter(year=year, stdout=self.stdout)
        importer.run(only_district=options.get('district'))
        self.stdout.write(self.style.SUCCESS(f'Županijski dom {year} import complete.'))
