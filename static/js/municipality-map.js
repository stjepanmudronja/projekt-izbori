// Karta općina: every municipality coloured by one election.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Municipality map (Analitika → Karta općina; /api/map/*) ----
// Outlines: static/hr_municipalities.json, built by tools/build_muni_map.py.
// Main parties keep the colours people know them by; the rest take a palette.
const MAP_PARTY_COLORS = {
    'HDZ': '#1f4ea8', 'SDP': '#e2231a', 'DP': '#6d4c41', 'MOŽEMO!': '#00a676', 'MOST': '#f39200',
    'HSS': '#7cb342', 'IDS': '#29b6f6', 'HNS': '#fdd835', 'HSLS': '#ffb300', 'HSP': '#37474f',
    'HSU': '#ab47bc', 'NPS': '#ec407a', 'SDSS': '#5c6bc0', 'HDSSB': '#00838f', 'NEZAVISNI': '#9e9e9e',
    'ZORAN MILANOVIĆ': '#e2231a', 'IVO JOSIPOVIĆ': '#e2231a', 'DRAGAN PRIMORAC': '#1f4ea8',
    'KOLINDA GRABAR-KITAROVIĆ': '#1f4ea8', 'JADRANKA KOSOR': '#1f4ea8', 'ANDRIJA HEBRANG': '#1f4ea8',
    'STJEPAN MESIĆ': '#fdd835', 'DRAŽEN BUDIŠA': '#ffb300', 'MIROSLAV ŠKORO': '#6d4c41',
    'MILAN BANDIĆ': '#78909c', 'IVAN VILIBOR SINČIĆ': '#c0ca33', 'MARIJA SELAK RASPUDIĆ': '#8e24aa',
};
const MAP_PALETTE = ['#8e44ad', '#16a085', '#d35400', '#2c3e50', '#c0392b', '#27ae60', '#7f8c8d', '#f1c40f', '#e67e22', '#1abc9c'];
const MAP_NO_DATA = '#e9ecef';
const _map = { ready: false, elections: [], kind: 'vijece', yearIdx: 0, round: 1, mode: 'winner', party: null,
               cache: {}, data: null, colors: {} };

async function initMapModule() {
    if (_map.ready) return;
    const spinner = document.getElementById('mapSpinner');
    spinner.classList.add('show');
    try {
        const [shapes, elections] = await Promise.all([
            fetch('/static/hr_municipalities.json').then(r => r.json()),
            fetch('/api/map/elections').then(r => r.json()),
        ]);
        _map.elections = elections.filter(k => k.years.length);
        const wrap = document.getElementById('mapSvgWrap');
        wrap.insertAdjacentHTML('afterbegin', `<svg viewBox="${shapes.viewBox}" xmlns="http://www.w3.org/2000/svg">${
            shapes.shapes.map(s => `<path d="${s.d}" data-id="${s.id ?? ''}" data-name="${escapeHtml(s.name)}"${s.id ? '' : ' class="no-data"'}></path>`).join('')
        }</svg>`);
        document.getElementById('mapSource').textContent = 'Granice: ' + shapes.source;
        const kindSel = document.getElementById('mapKind');
        kindSel.innerHTML = _map.elections.map(k => `<option value="${k.kind}">${escapeHtml(k.label)}</option>`).join('');
        kindSel.value = _map.kind;
        kindSel.addEventListener('change', () => { _map.kind = kindSel.value; _map.party = null; setMapKind(); });
        document.getElementById('mapYear').addEventListener('input', e => { _map.yearIdx = +e.target.value; loadMap(); });
        document.querySelectorAll('#mapModeGroup button').forEach(b => b.addEventListener('click', () => {
            _map.mode = b.dataset.mode;
            document.querySelectorAll('#mapModeGroup button').forEach(x => x.classList.toggle('active', x === b));
            renderMap();
        }));
        document.querySelectorAll('#mapRoundGroup button').forEach(b => b.addEventListener('click', () => {
            _map.round = +b.dataset.round;
            document.querySelectorAll('#mapRoundGroup button').forEach(x => x.classList.toggle('active', x === b));
            loadMap();
        }));
        document.getElementById('mapParty').addEventListener('change', e => { _map.party = e.target.value; renderMap(); });
        const svg = wrap.querySelector('svg');
        svg.addEventListener('mousemove', mapHover);
        svg.addEventListener('mouseleave', () => { document.getElementById('mapTooltip').style.display = 'none'; });
        svg.addEventListener('click', e => {
            const id = parseInt(e.target.dataset && e.target.dataset.id, 10);
            if (!id) return;
            if (mapOpenElection(id)) return;
            if (!activateModule('place', { pushState: false, focusInput: false })) return;
            openPlace(id, { push: true });
        });
        _map.ready = true;
        setMapKind();
    } catch (err) {
        console.error('map init failed', err);
        document.getElementById('mapTitle').textContent = 'Karta trenutačno nije dostupna.';
    } finally {
        spinner.classList.remove('show');
    }
}

