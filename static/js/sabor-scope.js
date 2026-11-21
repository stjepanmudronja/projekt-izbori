// Sabor: izborne jedinice, scope dropdowns, map and compare chips.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// === Sabor scope dropdowns + map + compare chips
const _sabor = { initialized: false, mapPaths: [], compareScopes: [], year: null, scopeSeq: 0 };

async function initSaborScope() {
    const selD = document.getElementById('saborSelDistrict');
    const selM = document.getElementById('saborSelMuni');
    const selS = document.getElementById('saborSelStation');
    if (!selD || _sabor.initialized) return;
    _sabor.initialized = true;

    // Districts depend on the chosen year. Fetch once we know a year — at
    // module-init time we use the most recent year (grabbed from the buttons).
    const yearBtn = document.querySelector('#saborAnalysisYears .sa-year-btn');
    const initYear = yearBtn ? parseInt(yearBtn.dataset.year, 10) : null;
    if (initYear) await loadSaborDistrictOptions(initYear);

    loadSaborDistrictsMap().catch(e => console.warn('sabor districts map load failed', e));

    selD.addEventListener('change', async () => {
        selM.innerHTML = '<option value="">Sva mjesta u izbornoj jedinici</option>';
        selS.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
        selM.disabled = true; selS.disabled = true;
        const num = selD.value ? selD.options[selD.selectedIndex].dataset.number : '';
        saborHighlightMapDistrict(num || null);
        if (selD.value) {
            const yearForFetch = _sabor.year || initYear;
            const r = await fetch(`/api/sabor/district-municipalities/${selD.value}?year=${yearForFetch}`);
            if (r.ok) {
                // Backend still threshold-filters by vote count (≥50) and returns
                // them biggest-first, but we re-sort alphabetically (hr collation)
                // here and show plain names — easier to scan than a list ranked
                // by size.
                const munis = (await r.json()).slice();
                munis.sort((a, b) => a.name.localeCompare(b.name, 'hr'));
                munis.forEach(m => {
                    const o = document.createElement('option');
                    o.value = m.id;
                    o.textContent = m.name;
                    selM.appendChild(o);
                });
                selM.disabled = false;
            }
        }
        saborUpdateAddBtn();
        refreshSaborScopeArea();
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
        saborUpdateAddBtn();
        refreshSaborScopeArea();
    });
    selS.addEventListener('change', () => {
        saborUpdateAddBtn();
        refreshSaborScopeArea();
    });

    document.getElementById('saborAddCompareBtn').addEventListener('click', onSaborAddCompare);
    document.getElementById('saborClearScopeBtn').addEventListener('click', onSaborClearScope);
}

async function loadSaborDistrictOptions(year) {
    const sel = document.getElementById('saborSelDistrict');
    if (!sel) return;
    // Wipe everything except the placeholder
    while (sel.options.length > 1) sel.remove(1);
    try {
        const r = await fetch(`/api/sabor/districts/${year}`);
        if (r.ok) {
            (await r.json()).forEach(d => {
                const opt = document.createElement('option');
                opt.value = d.id;
                opt.textContent = d.name;
                opt.dataset.number = d.number;
                sel.appendChild(opt);
            });
        }
    } catch (e) { console.warn('districts load failed', e); }
}

async function loadSaborDistrictsMap() {
    const wrap = document.getElementById('saborCroatiaMapWrap');
    const res = await fetch('/static/croatia_districts.svg');
    const svgText = await res.text();
    wrap.innerHTML = svgText;
    const embeddedStyle = wrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    const svgTitle = wrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();
    // The districts SVG groups paths by <g data-district="I">. Click any path
    // inside a group to pick that district.
    _sabor.mapPaths = wrap.querySelectorAll('path[data-district]');
    const label = document.getElementById('saborMapCountyLabel');
    const ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI'];
    _sabor.mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const sel = document.getElementById('saborSelDistrict');
            const roman = path.getAttribute('data-district');
            const num = ROMAN.indexOf(roman) + 1;
            for (let i = 0; i < sel.options.length; i++) {
                if (parseInt(sel.options[i].dataset.number || '0', 10) === num) {
                    sel.value = sel.options[i].value;
                    sel.dispatchEvent(new Event('change'));
                    break;
                }
            }
        });
        path.addEventListener('mouseenter', () => {
            label.textContent = `${path.getAttribute('data-district')}. izborna jedinica`;
        });
        path.addEventListener('mouseleave', () => {
            const selected = wrap.querySelector('path.selected');
            label.textContent = selected ? `${selected.getAttribute('data-district')}. izborna jedinica` : '';
        });
    });
}

function saborHighlightMapDistrict(number) {
    _sabor.mapPaths.forEach(p => p.classList.remove('selected'));
    const label = document.getElementById('saborMapCountyLabel');
    if (!number) { if (label) label.textContent = ''; return; }
    const ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X','XI'];
    const roman = ROMAN[parseInt(number, 10) - 1];
    if (!roman) return;
    document.getElementById('saborCroatiaMapWrap')
        .querySelectorAll(`path[data-district="${roman}"]`)
        .forEach(p => p.classList.add('selected'));
    label.textContent = `${roman}. izborna jedinica`;
}

function saborUpdateAddBtn() {
    const btn = document.getElementById('saborAddCompareBtn');
    if (!btn) return;
    // Scope chips and multi-year comparison are mutually exclusive — combining
    // them would fan out into scopes × years columns.
    const multiYear = (_saState.years && _saState.years.length > 1);
    btn.disabled = multiYear || !document.getElementById('saborSelDistrict').value;
}

function saborCurrentScopeKey() {
    const sId = document.getElementById('saborSelStation').value;
    const mId = document.getElementById('saborSelMuni').value;
    const dId = document.getElementById('saborSelDistrict').value;
    const sel = document.getElementById('saborSelStation');
    const selM = document.getElementById('saborSelMuni');
    const selD = document.getElementById('saborSelDistrict');
    if (sId) return { type: 'station', id: parseInt(sId, 10), label: sel.options[sel.selectedIndex].textContent };
    if (mId) return { type: 'municipality', id: parseInt(mId, 10), label: selM.options[selM.selectedIndex].textContent };
    if (dId) return { type: 'district', id: parseInt(dId, 10), label: selD.options[selD.selectedIndex].textContent };
    return null;
}

function onSaborAddCompare() {
    const sc = saborCurrentScopeKey();
    if (!sc) return;
    if (_sabor.compareScopes.find(x => x.type === sc.type && x.id === sc.id)) return;
    if (_sabor.compareScopes.length >= 3) return; // side-by-side cap
    _sabor.compareScopes.push(sc);
    renderSaborCompareChips();
    refreshSaborScopeArea();
}

function onSaborRemoveCompare(type, id) {
    _sabor.compareScopes = _sabor.compareScopes.filter(x => !(x.type === type && x.id === id));
    renderSaborCompareChips();
    refreshSaborScopeArea();
}

function onSaborClearScope() {
    document.getElementById('saborSelDistrict').value = '';
    document.getElementById('saborSelMuni').innerHTML = '<option value="">Sva mjesta u izbornoj jedinici</option>';
    document.getElementById('saborSelStation').innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    document.getElementById('saborSelMuni').disabled = true;
    document.getElementById('saborSelStation').disabled = true;
    _sabor.compareScopes = [];
    saborHighlightMapDistrict(null);
    saborUpdateAddBtn();
    renderSaborCompareChips();
    refreshSaborScopeArea();
}

function renderSaborCompareChips() {
    const wrap = document.getElementById('saborCompareChips');
    if (!wrap) return;
    if (_sabor.compareScopes.length === 0) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = _sabor.compareScopes.map(s => {
        const typeLabel = s.type === 'station' ? 'BM' : s.type === 'municipality' ? 'Gr/Op' : 'IJ';
        return `<span class="izl-compare-chip">
            <span class="badge bg-secondary me-1" style="font-size:0.6rem;">${typeLabel}</span>
            ${escapeHtml(s.label)}
            <button type="button" class="chip-x" data-type="${s.type}" data-id="${s.id}" aria-label="Ukloni">×</button>
        </span>`;
    }).join('');
    wrap.querySelectorAll('.chip-x').forEach(btn => {
        btn.addEventListener('click', () => onSaborRemoveCompare(btn.dataset.type, parseInt(btn.dataset.id, 10)));
    });
}

