"""Browser smoke checks: the site in a real Chrome, page by page.

The data checks (test_data.py) read the database and the API; these open
every page in Google Chrome (driven by Playwright, headless) and fail on a
console error, an uncaught exception, a page that opens the wrong module or
shows nothing, and on the interactive features breaking. They start the site
themselves on a free port, so no server needs to be running, and they only
read.

Setup (once): pip install -r requirements-dev.txt   (uses the installed Chrome)
Run:          python -m unittest tests.test_browser -v      (~1-2 min)
"""
import threading
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:                       # not installed: skip, don't fail
    sync_playwright = None

import logging

from werkzeug.serving import make_server

from app import app

# Console messages that are not the site's fault.
IGNORED = ('favicon.ico',)


def setUpModule():
    global server, base, pw, browser
    if sync_playwright is None:
        raise unittest.SkipTest('playwright not installed (pip install -r requirements-dev.txt)')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)      # no request log in the output
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.launch(channel='chrome', headless=True)
    except Exception as exc:
        pw.stop()
        server.shutdown()
        raise unittest.SkipTest(f'Google Chrome not available: {exc}')


def tearDownModule():
    browser.close()
    pw.stop()
    server.shutdown()


class Page:
    """A fresh page that records every console error and uncaught exception."""

    def __init__(self, path, wait_ms=0):
        self.errors = []
        self.page = browser.new_page(viewport={'width': 1400, 'height': 900})
        # A failed request is reported by its URL; Chrome's console line for it names none.
        self.page.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text
                     and self.errors.append(f'console: {m.text}'))
        self.page.on('response', lambda r: r.status >= 400 and not any(i in r.url for i in IGNORED)
                     and self.errors.append(f'HTTP {r.status}: {r.url.replace(base, "")}'))
        self.page.on('pageerror', lambda e: self.errors.append(f'exception: {e}'))
        self.page.goto(base + path, wait_until='networkidle', timeout=60000)
        if wait_ms:
            self.page.wait_for_timeout(wait_ms)

    def js(self, script, arg=None):
        return self.page.evaluate(script, arg)

    def wait(self, script, timeout=30000):
        self.page.wait_for_function(script, timeout=timeout)

    def close(self):
        self.page.close()


class BrowserTestCase(unittest.TestCase):
    def open(self, path, wait_ms=0):
        p = Page(path, wait_ms)
        self.addCleanup(p.close)
        return p

    def assertNoErrors(self, p):
        self.assertEqual(p.errors, [], 'console errors or exceptions on the page')


class EveryPage(BrowserTestCase):
    PAGES = {
        '/': 'module-home',
        '/politicar': 'module-person',
        '/politicar/3780-franjo-tudman': 'module-person',
        '/prema-lokaciji': 'module-station',
        '/usporedba': 'module-compare',
        '/mjesto/439-klis': 'module-place',
        '/stranke': 'module-parties',
        '/stranke/8-hdz': 'module-parties',
        '/predsjednicki-izbori': 'module-results-predsjednicki',
        '/eu-parlamentarni-izbori': 'module-results-eu',
        '/lokalni-izbori': 'module-results-lokalni',
        '/rezultati-koalicije-sabor': 'module-sabor-analysis',
        '/zupanijski-dom': 'module-sabor-analysis',
        '/izlaznost': 'module-analytics-turnout',
        '/karta': 'module-analytics-map',
        '/snaga-stranaka': 'module-analytics-parties',
    }

    def test_every_page_opens_without_errors(self):
        for path, panel in self.PAGES.items():
            with self.subTest(path=path):
                p = self.open(path, wait_ms=500)
                active = p.js("document.querySelector('.module-panel.active')?.id")
                self.assertEqual(active, panel)
                text = p.js("document.querySelector('.module-panel.active').innerText.length")
                self.assertGreater(text, 50, 'the page shows next to nothing')
                self.assertNoErrors(p)

    def test_politician_page_shows_the_politician(self):
        p = self.open('/politicar/3780-franjo-tudman')
        p.wait("document.querySelector('#module-person').innerText.includes('TUĐMAN')")
        self.assertNoErrors(p)

    def test_party_page_is_visible(self):
        # It once loaded its data into a box that stayed hidden.
        p = self.open('/stranke/8-hdz')
        p.wait("getComputedStyle(document.getElementById('partyDetail')).display !== 'none'"
               " && document.getElementById('partyDetail').innerText.includes('HRVATSKA DEMOKRATSKA ZAJEDNICA')")
        self.assertNoErrors(p)


