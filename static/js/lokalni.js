// Lokalni izbori: per-station, municipality and county results, 1993/1997 wards.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// === Lokalni izbori — per-station results module ===
// `years` are the selected years oldest first, `picked` the same in click
// order (the oldest pick is dropped past 3), `year` the newest of them.
const lok = { initialized: false, year: null, years: [], picked: [], currentRound: 1, mapPaths: [], compareScopes: [] };
const LOK_COUNTY_KINDS = new Set(['zupan', 'zup_skupstina', 'zup_skupstina_ij']);
// 1997's single-member wards (izborne jedinice): each ward is its own race,
// shown as one card per ward rather than one bar chart, and not comparable.
const LOK_WARD_KINDS = new Set(['vijece_ij', 'zup_skupstina_ij']);
// Kinds whose ElectoralLists are 1:1 with a candidate (head-of-executive
// races), so each bar label is a person name and links to that person's page.
// vijece / zup_skupstina lists are party tickets and aren't person-linkable.
const LOK_PERSON_KINDS = new Set(['nacelnik', 'zupan']);
const LOK_KIND_LABELS = {
    vijece: 'Vijeće', nacelnik: 'Načelnik',
    zupan: 'Župan', zup_skupstina: 'Žup. skupština',
    vijece_ij: 'Vijeće (izb. jedinice)', zup_skupstina_ij: 'Žup. skupština (izb. jedinice)',
};

async function initLokalniModule() {
    if (lok.initialized) return;
    lok.initialized = true;
    const selC = document.getElementById('lokSelCounty');
    const selM = document.getElementById('lokSelMuni');
    const selS = document.getElementById('lokSelStation');
    const selK = document.getElementById('lokSelKind');

    const cRes = await fetch('/api/counties');
    if (cRes.ok) {
        const counties = await cRes.json();
        counties.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            selC.appendChild(opt);
        });
    }

    loadLokCroatiaMap().catch(e => console.warn('lok map load failed', e));
    await initLokYearPicker();

    selC.addEventListener('change', onLokCountyChange);
    selM.addEventListener('change', onLokMuniChange);
    selS.addEventListener('change', onLokStationChange);
    selK.addEventListener('change', () => { lokUpdateAddBtn(); loadLokResults(); });

    document.getElementById('lokAddCompareBtn').addEventListener('click', onLokAddCompare);
    document.getElementById('lokClearScopeBtn').addEventListener('click', onLokClearScope);

    document.getElementById('lokShowRound2').addEventListener('change', (e) => {
        lok.currentRound = e.target.checked ? 2 : 1;
        loadLokResults();
    });
}

// Single-member wards (izborne jedinice) exist only in 1993 and 1997, so
// their two kinds are offered only for those years. The options are taken
// out of the list rather than hidden (Safari shows hidden options); a ward
// kind left selected when another year is picked falls back to none.
const LOK_WARD_YEARS = new Set([1993, 1997]);
const _lokWardOptions = [];
function lokSyncKindOptions() {
    const sel = document.getElementById('lokSelKind');
    if (!_lokWardOptions.length) {
        sel.querySelectorAll('option').forEach(o => {
            if (LOK_WARD_KINDS.has(o.value)) _lokWardOptions.push({ opt: o, group: o.parentNode });
        });
    }
    // Compared years share one kind, so wards are offered only when every
    // selected year has them.
    const show = lok.years.length > 0 && lok.years.every(y => LOK_WARD_YEARS.has(y));
    if (!show && LOK_WARD_KINDS.has(sel.value)) {
        sel.value = '';
        lokUpdateAddBtn();
    }
    _lokWardOptions.forEach(({ opt, group }) => {
        if (show && !opt.parentNode) group.appendChild(opt);
        else if (!show && opt.parentNode) opt.remove();
    });
}