async function refreshSaborScopeArea() {
    const area = document.getElementById('saborScopeArea');
    if (!area) return;
    if (!_sabor.year) { area.innerHTML = ''; return; }

    // Pick scope: chips OR current dropdowns. National (no scope) → no scope card.
    const scopes = _sabor.compareScopes.length > 0
        ? _sabor.compareScopes.slice()
        : (saborCurrentScopeKey() ? [saborCurrentScopeKey()] : []);
    if (scopes.length === 0) { area.innerHTML = ''; return; }

    area.innerHTML = '<div class="text-muted small"><i class="bi bi-hourglass-split me-1"></i>Učitavam podatke za odabir...</div>';

    // Picking a district and then a town starts two loads; the later pick wins
    // even when the earlier (bigger) one answers last.
    const seq = ++_sabor.scopeSeq;
    const results = await Promise.all(scopes.map(async (sc, i) => {
        const p = new URLSearchParams();
        if (sc.type === 'station') p.set('station_id', sc.id);
        else if (sc.type === 'municipality') p.set('municipality_id', sc.id);
        else if (sc.type === 'district') p.set('district_id', sc.id);
        const r = await fetch(`/api/national/results/sabor/${_sabor.year}?${p.toString()}`);
        const data = r.ok ? await r.json() : { error: `HTTP ${r.status}`, scope_label: sc.label };
        data._chartPrefix = `sabsc${i}_`;
        data._scope = sc;
        return data;
    }));
    if (seq !== _sabor.scopeSeq) return;
    renderSaborScopeBlocks(results);
}

function renderSaborScopeBlocks(results) {
    const area = document.getElementById('saborScopeArea');
    if (!area) return;
    if (!window._electionBarData) window._electionBarData = {};

    const heading = `<h5 class="fw-bold mt-2 mb-2" style="color:#0f3460;">
        <i class="bi bi-bar-chart me-2"></i>Glasovi po listama u odabranim zonama
    </h5>`;

    const cards = results.map(d => {
        if (d.error) {
            return `<div class="compare-card"><div class="compare-card-header"><h6>${escapeHtml(d.scope_label || '')}</h6></div>
                    <div class="compare-card-body"><div class="alert alert-warning mb-0">${escapeHtml(d.error)}</div></div></div>`;
        }
        const el = (d.elections || [])[0];
        const turnoutPct = el && el.registered_voters > 0 ? (el.ballots_cast / el.registered_voters) * 100 : 0;
        const chartId = `sabsc_${d._chartPrefix}r1`;
        return `<div class="compare-card">
            <div class="compare-card-header">
                <h6><i class="bi bi-geo-alt me-1"></i>${escapeHtml(d.scope_label || '')}</h6>
                ${el ? `<span style="font-size:0.78rem;">${formatPct(turnoutPct)} izlaznost</span>` : ''}
            </div>
            <div class="compare-card-body">
                <div class="text-muted" style="font-size:0.78rem; margin-bottom:0.4rem;">Parlamentarni izbori ${d.year}.</div>
                ${el ? `<div class="d-flex gap-2 flex-wrap mb-2" style="font-size:0.78rem;">
                    <small class="text-muted"><i class="bi bi-people me-1"></i>Upisani: <strong>${formatNumber(el.registered_voters)}</strong></small>
                    <small class="text-muted"><i class="bi bi-check2-circle me-1"></i>Glasali: <strong>${formatNumber(el.ballots_cast)}</strong></small>
                </div>` : ''}
                <div class="bar-chart-area" id="barChart_${chartId}" data-election-idx="${chartId}"></div>
                <div class="d-flex justify-content-between align-items-center mt-1">
                    <div class="bar-drag-hint" style="font-size:0.7rem;"><i class="bi bi-arrows-move me-1"></i>Spoji stupce</div>
                    <button class="btn btn-outline-secondary bar-reset-btn btn-sm" onclick="resetBarChart('${chartId}')" style="display:none;" id="resetBtn_${chartId}">
                        <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
                    </button>
                </div>
            </div>
        </div>`;
    }).join('');
    area.innerHTML = heading + `<div class="compare-grid scope-compare-grid">${cards}</div>`;

    // Now populate the bar charts via the shared helper
    results.forEach(d => {
        if (d.error) return;
        const el = (d.elections || [])[0];
        if (!el || !el.top_lists) return;
        const items = el.top_lists.filter(x => x.votes > 0).slice(0, 30);
        if (items.length === 0) return;
        const chartId = `sabsc_${d._chartPrefix}r1`;
        const palette = [
            '#0f3460', '#dc3545', '#198754', '#fd7e14', '#6f42c1',
            '#0dcaf0', '#ca8a04', '#db2777', '#4f46e5', '#059669',
            '#d97706', '#7c3aed', '#0d9488', '#e11d48', '#6366f1',
            '#65a30d', '#c026d3', '#0284c7', '#b91c1c', '#047857',
        ];
        const original = items.map((it, i) => ({
            name: it.name, votes: it.votes,
            color: palette[i % palette.length], origNames: [it.name],
        }));
        window._electionBarData[chartId] = {
            original: JSON.parse(JSON.stringify(original)),
            current: original,
            validBallots: el.valid_ballots,
        };
        buildBarChart(chartId);
    });
}