function mapKindSpec() { return _map.elections.find(k => k.kind === _map.kind) || _map.elections[0]; }

// A click on a municipality opens the election on show, scoped to that town:
// Predsjednički / EU at its county + municipality and year, local councils on
// the Lokalni page. Sabor has no municipality scope of its own (its pages go by
// electoral district), and a town with no result on the map has nothing to
// open, so both fall back to the town's page. Returns true when it navigated.
function mapOpenElection(muniId) {
    const d = _map.data;
    const m = d && d.munis[muniId];
    if (!m || !m.county_id) return false;
    const year = d.year;
    if (_map.kind === 'vijece') {
        izlNavigateTo('lokalni', year, { kind: 'vijece', countyId: m.county_id, municipalityId: muniId });
        return true;
    }
    if (_map.kind === 'predsjednicki' || _map.kind === 'eu') {
        resultsPreselect(_map.kind, year, m.county_id, muniId);
        return true;
    }
    if (_map.kind === 'sabor' && m.district_id) {
        saborPreselect(year, m.district_id, muniId);
        return true;
    }
    return false;
}

// Open the Sabor page on one year, scoped to an izborna jedinica and a town.
// The module's own init loads the newest year's districts, and loading a year
// clears the scope and reloads its districts, so each step waits for the one
// before: init's district list, then the year (_sabor.year is reset first so
// re-picking the year on show is waited for too), then the district's towns.
function saborPreselect(year, districtId, muniId) {
    const link = document.querySelector('.sidebar-nav a[data-module="sabor-analysis"]');
    if (link) link.click();
    const waitFor = (test, cb, attempts = 0) => {
        if (test()) cb();
        else if (attempts < 80) setTimeout(() => waitFor(test, cb, attempts + 1), 100);
    };
    const hasOption = (sel, v) => sel && Array.from(sel.options).some(o => o.value === String(v));
    const selD = () => document.getElementById('saborSelDistrict');
    const selM = () => document.getElementById('saborSelMuni');
    waitFor(() => document.querySelector(`.sa-year-btn[data-year="${year}"]`)
                  && _sabor.initialized && selD().options.length > 1, () => {
        _sabor.year = null;
        setSaborYears([year]);
        waitFor(() => _sabor.year === year && hasOption(selD(), districtId), () => {
            const d = selD();
            d.value = String(districtId);
            d.dispatchEvent(new Event('change'));
            waitFor(() => hasOption(selM(), muniId), () => {
                const mSel = selM();
                mSel.value = String(muniId);
                mSel.dispatchEvent(new Event('change'));
                document.getElementById('saborScopeArea')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
    });
}

// Open the Predsjednički or EU page on one year, scoped to a county and
// municipality. The year is cleared while the dropdowns are driven, so their
// change handlers (which refetch at the current year) stay idle and only the
// final setActiveYears loads results - no out-of-order responses.
function resultsPreselect(category, year, countyId, muniId) {
    const link = document.querySelector(`.sidebar-nav a[data-module="results-${category}"]`);
    if (link) link.click();
    const p = category === 'predsjednicki' ? 'pred' : 'eus';
    const scope = category === 'predsjednicki' ? _pred : _eus;
    const st = _resultsState[category] || (_resultsState[category] = {});
    st.years = []; st.year = null;
    scope.compareScopes = [];
    (category === 'predsjednicki' ? renderPredCompareChips : renderEusCompareChips)();
    const waitFor = (test, cb, attempts = 0) => {
        if (test()) cb();
        else if (attempts < 50) setTimeout(() => waitFor(test, cb, attempts + 1), 100);
        else cb();
    };
    const hasOption = (sel, v) => sel && Array.from(sel.options).some(o => o.value === String(v));
    const selC = () => document.getElementById(`${p}SelCounty`);
    const selM = () => document.getElementById(`${p}SelMuni`);
    const yearBtn = () => document.querySelector(`#module-results-${category} .results-year-btn[data-year="${year}"]`);
    waitFor(() => hasOption(selC(), countyId) && yearBtn(), () => {
        const c = selC();
        if (hasOption(c, countyId)) {
            c.value = String(countyId);
            c.dispatchEvent(new Event('change'));
        }
        waitFor(() => hasOption(selM(), muniId), () => {
            const mSel = selM();
            if (hasOption(mSel, muniId)) {
                mSel.value = String(muniId);
                mSel.dispatchEvent(new Event('change'));
            }
            setActiveYears(category, [year]);
        });
    });
}

function setMapKind() {
    const spec = mapKindSpec();
    const slider = document.getElementById('mapYear');
    slider.max = spec.years.length - 1;
    _map.yearIdx = spec.years.length - 1;              // the latest election
    slider.value = _map.yearIdx;
    document.getElementById('mapYearTicks').innerHTML = spec.years.map(y => `<span>${y.year}.</span>`).join('');
    loadMap();
}

async function loadMap() {
    const spec = mapKindSpec();
    const y = spec.years[_map.yearIdx];
    document.getElementById('mapYearLabel').textContent = `${y.year}.`;
    const hasRound2 = y.rounds.includes(2);
    document.getElementById('mapRoundWrap').style.display = hasRound2 ? '' : 'none';
    const round = hasRound2 ? _map.round : 1;
    const key = `${spec.kind}|${y.year}|${round}`;
    const spinner = document.getElementById('mapSpinner');
    if (!_map.cache[key]) {
        spinner.classList.add('show');
        try {
            _map.cache[key] = await fetch(`/api/map/data?kind=${spec.kind}&year=${y.year}&round=${round}`).then(r => r.json());
        } finally {
            spinner.classList.remove('show');
        }
    }
    // A later slider move may have overtaken this request.
    if (key !== `${mapKindSpec().kind}|${mapKindSpec().years[_map.yearIdx].year}|${mapKindSpec().years[_map.yearIdx].rounds.includes(2) ? _map.round : 1}`) return;
    _map.data = _map.cache[key];
    // Colours: known parties keep theirs; others in order of municipalities won.
    _map.colors = {};
    let next = 0;
    for (const w of [..._map.data.winners, ..._map.data.parties]) {
        if (!_map.colors[w.key]) _map.colors[w.key] = MAP_PARTY_COLORS[w.key] || MAP_PALETTE[next++ % MAP_PALETTE.length];
    }
    const partySel = document.getElementById('mapParty');
    partySel.innerHTML = _map.data.parties.map(p => `<option value="${escapeHtml(p.key)}">${escapeHtml(p.label)} (${homePct(p.share)})</option>`).join('');
    if (!_map.data.parties.some(p => p.key === _map.party)) _map.party = _map.data.parties.length ? _map.data.parties[0].key : null;
    partySel.value = _map.party || '';
    renderMap();
}

function mapMix(hex, t) {
    // From near-white (t = 0) to the colour (t = 1).
    const n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
    const m = (c, w) => Math.round(w + (c - w) * t);
    return `rgb(${m(r, 247)},${m(g, 248)},${m(b, 250)})`;
}

function renderMap() {
    const d = _map.data;
    if (!d) return;
    const spec = mapKindSpec();
    const party = d.parties.find(p => p.key === _map.party);
    document.getElementById('mapPartyWrap').style.display = _map.mode === 'share' ? '' : 'none';
    const roundTxt = mapKindSpec().years[_map.yearIdx].rounds.includes(2) ? `, ${d.round}. krug` : '';
    const what = _map.mode === 'winner' ? 'pobjednik po općinama i gradovima'
        : _map.mode === 'share' ? `udio: ${party ? party.label : ''}` : 'izlaznost';
    document.getElementById('mapTitle').textContent = `${spec.label} ${d.year}.${roundTxt} - ${what}`;

    const vals = Object.values(d.munis);
    const shareMax = party ? Math.max(1, ...vals.map(m => (m.shares || {})[party.key] || 0)) : 1;
    const turnouts = vals.map(m => m.turnout).filter(t => t != null).sort((a, b) => a - b);
    const tLo = turnouts.length ? turnouts[Math.floor(turnouts.length * 0.02)] : 0;
    const tHi = turnouts.length ? turnouts[Math.ceil(turnouts.length * 0.98) - 1] : 100;
    const fill = m => {
        if (!m) return MAP_NO_DATA;
        if (_map.mode === 'winner') return m.winner ? _map.colors[m.winner] : MAP_NO_DATA;
        if (_map.mode === 'share') return party && m.shares ? mapMix(_map.colors[party.key] || '#1f4ea8', ((m.shares[party.key] || 0) / shareMax) ** 0.8) : MAP_NO_DATA;
        return m.turnout == null ? MAP_NO_DATA : mapMix('#0f3460', Math.min(1, Math.max(0, (m.turnout - tLo) / ((tHi - tLo) || 1))) * 0.9 + 0.1);
    };
    document.querySelectorAll('#mapSvgWrap path').forEach(p => {
        p.style.fill = fill(d.munis[p.dataset.id]);
    });

    const legend = document.getElementById('mapLegend');
    if (_map.mode === 'winner') {
        legend.innerHTML = `<div class="fw-semibold mb-2">Pobjednik u općini / gradu</div>` +
            d.winners.map(w => `<div class="map-legend-row"><i style="background:${_map.colors[w.key]}"></i><span>${escapeHtml(w.label)}</span><span>${w.count}</span></div>`).join('') +
            `<div class="text-muted mt-2" style="font-size:.75rem;">Broj = općine i gradovi u kojima je stranka (kandidat) dobila najviše glasova.</div>`;
    } else if (_map.mode === 'share' && party) {
        legend.innerHTML = `<div class="fw-semibold mb-1">${escapeHtml(party.label)}</div>
            <div class="text-muted" style="font-size:.75rem;">${escapeHtml(party.name)}</div>
            <div class="map-gradient" style="background:linear-gradient(90deg, ${mapMix(_map.colors[party.key] || '#1f4ea8', 0)}, ${_map.colors[party.key] || '#1f4ea8'})"></div>
            <div class="d-flex justify-content-between text-muted" style="font-size:.75rem;"><span>0 %</span><span>${homePct(shareMax)}</span></div>
            <div class="mt-2" style="font-size:.85rem;">Ukupno: <b>${homePct(party.share)}</b></div>`;
    } else {
        legend.innerHTML = `<div class="fw-semibold mb-1">Izlaznost</div>
            <div class="map-gradient" style="background:linear-gradient(90deg, ${mapMix('#0f3460', 0.1)}, ${mapMix('#0f3460', 1)})"></div>
            <div class="d-flex justify-content-between text-muted" style="font-size:.75rem;"><span>${homePct(tLo)} ili manje</span><span>${homePct(tHi)} ili više</span></div>`;
    }
}

function mapHover(e) {
    const tip = document.getElementById('mapTooltip');
    const path = e.target.closest && e.target.closest('path');
    if (!path || !_map.data) { tip.style.display = 'none'; return; }
    const m = _map.data.munis[path.dataset.id];
    const party = _map.data.parties.find(p => p.key === _map.party);
    let html = `<b>${escapeHtml(path.dataset.name)}</b>`;
    if (!m) html += '<br>Nema podataka za ove izbore.';
    else {
        if (m.winner) html += `<br>Pobjednik: ${escapeHtml(m.winner_label)} (${homePct(m.winner_share)})`;
        if (_map.mode === 'share' && party && m.shares) html += `<br>${escapeHtml(party.label)}: ${homePct(m.shares[party.key] || 0)}`;
        if (m.turnout != null) html += `<br>Izlaznost: ${homePct(m.turnout)}`;
    }
    const opensElection = m && m.county_id && (['predsjednicki', 'eu', 'vijece'].includes(_map.kind)
        || (_map.kind === 'sabor' && m.district_id));
    html += `<div class="text-muted mt-1" style="font-size:.72rem;">Klikni za ${opensElection ? 'rezultate ovih izbora u mjestu' : 'stranicu mjesta'}</div>`;
    tip.innerHTML = html;
    const box = document.getElementById('mapSvgWrap').getBoundingClientRect();
    let x = e.clientX - box.left + 14, y = e.clientY - box.top + 14;
    tip.style.display = 'block';
    if (x + tip.offsetWidth > box.width) x = e.clientX - box.left - tip.offsetWidth - 14;
    tip.style.left = `${x}px`;
    tip.style.top = `${y}px`;
}
