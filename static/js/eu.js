// Europski parlament: scope widgets, seats and candidates.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// === EU scope: same widgets as predsjednicki, but on the EU page (eus* IDs)
const _eus = { mapPaths: [], compareScopes: [] };

async function initEuScope() {
    const selC = document.getElementById('eusSelCounty');
    const selM = document.getElementById('eusSelMuni');
    const selS = document.getElementById('eusSelStation');
    if (!selC || selC._wired) return;
    selC._wired = true;

    try {
        const res = await fetch('/api/counties');
        if (res.ok) {
            (await res.json()).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id; opt.textContent = c.name;
                selC.appendChild(opt);
            });
        }
    } catch (e) { console.warn('counties load failed', e); }

    loadEusCroatiaMap().catch(e => console.warn('eus map load failed', e));

    selC.addEventListener('change', async () => {
        selM.innerHTML = '<option value="">Sva mjesta u županiji</option>';
        selS.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
        selM.disabled = true; selS.disabled = true;
        const txt = selC.value ? selC.options[selC.selectedIndex].textContent : '';
        eusHighlightMapCounty(txt || null);
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
        eusUpdateAddBtn();
        refetchEuWithScope();
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
        eusUpdateAddBtn();
        refetchEuWithScope();
    });
    selS.addEventListener('change', () => {
        eusUpdateAddBtn();
        refetchEuWithScope();
    });

    document.getElementById('eusAddCompareBtn').addEventListener('click', onEusAddCompare);
    document.getElementById('eusClearScopeBtn').addEventListener('click', onEusClearScope);
}