// `opts` lets compare mode redirect the output into a per-year column instead
// of the single-year card's fixed ids. `idSuffix` keeps the "Prikaži sve"
// toggle scoped to its own column — without it one click would expand the
// candidate table in every year at once.
function renderActualSaborResults(seatsData, opts) {
    opts = opts || {};
    const card = opts.cardEl !== undefined ? opts.cardEl : document.getElementById('saActualResultsCard');
    const hemiEl = opts.hemicycleEl || document.getElementById('saActualHemicycle');
    const legendEl = opts.legendEl || document.getElementById('saActualLegend');
    const candEl = opts.candidateEl || document.getElementById('saActualCandidateList');
    const extraCls = `sa-actual-cand-extra${opts.idSuffix || ''}`;
    if (!seatsData || !seatsData.parties) { if (card) card.style.display = 'none'; return; }
    if (card) card.style.display = 'block';

    const parties = seatsData.parties;
    const totalSeats = seatsData.total_seats || 151;
    const candidates = seatsData.candidates || [];

    const partyColors = {};
    parties.forEach((p, i) => { partyColors[p.name] = hemicycleColors[i % hemicycleColors.length]; });

    // Build seat list with candidate names
    const seatList = [];
    let candIdx = 0;
    parties.forEach(p => {
        for (let i = 0; i < p.seats; i++) {
            const c = candidates[candIdx] || {};
            // `candidate` stays null when the seat has no known holder (pre-2015
            // years publish no candidate names for districts I-XI), so the
            // table can show a placeholder instead of echoing the party name.
            seatList.push({ party: p.name, color: partyColors[p.name], candidate: c.name || null, person_id: c.person_id, district: c.district || '', roles: c.roles });
            candIdx++;
        }
    });
    const namedSeats = seatList.filter(s => s.candidate).length;

    // Hemicycle SVG
    const svgW = 700, svgH = 380, cx = svgW / 2, cy = svgH - 30, dotR = 8, dotSpacing = dotR * 2.5, innerR = 90;
    const rows = []; let totalCap = 0; let r = innerR;
    while (totalCap < seatList.length) { const arc = Math.PI * r; const cap = Math.floor(arc / dotSpacing); rows.push({ radius: r, capacity: cap }); totalCap += cap; r += dotSpacing; }
    const nRows = rows.length; let seatsToPlace = seatList.length; const rowSeats = []; const capSum = rows.reduce((s, r) => s + r.capacity, 0);
    for (let i = 0; i < nRows; i++) { if (i === nRows - 1) rowSeats.push(seatsToPlace); else { const n = Math.round((rows[i].capacity / capSum) * seatList.length); rowSeats.push(Math.min(n, seatsToPlace)); seatsToPlace -= rowSeats[i]; } }
    const positions = [];
    for (let ri = 0; ri < nRows; ri++) { const count = rowSeats[ri]; const radius = rows[ri].radius; for (let i = 0; i < count; i++) { const angle = Math.PI - (Math.PI * (i + 0.5) / count); positions.push({ x: cx + radius * Math.cos(angle), y: cy - radius * Math.sin(angle) }); } }
    positions.sort((a, b) => { const aA = Math.atan2(cy - a.y, a.x - cx); const aB = Math.atan2(cy - b.y, b.x - cx); return aB - aA; });

    let dots = '';
    positions.forEach((pos, i) => {
        const seat = seatList[i]; if (!seat) return;
        const tip = [seat.candidate, seat.party, seat.district].filter(Boolean).join('\n');
        dots += `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}" fill="${seat.color}" stroke="white" stroke-width="1.5" style="cursor:pointer;"><title>${tip}</title></circle>`;
    });

    hemiEl.innerHTML = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:700px; display:block; margin:0 auto;">
            ${dots}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">${totalSeats}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="12" fill="#6c757d">mandata</text>
        </svg>`;

    // Legend — stacked vertically, sorted by seats desc
    const legendParties = [...parties].sort((a, b) => b.seats - a.seats || a.name.localeCompare(b.name));
    legendEl.innerHTML = `
        <div class="d-flex flex-column gap-1 align-items-stretch mx-auto" style="max-width:520px;">
            ${legendParties.map(p => `<div class="d-flex align-items-center gap-1" style="font-size:0.82rem; padding:4px 8px; border-radius:6px;" title="${p.name}">
                <span style="width:14px;height:14px;border-radius:50%;background:${partyColors[p.name]};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15);"></span>
                <span class="fw-semibold">${p.name.length > 35 ? p.name.substring(0, 32) + '...' : p.name}</span>
                <span class="text-muted">(${p.seats})</span>
            </div>`).join('')}
        </div>`;

    // Candidate list with show-more.
    //
    // Two sources, in order of preference:
    //   1. `members` — the curated roster of who actually sat in this saziv
    //      (ParliamentMember). The only source for pre-2015 years, where no
    //      candidate names were published for districts I-XI, and the only one
    //      that knows about mid-term arrivals and departures.
    //   2. `seatList` — holders derived from the results (D'Hondt +
    //      preferential votes), which is all 2015+ needs.
    const members = seatsData.members || [];
    const useRoster = members.length > 0;
    const INITIAL = 100;

    // A roster names each member's own party in full ("SOCIJALDEMOKRATSKA
    // PARTIJA HRVATSKE - SDP"), the same form 2015+ shows, but those are not
    // the joint lists the hemicycle is coloured by — the 2011 Kukuriku list is
    // one colour there and four parties here — so the table gets its own ramp.
    // Some rosters record no party at all — the published list of the 2003
    // saziv is names only — and then the column and the colour dot are
    // dropped rather than shown empty for every row.
    const hasParty = useRoster && members.some(m => m.party);
    // A roster published per district can fill the same Izborna jedinica
    // column the derived years use; one published as a national roll cannot,
    // and keeps Napomena in that slot instead.
    const hasDistrict = useRoster && members.some(m => m.district);
    const hasNote = useRoster && members.some(m => m.note || m.minority);
    const rosterColors = {};
    if (hasParty) {
        const order = [];
        members.forEach(m => { if (!order.includes(m.party)) order.push(m.party); });
        order.forEach((party, i) => { rosterColors[party] = hemicycleColors[i % hemicycleColors.length]; });
    }

    const tableRows = useRoster ? members : seatList;
    const candRows = tableRows.map((row, i) => {
        const hidden = i >= INITIAL ? ` style="display:none;" class="${extraCls}"` : '';
        const color = useRoster ? rosterColors[row.party] : row.color;
        const dot = (useRoster && !hasParty) ? ''
            : `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>`;
        // Clickable name → that politician's page (delegated handler at .bar-label-link).
        // A derived seat with no known holder gets inert placeholder text:
        // linking it would fire a politician search for a party name.
        const name = useRoster ? row.name : row.candidate;
        const nameHtml = name
            ? personLinkHtml(name, row.person_id) + roleBadgesHtml(row)
            : `<span class="text-muted fst-italic" title="Imena kandidata nisu objavljena za ovu izbornu godinu">nije objavljeno</span>`;
        const noteCell = `${row.minority ? '<span class="badge bg-secondary" style="font-size:0.7rem;">nacionalne manjine</span> ' : ''}${escapeHtml(row.note || '')}`;
        const lastCols = useRoster
            ? (hasDistrict ? `<td class="text-muted" style="font-size:0.85rem;">${escapeHtml(row.district || '')}</td>` : '')
              + (hasNote ? `<td class="text-muted" style="font-size:0.85rem;">${noteCell}</td>` : '')
            : `<td class="text-muted" style="font-size:0.85rem;">${row.district}</td>`;
        const partyCell = (useRoster && !hasParty) ? ''
            : `<td class="text-muted" style="font-size:0.85rem;">${escapeHtml(row.party)}</td>`;
        return `<tr${hidden}><td style="width:30px;" class="text-muted text-end pe-2">${i + 1}.</td><td>${dot}${nameHtml}</td>${partyCell}${lastCols}</tr>`;
    }).join('');
    const showBtn = tableRows.length > INITIAL
        ? `<div class="text-center mt-2"><button class="btn btn-outline-primary btn-sm" onclick="document.querySelectorAll('.${extraCls}').forEach(r=>r.style.display='');this.style.display='none';"><i class="bi bi-chevron-down me-1"></i>Prikaži sve (${tableRows.length - INITIAL} preostalih)</button></div>` : '';

    // Explain why the roster can outnumber the seats, or — with no roster —
    // why pre-2015 rows are blank: those years had no preferential voting, so
    // DIP published list totals only for districts I-X(I) and no names.
    let missingNote = '';
    if (useRoster) {
        // The roster holds who *won* a mandate, so it should match the seat
        // count exactly; a shortfall means names are still missing.
        const short = seatList.length - tableRows.length;
        missingNote = `<div class="alert alert-secondary py-2 px-3 mb-2" style="font-size:0.82rem;">
               <i class="bi bi-info-circle me-1"></i>Zastupnici izabrani na ovim izborima. Imena nisu izračunata iz rezultata -
               preferencijsko glasovanje uvedeno je tek 2015., pa za izborne jedinice I.-XI. nisu objavljena imena kandidata.
               Zamjenici koji su mandat preuzeli tijekom saziva nisu na popisu.
               ${hasDistrict ? '' : 'Iz istog razloga nije poznata ni izborna jedinica pojedinog zastupnika.'}
               ${short > 0 ? `Poznato je ${tableRows.length} od ${seatList.length} mandata.` : ''}
               ${hasParty ? '' : 'Objavljeni popis ovog saziva navodi samo imena, bez stranačke pripadnosti.'}
           </div>`;
    } else if (namedSeats < seatList.length) {
        missingNote = `<div class="alert alert-secondary py-2 px-3 mb-2" style="font-size:0.82rem;">
               <i class="bi bi-info-circle me-1"></i>Za ovu izbornu godinu objavljeni su samo rezultati po listama,
               bez imena kandidata (preferencijsko glasovanje uvedeno je 2015.).
               Poznato je ${namedSeats} od ${seatList.length} mandata.
           </div>`;
    }

    // The hemicycle reports the Sabor's full size, but only districts we hold
    // results for can be allocated. 2000 is the case: its diaspora and
    // minority districts returned 6 and 5 members whose per-station results
    // were never published, so "151 mandata" over 140 dots needs explaining.
    // Informational, not a warning — the gap is a permanent property of what
    // DIP released for that year, not something waiting to be fixed.
    if (seatList.length < totalSeats) {
        const missing = [...new Set(seatList.map(x => x.district))].some(d => /XI\./.test(d || ''))
            ? '' : ' Izborne jedinice XI. (dijaspora) i XII. (nacionalne manjine) nisu obuhvaćene objavljenim rezultatima za ovu godinu.';
        missingNote += `<div class="alert alert-secondary py-2 px-3 mb-2" style="font-size:0.82rem;">
               <i class="bi bi-info-circle me-1"></i>Prikazano je ${seatList.length} od ${totalSeats} mandata.${missing}
           </div>`;
    }

    candEl.innerHTML = `
        <h6 class="fw-bold mt-4 mb-2"><i class="bi bi-person-lines-fill me-2"></i>Zastupnici</h6>
        ${missingNote}
        <div class="table-responsive"><table class="table table-sm table-hover mb-0" style="font-size:0.88rem;">
            <thead><tr><th></th><th>Ime i prezime</th>${(useRoster && !hasParty) ? '' : '<th>Stranka / Koalicija</th>'}${useRoster ? ((hasDistrict ? '<th>Izborna jedinica</th>' : '') + (hasNote ? '<th>Napomena</th>' : '')) : '<th>Izborna jedinica</th>'}</tr></thead>
            <tbody>${candRows}</tbody>
        </table></div>${showBtn}`;
}

// Compare 2-3 sazivs side by side. Only "Konačni rezultati" is comparable —
// the coalition simulation is a single interactive sandbox on one shared
// _saState, so it's hidden here and returns when you drop back to one year.
async function loadSaborCompare(years, seq) {
    if (seq === undefined) seq = ++_saLoadSeq;
    const stale = () => seq !== _saLoadSeq;
    const spinner = document.getElementById('saborAnalysisSpinner');
    const single = document.getElementById('saborAnalysisArea');
    const area = document.getElementById('saborCompareArea');
    single.style.display = 'none';
    document.getElementById('saborScopeArea').innerHTML = '';
    area.style.display = 'none';
    spinner.classList.add('show');

    const datasets = await Promise.all(years.map(async y => {
        const r = await fetch(`/api/national/sabor-seats/${y}`);
        if (!r.ok) return { year: y, error: `HTTP ${r.status}` };
        const d = await r.json();
        return { year: y, data: d };
    }));
    if (stale()) return;

    spinner.classList.remove('show');

    const grid = document.createElement('div');
    grid.className = 'compare-grid scope-compare-grid';
    area.innerHTML = '';
    area.appendChild(grid);

    datasets.forEach((ds, i) => {
        const col = document.createElement('div');
        col.className = 'compare-card';
        const seats = ds.data && ds.data.total_seats ? `${ds.data.total_seats} mandata` : '';
        col.innerHTML = `<div class="compare-card-header">
                <h6><i class="bi bi-bank me-1"></i>Sabor ${ds.year}.</h6>
                ${seats ? `<span class="badge bg-info text-dark" style="font-size:0.65rem;">${seats}</span>` : ''}
            </div>`;
        grid.appendChild(col);
        if (ds.error) {
            col.insertAdjacentHTML('beforeend',
                `<div class="compare-card-body"><div class="alert alert-warning mb-0">${escapeHtml(ds.error)}</div></div>`);
            return;
        }
        const body = document.createElement('div');
        body.className = 'compare-card-body';
        const hemi = document.createElement('div');
        const legend = document.createElement('div');
        legend.className = 'mt-3';
        const cands = document.createElement('div');
        cands.className = 'mt-3';
        body.append(hemi, legend, cands);
        col.appendChild(body);
        renderActualSaborResults(ds.data, {
            cardEl: null, hemicycleEl: hemi, legendEl: legend,
            candidateEl: cands, idSuffix: `-cmp${i}`,
        });
    });

    area.style.display = 'block';
}

async function loadSaborAnalysis(year, seq) {
    if (seq === undefined) seq = ++_saLoadSeq;
    const stale = () => seq !== _saLoadSeq;
    document.getElementById('saborCompareArea').style.display = 'none';
    document.querySelectorAll('.sa-year-btn').forEach(b => b.classList.toggle('active', parseInt(b.dataset.year) === year));
    const spinner = document.getElementById('saborAnalysisSpinner');
    const area = document.getElementById('saborAnalysisArea');
    area.style.display = 'none';
    spinner.classList.add('show');

    // Fetch raw data and actual seat results in parallel
    const [rawRes, seatsRes] = await Promise.all([
        fetch(`/api/national/sabor-raw/${year}`),
        fetch(`/api/national/sabor-seats/${year}`),
    ]);
    if (stale()) return;
    const data = await rawRes.json();
    const seatsData = await seatsRes.json();
    if (stale()) return;

    // Render actual results hemicycle
    renderActualSaborResults(seatsData);

    _saState.rawData = data;
    _saState.year = year;
    _saState.years = [year];  // keep the picker's set in sync with single-year loads
    _sabor.year = year; // mirror so the scope card knows the active year
    // District ids vary per year; reload the dropdown for the freshly picked year
    // and clear any stale chips/selection from a different year.
    _sabor.compareScopes = [];
    renderSaborCompareChips();
    onSaborClearScope();
    loadSaborDistrictOptions(year);
    refreshSaborScopeArea();
    _saState.merges = {};
    _saState.initialGroups = {};  // listName -> original primary_party label (for "A + B" merge display)
    _saState.excluded = new Set();
    _saState.forceInclude = new Set();

    // Init merge map: use group field to pre-merge coalition variants
    data.districts.forEach(d => d.lists.forEach(l => {
        const primary = l.group || l.name;
        _saState.merges[l.name] = primary;
        _saState.initialGroups[l.name] = primary;
    }));

    spinner.classList.remove('show');
    area.style.display = 'block';

    computeAndRenderSA();

    // Load district maps for both sections
    loadDistrictMap('saActualMapWrap', 'saActualMapLabel', seatsData, null);
    loadDistrictMap('saSimMapWrap', 'saSimMapLabel', data, (distRoman) => {
        scrollToDistrict(distRoman, 'saDistrictsArea');
    });
}

function computeDHondtClient(districts, merges, excluded, forceInclude) {
    const totalSeats = {};
    const districtResults = [];

    for (const dist of districts) {
        const nSeats = dist.seats;

        // Merge votes
        const mergedVotes = {};
        for (const list of dist.lists) {
            if (excluded.has(list.name)) continue;
            const group = merges[list.name] || list.name;
            mergedVotes[group] = (mergedVotes[group] || 0) + list.votes;
        }

        const totalDistVotes = Object.values(mergedVotes).reduce((s, v) => s + v, 0);

        // Minority district: seats are fixed per candidate, skip D'Hondt
        if (dist.minority) {
            const distSeats = {};
            for (const list of dist.lists) {
                if (excluded.has(list.name)) continue;
                const group = merges[list.name] || list.name;
                const seats = list.fixed_seats || 1;
                distSeats[group] = (distSeats[group] || 0) + seats;
                totalSeats[group] = (totalSeats[group] || 0) + seats;
            }
            districtResults.push({
                name: dist.name, seats: nSeats, mergedVotes, distSeats,
                totalVotes: totalDistVotes, eligibleVotes: totalDistVotes,
                originalLists: dist.lists, belowThreshold: new Set(),
                thresholdPct: 0, thresholdVotes: 0,
            });
            continue;
        }

        // 5% threshold for standard districts
        const isStandard = nSeats === 14;
        const threshold = isStandard ? totalDistVotes * 0.05 : 0;

        // Track which groups are below threshold
        const belowThreshold = new Set();
        const eligible = Object.entries(mergedVotes).filter(([name, v]) => {
            if (v >= threshold) return true;
            // Force-included parties bypass threshold
            if (forceInclude && forceInclude.has(name)) return true;
            belowThreshold.add(name);
            return false;
        });

        // D'Hondt quotients
        const quotients = [];
        for (const [name, votes] of eligible) {
            for (let d = 1; d <= nSeats; d++) {
                quotients.push({ quotient: votes / d, name });
            }
        }
        quotients.sort((a, b) => b.quotient - a.quotient);
        const winners = quotients.slice(0, nSeats);

        const distSeats = {};
        for (const w of winners) {
            distSeats[w.name] = (distSeats[w.name] || 0) + 1;
            totalSeats[w.name] = (totalSeats[w.name] || 0) + 1;
        }

        // Sum of votes only from eligible parties (used for effective %)
        const eligibleVotes = eligible.reduce((s, [_, v]) => s + v, 0);

        districtResults.push({
            name: dist.name,
            seats: nSeats,
            mergedVotes,
            distSeats,
            totalVotes: totalDistVotes,
            eligibleVotes,
            originalLists: dist.lists,
            belowThreshold,
            thresholdPct: isStandard ? 5 : 0,
            thresholdVotes: threshold,
        });
    }

    return { districts: districtResults, totalSeats };
}

function computeAndRenderSA() {
    const { rawData, merges, excluded, forceInclude, jumpers } = _saState;
    const computed = computeDHondtClient(rawData.districts, merges, excluded, forceInclude);
    _saState.computed = computed;

    // Apply jumper deltas on top of D'Hondt seats
    const adjustedSeats = { ...computed.totalSeats };
    for (const [name, delta] of Object.entries(jumpers)) {
        adjustedSeats[name] = (adjustedSeats[name] || 0) + delta;
        if (adjustedSeats[name] <= 0) delete adjustedSeats[name];
    }

    // Auto-clear jumper source if it has no seats left to give
    if (_saState.jumperSource && !adjustedSeats[_saState.jumperSource]) {
        _saState.jumperSource = null;
    }

    const totalAllocated = Object.values(adjustedSeats).reduce((s, v) => s + v, 0);

    // Build parties array sorted by seats desc
    const parties = Object.entries(adjustedSeats)
        .map(([name, seats]) => ({ name, seats }))
        .sort((a, b) => b.seats - a.seats);

    renderSAHemicycle(parties, totalAllocated);
    renderSADistricts(computed.districts);

    // Show/hide reset button
    const hasJumpers = Object.values(jumpers).some(v => v !== 0);
    const hasChanges = hasJumpers || excluded.size > 0 || forceInclude.size > 0 || Object.entries(merges).some(([k, v]) => k !== v);
    document.getElementById('saResetBtn').classList.toggle('d-none', !hasChanges);
}

function renderSAHemicycle(parties, totalAllocated) {
    const container = document.getElementById('saHemicycleContainer');
    const legendContainer = document.getElementById('saLegend');

    // Assign colors
    const partyColors = {};
    parties.forEach((p, i) => { partyColors[p.name] = hemicycleColors[i % hemicycleColors.length]; });

    // Build seat array
    const seats = [];
    parties.forEach(p => {
        for (let i = 0; i < p.seats; i++) {
            seats.push({ party: p.name, color: partyColors[p.name] });
        }
    });

    // Hemicycle layout
    const svgW = 700, svgH = 380;
    const cx = svgW / 2, cy = svgH - 30;
    const dotR = 8;
    const dotSpacing = dotR * 2.5;
    const innerR = 90;

    const rows = [];
    let totalCapacity = 0;
    let r = innerR;
    while (totalCapacity < seats.length) {
        const arc = Math.PI * r;
        const capacity = Math.floor(arc / dotSpacing);
        rows.push({ radius: r, capacity });
        totalCapacity += capacity;
        r += dotSpacing;
    }

    const nRows = rows.length;
    let seatsToPlace = seats.length;
    const rowSeats = [];
    const totalCap = rows.reduce((s, r) => s + r.capacity, 0);
    for (let i = 0; i < nRows; i++) {
        if (i === nRows - 1) { rowSeats.push(seatsToPlace); }
        else {
            const n = Math.round((rows[i].capacity / totalCap) * seats.length);
            rowSeats.push(Math.min(n, seatsToPlace));
            seatsToPlace -= rowSeats[i];
        }
    }

    const positions = [];
    for (let ri = 0; ri < nRows; ri++) {
        const count = rowSeats[ri];
        const radius = rows[ri].radius;
        for (let i = 0; i < count; i++) {
            const angle = Math.PI - (Math.PI * (i + 0.5) / count);
            positions.push({
                x: cx + radius * Math.cos(angle),
                y: cy - radius * Math.sin(angle),
            });
        }
    }

    positions.sort((a, b) => {
        const angleA = Math.atan2(cy - a.y, a.x - cx);
        const angleB = Math.atan2(cy - b.y, b.x - cx);
        return angleB - angleA;
    });

    let dots = '';
    positions.forEach((pos, i) => {
        const seat = seats[i];
        if (!seat) return;
        const shortParty = seat.party.length > 50 ? seat.party.substring(0, 47) + '...' : seat.party;
        dots += `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}" fill="${seat.color}" stroke="white" stroke-width="1.5" style="cursor:pointer;">
            <title>${shortParty} (${parties.find(p => p.name === seat.party)?.seats || 0} mandata)</title>
        </circle>`;
    });

    container.innerHTML = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:700px; display:block; margin:0 auto;">
            ${dots}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">${totalAllocated}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="12" fill="#6c757d">mandata</text>
        </svg>`;

    // Legend with drag-and-drop + jumper controls
    const { jumpersActive, jumperSource, jumpers, computed } = _saState;
    const merges = _saState.merges || {};
    const initialGroups = _saState.initialGroups || {};

    // Build merged labels: for each current leader, collect distinct original primary-party names
    const mergedLabels = {};
    for (const [listName, leader] of Object.entries(merges)) {
        const primary = initialGroups[listName] || listName;
        if (!mergedLabels[leader]) mergedLabels[leader] = [];
        if (!mergedLabels[leader].includes(primary)) mergedLabels[leader].push(primary);
    }

    // Always sort by seats desc and stack vertically so rows don't shift on change
    const legendParties = [...parties].sort((a, b) => b.seats - a.seats || a.name.localeCompare(b.name));

    const legendItems = legendParties.map(p => {
        const labelParts = mergedLabels[p.name] && mergedLabels[p.name].length > 0 ? mergedLabels[p.name] : [p.name];
        const fullLabel = labelParts.join(' + ');
        const shortName = fullLabel.length > 90 ? fullLabel.substring(0, 87) + '...' : fullLabel;
        const delta = jumpers[p.name] || 0;
        const deltaLabel = delta > 0 ? ` <span class="text-success fw-bold">+${delta}</span>` : delta < 0 ? ` <span class="text-danger fw-bold">${delta}</span>` : '';
        const isSource = jumperSource === p.name;
        const sourceBorder = isSource ? 'border-color:#dc3545 !important; background:rgba(220,53,69,0.08);' : '';

        let jumperBtns = '';
        if (jumpersActive) {
            if (!jumperSource) {
                // No source selected: show "oduzmi" button on each party that has seats
                jumperBtns = `<button class="btn btn-outline-danger btn-sm py-0 px-1 ms-1" style="font-size:0.7rem; line-height:1.3;"
                    onclick="event.stopPropagation(); selectJumperSource('${p.name.replace(/'/g, "\\'")}')">
                    <i class="bi bi-dash-lg"></i></button>`;
            } else if (isSource) {
                // This is the source: show cancel button
                jumperBtns = `<button class="btn btn-outline-secondary btn-sm py-0 px-1 ms-1" style="font-size:0.7rem; line-height:1.3;"
                    onclick="event.stopPropagation(); _saState.jumperSource=null; computeAndRenderSA();">
                    <i class="bi bi-x-lg"></i></button>`;
            } else {
                // Source is selected, this is a target: show "dodaj" button
                jumperBtns = `<button class="btn btn-outline-success btn-sm py-0 px-1 ms-1" style="font-size:0.7rem; line-height:1.3;"
                    onclick="event.stopPropagation(); transferSeat('${jumperSource.replace(/'/g, "\\'")}', '${p.name.replace(/'/g, "\\'")}')">
                    <i class="bi bi-plus-lg"></i></button>`;
            }
        }

        return `<div class="sa-legend-item d-flex align-items-start gap-1"
                     draggable="true" data-party="${p.name}"
                     title="${fullLabel}"
                     style="font-size:0.82rem; cursor:grab; padding:4px 8px; border-radius:6px; border:2px solid transparent; transition:all 0.15s; ${sourceBorder}">
                    <span style="width:14px;height:14px;border-radius:50%;background:${partyColors[p.name]};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15); margin-top:3px;"></span>
                    <span class="fw-semibold" style="flex:1; word-break:break-word;">${shortName}</span>
                    <span class="text-muted flex-shrink-0">(${p.seats})</span>${deltaLabel}${jumperBtns}
                </div>`;
    }).join('');

    let jumperHint = '';
    if (jumpersActive && !jumperSource) {
        jumperHint = `<div class="text-warning text-center mt-1" style="font-size:0.78rem;"><i class="bi bi-info-circle me-1"></i>Klikni <i class="bi bi-dash-lg"></i> na stranci od koje želiš oduzeti mandat</div>`;
    } else if (jumpersActive && jumperSource) {
        const shortSrc = jumperSource.length > 30 ? jumperSource.substring(0, 27) + '...' : jumperSource;
        jumperHint = `<div class="text-success text-center mt-1" style="font-size:0.78rem;"><i class="bi bi-info-circle me-1"></i>Klikni <i class="bi bi-plus-lg"></i> na stranci kojoj želiš dodati mandat od <strong>${shortSrc}</strong></div>`;
    }

    legendContainer.innerHTML = `
        <div class="d-flex flex-column gap-1 align-items-stretch mx-auto" style="max-width:520px;">${legendItems}</div>
        ${jumperHint}
        <div class="text-muted text-center mt-1" style="font-size:0.78rem;"><i class="bi bi-arrows-move me-1"></i>Povuci stranku na drugu u legendu ili tablici za spajanje</div>`;

    // Drag-drop on legend
    attachSALegendDragDrop(legendContainer);
}

