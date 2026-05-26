from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import (
    ElectionType, Election, ElectionRound, ElectoralList, Candidacy,
    Person, ElectedMandate,
)

# Croatian MEPs actually seated from the 2024 European Parliament election.
# This is curated by hand because it can't be derived from vote totals — some
# elected candidates ceded their seat to the next on the preferential list
# (dual office). Keys are Person.normalized_name (diacritics stripped, upper);
# note Jerković's compound DB surname "JERKOVIĆ KRALJIĆ".
MEPS_2024 = [
    ('STEPHEN NIKOLA BARTULICA', 'Europski konzervativci i reformisti (ECR)'),
    ('BILJANA BORZAN',           'Progresivni savez socijalista i demokrata (S&D)'),
    ('GORDAN BOSANAC',           'Zeleni/Europski slobodni savez (Verts/ALE)'),
    ('NIKOLINA BRNJAC',          'Europska pučka stranka (EPP)'),
    ('SUNCANA GLAVAK',           'Europska pučka stranka (EPP)'),
    ('ROMANA JERKOVIC KRALJIC',  'Progresivni savez socijalista i demokrata (S&D)'),
    ('TONINO PICULA',            'Progresivni savez socijalista i demokrata (S&D)'),
    ('KARLO RESSLER',            'Europska pučka stranka (EPP)'),
    ('TOMISLAV SOKOL',           'Europska pučka stranka (EPP)'),
    ('DAVOR IVO STIER',          'Europska pučka stranka (EPP)'),
    ('MARKO VESLIGAJ',           'Progresivni savez socijalista i demokrata (S&D)'),
    ('ZELJANA ZOVKO',            'Europska pučka stranka (EPP)'),
]
EU_YEAR = 2024


class Command(BaseCommand):
    help = 'Flag the sitting Croatian MEPs (2024 EP term) as ElectedMandate rows.'

    def handle(self, *args, **options):
        etype = ElectionType.objects.filter(slug='eu_parliament').first()
        election = Election.objects.filter(election_type=etype, year=EU_YEAR).first() if etype else None
        if not election:
            self.stderr.write(self.style.ERROR(f'No EU parliament election for {EU_YEAR}'))
            return

        round_ids = list(
            ElectionRound.objects.filter(election=election).values_list('id', flat=True)
        )

        created = updated = missing = 0
        kept_candidacy_ids = []
        with transaction.atomic():
            for norm_name, group in MEPS_2024:
                person = Person.objects.filter(normalized_name=norm_name).first()
                candidacy = None
                if person:
                    candidacy = (
                        Candidacy.objects
                        .filter(person=person, electoral_list__election_round_id__in=round_ids)
                        .first()
                    )
                if not candidacy:
                    self.stderr.write(self.style.WARNING(f'  MISSING candidacy for {norm_name}'))
                    missing += 1
                    continue

                obj, was_created = ElectedMandate.objects.update_or_create(
                    candidacy=candidacy, defaults={'group': group}
                )
                kept_candidacy_ids.append(candidacy.id)
                created += was_created
                updated += (not was_created)
                self.stdout.write(f'  {"+" if was_created else "~"} {person.first_name} {person.last_name} — {group}')

            # Keep this command authoritative for the EU-2024 term: drop any stale
            # mandate rows on EU-2024 candidacies not in the current list.
            stale = (
                ElectedMandate.objects
                .filter(candidacy__electoral_list__election_round_id__in=round_ids)
                .exclude(candidacy_id__in=kept_candidacy_ids)
            )
            stale_n = stale.count()
            stale.delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nEU {EU_YEAR} mandates — created {created}, updated {updated}, '
            f'missing {missing}, stale removed {stale_n}.'
        ))
