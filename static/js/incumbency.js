// Ponovni izbor (Analitika): do načelnici, gradonačelnici and župani win again?
// /api/analytics/incumbency. Part of the site script, split from
// templates/index.html; the files load in the order index.html lists them and
// share one global scope.

const INC_COLORS = { won: '#0c8599', lost: '#e8590c', did_not_run: '#adb5bd' };
const INC_KIND_LABEL = { sve: 'svi', opcina: 'načelnici', grad: 'gradonačelnici', zupanija: 'župani' };
const _inc = { ready: false, data: null, kind: 'sve', chart: null, termsChart: null };

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
    renderIncumbency();
}

function renderIncumbency() {
    renderIncTiles();
    renderIncChart();
    renderIncTerms();
    renderIncDefeated();
    renderIncLong();
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
    const rows = (_inc.data.defeated[year] || []).filter(d => _inc.kind === 'sve' || d.kind === _inc.kind);
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
        .filter(d => _inc.kind === 'sve' || d.kind === _inc.kind)
        .filter(d => !q || (d.name || '').toUpperCase().includes(q) || d.person.name.toUpperCase().includes(q));
    document.getElementById('incLong').innerHTML = rows.length ? rows.map(d => `<tr>
            <td>${incPlace(d)}</td><td class="text-muted small">${d.office}</td>
            <td>${personLinkHtml(d.person.name, d.person.person_id)}</td>
            <td class="text-end">${d.unopposed ? '<span class="text-muted small">jedini kandidat</span>' : incShare(d.person.share)}</td>
        </tr>`).join('') : '<tr><td colspan="4" class="text-muted">Nitko.</td></tr>';
}