function attachSALegendDragDrop(container) {
    const items = container.querySelectorAll('.sa-legend-item');
    items.forEach(item => {
        item.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', item.dataset.party);
            item.style.opacity = '0.5';
        });
        item.addEventListener('dragend', () => {
            item.style.opacity = '1';
            items.forEach(it => { it.style.borderColor = 'transparent'; it.style.background = ''; });
        });
        item.addEventListener('dragover', e => {
            e.preventDefault();
            item.style.borderColor = '#0d6efd';
            item.style.background = 'rgba(13,110,253,0.08)';
        });
        item.addEventListener('dragleave', () => {
            item.style.borderColor = 'transparent';
            item.style.background = '';
        });
        item.addEventListener('drop', e => {
            e.preventDefault();
            item.style.borderColor = 'transparent';
            item.style.background = '';
            const from = e.dataTransfer.getData('text/plain');
            const to = item.dataset.party;
            if (from && to && from !== to) mergeSAParties(from, to);
        });
    });
}

function mergeSAParties(from, to) {
    const { merges } = _saState;
    // Everything pointing to 'from' now points to 'to'
    for (const key in merges) {
        if (merges[key] === from) merges[key] = to;
    }
    computeAndRenderSA();
}

function unmergeSAParty(listName) {
    // Pop one list out of its merged group. Other members of the group stay merged.
    const { merges } = _saState;
    const currentLeader = merges[listName] || listName;
    if (currentLeader === listName) {
        // listName is the group's leader — promote another member so the rest remain grouped
        const members = Object.keys(merges).filter(k => merges[k] === listName && k !== listName);
        if (members.length > 0) {
            const newLeader = members[0];
            members.forEach(m => { merges[m] = newLeader; });
            merges[newLeader] = newLeader;
        }
    }
    merges[listName] = listName;
    computeAndRenderSA();
}

