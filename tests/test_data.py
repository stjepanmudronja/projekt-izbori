"""Regression checks against the live `projekt_izbori` database.

Read-only: they query the database and the Flask app's own endpoints (through
Flask's test client, no server needed) and compare the result with figures
already verified against the published results — the numbers are the ones
CLAUDE.md records per importer. A failure after an import, a merge/split
command or a code change means something moved that should not have.

Run from the project root, with the virtualenv active:

    python -m unittest discover -s tests -t . -v

or a single group:  python -m unittest tests.test_data.SaborSeats -v
"""
import re
import unittest
from pathlib import Path

from app import app, db

ROOT = Path(__file__).resolve().parent.parent


def setUpModule():
    global client, ctx
    ctx = app.app_context()
    ctx.push()
    client = app.test_client()
    try:
        db.session.execute(db.text('select 1'))
    except Exception as exc:                  # no database, no point going on
        raise unittest.SkipTest(f'database projekt_izbori not reachable: {exc}')


def tearDownModule():
    ctx.pop()


def get(url):
    res = client.get(url)
    assert res.status_code == 200, f'{url} -> {res.status_code}'
    return res.get_json()


def scalar(sql, **kw):
    return db.session.execute(db.text(sql), kw).scalar()


class SaborSeats(unittest.TestCase):
    """Seat totals and the published distribution per Sabor (Zastupnički dom)."""

    def seats(self, year):
        d = get(f'/api/national/sabor-seats/{year}')
        return d, sorted((p['seats'] for p in d['parties']), reverse=True)

    def test_house_size_per_year(self):
        # 152 in 2003 (4 diaspora seats), 153 in 2007 (5), 151 otherwise.
        for year, size in {2003: 152, 2007: 153, 2011: 151, 2015: 151,
                           2016: 151, 2020: 151, 2024: 151}.items():
            with self.subTest(year=year):
                d, seats = self.seats(year)
                self.assertEqual(d['total_seats'], size)
                self.assertEqual(sum(seats), size)

    def test_2000_allocates_districts_i_to_x_only(self):
        # Districts XI and XII were never supplied: 140 of 151 seats.
        d, seats = self.seats(2000)
        self.assertEqual(d['total_seats'], 151)
        self.assertEqual(sum(seats), 140)

    def test_published_distributions(self):
        expected = {
            2011: [80, 47, 8, 6, 6, 2, 1, 1],
            2015: [59, 56, 19],
            2016: [61, 54, 13],
            2020: [66, 41, 16],
            2024: [61, 42, 14, 11, 10],
        }
        for year, top in expected.items():
            with self.subTest(year=year):
                self.assertEqual(self.seats(year)[1][:len(top)], top)
        self.assertEqual(self.seats(2003)[1][0], 66)        # HDZ 2003
        self.assertEqual(self.seats(2007)[1][:2], [66, 56])  # HDZ, SDP 2007

    def test_rosters_hold_one_member_per_seat(self):
        for year, size in {2003: 152, 2007: 153, 2011: 151}.items():
            with self.subTest(year=year):
                self.assertEqual(len(get(f'/api/national/sabor-seats/{year}')['members']), size)


class EarlierChambers(unittest.TestCase):
    """1990-1997: seats are stated in the reports, not allocated."""

    def check(self, url, total, top, key='total_seats'):
        d = get(url)
        seats = sorted((p['seats'] for p in d['parties']), reverse=True)
        self.assertEqual(d[key], total)
        self.assertEqual(sum(seats), total)
        self.assertEqual(seats[:len(top)], top)

    def test_sabor_1992(self):
        self.check('/api/national/sabor-1992', 138, [85, 14, 11, 6, 6, 5])

    def test_sabor_1995(self):
        self.check('/api/national/sabor-1995', 127, [75])

    def test_zupanijski_dom(self):
        self.check('/api/national/zupanijski-dom/1993', 63, [37, 18, 5, 3], key='elected_seats')
        self.check('/api/national/zupanijski-dom/1997', 63, [42], key='elected_seats')

    def test_1990_chambers(self):
        self.check('/api/national/sabor-1990/dpv/1990', 80, [55, 17, 3, 2, 1, 1])
        self.check('/api/national/sabor-1990/vo/1990', 115, [70, 33])
        self.check('/api/national/sabor-1990/vur/1990', 156, [83, 42])


