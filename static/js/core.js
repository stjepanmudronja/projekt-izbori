// Module switching, sidebar, page titles, pretty URLs and shareable links.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// Module switching
const sidebarLinks = document.querySelectorAll('.sidebar-nav a[data-module]');
const modulePanels = document.querySelectorAll('.module-panel');
const moduleTitle = document.getElementById('moduleTitle');

const moduleTitles = {
    home: '<i class="bi bi-stars me-2"></i>Početna',
    person: '<i class="bi bi-person me-2"></i>Političar',
    station: '<i class="bi bi-geo-alt me-2"></i>Prema lokaciji',
    place: '<i class="bi bi-house-door me-2"></i>Općine i gradovi',
    compare: '<i class="bi bi-arrow-left-right me-2"></i>Usporedi biračka mjesta',
    'results-predsjednicki': '<i class="bi bi-person-badge me-2"></i>Predsjednički izbori',
    'results-eu': '<i class="bi bi-globe-europe-africa me-2"></i>EU parlamentarni izbori',
    'results-lokalni': '<i class="bi bi-building me-2"></i>Lokalni izbori',
    'sabor-analysis': '<i class="bi bi-people-fill me-2"></i>Rezultati i koalicije (Sabor)',
    'analytics-turnout': '<i class="bi bi-graph-up me-2"></i>Izlaznost',
    'analytics-map': '<i class="bi bi-map me-2"></i>Karta općina',
    'analytics-parties': '<i class="bi bi-bar-chart-line me-2"></i>Snaga stranaka kroz vrijeme',
    parties: '<i class="bi bi-flag me-2"></i>Stranke',
};

const stationSubnav = document.getElementById('stationSubnav');

// Bidirectional map between module IDs (used internally for DOM lookup) and
// pretty URL slugs (used in the address bar). Keep in sync with SPA_ROUTES in
// app.py — if a module isn't here, the URL falls back to "/".
const MODULE_SLUGS = {
    'home': '',                 // the home page is "/"
    'person': 'politicar',
    'station': 'prema-lokaciji',
    'place': 'mjesto',
    'parties': 'stranke',
    'compare': 'usporedba',
    'results-predsjednicki': 'predsjednicki-izbori',
    'results-eu': 'eu-parlamentarni-izbori',
    'results-lokalni': 'lokalni-izbori',
    'sabor-analysis': 'rezultati-koalicije-sabor',
    'analytics-turnout': 'izlaznost',
    'analytics-map': 'karta',
    'analytics-parties': 'snaga-stranaka',
};
const SLUG_TO_MODULE = Object.fromEntries(Object.entries(MODULE_SLUGS).map(([k, v]) => [v, k]));

function activateModule(mod, opts) {
    opts = opts || {};
    const link = document.querySelector(`.sidebar-nav a[data-module="${mod}"]`);
    if (!link || link.classList.contains('disabled')) return false;

    sidebarLinks.forEach(l => l.classList.remove('active'));
    link.classList.add('active');

    modulePanels.forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`module-${mod}`);
    if (panel) {
        panel.classList.add('active');
        if (opts.focusInput !== false) {
            const input = panel.querySelector('.search-input') || panel.querySelector('#compareSearchInput');
            if (input) input.focus();
        }
    }

    if (mod === 'station' || mod === 'compare') stationSubnav.classList.add('open');
    else stationSubnav.classList.remove('open');

    if (moduleTitles[mod]) moduleTitle.innerHTML = moduleTitles[mod];
    // One PDF export for every page; Sabor and EU keep their own, richer ones.
    document.getElementById('pdfExportBtn').style.display = PDF_SKIP_MODULES.has(mod) ? 'none' : '';

    if (mod === 'home') initHome();
    if (mod === 'place') initPlaceModule();
    if (mod === 'analytics-turnout') initIzlaznost();
    if (mod === 'analytics-map') initMapModule();
    if (mod === 'analytics-parties') initPartyStrength();
    if (mod === 'parties') initPartiesModule();
    if (mod === 'sabor-analysis') initSaborAnalysis();
    if (mod === 'results-lokalni') initLokalniModule();
    else if (mod && mod.startsWith('results-')) {
        initResultsModule(mod.substring('results-'.length));
    }

    if (opts.pushState) {
        const slug = MODULE_SLUGS[mod];
        // Back on Političar / a town page with something on show: its link.
        const path = mod === 'person' ? personPath(_compareItems.person)
            : mod === 'place' ? placePath(_placeShown)
            : mod === 'parties' ? partyPath(_partyShown)
            : (slug ? `/${slug}` : '/');
        if (window.location.pathname !== path) {
            history.pushState({ mod }, '', path);
        }
    }
    return true;
}

sidebarLinks.forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        activateModule(link.dataset.module, { pushState: true });
    });
});
// "Projekt Izbori" in the sidebar, and the home page's shortcut buttons.
document.getElementById('homeBrand').addEventListener('click', e => {
    if (e.metaKey || e.ctrlKey) return;              // a new tab opens "/" itself
    e.preventDefault();
    activateModule('home', { pushState: true, focusInput: false });
});
document.addEventListener('click', e => {
    const go = e.target.closest && e.target.closest('.home-go');
    if (!go) return;
    e.preventDefault();
    activateModule(go.dataset.go, { pushState: true });
});

// ---- Shareable links: /politicar/1952-jakov-vetma[/5-zoran-milanovic] ----
function urlSlug(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[Đđ]/g, 'd')
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
function personPath(items) {
    return items.length ? '/politicar/' + items.map(it => `${it.id}-${urlSlug(it.name)}`).join('/') : '/politicar';
}
let _restoringUrl = null;     // the path being restored, while it loads
// Put the politicians on show in the address bar, so the page can be
// bookmarked or sent. Not while a link is being restored.
function syncPersonUrl() {
    if (_restoringUrl) return;
    const panel = document.getElementById('module-person');
    if (!panel || !panel.classList.contains('active')) return;
    const path = personPath(_compareItems.person);
    if (window.location.pathname !== path) history.pushState({ mod: 'person' }, '', path);
}
async function restorePersonsFromUrl(segments) {
    const ids = segments.map(s => parseInt(s, 10)).filter(n => n > 0);
    const path = window.location.pathname;
    const shown = _compareItems.person.map(it => it.id);
    if (_restoringUrl === path || (ids.length === shown.length && ids.every((id, i) => id === shown[i]))) return;
    _restoringUrl = path;
    try {
        _compareItems.person = [];
        renderCompareTags('person');
        rerenderCompareModule('person');
        for (const id of ids) await loadDetail('person', id);
    } finally {
        _restoringUrl = null;
    }
}
function copyPersonLink(id, name, btn) {
    const url = window.location.origin + personPath([{ id, name }]);
    navigator.clipboard.writeText(url).then(() => {
        btn.innerHTML = '<i class="bi bi-check2"></i>';
        setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg"></i>'; }, 1500);
    });
}
