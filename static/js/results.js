// Shared result rendering: election filters, result cards and charts.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// --- Universal election filter system ---
// Stores raw data per module so checkboxes can re-render without re-fetching
const _rawData = {
    person: null,   // { type: 'person', data: apiResponse }
    station: null,  // { elections: [...] }
    compare: null,  // handled via compareState
};

function classifyElection(el) {
    const t = (el.election_type || '').toLowerCase();
    if (t.includes('predsjednič')) return 'predsjednicki';
    if (t.includes('parlamentar') && !t.includes('europ')) return 'sabor';
    if (t.includes('europ')) return 'eu';
    return 'local';
}

function getFilterState(moduleName) {
    const container = document.querySelector(`.election-filters[data-module="${moduleName}"]`);
    if (!container) return { eu: true, local: true, predsjednicki: true, sabor: true, round2: true };
    const cbs = container.querySelectorAll('.filter-election');
    const state = {};
    cbs.forEach(cb => { state[cb.value] = cb.checked; });
    return state;
}

function filterResults(results, moduleName) {
    const f = getFilterState(moduleName);
    return results.filter(el => {
        const cat = classifyElection(el);
        if (cat === 'eu' && !f.eu) return false;
        if (cat === 'local' && !f.local) return false;
        if (cat === 'predsjednicki' && !f.predsjednicki) return false;
        if (cat === 'sabor' && !f.sabor) return false;
        if ((el.round || 1) >= 2 && !f.round2) return false;
        return true;
    });
}

function applyFilters(moduleName) {
    if (moduleName === 'station') {
        if (!_rawData.station) return;
        const filtered = filterResults(_rawData.station, 'station');
        const detailResults = document.getElementById('locationDetailResults');
        renderStationWinnerChart(filtered);
        renderStationResults(detailResults, filtered);
    } else if (moduleName === 'person' && _compareItems.person.length > 0) {
        rerenderCompareModule('person');
    } else if (moduleName === 'compare') {
        renderComparisons();
    }
}

// Attach checkbox listeners for all modules
document.querySelectorAll('.election-filters').forEach(container => {
    const mod = container.dataset.module;
    container.querySelectorAll('.filter-election').forEach(cb => {
        cb.addEventListener('change', () => applyFilters(mod));
    });
});

// Show one place's (or one area's) results: header, winner chart and cards.
// `town` ({id, name}) adds the link to the town's page.
function renderLocationData(data, town) {
    const detailSection = document.getElementById('locationDetailSection');
    const detailName = document.getElementById('locationDetailName');
    const detailResults = document.getElementById('locationDetailResults');
    detailSection.style.display = 'block';

    // Store raw data for filtering
    _rawData.station = data.elections;

    detailName.innerHTML = `<i class="bi bi-geo-alt-fill me-2"></i>${escapeHtml(data.label || '')}`;
    // A town's whole history is on its own page.
    if (town) {
        detailName.innerHTML += ` <span class="small fw-normal ms-2"><i class="bi bi-house-door me-1"></i>${placeLinkHtml(town.id, town.name)}: načelnici, vijeće i svi izbori</span>`;
    }
    renderNumberOnlyNote(data);
    const filtered = filterResults(data.elections, 'station');
    renderStationWinnerChart(filtered);
    renderStationResults(detailResults, filtered);
}

async function loadLocationResults() {
    const params = new URLSearchParams();
    if (selStation.value) {
        params.set('station_id', selStation.value);
    } else if (selStreet.value && selMunicipality.value) {
        params.set('municipality_id', selMunicipality.value);
        params.set('street', selStreet.value);
    } else if (selMunicipality.value) {
        params.set('municipality_id', selMunicipality.value);
    } else if (selCounty.value) {
        params.set('county_id', selCounty.value);
    }

    const spinner = document.getElementById('locationSpinner');
    const detailSection = document.getElementById('locationDetailSection');

    detailSection.style.display = 'none';
    spinner.classList.add('show');

    const res = await fetch(`/api/location-results?${params}`);
    const data = await res.json();

    spinner.classList.remove('show');
    const muniId = parseInt(selMunicipality.value, 10);
    renderLocationData(data, muniId ? { id: muniId, name: selMunicipality.options[selMunicipality.selectedIndex].textContent } : null);

    // Show map if specific station selected
    if (selStation.value) {
        const stationRes = await fetch(`/api/station/${selStation.value}`);
        const stationData = await stationRes.json();
        renderStationMap(stationData);
    } else {
        document.getElementById('stationMapCard').style.display = 'none';
    }
}

// Presidential 2000-2009 and Sabor 2000-2007 were published per station
// number only, so a place lacks them wherever its number meant several places.
function renderNumberOnlyNote(data) {
    const note = document.getElementById('locationNumberOnlyNote');
    const missing = data.number_only_missing || [];
    note.style.display = missing.length ? '' : 'none';
    note.innerHTML = missing.length
        ? `<i class="bi bi-info-circle me-1"></i><b>Nema rezultata za ovo biračko mjesto:</b> ${missing.map(escapeHtml).join(', ')}.`
        : '';
}

function getElectionColor(type) {
    if (type.toLowerCase().includes('predsjednič')) return { bg: 'rgba(220, 53, 69, 0.15)', border: 'rgb(220, 53, 69)' };
    if (type.toLowerCase().includes('parlamentar') || type.toLowerCase().includes('sabor')) return { bg: 'rgba(13, 110, 253, 0.15)', border: 'rgb(13, 110, 253)' };
    if (type.toLowerCase().includes('eu')) return { bg: 'rgba(13, 202, 240, 0.15)', border: 'rgb(13, 202, 240)' };
    if (type.toLowerCase().includes('lokaln')) return { bg: 'rgba(25, 135, 84, 0.15)', border: 'rgb(25, 135, 84)' };
    return { bg: 'rgba(108, 117, 125, 0.15)', border: 'rgb(108, 117, 125)' };
}