// One button per year with lokalni results, newest selected. Picking a year
// keeps the chosen place and race and reloads them for that year. Like the
// other modules' pickers it is additive: a second year joins the selection
// (max 3, the oldest pick dropped first) and the race is shown side by side
// per year; clicking an active year removes it, never emptying the set.
// Scope chips keep it single-select, since scopes × years would multiply.
async function initLokYearPicker() {
    const picker = document.getElementById('lokYearPicker');
    const res = await fetch('/api/lokalni/years');
    const years = res.ok ? await res.json() : [];
    if (!years.length) return;
    picker.insertAdjacentHTML('beforeend', years.map(y =>
        `<button type="button" class="btn btn-outline-primary btn-sm results-year-btn" data-year="${y}">${y}.</button>`
    ).join('') + (years.length > 1
        ? `<small class="text-muted ms-2 align-self-center" style="font-size:0.72rem;">Klikni više godina za usporedbu (max 3).</small>`
        : ''));
    setLokYears([years[0]], false);
    picker.querySelectorAll('.results-year-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // A focused outline button paints like an active one, so a year
            // just deselected would still look selected.
            btn.blur();
            const yr = parseInt(btn.dataset.year, 10);
            let next;
            if (lok.compareScopes.length > 0) {
                next = [yr];
            } else if (lok.picked.includes(yr)) {
                next = lok.picked.filter(y => y !== yr);
                if (next.length === 0) next = [yr];
            } else {
                next = lok.picked.concat(yr).slice(-3);
            }
            setLokYears(next);
        });
    });
}

// Single entry point for the active years — the picker and deep links, which
// must land on exactly one year rather than toggle it.
function setLokYears(years, reload = true) {
    lok.picked = years.slice();
    lok.years = years.slice().sort((a, b) => a - b);
    lok.year = lok.years[lok.years.length - 1];
    document.querySelectorAll('#lokYearPicker .results-year-btn').forEach(b =>
        b.classList.toggle('active', lok.years.includes(parseInt(b.dataset.year, 10))));
    lokSyncKindOptions();
    if (reload) loadLokResults();
}

