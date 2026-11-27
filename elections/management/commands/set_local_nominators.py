"""Who nominated each mayor, načelnik and župan candidate, 2009-2025.

    python manage.py set_local_nominators [--year 2025] [--dry-run]

The results we import print only the candidate's name, so an executive race's
ElectoralList (one per candidate) is named for the candidate and says nothing
of party. This fills `ElectoralList.parties` for those lists from:
- 2013-2025: DIP's results archive, one file per race with every candidate's
  nominating parties, fetched by `tools/fetch_local_nominators.py` into
  Rezultati_lokalni_izbori/<year>/predlagatelji/ (2013 and 2017 CSV — the
  full names in columns 20-31 —, 2021 and 2025 JSON `strankePuniNaziv`);
- 2009: the DIP report's text dump (2009/text/), which prints the parties
  under each candidate; `local_2009_parse` already reads them.
A `Party` row is one printed party name ("HRVATSKA DEMOKRATSKA ZAJEDNICA -
HDZ"); a candidate of a group of voters gets "KANDIDAT GRUPE BIRAČA". Every
round's list of that candidate in that race is linked, so a runoff list has
them too.

A candidate is found by year, county and name (as the importers clean it),
the town breaking a tie; what is not found is reported, never guessed. Safe
to re-run; run it again after `import_local --wipe` of a year, which deletes
the lists and their links.
"""
import csv
import difflib
import io
import json
import re
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from elections.importers.local_2009_parse import parse_text
from elections.importers.name_utils import clean_candidate_name, normalize_person_name, split_birth_year, strip_diacritics
from elections.models import County, ElectoralList, Municipality, Party

ROOT = Path(settings.BASE_DIR) / 'files' / 'Rezultati_lokalni_izbori'
EXEC_SLUGS = ('local_mayor', 'local_city_mayor', 'local_county_prefect')
GROUP = 'KANDIDAT GRUPE BIRAČA'
YEARS = (2009, 2013, 2017, 2021, 2025)


def name_key(raw):
    """The importers' cleaning, then letters only: 'dr.sc. ZVONIMIR SABATI',
    'OŽIĆ - BEBEK' and 'Ožić-Bebek' meet."""
    name = split_birth_year(clean_candidate_name(re.sub(r'\s+-\s+', '-', raw or '')))[0]
    return re.sub(r'[^A-Z]', '', normalize_person_name(name))


def place_key(name):
    return re.sub(r'[^A-Z]', '', strip_diacritics((name or '').upper()))


def _party(name):
    name = ' '.join((name or '').split()).strip(' ,')
    if re.fullmatch(r'KANDIDAT(I)? GRUPE BIRAČA', name, re.I):
        return GROUP
    return name


def read_archive(year):
    """[(county code, town, candidate, [party names])] from the archive files."""
    out = []
    folder = ROOT / str(year) / 'predlagatelji'
    for path in sorted(folder.glob('r_*')):
        if path.suffix == '.json':
            d = json.loads(path.read_text(encoding='utf-8-sig'))
            for c in d.get('lista', []):
                parties = [_party(p['naziv']) for p in c.get('strankePuniNaziv') or []] or [_party(c.get('stranke'))]
                out.append((d['zupSifra'], d.get('gropNaziv') or d.get('zupNaziv'), c['naziv'], parties, d['izboriOznaka'] == '15'))
        else:
            for row in csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig')), delimiter=';'):
                if len(row) < 40:
                    continue
                # 0 race type, 3 county, 9 town, 19 rbr, then the full party names, the
                # candidate (the field before " - kandidat"), the deputies and the short
                # form ("HDZ, HSS, DC"). 2013 has one party column fewer than 2017.
                at = next(i for i, x in enumerate(row) if i > 20 and x.strip().startswith('- kandidat'))
                parties = [_party(p) for p in row[20:at - 1] if p.strip()]
                short = next((x for x in row[at:] if x and x == x.upper() and (',' in x or 'GRUPE' in x)), '')
                out.append((row[3], row[9], row[at - 1], parties or [_party(short)], row[0] == '15'))
    return out


