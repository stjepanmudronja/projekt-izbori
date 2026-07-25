"""Merge Person rows that are the same human recorded under different names.

`normalize_persons` only merges rows whose normalized names match exactly, so
it can't see the commonest real-world split: DIP records a middle name in some
years and not others ("IVAN SINČIĆ" in 2014/2015, "IVAN VILIBOR SINČIĆ" from
2016 on). Those variants can't be merged automatically — plenty of genuinely
different people also differ by one middle token, so every merge here is a
curated, evidenced decision. `--suggest` finds the candidates; a human decides.
"""
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from elections.models import Person, Candidacy


# (canonical name, variant name, evidence). The canonical is the fuller name —
# it's the better display label and matches the more recent records.
KNOWN_ALIASES = [
    ('IVAN VILIBOR SINČIĆ', 'IVAN SINČIĆ',
     'Živi zid, VII. IJ in 2015/2016/2020; middle name absent from the 2014 '
     'presidential, 2014 EU and 2015 sabor files, present from 2016 on'),
    ('PREDRAG FRED MATIĆ', 'PREDRAG MATIĆ',
     'SDP, V. IJ in every sabor 2015-2024; "Fred" recorded from 2019 on'),
    ('NATALIA TAFRA BAZINA', 'NATALIA BAZINA',
     'PAMETNO lineage, X. IJ in 2015/2016/2020; surname extended by 2020'),
]


class Command(BaseCommand):
    help = 'Merge curated same-person name variants (middle names, added surnames)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be merged without changing anything')
        parser.add_argument('--suggest', action='store_true',
                            help='List unmerged middle-name candidate pairs for review, then exit')

    def handle(self, *args, **options):
        if options['suggest']:
            self._suggest()
            return

        dry_run = options['dry_run']
        merged = 0
        for canonical_name, variant_name, evidence in KNOWN_ALIASES:
            canonical = self._find(canonical_name)
            variant = self._find(variant_name)
            if canonical is None or variant is None:
                # Already merged, or neither year is imported yet.
                self.stdout.write(f"  skip {variant_name} -> {canonical_name}: not both present")
                continue
            if canonical.pk == variant.pk:
                continue

            count = variant.candidacies.count()
            self.stdout.write(
                f"  {variant_name} (id={variant.pk}, {count} candidacies) "
                f"-> {canonical_name} (id={canonical.pk})\n     {evidence}"
            )
            if not dry_run:
                with transaction.atomic():
                    variant.candidacies.update(person=canonical)
                    variant.delete()
            merged += 1

        action = 'Would merge' if dry_run else 'Merged'
        self.stdout.write(self.style.SUCCESS(f'{action} {merged} person alias(es)'))

    @staticmethod
    def _find(full_name):
        first, _, last = full_name.partition(' ')
        return Person.objects.filter(first_name=first, last_name=last).first()

    def _suggest(self):
        """Find persons differing only by inserted middle token(s).

        A pair appearing in the same election type and year is almost certainly
        two different people — nobody stands twice in one election — so that is
        flagged as the strongest disqualifier.
        """
        known = {v for _, v, _ in KNOWN_ALIASES} | {c for c, _, _ in KNOWN_ALIASES}
        by_ends = defaultdict(list)
        for person in Person.objects.all():
            tokens = (person.normalized_name or '').split()
            if len(tokens) >= 2:
                by_ends[(tokens[0], tokens[-1])].append((person, tokens))

        found = 0
        for group in by_ends.values():
            shorts = [p for p, t in group if len(t) == 2]
            longs = [p for p, t in group if len(t) > 2]
            for short in shorts:
                for long in longs:
                    if self._name(short) in known and self._name(long) in known:
                        continue
                    found += 1
                    a, b = self._elections(short), self._elections(long)
                    overlap = sorted(a & b)
                    self.stdout.write(
                        f"\n  {self._name(short)} {sorted(a)}"
                        f"\n  {self._name(long)} {sorted(b)}"
                        f"\n     same election as both: {overlap or 'none'}"
                        f"{'  <- likely DIFFERENT people' if overlap else ''}"
                    )
        self.stdout.write(f"\n{found} candidate pair(s) needing review")

    @staticmethod
    def _name(person):
        return f'{person.first_name} {person.last_name}'.strip()

    @staticmethod
    def _elections(person):
        return {
            (c.electoral_list.election_round.election.election_type.slug,
             c.electoral_list.election_round.election.year)
            for c in Candidacy.objects.filter(person=person).select_related(
                'electoral_list__election_round__election__election_type')
        }