async function loadLokCroatiaMap() {
    const wrap = document.getElementById('lokCroatiaMapWrap');
    const res = await fetch('/static/croatia_map.svg');
    const svgText = await res.text();
    wrap.innerHTML = svgText;
    const embeddedStyle = wrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    const svgTitle = wrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();
    lok.mapPaths = wrap.querySelectorAll('path[data-county]');
    const label = document.getElementById('lokMapCountyLabel');
    lok.mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const sel = document.getElementById('lokSelCounty');
            const name = path.getAttribute('data-county');
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].textContent.toUpperCase() === name.toUpperCase()) {
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

function lokHighlightMapCounty(name) {
    lok.mapPaths.forEach(p => p.classList.remove('selected'));
    const label = document.getElementById('lokMapCountyLabel');
    if (name) {
        const target = document.getElementById('lokCroatiaMapWrap')
            .querySelector(`path[data-county="${name}"]`);
        if (target) target.classList.add('selected');
        label.textContent = name;
    } else if (label) {
        label.textContent = '';
    }
}

function lokUpdateAddBtn() {
    // County-level kinds need just a county; muni-level kinds need a muni.
    const btn = document.getElementById('lokAddCompareBtn');
    if (!btn) return;
    const cId = document.getElementById('lokSelCounty').value;
    const mId = document.getElementById('lokSelMuni').value;
    const k = document.getElementById('lokSelKind').value;
    if (!k || LOK_WARD_KINDS.has(k)) { btn.disabled = true; return; }
    btn.disabled = LOK_COUNTY_KINDS.has(k) ? !cId : !mId;
}

function lokCurrentScopeKey() {
    const sId = document.getElementById('lokSelStation').value;
    const mId = document.getElementById('lokSelMuni').value;
    const cId = document.getElementById('lokSelCounty').value;
    const k = document.getElementById('lokSelKind').value;
    const selS = document.getElementById('lokSelStation');
    const selM = document.getElementById('lokSelMuni');
    const selC = document.getElementById('lokSelCounty');
    if (!k) return null;
    if (LOK_COUNTY_KINDS.has(k)) {
        if (!cId) return null;
        return { type: 'county', id: parseInt(cId, 10), kind: k,
                 label: selC.options[selC.selectedIndex].textContent };
    }
    if (!mId) return null;
    if (sId) {
        return { type: 'station', id: parseInt(sId, 10), kind: k,
                 label: selS.options[selS.selectedIndex].textContent,
                 muniLabel: selM.options[selM.selectedIndex].textContent };
    }
    return { type: 'municipality', id: parseInt(mId, 10), kind: k,
             label: selM.options[selM.selectedIndex].textContent };
}

function onLokAddCompare() {
    const sc = lokCurrentScopeKey();
    if (!sc) return;
    if (lok.compareScopes.find(x => x.type === sc.type && x.id === sc.id && x.kind === sc.kind)) return;
    if (lok.compareScopes.length >= 3) return; // side-by-side cap
    // Scope chips compare places within one year.
    if (lok.years.length > 1) setLokYears([lok.year], false);
    lok.compareScopes.push(sc);
    renderLokCompareChips();
    loadLokResults();
}

function onLokRemoveCompare(type, id, kind) {
    lok.compareScopes = lok.compareScopes.filter(x => !(x.type === type && x.id === id && x.kind === kind));
    renderLokCompareChips();
    loadLokResults();
}

function onLokClearScope() {
    document.getElementById('lokSelCounty').value = '';
    document.getElementById('lokSelMuni').innerHTML = '<option value="">Odaberi grad/općinu...</option>';
    document.getElementById('lokSelStation').innerHTML = '<option value="">Sva biračka mjesta (cijela općina/grad)</option>';
    document.getElementById('lokSelKind').value = '';
    document.getElementById('lokSelMuni').disabled = true;
    document.getElementById('lokSelStation').disabled = true;
    document.getElementById('lokSelKind').disabled = true;
    lok.compareScopes = [];
    lokHighlightMapCounty(null);
    lokUpdateAddBtn();
    renderLokCompareChips();
    document.getElementById('lokResultsArea').style.display = 'none';
    document.getElementById('lokEmpty').style.display = '';
}

function renderLokCompareChips() {
    const wrap = document.getElementById('lokCompareChips');
    if (!wrap) return;
    if (lok.compareScopes.length === 0) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = lok.compareScopes.map(s => {
        const typeLabel = s.type === 'station' ? 'BM' : (s.type === 'county' ? 'Žup' : 'Gr/Op');
        const kindLabel = LOK_KIND_LABELS[s.kind] || s.kind;
        const sub = s.muniLabel ? ` <span style="color:#888">· ${escapeHtml(s.muniLabel)}</span>` : '';
        return `<span class="izl-compare-chip">
            <span class="badge bg-secondary me-1" style="font-size:0.6rem;">${typeLabel}</span>
            <span class="badge bg-info text-dark me-1" style="font-size:0.6rem;">${kindLabel}</span>
            ${escapeHtml(s.label)}${sub}
            <button type="button" class="chip-x" data-type="${s.type}" data-id="${s.id}" data-kind="${s.kind}" aria-label="Ukloni">×</button>
        </span>`;
    }).join('');
    wrap.querySelectorAll('.chip-x').forEach(btn => {
        btn.addEventListener('click', () => onLokRemoveCompare(btn.dataset.type, parseInt(btn.dataset.id, 10), btn.dataset.kind));
    });
}

function updateLokRoundSwitch() {
    // Switch on == currentRound 2 == render krug 1 and 2 stacked.
    const sw = document.getElementById('lokShowRound2');
    if (sw) sw.checked = lok.currentRound === 2;
}

async function onLokCountyChange() {
    const selC = document.getElementById('lokSelCounty');
    const selM = document.getElementById('lokSelMuni');
    const selS = document.getElementById('lokSelStation');
    const selK = document.getElementById('lokSelKind');
    selM.innerHTML = '<option value="">Odaberi grad/općinu...</option>';
    selS.innerHTML = '<option value="">Sva biračka mjesta (cijela općina/grad)</option>';
    selM.disabled = true; selS.disabled = true;
    const txt = selC.value ? selC.options[selC.selectedIndex].textContent : '';
    lokHighlightMapCounty(txt || null);
    if (lok.compareScopes.length === 0) {
        document.getElementById('lokResultsArea').style.display = 'none';
        document.getElementById('lokEmpty').style.display = '';
    }
    lokUpdateAddBtn();
    if (!selC.value) { selK.disabled = true; return; }
    const res = await fetch(`/api/municipalities/${selC.value}`);
    const data = await res.json();
    data.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id; opt.textContent = m.name;
        selM.appendChild(opt);
    });
    selM.disabled = false;
    selK.disabled = false;
    if (selK.value && LOK_COUNTY_KINDS.has(selK.value)) loadLokResults();
}