function renderVotesChart(panel, results, type) {
    const chartContainer = panel.querySelector('.chart-container');
    const canvas = panel.querySelector('.votes-chart');
    const modKey = panel.id;

    if (moduleCharts[modKey]) {
        moduleCharts[modKey].destroy();
        moduleCharts[modKey] = null;
    }

    const votesKey = type === 'person' ? 'candidate_votes' : 'total_votes';
    const filtered = results.filter(r => r[votesKey] > 0).reverse();

    if (filtered.length === 0) {
        chartContainer.style.display = 'none';
        return;
    }

    chartContainer.style.display = 'block';

    const labels = filtered.map(r => {
        let label = r.election_type.replace('izbori', '').trim();
        if (r.date) {
            const d = new Date(r.date);
            label += `\n${d.toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' })}`;
        } else {
            label += ` ${r.year}`;
        }
        if (r.round > 1) label += ` (${r.round}. krug)`;
        if (r.district) label += `\n${r.district}`;
        return label;
    });

    const shareValues = filtered.map(r => r.vote_share || 0);
    const rawVotes = filtered.map(r => r[votesKey]);
    const totalBallots = filtered.map(r => r.total_valid_ballots || 0);
    const colors = filtered.map(r => getElectionColor(r.election_type));
    // Per-point click target: open the matching election results module.
    // Lokalni results carry kind + county + muni so the dropdowns can be
    // preselected (see izlNavigateTo / lokalniPreselect).
    const pointTargets = filtered.map(r => {
        const cat = electionTypeToCategory(r.election_type);
        if (!cat) return null;
        const t = { cat, year: r.year };
        if (cat === 'lokalni') {
            t.kind = r.lokalni_kind || null;
            t.countyId = r.county_id || null;
            t.municipalityId = r.municipality_id || null;
        }
        return t;
    });

    // Wider per-election spacing + horizontal scroll, set up before chart
    // creation so Chart.js sizes to the (potentially wider) inner element.
    applyChartScroll(canvas, labels.length, { height: 320 });

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, 'rgba(15, 52, 96, 0.25)');
    gradient.addColorStop(1, 'rgba(15, 52, 96, 0.02)');

    moduleCharts[modKey] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Udio glasova (%)',
                data: shareValues,
                borderColor: 'rgb(15, 52, 96)',
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                borderWidth: 3,
                pointBackgroundColor: colors.map(c => c.border),
                pointBorderColor: '#fff',
                pointBorderWidth: 2.5,
                pointRadius: 7,
                pointHoverRadius: 10,
                pointHoverBorderWidth: 3,
                pointStyle: 'circle',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            onClick: (evt, items) => {
                if (items && items.length) {
                    const t = pointTargets[items[0].index];
                    if (t) izlNavigateTo(t.cat, t.year, t);
                }
            },
            onHover: (evt, items) => {
                const hit = items && items.length && pointTargets[items[0].index];
                if (evt && evt.native) evt.native.target.style.cursor = hit ? 'pointer' : 'default';
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 13 },
                    padding: 14,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(ctx) {
                            const i = ctx.dataIndex;
                            return [
                                `Udio: ${shareValues[i]}%`,
                                `Glasovi: ${rawVotes[i].toLocaleString('hr-HR')}`,
                                `Ukupno glasača: ${totalBallots[i].toLocaleString('hr-HR')}`
                            ];
                        },
                        afterLabel: function(ctx) {
                            return pointTargets[ctx.dataIndex] ? '\nKlikni za otvaranje rezultata.' : '';
                        }
                    }
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: Math.min(Math.max(...shareValues) * 1.4, 100),
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { callback: v => formatPct(v, 0), font: { size: 12 } },
                    title: { display: true, text: 'Udio glasova (%)', font: { size: 12, weight: 'bold' }, color: '#6c757d' }
                },
                x: {
                    grid: { color: 'rgba(0,0,0,0.03)' },
                    ticks: { font: { size: 11 }, maxRotation: 45 }
                }
            },
            animation: { duration: 1000, easing: 'easeOutQuart' }
        }
    });
}

