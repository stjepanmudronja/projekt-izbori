"""Merge Person rows that are the same human recorded under different names.

`normalize_persons` only merges rows whose normalized names match exactly, so
it can't see the commonest real-world split: DIP records a middle name in some
years and not others ("IVAN SINČIĆ" in 2014/2015, "IVAN VILIBOR SINČIĆ" from
2016 on). Those variants can't be merged automatically — plenty of genuinely
different people also differ by one middle token, so every merge here is a
curated, evidenced decision. `--suggest` finds the candidates; a human decides.

One class *is* safe by rule and so runs automatically: the same name written
with and without a hyphen ("GORAN BEUS RICHEMBERGH" / "GORAN BEUS-RICHEMBERGH").
normalize_person_name() keeps hyphens, so the two spellings are different keys,
and Croatian compound names differ by a hyphen alone — never two people.
"""
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from elections.importers.name_utils import normalize_person_name, parse_person_name
from elections.models import Person, Candidacy, ParliamentMember


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
    ('SEAD BRACO HASANOVIĆ', 'SEAD HASANOVIĆ',
     'same minority sub-district 125 in 2007, 2011 and 2016, never twice in one '
     'election; the nickname "Braco" is recorded from 2011 on'),
]


# Names where the un-hyphenated spelling is the real one, so it wins even when
# the hyphenated row carries more candidacies (the usual tie-break can't tell).
# Keyed by the de-hyphenated normalized name. Also used to rename a survivor
# that was already merged the other way, so this stays correct after a
# re-import recreates the hyphenated spelling.
PREFER_UNHYPHENATED = {
    'ILIRJANA CROATA MEDUR':
        '"Croata" is a middle name, not half a compound surname — the hyphen is '
        'clean_candidate_name() closing an "ILIRJANA- CROATA" split in the source file',
}


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
        merged = self._merge_hyphen_variants(dry_run)
        merged += self._apply_spelling_preferences(dry_run)
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
                self._absorb(canonical, variant)
            merged += 1

        action = 'Would merge' if dry_run else 'Merged'
        self.stdout.write(self.style.SUCCESS(f'{action} {merged} person alias(es)'))

    def _apply_spelling_preferences(self, dry_run):
        """Drop an artifact hyphen from a PREFER_UNHYPHENATED name.

        The merge pass above only chooses between rows that both exist. Once
        one has already won with the hyphenated spelling, nothing else would
        ever correct it — so rename it here, or absorb it if the un-hyphenated
        row has since reappeared from a re-import.
        """
        fixed = 0
        for loose, evidence in PREFER_UNHYPHENATED.items():
            for person in Person.objects.filter(normalized_name__contains='-'):
                if (person.normalized_name or '').replace('-', ' ') != loose:
                    continue
                display = f'{person.first_name} {person.last_name}'.replace('-', ' ')
                target = Person.objects.filter(normalized_name=loose).first()
                self.stdout.write(
                    f"  {person.normalized_name} (id={person.pk}) -> {display}"
                    f"\n     {evidence}"
                )
                if not dry_run:
                    if target:
                        self._absorb(target, person)
                    else:
                        person.first_name, person.last_name = parse_person_name(display)
                        person.normalized_name = normalize_person_name(display)
                        person.save(update_fields=[
                            'first_name', 'last_name', 'normalized_name'])
                fixed += 1
        return fixed

    @staticmethod
    def _absorb(canonical, variant):
        """Move everything hanging off `variant` onto `canonical`, then drop it.

        ParliamentMember is unique per (election, person), so a roster row for
        an election the canonical already sits in would collide — that is the
        same membership recorded twice and is simply dropped.
        """
        with transaction.atomic():
            variant.candidacies.update(person=canonical)
            taken = set(
                ParliamentMember.objects
                .filter(person=canonical).values_list('election_id', flat=True)
            )
            memberships = ParliamentMember.objects.filter(person=variant)
            memberships.filter(election_id__in=taken).delete()
            memberships.update(person=canonical)
            variant.delete()

    def _merge_hyphen_variants(self, dry_run):
        """Merge rows whose normalized names differ only by hyphens.

        Safe without curation, unlike the middle-name splits above: a hyphen
        never distinguishes two Croatian politicians. The row with more
        candidacies survives, so the merge repoints as little as possible and
        keeps the spelling the most source files actually use.
        """
        by_loose = defaultdict(list)
        for person in Person.objects.all():
            by_loose[(person.normalized_name or '').replace('-', ' ')].append(person)

        merged = 0
        for loose, group in by_loose.items():
            if len(group) < 2:
                continue
            # Most candidacies first, so the merge repoints as little as
            # possible and keeps the spelling most source files use. On a tie
            # prefer the un-hyphenated form: a hyphen between two name tokens
            # is usually clean_candidate_name() closing a "BEUS- RICHEMBERGH"
            # split, not a character the person's name actually has.
            if loose in PREFER_UNHYPHENATED:
                # Curated: the un-hyphenated spelling is the person's real
                # name, so it survives however few candidacies it carries.
                group.sort(key=lambda q: (
                    '-' in (q.normalized_name or ''), -q.candidacies.count(), q.pk))
            else:
                group.sort(key=lambda q: (
                    -q.candidacies.count(), '-' in (q.normalized_name or ''), q.pk))
            canonical, variants = group[0], group[1:]
            for variant in variants:
                self.stdout.write(
                    f"  {variant.normalized_name} (id={variant.pk}, "
                    f"{variant.candidacies.count()} candidacies) -> "
                    f"{canonical.normalized_name} (id={canonical.pk})\n"
                    f"     hyphen spelling variant of the same name"
                )
                if not dry_run:
                    self._absorb(canonical, variant)
                merged += 1
        return merged

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
