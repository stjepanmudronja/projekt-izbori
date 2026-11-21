// National results pages (Predsjednički, EU) by year and scope.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- National results feature ----
const nationalIcons = {
    predsjednicki: 'bi-person-badge',
    eu: 'bi-globe-europe-africa',
    sabor: 'bi-bank',
    lokalni: 'bi-building',
};

let _nationalData = null; // store for re-rendering

const _resultsModuleInitialized = {};
// Per-category active year + selected scope (county/muni/station). Used so
// changing the dropdowns refetches the same year with the new scope.
const _resultsState = {};

// How many compare-scope chips are currently set for this category. Used to
// decide whether year-picker clicks toggle (multi-year mode) or just replace
// (single-year mode, when scope chips already drive the comparison).
function activeScopeChipCount(category) {
    if (category === 'predsjednicki') return (_pred?.compareScopes || []).length;
    if (category === 'eu') return (_eus?.compareScopes || []).length;
    return 0;
}

// Apply the active-year set: update visual state, sync _resultsState, and
// (re)load results. Used by year-picker clicks and external callers
// (izlNavigateTo passes [year]).
function setActiveYears(category, years) {
    const sorted = years.slice().sort((a, b) => a - b);
    const st = _resultsState[category] || (_resultsState[category] = {});
    st.years = sorted;
    st.year = sorted[sorted.length - 1]; // back-compat single-year accessor
    const panel = document.getElementById(`module-results-${category}`);
    if (panel) {
        panel.querySelectorAll('.results-year-btn').forEach(b => {
            b.classList.toggle('active', sorted.includes(parseInt(b.dataset.year, 10)));
        });
    }
    // When 2+ years are active, scope-chip comparison is mutually exclusive
    // (cross-product would explode). Disable the add button visually.
    const addBtnId = category === 'predsjednicki' ? 'predAddCompareBtn'
                   : category === 'eu' ? 'eusAddCompareBtn' : null;
    if (addBtnId) {
        const addBtn = document.getElementById(addBtnId);
        if (addBtn && sorted.length > 1) addBtn.disabled = true;
    }
    loadNationalResults(category, st.year);
}

async function initResultsModule(category) {
    if (_resultsModuleInitialized[category]) return;
    _resultsModuleInitialized[category] = true;

    const panel = document.getElementById(`module-results-${category}`);
    const picker = panel.querySelector('.results-year-picker');

    const res = await fetch('/api/national/election-types');
    const categories = await res.json();
    const cat = categories.find(c => c.key === category);
    if (!cat || !cat.years || !cat.years.length) {
        picker.innerHTML = '<span class="text-muted">Nema podataka</span>';
        return;
    }

    picker.innerHTML = cat.years.map(y =>
        `<button class="btn btn-outline-primary btn-sm sa-year-btn results-year-btn" data-cat="${category}" data-year="${y}">${y}.</button>`
    ).join('') + (cat.years.length > 1
        ? `<small class="text-muted ms-2 align-self-center" style="font-size:0.72rem;">Klikni više godina za usporedbu (max 3).</small>`
        : '');
    picker.querySelectorAll('.results-year-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const yr = parseInt(btn.dataset.year, 10);
            const st = _resultsState[category] || (_resultsState[category] = {});
            const cur = (st.years && st.years.length ? st.years : (st.year ? [st.year] : [])).slice();
            const scopeChipCount = activeScopeChipCount(category);
            let next;
            if (scopeChipCount > 0) {
                // Scope-chip comparison is active; year picker stays single-select.
                next = [yr];
            } else if (cur.includes(yr)) {
                next = cur.filter(y => y !== yr);
                if (next.length === 0) next = [yr]; // never empty
            } else {
                next = cur.concat(yr);
                if (next.length > 3) next = next.slice(-3);
            }
            setActiveYears(category, next);
        });
    });

    // Wire scope dropdowns
    if (category === 'predsjednicki') {
        await initPredsjednickiScope();
    } else if (category === 'eu') {
        await initEuScope();
    }
}

const _pred = { mapPaths: [], compareScopes: [] };

async function initPredsjednickiScope() {
    const selC = document.getElementById('predSelCounty');
    const selM = document.getElementById('predSelMuni');
    const selS = document.getElementById('predSelStation');
    if (!selC || selC._wired) return;
    selC._wired = true;

    try {
        const res = await fetch('/api/counties');
        if (res.ok) {
            const counties = await res.json();
            counties.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                selC.appendChild(opt);
            });
        }
    } catch (e) { console.warn('counties load failed', e); }

    loadPredCroatiaMap().catch(e => console.warn('pred map load failed', e));

    selC.addEventListener('change', async () => {
        selM.innerHTML = '<option value="">Sva mjesta u županiji</option>';
        selS.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
        selM.disabled = true; selS.disabled = true;
        const txt = selC.value ? selC.options[selC.selectedIndex].textContent : '';
        predHighlightMapCounty(txt || null);
        if (selC.value) {
            const r = await fetch(`/api/municipalities/${selC.value}`);
            if (r.ok) {
                (await r.json()).forEach(m => {
                    const o = document.createElement('option');
                    o.value = m.id; o.textContent = m.name;
                    selM.appendChild(o);
                });
                selM.disabled = false;
            }
        }
        predUpdateAddBtn();
        refetchPredsjednickiWithScope();
    });
    selM.addEventListener('change', async () => {
        selS.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
        selS.disabled = true;
        if (selM.value) {
            const r = await fetch(`/api/polling-stations/${selM.value}`);
            if (r.ok) {
                (await r.json()).forEach(s => {
                    const o = document.createElement('option');
                    o.value = s.id; o.textContent = s.name;
                    selS.appendChild(o);
                });
                selS.disabled = false;
            }
        }
        predUpdateAddBtn();
        refetchPredsjednickiWithScope();
    });
    selS.addEventListener('change', () => {
        predUpdateAddBtn();
        refetchPredsjednickiWithScope();
    });

    document.getElementById('predAddCompareBtn').addEventListener('click', onPredAddCompare);
    document.getElementById('predClearScopeBtn').addEventListener('click', onPredClearScope);
}

