from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from elections.models import Person, Candidacy, CandidateResult
from elections.importers.name_utils import normalize_person_name


class Command(BaseCommand):
    help = 'Deduplicate persons by normalized name, merging candidacies'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be merged without making changes')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Group persons by normalized name
        groups = defaultdict(list)
        for person in Person.objects.all().order_by('id'):
            groups[person.normalized_name].append(person)

        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        self.stdout.write(f"Found {len(duplicates)} groups of duplicate persons\n")

        merged_count = 0
        for normalized, persons in sorted(duplicates.items()):
            canonical = persons[0]  # keep the first (oldest) entry
            dupes = persons[1:]

            candidacy_count = sum(p.candidacies.count() for p in dupes)
            self.stdout.write(
                f"  {normalized}: merging {len(dupes)} duplicate(s) into "
                f"'{canonical.first_name} {canonical.last_name}' (id={canonical.id}), "
                f"{candidacy_count} candidacies to re-point\n"
            )

            if not dry_run:
                with transaction.atomic():
                    for dupe in dupes:
                        # Re-point candidacies
                        dupe.candidacies.update(person=canonical)
                        dupe.delete()

            merged_count += len(dupes)

        action = "Would merge" if dry_run else "Merged"
        self.stdout.write(self.style.SUCCESS(
            f"{action} {merged_count} duplicate person records "
            f"across {len(duplicates)} groups\n"
        ))