async function loadEusCroatiaMap() {
    const wrap = document.getElementById('eusCroatiaMapWrap');
    const res = await fetch('/static/croatia_map.svg');
    const svgText = await res.text();
    wrap.innerHTML = svgText;
    const embeddedStyle = wrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    const svgTitle = wrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();
    _eus.mapPaths = wrap.querySelectorAll('path[data-county]');
    const label = document.getElementById('eusMapCountyLabel');
    _eus.mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const sel = document.getElementById('eusSelCounty');
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

function eusHighlightMapCounty(name) {
    _eus.mapPaths.forEach(p => p.classList.remove('selected'));
    const label = document.getElementById('eusMapCountyLabel');
    if (name) {
        const target = document.getElementById('eusCroatiaMapWrap')
            .querySelector(`path[data-county="${name}"]`);
        if (target) target.classList.add('selected');
        label.textContent = name;
    } else if (label) {
        label.textContent = '';
    }
}

function eusUpdateAddBtn() {
    const btn = document.getElementById('eusAddCompareBtn');
    if (!btn) return;
    const multiYear = (_resultsState['eu']?.years?.length || 0) > 1;
    btn.disabled = !document.getElementById('eusSelCounty').value || multiYear;
}

function eusCurrentScopeKey() {
    const sId = document.getElementById('eusSelStation').value;
    const mId = document.getElementById('eusSelMuni').value;
    const cId = document.getElementById('eusSelCounty').value;
    const sel = document.getElementById('eusSelStation');
    const selM = document.getElementById('eusSelMuni');
    const selC = document.getElementById('eusSelCounty');
    if (sId) return { type: 'station', id: parseInt(sId, 10), label: sel.options[sel.selectedIndex].textContent };
    if (mId) return { type: 'municipality', id: parseInt(mId, 10), label: selM.options[selM.selectedIndex].textContent };
    if (cId) return { type: 'county', id: parseInt(cId, 10), label: selC.options[selC.selectedIndex].textContent };
    return null;
}

function onEusAddCompare() {
    const sc = eusCurrentScopeKey();
    if (!sc) return;
    if (_eus.compareScopes.find(x => x.type === sc.type && x.id === sc.id)) return;
    if (_eus.compareScopes.length >= 3) return; // side-by-side cap
    _eus.compareScopes.push(sc);
    renderEusCompareChips();
    refetchEuWithScope();
}

function onEusRemoveCompare(type, id) {
    _eus.compareScopes = _eus.compareScopes.filter(x => !(x.type === type && x.id === id));
    renderEusCompareChips();
    refetchEuWithScope();
}

function onEusClearScope() {
    document.getElementById('eusSelCounty').value = '';
    document.getElementById('eusSelMuni').innerHTML = '<option value="">Sva mjesta u županiji</option>';
    document.getElementById('eusSelStation').innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    document.getElementById('eusSelMuni').disabled = true;
    document.getElementById('eusSelStation').disabled = true;
    _eus.compareScopes = [];
    eusHighlightMapCounty(null);
    eusUpdateAddBtn();
    renderEusCompareChips();
    refetchEuWithScope();
}

function renderEusCompareChips() {
    const wrap = document.getElementById('eusCompareChips');
    if (!wrap) return;
    if (_eus.compareScopes.length === 0) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = _eus.compareScopes.map(s => {
        const typeLabel = s.type === 'station' ? 'BM' : s.type === 'municipality' ? 'Gr/Op' : 'Žup';
        return `<span class="izl-compare-chip">
            <span class="badge bg-secondary me-1" style="font-size:0.6rem;">${typeLabel}</span>
            ${escapeHtml(s.label)}
            <button type="button" class="chip-x" data-type="${s.type}" data-id="${s.id}" aria-label="Ukloni">×</button>
        </span>`;
    }).join('');
    wrap.querySelectorAll('.chip-x').forEach(btn => {
        btn.addEventListener('click', () => onEusRemoveCompare(btn.dataset.type, parseInt(btn.dataset.id, 10)));
    });
}

function refetchEuWithScope() {
    const st = _resultsState['eu'];
    if (!st || !st.year) return;
    loadNationalResults('eu', st.year);
}

async function loadNationalResults(category, year) {
    const panel = document.getElementById(`module-results-${category}`);
    if (!panel) return;
    const spinner = panel.querySelector('.results-spinner');
    const resultsArea = panel.querySelector('.results-area');

    resultsArea.style.display = 'none';
    spinner.classList.add('show');

    // Helper: build URLSearchParams from a scope chip
    const scopeToParams = sc => {
        const p = new URLSearchParams();
        if (!sc) return p;
        if (sc.type === 'station') p.set('station_id', sc.id);
        else if (sc.type === 'municipality') p.set('municipality_id', sc.id);
        else if (sc.type === 'county') p.set('county_id', sc.id);
        return p;
    };

    // Helper: build URLSearchParams from current dropdown scope (no chip).
    const currentScopeParams = () => {
        const params = new URLSearchParams();
        const idPrefix = category === 'predsjednicki' ? 'pred' : 'eus';
        const sId = document.getElementById(`${idPrefix}SelStation`)?.value;
        const mId = document.getElementById(`${idPrefix}SelMuni`)?.value;
        const cId = document.getElementById(`${idPrefix}SelCounty`)?.value;
        if (sId) params.set('station_id', sId);
        else if (mId) params.set('municipality_id', mId);
        else if (cId) params.set('county_id', cId);
        return params;
    };

    // Compare mode: one fetch per chip, render N cards stacked.
    const compareScopes = category === 'predsjednicki' ? _pred.compareScopes
                       : category === 'eu' ? _eus.compareScopes
                       : [];
    if (compareScopes.length > 0) {
        const fetchScope = async sc => {
            const p = scopeToParams(sc);
            const r = await fetch(`/api/national/results/${category}/${year}?${p.toString()}`);
            const data = r.ok ? await r.json() : { error: `HTTP ${r.status}`, scope_label: sc.label };
            // Stash the scope-params querystring so renderEuSeats can forward it
            data._scopeQs = p.toString();
            return data;
        };
        const results = await Promise.all(compareScopes.map(fetchScope));
        spinner.classList.remove('show');
        resultsArea.style.display = 'block';
        results.forEach((d, i) => { d._panel = panel; d._compareIndex = i; });
        renderNationalResultsMulti(results);
        return;
    }

    // Multi-year mode: 2+ years selected, no scope chips. Fetch each year at
    // the current dropdown scope and render side-by-side.
    const st = _resultsState[category] || {};
    const years = (st.years && st.years.length > 1) ? st.years : null;
    if (years && (category === 'predsjednicki' || category === 'eu')) {
        const baseParams = currentScopeParams();
        const scopeLabelSuffix = baseParams.toString() ? (function () {
            // Best-effort label for the current dropdown scope.
            const idPrefix = category === 'predsjednicki' ? 'pred' : 'eus';
            const selS = document.getElementById(`${idPrefix}SelStation`);
            const selM = document.getElementById(`${idPrefix}SelMuni`);
            const selC = document.getElementById(`${idPrefix}SelCounty`);
            if (selS?.value) return selS.options[selS.selectedIndex].textContent;
            if (selM?.value) return selM.options[selM.selectedIndex].textContent;
            if (selC?.value) return selC.options[selC.selectedIndex].textContent;
            return '';
        })() : '';
        const fetchYear = async y => {
            const r = await fetch(`/api/national/results/${category}/${y}?${baseParams.toString()}`);
            const data = r.ok ? await r.json() : { error: `HTTP ${r.status}` };
            data.scope_label = scopeLabelSuffix ? `${y}. · ${scopeLabelSuffix}` : `${y}.`;
            data._scopeQs = baseParams.toString();
            return data;
        };
        const results = await Promise.all(years.map(fetchYear));
        spinner.classList.remove('show');
        resultsArea.style.display = 'block';
        results.forEach((d, i) => { d._panel = panel; d._compareIndex = i; });
        renderNationalResultsMulti(results);
        return;
    }

    // Single-scope path (default): use the current dropdowns as the scope.
    const params = new URLSearchParams();
    if (category === 'predsjednicki') {
        const sId = document.getElementById('predSelStation')?.value;
        const mId = document.getElementById('predSelMuni')?.value;
        const cId = document.getElementById('predSelCounty')?.value;
        if (sId) params.set('station_id', sId);
        else if (mId) params.set('municipality_id', mId);
        else if (cId) params.set('county_id', cId);
    } else if (category === 'eu') {
        const sId = document.getElementById('eusSelStation')?.value;
        const mId = document.getElementById('eusSelMuni')?.value;
        const cId = document.getElementById('eusSelCounty')?.value;
        if (sId) params.set('station_id', sId);
        else if (mId) params.set('municipality_id', mId);
        else if (cId) params.set('county_id', cId);
    }
    const qs = params.toString() ? `?${params.toString()}` : '';

    const res = await fetch(`/api/national/results/${category}/${year}${qs}`);
    const data = await res.json();
    data._panel = panel;
    data._scopeQs = params.toString();

    spinner.classList.remove('show');
    resultsArea.style.display = 'block';

    _nationalData = data;
    renderNationalResults(data);
}

function renderNationalResultsMulti(results) {
    // Render N scopes side-by-side (max 3) — same .compare-grid layout used by
    // the "Usporedi" feature in Prema lokaciji. Each column gets its own
    // results-area wrapper and a compare-index prefix so chart-ids stay unique.
    const panel = results[0] && results[0]._panel;
    const container = panel ? panel.querySelector('.results-area') : null;
    if (!container) return;
    container.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'compare-grid scope-compare-grid';
    container.appendChild(grid);

    results.forEach((d, i) => {
        const col = document.createElement('div');
        col.className = 'compare-card';
        const headerHtml = d.error
            ? `<div class="compare-card-header"><h6>${escapeHtml(d.scope_label || '')}</h6></div>
               <div class="compare-card-body"><div class="alert alert-warning mb-0">${escapeHtml(d.error)}</div></div>`
            : `<div class="compare-card-header"><h6><i class="bi bi-geo-alt me-1"></i>${escapeHtml(d.scope_label || '')}</h6></div>`;
        col.innerHTML = headerHtml;
        grid.appendChild(col);
        if (d.error) return;
        const body = document.createElement('div');
        body.className = 'compare-card-body';
        const wrap = document.createElement('div');
        wrap.className = 'results-area';
        body.appendChild(wrap);
        col.appendChild(body);
        const fakePanel = { querySelector: sel => sel === '.results-area' ? wrap : panel.querySelector(sel) };
        const dataCopy = Object.assign({}, d, { _panel: fakePanel, _compareIdxPrefix: `cmp${i}_` });
        renderNationalResults(dataCopy);
    });
}

function renderNationalResults(data) {
    const panel = data._panel || document.getElementById(`module-results-${data.category}`);
    const container = panel ? panel.querySelector('.results-area') : null;
    if (!container) return;
    const elections = data.elections || [];

    if (elections.length === 0) {
        container.innerHTML = data.error
            ? `<div class="alert alert-info small py-2"><i class="bi bi-info-circle me-1"></i>${escapeHtml(data.error)}</div>`
            : '<p class="text-muted p-3">Nema podataka za odabrane izbore.</p>';
        return;
    }

    const idPrefix = data._compareIdxPrefix || '';
    // For EU we only show the hemicycle + Zastupnici list at the national
    // scope. When the user narrows to a county/muni/station, the seat-
    // allocation visualisation isn't meaningful — fall back to the same
    // bar-chart layout that other categories use.
    const scope = data.scope || 'national';
    const isEuNational = data.category === 'eu' && scope === 'national';
    const useBarChart = data.category !== 'eu' || !isEuNational;

    const electionCards = elections.map((el, idx) => {
        const turnoutPct = el.registered_voters > 0
            ? (el.ballots_cast / el.registered_voters) * 100 : 0;
        const chartId = `${idPrefix}nat_${idx}`;

        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                <div>
                    <span class="badge ${electionBadgeColor(el.election_type)} badge-election me-1">${el.election_type}</span>
                    <span class="badge bg-dark badge-election">${el.date ? new Date(el.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' }) : el.year}</span>
                    ${el.round > 1 ? '<span class="badge bg-warning text-dark badge-election">' + el.round + '. krug</span>' : ''}
                </div>
                <div class="text-end">
                    <span class="vote-number">${formatPct(turnoutPct)}</span>
                    <br><small class="text-muted">izlaznost</small>
                </div>
            </div>
            <div class="d-flex gap-3 flex-wrap mb-2">
                <small class="text-muted"><i class="bi bi-people me-1"></i>Upisani: <strong>${formatNumber(el.registered_voters)}</strong></small>
                <small class="text-muted"><i class="bi bi-check2-circle me-1"></i>Glasali: <strong>${formatNumber(el.ballots_cast)}</strong></small>
                <small class="text-muted"><i class="bi bi-check-lg me-1"></i>Važeći: <strong>${formatNumber(el.valid_ballots)}</strong></small>
            </div>
            ${isEuNational ? `<div class="eu-seats-slot mb-3" id="euSeatsSlot_${data.category}_${chartId}" data-year="${el.year}"></div>` : ''}
            ${useBarChart ? `
            <div class="bar-chart-area" id="barChart_${chartId}" data-election-idx="${chartId}"></div>
            <div class="d-flex justify-content-between align-items-center mt-1">
                <div class="bar-drag-hint"><i class="bi bi-arrows-move me-1"></i>Povuci stupac na drugi za spajanje rezultata</div>
                <button class="btn btn-outline-secondary bar-reset-btn" onclick="resetBarChart('${chartId}')" style="display:none;" id="resetBtn_${chartId}">
                    <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
                </button>
            </div>` : ''}
        </div>`;
    }).join('');

    container.innerHTML = electionCards;

    // Build the bar chart whenever it's rendered. Use idPrefix so compare-mode
    // keys are unique per scope card.
    if (useBarChart) {
        elections.forEach((el, idx) => {
            const chartId = `${idPrefix}nat_${idx}`;
            // For EU non-national scope, use top_lists (party vote totals) since
            // there are no per-candidate votes recorded outside the national level.
            // For other categories, prefer top_candidates if present.
            const hasCandidates = el.top_candidates && el.top_candidates.length > 0 && data.category !== 'eu';
            const items = hasCandidates ? el.top_candidates : el.top_lists;
            if (!items || items.length === 0) return;

            const originalItems = items.map((it, i) => ({
                name: it.name,
                votes: it.votes,
                color: barColors[i % barColors.length],
                origNames: [it.name],
            }));

            window._electionBarData[chartId] = {
                original: JSON.parse(JSON.stringify(originalItems)),
                current: originalItems,
                validBallots: el.valid_ballots,
                kind: hasCandidates ? 'person' : 'list',
            };

            buildBarChart(chartId);
        });
    }

    // EU national only: fetch + render D'Hondt seat allocation. Skipped when
    // a county/muni/station scope is active (bar chart above is shown instead).
    if (isEuNational) {
        const scopeQs = data._scopeQs ? `?${data._scopeQs}` : '';
        elections.forEach((el, idx) => {
            const cid = `${idPrefix}nat_${idx}`;
            const slot = panel.querySelector(`#euSeatsSlot_eu_${cid}`);
            if (!slot) return;
            fetch(`/api/national/eu-seats/${el.year}${scopeQs}`)
                .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
                .then(seatsData => renderEuSeats(slot, seatsData))
                .catch(err => { console.warn(`EU seats fetch failed for ${el.year}:`, err); });
        });
    }
}

function renderEuSeats(slot, data) {
    if (!data || !data.parties || data.parties.length === 0) return;
    // Initialize per-slot merge state. Each party initially "leads itself";
    // dragging A onto B remaps A's leader to B and triggers a recompute.
    const state = {
        rawParties: data.parties,
        rawCandidates: data.candidates || [],
        totalSeats: data.total_seats,
        totalVotes: data.total_votes,
        thresholdVotes: data.threshold_votes,
        thresholdPct: data.threshold_pct,
        merges: {},
        partyColors: {},
    };
    data.parties.forEach((p, i) => {
        state.merges[p.name] = p.name;
        state.partyColors[p.name] = hemicycleColors[i % hemicycleColors.length];
    });
    slot._euState = state;
    renderEuView(slot);
}

function computeEuView(state) {
    // Group raw parties by their current merge leader
    const grouped = {};
    state.rawParties.forEach(p => {
        const leader = state.merges[p.name] || p.name;
        if (!grouped[leader]) grouped[leader] = { name: leader, votes: 0, members: [] };
        grouped[leader].votes += p.votes;
        grouped[leader].members.push(p.name);
    });

    // 5 % threshold + D'Hondt over the (possibly merged) groups
    const eligible = Object.values(grouped).filter(g => g.votes >= state.thresholdVotes);
    const quotients = [];
    eligible.forEach(g => {
        for (let d = 1; d <= state.totalSeats; d++) quotients.push({ q: g.votes / d, leader: g.name });
    });
    quotients.sort((a, b) => b.q - a.q);
    const seatsByLeader = {};
    quotients.slice(0, state.totalSeats).forEach(w => {
        seatsByLeader[w.leader] = (seatsByLeader[w.leader] || 0) + 1;
    });

    const parties = Object.values(grouped).map(g => ({
        name: g.name,
        members: g.members,
        votes: g.votes,
        votes_pct: state.totalVotes ? (g.votes / state.totalVotes * 100) : 0,
        seats: seatsByLeader[g.name] || 0,
        eligible: g.votes >= state.thresholdVotes,
    })).sort((a, b) => b.seats - a.seats || b.votes - a.votes);

    // Re-mark winners: pool candidates by current leader, sort by preferential
    // votes desc, top N within each leader's pool become winners.
    const candsByLeader = {};
    state.rawCandidates.forEach(c => {
        const leader = state.merges[c.party] || c.party;
        if (!candsByLeader[leader]) candsByLeader[leader] = [];
        candsByLeader[leader].push(c);
    });
    Object.values(candsByLeader).forEach(arr => arr.sort((a, b) => b.personal_votes - a.personal_votes));
    const winnerIds = new Set();
    parties.forEach(p => {
        if (p.seats === 0) return;
        (candsByLeader[p.name] || []).slice(0, p.seats).forEach(c => winnerIds.add(c.candidacy_id));
    });
    const candidates = state.rawCandidates.map(c => ({ ...c, is_winner: winnerIds.has(c.candidacy_id) }));

    const hasMerges = Object.entries(state.merges).some(([k, v]) => k !== v);
    return { parties, candidates, hasMerges };
}

function mergeEuParties(slot, fromName, toName) {
    const state = slot._euState;
    if (!state || fromName === toName) return;
    Object.entries(state.merges).forEach(([party, leader]) => {
        if (leader === fromName) state.merges[party] = toName;
    });
    renderEuView(slot);
}

function resetEuParties(slot) {
    const state = slot._euState;
    if (!state) return;
    state.rawParties.forEach(p => { state.merges[p.name] = p.name; });
    renderEuView(slot);
}

async function exportEuPDF(slot) {
    const state = slot._euState;
    if (!state) return;
    const { parties, candidates, hasMerges } = computeEuView(state);
    const year = slot.dataset.year || '';

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pageW = pdf.internal.pageSize.getWidth();
    const pageH = pdf.internal.pageSize.getHeight();
    const margin = 15;
    const contentW = pageW - margin * 2;
    let curY = margin;

    function checkPage(needed) {
        if (curY + needed > pageH - margin) { pdf.addPage(); curY = margin; }
    }

    pdf.setFontSize(18);
    pdf.setFont(undefined, 'bold');
    pdf.text(`Izbori za Europski parlament ${year}.`, margin, curY);
    curY += 8;
    pdf.setFontSize(11);
    pdf.setFont(undefined, 'normal');
    pdf.text(hasMerges ? 'Simulacija (drag & drop koalicije)' : 'Konačna raspodjela mandata (D\'Hondt, prag 5 %)', margin, curY);
    curY += 8;

    // Capture hemicycle + legend image
    const region = slot.querySelector('.eu-export-region');
    if (region) {
        const canvas = await html2canvas(region, { scale: 2, backgroundColor: '#ffffff', logging: false });
        const imgData = canvas.toDataURL('image/png');
        const ratio = canvas.width / canvas.height;
        let imgW = contentW;
        let imgH = imgW / ratio;
        if (imgH > 130) { imgH = 130; imgW = imgH * ratio; }
        checkPage(imgH);
        pdf.addImage(imgData, 'PNG', margin + (contentW - imgW) / 2, curY, imgW, imgH);
        curY += imgH + 6;
    }

    // Parties summary table
    checkPage(20);
    pdf.setFontSize(13);
    pdf.setFont(undefined, 'bold');
    pdf.text('Stranke / koalicije', margin, curY);
    curY += 6;
    pdf.setFontSize(9);
    pdf.setFont(undefined, 'bold');
    const colW = [contentW * 0.55, contentW * 0.18, contentW * 0.12, contentW * 0.15];
    pdf.text('Naziv', margin, curY);
    pdf.text('Glasovi', margin + colW[0], curY, { align: 'left' });
    pdf.text('% valjanih', margin + colW[0] + colW[1], curY);
    pdf.text('Mandati', margin + colW[0] + colW[1] + colW[2], curY);
    curY += 5;
    pdf.setFont(undefined, 'normal');
    parties.forEach(p => {
        if (curY > pageH - margin - 5) { pdf.addPage(); curY = margin; }
        const memberLabels = (state.merges && Object.entries(state.merges).filter(([_, l]) => l === p.name).map(([k]) => k)) || [p.name];
        const fullLabel = memberLabels.join(' + ');
        const display = fullLabel.length > 65 ? fullLabel.substring(0, 62) + '…' : fullLabel;
        pdf.text(display, margin, curY);
        pdf.text(p.votes.toLocaleString('hr-HR'), margin + colW[0], curY);
        pdf.text(p.votes_pct.toFixed(2) + '%', margin + colW[0] + colW[1], curY);
        pdf.text(String(p.seats) + (p.eligible ? '' : ' *'), margin + colW[0] + colW[1] + colW[2], curY);
        curY += 5;
    });
    curY += 2;
    pdf.setFontSize(8);
    pdf.text('* ispod 5 % praga', margin, curY);
    curY += 6;

    // Candidates table — winners then top non-winners
    checkPage(15);
    pdf.setFontSize(13);
    pdf.setFont(undefined, 'bold');
    pdf.text('Kandidati', margin, curY);
    curY += 6;
    pdf.setFontSize(9);
    pdf.setFont(undefined, 'bold');
    const cc = [contentW * 0.05, contentW * 0.40, contentW * 0.30, contentW * 0.13, contentW * 0.12];
    pdf.text('#', margin, curY);
    pdf.text('Ime', margin + cc[0], curY);
    pdf.text('Stranka', margin + cc[0] + cc[1], curY);
    pdf.text('Pref. glasovi', margin + cc[0] + cc[1] + cc[2], curY);
    pdf.text('% valj.', margin + cc[0] + cc[1] + cc[2] + cc[3], curY);
    curY += 5;
    pdf.setFont(undefined, 'normal');
    const sorted = candidates.slice().sort((a, b) => {
        if (a.is_winner !== b.is_winner) return a.is_winner ? -1 : 1;
        return b.personal_votes - a.personal_votes;
    });
    sorted.forEach((c, i) => {
        if (curY > pageH - margin - 5) { pdf.addPage(); curY = margin; }
        const partyShort = (c.party || '').split('\n')[0];
        const partyDisp = partyShort.length > 38 ? partyShort.substring(0, 35) + '…' : partyShort;
        if (!c.is_winner) pdf.setTextColor(160);
        pdf.text(String(i + 1), margin, curY);
        pdf.text((c.is_winner ? '✓ ' : '   ') + c.name, margin + cc[0], curY);
        pdf.text(partyDisp, margin + cc[0] + cc[1], curY);
        pdf.text(c.personal_votes.toLocaleString('hr-HR'), margin + cc[0] + cc[1] + cc[2], curY);
        pdf.text(c.personal_pct.toFixed(2) + '%', margin + cc[0] + cc[1] + cc[2] + cc[3], curY);
        if (!c.is_winner) pdf.setTextColor(0);
        curY += 4.5;
    });

    pdf.save(`EU_parlament_${year}${hasMerges ? '_simulacija' : ''}.pdf`);
}

function exportEuXLSX(slot) {
    const state = slot._euState;
    if (!state) return;
    const { parties, candidates, hasMerges } = computeEuView(state);
    const year = slot.dataset.year || '';

    const wb = XLSX.utils.book_new();

    // Sheet 1: parties
    const partyRows = [
        [`Izbori za Europski parlament ${year}.${hasMerges ? ' - simulacija' : ''}`],
        [`Ukupno valjanih glasova: ${state.totalVotes.toLocaleString('hr-HR')}  ·  Prag (5 %): ${state.thresholdVotes.toLocaleString('hr-HR')}`],
        [],
        ['Stranka / koalicija', 'Glasovi', '% valjanih', 'Mandati', 'Status'],
    ];
    parties.forEach(p => {
        const memberLabels = Object.entries(state.merges).filter(([_, l]) => l === p.name).map(([k]) => k);
        const fullLabel = memberLabels.length > 0 ? memberLabels.join(' + ') : p.name;
        const status = p.eligible ? (p.seats > 0 ? 'Iznad praga (mandat)' : 'Iznad praga') : 'Ispod 5 %';
        partyRows.push([fullLabel, p.votes, +(p.votes_pct.toFixed(2)), p.seats, status]);
    });
    const wsP = XLSX.utils.aoa_to_sheet(partyRows);
    wsP['!cols'] = [{ wch: 60 }, { wch: 12 }, { wch: 12 }, { wch: 10 }, { wch: 22 }];
    XLSX.utils.book_append_sheet(wb, wsP, 'Stranke');

    // Sheet 2: candidates
    const sortedCands = candidates.slice().sort((a, b) => {
        if (a.is_winner !== b.is_winner) return a.is_winner ? -1 : 1;
        return b.personal_votes - a.personal_votes;
    });
    const candRows = [
        [`Kandidati - Izbori za Europski parlament ${year}.`],
        [],
        ['#', 'Ime i prezime', 'Stranka / lista', 'Pozicija na listi', 'Pref. glasovi', '% valjanih', 'Status'],
    ];
    sortedCands.forEach((c, i) => {
        candRows.push([
            i + 1,
            c.name,
            (c.party || '').split('\n')[0],
            c.list_position,
            c.personal_votes,
            +(c.personal_pct.toFixed(2)),
            c.is_winner ? 'Izabran' : 'Nije izabran',
        ]);
    });
    const wsC = XLSX.utils.aoa_to_sheet(candRows);
    wsC['!cols'] = [{ wch: 5 }, { wch: 32 }, { wch: 50 }, { wch: 8 }, { wch: 13 }, { wch: 12 }, { wch: 14 }];
    XLSX.utils.book_append_sheet(wb, wsC, 'Kandidati');

    XLSX.writeFile(wb, `EU_parlament_${year}${hasMerges ? '_simulacija' : ''}.xlsx`);
}

function attachEuLegendDragDrop(slot) {
    const items = slot.querySelectorAll('.eu-legend-item');
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
            if (from && to && from !== to) mergeEuParties(slot, from, to);
        });
    });
}