function excludeSAParty(name) {
    // Exclude all list names that map to this group
    const { merges, excluded } = _saState;
    for (const key in merges) {
        if (merges[key] === name) excluded.add(key);
    }
    computeAndRenderSA();
}

function includeSAParty(name) {
    const { merges, excluded } = _saState;
    for (const key in merges) {
        if (merges[key] === name) excluded.delete(key);
    }
    computeAndRenderSA();
}

function forceIncludeSAParty(name) {
    _saState.forceInclude.add(name);
    computeAndRenderSA();
}

function unforceIncludeSAParty(name) {
    _saState.forceInclude.delete(name);
    computeAndRenderSA();
}

function resetSaborAnalysis() {
    const { rawData, merges, excluded, forceInclude } = _saState;
    excluded.clear();
    forceInclude.clear();
    _saState.jumpers = {};
    _saState.jumperSource = null;
    _saState.jumpersActive = false;
    document.getElementById('saJumperBtn').classList.remove('active', 'btn-warning');
    document.getElementById('saJumperBtn').classList.add('btn-outline-warning');
    rawData.districts.forEach(d => d.lists.forEach(l => { merges[l.name] = l.group || l.name; }));
    computeAndRenderSA();
}

function toggleJumpers() {
    _saState.jumpersActive = !_saState.jumpersActive;
    _saState.jumperSource = null;
    const btn = document.getElementById('saJumperBtn');
    btn.classList.toggle('btn-outline-warning', !_saState.jumpersActive);
    btn.classList.toggle('btn-warning', _saState.jumpersActive);
    btn.classList.toggle('active', _saState.jumpersActive);
    computeAndRenderSA();
}