class Totals(unittest.TestCase):
    """Electorate and vote totals that reconcile exactly with the reports."""

    def turnout(self, slug, year, rnd=1):
        return db.session.execute(db.text("""
            select sum(t.registered_voters), sum(t.ballots_cast)
            from elections_turnoutdata t
            join elections_electionround er on er.id = t.election_round_id
            join elections_election e on e.id = er.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug = :slug and e.year = :year and er.round_number = :rnd"""),
            dict(slug=slug, year=year, rnd=rnd)).one()

    def test_sabor_registered_voters(self):
        self.assertEqual(self.turnout('sabor', 2003)[0], 4087553)
        self.assertEqual(tuple(self.turnout('sabor', 1995)), (4033072, 2609429))

    def test_presidential_national_summaries(self):
        self.assertEqual(self.turnout('presidential', 1992)[0], 3575032)
        self.assertEqual(self.turnout('presidential', 1997)[0], 4061479)

    def test_zupanijski_dom_electorate(self):
        self.assertEqual(tuple(self.turnout('sabor_zupanijski', 1993)), (3580396, 2303782))
        self.assertEqual(self.turnout('sabor_zupanijski', 1997)[0], 3664693)

    def test_sabor_1992_national_list(self):
        # The 17 lists sum to cast - invalid = 2,631,535 (district 65 = the list).
        total = scalar("""
            select sum(lr.votes) from elections_listresult lr
            join elections_electorallist el on el.id = lr.electoral_list_id
            join elections_electoraldistrict ed on ed.id = el.district_id
            join elections_electionround er on er.id = el.election_round_id
            join elections_election e on e.id = er.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug = 'sabor' and e.year = 1992 and ed.number = 65""")
        self.assertEqual(total, 2631535)


class Presidents(unittest.TestCase):
    def test_every_election_has_one_winner(self):
        pres = get('/api/home')['presidential']
        years = [e['year'] for e in pres['elections']]
        self.assertEqual(sorted(years), [1992, 1997, 2000, 2005, 2009, 2014, 2019, 2024])
        e2024 = next(e for e in pres['elections'] if e['year'] == 2024)
        self.assertEqual(e2024['winner']['name'], 'ZORAN MILANOVIĆ')
        self.assertAlmostEqual(e2024['winner']['share'], 74.68, places=2)

    def test_home_cards_have_a_career_for_every_president(self):
        pres = get('/api/home')['presidential']
        for e in pres['elections']:
            with self.subTest(year=e['year']):
                self.assertTrue(pres['careers'].get(str(e['winner']['person_id'])))


class PartyStrength(unittest.TestCase):
    """Snaga stranaka against the published national shares."""

    @classmethod
    def setUpClass(cls):
        d = get('/api/analytics/party-strength?kind=sabor')
        cls.by = {p['short_name'] or p['name']: {pt['year']: pt['share'] for pt in p['points']}
                  for p in d['parties']}

    def test_published_shares(self):
        self.assertEqual(self.by['HDZ'][1992], 44.71)
        self.assertEqual(self.by['HDZ'][1995], 45.23)
        self.assertEqual(self.by['HDZ'][2003], 33.92)
        self.assertEqual(self.by['HDZ'][2007], 36.62)
        self.assertEqual(self.by['SDP'][2007], 31.33)
        self.assertEqual(self.by['SDP'][2011], 40.72)
        self.assertEqual(self.by['HSP'][1995], 5.01)

    def test_renamed_registration_is_another_party(self):
        # "SDP - Stranka demokratskih promjena" (1992, register no. 70) is not
        # today's SDP (no. 88): a name change makes a different party.
        self.assertNotIn(1992, self.by['SDP'])
        self.assertIn(1992, self.by['SOCIJALDEMOKRATSKA PARTIJA HRVATSKE--STRANKA DEMOKRATSKIH PROMJENA'])

    def test_every_kind_answers(self):
        for kind in ('sabor', 'eu', 'vijeca', 'skupstine', 'sve'):
            with self.subTest(kind=kind):
                self.assertTrue(get(f'/api/analytics/party-strength?kind={kind}')['parties'])


class PartyNames(unittest.TestCase):
    """Party linking: a name change is another party (the data's owner's
    rule), and an abbreviation alone never joins two different parties."""

    @classmethod
    def setUpClass(cls):
        from webapp.parties import _party_links, _party_link_tables
        from webapp.models import RegisteredParty
        _party_links()
        regs = {p.registry_number: p.id for p in RegisteredParty.query.all()}
        cls.printed = staticmethod(lambda reg: {name.upper() for (name, _y) in _party_link_tables()[1].get(regs[reg], {})})
        cls.lines = {}                            # line id -> years with a point, Sabor and councils together
        for kind in ('sabor', 'vijeca'):
            for p in get(f'/api/analytics/party-strength?kind={kind}')['parties']:
                cls.lines.setdefault(p['id'], set()).update(pt['year'] for pt in p['points'])

    def test_shared_abbreviation_is_not_one_party(self):
        self.assertFalse(any('SAVEZ ZA PROMJENE' in n for n in self.printed(231)))     # Stranka penzionera, SP
        self.assertFalse(any('PRAVAŠI' in n for n in self.printed(150)))               # Hrvatski proljećari, HP
        self.assertFalse(any('DEMOKRATSKA AKCIJA' in n for n in self.printed(54)))     # Dalmatinska akcija, DA
        self.assertFalse(any('1861' in n for n in self.printed(19)))                   # HSP-1861 is not HSP

    def test_hyphenated_abbreviation(self):
        # "HRVATSKA STRANKA PRAVA - 1861 - HSP-1861" (2000) is HSP-1861.
        self.assertIn('HRVATSKA STRANKA PRAVA - 1861 - HSP-1861', self.printed(97))

    def test_old_name_is_its_own_line(self):
        self.assertIn(1992, self.lines['45:Hrvatska narodna stranka'])
        self.assertFalse({y for y in self.lines['45'] if y < 2007}, 'HNS - Liberalni demokrati before 2007')
        self.assertIn(2016, self.lines['245:Most nezavisnih lista'])
        self.assertFalse({y for y in self.lines['245'] if y < 2021}, 'MOST before 2021')

    def test_party_page_says_which_name(self):
        ran = {h['year']: h['ran_as'] for h in get('/api/stranke/45')['history'] if h['led_lists']}
        self.assertEqual(ran[1992], 'Hrvatska narodna stranka')
        self.assertIsNone(ran[2009])