function renderEuView(slot) {
    const state = slot._euState;
    const { parties, candidates, hasMerges } = computeEuView(state);
    const partyColors = state.partyColors;
    const totalSeats = state.totalSeats;

    // Original primary-party labels per leader, for "A + B + C" display after merges
    const mergedLabels = {};
    Object.entries(state.merges).forEach(([party, leader]) => {
        if (!mergedLabels[leader]) mergedLabels[leader] = [];
        if (!mergedLabels[leader].includes(party)) mergedLabels[leader].push(party);
    });

    // Seat list (one entry per seat, ordered by party rank)
    const seatList = [];
    let candIdx = 0;
    const winnersInOrder = candidates.filter(c => c.is_winner)
        .sort((a, b) => b.personal_votes - a.personal_votes);
    parties.forEach(p => {
        for (let i = 0; i < p.seats; i++) {
            // Find the next unassigned winner from this party
            const c = winnersInOrder.find(x => !x._used && (state.merges[x.party] || x.party) === p.name);
            if (c) { c._used = true; seatList.push({ party: p.name, color: partyColors[p.name], candidate: c.name, person_id: c.person_id }); }
            else seatList.push({ party: p.name, color: partyColors[p.name], candidate: p.name });
            candIdx++;
        }
    });

    // Hemicycle layout (mirrors renderActualResults so it visually matches Sabor)
    const svgW = 700, svgH = 300, cx = svgW / 2, cy = svgH - 30, dotR = 12, dotSpacing = dotR * 2.5, innerR = 80;
    const rows = []; let totalCap = 0; let r = innerR;
    while (totalCap < seatList.length) {
        const arc = Math.PI * r;
        const cap = Math.floor(arc / dotSpacing);
        rows.push({ radius: r, capacity: cap });
        totalCap += cap;
        r += dotSpacing;
    }
    const nRows = rows.length;
    let seatsToPlace = seatList.length;
    const rowSeats = [];
    const capSum = rows.reduce((s, rr) => s + rr.capacity, 0);
    for (let i = 0; i < nRows; i++) {
        if (i === nRows - 1) rowSeats.push(seatsToPlace);
        else {
            const n = Math.round((rows[i].capacity / capSum) * seatList.length);
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
            positions.push({ x: cx + radius * Math.cos(angle), y: cy - radius * Math.sin(angle) });
        }
    }
    positions.sort((a, b) => Math.atan2(cy - b.y, b.x - cx) - Math.atan2(cy - a.y, a.x - cx));

    let dots = '';
    positions.forEach((pos, i) => {
        const seat = seatList[i]; if (!seat) return;
        dots += `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}" fill="${seat.color}" stroke="white" stroke-width="2" style="cursor:pointer;"><title>${escapeHtml(seat.candidate)}\n${escapeHtml(seat.party)}</title></circle>`;
    });
    const hemiSvg = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:560px; display:block; margin:0 auto;">
            ${dots}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="32" font-weight="bold" fill="#1a1a2e">${totalSeats}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="13" fill="#6c757d">mandata</text>
        </svg>`;

    // Legend — every party (draggable to merge); below-threshold rows greyed out.
    const legendRows = parties.map(p => {
        const dim = p.seats === 0 ? 'opacity:0.55;' : '';
        const swatch = p.seats > 0
            ? `<span style="width:14px;height:14px;border-radius:50%;background:${partyColors[p.name]};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15);"></span>`
            : `<span style="width:14px;height:14px;border-radius:50%;background:#dee2e6;display:inline-block;flex-shrink:0;border:1px solid #ccc;"></span>`;
        const thresholdNote = !p.eligible
            ? ` <span class="badge bg-light text-muted ms-1" style="font-size:0.65rem;">ispod 5%</span>`
            : '';
        // Build merge label "PARTY A + PARTY B + ..."
        const memberLabels = (mergedLabels[p.name] || [p.name]);
        const fullLabel = memberLabels.join(' + ');
        const shortName = fullLabel.length > 50 ? fullLabel.substring(0, 47) + '…' : fullLabel;
        return `<div class="eu-legend-item d-flex align-items-center gap-2"
             draggable="true" data-party="${escapeHtml(p.name)}"
             style="font-size:0.85rem; padding:3px 6px; ${dim} cursor:grab; border:2px solid transparent; border-radius:6px; transition:all 0.15s;"
             title="${escapeHtml(fullLabel)}">
            ${swatch}
            <span class="fw-semibold flex-grow-1">${escapeHtml(shortName)}</span>
            <span class="text-muted small">${p.votes.toLocaleString('hr-HR')} (${formatPct(p.votes_pct, 2)})</span>
            <span class="text-muted" style="min-width:28px; text-align:right;"><strong>${p.seats}</strong></span>
            ${thresholdNote}
        </div>`;
    }).join('');

    // Candidates: winners first (by preference desc), then non-winners (by preference desc).
    // First 50 visible; rest revealed with a "Prikaži još" button.
    const allCands = candidates.slice();
    allCands.sort((a, b) => {
        if (a.is_winner !== b.is_winner) return a.is_winner ? -1 : 1;
        return b.personal_votes - a.personal_votes;
    });
    const winnerCount = allCands.filter(c => c.is_winner).length;
    const INITIAL = 50;
    const STEP = 50;

    const buildRow = c => {
        const partyShort = (c.party || '').split('\n')[0];
        const leader = state.merges[c.party] || c.party;
        const color = partyColors[leader] || '#adb5bd';
        const dim = c.is_winner ? '' : 'opacity:0.55;';
        const winnerBadge = c.is_winner
            ? '<span class="badge bg-success-subtle text-success ms-2" style="font-size:0.65rem;">izabran</span>'
            : '<span class="badge bg-light text-muted ms-2" style="font-size:0.65rem;">nije izabran</span>';
        // Clickable candidate name → that politician's page (same fuzzy-search hop as bar labels)
        const nameHtml = personLinkHtml(c.name, c.person_id);
        return `<tr style="${dim}">
            <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>${nameHtml}${winnerBadge}</td>
            <td class="text-muted" style="font-size:0.85rem;">${escapeHtml(partyShort)}</td>
            <td class="text-end" style="white-space:nowrap;"><strong>${c.personal_votes.toLocaleString('hr-HR')}</strong></td>
            <td class="text-end text-muted" style="white-space:nowrap;">${formatPct(c.personal_pct, 2)}</td>
        </tr>`;
    };

    const candRows = allCands.map((c, i) => {
        if (i >= INITIAL) {
            return buildRow(c).replace('<tr style="', '<tr class="eu-cand-extra" style="display:none;');
        }
        return buildRow(c);
    }).join('');

    const slotId = slot.id;
    const showMoreBtn = allCands.length > INITIAL
        ? `<div class="text-center mt-2">
             <button class="btn btn-outline-primary btn-sm" data-show-more="${slotId}" data-step="${STEP}">
                 <i class="bi bi-chevron-down me-1"></i>Prikaži još (${allCands.length - INITIAL} preostalih)
             </button>
           </div>`
        : '';

    const resetBtn = hasMerges
        ? `<button class="btn btn-outline-secondary btn-sm" data-eu-reset="${slotId}">
               <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi spajanja
           </button>`
        : '';

    const exportButtons = `
        <button class="btn btn-danger btn-sm" data-eu-pdf="${slotId}">
            <i class="bi bi-file-earmark-pdf me-1"></i>PDF
        </button>
        <button class="btn btn-success btn-sm" data-eu-xlsx="${slotId}">
            <i class="bi bi-file-earmark-spreadsheet me-1"></i>XLSX
        </button>`;

    slot.innerHTML = `
        <div class="card border-0" style="background:#f8f9fa; border-radius:10px;">
            <div class="card-body p-3">
                <div class="d-flex justify-content-between align-items-start gap-2 mb-2 flex-wrap">
                    <h6 class="fw-bold mb-0" style="color:#0f3460;">
                        <i class="bi bi-bank me-2"></i>Raspodjela mandata (D'Hondt, prag 5 %)${hasMerges ? ' - simulacija' : ''}
                    </h6>
                    <div class="d-flex gap-2 flex-wrap">
                        ${resetBtn}
                        ${exportButtons}
                    </div>
                </div>
                <div class="eu-export-region">
                ${hemiSvg}
                <div class="d-flex flex-column gap-1 mx-auto mt-2" style="max-width:560px;">
                    ${legendRows}
                </div>
                </div>
                <div class="text-muted text-center mt-1" style="font-size:0.78rem;">
                    <i class="bi bi-arrows-move me-1"></i>Povuci stranku na drugu za spajanje u koaliciju
                </div>
                <div class="text-center text-muted small mt-1">
                    Ukupno valjanih glasova: <strong>${state.totalVotes.toLocaleString('hr-HR')}</strong>
                    · Prag (5 %): <strong>${state.thresholdVotes.toLocaleString('hr-HR')}</strong> glasova
                </div>
                <details class="mt-3" open>
                    <summary class="fw-semibold" style="cursor:pointer; color:#0f3460; font-size:0.9rem;">
                        <i class="bi bi-person-lines-fill me-1"></i>Zastupnici (${winnerCount}) + ostali kandidati po preferencijama
                    </summary>
                    <div class="text-muted small mt-1 mb-2">
                        Izabrani prikazani prvi, zatim ostali kandidati od najviše prema najmanje preferencijalnih glasova.
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0" style="font-size:0.88rem;">
                            <thead><tr>
                                <th>Ime i prezime</th>
                                <th>Stranka / Koalicija</th>
                                <th class="text-end">Preferencijalni glasovi</th>
                                <th class="text-end">% valjanih</th>
                            </tr></thead>
                            <tbody>${candRows}</tbody>
                        </table>
                    </div>
                    ${showMoreBtn}
                </details>
            </div>
        </div>`;

    // Wire drag-drop on legend, reset, exports, and "Prikaži još" — fresh handlers each render.
    attachEuLegendDragDrop(slot);
    const reset = slot.querySelector('button[data-eu-reset]');
    if (reset) reset.addEventListener('click', () => resetEuParties(slot));
    const pdfBtn = slot.querySelector('button[data-eu-pdf]');
    if (pdfBtn) pdfBtn.addEventListener('click', () => exportEuPDF(slot));
    const xlsxBtn = slot.querySelector('button[data-eu-xlsx]');
    if (xlsxBtn) xlsxBtn.addEventListener('click', () => exportEuXLSX(slot));
    const btn = slot.querySelector('button[data-show-more]');
    if (btn) {
        btn.addEventListener('click', () => {
            const hiddenRows = slot.querySelectorAll('tr.eu-cand-extra[style*="display:none"]');
            const step = parseInt(btn.dataset.step, 10) || STEP;
            for (let i = 0; i < step && i < hiddenRows.length; i++) {
                hiddenRows[i].style.display = '';
            }
            const stillHidden = slot.querySelectorAll('tr.eu-cand-extra[style*="display:none"]').length;
            if (stillHidden === 0) btn.remove();
            else btn.innerHTML = `<i class="bi bi-chevron-down me-1"></i>Prikaži još (${stillHidden} preostalih)`;
        });
    }
}

const hemicycleColors = [
    '#2563eb', '#dc2626', '#16a34a', '#ea580c', '#9333ea',
    '#0891b2', '#ca8a04', '#db2777', '#4f46e5', '#059669',
    '#d97706', '#7c3aed', '#0d9488', '#e11d48', '#6366f1',
    '#65a30d', '#c026d3', '#0284c7', '#b91c1c', '#047857',
];

function renderHemicycle(saborData) {
    const parties = saborData.parties || [];
    const totalSeats = saborData.total_seats || 151;
    const container = document.getElementById('hemicycleContainer');
    const legendContainer = document.getElementById('seatLegend');

    // Assign colors to parties
    const partyColors = {};
    parties.forEach((p, i) => {
        partyColors[p.name] = hemicycleColors[i % hemicycleColors.length];
    });

    // SVG dimensions
    const svgW = 700, svgH = 380;
    const cx = svgW / 2, cy = svgH - 30;
    const dotR = 8;
    const dotSpacing = dotR * 2.5;
    const innerR = 90;

    // Calculate row capacities (inner to outer)
    const rows = [];
    let totalCapacity = 0;
    let r = innerR;
    while (totalCapacity < totalSeats) {
        const arc = Math.PI * r;
        const capacity = Math.floor(arc / dotSpacing);
        rows.push({ radius: r, capacity });
        totalCapacity += capacity;
        r += dotSpacing;
    }

    // Distribute seats across rows proportionally
    const nRows = rows.length;
    let seatsToPlace = totalSeats;
    const rowSeats = [];
    const totalCap = rows.reduce((s, r) => s + r.capacity, 0);
    for (let i = 0; i < nRows; i++) {
        if (i === nRows - 1) {
            rowSeats.push(seatsToPlace);
        } else {
            const n = Math.round((rows[i].capacity / totalCap) * totalSeats);
            rowSeats.push(Math.min(n, seatsToPlace));
            seatsToPlace -= rowSeats[i];
        }
    }

    // Build seat positions — all positions first, then assign party colors
    const positions = [];
    for (let ri = 0; ri < nRows; ri++) {
        const count = rowSeats[ri];
        const radius = rows[ri].radius;
        for (let i = 0; i < count; i++) {
            // Spread from left (π) to right (0)
            const angle = Math.PI - (Math.PI * (i + 0.5) / count);
            positions.push({
                x: cx + radius * Math.cos(angle),
                y: cy - radius * Math.sin(angle),
                row: ri,
                col: i,
                colFrac: count > 1 ? i / (count - 1) : 0.5, // 0=left, 1=right
            });
        }
    }

    // Sort positions by angle (left-to-right = π to 0) so parties sit in blocks
    positions.sort((a, b) => {
        const angleA = Math.atan2(cy - a.y, a.x - cx);
        const angleB = Math.atan2(cy - b.y, b.x - cx);
        return angleB - angleA; // π (left) first, 0 (right) last
    });

    // Build seat array with candidate names
    const candidates = saborData.candidates || [];
    const seatList = [];
    let candIdx = 0;
    parties.forEach(p => {
        for (let i = 0; i < p.seats; i++) {
            const cand = candidates[candIdx] || {};
            seatList.push({
                party: p.name,
                color: partyColors[p.name],
                candidate: cand.name || p.name,
                person_id: cand.person_id,
                district: cand.district || '',
            });
            candIdx++;
        }
    });

    // Assign to positions — each party gets a contiguous block
    let posIdx = 0;
    const seatData = new Array(positions.length);
    seatList.forEach((seat, i) => {
        seatData[i] = seat;
    });

    // Render dots
    let dots = '';
    positions.forEach((pos, i) => {
        const seat = seatData[i];
        if (!seat) return;
        const tooltip = `${seat.candidate}\n${seat.party}\n${seat.district}`;
        dots += `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}" fill="${seat.color}" stroke="white" stroke-width="1.5" style="cursor:pointer;">
            <title>${tooltip}</title>
        </circle>`;
    });

    container.innerHTML = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:700px; display:block; margin:0 auto;">
            ${dots}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">${totalSeats}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="12" fill="#6c757d">mandata</text>
        </svg>`;

    // Store hemicycle state for drag-and-drop merging
    window._hemicycleState = {
        parties: JSON.parse(JSON.stringify(parties)),
        partyColors: { ...partyColors },
        seatList: seatList.slice(),
        // Track merged groups: partyName -> groupLeader
        mergeMap: {},
    };
    parties.forEach(p => { window._hemicycleState.mergeMap[p.name] = p.name; });

    renderHemicycleLegend();

    // Candidate list with show-more
    const candContainer = document.getElementById('seatCandidateList');
    renderCandidateList(candContainer, seatList);
}

