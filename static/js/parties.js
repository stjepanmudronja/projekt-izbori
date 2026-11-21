// Stranke: the official party register and one party's page.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Općine i gradovi: one town's electoral history (/mjesto/439-klis) ----
// ---- Stranke: party register (/api/stranke) ----
let _parties = null, _partyShown = null, _partyChart = null, _partyStatus = '';
// Where the Stranke data comes from, under the list and every party page.
const PARTY_SOURCE_HTML = `<i class="bi bi-info-circle me-1"></i><b>Izvor:</b>
    podaci o strankama (naziv, kratica, sjedište, datum upisa i prestanka) iz
    <a href="https://registri-npo-mpu.gov.hr/#!stranke" target="_blank" rel="noopener">Registra političkih stranaka Republike Hrvatske</a>,
    koji vodi Ministarstvo pravosuđa, uprave i digitalne transformacije
    (<a href="https://data.gov.hr/ckan/dataset/registar-politickih-stranaka-republike-hrvatske" target="_blank" rel="noopener">otvoreni podaci, data.gov.hr</a>,
    Otvorena dozvola); izborni rezultati iz službenih izvješća
    <a href="https://www.izbori.hr/" target="_blank" rel="noopener">Državnog izbornog povjerenstva</a>.
    Stranka je povezana s izbornom listom prema nazivu ili kratici, pa male stranke koje nastupaju pod drugim imenom mogu nedostajati.`;
function partyPath(p) {
    return p ? `/stranke/${p.registry_number}-${urlSlug(p.short_name || p.name)}` : '/stranke';
}
const partyDate = iso => iso ? new Date(iso).toLocaleDateString('hr-HR', { day: 'numeric', month: 'numeric', year: 'numeric' }) : '-';
const partyStatusBadge = p => p.status === 'AKTIVAN'
    ? '<span class="party-status active">Aktivna</span>'
    : `<span class="party-status ceased">Prestala${p.status_on ? ' ' + partyDate(p.status_on) : ''}</span>`;

async function initPartiesModule() {
    if (_parties) return;
    const spinner = document.getElementById('partySpinner');
    spinner.classList.add('show');
    try {
        _parties = await fetch('/api/stranke').then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    document.getElementById('partyListSource').innerHTML = PARTY_SOURCE_HTML;
    document.getElementById('partySearch').addEventListener('input', renderPartyList);
    document.getElementById('partyOnlyElections').addEventListener('change', renderPartyList);
    document.querySelectorAll('#partyStatusGroup button').forEach(b => b.addEventListener('click', () => {
        _partyStatus = b.dataset.status;
        document.querySelectorAll('#partyStatusGroup button').forEach(x => x.classList.toggle('active', x === b));
        renderPartyList();
    }));
    document.getElementById('partyRows').addEventListener('click', e => {
        const tr = e.target.closest('tr[data-reg]');
        if (tr) openParty(+tr.dataset.reg, { push: true });
    });
    renderPartyList();
}

function renderPartyList() {
    if (!_parties) return;
    const q = partyFold(document.getElementById('partySearch').value);
    const only = document.getElementById('partyOnlyElections').checked;
    const rows = _parties.filter(p =>
        (!_partyStatus || p.status === _partyStatus) && (!only || p.elections) &&
        (!q || partyFold(`${p.name} ${p.short_name} ${p.city}`).includes(q)))
        // Parties that stood in most elections first, then by name.
        .sort((a, b) => b.elections - a.elections || a.name.localeCompare(b.name, 'hr'));
    const active = rows.filter(p => p.status === 'AKTIVAN').length;
    document.getElementById('partyCount').textContent =
        `${rows.length} stranaka (${active} aktivnih, ${rows.length - active} prestalih)`;
    document.getElementById('partyRows').innerHTML = rows.map(p => `<tr data-reg="${p.registry_number}">
        <td class="fw-semibold">${escapeHtml(p.name)}</td>
        <td>${escapeHtml(p.short_name || '')}</td>
        <td>${escapeHtml(p.city || '')}</td>
        <td>${partyDate(p.registered_on)}</td>
        <td>${partyStatusBadge(p)}</td>
        <td class="text-end">${p.elections ? `${p.elections} <small class="text-muted">(${p.first_year}.-${p.last_year}.)</small>` : '<small class="text-muted">-</small>'}</td>
    </tr>`).join('');
}
function partyFold(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[Đđ]/g, 'd').toLowerCase().trim();
}

