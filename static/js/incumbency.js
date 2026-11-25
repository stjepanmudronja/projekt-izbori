// Ponovni izbor (Analitika): do načelnici, gradonačelnici and župani win again?
// /api/analytics/incumbency. Part of the site script, split from
// templates/index.html; the files load in the order index.html lists them and
// share one global scope.

const INC_COLORS = { won: '#0c8599', lost: '#e8590c', did_not_run: '#adb5bd' };
const INC_KIND_LABEL = { sve: 'svi', opcina: 'načelnici', grad: 'gradonačelnici', zupanija: 'župani' };
const _inc = { ready: false, data: null, kind: 'sve', chart: null, termsChart: null, county: null };
// Map: re-election rate, one hue light -> dark (the chart's "won" teal).
const INC_MAP_LO = [227, 244, 246], INC_MAP_HI = [8, 92, 107], INC_MAP_NONE = '#e9ecef';

const incPct = (a, b) => b ? (a / b * 100).toLocaleString('hr-HR', { maximumFractionDigits: 0 }) + ' %' : '–';
const incShare = v => v == null ? '–' : v.toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';

async function initIncumbency() {
    if (_inc.ready) return;
    _inc.ready = true;
    const spinner = document.getElementById('incSpinner');
    spinner.classList.add('show');
    try {
        _inc.data = await fetch('/api/analytics/incumbency').then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    document.getElementById('incArea').style.display = '';
    document.getElementById('incKind').addEventListener('click', e => {
        const b = e.target.closest('[data-inc-kind]');
        if (!b) return;
        _inc.kind = b.dataset.incKind;
        document.querySelectorAll('#incKind button').forEach(x => x.classList.toggle('active', x === b));
        renderIncumbency();
    });
    const sel = document.getElementById('incYear');
    sel.innerHTML = _inc.data.per_year.map(y => y.year).reverse().map(y => `<option value="${y}">${y}.</option>`).join('');
    sel.addEventListener('change', renderIncDefeated);
    document.getElementById('incSearch').addEventListener('input', renderIncLong);
    const years = _inc.data.per_year.map(y => y.year).reverse();
    const cy = document.getElementById('incCountyYear');
    cy.innerHTML = years.map(y => `<option value="${y}">${y}.</option>`).join('')
        + `<option value="all">Svi izbori ${years[years.length - 1]}.–${years[0]}.</option>`;
    cy.addEventListener('change', renderIncCounties);
    const close = document.getElementById('incCloseYear');
    close.innerHTML = years.map(y => `<option value="${y}">${y}.</option>`).join('');
    close.addEventListener('change', renderIncClose);
    document.getElementById('incCounties').addEventListener('click', e => {
        const tr = e.target.closest('[data-county]');
        if (tr) setIncCounty(tr.dataset.county);
    });
    document.getElementById('incArea').addEventListener('click', e => {
        if (e.target.closest('.inc-county-filter .badge')) setIncCounty(null);
    });
    await loadIncMap();
    renderIncumbency();
}

function renderIncumbency() {
    renderIncTiles();
    renderIncChart();
    renderIncTerms();
    renderIncCounties();
    renderIncClose();
    renderIncDefeated();
    renderIncLong();
}

// ---- By county: map + table; a click narrows the lists below to that county ----
const incCountyName = code => docPartyCase(_inc.data.counties[code] || '');
// In the table and the filter badge: "Splitsko-dalmatinska" (every row is a županija).
const incCountyShort = code => incCountyName(code).replace(/ županija$/, '');
const incInCounty = d => !_inc.county || d.county === _inc.county;
const incOfKind = d => _inc.kind === 'sve' || d.kind === _inc.kind;

async function loadIncMap() {
    const holder = document.getElementById('incMap');
    try {
        holder.innerHTML = await fetch('/static/croatia_map.svg').then(r => r.text());
    } catch (e) {
        return;                     // the table still has every figure
    }
    const svg = holder.querySelector('svg');
    svg.querySelectorAll('style, title').forEach(x => x.remove());   // its global "path" rule would leak
    svg.removeAttribute('width');
    svg.removeAttribute('height');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Karta županija: udio ponovno izabranih');
    const tip = document.getElementById('incMapTip');
    const wrap = holder.parentElement;
    svg.querySelectorAll('path[id^="HR-"]').forEach(path => {
        const code = path.id.slice(3);
        path.addEventListener('mousemove', e => {
            const c = (incCountyCounts()[code] || {})[_inc.kind];
            const box = wrap.getBoundingClientRect();
            tip.innerHTML = `<b>${escapeHtml(incCountyName(code))}</b><br>` + (c && c.races
                ? `Ponovno izabrani: ${incPct(c.won, c.won + c.lost)} (${c.won} od ${c.won + c.lost})<br>Izgubili: ${c.lost} · nisu se kandidirali: ${c.did_not_run}<br>${c.races} mjesta`
                : 'Nema takvih izbora');
            tip.style.display = 'block';
            tip.style.left = Math.min(e.clientX - box.left + 14, box.width - tip.offsetWidth - 4) + 'px';
            tip.style.top = (e.clientY - box.top + 14) + 'px';
        });
        path.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
        path.addEventListener('click', () => setIncCounty(code));
    });
}

// {code: {kind: counts}} for the year picked, or summed over every election.
function incCountyCounts() {
    const year = document.getElementById('incCountyYear').value;
    const byCounty = _inc.data.by_county;
    if (year !== 'all') return byCounty[year] || {};
    const out = {};
    Object.values(byCounty).forEach(per => Object.entries(per).forEach(([code, kinds]) => {
        Object.entries(kinds).forEach(([kind, c]) => {
            const t = ((out[code] = out[code] || {})[kind] = out[code][kind] || { races: 0, won: 0, won_first_round: 0, lost: 0, did_not_run: 0 });
            Object.keys(t).forEach(k => { t[k] += c[k]; });
        });
    }));
    return out;
}

const incRate = c => c && c.won + c.lost ? c.won / (c.won + c.lost) * 100 : null;
function incMapColor(rate, lo, hi) {
    if (rate == null) return INC_MAP_NONE;
    const t = hi > lo ? Math.max(0, Math.min(1, (rate - lo) / (hi - lo))) : 1;
    return `rgb(${INC_MAP_LO.map((v, i) => Math.round(v + (INC_MAP_HI[i] - v) * t)).join(',')})`;
}

function renderIncCounties() {
    const counts = incCountyCounts();
    const codes = Object.keys(_inc.data.counties).sort();
    const rows = codes.map(code => ({ code, c: (counts[code] || {})[_inc.kind] || null }))
        .map(r => ({ ...r, rate: incRate(r.c) }));
    const rates = rows.map(r => r.rate).filter(v => v != null);
    const lo = rates.length ? Math.floor(Math.min(...rates) / 5) * 5 : 0;
    const hi = rates.length ? Math.max(lo + 5, Math.ceil(Math.max(...rates) / 5) * 5) : 100;
    rows.forEach(r => { r.color = incMapColor(r.rate, lo, hi); });

    document.querySelectorAll('#incMap path[id^="HR-"]').forEach(path => {
        const r = rows.find(x => x.code === path.id.slice(3));
        path.style.fill = r ? r.color : INC_MAP_NONE;
        path.classList.toggle('selected', path.id.slice(3) === _inc.county);
    });
    const grad = [0, .5, 1].map(t => incMapColor(lo + (hi - lo) * t, lo, hi)).join(',');
    document.getElementById('incMapLegend').innerHTML =
        `<span>${lo} %</span><span class="bar" style="background:linear-gradient(90deg,${grad})"></span><span>${hi} %</span>`
        + `<span class="none"></span><span>nema takvih izbora</span>`;

    rows.sort((a, b) => (b.rate ?? -1) - (a.rate ?? -1) || incCountyName(a.code).localeCompare(incCountyName(b.code), 'hr'));
    document.getElementById('incCounties').innerHTML = rows.map(r => `<tr data-county="${r.code}" class="${r.code === _inc.county ? 'selected' : ''}" title="Prikaži samo ovu županiju u popisima ispod">
            <td><span class="inc-swatch" style="background:${r.color}"></span>${escapeHtml(incCountyShort(r.code))}</td>
            <td class="text-end">${r.c && r.c.won + r.c.lost ? `<b>${incPct(r.c.won, r.c.won + r.c.lost)}</b> <span class="text-muted small">${r.c.won}/${r.c.won + r.c.lost}</span>` : '–'}</td>
            <td class="text-end">${r.c ? r.c.lost : '–'}</td>
            <td class="text-end">${r.c ? r.c.did_not_run : '–'}</td>
            <td class="text-end text-muted">${r.c ? r.c.races : 0}</td></tr>`).join('');
    document.querySelectorAll('.inc-county-filter').forEach(el => {
        el.innerHTML = _inc.county ? `<span class="badge text-bg-light border" title="Prikaži sve županije">${escapeHtml(incCountyShort(_inc.county))} <i class="bi bi-x"></i></span>` : '';
    });
}

function setIncCounty(code) {
    _inc.county = code && code !== _inc.county ? code : null;
    renderIncCounties();
    renderIncClose();
    renderIncDefeated();
    renderIncLong();
}

// 1 glas, 2-4 glasa, 5+ glasova; 11-14 always glasova, 21 glas, 22 glasa.
function incVotesWord(v) {
    const d = v % 10, h = v % 100;
    return h >= 11 && h <= 14 ? 'glasova' : d === 1 ? 'glas' : d >= 2 && d <= 4 ? 'glasa' : 'glasova';
}

function renderIncClose() {
    const year = document.getElementById('incCloseYear').value;
    const rows = (_inc.data.close[year] || []).filter(incOfKind).filter(incInCounty);
    const share = v => v == null ? '–' : v.toLocaleString('hr-HR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' %';
    const n = v => v.toLocaleString('hr-HR');
    document.getElementById('incClose').innerHTML = rows.length ? rows.map(d => `<tr>
            <td>${incPlace(d)} <span class="text-muted small">${d.office}</span></td>
            <td>${personLinkHtml(d.incumbent.name, d.incumbent.person_id)}${d.round > 1 ? ' <span class="text-muted small">2. krug</span>' : ''}</td>
            <td class="text-end">${share(d.incumbent.share)}</td>
            <td>${personLinkHtml(d.runner_up.name, d.runner_up.person_id)}</td>
            <td class="text-end">${share(d.runner_up.share)}</td>
            <td class="text-end"><b>${d.margin.toLocaleString('hr-HR', { maximumFractionDigits: 2 })} p.b.</b><div class="small text-muted">${n(d.votes_ahead)} ${incVotesWord(d.votes_ahead)}</div></td>
        </tr>`).join('') : '<tr><td colspan="6" class="text-muted">Nitko.</td></tr>';
    const m = _inc.data.close_margin.toLocaleString('hr-HR');
    document.getElementById('incCloseNote').textContent =
        `Oni na dužnosti koji su ponovno izabrani s manje od ${m} postotna boda prednosti pred drugim u odlučujućem krugu, najtješnje prvo.`;
}

const incCounts = y => y.by_kind[_inc.kind] || { races: 0, won: 0, won_first_round: 0, lost: 0, did_not_run: 0 };

function renderIncTiles() {
    const last = _inc.data.per_year[_inc.data.per_year.length - 1];
    const c = incCounts(last);
    const terms = _inc.data.terms.by_kind[_inc.kind] || {};
    const all = Object.values(terms).reduce((s, v) => s + v, 0);
    const longest = terms[String(_inc.data.years.length)] || 0;
    const tile = (title, big, sub, color) => `<div class="col-sm-6 col-xl-3"><div class="card p-3 h-100 inc-tile" style="border-left:4px solid ${color};">
        <div class="small text-muted">${title}</div><div class="fs-3 fw-bold">${big}</div><div class="small">${sub}</div></div></div>`;
    document.getElementById('incTiles').innerHTML =
        tile(`Ponovno izabrani ${last.year}.`, incPct(c.won, c.won + c.lost), `${c.won} od ${c.won + c.lost} koji su se ponovno kandidirali`, INC_COLORS.won)
        + tile(`Izgubili na dužnosti ${last.year}.`, String(c.lost), `od ${c.races} mjesta`, INC_COLORS.lost)
        + tile(`Nisu se kandidirali ${last.year}.`, incPct(c.did_not_run, c.races), `${c.did_not_run} od ${c.races} mjesta`, INC_COLORS.did_not_run)
        + tile(`Na dužnosti od ${_inc.data.years[0]}.`, String(longest), `od ${all} — pobijedili na svih ${_inc.data.years.length} izbora`, '#3b5bdb');
}

function renderIncChart() {
    const rows = _inc.data.per_year;
    const ds = (key, label) => ({
        label, backgroundColor: INC_COLORS[key], borderRadius: 3, borderSkipped: false,
        data: rows.map(y => { const c = incCounts(y); return c.races ? c[key] / c.races * 100 : 0; }),
        counts: rows.map(y => incCounts(y)), key,
    });
    if (_inc.chart) _inc.chart.destroy();
    _inc.chart = new Chart(document.getElementById('incChart'), {
        type: 'bar',
        data: { labels: rows.map(y => `${y.year}.`), datasets: [ds('won', 'Ponovno izabran/a'), ds('lost', 'Izgubio/la'), ds('did_not_run', 'Nije se kandidirao/la')] },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { stacked: true, grid: { display: false } },
                      y: { stacked: true, min: 0, max: 100, ticks: { callback: v => v + ' %' }, grid: { color: '#eef0f3' } } },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltip: {
                    callbacks: {
                        label: item => {
                            const c = item.dataset.counts[item.dataIndex];
                            return `${item.dataset.label}: ${c[item.dataset.key]} od ${c.races} (${incPct(c[item.dataset.key], c.races)})`;
                        },
                        footer: items => {
                            const c = items[0].dataset.counts[items[0].dataIndex];
                            return `Od onih koji su se kandidirali pobijedilo ${incPct(c.won, c.won + c.lost)}, u prvom krugu ${c.won_first_round}.`;
                        },
                    },
                },
            },
        },
    });
}

