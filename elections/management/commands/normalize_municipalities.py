from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from elections.models import (
    Municipality, PollingStation, TurnoutData, ListResult, CandidateResult,
)
from elections.importers.name_utils import normalize_municipality_name


class Command(BaseCommand):
    help = (
        'Merge duplicate municipalities (e.g. "DUGO SELO" vs "GRAD DUGO SELO") '
        'created by differing naming conventions across election-year imports. '
        'Repoints polling stations and their results onto one canonical row so '
        'per-municipality / per-county aggregation covers every year.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be merged without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        groups = defaultdict(list)
        for m in Municipality.objects.all().order_by('id'):
            groups[(m.county_id, normalize_municipality_name(m.name))].append(m)

        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        self.stdout.write(f"Found {len(duplicates)} groups of duplicate municipalities\n")

        merged_munis = moved_stations = merged_stations = moved_results = 0
        skipped_groups = 0

        for key, munis in sorted(duplicates.items(), key=lambda kv: kv[0]):
            # Safety guard: never merge a group that mixes two *different* real
            # types (a genuine grad-vs-općina pair sharing a base name).
            real_types = {
                (m.type or '').lower() for m in munis
                if (m.type or '').lower() not in ('', 'sažetak')
            }
            if len(real_types) > 1:
                self.stdout.write(self.style.WARNING(
                    f"  SKIP {key}: mixes types {real_types}: "
                    f"{[(m.id, m.name) for m in munis]}\n"
                ))
                skipped_groups += 1
                continue

            canonical = self._pick_canonical(munis)
            dupes = [m for m in munis if m.id != canonical.id]

            self.stdout.write(
                f"  [c{canonical.county_id}] {key[1]}: keep '{canonical.name}' "
                f"(id={canonical.id}, type={canonical.type!r}) <- "
                f"{[(m.id, m.name) for m in dupes]}\n"
            )

            if dry_run:
                merged_munis += len(dupes)
                continue

            with transaction.atomic():
                for dupe in dupes:
                    s_moved, s_merged, r_moved = self._merge_muni(dupe, canonical)
                    moved_stations += s_moved
                    merged_stations += s_merged
                    moved_results += r_moved
                    dupe.delete()  # CASCADE drops any leftover conflicting rows
                    merged_munis += 1

        action = "Would merge" if dry_run else "Merged"
        self.stdout.write(self.style.SUCCESS(
            f"\n{action} {merged_munis} duplicate municipalities across "
            f"{len(duplicates) - skipped_groups} groups "
            f"({skipped_groups} skipped).\n"
        ))
        if not dry_run:
            self.stdout.write(
                f"Polling stations repointed: {moved_stations}, "
                f"merged by number: {merged_stations}, "
                f"result rows moved: {moved_results}\n"
            )

    def _pick_canonical(self, munis):
        """Keep the row with a real type set (clean, prefix-free name); lowest id wins ties."""
        typed = [m for m in munis if (m.type or '').lower() not in ('', 'sažetak')]
        return min(typed or munis, key=lambda m: m.id)

    def _merge_muni(self, dupe, canonical):
        moved = merged = results_moved = 0
        existing = {s.number: s for s in canonical.polling_stations.all()}
        for st in list(dupe.polling_stations.all()):
            target = existing.get(st.number)
            if target is None:
                st.municipality = canonical
                st.save(update_fields=['municipality'])
                existing[st.number] = st
                moved += 1
            else:
                results_moved += self._move_station_results(st, target)
                st.delete()  # leftover conflicting result rows go with it (CASCADE)
                merged += 1
        return moved, merged, results_moved

    @staticmethod
    def _move_station_results(src, dst):
        """Bulk-repoint result rows from src station to dst, skipping any that
        would violate a unique constraint (same round/list/candidacy already on
        dst — i.e. a true duplicate, which is then dropped with src)."""
        moved = 0

        dst_rounds = TurnoutData.objects.filter(polling_station=dst).values_list(
            'election_round_id', flat=True)
        moved += (TurnoutData.objects.filter(polling_station=src)
                  .exclude(election_round_id__in=list(dst_rounds))
                  .update(polling_station=dst))

        dst_lists = ListResult.objects.filter(polling_station=dst).values_list(
            'electoral_list_id', flat=True)
        moved += (ListResult.objects.filter(polling_station=src)
                  .exclude(electoral_list_id__in=list(dst_lists))
                  .update(polling_station=dst))

        dst_cands = CandidateResult.objects.filter(polling_station=dst).values_list(
            'candidacy_id', flat=True)
        moved += (CandidateResult.objects.filter(polling_station=src)
                  .exclude(candidacy_id__in=list(dst_cands))
                  .update(polling_station=dst))

        return moved