async function onLokMuniChange() {
    const selM = document.getElementById('lokSelMuni');
    const selS = document.getElementById('lokSelStation');
    const selK = document.getElementById('lokSelKind');
    selS.innerHTML = '<option value="">Sva biračka mjesta (cijela općina/grad)</option>';
    selS.disabled = true;
    if (lok.compareScopes.length === 0 && (!selK.value || !LOK_COUNTY_KINDS.has(selK.value))) {
        document.getElementById('lokResultsArea').style.display = 'none';
        document.getElementById('lokEmpty').style.display = '';
    }
    lokUpdateAddBtn();
    if (!selM.value) return;
    const res = await fetch(`/api/polling-stations/${selM.value}`);
    const data = await res.json();
    data.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id; opt.textContent = s.name;
        selS.appendChild(opt);
    });
    selS.disabled = false;
    if (selK.value && !LOK_COUNTY_KINDS.has(selK.value)) loadLokResults();
}

function onLokStationChange() {
    const selK = document.getElementById('lokSelKind');
    lokUpdateAddBtn();
    if (selK.value) loadLokResults();
}

// 1993/1997 wards: one card per izborna jedinica with its candidates.
async function loadLokWards(sc) {
    const empty = document.getElementById('lokEmpty');
    const area = document.getElementById('lokResultsArea');
    const spinner = document.getElementById('lokSpinner');
    empty.style.display = 'none';
    area.style.display = 'none';
    spinner.style.display = '';
    document.getElementById('lokRoundToggle').classList.add('d-none');
    const years = lok.years.length ? lok.years : [lok.year || 1997];
    const parts = await Promise.all(years.map(async y => {
        const params = new URLSearchParams({ year: y });
        params.set(sc.type === 'county' ? 'county_id' : 'municipality_id', sc.id);
        const res = await fetch('/api/lokalni/wards?' + params.toString());
        const data = await res.json().catch(() => ({}));
        return lokWardsHtml(res, data, years.length > 1 ? 'col-12' : 'col-md-6');
    }));
    spinner.style.display = 'none';
    area.style.display = '';
    if (years.length === 1) {
        area.innerHTML = parts[0];
        return;
    }
    const kindLabel = LOK_KIND_LABELS[sc.kind] || sc.kind;
    area.innerHTML = `<div class="compare-grid scope-compare-grid">${years.map((y, i) => `
        <div class="compare-card">
            <div class="compare-card-header">
                <h6><i class="bi bi-calendar3 me-1"></i>${y}.</h6>
                <span class="badge bg-info text-dark" style="font-size:0.65rem;">${kindLabel}</span>
            </div>
            <div class="compare-card-body">${parts[i]}</div>
        </div>`).join('')}</div>`;
}