class MapSwing(unittest.TestCase):
    """Karta općina, "Promjena": one party's change between two elections."""

    def swing(self, **kw):
        q = '&'.join(f'{k}={v}' for k, v in kw.items())
        return get(f'/api/map/swing?{q}')

    def test_national_change(self):
        d = self.swing(kind='sabor', year=2024, base_kind='sabor', base_year=2020, party='HDZ')
        self.assertEqual((d['national']['base'], d['national']['value']), (36.8, 33.52))
        self.assertEqual(d['gained'] + d['lost'] + sum(1 for m in d['munis'].values() if m['change'] == 0),
                         len(d['munis']))

    def test_renamed_party_is_another_party(self):
        # A name change makes a different party: 2020's "Domovinski pokret
        # Miroslava Škore" is not 2024's DP, so DP has no 2020 to compare with.
        r = client.get('/api/map/swing?kind=sabor&year=2024&base_kind=sabor&base_year=2020&party=DP')
        self.assertEqual(r.status_code, 404)
        offered = [p['key'] for p in self.swing(kind='sabor', year=2024, base_kind='sabor', base_year=2020)['parties']]
        self.assertNotIn('DP', offered)

    def test_same_candidate_across_runoffs(self):
        d = self.swing(kind='predsjednicki', year=2024, round=2, base_kind='predsjednicki',
                       base_year=2019, base_round=2, party='ZORAN MILANOVIĆ')
        self.assertEqual((d['national']['base'], d['national']['value']), (53.75, 75.26))

    def test_bad_input(self):
        self.assertEqual(client.get('/api/map/swing?kind=sabor&year=2024&base_kind=sabor&base_year=2020&party=XX').status_code, 404)
        self.assertEqual(client.get('/api/map/swing?kind=sabor&year=2099&base_kind=sabor&base_year=2020').status_code, 404)
        self.assertEqual(client.get('/api/map/swing?kind=nema&year=2024&base_kind=sabor&base_year=2020').status_code, 400)


class CacheClearing(unittest.TestCase):
    """New data empties the caches by itself: no restart after an import."""

    def test_every_module_cache_is_registered(self):
        """A module-level dict a view keeps results in must be data_cache(...),
        or it would keep serving the data from before an import."""
        unregistered = []
        for path in sorted((ROOT / 'webapp').glob('*.py')):
            if path.name == 'core.py':            # the registry itself
                continue
            for n, line in enumerate(path.read_text().splitlines(), 1):
                if re.match(r'_\w*(CACHE|cache|_UNITS)\w* = ', line) and 'data_cache(' not in line:
                    unregistered.append(f'{path.name}:{n}: {line.strip()}')
        self.assertEqual(unregistered, [])

    def test_a_write_clears_everything_once(self):
        from webapp import core
        versions = iter([100, 100, 101, 101])
        hooks, ran = core._AFTER_CLEAR[:], []
        cache = core.data_cache({'x': 1})
        original = core.data_version
        core.data_version = lambda: next(versions)
        core._AFTER_CLEAR[:] = [lambda: ran.append(1)]   # not the real warm-up
        core._data_check['version'] = None
        try:
            self.assertFalse(core.check_data_changed(force=True))   # first look: the mark
            self.assertFalse(core.check_data_changed(force=True))   # unchanged
            self.assertEqual(cache, {'x': 1})
            self.assertTrue(core.check_data_changed(force=True))    # a write
            self.assertEqual((cache, ran), ({}, [1]))
            cache['x'] = 2
            self.assertFalse(core.check_data_changed(force=True))   # nothing new
            self.assertEqual(cache, {'x': 2})
        finally:
            core.data_version = original
            core._AFTER_CLEAR[:] = hooks
            core._DATA_CACHES.remove(cache.clear)
            core._data_check['version'] = None

    def test_static_cache_is_registered(self):
        from webapp import core
        from webapp.sabor import sabor_seats
        self.assertIn(sabor_seats.cache.clear, core._DATA_CACHES)

    def test_data_version_reads(self):
        from webapp.core import data_version
        with app.app_context():
            self.assertGreaterEqual(data_version(), 0)