function renderMultiLineChart(panel, type) {
    const chartContainer = panel.querySelector('.chart-container');
    const canvas = panel.querySelector('.votes-chart');
    const modKey = panel.id;

    if (moduleCharts[modKey]) {
        moduleCharts[modKey].destroy();
        moduleCharts[modKey] = null;
    }

    const items = _compareItems[type];
    if (items.length === 0) {
        chartContainer.style.display = 'none';
        return;
    }

    const votesKey = type === 'person' ? 'candidate_votes' : 'total_votes';

    // A pre-2015 Sabor mandate has no preferential vote to plot — the ballot
    // had none — but dropping it would erase a term served from the chart
    // entirely. Keep it, at 0%, and say why in the tooltip.
    const plottable = r => r[votesKey] > 0 || r.mandate_only;

    // Build unified X-axis labels from all items
    const allLabelsSet = new Map(); // key -> display label
    items.forEach(item => {
        const filtered = filterResults(item.data.results, type).filter(plottable);
        filtered.forEach(r => {
            const key = `${r.election_type}|${r.date || r.year}|${r.round}|${r.district || ''}`;
            if (!allLabelsSet.has(key)) {
                let label = r.election_type.replace('izbori', '').trim();
                if (r.date) {
                    const d = new Date(r.date);
                    label += `\n${d.toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' })}`;
                } else {
                    label += ` ${r.year}`;
                }
                if (r.round > 1) label += ` (${r.round}. krug)`;
                if (r.district) label += `\n${r.district}`;
                allLabelsSet.set(key, {
                    label, date: r.date || `${r.year}`, round: r.round,
                    election_type: r.election_type, year: r.year,
                    lokalni_kind: r.lokalni_kind || null,
                    county_id: r.county_id || null,
                    municipality_id: r.municipality_id || null,
                });
            }
        });
    });

    // Sort labels by date
    const sortedKeys = [...allLabelsSet.entries()].sort((a, b) => {
        const da = a[1].date, db = b[1].date;
        if (da < db) return -1;
        if (da > db) return 1;
        return a[1].round - b[1].round;
    });
    const labels = sortedKeys.map(e => e[1].label);
    const labelKeys = sortedKeys.map(e => e[0]);
    // Per-x-position click target: same labels are shared across all compared
    // items, so clicking any circle at that x opens that election's results.
    const pointTargets = sortedKeys.map(e => {
        const cat = electionTypeToCategory(e[1].election_type);
        if (!cat) return null;
        const t = { cat, year: e[1].year };
        if (cat === 'lokalni') {
            t.kind = e[1].lokalni_kind || null;
            t.countyId = e[1].county_id || null;
            t.municipalityId = e[1].municipality_id || null;
        }
        return t;
    });

    if (labels.length === 0) {
        chartContainer.style.display = 'none';
        return;
    }

    chartContainer.style.display = 'block';

    // Build one dataset per item
    const datasets = items.map((item, i) => {
        const color = compareLineColors[i % compareLineColors.length];
        const filtered = filterResults(item.data.results, type).filter(plottable);

        // Map results to unified label positions
        const resultMap = {};
        const rankMap = {};
        filtered.forEach(r => {
            const key = `${r.election_type}|${r.date || r.year}|${r.round}|${r.district || ''}`;
            resultMap[key] = r.vote_share || 0;
            if (r.rank || r.won_seat || r.eu_mep || r.roles) rankMap[key] = { rank: r.rank, total: r.total_candidates_in_round, won_seat: r.won_seat, eu_mep: r.eu_mep, mandate_only: r.mandate_only, mandate_reason: r.mandate_reason, roles: r.roles };
        });

        const data = labelKeys.map(k => resultMap[k] ?? null);
        const ranks = labelKeys.map(k => rankMap[k] || null);

        // Per-point styling: gold for winner (rank=1), silver for runner-up
        // (rank=2), green for a Sabor seat, blue for a European Parliament seat.
        // A key Sabor office (PM, Speaker, deputy, Secretary) outranks all of
        // these: its point takes the office's colour and glows (roleGlowPlugin).
        const topRole = r => r && r.roles && r.roles.length ? SABOR_ROLE_STYLE[r.roles[0].role] : null;
        const pointBg = ranks.map(r => !r ? color : topRole(r) ? topRole(r).bg : (r.rank === 1 ? '#FFD700' : r.rank === 2 ? '#C0C0C0' : r.won_seat ? '#28a745' : r.eu_mep ? '#0d6efd' : color));
        const pointBorder = ranks.map(r => !r ? '#fff' : topRole(r) ? topRole(r).border : (r.rank === 1 ? '#B8860B' : r.rank === 2 ? '#808080' : r.won_seat ? '#166528' : r.eu_mep ? '#084298' : '#fff'));
        const pointRadii = ranks.map(r => !r ? 5 : topRole(r) ? (r.roles[0].role === 'pm' ? 10 : 9) : (r.rank === 1 ? 9 : r.rank === 2 ? 7 : r.won_seat ? 7 : r.eu_mep ? 7 : 5));

        return {
            label: item.name,
            data: data,
            borderColor: color,
            backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.1)'),
            fill: false,
            tension: 0.3,
            borderWidth: 2.5,
            pointBackgroundColor: pointBg,
            pointBorderColor: pointBorder,
            pointBorderWidth: 2,
            pointRadius: pointRadii,
            pointHoverRadius: pointRadii.map(r => r + 3),
            spanGaps: true,
            // A 100% share sits on the axis's top edge; unclipped (with the
            // layout padding below) its point is drawn whole, not halved.
            clip: false,
            _ranks: ranks,
        };
    });

    const allValues = datasets.flatMap(ds => ds.data.filter(v => v !== null));
    // Someone whose only plotted points are pre-2015 mandates sits entirely at
    // 0%; without a floor the y-axis would collapse to zero height.
    const peak = allValues.length > 0 ? Math.max(...allValues) : 0;
    const maxVal = peak > 0 ? peak : 100;

    // Wider per-election spacing + horizontal scroll, set up before chart
    // creation so Chart.js sizes to the (potentially wider) inner element.
    applyChartScroll(canvas, labels.length, { height: 320 });

    const ctx = canvas.getContext('2d');
    moduleCharts[modKey] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        plugins: [roleGlowPlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            // Room above the plot for the largest point (radius 9, 12 hovered).
            layout: { padding: { top: 14 } },
            interaction: { intersect: false, mode: 'index' },
            onClick: (evt, items_) => {
                if (items_ && items_.length) {
                    const t = pointTargets[items_[0].index];
                    if (t) izlNavigateTo(t.cat, t.year, t);
                }
            },
            onHover: (evt, items_) => {
                const hit = items_ && items_.length && pointTargets[items_[0].index];
                if (evt && evt.native) evt.native.target.style.cursor = hit ? 'pointer' : 'default';
            },
            plugins: {
                legend: {
                    display: items.length > 1,
                    position: 'top',
                    labels: { usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 12 } },
                },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 13 },
                    padding: 14,
                    cornerRadius: 8,
                    callbacks: {
                        afterLabel: function(ctx) {
                            const r = ctx.dataset._ranks && ctx.dataset._ranks[ctx.dataIndex];
                            if (!r) return '';
                            if (r.roles && r.roles.length) {
                                return r.roles.map(x => {
                                    const when = roleDatesText(x);
                                    return `${(SABOR_ROLE_STYLE[x.role] || {}).icon || ''} ${x.title}${when ? ' (' + when + ')' : ''}`;
                                });
                            }
                            if (r.rank === 1) return `🥇 Pobjednik (1. od ${r.total})`;
                            if (r.rank === 2) return `🥈 Drugoplasirani (2. od ${r.total})`;
                            if (r.won_seat && r.mandate_only) {
                                return '🟢 Osvojio mandat - ' + mandateReasonText(r).replace(/\.$/, '');
                            }
                            if (r.won_seat) return `🟢 Ušao u Sabor`;
                            if (r.eu_mep) return `🔵 Ušao u EU parlament`;
                            if (r.rank) return `${r.rank}. mjesto od ${r.total}`;
                            return '';
                        },
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: Math.min(maxVal * 1.4, 100),
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { callback: v => formatPct(v, 0), font: { size: 12 } },
                    title: { display: true, text: 'Udio glasova (%)', font: { size: 12, weight: 'bold' }, color: '#6c757d' }
                },
                x: {
                    grid: { color: 'rgba(0,0,0,0.03)' },
                    ticks: { font: { size: 11 }, maxRotation: 45 }
                }
            },
            animation: { duration: 800, easing: 'easeOutQuart' }
        }
    });
}