function selectJumperSource(partyName) {
    _saState.jumperSource = partyName;
    computeAndRenderSA();
}

function transferSeat(from, to) {
    // Check source has seats to give
    const computed = _saState.computed;
    const baseSeats = computed.totalSeats[from] || 0;
    const currentDelta = _saState.jumpers[from] || 0;
    if (baseSeats + currentDelta <= 0) return;

    _saState.jumpers[from] = (currentDelta) - 1;
    _saState.jumpers[to] = (_saState.jumpers[to] || 0) + 1;
    computeAndRenderSA();
}

async function exportSaborAnalysisPDF() {
    const { year, computed, jumpers } = _saState;
    if (!computed) return;

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = 15;
    const contentW = pageW - margin * 2;
    let curY = margin;

    // Helper: add text with page-break check
    function checkPage(needed) {
        if (curY + needed > pageH - margin) {
            pdf.addPage();
            curY = margin;
        }
    }

    // Helper: capture a DOM element as image and add to PDF
    async function addElementToPDF(el, maxHeightMM) {
        // Ensure the section is visible for capture
        const collapse = el.closest('.collapse');
        const wasHidden = collapse && !collapse.classList.contains('show');
        if (wasHidden) collapse.classList.add('show');

        const canvas = await html2canvas(el, {
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff',
            logging: false,
        });

        if (wasHidden) collapse.classList.remove('show');

        const imgData = canvas.toDataURL('image/png');
        const ratio = canvas.width / canvas.height;
        let imgW = contentW;
        let imgH = imgW / ratio;

        if (maxHeightMM && imgH > maxHeightMM) {
            imgH = maxHeightMM;
            imgW = imgH * ratio;
        }

        checkPage(imgH);
        pdf.addImage(imgData, 'PNG', margin, curY, imgW, imgH);
        curY += imgH + 5;
    }

    // Title
    pdf.setFontSize(18);
    pdf.setFont(undefined, 'bold');
    pdf.text(`Analiza parlamentarnih izbora ${year}.`, margin, curY);
    curY += 10;

    // --- Section 1: Actual results hemicycle + legend ---
    const actualCard = document.getElementById('saActualResultsCard');
    if (actualCard && actualCard.style.display !== 'none') {
        pdf.setFontSize(14);
        pdf.setFont(undefined, 'bold');
        pdf.text('Konačni rezultati - raspodjela mandata (D\'Hondt)', margin, curY);
        curY += 7;

        const actualHemi = document.getElementById('saActualHemicycle');
        if (actualHemi) await addElementToPDF(actualHemi, 120);

        const actualLegend = document.getElementById('saActualLegend');
        if (actualLegend) await addElementToPDF(actualLegend, 60);
    }

    // --- Section 2: Simulation hemicycle + legend ---
    checkPage(20);
    pdf.setFontSize(14);
    pdf.setFont(undefined, 'bold');
    pdf.text('Simulacija - raspodjela mandata', margin, curY);
    curY += 7;

    const simHemi = document.getElementById('saHemicycleContainer');
    if (simHemi) await addElementToPDF(simHemi, 120);

    const simLegend = document.getElementById('saLegend');
    if (simLegend) await addElementToPDF(simLegend, 60);

    // --- Section 3: Summary table ---
    checkPage(30);
    pdf.setFontSize(14);
    pdf.setFont(undefined, 'bold');
    pdf.text('Ukupni rezultati', margin, curY);
    curY += 7;

    // Build adjusted seats (with jumpers applied)
    const adjustedSeats = { ...computed.totalSeats };
    for (const [name, delta] of Object.entries(jumpers)) {
        adjustedSeats[name] = (adjustedSeats[name] || 0) + delta;
        if (adjustedSeats[name] <= 0) delete adjustedSeats[name];
    }
    const totalParties = Object.entries(adjustedSeats).sort((a, b) => b[1] - a[1]);
    const totalAllocated = totalParties.reduce((s, [_, v]) => s + v, 0);

    pdf.setFontSize(9);
    pdf.setFont(undefined, 'bold');
    const col1 = margin, col2 = margin + 120, col3 = margin + 145;
    pdf.text('Stranka / Koalicija', col1, curY);
    pdf.text('Mandati', col2, curY);
    pdf.text('% mandata', col3, curY);
    curY += 1;
    pdf.setDrawColor(180);
    pdf.line(margin, curY, pageW - margin, curY);
    curY += 4;

    pdf.setFont(undefined, 'normal');
    totalParties.forEach(([name, seats]) => {
        checkPage(6);
        const displayName = name.length > 70 ? name.substring(0, 67) + '...' : name;
        pdf.text(displayName, col1, curY);
        pdf.text(String(seats), col2, curY);
        pdf.text((seats / totalAllocated * 100).toFixed(1) + '%', col3, curY);
        curY += 5;
    });

    checkPage(8);
    pdf.setFont(undefined, 'bold');
    curY += 2;
    pdf.line(margin, curY, pageW - margin, curY);
    curY += 5;
    pdf.text('Ukupno', col1, curY);
    pdf.text(String(totalAllocated), col2, curY);
    curY += 8;

    // --- Section 4: Per-district results ---
    computed.districts.forEach(dist => {
        checkPage(40);
        pdf.setFontSize(11);
        pdf.setFont(undefined, 'bold');
        pdf.text(`${dist.name} (${dist.seats} mandata)`, margin, curY);
        curY += 6;

        pdf.setFontSize(8);
        pdf.setFont(undefined, 'bold');
        const dc1 = margin, dc2 = margin + 100, dc3 = margin + 118, dc4 = margin + 136, dc5 = margin + 155;
        pdf.text('Lista', dc1, curY);
        pdf.text('Glasovi', dc2, curY);
        pdf.text('% ukupno', dc3, curY);
        pdf.text('Efektivni %', dc4, curY);
        pdf.text('Mandati', dc5, curY);
        curY += 1;
        pdf.setDrawColor(200);
        pdf.line(margin, curY, pageW - margin, curY);
        curY += 4;

        pdf.setFont(undefined, 'normal');
        const sorted = Object.entries(dist.mergedVotes).sort((a, b) => b[1] - a[1]);
        sorted.forEach(([name, votes]) => {
            checkPage(6);
            const displayName = name.length > 55 ? name.substring(0, 52) + '...' : name;
            const rawPct = dist.totalVotes > 0 ? (votes / dist.totalVotes * 100).toFixed(1) : '0.0';
            const effPct = dist.eligibleVotes > 0 ? (votes / dist.eligibleVotes * 100).toFixed(1) : '0.0';
            const seats = dist.distSeats[name] || 0;
            const isBelowThreshold = dist.belowThreshold.has(name);

            pdf.text(displayName, dc1, curY);
            pdf.text(String(votes), dc2, curY);
            pdf.text(rawPct + '%', dc3, curY);
            pdf.text(isBelowThreshold ? '-' : effPct + '%', dc4, curY);
            pdf.text(String(seats), dc5, curY);
            curY += 4.5;
        });
        curY += 5;
    });

    pdf.save(`Analiza_Sabor_${year}.pdf`);
}

