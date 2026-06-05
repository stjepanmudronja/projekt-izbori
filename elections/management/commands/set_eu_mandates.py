from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import (
    ElectionType, Election, ElectionRound, ElectoralList, Candidacy,
    Person, ElectedMandate,
)

# Croatian MEPs actually seated, by EP-election year. Curated by hand because
# it can't be derived from vote totals — some elected candidates ceded their
# seat to the next on the preferential list (dual office, Commissioner role,
# etc.). Keys are Person.normalized_name (diacritics stripped, uppercase).
#
# Notes per term:
#   2019: Croatia got 11 seats; a 12th MEP joined Feb 2020 post-Brexit
#         (Sokol). Šuica vacated her seat Dec 2019 to become European
#         Commission VP; Ressler took her place. The list below records
#         everyone who held a seat at any point in that saziv.
#   2024: Current saziv. See `MEPS_BY_YEAR[2024]`.
MEPS_BY_YEAR = {
    2024: [
        ('STEPHEN NIKOLA BARTULICA',  'Europski konzervativci i reformisti (ECR)'),
        ('BILJANA BORZAN',            'Progresivni savez socijalista i demokrata (S&D)'),
        ('GORDAN BOSANAC',            'Zeleni/Europski slobodni savez (Verts/ALE)'),
        ('NIKOLINA BRNJAC',           'Europska pučka stranka (EPP)'),
        ('SUNCANA GLAVAK',            'Europska pučka stranka (EPP)'),
        ('ROMANA JERKOVIC KRALJIC',   'Progresivni savez socijalista i demokrata (S&D)'),
        ('TONINO PICULA',             'Progresivni savez socijalista i demokrata (S&D)'),
        ('KARLO RESSLER',             'Europska pučka stranka (EPP)'),
        ('TOMISLAV SOKOL',            'Europska pučka stranka (EPP)'),
        ('DAVOR IVO STIER',           'Europska pučka stranka (EPP)'),
        ('MARKO VESLIGAJ',            'Progresivni savez socijalista i demokrata (S&D)'),
        ('ZELJANA ZOVKO',             'Europska pučka stranka (EPP)'),
    ],
    2019: [
        ('RUZA TOMASIC',              'Europski konzervativci i reformisti (ECR)'),
        ('KARLO RESSLER',             'Europska pučka stranka (EPP)'),
        ('DUBRAVKA SUICA',            'Europska pučka stranka (EPP)'),
        ('TOMISLAV SOKOL',            'Europska pučka stranka (EPP)'),
        ('ZELJANA ZOVKO',             'Europska pučka stranka (EPP)'),
        ('VALTER FLEGO',              'Obnovimo Europu (Renew Europe)'),
        ('MISLAV KOLAKUSIC',          'Nezavisni zastupnici (NI)'),
        ('BILJANA BORZAN',            'Progresivni savez socijalista i demokrata (S&D)'),
        ('TONINO PICULA',             'Progresivni savez socijalista i demokrata (S&D)'),
        ('PREDRAG FRED MATIC',        'Progresivni savez socijalista i demokrata (S&D)'),
        ('ROMANA JERKOVIC KRALJIC',   'Progresivni savez socijalista i demokrata (S&D)'),
        ('IVAN VILIBOR SINCIC',       'Nezavisni zastupnici (NI)'),
    ],
}


class Command(BaseCommand):
    help = 'Flag seated Croatian MEPs as ElectedMandate rows for a given EP-election year.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year', type=int, default=2024,
            help='EP-election year to seed (default: 2024). Must have a roster in MEPS_BY_YEAR.',
        )

    def handle(self, *args, year, **options):
        meps = MEPS_BY_YEAR.get(year)
        if not meps:
            self.stderr.write(self.style.ERROR(
                f'No MEP roster defined for {year}. Add one to MEPS_BY_YEAR.'
            ))
            return

        etype = ElectionType.objects.filter(slug='eu_parliament').first()
        election = Election.objects.filter(election_type=etype, year=year).first() if etype else None
        if not election:
            self.stderr.write(self.style.ERROR(f'No EU parliament election for {year}'))
            return

        round_ids = list(
            ElectionRound.objects.filter(election=election).values_list('id', flat=True)
        )

        created = updated = missing = 0
        kept_candidacy_ids = []
        with transaction.atomic():
            for norm_name, group in meps:
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

            # Keep this command authoritative for THIS year's term: drop any
            # stale mandate rows on this year's candidacies that aren't in the
            # current roster. (Each year is scoped via round_ids, so other
            # years' mandates are untouched.)
            stale = (
                ElectedMandate.objects
                .filter(candidacy__electoral_list__election_round_id__in=round_ids)
                .exclude(candidacy_id__in=kept_candidacy_ids)
            )
            stale_n = stale.count()
            stale.delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nEU {year} mandates — created {created}, updated {updated}, '
            f'missing {missing}, stale removed {stale_n}.'
        ))