// HTML-returning versions for compare result cards
function renderPersonResultsHTML(results) {
    if (results.length === 0) return '<p class="text-muted">Nema izbornih podataka.</p>';
    return results.map(r => {
        const showListName = r.list_name && r.list_name.toUpperCase() !== (r._personFullName || '').toUpperCase();
        const cat = electionTypeToCategory(r.election_type);
        const lokAttrs = cat === 'lokalni'
            ? ` data-kind="${escapeHtml(r.lokalni_kind || '')}" data-county-id="${r.county_id || ''}" data-muni-id="${r.municipality_id || ''}"`
            : '';
        const linkAttrs = cat
            ? `class="result-badges result-badges-link" data-cat="${cat}" data-year="${r.year}"${lokAttrs} role="button" tabindex="0" title="Otvori ${escapeHtml(r.election_type)} ${r.year}."`
            : `class="result-badges"`;
        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div ${linkAttrs}>
                    <span class="badge ${electionBadgeColor(r.election_type)} badge-election me-1">${r.election_type}</span>
                    <span class="badge bg-dark badge-election">${r.date ? new Date(r.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' }) : r.year}</span>
                    ${r.round > 1 ? `<span class="badge bg-warning text-dark badge-election">${r.round}. krug</span>` : ''}
                    ${rankBadgeHtml(r)}
                    ${r.list_holder ? '<span class="badge bg-secondary badge-election" title="Prvi na listi koju je predvodio">Nositelj liste</span>' : ''}
                </div>
                <div class="text-end">
                    ${r.vote_share ? `<div class="vote-number">${formatPct(r.vote_share)}</div><small class="text-muted">udio glasova</small>` : ''}
                </div>
            </div>
            <div class="mt-2">
                ${showListName ? `<div class="fw-semibold">${r.list_name}</div>` : ''}
                <div class="d-flex gap-3 flex-wrap">
                    ${r.district ? `<small class="text-muted"><i class="bi bi-geo-alt me-1"></i>${r.district}</small>` : ''}
                    ${r.position ? `<small class="text-muted"><i class="bi bi-list-ol me-1"></i>Pozicija: ${r.position}</small>` : ''}
                    ${r.note ? `<small class="text-muted"><i class="bi bi-info-circle me-1"></i>${escapeHtml(r.note)}</small>` : ''}
                </div>
            </div>
            <hr class="my-2" style="opacity: 0.1;">
            <div class="d-flex gap-3 flex-wrap">
                ${/* A mandate won before preferential voting has no personal
                      result, so this row would otherwise be an empty strip
                      under a divider. Say why instead. */ ''}
                ${r.mandate_only ? `<small class="text-muted fst-italic"><i class="bi bi-info-circle me-1"></i>${mandateReasonText(r)}</small>` : ''}
                ${r.list_holder ? listHolderHtml(r) : ''}
                ${r.candidate_votes ? `<small class="text-muted"><i class="bi bi-person-check me-1"></i>Glasovi: <strong>${formatNumber(r.candidate_votes)}</strong></small>` : ''}
                ${r.total_valid_ballots ? `<small class="text-muted"><i class="bi bi-people me-1"></i>Ukupno glasača: <strong>${formatNumber(r.total_valid_ballots)}</strong></small>` : ''}
            </div>
        </div>`;
    }).join('');
}

function electionBadgeColor(type) {
    const colors = {
        'Predsjednički izbori': 'bg-danger',
        'Parlamentarni izbori': 'bg-primary',
        'Izbori za EU parlament': 'bg-info',
        'Lokalni izbori': 'bg-success',
    };
    for (const [key, cls] of Object.entries(colors)) {
        if (type.toLowerCase().includes(key.toLowerCase().split(' ')[0])) return cls;
    }
    return 'bg-secondary';
}

// Map an election_type string (as stored in the DB / returned by the API) to
// the category key used by izlNavigateTo() and the results-* modules.
function electionTypeToCategory(type) {
    const t = (type || '').toLowerCase();
    // The Sabor's own chambers (1990's three, the Županijski dom) before the
    // checks below, which would read their "vijeće" / "župan" as local.
    if (t.endsWith('sabora')) return 'sabor';
    if (t.includes('predsjednič')) return 'predsjednicki';
    if (t.includes('europski') || t.includes('eu parlament')) return 'eu';
    if (t.includes('parlamentarni') || t === 'sabor') return 'sabor';
    if (
        t.includes('župan') || t.includes('načelnik') || t.includes('gradonačelnik') ||
        t.includes('vijeće') || t.includes('skupština') || t.includes('lokal')
    ) return 'lokalni';
    return null;
}

function formatNumber(n) {
    return n.toLocaleString('hr-HR');
}

function formatPct(n, decimals = 1) {
    if (n === null || n === undefined || isNaN(n)) return '';
    return Number(n).toLocaleString('hr-HR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    }) + '%';
}

// A mandate with no personal vote attached. The Sabor's reason is that
// preferential voting arrived only in 2015; the Županijski dom never had it,
// having been abolished in 2001, so the 2015 date would make no sense there.
function mandateReasonText(r) {
    if (r.mandate_reason === 'sabor' || !r.mandate_reason) {
        return 'Preferencijski glasovi uvedeni su tek 2015., pa za ovaj mandat nema osobnog rezultata.';
    }
    return 'Objavljeni su samo rezultati po listama, pa za ovaj mandat nema osobnog rezultata.';
}

// Before 2009 the council (or county assembly) chose the executive after the
// election, so these years name only who led each list.
const LIST_HOLDER_NOTE = 'Prije 2009. načelnike, gradonačelnike i župane biralo je predstavničko tijelo nakon izbora; nositelj liste nije nužno preuzeo tu dužnost.';

function listHolderHtml(r) {
    const place = r.list_place ? `${r.list_place}. od ${r.lists_in_race} lista, ` : '';
    return `<small class="text-muted"><i class="bi bi-list-ol me-1"></i>Lista: <strong>${place}${formatNumber(r.list_votes)} glasova (${formatPct(r.list_share)})</strong></small>
        ${r.year < 2009 ? `<small class="text-muted fst-italic"><i class="bi bi-info-circle me-1"></i>${LIST_HOLDER_NOTE}</small>` : ''}`;
}

// Key offices of a Sabor term: badge class, emoji and chart-point colours.
const SABOR_ROLE_STYLE = {
    pm:        { cls: 'role-pm',        icon: '👑', bg: '#FFD700', border: '#B8860B', glow: 'rgba(255, 200, 0, 0.9)' },
    deputy_pm: { cls: 'role-deputy-pm', icon: '⭐', bg: '#F2D675', border: '#C9A227', glow: 'rgba(255, 205, 60, 0.55)' },
    minister:  { cls: 'role-minister',  icon: '💼', bg: '#2aa198', border: '#16706a', glow: 'rgba(42, 161, 152, 0.55)' },
    speaker:   { cls: 'role-speaker',   icon: '🏛️', bg: '#6f42c1', border: '#45207d', glow: 'rgba(111, 66, 193, 0.7)' },
    deputy:    { cls: 'role-deputy',    icon: '🔷', bg: '#a07fe0', border: '#6f42c1', glow: 'rgba(160, 127, 224, 0.6)' },
    secretary: { cls: 'role-secretary', icon: '📋', bg: '#627891', border: '#4c5f74', glow: 'rgba(98, 120, 145, 0.6)' },
};

// Redraws a key-office point with a soft halo of its colour (Chart.js points
// have no shadow option). Reads the per-point roles a dataset carries in _ranks.
const roleGlowPlugin = {
    id: 'roleGlow',
    afterDatasetsDraw(chart) {
        const { ctx } = chart;
        chart.data.datasets.forEach((ds, di) => {
            const meta = chart.getDatasetMeta(di);
            if (meta.hidden || !ds._ranks) return;
            ds._ranks.forEach((r, i) => {
                if (!r || !r.roles || !r.roles.length) return;
                const pt = meta.data[i];
                if (!pt || pt.skip || ds.data[i] == null) return;
                const s = SABOR_ROLE_STYLE[r.roles[0].role];
                if (!s) return;
                const radius = pt.options ? pt.options.radius : 9;
                ctx.save();
                ctx.shadowColor = s.glow;
                ctx.shadowBlur = r.roles[0].role === 'pm' ? 18 : 12;
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
                ctx.fillStyle = s.bg;
                ctx.fill();
                ctx.lineWidth = 2;
                ctx.strokeStyle = s.border;
                ctx.stroke();
                ctx.restore();
            });
        });
    },
};

function roleDatesText(x) {
    const fmt = d => { const [y, m, dd] = d.split('-'); return `${+dd}. ${+m}. ${y}.`; };
    if (x.start && x.end) return `${fmt(x.start)} – ${fmt(x.end)}`;
    if (x.start) return `od ${fmt(x.start)}`;
    if (x.end) return `do ${fmt(x.end)}`;
    return '';
}

function roleBadgesHtml(r) {
    if (!r || !r.roles) return '';
    return r.roles.map(x => {
        const s = SABOR_ROLE_STYLE[x.role] || SABOR_ROLE_STYLE.secretary;
        const when = roleDatesText(x);
        return `<span class="badge rank-badge ${s.cls}" title="${escapeHtml(x.title)}${when ? ' · ' + when : ''}">${s.icon} ${escapeHtml(x.title)}</span>`;
    }).join('');
}

function rankBadgeHtml(r) {
    return roleBadgesHtml(r) + seatOrRankBadgeHtml(r);
}

function seatOrRankBadgeHtml(r) {
    if (!r) return '';
    if (r.eu_mep) {
        const grp = r.eu_group ? ` - ${r.eu_group}` : '';
        return `<span class="badge rank-badge rank-eu" title="Zastupnik u Europskom parlamentu (saziv ${r.year}.)${escapeHtml(grp)}">🔵 Ušao u EU parlament</span>`;
    }
    if (r.won_seat) {
        // The Županijski dom was a chamber of the Sabor, not the Sabor, and a
        // badge reading "Ušao u Sabor" on a 1997 upper-house mandate reads as
        // the lower house.
        const house = /Županijski/.test(r.election_type || '') ? 'Županijski dom'
            : /Društveno-političko/.test(r.election_type || '') ? 'DPV Sabora'
            : /Vijeće općina/.test(r.election_type || '') ? 'Vijeće općina'
            : /Vijeće udruženog rada/.test(r.election_type || '') ? 'Vijeće udruženog rada' : 'Sabor';
        return `<span class="badge rank-badge rank-seat" title="Osvojio mandat - ušao u ${house}">🟢 Ušao u ${house}</span>`;
    }
    if (!r.rank) return '';
    const total = r.total_candidates_in_round || '';
    if (r.rank === 1) {
        return `<span class="badge rank-badge rank-winner" title="Pobjednik (1. od ${total})">🥇 Pobjednik</span>`;
    }
    if (r.rank === 2) {
        return `<span class="badge rank-badge rank-runner-up" title="Drugoplasirani (2. od ${total})">🥈 Drugoplasirani</span>`;
    }
    return '';
}

function renderPersonResults(container, results) {
    if (results.length === 0) {
        container.innerHTML = '<p class="text-muted">Nema izbornih podataka.</p>';
        return;
    }

    container.innerHTML = results.map(r => {
        const showListName = r.list_name && r.list_name.toUpperCase() !== (r._personFullName || '').toUpperCase();
        const cat = electionTypeToCategory(r.election_type);
        const lokAttrs = cat === 'lokalni'
            ? ` data-kind="${escapeHtml(r.lokalni_kind || '')}" data-county-id="${r.county_id || ''}" data-muni-id="${r.municipality_id || ''}"`
            : '';
        const linkAttrs = cat
            ? `class="result-badges result-badges-link" data-cat="${cat}" data-year="${r.year}"${lokAttrs} role="button" tabindex="0" title="Otvori ${escapeHtml(r.election_type)} ${r.year}."`
            : `class="result-badges"`;
        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div ${linkAttrs}>
                    <span class="badge ${electionBadgeColor(r.election_type)} badge-election me-1">${r.election_type}</span>
                    <span class="badge bg-dark badge-election">${r.date ? new Date(r.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' }) : r.year}</span>
                    ${r.round > 1 ? `<span class="badge bg-warning text-dark badge-election">${r.round}. krug</span>` : ''}
                    ${rankBadgeHtml(r)}
                    ${r.list_holder ? '<span class="badge bg-secondary badge-election" title="Prvi na listi koju je predvodio">Nositelj liste</span>' : ''}
                </div>
                <div class="text-end">
                    ${r.vote_share ? `<div class="vote-number">${formatPct(r.vote_share)}</div><small class="text-muted">udio glasova</small>` : ''}
                </div>
            </div>
            <div class="mt-2">
                ${showListName ? `<div class="fw-semibold">${r.list_name}</div>` : ''}
                <div class="d-flex gap-3 flex-wrap">
                    ${r.district ? `<small class="text-muted"><i class="bi bi-geo-alt me-1"></i>${r.district}</small>` : ''}
                    ${r.position ? `<small class="text-muted"><i class="bi bi-list-ol me-1"></i>Pozicija: ${r.position}</small>` : ''}
                    ${r.note ? `<small class="text-muted"><i class="bi bi-info-circle me-1"></i>${escapeHtml(r.note)}</small>` : ''}
                </div>
            </div>
            <hr class="my-2" style="opacity: 0.1;">
            <div class="d-flex gap-3 flex-wrap">
                ${/* A mandate won before preferential voting has no personal
                      result, so this row would otherwise be an empty strip
                      under a divider. Say why instead. */ ''}
                ${r.mandate_only ? `<small class="text-muted fst-italic"><i class="bi bi-info-circle me-1"></i>${mandateReasonText(r)}</small>` : ''}
                ${r.list_holder ? listHolderHtml(r) : ''}
                ${r.candidate_votes ? `<small class="text-muted"><i class="bi bi-person-check me-1"></i>Glasovi: <strong>${formatNumber(r.candidate_votes)}</strong></small>` : ''}
                ${r.total_valid_ballots ? `<small class="text-muted"><i class="bi bi-people me-1"></i>Ukupno glasača: <strong>${formatNumber(r.total_valid_ballots)}</strong></small>` : ''}
                ${r.list_votes && r.list_votes !== r.candidate_votes && !r.list_holder ? `<small class="text-muted"><i class="bi bi-list-ul me-1"></i>Glasovi za listu: <strong>${formatNumber(r.list_votes)}</strong></small>` : ''}
            </div>
        </div>`;
    }).join('');
}

// Station winner chart
let stationWinnerChartInstance = null;

function renderStationWinnerChart(elections) {
    const chartCard = document.getElementById('stationWinnerChartCard');
    const canvas = document.getElementById('stationWinnerChart');

    if (stationWinnerChartInstance) {
        stationWinnerChartInstance.destroy();
        stationWinnerChartInstance = null;
    }

    if (!elections || elections.length === 0) {
        chartCard.style.display = 'none';
        return;
    }

    // For each election, find the winner (top candidate or top list) — chronological order
    const winners = elections.slice().reverse().map(el => {
        const hasCandidates = el.top_candidates && el.top_candidates.length > 0;
        const items = hasCandidates ? el.top_candidates : el.top_lists;
        if (items.length === 0) return null;

        const winner = items[0]; // already sorted desc by votes from API
        const votePct = el.valid_ballots > 0 ? (winner.votes / el.valid_ballots) * 100 : 0;

        // Date first, then election type
        let datePart = el.date
            ? new Date(el.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' })
            : `${el.year}`;
        let typePart = el.election_type.replace('izbori', '').trim();
        if (el.round > 1) typePart += ` (${el.round}. krug)`;

        const cat = electionTypeToCategory(el.election_type);
        return {
            label: `${datePart}\n${typePart}`,
            name: winner.name,
            holder: winner.holder ? winner.holder.name : null,     // 2001-2009 councils
            votes: winner.votes,
            votePct,
            electionType: el.election_type,
            // Where a click on the point leads: that election's results page,
            // scoped to this place for a local one.
            target: cat ? { cat, year: el.year, kind: el.lokalni_kind || null,
                            countyId: el.county_id || null, municipalityId: el.municipality_id || null } : null,
        };
    }).filter(Boolean);

    if (winners.length === 0) {
        chartCard.style.display = 'none';
        return;
    }

    chartCard.style.display = 'block';

    // Multi-line labels: date, election type, winner name (truncated)
    const labels = winners.map(w => {
        const lines = w.label.split('\n');
        const shortName = w.name.length > 18 ? w.name.substring(0, 16) + '...' : w.name;
        lines.push(shortName);
        return lines;
    });
    const pctValues = winners.map(w => w.votePct);
    const colors = winners.map(w => getElectionColor(w.electionType));
    const winnerNames = winners.map(w => w.name);
    const winnerVotes = winners.map(w => w.votes);

    // Wider per-election spacing + horizontal scroll, set up before chart
    // creation so Chart.js sizes to the (potentially wider) inner element.
    applyChartScroll(canvas, labels.length, { height: 230 });

    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, 'rgba(15, 52, 96, 0.25)');
    gradient.addColorStop(1, 'rgba(15, 52, 96, 0.02)');

    stationWinnerChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pobjednik - udio glasova (%)',
                data: pctValues,
                borderColor: 'rgb(15, 52, 96)',
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                borderWidth: 3,
                pointBackgroundColor: colors.map(c => c.border),
                pointBorderColor: '#fff',
                pointBorderWidth: 2.5,
                pointRadius: 7,
                pointHoverRadius: 10,
                pointHoverBorderWidth: 3,
                pointStyle: 'circle',
                // A 100% winner sits on the axis's top edge; unclipped (with
                // the layout padding below) its point is drawn whole.
                clip: false,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            onClick: (evt, items) => {
                const t = items && items.length && winners[items[0].index].target;
                if (t) izlNavigateTo(t.cat, t.year, t);
            },
            onHover: (evt, items) => {
                const hit = items && items.length && winners[items[0].index].target;
                if (evt && evt.native) evt.native.target.style.cursor = hit ? 'pointer' : 'default';
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(26, 26, 46, 0.95)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 13 },
                    padding: 14,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        footer: ctx => ctx.length && winners[ctx[0].dataIndex].target ? 'Klikni za otvaranje rezultata.' : '',
                        label: function(ctx) {
                            const i = ctx.dataIndex;
                            // Chart.js draws each line on one row, newlines and
                            // all, so a coalition (2025 joins its parties with
                            // newlines, 2021 with commas) ran off the screen: one
                            // party per line, a long name wrapped at word breaks.
                            const parties = winnerNames[i].split(/\s*\n\s*/).flatMap(p =>
                                p.split(/,\s+/).map((x, j, all) => j < all.length - 1 ? x + ',' : x));
                            const nameLines = parties.flatMap(part => {
                                const out = [];
                                for (const word of part.split(' ')) {
                                    const last = out.length - 1;
                                    if (last >= 0 && (out[last] + ' ' + word).length <= 45) out[last] += ' ' + word;
                                    else out.push(word);
                                }
                                return out;
                            });
                            return [
                                `Pobjednik: ${nameLines[0]}`,
                                ...nameLines.slice(1).map(l => `    ${l}`),
                                ...(winners[i].holder ? [`Nositelj liste: ${winners[i].holder}`] : []),
                                `Udio: ${formatPct(pctValues[i])}`,
                                `Glasovi: ${winnerVotes[i].toLocaleString('hr-HR')}`,
                            ];
                        }
                    }
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: Math.min(Math.max(...pctValues) * 1.4, 100),
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { callback: v => formatPct(v, 0), font: { size: 12 } },
                    title: { display: true, text: 'Udio glasova pobjednika (%)', font: { size: 12, weight: 'bold' }, color: '#6c757d' }
                },
                x: {
                    grid: { color: 'rgba(0,0,0,0.03)' },
                    ticks: {
                        font: { size: 10 },
                        maxRotation: 90,
                        minRotation: 90,
                    }
                }
            },
            layout: {
                // top: room for the largest point (radius 10 hovered, 3px border).
                padding: { top: 14, bottom: 10 }
            },
            animation: { duration: 1000, easing: 'easeOutQuart' }
        }
    });
}