function lokWardsHtml(res, data, colClass) {
    if (!res.ok) {
        return `<div class="alert alert-warning">${escapeHtml(data.error || `HTTP ${res.status}`)}</div>`;
    }
    if (!data.wards.length) {
        return '<div class="alert alert-info">Za ovo mjesto nema izbornih jedinica (sva su mjesta dodijeljena po listama).</div>';
    }
    const fmt = n => (n ?? 0).toLocaleString('hr-HR');
    return `
        <div class="text-muted small mb-2"><i class="bi bi-info-circle me-1"></i>
            ${escapeHtml(data.election_type)} ${data.year}. - dio vijeća biran je u jednomandatnim izbornim jedinicama
            (relativnom većinom), uz mjesta dodijeljena po listama.</div>
        <div class="row g-3">${data.wards.map(w => `
            <div class="${colClass}"><div class="card h-100"><div class="card-body">
                <h6 class="card-title mb-1">${escapeHtml(w.name)}</h6>
                ${w.registered_voters ? `<div class="text-muted small mb-2">Birača ${fmt(w.registered_voters)},
                    glasovalo ${fmt(w.ballots_cast)}, nevažećih ${fmt(w.invalid_ballots)}</div>` : ''}
                <table class="table table-sm mb-0"><tbody>${w.candidates.map(c => `
                    <tr class="${c.winner ? 'fw-semibold' : ''}">
                        <td>${c.winner ? '<i class="bi bi-check-circle-fill text-success me-1" title="Izabran(a)"></i>' : ''}${personLinkHtml(c.name, c.person_id)}</td>
                        <td class="text-muted small">${escapeHtml(c.party)}</td>
                        <td class="text-end">${w.winner_only ? '<span class="text-muted small" title="Izvješće za ovu jedinicu navodi samo izabranog kandidata">samo izabrani</span>'
                            : w.unopposed && c.votes == null ? '<span class="text-muted small">jedini kandidat</span>' : fmt(c.votes)}</td>
                        <td class="text-end text-muted small">${c.votes_pct != null ? c.votes_pct.toFixed(2) + ' %' : ''}</td>
                    </tr>`).join('')}</tbody></table>
            </div></div></div>`).join('')}</div>`;
}

