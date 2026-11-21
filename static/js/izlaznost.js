// Izlaznost: turnout across elections and scopes.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// === Izlaznost (turnout) analytics module ===
const izl = {
    initialized: false,
    elections: [],
    chart: null,
    // Active scope from the dropdowns (one of: national, county, municipality, station)
    scope: { level: 'national', countyId: null, countyName: '', muniId: null, muniName: '', stationId: null, stationLabel: '' },
    // Multi-station compare list. When non-empty, chart switches to multi-line mode.
    compareStations: [], // [{id, label, muniName, countyName}]
    mapPaths: [],
};

const IZL_CATEGORY_COLORS = {
    sabor: 'rgb(220, 53, 69)',
    predsjednicki: 'rgb(15, 52, 96)',
    eu: 'rgb(0, 110, 195)',
    lokalni: 'rgb(25, 135, 84)',
};

const IZL_COMPARE_PALETTE = [
    '#0f3460', '#dc3545', '#198754', '#fd7e14', '#6f42c1',
    '#0dcaf0', '#d63384', '#20c997', '#ffc107', '#6c757d',
];

async function initIzlaznost() {
    if (izl.initialized) return;
    izl.initialized = true;

    // Wire up event handlers up front so they survive any data-fetch failure.
    document.querySelectorAll('.izl-filter-cat').forEach(cb => {
        cb.addEventListener('change', loadIzlaznostData);
    });
    document.getElementById('izlShowRound2').addEventListener('change', loadIzlaznostData);
    document.getElementById('izlSelCounty').addEventListener('change', onIzlCountyChange);
    document.getElementById('izlSelMuni').addEventListener('change', onIzlMuniChange);
    document.getElementById('izlSelStation').addEventListener('change', onIzlStationChange);
    document.getElementById('izlAddCompareBtn').addEventListener('click', onIzlAddCompare);
    document.getElementById('izlClearScopeBtn').addEventListener('click', onIzlClearScope);

    // Map is a static asset — load independently so a DB outage doesn't hide it.
    loadIzlCroatiaMap().catch(err => console.warn('Croatia map load failed:', err));

    const empty = document.getElementById('izlEmpty');
    try {
        const eRes = await fetch('/api/analytics/elections');
        if (!eRes.ok) throw new Error(`HTTP ${eRes.status}`);
        izl.elections = await eRes.json();
    } catch (err) {
        izl.initialized = false; // allow retry on next module switch
        empty.style.display = '';
        empty.innerHTML = `<div class="text-danger fw-semibold mb-1">Greška pri učitavanju izbora</div>
            <div class="text-muted small">Provjeri da Flask server radi i da je baza dostupna (vidi konzolu).</div>`;
        console.error('initIzlaznost: /api/analytics/elections failed', err);
        return;
    }

    try {
        const cRes = await fetch('/api/counties');
        if (!cRes.ok) throw new Error(`HTTP ${cRes.status}`);
        const counties = await cRes.json();
        const selC = document.getElementById('izlSelCounty');
        counties.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            selC.appendChild(opt);
        });
    } catch (err) {
        // Non-fatal — Hrvatska view still works without the dropdowns
        console.warn('initIzlaznost: /api/counties failed', err);
    }

    loadIzlaznostData();
}

async function loadIzlCroatiaMap() {
    const wrap = document.getElementById('izlCroatiaMapWrap');
    const res = await fetch('/static/croatia_map.svg');
    const svgText = await res.text();
    wrap.innerHTML = svgText;
    const embeddedStyle = wrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    const svgTitle = wrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();

    izl.mapPaths = wrap.querySelectorAll('path[data-county]');
    const label = document.getElementById('izlMapCountyLabel');

    izl.mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const countyName = path.getAttribute('data-county');
            const sel = document.getElementById('izlSelCounty');
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

function izlHighlightMapCounty(countyName) {
    izl.mapPaths.forEach(p => p.classList.remove('selected'));
    const label = document.getElementById('izlMapCountyLabel');
    if (countyName) {
        const target = document.getElementById('izlCroatiaMapWrap')
            .querySelector(`path[data-county="${countyName}"]`);
        if (target) target.classList.add('selected');
        label.textContent = countyName;
    } else {
        label.textContent = '';
    }
}

async function onIzlCountyChange() {
    const sel = document.getElementById('izlSelCounty');
    const selMuni = document.getElementById('izlSelMuni');
    const selStation = document.getElementById('izlSelStation');

    selMuni.innerHTML = '<option value="">Sva mjesta u županiji</option>';
    selStation.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    selMuni.disabled = true;
    selStation.disabled = true;

    const countyId = sel.value;
    const countyName = countyId ? sel.options[sel.selectedIndex].textContent : '';
    izl.scope = countyId
        ? { level: 'county', countyId: parseInt(countyId, 10), countyName, muniId: null, muniName: '', stationId: null, stationLabel: '' }
        : { level: 'national', countyId: null, countyName: '', muniId: null, muniName: '', stationId: null, stationLabel: '' };

    izlHighlightMapCounty(countyName || null);
    izlUpdateAddBtn();

    if (countyId) {
        const res = await fetch(`/api/municipalities/${countyId}`);
        const data = await res.json();
        data.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.name;
            selMuni.appendChild(opt);
        });
        selMuni.disabled = false;
    }

    loadIzlaznostData();
}