class WomenInPolitics(unittest.TestCase):
    """Žene u politici: gender from first names, and the published shares."""

    @classmethod
    def setUpClass(cls):
        cls.data = get('/api/analytics/women')
        cls.by = {(e['kind'], e['year']): e for e in cls.data['elections']}

    def test_name_rules(self):
        from webapp.women import name_gender
        for name, g in [('IVAN', 'M'), ('MARIJA', 'F'), ('Ana-Marija', 'F'), ('LUKA', 'M'), ('NIKOLA', 'M'),
                        ('IVICA', 'M'), ('KATICA', 'F'), ('INES', 'F'), ('NIVES', 'F'), ('KARMEN', 'F'),
                        ('SAŠA', None), ('ANDREA', None), ('I', None), ('', None)]:
            with self.subTest(name=name):
                self.assertEqual(name_gender(name), g)

    def test_few_unknown(self):
        p = self.data['people']
        self.assertLess(p['unknown'] / p['total'], 0.01)

    def test_published_shares(self):
        """Sabor as elected 2003 (27 of 152, ~18 %) and 2020 (34 of 151 as elected —
        a count of 35 includes a later substitute; it matched here only while
        Peđa Grbin was read as a woman);
        Croatia's first woman president in 2014; EU 2014 six of eleven."""
        self.assertEqual(self.by[('sabor', 2003)]['elected']['f'], 27)
        self.assertEqual(self.by[('sabor', 2020)]['elected']['f'], 34)
        self.assertEqual(self.by[('predsjednicki', 2014)]['elected'], {'f': 1, 'm': 0, 'u': 0})
        self.assertEqual(self.by[('eu', 2014)]['elected']['f'], 6)
        self.assertIsNone(self.by[('sabor', 2011)]['candidates'])      # only district XII is published

    def test_parties_add_up(self):
        """Every seat of a list election belongs to one party row."""
        for year, seats in ((2015, 151), (2016, 151), (2020, 151), (2024, 151)):
            rows = self.data['parties'][f'sabor-{year}']
            total = sum(r['elected']['f'] + r['elected']['m'] + r['elected']['u'] for r in rows)
            with self.subTest(year=year):
                self.assertEqual(total, seats)
                self.assertEqual(sum(r['elected']['f'] for r in rows), self.by[('sabor', year)]['elected']['f'])


    def test_offices_and_counties_add_up(self):
        """Executives by office add up to the local row; counties to the country,
        less Zagreb's župan-less count (Grad Zagreb's gradonačelnik is its race)."""
        for year in (2009, 2013, 2017, 2021, 2025):
            offices = self.data['by_office'][str(year)]
            counties = self.data['by_county'][str(year)]
            local = self.by[('lokalni', year)]['elected']
            with self.subTest(year=year):
                self.assertEqual(sum(o['elected']['f'] for o in offices.values()), local['f'])
                self.assertEqual(len(counties), 21)
                self.assertEqual(sum(sum(c['elected'].values()) for c in counties.values()),
                                 sum(sum(o['elected'].values()) for o in offices.values()))
        self.assertEqual(self.data['by_office']['2025']['zupanija']['elected']['f'], 3)

    def test_list_positions_and_leaders(self):
        """Place on the list: buckets add up to the party rows (Sabor 2024, every
        seat but the minorities'); list leaders exist for 2001-2009 only."""
        rows = self.data['by_position']['sabor-2024']
        self.assertEqual([r['bucket'] for r in rows], ['1', '2-3', '4+'])
        won = sum(sum(r['elected'].values()) for r in rows)
        self.assertEqual(won, 151 - 8)
        self.assertLess(rows[0]['candidates']['f'] / sum(rows[0]['candidates'].values()),
                        rows[2]['candidates']['f'] / sum(rows[2]['candidates'].values()))
        self.assertEqual(sorted({l['year'] for l in self.data['leaders']}), [2001, 2005, 2009])
        for l in self.data['leaders']:
            with self.subTest(year=l['year'], body=l['body']):
                self.assertLessEqual(sum(l['first'].values()), sum(l['all'].values()))