async function loadPredCroatiaMap() {
    const wrap = document.getElementById('predCroatiaMapWrap');
    const res = await fetch('/static/croatia_map.svg');
    const svgText = await res.text();
    wrap.innerHTML = svgText;
    const embeddedStyle = wrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    const svgTitle = wrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();
    _pred.mapPaths = wrap.querySelectorAll('path[data-county]');
    const label = document.getElementById('predMapCountyLabel');
    _pred.mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const sel = document.getElementById('predSelCounty');
            const countyName = path.getAttribute('data-county');
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].textContent.toUpperCase() === countyName.toUpperCase()) {
                    sel.value = sel.options[i].value;
                    sel.dispatchEvent(new Event('change'));
                    break;
                }
            }
        });
        path.addEventListener('mouseenter', () => {
            if (!path.classList.contains('selected')) label.textContent = path.getAttribute('data-county');
        });
        path.addEventListener('mouseleave', () => {
            const selected = wrap.querySelector('path.selected');
            label.textContent = selected ? selected.getAttribute('data-county') : '';
        });
    });
}

function predHighlightMapCounty(countyName) {
    _pred.mapPaths.forEach(p => p.classList.remove('selected'));
    const label = document.getElementById('predMapCountyLabel');
    if (countyName) {
        const target = document.getElementById('predCroatiaMapWrap')
            .querySelector(`path[data-county="${countyName}"]`);
        if (target) target.classList.add('selected');
        label.textContent = countyName;
    } else {
        if (label) label.textContent = '';
    }
}

function predUpdateAddBtn() {
    const btn = document.getElementById('predAddCompareBtn');
    if (!btn) return;
    // Enable when any scope is selected (county / muni / station). Disabled
    // when multi-year mode is active (mutually exclusive with scope chips).
    const cId = document.getElementById('predSelCounty').value;
    const multiYear = (_resultsState['predsjednicki']?.years?.length || 0) > 1;
    btn.disabled = !cId || multiYear;
}

function predCurrentScopeKey() {
    const sId = document.getElementById('predSelStation').value;
    const mId = document.getElementById('predSelMuni').value;
    const cId = document.getElementById('predSelCounty').value;
    const sel = document.getElementById('predSelStation');
    const selM = document.getElementById('predSelMuni');
    const selC = document.getElementById('predSelCounty');
    if (sId) return { type: 'station', id: parseInt(sId, 10), label: sel.options[sel.selectedIndex].textContent };
    if (mId) return { type: 'municipality', id: parseInt(mId, 10), label: selM.options[selM.selectedIndex].textContent };
    if (cId) return { type: 'county', id: parseInt(cId, 10), label: selC.options[selC.selectedIndex].textContent };
    return null;
}

function onPredAddCompare() {
    const sc = predCurrentScopeKey();
    if (!sc) return;
    const dupe = _pred.compareScopes.find(x => x.type === sc.type && x.id === sc.id);
    if (dupe) return;
    if (_pred.compareScopes.length >= 3) return; // side-by-side cap, mirrors Usporedi module
    _pred.compareScopes.push(sc);
    renderPredCompareChips();
    refetchPredsjednickiWithScope();
}

function onPredRemoveCompare(type, id) {
    _pred.compareScopes = _pred.compareScopes.filter(x => !(x.type === type && x.id === id));
    renderPredCompareChips();
    refetchPredsjednickiWithScope();
}

function onPredClearScope() {
    document.getElementById('predSelCounty').value = '';
    document.getElementById('predSelMuni').innerHTML = '<option value="">Sva mjesta u županiji</option>';
    document.getElementById('predSelStation').innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    document.getElementById('predSelMuni').disabled = true;
    document.getElementById('predSelStation').disabled = true;
    _pred.compareScopes = [];
    predHighlightMapCounty(null);
    predUpdateAddBtn();
    renderPredCompareChips();
    refetchPredsjednickiWithScope();
}

function renderPredCompareChips() {
    const wrap = document.getElementById('predCompareChips');
    if (!wrap) return;
    if (_pred.compareScopes.length === 0) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = _pred.compareScopes.map(s => {
        const typeLabel = s.type === 'station' ? 'BM' : s.type === 'municipality' ? 'Gr/Op' : 'Žup';
        return `<span class="izl-compare-chip">
            <span class="badge bg-secondary me-1" style="font-size:0.6rem;">${typeLabel}</span>
            ${escapeHtml(s.label)}
            <button type="button" class="chip-x" data-type="${s.type}" data-id="${s.id}" aria-label="Ukloni">×</button>
        </span>`;
    }).join('');
    wrap.querySelectorAll('.chip-x').forEach(btn => {
        btn.addEventListener('click', () => onPredRemoveCompare(btn.dataset.type, parseInt(btn.dataset.id, 10)));
    });
}

function refetchPredsjednickiWithScope() {
    const st = _resultsState['predsjednicki'];
    if (!st || !st.year) return; // user hasn't picked a year yet
    loadNationalResults('predsjednicki', st.year);
}