function renderIncTerms() {
    const terms = _inc.data.terms.by_kind[_inc.kind] || {};
    const n = _inc.data.years.length;
    const labels = Array.from({ length: n }, (_, i) => i + 1);
    document.getElementById('incTermsTitle').textContent = `Izabrani zaredom (${_inc.data.terms.year}.)`;
    if (_inc.termsChart) _inc.termsChart.destroy();
    _inc.termsChart = new Chart(document.getElementById('incTermsChart'), {
        type: 'bar',
        data: { labels: labels.map(i => i === 1 ? '1 (novi)' : `${i}×`),
                datasets: [{ label: 'Nositelji dužnosti', data: labels.map(i => terms[String(i)] || 0), backgroundColor: '#3b5bdb', borderRadius: 4 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#eef0f3' } } },
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: item => {
                    const i = item.dataIndex + 1;
                    return i === 1 ? `${item.raw} izabrano prvi put` : `${item.raw} izabrano ${i} puta zaredom (od ${_inc.data.terms.year - 4 * (i - 1)}.)`;
                } } },
            },
        },
    });
}

const incPlace = d => d.place_id ? placeLinkHtml(d.place_id, d.name) : escapeHtml(d.name || '');

function renderIncDefeated() {
    const year = document.getElementById('incYear').value;
    const rows = (_inc.data.defeated[year] || []).filter(incOfKind).filter(incInCounty);
    document.getElementById('incDefeated').innerHTML = rows.length ? rows.map(d => `<tr>
            <td>${incPlace(d)} <span class="text-muted small">${d.office}</span></td>
            <td>${personLinkHtml(d.incumbent.name, d.incumbent.person_id)}</td>
            <td class="text-end text-muted">${incShare(d.won_before)}</td>
            <td class="text-end">${incShare(d.incumbent.share)}${d.out_in_first_round ? ' <span class="badge bg-secondary" title="Nije ušao/la u drugi krug">ispao/la u 1. krugu</span>' : d.round > 1 ? ' <span class="text-muted small">2. krug</span>' : ''}</td>
            <td>${personLinkHtml(d.winner.name, d.winner.person_id)}</td>
            <td class="text-end">${incShare(d.winner.share)}</td>
        </tr>`).join('') : '<tr><td colspan="6" class="text-muted">Nitko.</td></tr>';
}

function renderIncLong() {
    const q = (document.getElementById('incSearch').value || '').trim().toUpperCase();
    const year = _inc.data.terms.year;
    document.getElementById('incLongTitle').textContent = `Na dužnosti od ${_inc.data.years[0]}. — ${INC_KIND_LABEL[_inc.kind]} koji su pobijedili na svim izborima`;
    document.getElementById('incLongShareHead').textContent = `Udio ${year}.`;
    const rows = _inc.data.long_serving
        .filter(incOfKind).filter(incInCounty)
        .filter(d => !q || (d.name || '').toUpperCase().includes(q) || d.person.name.toUpperCase().includes(q));
    document.getElementById('incLong').innerHTML = rows.length ? rows.map(d => `<tr>
            <td>${incPlace(d)}</td><td class="text-muted small">${d.office}</td>
            <td>${personLinkHtml(d.person.name, d.person.person_id)}</td>
            <td class="text-end">${d.unopposed ? '<span class="text-muted small">jedini kandidat</span>' : incShare(d.person.share)}</td>
        </tr>`).join('') : '<tr><td colspan="4" class="text-muted">Nitko.</td></tr>';
}