class Incumbency(unittest.TestCase):
    """Ponovni izbor: what happened to each place's last winner."""

    @classmethod
    def setUpClass(cls):
        cls.data = get('/api/analytics/incumbency')

    def test_every_place_accounted_for(self):
        self.assertEqual(self.data['years'], [2009, 2013, 2017, 2021, 2025])
        for y in self.data['per_year']:
            for kind, c in y['by_kind'].items():
                with self.subTest(year=y['year'], kind=kind):
                    self.assertEqual(c['won'] + c['lost'] + c['did_not_run'], c['races'])
            self.assertEqual(y['by_kind']['sve']['races'], 576)          # 556 towns + 20 counties

    def test_lists_match_counts(self):
        terms = self.data['terms']['by_kind']['sve']
        self.assertEqual(sum(terms.values()), 576)
        self.assertEqual(len(self.data['long_serving']), terms['5'])
        for y in self.data['per_year']:
            self.assertEqual(len(self.data['defeated'][str(y['year'])]), y['by_kind']['sve']['lost'])

    def test_known_races(self):
        """Zagreb 2021: Bandić, the 2017 winner, had died - not a defeat; Korčula
        2025: the sitting gradonačelnica lost the runoff 49.9 : 50.1."""
        names = lambda y: {d['name']: d for d in self.data['defeated'][y]}
        self.assertNotIn('GRAD ZAGREB', names('2021'))
        k = names('2025')['KORČULA']
        self.assertEqual((k['incumbent']['share'], k['winner']['share'], k['round']), (49.9, 50.1, 2))


    def test_counties_add_up_to_the_country(self):
        d = self.data
        self.assertEqual(len(d['counties']), 21)
        for row in d['per_year']:
            per = d['by_county'][str(row['year'])]
            for kind, total in row['by_kind'].items():
                with self.subTest(year=row['year'], kind=kind):
                    for k in ('races', 'won', 'lost', 'did_not_run'):
                        self.assertEqual(sum(c.get(kind, {}).get(k, 0) for c in per.values()), total[k])

    def test_close_calls(self):
        d = self.data
        for y, rows in d['close'].items():
            margins = [r['margin'] for r in rows]
            self.assertEqual(margins, sorted(margins))
            self.assertTrue(all(0 <= m < d['close_margin'] for m in margins))
            self.assertTrue(all(r['votes_ahead'] > 0 and r['county'] for r in rows))
        # Varaždinska 2025: Stričak kept the county by 18 votes in the runoff.
        top = d['close']['2025'][0]
        self.assertEqual((top['name'], top['incumbent']['name'], top['votes_ahead'], top['round']),
                         ('VARAŽDINSKA ŽUPANIJA', 'ANĐELKO STRIČAK', 18, 2))

    def test_places_match_the_counts(self):
        """The map's outcome per općina/grad adds up to the counts per kind."""
        for row in self.data['per_year']:
            places = get(f"/api/analytics/incumbency/places/{row['year']}")['munis']
            c = {k: row['by_kind'][k] for k in ('opcina', 'grad')}
            with self.subTest(year=row['year']):
                self.assertEqual(len(places), c['opcina']['races'] + c['grad']['races'])
                outcomes = [p['o'] for p in places.values()]
                self.assertEqual(outcomes.count('won1') + outcomes.count('won2'), c['opcina']['won'] + c['grad']['won'])
                self.assertEqual(outcomes.count('won1'), c['opcina']['won_first_round'] + c['grad']['won_first_round'])
                self.assertEqual(outcomes.count('lost'), c['opcina']['lost'] + c['grad']['lost'])
                self.assertEqual(outcomes.count('open'), c['opcina']['did_not_run'] + c['grad']['did_not_run'])
        self.assertNotIn('munis', self.data)        # kept off the page's own payload


class People(unittest.TestCase):
    """Person rows: curated splits hold, no party codes left in names."""

    def test_no_two_unlabelled_rows_share_a_name(self):
        dup = scalar("""select count(*) from (select normalized_name from elections_person
                        group by normalized_name, disambiguation having count(*) > 1) x""")
        self.assertEqual(dup, 0)

    def test_no_party_code_fused_into_a_name(self):
        # 1993 OCR once stored "IVAN STANEK HDZ"; split_fused_party fixed it.
        n = scalar(r"""select count(*) from elections_person
                       where normalized_name ~ ' (HDZ|SDP|HSS|HSLS|HSP|HNS|IDS)$'""")
        self.assertEqual(n, 0)

    def test_curated_namesakes_stay_split(self):
        for name, label in [('SANDRA PERKOVIC', 'Ližnjan, 1997.'), ('FRANJO TUDMAN', 'Luka, 1997.')]:
            with self.subTest(name=name):
                self.assertEqual(scalar("""select count(*) from elections_person
                                           where normalized_name = :n and disambiguation = :l""",
                                        n=name, l=label), 1)

    def test_home_public_figures_resolve(self):
        figures = get('/api/home')['public_figures']
        from app import HOME_PUBLIC_FIGURES
        self.assertEqual(len(figures), len(HOME_PUBLIC_FIGURES))


