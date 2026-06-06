from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import Person
from elections.importers.name_utils import (
    clean_candidate_name, normalize_person_name, parse_person_name,
)


class Command(BaseCommand):
    help = (
        "Strip academic titles (mr.sc., prof.dr.sc., dipl.iur., ...) from "
        "existing Person rows whose stored name carries them. For each "
        "titled Person we recompute the cleaned name + normalized_name; "
        "if an un-titled Person with the same normalized_name already "
        "exists we merge the titled row into it (re-pointing candidacies "
        "and deleting the duplicate); otherwise we update the titled row "
        "in place. Idempotent — re-runs are no-ops once everything is clean."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing.',
        )

    def handle(self, *args, dry_run, **options):
        # A Person row is "titled" when running its stored name through the
        # cleanup pipeline produces a different normalized_name. That covers
        # both prefix titles ("mr.sc. ANDREJ PLENKOVIĆ") and trailing
        # comma-separated suffixes (", dipl.iur.").
        merged = updated = skipped = 0
        with transaction.atomic():
            for p in Person.objects.all().order_by('id'):
                full = f'{p.first_name} {p.last_name}'.strip()
                cleaned_full = clean_candidate_name(full)
                cleaned_norm = normalize_person_name(cleaned_full)
                if cleaned_norm == p.normalized_name:
                    continue  # nothing to strip

                target = Person.objects.filter(normalized_name=cleaned_norm).exclude(id=p.id).first()
                if target:
                    cand_count = p.candidacies.count()
                    self.stdout.write(
                        f'  [merge] {p.normalized_name!r:50s} → keep id={target.id} '
                        f'({target.first_name} {target.last_name!r}); moving {cand_count} candidacies'
                    )
                    if not dry_run:
                        p.candidacies.update(person=target)
                        p.delete()
                    merged += 1
                else:
                    new_first, new_last = parse_person_name(cleaned_full)
                    self.stdout.write(
                        f'  [strip] {p.normalized_name!r:50s} → '
                        f'first={new_first!r} last={new_last!r} norm={cleaned_norm!r}'
                    )
                    if not dry_run:
                        p.first_name = new_first
                        p.last_name = new_last
                        p.normalized_name = cleaned_norm
                        p.save(update_fields=['first_name', 'last_name', 'normalized_name'])
                    updated += 1

            if dry_run:
                # roll back even the no-op transaction for clarity
                transaction.set_rollback(True)

        action = 'Would' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{action} merge {merged} duplicate(s), strip-in-place '
            f'{updated} row(s), {skipped} skipped.'
        ))
