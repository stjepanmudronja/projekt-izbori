"""Attach every polling-station result to the place it was reported at.

Stations used to be keyed on municipality + number, and a station's name and
address were whichever import first touched it. DIP renumbers stations between
elections — in Grad Zagreb 458 of 2017's 612 numbers name a different place
than the stored station of that number — so one station row held several
places' results in different years.

This command re-reads every source that names its stations, in the importers'
remap mode: the import runs inside a transaction that is rolled back, writing
nothing, and records the place behind every result row as (round, municipality,
number, place). Each round's results are then moved onto the row of that
number and place (`station_for_place`), created where missing. Persons, lists
and candidacies are not touched.

Last, results from sources that name no place (presidential 2000-2009, Sabor
2000-2011) are left on their number only when it has only ever meant one place;
where it meant several, they go to an unnamed row, since nothing says which.

Re-run after an import; it is idempotent. `--only` remaps a single source and
skips that last step, which needs every named source's mapping.
"""
import re
from collections import defaultdict
from itertools import combinations

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from elections.importers.base import same_place, similar_names, station_for_place
from elections.importers.name_utils import place_key, strip_diacritics
from elections.models import PollingStation, Municipality


def sources():
    from elections.importers.presidential import PresidentialImporter
    from elections.importers.eu_parliament import YEAR_CONFIG, EUParliamentImporter
    from elections.importers.sabor import SaborImporter
    from elections.importers.sabor_legacy import SaborLegacyImporter
    from elections.importers.local import LocalImporter
    out = [(f'predsjednicki {y}', lambda y=y: PresidentialImporter(years=[y]))
           for y in sorted(PresidentialImporter.YEARS)]
    out += [(f'eu {y}', lambda y=y: EUParliamentImporter(year=y)) for y in sorted(YEAR_CONFIG)]
    out += [(f'sabor {y}', lambda y=y: SaborLegacyImporter(year=y)) for y in SaborLegacyImporter.YEARS]
    out += [(f'sabor {y}', lambda y=y: SaborImporter(year=y)) for y in (2015, 2016, 2020, 2024)]
    out += [(f'lokalni {y}', lambda y=y: LocalImporter(year=y)) for y in (2013, 2017, 2021, 2025)]
    return out


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = 'Move polling-station results onto the place they were reported at'

    def add_arguments(self, parser):
        parser.add_argument('--only', help='one source, e.g. "lokalni 2017"')
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, only=None, dry_run=False, **opts):
        todo = [s for s in sources() if only is None or s[0] == only]
        if not todo:
            self.stderr.write(f'unknown source {only!r}; one of: {[s[0] for s in sources()]}')
            return
        mapping = set()
        for label, make in todo:
            importer = make()
            importer.stdout = open('/dev/null', 'w')
            importer.remap = set()
            try:
                with transaction.atomic():
                    importer.run()
                    raise _Rollback
            except _Rollback:
                pass
            self.stdout.write(f'{label}: {len(importer.remap)} result places read')
            mapping |= importer.remap

        # One place per (round, municipality, number), or the source is
        # contradicting itself and that number is left alone.
        places = defaultdict(dict)
        for rnd, muni, number, name, loc, addr in mapping:
            k = place_key(name, loc, addr)
            places[(rnd, muni, number)].setdefault(k, (name, loc, addr))
        conflicts = {g: p for g, p in places.items() if len([k for k in p if k]) > 1}
        for g, p in list(conflicts.items())[:20]:
            self.stdout.write(f'  conflict, left alone: round {g[0]} muni {g[1]} no. {g[2]}: {list(p.values())}')
        self.stdout.write(f'{len(conflicts)} conflicting numbers')

        with transaction.atomic():
            moved, created = self._apply(places, conflicts)
            self.stdout.write(f'moved {moved} result rows, created {created} stations')
            if only is None:
                moved, created = self._orphan(places)
                self.stdout.write(f'unnamed sources: moved {moved} result rows off numbers '
                                  f'that meant several places, created {created} unnamed stations')
                self.stdout.write(f'gave {self._fill_buildings()} name-only stations their building')
                self.stdout.write(f'spelled {self._zagreb_sabor()} Zagreb Sabor stations '
                                  f'as their Grad Zagreb place')
                joined = total = self._join_spellings()
                while joined:                  # a joined place can pair up anew
                    joined = self._join_spellings()
                    total += joined
                self.stdout.write(f'spelled {total} stations as the other spelling of their address')
                with connection.cursor() as c:
                    c.execute('''DELETE FROM elections_pollingstation p WHERE
                        NOT EXISTS (SELECT 1 FROM elections_turnoutdata WHERE polling_station_id = p.id)
                        AND NOT EXISTS (SELECT 1 FROM elections_listresult WHERE polling_station_id = p.id)
                        AND NOT EXISTS (SELECT 1 FROM elections_candidateresult WHERE polling_station_id = p.id)''')
                    self.stdout.write(f'deleted {c.rowcount} stations left without results')
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write('dry run: rolled back')

    def _fill_buildings(self):
        """2017 names only the station (its settlement or mjesni odbor). Such
        a row takes the building and address of the station of the same name
        in its municipality, when that name is at exactly one building."""
        by_muni = defaultdict(list)
        for s in PollingStation.objects.order_by('id'):
            by_muni[s.municipality_id].append(s)
        n = 0
        for rows in by_muni.values():
            built = [r for r in rows if r.location or r.address]
            for r in rows:
                if r.location or r.address or not r.name:
                    continue
                seen = ({(b.location, b.address) for b in built if place_key(b.name) == place_key(r.name)}
                        or {(b.location, b.address) for b in built if similar_names(r.name, b.name)})
                if len(seen) == 1:
                    r.location, r.address = seen.pop()
                    r.save(update_fields=['location', 'address'])
                    n += 1
        return n

    def _zagreb_sabor(self):
        """Sabor files Zagreb's stations under its electoral districts ("ZAGREB
        - VI. IZBORNA JEDINICA", "ZAGREB-JUGOISTOK"), not under GRAD ZAGREB.
        The app treats those as one town with GRAD ZAGREB and matches places
        by `place_key`, so a district's station takes the spelling of the Grad
        Zagreb place it is (`same_place`), where exactly one is."""
        city = [s for s in PollingStation.objects.filter(municipality__name='GRAD ZAGREB')
                if place_key(s.name, s.location, s.address)
                and not (s.location or '').startswith('sažetak')]
        keys = {place_key(s.name, s.location, s.address) for s in city}
        by_number = defaultdict(list)          # blocked on the address's house numbers
        for s in city:
            by_number[frozenset(re.findall(r'\d+', s.address or ''))].append(s)
        n = 0
        for s in (PollingStation.objects.filter(municipality__county__code='21')
                  .exclude(municipality__name='GRAD ZAGREB')):
            k = place_key(s.name, s.location, s.address)
            if not k or k in keys:
                continue
            twins = {place_key(r.name, r.location, r.address): r
                     for r in by_number[frozenset(re.findall(r'\d+', s.address or ''))]
                     if same_place(r, s.name, s.location, s.address)}
            if len(twins) == 1:
                twin = twins.popitem()[1]
                s.name, s.location, s.address = twin.name, twin.location, twin.address
                s.save(update_fields=['name', 'location', 'address'])
                n += 1
        return n

    # Words that say what kind of street it is, not which one.
    STREET_TYPES = {'ULICA', 'UL', 'CESTA', 'TRG', 'PUT', 'BB', 'KBR', 'BR', 'BROJ',
                    'NASELJE', 'ODVOJAK', 'PROLAZ', 'SETALISTE', 'OBALA'}

    def _street(self, address, town):
        """(house numbers, street words cut to 5 letters, street type) of an
        address, leaving out the town's own name ("SLAVONSKI BROD, ...")."""
        a = strip_diacritics((address or '').upper())
        numbers = set()
        for digits, slash, letter in re.findall(r'(\d+)\s*(?:/\s*([A-Z0-9]+)|([A-Z])\b)?', a):
            numbers |= {digits, slash or letter} - {''}
        town_words = set(re.findall(r'[A-Z]+', strip_diacritics(town.upper())))
        words = {w[:5] for w in re.findall(r'[A-Z]+', a)
                 if len(w) >= 3 and w not in town_words and w not in self.STREET_TYPES}
        kind = set(re.findall(r'\b(OBALA|TRG|CESTA|PUT|SETALISTE)\b', a))
        return frozenset(numbers), words, kind

    def _join_spellings(self):
        """One address spelled two ways ("KVATERNIKOVA 7" / "EUGENA KVATERNIKA
        7", "S. RADIĆA 19" / "STJEPANA RADIĆA 19", "52 A" / "52A") is one
        place. Two places of a municipality are the same when their house
        numbers agree, one's street words are among the other's, any street
        types agree and no election has both (a source spells a place one way).
        The spelling of fewer elections takes the other's building and
        address; one that fits several places is left alone."""
        with connection.cursor() as c:
            c.execute('SELECT polling_station_id, array_agg(DISTINCT election_round_id) '
                      'FROM elections_turnoutdata GROUP BY 1')
            rounds = dict(c.fetchall())
        by_muni = defaultdict(lambda: defaultdict(list))
        for s in PollingStation.objects.select_related('municipality'):
            if s.address and not (s.location or '').startswith('sažetak') \
                    and s.municipality.name != 'HRVATSKA':     # mobile stations of every town
                by_muni[s.municipality][place_key(s.name, s.location, s.address)].append(s)
        n = 0
        for muni, places in by_muni.items():
            town = f'{muni.name} {muni.name.replace(" - ", " ")}'
            info = {k: (self._street(rows[0].address, town),
                        set().union(*(rounds.get(r.id, []) for r in rows)))
                    for k, rows in places.items()}
            partners = defaultdict(set)
            for k1, k2 in combinations(places, 2):
                (n1, w1, t1), r1 = info[k1]
                (n2, w2, t2), r2 = info[k2]
                if (r1 & r2 or not n1 or n1 != n2 or not w1 or not w2
                        or not (w1 <= w2 or w2 <= w1) or (t1 and t2 and t1 != t2)):
                    continue
                small, big = sorted((k1, k2), key=lambda k: (len(info[k][1]), k))
                partners[small].add(big)
            for small, bigs in partners.items():
                if len(bigs) != 1:
                    continue
                big = next(iter(bigs))
                while len(partners.get(big, ())) == 1:         # a chain of spellings
                    big = next(iter(partners[big]))
                twin = places[big][0]
                for r in places[small]:
                    r.location, r.address = twin.location, twin.address
                    r.save(update_fields=['location', 'address'])
                    n += 1
        return n

    def _rows(self):
        rows = defaultdict(list)
        for s in PollingStation.objects.order_by('id'):
            rows[(s.municipality_id, s.number)].append(s)
        return rows

    def _apply(self, places, conflicts):
        rows = self._rows()
        munis = {}
        created = 0
        targets = {}
        moves = defaultdict(list)          # round -> [(from ids, to id)]
        for (rnd, muni, number), p in places.items():
            if (rnd, muni, number) in conflicts:
                continue
            named = [(k, v) for k, v in p.items() if k]
            if not named:
                continue
            group = rows[(muni, number)]
            if not group:
                continue                   # no results stored at that number
            tkey = (muni, number, named[0][0])
            if tkey not in targets:
                if muni not in munis:
                    munis[muni] = Municipality.objects.get(pk=muni)
                target = station_for_place(munis[muni], number, *named[0][1], rows=group)
                if target.id not in {s.id for s in group}:
                    group.append(target)
                    created += 1
                targets[tkey] = target
            target = targets[tkey]
            others = [s.id for s in group if s.id != target.id]
            if others:
                moves[rnd].append((others, target.id))
        return self._move(moves), created

    def _orphan(self, places):
        """Results with no named place, on a number that has meant several
        places, go to that number's unnamed row."""
        named = {(rnd, muni, number) for (rnd, muni, number), p in places.items() if any(p)}
        rows = self._rows()
        moves = defaultdict(list)
        created = 0
        for (muni, number), group in rows.items():
            placed = [s for s in group if place_key(s.name, s.location, s.address)]
            if len(placed) < 2:
                continue
            ids = [s.id for s in placed]
            with connection.cursor() as c:
                c.execute('''SELECT DISTINCT election_round_id FROM elections_turnoutdata
                             WHERE polling_station_id = ANY(%s)
                             UNION SELECT DISTINCT l.election_round_id FROM elections_listresult r
                             JOIN elections_electorallist l ON l.id = r.electoral_list_id
                             WHERE r.polling_station_id = ANY(%s)''', [ids, ids])
                rounds = [r for (r,) in c.fetchall() if (r, muni, number) not in named]
            if not rounds:
                continue
            blank = next((s for s in group if not place_key(s.name, s.location, s.address)), None)
            if blank is None:
                blank = PollingStation.objects.create(municipality_id=muni, number=number, name='')
                group.append(blank)
                created += 1
            for r in rounds:
                moves[r].append((ids, blank.id))
        return self._move(moves), created

    def _move(self, moves):
        n = 0
        with connection.cursor() as c:
            for rnd, pairs in moves.items():
                values = [(old, new) for olds, new in pairs for old in olds]
                if not values:
                    continue
                vals = ','.join(['(%s,%s)'] * len(values))
                flat = [x for pair in values for x in pair]
                c.execute(f'''UPDATE elections_turnoutdata t SET polling_station_id = m.new
                              FROM (VALUES {vals}) m(old, new)
                              WHERE t.polling_station_id = m.old AND t.election_round_id = %s''',
                          flat + [rnd])
                n += c.rowcount
                c.execute(f'''UPDATE elections_listresult r SET polling_station_id = m.new
                              FROM (VALUES {vals}) m(old, new), elections_electorallist l
                              WHERE r.polling_station_id = m.old AND r.electoral_list_id = l.id
                                AND l.election_round_id = %s''', flat + [rnd])
                n += c.rowcount
                c.execute(f'''UPDATE elections_candidateresult r SET polling_station_id = m.new
                              FROM (VALUES {vals}) m(old, new), elections_candidacy cy,
                                   elections_electorallist l
                              WHERE r.polling_station_id = m.old AND r.candidacy_id = cy.id
                                AND cy.electoral_list_id = l.id AND l.election_round_id = %s''',
                          flat + [rnd])
                n += c.rowcount
        return n