class Pages(unittest.TestCase):
    """Every page and the endpoints behind them answer."""

    def test_spa_routes_serve_the_page(self):
        for path in ('/', '/politicar', '/prema-lokaciji', '/stranke', '/stranke/8-hdz', '/mjesto/439-klis',
                     '/predsjednicki-izbori', '/eu-parlamentarni-izbori', '/lokalni-izbori',
                     '/rezultati-koalicije-sabor', '/zupanijski-dom', '/izlaznost', '/karta', '/snaga-stranaka', '/zene-u-politici', '/ponovni-izbor'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

    def test_api_smoke(self):
        get('/api/counties')
        self.assertTrue(get('/api/person/3780')['results'])         # Franjo Tuđman
        self.assertTrue(get('/api/stranke/8')['history'])           # HDZ
        self.assertGreater(len(get('/api/stranke')), 400)
        self.assertTrue(get('/api/map/elections'))

    def test_sidebar_modules_have_panels_and_routes(self):
        html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
        core_js = (ROOT / 'static' / 'js' / 'core.js').read_text(encoding='utf-8')
        nav = html[html.index('<nav'):html.index('</nav>')]
        slugs = dict(re.findall(r"'([\w-]+)':\s*'([\w-]*)',", core_js[core_js.index('const MODULE_SLUGS'):]
                                .split('};', 1)[0]))
        from app import SPA_ROUTES
        for mod in re.findall(r'data-module="([\w-]+)"', nav):
            with self.subTest(module=mod):
                self.assertIn(f'id="module-{mod}"', html)
                if slugs.get(mod):
                    self.assertIn(slugs[mod], SPA_ROUTES)


class PartySwitchers(unittest.TestCase):
    """Prelasci između stranaka: moves between lists that share no party."""

    @classmethod
    def setUpClass(cls):
        cls.data = get('/api/analytics/switchers')
        cls.by_name = {p['name']: p for p in cls.data['people']}
        cls.label = lambda self, k: self.data['parties'][str(k)]['label']

    def path(self, name):
        return [(e['year'], self.label(e['parties'][0])) for e in self.by_name[name]['path']]

    def test_every_move_is_a_change_of_leader(self):
        """Each move: neither list's leader stood on the other list; local
        races on the candidate's own independent list are skipped."""
        from webapp.switchers import party_moves
        for p in self.data['people']:
            self.assertTrue(p['moves'])
            self.assertEqual(party_moves(p['path']), p['moves'], p['name'])
            for m in p['moves']:
                self.assertNotEqual(m['from'], m['to'])

    def test_renames_are_not_moves(self):
        """SKH-SDP -> SDP, Most nezavisnih lista -> MOST, DP Miroslava Škore -> DP;
        no move is between two names that read the same."""
        for p in self.data['people']:
            for m in p['moves']:
                pair = {self.label(m['from']), self.label(m['to'])}
                self.assertNotEqual(len(pair), 1, p['name'])
        # Penava: HDZ (Vukovar 2013/2017, Sabor 2016), DP from 2020, his own list in
        # Vukovar 2021 in between — one move, not three.
        self.assertEqual([(m['year'], self.label(m['to'])) for m in self.by_name['Ivan Penava']['moves']], [(2020, 'DP')])

    def test_known_moves(self):
        self.assertIn((2016, 'Nezavisni'), self.path('Željko Glasnović'))
        # NPS on IDS's EU list 2024 and with SDP for župan 2025: no move after 2024.
        self.assertEqual([(m['year'], self.label(m['to'])) for m in self.by_name['Matija Posavec']['moves']],
                         [(2020, 'SDP'), (2024, 'NPS')])
        # Local races: nominators count; a mayor on his own list in between is no move.
        self.assertEqual([(m['year'], self.label(m['to'])) for m in self.by_name['Zlatko Hasanbegović']['moves']][:1],
                         [(2019, 'NHR')])   # Neovisni za Hrvatsku
        # A coalition partner standing on its own list has not moved (HSLS on HDZ's 2016 list).
        self.assertNotIn('Darinko Kosor', {p['name'] for p in self.data['people'] if p['elected']})

    def test_elected_by_default_is_most_of_the_moves(self):
        elected = [p for p in self.data['people'] if p['elected']]
        self.assertGreater(len(elected), 100)
        self.assertLess(len(elected), len(self.data['people']))


class LocalNominators(unittest.TestCase):
    """Who nominated each executive candidate (set_local_nominators)."""

    def nominators(self, year, slug, person):
        return [r[0] for r in db.session.execute(db.text("""
            select pa.name from elections_candidacy c
            join elections_person p on p.id = c.person_id
            join elections_electorallist el on el.id = c.electoral_list_id
            join elections_electorallist_parties lp on lp.electorallist_id = el.id
            join elections_party pa on pa.id = lp.party_id
            join elections_electionround er on er.id = el.election_round_id and er.round_number = 1
            join elections_election e on e.id = er.election_id and e.year = :y
            join elections_electiontype et on et.id = e.election_type_id and et.slug = :slug
            where p.normalized_name = :n order by lp.id"""), {'y': year, 'slug': slug, 'n': person})]

    def test_every_executive_candidate_has_nominators(self):
        with app.app_context():
            rows = db.session.execute(db.text("""
                select e.year, count(distinct el.id), count(distinct lp.electorallist_id)
                from elections_electorallist el
                join elections_electionround er on er.id = el.election_round_id
                join elections_election e on e.id = er.election_id
                join elections_electiontype et on et.id = e.election_type_id
                left join elections_electorallist_parties lp on lp.electorallist_id = el.id
                where et.slug in ('local_mayor', 'local_city_mayor', 'local_county_prefect')
                group by 1 order by 1""")).fetchall()
        for year, lists, linked in rows:
            with self.subTest(year=year):
                self.assertEqual(linked, lists)

    def test_known_nominators(self):
        with app.app_context():
            self.assertEqual(self.nominators(2025, 'local_county_prefect', 'ANDELKO STRICAK'),
                             ['HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 'HRVATSKA SOCIJALNO - LIBERALNA STRANKA - HSLS',
                              'STRANKA UMIROVLJENIKA SJEVER - SUS'])
            self.assertEqual(self.nominators(2009, 'local_county_prefect', 'PREDRAG STROMAR')[:2],
                             ['HRVATSKA NARODNA STRANKA - LIBERALNI DEMOKRATI - HNS', 'SOCIJALDEMOKRATSKA PARTIJA HRVATSKE - SDP'])
            self.assertEqual(self.nominators(2025, 'local_city_mayor', 'STIPO VELIC'),
                             ['HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ', 'HRVATSKA DEMOKRŠĆANSKA STRANKA - HDS',
                              'HRVATSKA STRANKA UMIROVLJENIKA - HSU'])


class Loyalty(unittest.TestCase):
    """Medalja vjernosti: the same party for the last ten years, still standing."""

    def medal(self, name):
        with app.app_context():
            pid = db.session.execute(db.text(
                "select id from elections_person where normalized_name = :n and disambiguation = ''"), {'n': name}).scalar()
        return get(f'/api/person/{pid}/loyalty')['medal']

    def test_loyal(self):
        m = self.medal('ANDREJ PLENKOVIC')
        self.assertEqual((m['kind'], m['party']['label'], m['from']), ('career', 'HDZ', 2011))
        m = self.medal('PEDA GRBIN')
        self.assertEqual((m['kind'], m['party']['label'], m['gender']), ('career', 'SDP', 'M'))

    def test_not_loyal(self):
        for name in ('JADRANKA KOSOR', 'IVAN PENAVA', 'MATIJA POSAVEC', 'VLADIMIR SISLJAGIC'):
            with self.subTest(name=name):
                self.assertIsNone(self.medal(name))

    def test_rule(self):
        from webapp.switchers import INDEPENDENT, loyalty_of
        ev = lambda y, *p, src='list': {'year': y, 'parties': list(p), 'source': src, 'county': None}
        rule = lambda *evs: loyalty_of(list(evs), year=2026)
        self.assertEqual(rule(ev(2011, 'A'), ev(2015, 'A', 'B'), ev(2024, 'B', 'A'))['party'], 'A')
        self.assertIsNone(rule(ev(2011, 'A'), ev(2024, 'A')))                                # two elections
        self.assertIsNone(rule(ev(2018, 'A'), ev(2021, 'A'), ev(2024, 'A')))                 # eight years to today
        self.assertIsNone(rule(ev(1995, 'A'), ev(2003, 'A'), ev(2011, 'A')))                 # loyal, but no longer standing
        self.assertIsNone(rule(ev(2009, INDEPENDENT), ev(2013, INDEPENDENT), ev(2017, INDEPENDENT)))
        # Their own local list in between neither breaks nor counts.
        self.assertEqual(rule(ev(2013, 'A', src='local'), ev(2016, 'A'), ev(2021, INDEPENDENT, src='local'),
                              ev(2024, 'A'))['elections'], 3)
        # Moved in 2003, then the same party from 2007 on: loyal "since".
        m = rule(ev(2003, 'B'), ev(2007, 'A'), ev(2011, 'A'), ev(2024, 'A'))
        self.assertEqual((m['kind'], m['from'], m['before']), ('since', 2007, 'B'))
        # Moved in 2019: not ten years yet.
        self.assertIsNone(rule(ev(2011, 'B'), ev(2015, 'B'), ev(2019, 'A'), ev(2021, 'A'), ev(2025, 'A')))


class PageMeta(unittest.TestCase):
    """Each page carries its own title, description and link preview
    (webapp/meta.py), since a crawler reading a shared link runs no script."""

    def head(self, path):
        html = client.get(path).get_data(as_text=True)
        tag = lambda pat: (re.search(pat, html) or [None, None])[1]
        return {'title': tag(r'<title>(.*?)</title>'), 'description': tag(r'name="description" content="(.*?)"'),
                'og_title': tag(r'property="og:title" content="(.*?)"'), 'og_image': tag(r'property="og:image" content="(.*?)"')}

    def test_every_route_has_its_own_title(self):
        from app import SPA_ROUTES
        from webapp.meta import PAGE_META
        seen = {}
        for slug in SPA_ROUTES:
            with self.subTest(slug=slug):
                self.assertIn(slug, PAGE_META)                      # a new page needs its title
                h = self.head(f'/{slug}')
                self.assertTrue(h['title'].endswith('· Projekt Izbori'))
                self.assertGreater(len(h['description']), 40)
                self.assertEqual(h['og_title'], h['title'])
                self.assertNotIn(h['title'], seen, seen.get(h['title']))
                seen[h['title']] = slug
        self.assertEqual(self.head('/')['title'], 'Projekt Izbori')

    def test_deep_links_name_what_they_show(self):
        self.assertEqual(self.head('/politicar/1952-jakov-vetma')['title'], 'Jakov Vetma · Projekt Izbori')
        self.assertEqual(self.head('/politicar/1952-x/5-y')['title'], 'Jakov Vetma i Zoran Milanović · Projekt Izbori')
        klis = self.head('/mjesto/439-klis')
        self.assertEqual(klis['title'], 'Klis · Projekt Izbori')
        self.assertIn('Općina Klis, Splitsko-dalmatinska županija', klis['description'])
        self.assertEqual(self.head('/stranke/8-hdz')['title'], 'Hrvatska demokratska zajednica (HDZ) · Projekt Izbori')
        # An id that does not exist still opens the page, with the section's title.
        self.assertEqual(self.head('/mjesto/999999-nema')['title'], 'Općine i gradovi · Projekt Izbori')
        self.assertEqual(self.head('/politicar/nista')['title'], 'Političari · Projekt Izbori')

    def test_icons_and_preview_are_served(self):
        img = self.head('/')['og_image']
        self.assertTrue(img.startswith('http') and 'og-image.png' in img)
        for path, mime in (('/favicon.ico', 'image/png'), ('/static/favicon.svg', 'image/svg+xml'),
                           ('/static/favicon-32.png', 'image/png'), ('/static/apple-touch-icon.png', 'image/png'),
                           ('/static/og-image.png', 'image/png')):
            with self.subTest(path=path):
                r = client.get(path)
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.mimetype, mime)
                r.close()
        png = (ROOT / 'static' / 'og-image.png').read_bytes()
        self.assertEqual((int.from_bytes(png[16:20], 'big'), int.from_bytes(png[20:24], 'big')), (1200, 630))


