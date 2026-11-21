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
               cache: {}, data: null, colors: {},
               // "Promjena": the earlier election ("kind|year|round"), whether the
               // reader picked it (else it follows the slider), the party key or
               // '__turnout', and the loaded swing figures.
               base: null, baseChosen: false, swingParty: null, swingCache: {}, swing: null };
// Diverging scale for the swing view: loss and gain poles with a neutral
// near-white at no change. Orange and teal on purpose: blue and red are HDZ
// and SDP on this site and would read as parties, not as loss and gain.
const MAP_SWING_LOSS = '#b35806';
const MAP_SWING_GAIN = '#00796b';

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
        }<defs><pattern id="mapHatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="#e9ecef"></rect><line x1="0" y1="0" x2="0" y2="6" stroke="#adb5bd" stroke-width="2"></line>
        </pattern></defs></svg>`);
        document.getElementById('mapSource').textContent = 'Granice: ' + shapes.source;
        const kindSel = document.getElementById('mapKind');
        kindSel.innerHTML = _map.elections.map(k => `<option value="${k.kind}">${escapeHtml(k.label)}</option>`).join('');
        kindSel.value = _map.kind;
        kindSel.addEventListener('change', () => { _map.kind = kindSel.value; _map.party = null; setMapKind(); });
        document.getElementById('mapYear').addEventListener('input', e => { _map.yearIdx = +e.target.value; loadMap(); });
        document.querySelectorAll('#mapModeGroup button').forEach(b => b.addEventListener('click', () => {
            _map.mode = b.dataset.mode;
            document.querySelectorAll('#mapModeGroup button').forEach(x => x.classList.toggle('active', x === b));
            if (_map.mode === 'swing') loadSwing(); else renderMap();
        }));
        document.getElementById('mapBase').addEventListener('change', e => {
            _map.base = e.target.value; _map.baseChosen = true; loadSwing();
        });
        document.getElementById('mapSwingParty').addEventListener('change', e => {
            _map.swingParty = e.target.value; loadSwing();
        });
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
            if (_map.mode !== 'swing' && mapOpenElection(id)) return;
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
    if (_map.mode === 'swing') loadSwing(); else renderMap();
}

// ---- "Promjena": one party's change in share (or turnout) between two elections ----
const mapElectionKey = (kind, year, round) => `${kind}|${year}|${round}`;
// The closed picker shows one option, so each names its kind, not only the group.
const MAP_KIND_SHORT = { predsjednicki: 'Predsjednički', sabor: 'Sabor', eu: 'Europski parlament', vijece: 'Vijeća' };

function mapCurrentElection() {
    const spec = mapKindSpec();
    const y = spec.years[_map.yearIdx];
    return { kind: spec.kind, year: y.year, round: y.rounds.includes(2) ? _map.round : 1 };
}

// The previous election of the same kind (same round where it has one), or
// the next when the one on show is the first.
function mapDefaultBase() {
    const spec = mapKindSpec();
    const cur = mapCurrentElection();
    const other = spec.years[_map.yearIdx > 0 ? _map.yearIdx - 1 : _map.yearIdx + 1];
    if (!other) return null;
    return mapElectionKey(spec.kind, other.year, other.rounds.includes(cur.round) ? cur.round : other.rounds[other.rounds.length - 1]);
}

function mapFillBaseOptions() {
    const cur = mapCurrentElection();
    const curKey = mapElectionKey(cur.kind, cur.year, cur.round);
    if (!_map.baseChosen || !_map.base || _map.base === curKey) _map.base = mapDefaultBase();
    const sel = document.getElementById('mapBase');
    sel.innerHTML = _map.elections.map(k => `<optgroup label="${escapeHtml(k.label)}">${
        k.years.slice().reverse().flatMap(y => y.rounds.map(r => {
            const key = mapElectionKey(k.kind, y.year, r);
            return key === curKey ? '' : `<option value="${key}">${MAP_KIND_SHORT[k.kind] || k.label} ${y.year}.${y.rounds.length > 1 ? ` (${r}. krug)` : ''}</option>`;
        })).join('')
    }</optgroup>`).join('');
    sel.value = _map.base || '';
}

function mapElectionLabel(key) {
    const [kind, year, round] = key.split('|');
    const spec = _map.elections.find(k => k.kind === kind);
    const y = spec && spec.years.find(v => v.year === +year);
    return `${spec ? spec.label : kind} ${year}.${y && y.rounds.length > 1 ? `, ${round}. krug` : ''}`;
}

async function loadSwing() {
    mapFillBaseOptions();
    const cur = mapCurrentElection();
    if (!_map.base) { _map.swing = null; renderMap(); return; }
    const [bk, by, br] = _map.base.split('|');
    const params = new URLSearchParams({ kind: cur.kind, year: cur.year, round: cur.round,
                                         base_kind: bk, base_year: by, base_round: br });
    if (_map.swingParty) params.set('party', _map.swingParty);
    const url = `/api/map/swing?${params}`;
    const spinner = document.getElementById('mapSpinner');
    if (!_map.swingCache[url]) {
        spinner.classList.add('show');
        try {
            let res = await fetch(url).then(r => r.json());
            // The party picked is not on both ballots: fall back to the largest one that is.
            if (res.error && _map.swingParty) {
                params.delete('party');
                res = await fetch(`/api/map/swing?${params}`).then(r => r.json());
            }
            _map.swingCache[url] = res;
        } finally {
            spinner.classList.remove('show');
        }
    }
    // A later choice may have overtaken this request.
    const now = mapCurrentElection();
    if (_map.mode !== 'swing' || mapElectionKey(now.kind, now.year, now.round) !== mapElectionKey(cur.kind, cur.year, cur.round)
        || !_map.base || _map.base !== `${bk}|${by}|${br}`) return;
    const d = _map.swingCache[url];
    _map.swing = d.error ? null : { ...d, base: _map.base, current: mapElectionKey(cur.kind, cur.year, cur.round) };
    if (_map.swing) {
        _map.swingParty = d.party;
        document.getElementById('mapSwingParty').innerHTML =
            d.parties.map(p => `<option value="${escapeHtml(p.key)}">${escapeHtml(p.label)} (${homePct(p.base_share)} → ${homePct(p.share)})</option>`).join('')
            + '<option value="__turnout">Izlaznost</option>';
        document.getElementById('mapSwingParty').value = d.party;
    }
    renderMap();
}

// "+3,4 p.b." / "−2,1 p.b." (postotnih bodova)
const mapPP = v => `${v > 0 ? '+' : v < 0 ? '−' : '±'}${Math.abs(v).toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} p.b.`;

// From the neutral middle to a pole; t in [-1, 1].
function mapSwingColor(t) {
    const pole = t < 0 ? MAP_SWING_LOSS : MAP_SWING_GAIN;
    const n = parseInt(pole.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
    const k = Math.min(1, Math.abs(t)) ** 0.8, mid = [243, 242, 238];
    const m = (c, w) => Math.round(w + (c - w) * k);
    return `rgb(${m(r, mid[0])},${m(g, mid[1])},${m(b, mid[2])})`;
}

// Symmetric scale: the 95th percentile of the changes, rounded up to a round
// number, so one outlier town does not wash out the rest.
function mapSwingLimit(changes) {
    const abs = changes.map(Math.abs).sort((a, b) => a - b);
    const p95 = abs.length ? abs[Math.min(abs.length - 1, Math.floor(abs.length * 0.95))] : 1;
    return [1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100].find(v => v >= p95) || 100;
}

function renderSwing() {
    const sw = _map.swing;
    const legend = document.getElementById('mapLegend');
    const title = document.getElementById('mapTitle');
    if (!sw) {
        title.textContent = 'Promjena - nema izbora za usporedbu';
        document.querySelectorAll('#mapSvgWrap path').forEach(p => { p.style.fill = 'url(#mapHatch)'; });
        legend.innerHTML = '<div class="text-muted">Odaberi izbore za usporedbu.</div>';
        return;
    }
    const turnout = sw.party === '__turnout';
    const party = sw.parties.find(p => p.key === sw.party);
    const what = turnout ? 'izlaznost' : (party ? party.label : sw.party);
    title.textContent = `Promjena: ${what} - ${mapElectionLabel(sw.base)} → ${mapElectionLabel(sw.current)}`;
    const L = mapSwingLimit(Object.values(sw.munis).map(m => m.change));
    document.querySelectorAll('#mapSvgWrap path').forEach(p => {
        const m = sw.munis[p.dataset.id];
        p.style.fill = m ? mapSwingColor(m.change / L) : 'url(#mapHatch)';
    });
    const ranked = Object.values(sw.munis).sort((a, b) => b.change - a.change);
    const row = m => `<div class="row-item"><span>${escapeHtml(m.name)}</span><span>${mapPP(m.change)}</span></div>`;
    const nat = sw.national;
    legend.innerHTML = `<div class="fw-semibold mb-1">${escapeHtml(what)}</div>
        <div class="map-gradient" style="background:linear-gradient(90deg, ${mapSwingColor(-1)}, ${mapSwingColor(0)}, ${mapSwingColor(1)})"></div>
        <div class="d-flex justify-content-between text-muted" style="font-size:.75rem;"><span>${mapPP(-L)} ili više</span><span>0</span><span>${mapPP(L)} ili više</span></div>
        <div class="d-flex justify-content-between text-muted" style="font-size:.75rem;"><span>pad</span><span>rast</span></div>
        ${nat.change != null ? `<div class="mt-2" style="font-size:.85rem;">Ukupno: ${homePct(nat.base)} → <b>${homePct(nat.value)}</b> (${mapPP(nat.change)})</div>` : ''}
        <div class="text-muted" style="font-size:.8rem;">Rast u ${sw.gained}, pad u ${sw.lost} od ${ranked.length} općina i gradova</div>
        <div class="d-flex align-items-center gap-2 mt-2 text-muted" style="font-size:.75rem;">
            <svg width="16" height="12"><rect width="16" height="12" fill="url(#mapHatch)"></rect></svg>nema rezultata na oba glasanja</div>
        <div class="map-swing-list">
            <div class="hd">Najveći rast</div>${ranked.slice(0, 5).filter(m => m.change > 0).map(row).join('') || '<div class="text-muted">-</div>'}
            <div class="hd">Najveći pad</div>${ranked.slice(-5).reverse().filter(m => m.change < 0).map(row).join('') || '<div class="text-muted">-</div>'}
        </div>
        <div class="text-muted mt-2" style="font-size:.72rem;">p.b. = postotni bodovi. ${turnout ? 'Izlaznost birača u općini.'
            : 'Udio od glasova za liste u općini; stranka bez liste u mjestu tamo ima 0 %. Koalicije su pod strankom koja ih predvodi.'}</div>`;
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
    document.getElementById('mapBaseWrap').style.display = _map.mode === 'swing' ? '' : 'none';
    document.getElementById('mapSwingPartyWrap').style.display = _map.mode === 'swing' ? '' : 'none';
    if (_map.mode === 'swing') { renderSwing(); return; }
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
    if (_map.mode === 'swing') {
        const sw = _map.swing;
        const s = sw && sw.munis[path.dataset.id];
        const p = sw && sw.parties.find(x => x.key === sw.party);
        const what = sw && (sw.party === '__turnout' ? 'Izlaznost' : (p ? p.label : sw.party));
        html += !s ? '<br>Nema rezultata na oba glasanja.'
            : `<br>${escapeHtml(what)}: ${homePct(s.base)} → ${homePct(s.value)}<br><b>${mapPP(s.change)}</b>`
              + `<div class="text-muted" style="font-size:.72rem;">${escapeHtml(mapElectionLabel(sw.base))} → ${escapeHtml(mapElectionLabel(sw.current))}</div>`;
        html += `<div class="text-muted mt-1" style="font-size:.72rem;">Klikni za stranicu mjesta</div>`;
        tip.innerHTML = html;
        const box = document.getElementById('mapSvgWrap').getBoundingClientRect();
        let x = e.clientX - box.left + 14, y = e.clientY - box.top + 14;
        tip.style.display = 'block';
        if (x + tip.offsetWidth > box.width) x = e.clientX - box.left - tip.offsetWidth - 14;
        tip.style.left = `${x}px`;
        tip.style.top = `${y}px`;
        return;
    }
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
