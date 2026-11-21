// Sabor: final results, hemicycle and the coalition simulator.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Sabor Analysis Module ----
// Electoral district colors for the map
const DISTRICT_COLORS = {
    'I': '#E8A838', 'II': '#E85050', 'III': '#9B59B6', 'IV': '#5B2C6F',
    'V': '#82C341', 'VI': '#F5A0C0', 'VII': '#F0D050', 'VIII': '#2E7D32',
    'IX': '#2E86C1', 'X': '#1A5276',
};

// District Roman numeral to Arabic for matching with data
const DISTRICT_ROMAN_TO_NUM = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
};

let _districtSvgCache = null;

async function loadDistrictMap(wrapperId, labelId, districtData, onClickDistrict) {
    const wrap = document.getElementById(wrapperId);
    if (!wrap) return;

    if (!_districtSvgCache) {
        const res = await fetch('/static/croatia_districts.svg');
        _districtSvgCache = await res.text();
    }

    wrap.innerHTML = _districtSvgCache;
    const svg = wrap.querySelector('svg');
    if (!svg) return;

    // Remove any embedded styles
    const embeddedStyle = svg.querySelector('style');
    if (embeddedStyle) embeddedStyle.remove();

    // Color each district group
    const groups = svg.querySelectorAll('.district-group');
    groups.forEach(g => {
        const distNum = g.dataset.district;
        const color = DISTRICT_COLORS[distNum] || '#ccc';
        g.querySelectorAll('path').forEach(p => { p.style.fill = color; });

        // Hover: show district name in label
        const label = document.getElementById(labelId);
        g.addEventListener('mouseenter', () => {
            if (label) label.textContent = distNum + '. izborna jedinica';
        });
        g.addEventListener('mouseleave', () => {
            if (label && !g.classList.contains('selected')) label.textContent = '';
        });

        // Click: scroll to district details
        g.addEventListener('click', () => {
            // Toggle selection
            groups.forEach(gg => gg.classList.remove('selected'));
            g.classList.add('selected');
            if (label) label.textContent = distNum + '. izborna jedinica';
            if (onClickDistrict) onClickDistrict(distNum);
        });
    });
}

function scrollToDistrict(distRoman, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const num = DISTRICT_ROMAN_TO_NUM[distRoman];
    if (!num) return;
    // Find the district card/section that matches
    const cards = container.querySelectorAll('[data-district-num]');
    for (const card of cards) {
        if (card.dataset.districtNum == num) {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            card.style.transition = 'background 0.3s';
            card.style.background = '#fff3cd';
            setTimeout(() => { card.style.background = ''; }, 2000);
            return;
        }
    }
}

const _saState = {
    rawData: null,
    merges: {},     // listName -> groupLeader
    excluded: new Set(),
    forceInclude: new Set(),  // parties forced above threshold
    computed: null,
    year: null,
    years: [],      // active year set; length > 1 puts the module in compare mode
    jumpersActive: false,
    jumpers: {},   // partyName -> seat delta (+/-)
    jumperSource: null,  // party currently giving seats
};

// Load available years when module shown
async function initSaborAnalysis() {
    const container = document.getElementById('saborAnalysisYears');
    if (container.children.length > 0) return; // already loaded
    const res = await fetch('/api/national/election-types');
    const data = await res.json();
    const sabor = (Array.isArray(data) ? data : data.categories || []).find(c => c.key === 'sabor');
    if (!sabor) { container.innerHTML = '<span class="text-muted">Nema podataka</span>'; return; }
    // 1997 is the Županijski dom, a different chamber — offered here because
    // it is the other house of the same parliament and this is where someone
    // looks for a Sabor year, but set apart and never comparable with the
    // Zastupnički dom years beside it.
    // 1995 and 1992 are the Zastupnički dom, but each under a different
    // mixed *system* — a national list plus first-past-the-post districts, so
    // no D'Hondt runs and neither can join a comparison. They therefore sit
    // with the other standalone years after the separator rather than among
    // the comparable blue ones; the signpost icon (vs the bank on the other
    // chamber) keeps the reason distinguishable.
    const comparableYears = sabor.years.filter(y => !isSaborMixedYear(y));
    container.innerHTML = comparableYears.map(y =>
        `<button class="btn btn-outline-primary btn-sm sa-year-btn" data-year="${y}">${y}.</button>`
    ).join('')
        + `<span class="align-self-center text-muted mx-1" style="font-size:0.9rem;">|</span>`
        // One run, newest first like the blue years, whatever the reason each
        // stands apart; the icon tells the chamber or system.
        + [
            ...SABOR_MIXED_YEARS.filter(y => sabor.years.includes(y)).map(y => [y,
                `<button class="btn btn-outline-secondary btn-sm sa-year-btn" data-year="${y}"
                     title="${SABOR_MIXED_TITLES[y]} Prikazuje se zasebno i ne ulazi u usporedbu.">${y}. <i class="bi bi-signpost-split ms-1"></i></button>`]),
            ...ZUP_DOM_YEARS.map(y => [y,
                `<button class="btn btn-outline-secondary btn-sm sa-year-btn" data-year="${y}"
                     title="Županijski dom - gornji dom Sabora, 1993.-2001.">${y}. <i class="bi bi-bank ms-1"></i></button>`]),
            ...DPV_YEARS.map(y => [y,
                `<button class="btn btn-outline-secondary btn-sm sa-year-btn" data-year="${y}"
                     title="Sabor iz 1990. - Društveno-političko vijeće (80 jedinica), Vijeće općina (115) i Vijeće udruženog rada (160); jednomandatne jedinice, dva kruga.">${y}. <i class="bi bi-columns-gap ms-1"></i></button>`]),
          ].sort((a, b) => b[0] - a[0]).map(([, html]) => html).join('')
        + (sabor.years.length > 1
        ? `<small class="text-muted ms-2 align-self-center" style="font-size:0.72rem;">Klikni više godina za usporedbu (max 3).</small>`
        : '');
    container.querySelectorAll('.sa-year-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Bootstrap paints :focus on .btn-outline-primary with the same
            // filled blue as .active, so a year you just *deselected* keeps
            // looking selected while it holds focus. Harmless when the picker
            // was single-select; misleading now that it's multi-select.
            btn.blur();
            onSaborYearClick(parseInt(btn.dataset.year, 10));
        });
    });
    await initSaborScope();
}