async function onIzlMuniChange() {
    const selMuni = document.getElementById('izlSelMuni');
    const selStation = document.getElementById('izlSelStation');

    selStation.innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    selStation.disabled = true;

    const muniId = selMuni.value;
    const muniName = muniId ? selMuni.options[selMuni.selectedIndex].textContent : '';

    if (muniId) {
        izl.scope.level = 'municipality';
        izl.scope.muniId = parseInt(muniId, 10);
        izl.scope.muniName = muniName;
    } else {
        izl.scope.level = izl.scope.countyId ? 'county' : 'national';
        izl.scope.muniId = null;
        izl.scope.muniName = '';
    }
    izl.scope.stationId = null;
    izl.scope.stationLabel = '';
    izlUpdateAddBtn();

    if (muniId) {
        const res = await fetch(`/api/polling-stations/${muniId}`);
        const data = await res.json();
        data.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.name;
            selStation.appendChild(opt);
        });
        selStation.disabled = false;
    }

    loadIzlaznostData();
}

function onIzlStationChange() {
    const selStation = document.getElementById('izlSelStation');
    const stationId = selStation.value;
    if (stationId) {
        izl.scope.level = 'station';
        izl.scope.stationId = parseInt(stationId, 10);
        izl.scope.stationLabel = selStation.options[selStation.selectedIndex].textContent;
    } else {
        izl.scope.level = izl.scope.muniId ? 'municipality' : (izl.scope.countyId ? 'county' : 'national');
        izl.scope.stationId = null;
        izl.scope.stationLabel = '';
    }
    izlUpdateAddBtn();
    loadIzlaznostData();
}

function izlUpdateAddBtn() {
    document.getElementById('izlAddCompareBtn').disabled = !izl.scope.stationId;
}

function onIzlAddCompare() {
    if (!izl.scope.stationId) return;
    if (izl.compareStations.find(s => s.id === izl.scope.stationId)) return;
    if (izl.compareStations.length >= IZL_COMPARE_PALETTE.length) return;
    izl.compareStations.push({
        id: izl.scope.stationId,
        label: izl.scope.stationLabel,
        muniName: izl.scope.muniName,
        countyName: izl.scope.countyName,
    });
    renderIzlCompareChips();
    loadIzlaznostData();
}

function onIzlRemoveCompare(id) {
    izl.compareStations = izl.compareStations.filter(s => s.id !== id);
    renderIzlCompareChips();
    loadIzlaznostData();
}

function onIzlClearScope() {
    document.getElementById('izlSelCounty').value = '';
    document.getElementById('izlSelMuni').innerHTML = '<option value="">Sva mjesta u županiji</option>';
    document.getElementById('izlSelStation').innerHTML = '<option value="">Sva biračka mjesta u općini</option>';
    document.getElementById('izlSelMuni').disabled = true;
    document.getElementById('izlSelStation').disabled = true;
    izl.scope = { level: 'national', countyId: null, countyName: '', muniId: null, muniName: '', stationId: null, stationLabel: '' };
    izl.compareStations = [];
    izlHighlightMapCounty(null);
    izlUpdateAddBtn();
    renderIzlCompareChips();
    loadIzlaznostData();
}

