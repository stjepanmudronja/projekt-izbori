from django.core.management.base import BaseCommand
from elections.importers.sabor import SaborImporter


class Command(BaseCommand):
    help = 'Import Sabor (parliamentary) election results from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--district', type=int, default=None,
            help='Only import a specific district (1-12)',
        )
        parser.add_argument(
            '--wipe-district', action='store_true',
            help='Delete existing data for the specified district before importing',
        )

    def handle(self, *args, **options):
        only_district = options.get('district')
        if options.get('wipe_district'):
            if only_district is None:
                self.stderr.write('--wipe-district requires --district')
                return
            self._wipe_district(only_district)
        importer = SaborImporter(stdout=self.stdout)
        importer.run(only_district=only_district)
        self.stdout.write(self.style.SUCCESS('Sabor import complete.'))

    def _wipe_district(self, district_num):
        from elections.models import (
            Election, ElectionRound, ElectoralDistrict, ElectoralList,
            Candidacy, ListResult, CandidateResult, TurnoutData,
        )
        try:
            election = Election.objects.get(
                election_type__slug='sabor', year=2024,
            )
        except Election.DoesNotExist:
            self.stdout.write('No existing Sabor 2024 election; nothing to wipe.')
            return
        round1 = ElectionRound.objects.get(election=election, round_number=1)

        # District 12 uses sub-districts 121-126; wipe all of them plus
        # the old monolithic district 12 (if it still exists).
        if district_num == 12:
            district_nums = [12, 121, 122, 123, 124, 125, 126]
        else:
            district_nums = [district_num]

        for dnum in district_nums:
            try:
                district = ElectoralDistrict.objects.get(election=election, number=dnum)
            except ElectoralDistrict.DoesNotExist:
                continue

            lists_qs = ElectoralList.objects.filter(election_round=round1, district=district)
            ps_ids = set(
                ListResult.objects.filter(electoral_list__in=lists_qs)
                .values_list('polling_station_id', flat=True)
                .distinct()
            )
            self.stdout.write(
                f'Wiping district {dnum}: '
                f'{lists_qs.count()} lists, {len(ps_ids)} polling stations'
            )
            CandidateResult.objects.filter(candidacy__electoral_list__in=lists_qs).delete()
            ListResult.objects.filter(electoral_list__in=lists_qs).delete()
            Candidacy.objects.filter(electoral_list__in=lists_qs).delete()
            lists_qs.delete()
            # Only delete turnout for non-minority districts. District 12
            # shares polling stations with districts 1-10 and its importer
            # doesn't write turnout, so wiping it would destroy correct data.
            if ps_ids and district_num != 12:
                TurnoutData.objects.filter(
                    election_round=round1, polling_station_id__in=ps_ids
                ).delete()
            # Also delete the old district 12 entry itself
            if dnum == 12:
                district.delete()

        self.stdout.write(f'District {district_num} wiped.')