// Station map (Google Maps embed)
function renderStationMap(data) {
    const mapCard = document.getElementById('stationMapCard');
    const iframe = document.getElementById('stationMap');

    if (!data.address) {
        mapCard.style.display = 'none';
        return;
    }

    const parts = [data.address, data.municipality, 'Croatia'].filter(Boolean);
    const query = parts.join(', ');

    mapCard.style.display = 'block';
    iframe.src = `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
}

const barColors = [
    'rgba(13, 110, 253, 0.8)',
    'rgba(220, 53, 69, 0.75)',
    'rgba(25, 135, 84, 0.75)',
    'rgba(255, 193, 7, 0.85)',
    'rgba(13, 202, 240, 0.75)',
    'rgba(111, 66, 193, 0.75)',
    'rgba(253, 126, 20, 0.75)',
    'rgba(102, 16, 242, 0.75)',
    'rgba(214, 51, 132, 0.75)',
    'rgba(32, 201, 151, 0.75)',
    'rgba(108, 117, 125, 0.75)',
    'rgba(52, 58, 64, 0.75)',
    'rgba(255, 140, 66, 0.75)',
    'rgba(0, 123, 167, 0.75)',
    'rgba(176, 65, 62, 0.75)',
    'rgba(80, 150, 50, 0.75)',
];

function renderStationResults(container, elections) {
    stationCharts.forEach(c => c.destroy());
    stationCharts = [];

    if (elections.length === 0) {
        container.innerHTML = '<p class="text-muted">Nema izbornih podataka za ovo biračko mjesto.</p>';
        return;
    }

    container.innerHTML = elections.map((el, idx) => {
        const turnoutPct = el.registered_voters > 0
            ? (el.ballots_cast / el.registered_voters) * 100
            : 0;
        // 2001-2009 councils: each list's leader (before 2009 there was no executive vote).
        const top = !(el.top_candidates && el.top_candidates.length) && el.top_lists && el.top_lists[0];
        const holderLine = top && top.holder ? `
            <div class="mt-2" style="font-size:0.85rem;">
                <i class="bi bi-person-badge me-1"></i>Nositelj liste s najviše glasova: <strong>${personLinkHtml(top.holder.name, top.holder.person_id)}</strong>
                ${el.year < 2009 ? `<div class="text-muted fst-italic" style="font-size:0.8rem;">* ${LIST_HOLDER_NOTE}</div>` : ''}
            </div>` : '';

        return `
        <div class="card result-card mb-3 p-3">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
                <div>
                    <span class="badge ${electionBadgeColor(el.election_type)} badge-election me-1">${el.election_type}</span>
                    <span class="badge bg-dark badge-election">${el.date ? new Date(el.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' }) : el.year}</span>
                    ${el.round > 1 ? `<span class="badge bg-warning text-dark badge-election">${el.round}. krug</span>` : ''}
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
            <div class="bar-chart-area" id="barChart_${idx}" data-election-idx="${idx}"></div>
            <div class="d-flex justify-content-between align-items-center mt-1">
                <div class="bar-drag-hint"><i class="bi bi-arrows-move me-1"></i>Povuci stupac na drugi za spajanje rezultata</div>
                <button class="btn btn-outline-secondary bar-reset-btn" onclick="resetBarChart(${idx})" style="display:none;" id="resetBtn_${idx}">
                    <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
                </button>
            </div>
            ${holderLine}
        </div>`;
    }).join('');

    // Clear only station-module keys (numeric), keep compare keys (string)
    if (!window._electionBarData) window._electionBarData = {};
    Object.keys(window._electionBarData).forEach(k => {
        if (!isNaN(Number(k))) delete window._electionBarData[k];
    });

    elections.forEach((el, idx) => {
        const hasCandidates = el.top_candidates && el.top_candidates.length > 0;
        const items = hasCandidates ? el.top_candidates : el.top_lists;
        if (items.length === 0) return;

        const originalItems = items.map((it, i) => ({
            name: it.name,
            votes: it.votes,
            color: barColors[i % barColors.length],
            origNames: [it.name],
            personId: it.person_id || null,
        }));

        window._electionBarData[idx] = {
            original: JSON.parse(JSON.stringify(originalItems)),
            current: originalItems,
            validBallots: el.valid_ballots,
            // Candidates are people: their names open the politician page.
            kind: hasCandidates ? 'person' : 'list',
        };

        buildBarChart(idx);
    });
}

function buildBarChart(idx) {
    const chartArea = document.getElementById(`barChart_${idx}`);
    const data = window._electionBarData[idx];
    if (!chartArea || !data) return;

    const items = data.current;
    const maxVotes = Math.max(...items.map(it => it.votes));

    chartArea.innerHTML = items.map((it, i) => {
        const pct = maxVotes > 0 ? (it.votes / maxVotes) * 100 : 0;
        const votePct = data.validBallots > 0 ? (it.votes / data.validBallots) * 100 : 0;
        const displayName = it.name.length > 40 ? it.name.substring(0, 37) + '...' : it.name;
        const isMerged = it.origNames && it.origNames.length > 1;

        // Make the label a clickable jump to the politician page when this
        // bar represents a single (unmerged) person.
        const isClickablePerson = data.kind === 'person' && it.origNames && it.origNames.length === 1;
        // A merged bar lists every name in full, one per line, in a smaller font,
        // instead of cutting "A + B + C" off at 40 characters.
        const labelHtml = isMerged
            ? `<div class="bar-label bar-label-merged">${it.origNames.map((n, k) =>
                  `<span>${k > 0 ? '+ ' : ''}${n}</span>`).join('')}</div>`
            : isClickablePerson
            ? `<div class="bar-label bar-label-link" data-person-name="${it.name.replace(/"/g, '&quot;')}"${it.personId ? ` data-person-id="${it.personId}"` : ''} title="Otvori stranicu političara: ${it.name.replace(/"/g, '&quot;')}">${displayName}</div>`
            : `<div class="bar-label">${displayName}</div>`;

        return `
        <div class="bar-row" draggable="true" data-chart="${idx}" data-bar="${i}"
             title="${it.name}: ${formatNumber(it.votes)} glasova (${formatPct(votePct)})">
            ${labelHtml}
            <div class="bar-track">
                <div class="bar-fill" style="width: ${Math.max(pct, 12)}%; background: ${it.color};">
                    <span class="bar-value">${formatNumber(it.votes)} (${formatPct(votePct)})</span>
                </div>
            </div>
        </div>`;
    }).join('');

    // Set up drag-and-drop
    const rows = chartArea.querySelectorAll('.bar-row');
    rows.forEach(row => {
        row.addEventListener('dragstart', onBarDragStart);
        row.addEventListener('dragend', onBarDragEnd);
        row.addEventListener('dragover', onBarDragOver);
        row.addEventListener('dragenter', onBarDragEnter);
        row.addEventListener('dragleave', onBarDragLeave);
        row.addEventListener('drop', onBarDrop);
    });
}

let dragSource = null;

function onBarDragStart(e) {
    dragSource = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', `${this.dataset.chart}:${this.dataset.bar}`);
}

function onBarDragEnd(e) {
    this.classList.remove('dragging');
    document.querySelectorAll('.bar-row.drag-over').forEach(el => el.classList.remove('drag-over'));
    dragSource = null;
}

function onBarDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function onBarDragEnter(e) {
    e.preventDefault();
    if (this !== dragSource && this.dataset.chart === dragSource?.dataset.chart) {
        this.classList.add('drag-over');
    }
}

function onBarDragLeave(e) {
    this.classList.remove('drag-over');
}

function onBarDrop(e) {
    e.preventDefault();
    this.classList.remove('drag-over');

    const rawData = e.dataTransfer.getData('text/plain');
    // Format: "chartKey:barIdx" — chartKey can be number or string like "cmp_123_0"
    const lastColon = rawData.lastIndexOf(':');
    const srcChartRaw = rawData.substring(0, lastColon);
    const srcBar = parseInt(rawData.substring(lastColon + 1));
    const srcChart = isNaN(Number(srcChartRaw)) ? srcChartRaw : Number(srcChartRaw);

    const tgtChartRaw = this.dataset.chart;
    const tgtChart = isNaN(Number(tgtChartRaw)) ? tgtChartRaw : Number(tgtChartRaw);
    const tgtBar = parseInt(this.dataset.bar);

    if (srcChart !== tgtChart || srcBar === tgtBar) return;

    const data = window._electionBarData[srcChart];
    if (!data) return;

    const items = data.current;
    const src = items[srcBar];
    const tgt = items[tgtBar];

    // Combine: merge src into tgt
    tgt.votes += src.votes;
    tgt.name = [...tgt.origNames, ...src.origNames].join(' + ');
    tgt.origNames = [...tgt.origNames, ...src.origNames];

    // Remove src
    items.splice(srcBar, 1);

    // Rebuild chart
    buildBarChart(srcChart);

    // Flash the combined row
    const chartArea = document.getElementById(`barChart_${srcChart}`);
    const newIdx = items.indexOf(tgt);
    const rows = chartArea.querySelectorAll('.bar-row');
    if (rows[newIdx]) rows[newIdx].classList.add('combined');

    // Show reset button
    document.getElementById(`resetBtn_${srcChart}`).style.display = 'inline-block';
}

function resetBarChart(idx) {
    const data = window._electionBarData[idx];
    if (!data) return;

    data.current = JSON.parse(JSON.stringify(data.original));
    buildBarChart(idx);
    document.getElementById(`resetBtn_${idx}`).style.display = 'none';
}