async function loadLokResults() {
    const empty = document.getElementById('lokEmpty');
    const area = document.getElementById('lokResultsArea');
    const spinner = document.getElementById('lokSpinner');

    // Define what to fetch:
    //   - compare mode (chips exist): one fetch per chip using its own kind
    //   - single mode (no chips): use the current dropdown selection
    const targets = [];
    if (lok.compareScopes.length > 0) {
        lok.compareScopes.forEach((sc, i) => {
            targets.push({ scope: sc, prefix: `cmp${i}_` });
        });
    } else {
        const countyId = document.getElementById('lokSelCounty').value;
        const muniId = document.getElementById('lokSelMuni').value;
        const stationId = document.getElementById('lokSelStation').value;
        const kind = document.getElementById('lokSelKind').value;
        if (!kind) return;
        let sc;
        if (LOK_COUNTY_KINDS.has(kind)) {
            if (!countyId) return;
            sc = { type: 'county', id: parseInt(countyId, 10), kind };
        } else {
            if (!stationId && !muniId) return;
            sc = stationId
                ? { type: 'station', id: parseInt(stationId, 10), kind }
                : { type: 'municipality', id: parseInt(muniId, 10), kind };
        }
        if (LOK_WARD_KINDS.has(kind)) return loadLokWards(sc);
        // Several years picked: the one race once per year, side by side.
        if (lok.years.length > 1) {
            lok.years.forEach(y => targets.push({ scope: sc, year: y, prefix: `y${y}_` }));
        } else {
            targets.push({ scope: sc, prefix: '' });
        }
    }

    empty.style.display = 'none';
    area.style.display = 'none';
    spinner.style.display = '';

    // The switch shows every later round: the runoff, and in 2021 also the
    // one repeat vote (Kraljevec na Sutli's načelnik went to a third round).
    // Rounds the race doesn't have are dropped once rounds_available is known.
    const roundsToFetch = lok.currentRound === 2 ? [1, 2, 3] : [1];
    const fetchOne = async (sc, rn, year) => {
        const params = new URLSearchParams({ kind: sc.kind, round: rn });
        if (year || lok.year) params.set('year', year || lok.year);
        if (sc.type === 'station') params.set('station_id', sc.id);
        else if (sc.type === 'county') params.set('county_id', sc.id);
        else params.set('municipality_id', sc.id);
        const res = await fetch('/api/lokalni/station-results?' + params.toString());
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            return { error: err.error || `HTTP ${res.status}`, round: rn, kind: sc.kind };
        }
        return await res.json();
    };

    // For each target (chip or single), fetch all wanted rounds in parallel.
    const blocks = await Promise.all(targets.map(async t => {
        const results = await Promise.all(roundsToFetch.map(rn => fetchOne(t.scope, rn, t.year)));
        return { target: t, results };
    }));
    spinner.style.display = 'none';

    // Round switch visibility — based on the first successful round's metadata.
    // `rounds_available` is per-kind: nacelnik/zupan have a runoff, vijece and
    // zup_skupstina are decided in one round.
    const toggle = document.getElementById('lokRoundToggle');
    const meta = blocks.flatMap(b => b.results).find(r => !r.error);
    const avail = (meta && meta.rounds_available) || [1];
    if (avail.length > 1) {
        toggle.classList.remove('d-none');
    } else {
        // Kind has no runoff — hide the switch and fall back to krug 1, so the
        // choice doesn't persist into a kind that can't honour it.
        toggle.classList.add('d-none');
        lok.currentRound = 1;
    }
    updateLokRoundSwitch();

    // Drop rounds this kind doesn't have. Without this, turning the switch on
    // for Gradonačelnik and then picking Gradsko vijeće renders a "no round 2
    // for election N" warning, because the fetch above already went out with
    // the previous kind's round selection.
    blocks.forEach(b => { b.results = b.results.filter(r => avail.includes(r.round)); });
    // A later round exists for the whole race type, not for every place: most
    // municipalities elected their načelnik in round 1, and only Kraljevec na
    // Sutli had a third. Drop a later round with no votes in this scope rather
    // than draw an empty card.
    blocks.forEach(b => { b.results = b.results.filter(r => r.error || r.round === 1 || r.total_votes > 0); });

    // Single mode (one place, one year): just stack the round cards as before.
    const compareMode = targets.length > 1;
    if (!compareMode) {
        area.innerHTML = blocks[0].results.map(d => d.error
            ? `<div class="alert alert-warning">${escapeHtml(d.error)} (krug ${d.round})</div>`
            : renderLokResultCard(Object.assign(d, { _chartPrefix: blocks[0].target.prefix }))
        ).join('');
        area.style.display = '';
        return;
    }

    // Compare mode: one column per chip or per year, side-by-side (max 3).
    const cols = blocks.map(b => {
        const sc = b.target.scope;
        const kindLabel = LOK_KIND_LABELS[sc.kind] || sc.kind;
        const headerLabel = b.target.year ? `${b.target.year}.`
            : sc.muniLabel ? `${sc.label} (${sc.muniLabel})` : sc.label;
        const cardsHtml = b.results.map(d => d.error
            ? `<div class="alert alert-warning">${escapeHtml(d.error)} (krug ${d.round})</div>`
            : renderLokResultCard(Object.assign(d, { _chartPrefix: b.target.prefix }))
        ).join('');
        return `<div class="compare-card">
            <div class="compare-card-header">
                <h6><i class="bi ${b.target.year ? 'bi-calendar3' : 'bi-geo-alt'} me-1"></i>${escapeHtml(headerLabel || '')}</h6>
                <span class="badge bg-info text-dark" style="font-size:0.65rem;">${kindLabel}</span>
            </div>
            <div class="compare-card-body">${cardsHtml}</div>
        </div>`;
    }).join('');
    area.innerHTML = `<div class="compare-grid scope-compare-grid">${cols}</div>`;
    area.style.display = '';
}