// Year picker is additive, mirroring the EU/predsjednički pickers: clicking a
// second year adds it to the selection (max 3) rather than replacing it.
// Clicking an active year removes it, but the set is never allowed to empty.
// The Županijski dom held exactly two elections, 1993 and 1997, before the
// 2001 amendments abolished it. Both sit after the separator: they are the
// other chamber, so they never join a Zastupnički dom comparison — but they
// can be told apart from each other, which is why there are two buttons and
// not one.
const ZUP_DOM_YEARS = [1997, 1993];
const isZupDomYear = y => ZUP_DOM_YEARS.includes(y);
// The 1990 Sabor had three chambers elected separately, all behind one
// button. A different chamber again, so it is standalone like the Županijski
// dom, with its own icon.
const DPV_YEARS = [1990];
const isDpvYear = y => DPV_YEARS.includes(y);
// 1995 and 1992 are the same chamber as every year beside them, so they belong
// in the year list — but each was elected under a mixed system nothing else
// here shares (a countrywide list plus first-past-the-post districts, with
// separate minority ballots), so each gets its own view and never enters a
// comparison. The two systems also differ from each other, hence two views.
const SABOR_MIXED_YEARS = [1995, 1992];
const isSaborMixedYear = y => SABOR_MIXED_YEARS.includes(y);
const SABOR_MIXED_TITLES = {
    1995: 'Izborni sustav iz 1995. - državna lista, 28 jednomandatnih izbornih jedinica, posebne liste i manjinske jedinice.',
    1992: 'Izborni sustav iz 1992. - državna lista, 60 jednomandatnih izbornih jedinica i 4 posebne jedinice za manjine.',
};

function onSaborYearClick(yr) {
    const cur = (_saState.years && _saState.years.length)
        ? _saState.years.slice()
        : (_saState.year ? [_saState.year] : []);
    let next;
    // Neither 1993/1997 nor 1992/1995 can share the compare grid. The first
    // pair is a different chamber — 63 county seats against 151 district ones
    // is not a comparison — and the second a different electoral system each,
    // with no list standing nationwide in the same sense as 2000 onward.
    // Picking any of them clears the other years rather than adding to them.
    const standalone = y => isZupDomYear(y) || isSaborMixedYear(y) || isDpvYear(y);
    if (standalone(yr) || cur.some(standalone)) {
        next = [yr];
    } else if (_sabor.compareScopes.length > 0) {
        // Scope-chip comparison is active — years stay single-select, since
        // scopes × years would multiply into an unreadable grid.
        next = [yr];
    } else if (cur.includes(yr)) {
        next = cur.filter(y => y !== yr);
        if (next.length === 0) next = [yr];
    } else {
        next = cur.concat(yr);
        if (next.length > 3) next = next.slice(-3);
    }
    setSaborYears(next);
}

// Guards against out-of-order completion. Clicking 2024 then 2020 quickly
// kicks off a single-year load followed by a compare load; the single-year
// load does more work (raw data, district options, maps, simulation), so it
// can finish last and overwrite the compare view with its own state. Every
// load takes a token and abandons itself once a newer one has started.
let _saLoadSeq = 0;