function exportSaborAnalysisXLSX() {
    const { computed, year, merges, excluded, forceInclude } = _saState;
    if (!computed) return;

    const wb = XLSX.utils.book_new();

    // --- Sheet 1: Ukupni rezultati (summary) ---
    const summaryRows = [['Analiza parlamentarnih izbora ' + year], []];
    const totalParties = Object.entries(computed.totalSeats).sort((a, b) => b[1] - a[1]);
    const totalAllocated = totalParties.reduce((s, [_, v]) => s + v, 0);
    summaryRows.push(['Stranka / Koalicija', 'Mandati', '% mandata']);
    totalParties.forEach(([name, seats]) => {
        summaryRows.push([name, seats, (seats / totalAllocated * 100).toFixed(1) + '%']);
    });
    summaryRows.push([], ['Ukupno', totalAllocated]);
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryRows);
    wsSummary['!cols'] = [{ wch: 60 }, { wch: 10 }, { wch: 12 }];
    XLSX.utils.book_append_sheet(wb, wsSummary, 'Ukupno');

    // --- One sheet per district ---
    computed.districts.forEach((dist) => {
        const groups = {};
        dist.originalLists.forEach(l => {
            const group = merges[l.name] || l.name;
            if (!groups[group]) groups[group] = { names: [], votes: 0, excluded: excluded.has(l.name) };
            groups[group].names.push(l.name);
            groups[group].votes += l.votes;
            if (!excluded.has(l.name)) groups[group].excluded = false;
        });

        const sorted = Object.entries(groups).sort((a, b) => b[1].votes - a[1].votes);
        const sheetRows = [[dist.name + ' (' + dist.seats + ' mandata)'], []];
        sheetRows.push(['Lista / Koalicija', 'Glasovi', '% ukupno', 'Efektivni %', 'Mandati', 'Status']);

        sorted.forEach(([groupName, g]) => {
            const rawPct = dist.totalVotes > 0 ? (g.votes / dist.totalVotes * 100).toFixed(1) : '0.0';
            const effPct = dist.eligibleVotes > 0 ? (g.votes / dist.eligibleVotes * 100).toFixed(1) : '0.0';
            const seats = dist.distSeats[groupName] || 0;
            const isBelowThreshold = dist.belowThreshold.has(groupName);
            const isForced = forceInclude.has(groupName);
            const isExcl = g.excluded;

            let status = '';
            if (isExcl) status = 'Isključeno';
            else if (isBelowThreshold && !isForced) status = 'Ispod praga 5%';
            else if (isForced) status = 'Uključeno (zaobiđen prag)';
            else status = 'Iznad praga';

            const displayName = g.names.length > 1 ? g.names.join('\n') : g.names[0];
            sheetRows.push([displayName, g.votes, rawPct + '%', (isExcl || (isBelowThreshold && !isForced)) ? '-' : effPct + '%', seats, status]);
        });

        const wastedVotes = dist.totalVotes - dist.eligibleVotes;
        const wastedPct = dist.totalVotes > 0 ? (wastedVotes / dist.totalVotes * 100).toFixed(1) : '0.0';
        sheetRows.push([]);
        sheetRows.push(['Ukupno glasova', dist.totalVotes]);
        sheetRows.push(['Efektivni glasovi (u raspodjeli)', dist.eligibleVotes]);
        sheetRows.push(['Propali glasovi (ispod praga)', wastedVotes, wastedPct + '%']);
        sheetRows.push(['Prag (5%)', Math.round(dist.thresholdVotes)]);

        const ws = XLSX.utils.aoa_to_sheet(sheetRows);
        ws['!cols'] = [{ wch: 60 }, { wch: 12 }, { wch: 12 }, { wch: 14 }, { wch: 10 }, { wch: 25 }];

        // Trim sheet name to 31 chars (Excel limit)
        let sheetName = dist.name.length > 31 ? dist.name.substring(0, 31) : dist.name;
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
    });

    XLSX.writeFile(wb, `Analiza_Sabor_${year}.xlsx`);
}