def read_2009():
    out = []
    for path in sorted((ROOT / '2009' / 'text').glob('*.txt')):
        county_code = path.stem.split('_')[2]
        for contest in parse_text(path.read_text(encoding='utf-8'))[1]:
            if contest.get('slug') not in EXEC_SLUGS or contest.get('round', 1) != 1:
                continue
            for e in contest['entries']:
                if 'name' in e:
                    out.append((county_code, contest.get('unit'), e['name'], [_party(p) for p in e['parties']] or [GROUP],
                                contest['slug'] == 'local_county_prefect' or county_code == '21'))
    return out


class Command(BaseCommand):
    help = "Fill ElectoralList.parties for executive races from DIP's nominating parties"

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, choices=YEARS)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        county_code = {c.id: c.code for c in County.objects.all()}
        munis = {m.id: m for m in Municipality.objects.all()}
        for year in ([opts['year']] if opts['year'] else YEARS):
            # Our lists: (county code, county-level race?, candidate) -> [(town key, list id)],
            # every round. County level: the župan, and Grad Zagreb's gradonačelnik, whom the
            # archive files with the župani.
            index = defaultdict(list)
            lists = (ElectoralList.objects
                     .filter(election_round__election__year=year,
                             election_round__election__election_type__slug__in=EXEC_SLUGS)
                     .select_related('district', 'election_round__election__election_type')
                     .prefetch_related('candidacies__person'))
            for el in lists:
                slug = el.election_round.election.election_type.slug
                num = el.district.number if el.district else None
                if slug == 'local_county_prefect':
                    code, town = county_code.get(num), None
                else:
                    m = munis.get(num)
                    code, town = (county_code.get(m.county_id), m.name) if m else (None, None)
                top = slug == 'local_county_prefect' or code == '21'
                keys = {name_key(el.name)} | {name_key(f'{c.person.first_name} {c.person.last_name}') for c in el.candidacies.all()}
                for k in keys:
                    index[(code, top, k)].append((place_key(town), el.id))

            rows = read_2009() if year == 2009 else read_archive(year)
            if not rows:
                self.stdout.write(f'{year}: no files')
                continue
            links, missing, ambiguous = {}, [], []
            for code, town, name, parties, top in rows:
                hits = index.get((code, top, name_key(name)), [])
                ids = {i for _, i in hits}
                if len({t for t, _ in hits}) > 1:
                    # One name in two races of a county: the town decides.
                    # The 2009 report names the town in the genitive ("Grada Ogulina").
                    want = place_key(town)
                    ids = {i for t, i in hits if t and (t == want or want.startswith(t))} or ids
                    if len({t for t, i in hits if i in ids}) > 1:
                        ambiguous.append((code, town, name))
                        continue
                if not ids:
                    missing.append((code, town, name))
                    continue
                for i in ids:
                    links[i] = parties
            # A runoff list left over: its round-1 list in the same race under a
            # near-identical name (2009 Pakrac prints "HUŠKA" in round 1, "HRUŠKA" in
            # the runoff).
            by_race = defaultdict(list)
            for el in lists:
                by_race[el.district_id].append(el)
            for el in lists:
                if el.id in links or el.election_round.round_number == 1:
                    continue
                twins = [o for o in by_race[el.district_id] if o.election_round.round_number == 1 and o.id in links
                         and difflib.SequenceMatcher(None, name_key(o.name), name_key(el.name)).ratio() >= 0.9]
                if len(twins) == 1:
                    links[el.id] = links[twins[0].id]
            self.stdout.write(f'{year}: {len(rows)} candidates in the files, {len(links)} lists linked, '
                              f'{len(missing)} not found, {len(ambiguous)} ambiguous')
            for m in (missing + ambiguous)[:15]:
                self.stdout.write(f'   {m}')
            if opts['dry_run']:
                continue
            with transaction.atomic():
                party_ids = {}
                for name in {p for ps in links.values() for p in ps}:
                    abbr = name.rsplit(' - ', 1)[1] if ' - ' in name else ''
                    party, _ = Party.objects.get_or_create(name=name, defaults={'short_name': abbr[:100]})
                    party_ids[name] = party.id
                through = ElectoralList.parties.through
                through.objects.filter(electorallist_id__in=list(links)).delete()
                through.objects.bulk_create([through(electorallist_id=i, party_id=party_ids[p])
                                             for i, ps in links.items() for p in dict.fromkeys(ps)])