// Single entry point for "which years are active" — used by the picker and by
// deep links, which need to land on exactly one year rather than toggling.
function setSaborYears(years) {
    const sorted = years.slice().sort((a, b) => b - a);
    _saState.years = sorted;
    document.querySelectorAll('.sa-year-btn').forEach(b =>
        b.classList.toggle('active', sorted.includes(parseInt(b.dataset.year, 10))));
    // Scope chips can't be combined with a multi-year comparison.
    const addBtn = document.getElementById('saborAddCompareBtn');
    if (addBtn && sorted.length > 1) addBtn.disabled = true;
    const seq = ++_saLoadSeq;
    const zupArea = document.getElementById('saborZupDomArea');
    const scopeArea = document.getElementById('saborScopeArea');
    const area95 = document.getElementById('sabor1995Area');
    if (area95) area95.style.display = 'none';
    if (sorted.length === 1 && isDpvYear(sorted[0])) {
        // Plurality in 80 single-member units: nothing to allocate either.
        document.getElementById('saborAnalysisArea').style.display = 'none';
        document.getElementById('saborCompareArea').style.display = 'none';
        document.getElementById('saborAnalysisSpinner').style.display = 'none';
        if (zupArea) zupArea.style.display = 'none';
        if (scopeArea) scopeArea.style.display = 'none';
        if (addBtn) addBtn.disabled = true;
        area95.style.display = '';
        loadSabor1990Into(area95, sorted[0], seq);
        return;
    }
    if (sorted.length === 1 && isSaborMixedYear(sorted[0])) {
        // Nothing to allocate here either: every seat (127 in 1995, 138 in
        // 1992) is stated by the DIP report, not derived from a D'Hondt pass.
        document.getElementById('saborAnalysisArea').style.display = 'none';
        document.getElementById('saborCompareArea').style.display = 'none';
        document.getElementById('saborAnalysisSpinner').style.display = 'none';
        if (zupArea) zupArea.style.display = 'none';
        if (scopeArea) scopeArea.style.display = 'none';
        if (addBtn) addBtn.disabled = true;
        area95.style.display = '';
        loadSaborMixedInto(area95, sorted[0], seq);
        return;
    }
    if (sorted.length === 1 && isZupDomYear(sorted[0])) {
        // Nothing to allocate, no districts to scope by, nothing to compare.
        document.getElementById('saborAnalysisArea').style.display = 'none';
        document.getElementById('saborCompareArea').style.display = 'none';
        document.getElementById('saborAnalysisSpinner').style.display = 'none';
        if (scopeArea) scopeArea.style.display = 'none';
        if (addBtn) addBtn.disabled = true;
        zupArea.style.display = '';
        loadZupanijskiDomInto(zupArea, sorted[0], seq);
        return;
    }
    if (zupArea) zupArea.style.display = 'none';
    if (scopeArea) scopeArea.style.display = '';
    if (sorted.length > 1) loadSaborCompare(sorted, seq);
    else loadSaborAnalysis(sorted[0], seq);
}

// Renders the upper house into whichever container asked for it — the
// standalone module and the Sabor page's 1997 button share this and the
// renderer below, so there is one copy of each.
const _zdCache = {};
async function loadZupanijskiDomInto(area, year, seq) {
    year = year || ZUP_DOM_YEARS[0];
    if (!_zdCache[year]) {
        area.innerHTML = '<div class="text-muted p-3">Učitavanje…</div>';
        const res = await fetch(`/api/national/zupanijski-dom/${year}`);
        if (!res.ok) {
            area.innerHTML = `<div class="alert alert-danger">Neuspješno učitavanje (HTTP ${res.status}).</div>`;
            return;
        }
        _zdCache[year] = await res.json();
    }
    if (seq !== undefined && seq !== _saLoadSeq) return;  // a newer click won
    renderZupanijskiDom(_zdCache[year], area);
}

// The 1990 Sabor had three chambers behind the one 1990 button; the view
// switches between them with its own pills, remembering the last one picked.
const _1990Cache = {};
let _sabor1990Chamber = 'dpv';
async function loadSabor1990Into(area, year, seq, chamber) {
    chamber = chamber || _sabor1990Chamber;
    _sabor1990Chamber = chamber;
    const key = `${chamber}/${year}`;
    if (!_1990Cache[key]) {
        area.innerHTML = '<div class="text-muted p-3">Učitavanje…</div>';
        const res = await fetch(`/api/national/sabor-1990/${key}`);
        if (!res.ok) {
            area.innerHTML = `<div class="alert alert-danger">Neuspješno učitavanje (HTTP ${res.status}).</div>`;
            return;
        }
        _1990Cache[key] = await res.json();
    }
    if (seq !== undefined && seq !== _saLoadSeq) return;  // a newer click won
    renderSabor1990(_1990Cache[key], area);
    area.querySelectorAll('[data-chamber]').forEach(btn => btn.addEventListener('click', () => {
        if (btn.dataset.chamber !== chamber) loadSabor1990Into(area, year, _saLoadSeq, btn.dataset.chamber);
    }));
}

const _mixedCache = {};
async function loadSaborMixedInto(area, year, seq) {
    if (!_mixedCache[year]) {
        area.innerHTML = '<div class="text-muted p-3">Učitavanje…</div>';
        const res = await fetch(`/api/national/sabor-${year}`);
        if (!res.ok) {
            area.innerHTML = `<div class="alert alert-danger">Neuspješno učitavanje (HTTP ${res.status}).</div>`;
            return;
        }
        _mixedCache[year] = await res.json();
    }
    if (seq !== undefined && seq !== _saLoadSeq) return;  // a newer click won
    (year === 1992 ? renderSabor1992 : renderSabor1995)(_mixedCache[year], area);
}