function renderCandidateList(container, seatList) {
    const INITIAL_SHOW = 100;
    const state = window._hemicycleState;
    const candRows = seatList.map((s, i) => {
        const group = state.mergeMap[s.party] || s.party;
        const color = state.partyColors[group] || s.color;
        const hidden = i >= INITIAL_SHOW ? ' style="display:none;" class="seat-cand-extra"' : '';
        // Clickable candidate name (same fuzzy-search hop as bar-label-link)
        const nameHtml = personLinkHtml(s.candidate, s.person_id);
        return `<tr${hidden}>
            <td style="width:30px;" class="text-muted text-end pe-2">${i + 1}.</td>
            <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>${nameHtml}</td>
            <td class="text-muted" style="font-size:0.85rem;">${s.party}</td>
            <td class="text-muted" style="font-size:0.85rem;">${s.district}</td>
        </tr>`;
    }).join('');

    const showMoreBtn = seatList.length > INITIAL_SHOW
        ? `<div class="text-center mt-2">
            <button class="btn btn-outline-primary btn-sm" id="showMoreCandBtn" onclick="document.querySelectorAll('.seat-cand-extra').forEach(r=>r.style.display='');this.style.display='none';">
                <i class="bi bi-chevron-down me-1"></i>Prikaži sve (${seatList.length - INITIAL_SHOW} preostalih)
            </button>
           </div>`
        : '';

    container.innerHTML = `
        <h6 class="fw-bold mt-4 mb-2"><i class="bi bi-person-lines-fill me-2"></i>Zastupnici</h6>
        <div class="table-responsive">
            <table class="table table-sm table-hover mb-0" style="font-size:0.88rem;">
                <thead><tr>
                    <th></th>
                    <th>Ime i prezime</th>
                    <th>Stranka / Koalicija</th>
                    <th>Izborna jedinica</th>
                </tr></thead>
                <tbody>${candRows}</tbody>
            </table>
        </div>
        ${showMoreBtn}`;
}