class FrontendFiles(unittest.TestCase):
    """The site script is split into static/js/*.js files that share one
    global scope and load in the order templates/index.html lists them."""

    @classmethod
    def setUpClass(cls):
        html = (ROOT / 'templates' / 'index.html').read_text(encoding='utf-8')
        cls.order = re.findall(r"asset\('js/([\w-]+\.js)'\)", html)
        cls.html = html

    def test_every_listed_asset_exists(self):
        self.assertIn("asset('css/app.css')", self.html)
        self.assertTrue((ROOT / 'static' / 'css' / 'app.css').exists())
        self.assertEqual(self.order[-1], 'boot.js')        # starts the app: must be last
        for f in self.order:
            with self.subTest(file=f):
                self.assertTrue((ROOT / 'static' / 'js' / f).exists())
        listed = set(self.order)
        on_disk = {p.name for p in (ROOT / 'static' / 'js').glob('*.js')}
        self.assertEqual(on_disk - listed, set(), 'a script on disk that the page never loads')

    def test_no_name_declared_twice(self):
        """The files share one global scope: a `const`/`let`/`class` declared at
        the top of two files is a SyntaxError that stops the second file
        loading (sabor-prediction.js once reused `_pred`, Predsjednički's
        state)."""
        seen, clashes = {}, []
        for f in self.order:
            text = (ROOT / 'static' / 'js' / f).read_text(encoding='utf-8')
            for m in re.finditer(r'^(?:const|let|class)\s+([A-Za-z_$][\w$]*)', text, re.M):
                name = m.group(1)
                if name in seen and seen[name] != f:
                    clashes.append(f'{name}: {seen[name]} and {f}')
                seen.setdefault(name, f)
        self.assertEqual(clashes, [])

    def test_no_load_time_reference_to_a_later_file(self):
        """Code that runs while a file loads (top-level statements) may not
        pass or call a function declared in a file loaded after it: in one
        script that worked by hoisting, across files it is a ReferenceError
        (location.js once passed loadLocationResults, from results.js)."""
        declared = {}
        for i, f in enumerate(self.order):
            text = (ROOT / 'static' / 'js' / f).read_text(encoding='utf-8')
            for m in re.finditer(r'^(?:async )?function\s+([A-Za-z_$][\w$]*)|^(?:const|let|var)\s+([A-Za-z_$][\w$]*)',
                                 text, re.M):
                declared.setdefault(m.group(1) or m.group(2), i)
        problems = []
        for i, f in enumerate(self.order):
            lines = (ROOT / 'static' / 'js' / f).read_text(encoding='utf-8').split('\n')
            for n, line in enumerate(lines, 1):
                if line.startswith((' ', '\t', '//', '}')):
                    continue
                names = re.findall(r'[(,]\s*([A-Za-z_$][\w$]*)\s*[),]', line) + re.findall(r'^([A-Za-z_$][\w$]*)\(', line)
                for name in names:
                    j = declared.get(name)
                    if j is not None and j > i:
                        problems.append(f'{f}:{n} uses {name} from {self.order[j]}')
        self.assertEqual(problems, [])

if __name__ == '__main__':
    unittest.main()