class Interactions(BrowserTestCase):
    def test_home_cards(self):
        p = self.open('/')
        p.wait("document.querySelectorAll('#homePresidents .home-card').length === 5", timeout=60000)
        self.assertGreater(p.js("document.querySelectorAll('#homeFigures .home-card').length"), 0)
        self.assertNoErrors(p)

    def test_location_results(self):
        p = self.open('/prema-lokaciji')
        p.wait("selCounty.options.length > 1")
        p.js("""() => { const c = [...selCounty.options].find(o => o.text.startsWith('SPLITSKO'));
                         selCounty.value = c.value; selCounty.dispatchEvent(new Event('change')); }""")
        p.wait("[...selMunicipality.options].some(o => o.text === 'KLIS')")
        p.js("""() => { const m = [...selMunicipality.options].find(o => o.text === 'KLIS');
                         selMunicipality.value = m.value; selMunicipality.dispatchEvent(new Event('change'));
                         btnShowResults.click(); }""")
        p.wait("getComputedStyle(document.getElementById('locationDetailSection')).display !== 'none'"
               " && document.getElementById('locationDetailResults').innerText.length > 500", timeout=60000)
        self.assertNoErrors(p)

    def test_presidential_year(self):
        p = self.open('/predsjednicki-izbori')
        p.wait("!!document.querySelector('#module-results-predsjednicki .results-year-btn[data-year=\"2024\"]')")
        p.js("document.querySelector('#module-results-predsjednicki .results-year-btn[data-year=\"2024\"]').click()")
        p.wait("document.querySelector('#module-results-predsjednicki .results-area').innerText.includes('ZORAN MILANOVIĆ')")
        self.assertNoErrors(p)

    def test_sabor_hemicycle(self):
        p = self.open('/rezultati-koalicije-sabor')
        p.wait("!!document.querySelector('.sa-year-btn[data-year=\"2024\"]')")
        p.js("document.querySelector('.sa-year-btn[data-year=\"2024\"]').click()")
        p.wait("document.querySelectorAll('#saActualHemicycle circle').length === 151", timeout=60000)
        self.assertNoErrors(p)

    def test_map_swing(self):
        p = self.open('/karta')
        p.wait("document.getElementById('mapTitle').textContent.length > 0", timeout=60000)
        p.js("document.querySelector('#mapModeGroup button[data-mode=\"swing\"]').click()")
        p.wait("document.getElementById('mapTitle').textContent.startsWith('Promjena:')", timeout=60000)
        self.assertGreater(p.js("[...document.querySelectorAll('#mapSvgWrap path')].filter(x => x.style.fill.startsWith('rgb')).length"), 500)
        self.assertNoErrors(p)

    def test_party_strength(self):
        p = self.open('/snaga-stranaka')
        p.wait("document.querySelectorAll('#psChips .ps-chip').length > 5")
        self.assertTrue(p.js("!!_ps.chart && _ps.chart.data.datasets.length > 0"))
        # A renamed party's old name is a line of its own, which can be switched on.
        p.js("loadPartyStrength('vijeca')")
        p.wait("!!document.querySelector('[data-ps-id=\"45:Hrvatska narodna stranka\"]')")
        p.js("document.querySelector('[data-ps-id=\"45:Hrvatska narodna stranka\"]').click()")
        self.assertTrue(p.js("_ps.chart.data.datasets.some(d => d.label === 'Hrvatska narodna stranka')"))
        self.assertNoErrors(p)