function renderIzlCompareChips() {
    const wrap = document.getElementById('izlCompareChips');
    if (izl.compareStations.length === 0) { wrap.innerHTML = ''; return; }
    wrap.innerHTML = izl.compareStations.map((s, i) => {
        const color = IZL_COMPARE_PALETTE[i % IZL_COMPARE_PALETTE.length];
        const sub = s.muniName ? ` <span style="color:#888">· ${escapeHtml(s.muniName)}</span>` : '';
        return `<span class="izl-compare-chip">
            <span class="chip-swatch" style="background:${color}"></span>
            ${escapeHtml(s.label)}${sub}
            <button type="button" class="chip-x" data-id="${s.id}" aria-label="Ukloni">×</button>
        </span>`;
    }).join('');
    wrap.querySelectorAll('.chip-x').forEach(btn => {
        btn.addEventListener('click', () => onIzlRemoveCompare(parseInt(btn.dataset.id, 10)));
    });
}

function izlSelectedIds() {
    const cats = new Set(
        [...document.querySelectorAll('.izl-filter-cat:checked')].map(cb => cb.value)
    );
    const showR2 = document.getElementById('izlShowRound2').checked;
    return izl.elections
        .filter(el => cats.has(el.category) && (showR2 || el.round_number !== 2))
        .map(el => el.id);
}

async function loadIzlaznostData() {
    const chartCard = document.getElementById('izlChartCard');
    const empty = document.getElementById('izlEmpty');
    const spinner = document.getElementById('izlSpinner');

    const selectedIds = izlSelectedIds();
    if (selectedIds.length === 0) {
        chartCard.style.display = 'none';
        empty.style.display = '';
        empty.textContent = 'Odaberi barem jednu kategoriju izbora.';
        return;
    }
    empty.style.display = 'none';
    spinner.style.display = '';

    const params = new URLSearchParams();
    params.set('groups', selectedIds.join(','));

    let data;
    if (izl.compareStations.length > 0) {
        // Multi-station mode — single fetch with explicit station_ids
        params.set('level', 'station');
        params.set('station_ids', izl.compareStations.map(s => s.id).join(','));
        const res = await fetch('/api/analytics/turnout?' + params.toString());
        data = await res.json();
    } else {
        // Single-scope mode — fetch at the chosen level and filter to the picked entity
        const level = izl.scope.level;
        if (level === 'national') {
            params.set('level', 'national');
        } else if (level === 'county') {
            params.set('level', 'county');
        } else if (level === 'municipality') {
            params.set('level', 'municipality');
            params.set('parent_id', izl.scope.countyId);
        } else if (level === 'station') {
            params.set('level', 'station');
            params.set('station_ids', izl.scope.stationId);
        }
        const res = await fetch('/api/analytics/turnout?' + params.toString());
        data = await res.json();
    }
    spinner.style.display = 'none';

    renderIzlaznostChart(data);
}

function izlScopeTitle() {
    if (izl.compareStations.length > 0) {
        return `Usporedba biračkih mjesta (${izl.compareStations.length})`;
    }
    const s = izl.scope;
    if (s.level === 'national') return 'Izlaznost - ukupno (Hrvatska)';
    if (s.level === 'county') return `Izlaznost - ${s.countyName}`;
    if (s.level === 'municipality') return `Izlaznost - ${s.muniName}, ${s.countyName}`;
    if (s.level === 'station') return `Izlaznost - ${s.stationLabel} (${s.muniName})`;
    return 'Izlaznost';
}

function izlPickRow(group) {
    // For single-scope queries against the existing endpoints, the response
    // contains all entities at that level. Pick the row matching the user's choice.
    if (izl.scope.level === 'county') {
        return group.rows.find(r => r.id === izl.scope.countyId) || null;
    }
    if (izl.scope.level === 'municipality') {
        return group.rows.find(r => r.id === izl.scope.muniId) || null;
    }
    // national / station-via-station_ids: single row already
    return group.rows[0] || null;
}