function renderLokResultCard(data) {
    // Reuse the global predsjednicki/sabor bar-chart renderer so we get
    // drag-to-merge and the "Poništi" reset button for free.
    const prefix = data._chartPrefix || '';
    const chartId = `lok_${prefix}r${data.round}`;
    const palette = [
        '#0f3460', '#dc3545', '#198754', '#fd7e14', '#6f42c1',
        '#0dcaf0', '#ca8a04', '#db2777', '#4f46e5', '#059669',
        '#d97706', '#7c3aed', '#0d9488', '#e11d48', '#6366f1',
        '#65a30d', '#c026d3', '#0284c7', '#b91c1c', '#047857',
    ];
    const items = (data.items || []).filter(i => i.votes > 0);
    // Executive races (nacelnik/zupan) have one candidate per list, so each
    // bar label is a person name — buildBarChart turns those into clickable
    // links to that politician's page via data.kind === 'person'.
    const barKind = LOK_PERSON_KINDS.has(data.kind) ? 'person' : 'party';
    if (!window._electionBarData) window._electionBarData = {};
    window._electionBarData[chartId] = {
        kind: barKind,
        original: items.map((it, i) => ({
            name: it.name, votes: it.votes, personId: it.person_id,
            color: palette[i % palette.length], origNames: [it.name],
        })),
        current: items.map((it, i) => ({
            name: it.name, votes: it.votes, personId: it.person_id,
            color: palette[i % palette.length], origNames: [it.name],
        })),
        validBallots: (data.turnout && data.turnout.valid_ballots) || data.total_votes || 0,
    };
    // Defer to after innerHTML is in DOM
    setTimeout(() => buildBarChart(chartId), 0);

    const t = data.turnout;
    const turnoutPct = t && t.registered_voters > 0
        ? (t.ballots_cast / t.registered_voters) * 100 : 0;

    // Bar chart placeholder — populated by buildBarChart(chartId) after insertion.
    const bars = `
        <div class="bar-chart-area" id="barChart_${chartId}" data-election-idx="${chartId}"></div>
        <div class="d-flex justify-content-between align-items-center mt-1">
            <div class="bar-drag-hint"><i class="bi bi-arrows-move me-1"></i>Povuci stupac na drugi za spajanje rezultata</div>
            <button class="btn btn-outline-secondary bar-reset-btn" onclick="resetBarChart('${chartId}')" style="display:none;" id="resetBtn_${chartId}">
                <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
            </button>
        </div>`;

    const noVotes = items.length === 0
        ? '<div class="text-muted text-center py-3">Nema rezultata za ovo biračko mjesto u odabranoj vrsti izbora.</div>'
        : '';

    // 2001-2009: who led each list, the first in bold — before 2009 the nearest the
    // result comes to naming the executive the council then chose.
    const led = items.filter(i => i.holder);
    const holdersBlock = led.length ? `
        <div class="mt-3">
            <div class="fw-semibold mb-1" style="color:#0f3460; font-size:0.9rem;"><i class="bi bi-person-badge me-1"></i>Nositelji lista</div>
            <table class="table table-sm mb-1"><tbody>
                ${led.map((i, n) => `<tr${n === 0 ? ' class="fw-semibold"' : ''}>
                    <td style="font-size:0.85rem;">${escapeHtml(i.name)}</td>
                    <td style="font-size:0.85rem; white-space:nowrap;">${personLinkHtml(i.holder.name, i.holder.person_id)}</td>
                    <td class="text-end" style="font-size:0.85rem; white-space:nowrap;">${formatNumber(i.votes)}</td>
                </tr>`).join('')}
            </tbody></table>
            ${data.year < 2009 ? `<small class="text-muted fst-italic">* ${LIST_HOLDER_NOTE}</small>` : ''}
        </div>` : '';

    // Per-station turnout breakdown (only present when scope=municipality)
    let stationsBlock = '';
    if (data.stations && data.stations.length > 0) {
        const totalRows = data.stations.length;
        const INITIAL_STATIONS = 12;
        const stationRow = (s, i) => {
            const pct = s.turnout_pct;
            const barWidth = Math.min(100, Math.max(0, pct));
            const barColor = pct >= 50 ? '#198754' : pct >= 30 ? '#fd7e14' : '#dc3545';
            const hidden = i >= INITIAL_STATIONS ? ' class="lok-station-extra" style="display:none;"' : '';
            return `<tr${hidden}>
                <td class="text-muted text-end pe-2" style="width:50px;">${s.number}</td>
                <td style="font-size:0.85rem;" title="${escapeHtml(s.address || '')}">${escapeHtml(s.location || s.name || '')}</td>
                <td class="text-end" style="font-size:0.85rem; white-space:nowrap;">${s.registered_voters.toLocaleString('hr-HR')}</td>
                <td class="text-end" style="font-size:0.85rem; white-space:nowrap;">${s.ballots_cast.toLocaleString('hr-HR')}</td>
                <td style="width:160px;">
                    <div style="background:#f1f3f5; border-radius:4px; position:relative; height:18px;">
                        <div style="width:${barWidth}%; background:${barColor}; height:100%; border-radius:4px;"></div>
                    </div>
                </td>
                <td class="text-end fw-bold" style="white-space:nowrap; color:#0f3460;">${formatPct(pct)}</td>
            </tr>`;
        };
        const tableBody = data.stations.map(stationRow).join('');
        const showMore = totalRows > INITIAL_STATIONS
            ? `<div class="text-center mt-2">
                <button class="btn btn-outline-secondary btn-sm" onclick="document.querySelectorAll('.lok-station-extra').forEach(r => r.style.display=''); this.style.display='none';">
                    <i class="bi bi-chevron-down me-1"></i>Prikaži sve (${totalRows - INITIAL_STATIONS} preostalih)
                </button>
              </div>`
            : '';
        stationsBlock = `
            <details class="mt-3" open>
                <summary class="fw-semibold" style="cursor:pointer; color:#0f3460; font-size:0.9rem;">
                    <i class="bi bi-geo-alt me-1"></i>Izlaznost po biračkim mjestima (${totalRows})
                </summary>
                <div class="table-responsive mt-2">
                    <table class="table table-sm table-hover mb-0">
                        <thead><tr>
                            <th class="text-end pe-2" style="width:50px;">Br.</th>
                            <th>Lokacija</th>
                            <th class="text-end">Upisani</th>
                            <th class="text-end">Glasali</th>
                            <th></th>
                            <th class="text-end">Izlaznost</th>
                        </tr></thead>
                        <tbody>${tableBody}</tbody>
                    </table>
                </div>
                ${showMore}
            </details>`;
    }

    const scopeLine = data.scope === 'station'
        ? `${escapeHtml(data.county)} · ${placeLinkHtml(data.municipality_id, data.municipality)} · ${escapeHtml(data.station_label || '')}${data.station_address ? ` · ${escapeHtml(data.station_address)}` : ''}`
        : `${escapeHtml(data.county)} · ${placeLinkHtml(data.municipality_id, data.municipality)} · <em>cijela ${data.municipality_type === 'grad' ? 'gradska' : 'općinska'} razina</em>`;
    return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                <div>
                    <h5 class="fw-bold mb-1">${escapeHtml(data.election_type)} - ${data.round}. krug</h5>
                    <div class="text-muted" style="font-size:0.85rem;">
                        ${scopeLine}
                    </div>
                </div>
                ${t ? `<div class="text-end">
                    <span class="vote-number">${formatPct(turnoutPct)}</span>
                    <br><small class="text-muted">izlaznost</small>
                </div>` : ''}
            </div>
            ${t ? `<div class="d-flex gap-3 flex-wrap mb-3">
                <small class="text-muted"><i class="bi bi-people me-1"></i>Upisani: <strong>${t.registered_voters.toLocaleString('hr-HR')}</strong></small>
                <small class="text-muted"><i class="bi bi-check2-circle me-1"></i>Glasali: <strong>${t.ballots_cast.toLocaleString('hr-HR')}</strong></small>
                <small class="text-muted"><i class="bi bi-check-lg me-1"></i>Važeći: <strong>${t.valid_ballots.toLocaleString('hr-HR')}</strong></small>
            </div>` : ''}
            ${bars}
            ${noVotes}
            ${holdersBlock}
            ${stationsBlock}
        </div>`;
}