class MyArea(BrowserTestCase):
    """Prema lokaciji, "Moje područje": several places added up."""

    def pick(self, p, county_prefix, town=None):
        p.js("""([prefix]) => { const c = [...selCounty.options].find(o => o.text.startsWith(prefix));
                                selCounty.value = c.value; selCounty.dispatchEvent(new Event('change')); }""", [county_prefix])
        if town:
            p.wait(f"[...selMunicipality.options].some(o => o.text === '{town}')")
            p.js("""([t]) => { const m = [...selMunicipality.options].find(o => o.text === t);
                               selMunicipality.value = m.value; selMunicipality.dispatchEvent(new Event('change')); }""", [town])
        p.js("document.getElementById('btnAddArea').click()")

    def test_build_and_show_an_area(self):
        p = self.open('/prema-lokaciji')
        p.wait("selCounty.options.length > 1")
        for town in ('SPLIT', 'KLIS', 'SOLIN'):
            self.pick(p, 'SPLITSKO', town)
        p.js("document.getElementById('btnAddArea').click()")          # the same town twice is ignored
        self.assertEqual(p.js("_area.items.map(x => x.name)"), ['SPLIT', 'KLIS', 'SOLIN'])
        p.js("document.getElementById('btnShowArea').click()")
        p.wait("document.getElementById('locationDetailName').innerText.includes('Moje područje: SPLIT, KLIS, SOLIN')"
               " && document.getElementById('locationDetailResults').innerText.length > 500", timeout=60000)
        # removing a chip
        p.js("document.querySelector('[data-area-remove=\"1\"]').click()")
        self.assertEqual(p.js("_area.items.map(x => x.name)"), ['SPLIT', 'SOLIN'])
        self.assertNoErrors(p)

    def test_area_link(self):
        p = self.open('/prema-lokaciji#podrucje=m:439;c:17')
        p.wait("document.getElementById('locationDetailName').innerText.includes('Moje područje: KLIS')", timeout=60000)
        self.assertEqual(p.js("_area.items.map(x => x.type + x.id)"), ['m439', 'c17'])
        self.assertNoErrors(p)


class Simulators(BrowserTestCase):
    def test_sabor_prediction_with_real_results_gives_real_seats(self):
        p = self.open('/rezultati-koalicije-sabor')
        mismatches = p.js("""async () => {
            await initPrediction();
            const out = {};
            for (const y of PRED_YEARS) {
                await loadPredictionYear(y);
                const s = predictionSeats(predictedDistricts());
                const o = await fetch('/api/national/sabor-seats/' + y).then(r => r.json());
                const total = Object.values(s).reduce((a, b) => a + b, 0);
                const bad = _saPred.groups.filter(g => (s[g.key] || 0) !== ((o.parties.find(x => x.name === g.key) || {}).seats || 0))
                                          .map(g => g.label);
                if (bad.length || total !== o.total_seats) out[y] = { bad, total, official: o.total_seats };
            }
            return out;
        }""")
        self.assertEqual(mismatches, {})
        self.assertNoErrors(p)

    def test_prediction_link_restores(self):
        p = self.open('/rezultati-koalicije-sabor#predikcija=2024;HDZ:30;SDP:30;MO%C5%BDEMO!:12;k:SDP,MO%C5%BDEMO!,manjine')
        p.wait("document.getElementById('predMajority').innerText.includes('73 od 151')", timeout=60000)
        self.assertNoErrors(p)

    def test_runoff_simulator(self):
        p = self.open('/predsjednicki-izbori')
        p.js("document.querySelector('[data-bs-target=\"#rsCollapse\"]').click()")
        p.wait("document.getElementById('rsResult').innerText.includes('Stvarni drugi krug')")
        # Everyone eliminated stays home: the finalists keep only their round-1 shares.
        share = p.js("""() => { _rs.others.forEach(o => { o.stay = 100; }); updateRunoff();
                               const [a, b] = _rs.finalists; return Math.round(a.votes / (a.votes + b.votes) * 1000) / 10; }""")
        self.assertIn(f"{share:.1f}".replace('.', ','), p.js("document.getElementById('rsResult').innerText"))
        self.assertNoErrors(p)

    def test_runoff_link_restores(self):
        p = self.open('/predsjednicki-izbori#drugi-krug=2019;o=80:20,70:0;f=0:5')
        p.wait("_rs.year === 2019 && _rs.others[0].toB === 80 && _rs.finalStay[1] === 5", timeout=60000)
        self.assertNoErrors(p)


if __name__ == '__main__':
    unittest.main()