function renderHemicycleLegend() {
    const legendContainer = document.getElementById('seatLegend');
    const state = window._hemicycleState;
    const { mergeMap, partyColors, parties } = state;

    // Build merged groups: group leader -> { names[], totalSeats, color }
    const groups = {};
    parties.forEach(p => {
        const leader = mergeMap[p.name];
        if (!groups[leader]) {
            groups[leader] = { names: [], seats: 0, color: partyColors[leader] };
        }
        groups[leader].names.push(p.name);
        groups[leader].seats += p.seats;
    });

    // Order: by merged seat count descending (ties broken by name) so rows don't reflow jarringly
    const orderedLeaders = parties
        .map(p => p.name)
        .filter(n => mergeMap[n] === n)
        .sort((a, b) => groups[b].seats - groups[a].seats || a.localeCompare(b));

    const hasMerges = Object.keys(groups).length < parties.length;

    const legendItems = orderedLeaders.map(leader => {
        const g = groups[leader];
        const label = g.names.length > 1
            ? g.names.map(n => n.length > 25 ? n.substring(0, 22) + '...' : n).join(' + ')
            : (leader.length > 35 ? leader.substring(0, 32) + '...' : leader);
        const displayLabel = label.length > 60 ? label.substring(0, 57) + '...' : label;
        return `<div class="hemi-legend-item d-flex align-items-center gap-1"
                     draggable="true"
                     data-party="${leader}"
                     title="${g.names.join(' + ')}"
                     style="font-size:0.82rem; cursor:grab; padding:4px 8px; border-radius:6px; border:2px solid transparent; transition:all 0.15s;">
                    <span style="width:14px;height:14px;border-radius:50%;background:${g.color};display:inline-block;flex-shrink:0;border:1px solid rgba(0,0,0,0.15);"></span>
                    <span class="fw-semibold">${displayLabel}</span>
                    <span class="text-muted">(${g.seats})</span>
                </div>`;
    }).join('');

    legendContainer.innerHTML = `
        <div class="d-flex flex-column gap-1 align-items-stretch mx-auto mb-2" style="max-width:520px;">
            ${legendItems}
        </div>
        <div class="d-flex justify-content-between align-items-center mt-1">
            <div class="text-muted" style="font-size:0.78rem;"><i class="bi bi-arrows-move me-1"></i>Povuci stranku na drugu za spajanje rezultata</div>
            <button class="btn btn-outline-secondary btn-sm ${hasMerges ? '' : 'd-none'}" id="resetHemicycleBtn" onclick="resetHemicycleMerges()">
                <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
            </button>
        </div>`;

    // Attach drag-and-drop handlers
    const items = legendContainer.querySelectorAll('.hemi-legend-item');
    items.forEach(item => {
        item.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', item.dataset.party);
            item.style.opacity = '0.5';
        });
        item.addEventListener('dragend', e => {
            item.style.opacity = '1';
            items.forEach(it => {
                it.style.borderColor = 'transparent';
                it.style.background = '';
            });
        });
        item.addEventListener('dragover', e => {
            e.preventDefault();
            item.style.borderColor = '#0d6efd';
            item.style.background = 'rgba(13,110,253,0.08)';
        });
        item.addEventListener('dragleave', e => {
            item.style.borderColor = 'transparent';
            item.style.background = '';
        });
        item.addEventListener('drop', e => {
            e.preventDefault();
            item.style.borderColor = 'transparent';
            item.style.background = '';
            const draggedParty = e.dataTransfer.getData('text/plain');
            const targetParty = item.dataset.party;
            if (draggedParty && targetParty && draggedParty !== targetParty) {
                mergeHemicycleParties(draggedParty, targetParty);
            }
        });
    });
}