async function openParty(n, opts = {}) {
    await initPartiesModule();
    const spinner = document.getElementById('partySpinner');
    spinner.classList.add('show');
    let d;
    try {
        d = await fetch(`/api/stranke/${n}`).then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    if (d.error) { closeParty({ push: false }); return; }
    _partyShown = d;
    if (opts.push) history.pushState({ mod: 'parties' }, '', partyPath(d));
    renderPartyDetail(d);
}

function closeParty(opts = {}) {
    _partyShown = null;
    if (_partyChart) { _partyChart.destroy(); _partyChart = null; }
    document.getElementById('partyDetail').style.display = 'none';
    document.getElementById('partyControls').style.display = '';
    document.getElementById('partyListWrap').style.display = '';
    if (opts.push) history.pushState({ mod: 'parties' }, '', '/stranke');
}

function renderPartyDetail(d) {
    document.getElementById('partyControls').style.display = 'none';
    document.getElementById('partyListWrap').style.display = 'none';
    const box = document.getElementById('partyDetail');
    const won = h => h.municipalities_won
        ? `<br><small class="text-muted">prva lista u ${h.municipalities_won} ${h.municipalities_won % 10 === 1 && h.municipalities_won % 100 !== 11 ? 'mjestu' : 'mjesta'}</small>` : '';
    const rows = d.history.map(h => `<tr>
        <td>${h.year}.</td>
        <td>${escapeHtml(h.election_type)}</td>
        <td class="text-end">${h.led_lists ? `${formatNumber(h.led_votes)} <small class="text-muted">(${homePct(h.led_share)})</small>${won(h)}` : '<small class="text-muted">-</small>'}</td>
        <td class="text-end">${h.partner_lists ? `${h.partner_lists} ${[2, 3, 4].includes(h.partner_lists % 10) && ![12, 13, 14].includes(h.partner_lists % 100) ? 'liste' : 'lista'}` : '<small class="text-muted">-</small>'}</td>
        <td style="font-size:.8rem;">${h.top_list ? escapeHtml(h.top_list.replace(/\n/g, ', ')) : ''}</td>
    </tr>`).join('');
    box.innerHTML = `
        <button type="button" class="btn btn-sm btn-outline-secondary mb-3" id="partyBack"><i class="bi bi-arrow-left me-1"></i>Sve stranke</button>
        <div class="card p-3 mb-3">
            <div class="d-flex flex-wrap align-items-center gap-2 mb-1">
                <h4 class="fw-bold mb-0">${escapeHtml(d.name)}</h4>
                ${d.short_name ? `<span class="badge bg-dark">${escapeHtml(d.short_name)}</span>` : ''}
                ${partyStatusBadge(d)}
            </div>
            <div class="text-muted" style="font-size:.88rem;">
                Upisana u registar ${partyDate(d.registered_on)}${d.status !== 'AKTIVAN' && d.status_on ? ` · prestala ${partyDate(d.status_on)}` : ''}
                ${d.seat ? ` · sjedište: ${escapeHtml(d.seat)}` : ''} · registarski broj ${d.registry_number}
            </div>
        </div>
        ${d.history.length ? `
        <div class="card p-3 mb-3">
            <h6 class="fw-bold mb-2">Udio glasova lista koje je stranka predvodila</h6>
            <div style="position:relative; height:260px;"><canvas id="partyChart"></canvas></div>
        </div>
        <div class="card p-0 mb-4">
            <div class="p-3 pb-2"><h6 class="fw-bold mb-0">Na izborima (${d.elections})</h6>
                <small class="text-muted">Stranka je "predvodila" listu kad je na njoj navedena prva; udio je od svih glasova za liste na tim izborima.
                U koaliciji: liste na kojima je bila partner.</small></div>
            <div class="table-responsive"><table class="table table-sm mb-0">
                <thead><tr><th>Godina</th><th>Izbori</th><th class="text-end">Predvodila liste: glasovi (udio)</th>
                    <th class="text-end">U koaliciji</th><th>Lista s najviše glasova</th></tr></thead>
                <tbody>${rows}</tbody>
            </table></div>
        </div>` : `<div class="alert alert-light">Stranka nije pronađena ni na jednoj izbornoj listi u bazi.
            Male i lokalne stranke često nastupaju pod drugim nazivom ili samo u koaliciji.</div>`}
        <div class="party-source">${PARTY_SOURCE_HTML}</div>`;
    box.style.display = '';
    document.getElementById('partyBack').addEventListener('click', () => closeParty({ push: true }));
    renderPartyChart(d);
}

function renderPartyChart(d) {
    if (_partyChart) { _partyChart.destroy(); _partyChart = null; }
    const canvas = document.getElementById('partyChart');
    if (!canvas) return;
    const series = [['Parlamentarni izbori', '#1f4ea8'], ['Izbori za Europski parlament', '#f39200'],
                    ['Gradska i općinska vijeća', '#00a676'], ['Županijska skupština', '#8e44ad']];
    const years = [...new Set(d.history.filter(h => h.led_share != null).map(h => h.year))].sort((a, b) => a - b);
    const datasets = series.map(([type, color]) => ({
        label: type, borderColor: color, backgroundColor: color, spanGaps: true, tension: .2, pointRadius: 4,
        data: years.map(y => { const h = d.history.find(x => x.year === y && x.election_type === type); return h ? h.led_share : null; }),
    })).filter(ds => ds.data.some(v => v != null));
    if (!datasets.length) { canvas.closest('.card').style.display = 'none'; return; }
    _partyChart = new Chart(canvas, {
        type: 'line',
        data: { labels: years.map(y => `${y}.`), datasets },
        options: { responsive: true, maintainAspectRatio: false,
                   plugins: { tooltip: { callbacks: { label: c => `${c.dataset.label}: ${homePct(c.parsed.y)}` } } },
                   scales: { y: { beginAtZero: true, ticks: { callback: v => `${v} %` } } } },
    });
}