function renderIzlaznostChart(data) {
    const chartCard = document.getElementById('izlChartCard');
    const empty = document.getElementById('izlEmpty');
    document.getElementById('izlChartTitle').textContent = izlScopeTitle();

    if (!data.groups || data.groups.length === 0) {
        chartCard.style.display = 'none';
        empty.style.display = '';
        empty.textContent = 'Nema podataka.';
        return;
    }
    chartCard.style.display = '';

    const multi = izl.compareStations.length > 0;

    // Sort groups chronologically by election date (then round) — shared x-axis
    const sortedGroups = [...data.groups].sort((a, b) => {
        const ma = izl.elections.find(e => e.id === a.id);
        const mb = izl.elections.find(e => e.id === b.id);
        const da = (ma && ma.date) || `${a.year}-12-31`;
        const db = (mb && mb.date) || `${b.year}-12-31`;
        if (da !== db) return da < db ? -1 : 1;
        return a.round_number - b.round_number;
    });

    const labels = sortedGroups.map(g => {
        const meta = izl.elections.find(e => e.id === g.id);
        let l = g.label;
        if (meta && meta.date) {
            const d = new Date(meta.date);
            l += `\n${d.toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' })}`;
        }
        return l;
    });
    const groupCategories = sortedGroups.map(g => g.category);

    const canvas = document.getElementById('izlChartCanvas');
    if (izl.chart) { izl.chart.destroy(); izl.chart = null; }
    // Wrap + size the scroll container BEFORE creating the chart so Chart.js
    // measures the (potentially wider) inner element on creation.
    applyChartScroll(canvas, labels.length, { height: 380 });
    const ctx = canvas.getContext('2d');

    let datasets;
    let tableRows;

    if (!multi) {
        // Single-scope: one dataset with per-category point colors (existing behavior)
        const points = sortedGroups.map(g => {
            const row = izlPickRow(g);
            const turnout = (row && row.registered > 0) ? (row.cast / row.registered * 100) : null;
            return {
                id: g.id, label: g.label, category: g.category,
                year: g.year, round: g.round_number,
                registered: row ? row.registered : 0,
                cast: row ? row.cast : 0,
                valid: row ? row.valid : 0,
                invalid: row ? row.invalid : 0,
                turnout: turnout,
            };
        });
        const values = points.map(p => p.turnout === null ? null : +p.turnout.toFixed(2));
        const pointColors = points.map(p => IZL_CATEGORY_COLORS[p.category] || '#6c757d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 320);
        gradient.addColorStop(0, 'rgba(15, 52, 96, 0.25)');
        gradient.addColorStop(1, 'rgba(15, 52, 96, 0.02)');
        datasets = [{
            label: 'Izlaznost (%)',
            data: values,
            borderColor: 'rgb(15, 52, 96)',
            backgroundColor: gradient,
            fill: true,
            tension: 0.3,
            borderWidth: 3,
            pointBackgroundColor: pointColors,
            pointBorderColor: '#fff',
            pointBorderWidth: 2.5,
            pointRadius: 7,
            pointHoverRadius: 10,
            pointHoverBorderWidth: 3,
            spanGaps: true,
            _points: points,
        }];
        tableRows = points.map(p => ({
            label: p.label, category: p.category, year: p.year,
            registered: p.registered, cast: p.cast, valid: p.valid,
            turnoutStr: p.turnout === null ? '-' : formatPct(p.turnout),
            colorDot: IZL_CATEGORY_COLORS[p.category] || '#6c757d',
        }));
    } else {
        // Multi-station compare: one dataset per station
        datasets = izl.compareStations.map((station, i) => {
            const color = IZL_COMPARE_PALETTE[i % IZL_COMPARE_PALETTE.length];
            const points = sortedGroups.map(g => {
                const row = (g.rows || []).find(r => r.id === station.id);
                const turnout = (row && row.registered > 0) ? (row.cast / row.registered * 100) : null;
                return {
                    registered: row ? row.registered : 0,
                    cast: row ? row.cast : 0,
                    valid: row ? row.valid : 0,
                    turnout: turnout,
                };
            });
            return {
                label: station.label,
                data: points.map(p => p.turnout === null ? null : +p.turnout.toFixed(2)),
                borderColor: color,
                backgroundColor: color + '22',
                fill: false,
                tension: 0.3,
                borderWidth: 2.5,
                pointBackgroundColor: color,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 9,
                spanGaps: true,
                _points: points,
                _station: station,
            };
        });
        // Build a wide table: one row per election, one col per station
        tableRows = sortedGroups.map((g, gi) => ({
            label: g.label,
            category: g.category,
            year: g.year,
            colorDot: IZL_CATEGORY_COLORS[g.category] || '#6c757d',
            cells: datasets.map(ds => {
                const p = ds._points[gi];
                return p.turnout === null ? '-' : formatPct(p.turnout);
            }),
        }));
    }

    izl.chart = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            onClick: (evt, items) => {
                if (!multi && items && items.length) {
                    const cat = groupCategories[items[0].index];
                    const year = sortedGroups[items[0].index].year;
                    izlNavigateTo(cat, year);
                }
            },
            onHover: (evt, items) => {
                evt.native.target.style.cursor = (!multi && items && items.length) ? 'pointer' : 'default';
            },
            plugins: {
                legend: { display: multi, position: 'bottom', labels: { boxWidth: 14, font: { size: 11 } } },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    padding: 14,
                    cornerRadius: 8,
                    displayColors: multi,
                    callbacks: {
                        label: function(c) {
                            const ds = c.dataset;
                            const p = ds._points[c.dataIndex];
                            if (!p || p.turnout === null) return `${ds.label}: nema podataka`;
                            const head = multi ? `${ds.label}: ${formatPct(p.turnout)}` : `Izlaznost: ${formatPct(p.turnout)}`;
                            return [
                                head,
                                `Glasovalo: ${p.cast.toLocaleString('hr-HR')}`,
                                `Upisanih: ${p.registered.toLocaleString('hr-HR')}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { callback: v => formatPct(v, 0), font: { size: 12 } },
                    title: { display: true, text: 'Izlaznost (%)', font: { size: 12, weight: 'bold' }, color: '#6c757d' },
                },
                x: {
                    grid: { color: 'rgba(0,0,0,0.03)' },
                    ticks: { font: { size: 11 }, maxRotation: 45 },
                },
            },
            animation: { duration: 700, easing: 'easeOutQuart' },
        },
    });

    // Data table beneath the chart
    const table = document.getElementById('izlChartTable');
    if (!multi) {
        // Banner: name selected elections that had no data for this scope.
        // For stations this typically means a mobile/abroad station that
        // only participated in parliamentary elections.
        const missingLabels = tableRows.filter(r => r.turnoutStr === '-').map(r => r.label);
        let banner = '';
        if (missingLabels.length > 0 && izl.scope.level === 'station') {
            banner = `<div class="alert alert-warning py-2 px-3 mb-2" style="font-size:0.82rem;">
                <i class="bi bi-info-circle me-1"></i>Ovo biračko mjesto nije korišteno za:
                <strong>${missingLabels.map(escapeHtml).join(', ')}</strong>.
                Mobilna i inozemna birališta obično se otvaraju samo za parlamentarne izbore.
            </div>`;
        } else if (missingLabels.length > 0 && izl.scope.level !== 'national') {
            banner = `<div class="alert alert-warning py-2 px-3 mb-2" style="font-size:0.82rem;">
                <i class="bi bi-info-circle me-1"></i>Nema podataka za:
                <strong>${missingLabels.map(escapeHtml).join(', ')}</strong>.
            </div>`;
        }
        table.innerHTML = banner + `
            <table class="table table-sm align-middle mb-0">
                <thead><tr>
                    <th>Izbori</th><th class="text-end">Upisani</th>
                    <th class="text-end">Glasovali</th><th class="text-end">Valjani</th>
                    <th class="text-end">Izlaznost</th>
                </tr></thead>
                <tbody>
                    ${tableRows.map(p => `<tr class="izl-tbl-row" data-cat="${p.category}" data-year="${p.year}" style="cursor:pointer;">
                        <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.colorDot};margin-right:8px;"></span><a href="#" class="text-decoration-none" style="color:#0f3460;">${escapeHtml(p.label)}</a></td>
                        <td class="text-end">${p.registered.toLocaleString('hr-HR')}</td>
                        <td class="text-end">${p.cast.toLocaleString('hr-HR')}</td>
                        <td class="text-end">${p.valid.toLocaleString('hr-HR')}</td>
                        <td class="text-end fw-bold" style="color:#0f3460;">${p.turnoutStr}</td>
                    </tr>`).join('')}
                </tbody>
            </table>
        `;
        table.querySelectorAll('.izl-tbl-row').forEach(tr => {
            tr.addEventListener('click', e => {
                e.preventDefault();
                izlNavigateTo(tr.dataset.cat, parseInt(tr.dataset.year, 10));
            });
        });
    } else {
        const stationHeaders = izl.compareStations.map((s, i) => {
            const color = IZL_COMPARE_PALETTE[i % IZL_COMPARE_PALETTE.length];
            return `<th class="text-end" style="white-space:nowrap;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>${escapeHtml(s.label)}
            </th>`;
        }).join('');
        table.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm align-middle mb-0">
                    <thead><tr>
                        <th>Izbori</th>${stationHeaders}
                    </tr></thead>
                    <tbody>
                        ${tableRows.map(r => `<tr>
                            <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${r.colorDot};margin-right:8px;"></span>${escapeHtml(r.label)}</td>
                            ${r.cells.map(c => `<td class="text-end fw-bold" style="color:#0f3460;">${c}</td>`).join('')}
                        </tr>`).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
}