function renderSADistricts(districtResults) {
    const container = document.getElementById('saDistrictsArea');
    const { merges, excluded, forceInclude } = _saState;

    const cards = districtResults.map((dist, di) => {
        // Build rows: show merged groups
        const groups = {};
        dist.originalLists.forEach(l => {
            const isExcl = excluded.has(l.name);
            const group = merges[l.name] || l.name;
            if (!groups[group]) groups[group] = { names: [], votes: 0, excluded: true };
            groups[group].names.push(l.name);
            groups[group].votes += l.votes;
            if (!isExcl) groups[group].excluded = false;
        });

        const sortedGroups = Object.entries(groups).sort((a, b) => b[1].votes - a[1].votes);

        const rows = sortedGroups.map(([groupName, g]) => {
            const rawPct = dist.totalVotes > 0 ? (g.votes / dist.totalVotes * 100) : 0;
            const effPct = dist.eligibleVotes > 0 ? (g.votes / dist.eligibleVotes * 100) : 0;
            const seats = dist.distSeats[groupName] || 0;
            const isBelowThreshold = dist.belowThreshold.has(groupName);
            const isForced = forceInclude.has(groupName);
            const isExcl = g.excluded;

            // Show each merged list on its own line
            let nameCell;
            if (g.names.length === 1) {
                nameCell = `<div style="white-space:normal; word-break:break-word;">${g.names[0]}</div>`;
            } else {
                const lines = g.names.map(n => {
                    const esc = n.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                    return `<div style="white-space:normal; word-break:break-word; padding:4px 0; display:flex; align-items:flex-start; gap:6px;">
                        <button class="btn btn-outline-secondary btn-sm p-0 px-1 flex-shrink-0"
                                style="font-size:0.7rem; line-height:1; margin-top:2px;"
                                onmousedown="event.stopPropagation();"
                                onclick="event.stopPropagation(); unmergeSAParty('${esc}')"
                                title="Odspoji ovu listu iz koalicije">
                            <i class="bi bi-x-lg"></i>
                        </button>
                        <span style="flex:1;">${n}</span>
                    </div>`;
                }).join('');
                nameCell = `<div style="border-left:4px solid #0d6efd; padding-left:10px; margin:4px 0; background:rgba(13,110,253,0.04); border-radius:0 6px 6px 0;">
                    ${lines}
                    <div class="pb-1"><span class="badge bg-info text-dark" style="font-size:0.65rem;">spojeno ${g.names.length}</span></div>
                </div>`;
            }

            // Determine row style and action button
            let rowClass = 'sa-dist-row';
            let rowStyle = 'cursor:grab;';
            let seatDisplay;
            let actionBtn;
            const esc = groupName.replace(/'/g, "\\'");

            if (isExcl) {
                // Manually excluded by user
                rowClass += ' text-decoration-line-through text-muted';
                rowStyle += ' opacity:0.5;';
                seatDisplay = '-';
                actionBtn = `<button class="btn btn-outline-success btn-sm p-0 px-1" onclick="includeSAParty('${esc}')" title="Uključi"><i class="bi bi-plus-circle"></i></button>`;
            } else if (isBelowThreshold && !isForced) {
                // Below 5% threshold — crossed out by default
                rowClass += ' text-decoration-line-through';
                rowStyle += ' opacity:0.6; background:rgba(220,53,69,0.04);';
                seatDisplay = `<span class="text-muted" title="Ispod praga od 5%">⊘</span>`;
                actionBtn = `<button class="btn btn-outline-success btn-sm p-0 px-1" onclick="forceIncludeSAParty('${esc}')" title="Uključi u izračun (zaobiđi prag)"><i class="bi bi-plus-circle"></i></button>`;
                // Add threshold badge to name cell
                nameCell += `<span class="badge bg-danger bg-opacity-75 ms-1" style="font-size:0.6rem; vertical-align:middle;">ispod 5%</span>`;
            } else if (isForced) {
                // Force-included (was below threshold, user enabled it)
                rowStyle += ' background:rgba(25,135,84,0.06);';
                seatDisplay = seats > 0 ? seats : '0';
                actionBtn = `<button class="btn btn-outline-warning btn-sm p-0 px-1" onclick="unforceIncludeSAParty('${esc}')" title="Vrati prag od 5%"><i class="bi bi-dash-circle"></i></button>`;
                nameCell += `<span class="badge bg-success bg-opacity-75 ms-1" style="font-size:0.6rem; vertical-align:middle;">uključeno</span>`;
            } else {
                // Normal — above threshold
                seatDisplay = seats > 0 ? seats : '0';
                actionBtn = `<button class="btn btn-outline-danger btn-sm p-0 px-1" onclick="excludeSAParty('${esc}')" title="Isključi"><i class="bi bi-x-circle"></i></button>`;
            }

            // For eligible parties: show effective %, for below-threshold: show raw %
            const isEligible = !isExcl && (!isBelowThreshold || isForced);
            const pctDisplay = isEligible
                ? `<strong>${formatPct(effPct)}</strong><br><small class="text-muted" style="font-size:0.7rem;">${formatPct(rawPct)} ukupno</small>`
                : `<span class="text-muted">${formatPct(rawPct)}</span>`;

            return `<tr draggable="true" data-group="${groupName}" data-district="${di}"
                        class="${rowClass}" style="${rowStyle}">
                <td title="${g.names.join(' + ')}" style="max-width:450px;">${nameCell}</td>
                <td class="text-end align-middle">${formatNumber(g.votes)}</td>
                <td class="text-end align-middle">${pctDisplay}</td>
                <td class="text-center fw-bold align-middle">${seatDisplay}</td>
                <td class="text-center align-middle" style="width:40px;">${actionBtn}</td>
            </tr>`;
        }).join('');

        const allocatedSeats = Object.values(dist.distSeats).reduce((s, v) => s + v, 0);
        const belowCount = dist.belowThreshold.size;
        const wastedVotes = dist.totalVotes - dist.eligibleVotes;
        const wastedPct = dist.totalVotes > 0 ? (wastedVotes / dist.totalVotes * 100) : 0;
        const thresholdInfo = dist.thresholdPct > 0
            ? `<span class="badge bg-warning text-dark ms-1" title="Prag: ${formatNumber(Math.round(dist.thresholdVotes))} glasova">${belowCount} ispod ${dist.thresholdPct}%</span>
               <span class="badge bg-secondary ms-1" title="Glasovi koji ne sudjeluju u raspodjeli">${formatPct(wastedPct)} propalo (${formatNumber(wastedVotes)})</span>`
            : '';

        // Extract district number from name (e.g., "I. IZBORNA JEDINICA" -> 1)
        const romanMatch = dist.name.match(/^([IVXL]+)\./);
        const distNum = romanMatch ? {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10,'XI':11,'XII':12}[romanMatch[1]] || di+1 : di+1;

        return `
        <div class="card result-card mb-3" data-district-num="${distNum}">
            <div class="card-header d-flex justify-content-between align-items-center" style="cursor:pointer;" data-bs-toggle="collapse" data-bs-target="#saDist${di}">
                <div>
                    <strong>${dist.name}</strong>
                    <span class="text-muted ms-2">(${dist.seats} mandata)</span>
                    ${thresholdInfo}
                </div>
                <div>
                    <span class="badge bg-primary">${allocatedSeats} dodijeljeno</span>
                    <i class="bi bi-chevron-down ms-2"></i>
                </div>
            </div>
            <div id="saDist${di}" class="collapse${di === 0 ? ' show' : ''}">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0" style="font-size:0.88rem;">
                            <thead><tr>
                                <th>Lista / Koalicija</th>
                                <th class="text-end">Glasovi</th>
                                <th class="text-end" title="Efektivni % (preraspodjela) / ukupni %">Efektivni %</th>
                                <th class="text-center">Mandati</th>
                                <th></th>
                            </tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');

    container.innerHTML = cards;

    // Attach drag-drop to table rows
    attachSARowDragDrop();
}

function attachSARowDragDrop() {
    const rows = document.querySelectorAll('.sa-dist-row');
    rows.forEach(row => {
        row.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', row.dataset.group);
            row.style.opacity = '0.5';
        });
        row.addEventListener('dragend', () => {
            row.style.opacity = '1';
            rows.forEach(r => { r.style.background = ''; });
        });
        row.addEventListener('dragover', e => {
            e.preventDefault();
            row.style.background = 'rgba(13,110,253,0.08)';
        });
        row.addEventListener('dragleave', () => { row.style.background = ''; });
        row.addEventListener('drop', e => {
            e.preventDefault();
            row.style.background = '';
            const from = e.dataTransfer.getData('text/plain');
            const to = row.dataset.group;
            if (from && to && from !== to) mergeSAParties(from, to);
        });
    });
}

// (initSaborAnalysis is invoked from activateModule alongside the other
// modules' inits. It used to hang off a separate sidebar-link click handler,
// which meant loading /rezultati-koalicije-sabor directly — or arriving via
// back/forward — showed the module with an empty year picker.)