function mergeHemicycleParties(from, to) {
    const state = window._hemicycleState;
    const { mergeMap, partyColors } = state;

    // Redirect everything that pointed to 'from' to now point to 'to'
    for (const key in mergeMap) {
        if (mergeMap[key] === from) {
            mergeMap[key] = to;
        }
    }

    // Update SVG circles
    const svg = document.querySelector('#hemicycleContainer svg');
    if (svg) {
        const circles = svg.querySelectorAll('circle');
        const targetColor = partyColors[to];
        circles.forEach(circle => {
            const title = circle.querySelector('title');
            if (!title) return;
            const text = title.textContent;
            // Check if this circle belongs to the 'from' group
            const partyLine = text.split('\n')[1]; // party name is second line
            if (partyLine && mergeMap[partyLine.trim()] === to) {
                circle.setAttribute('fill', targetColor);
            }
        });
    }

    // Re-render legend and candidate list
    renderHemicycleLegend();
    const candContainer = document.getElementById('seatCandidateList');
    if (candContainer) {
        renderCandidateList(candContainer, state.seatList);
    }
}

function resetHemicycleMerges() {
    const state = window._hemicycleState;
    // Reset merge map
    state.parties.forEach(p => { state.mergeMap[p.name] = p.name; });

    // Reset SVG circle colors
    const svg = document.querySelector('#hemicycleContainer svg');
    if (svg) {
        const circles = svg.querySelectorAll('circle');
        circles.forEach(circle => {
            const title = circle.querySelector('title');
            if (!title) return;
            const partyLine = title.textContent.split('\n')[1];
            if (partyLine) {
                const party = partyLine.trim();
                const color = state.partyColors[party];
                if (color) circle.setAttribute('fill', color);
            }
        });
    }

    renderHemicycleLegend();
    const candContainer = document.getElementById('seatCandidateList');
    if (candContainer) {
        renderCandidateList(candContainer, state.seatList);
    }
}
