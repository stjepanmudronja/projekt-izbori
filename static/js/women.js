// Žene u politici (Analitika): the share of women among candidates and the
// elected, per election (/api/analytics/women) and per party for list elections.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

const W_COLORS = { sabor: '#3b5bdb', eu: '#e8590c', lokalni: '#0ca678', predsjednicki: '#ae3ec9' };
const W_SHORT = { sabor: 'Sabor', eu: 'Europski parlament', lokalni: 'Gradonačelnici, načelnici i župani', predsjednicki: 'Predsjednički' };
const _w = { ready: false, data: null, which: 'elected', chart: null, partyChart: null };

const wTotal = c => c ? c.f + c.m + c.u : 0;
// Share of women among those whose gender is known; the unknown are left out of both sides.
const wShare = c => c && (c.f + c.m) ? c.f / (c.f + c.m) * 100 : null;
const wPct = v => v == null ? '–' : v.toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';
const wNum = v => v.toLocaleString('hr-HR');

async function initWomen() {
    if (_w.ready) return;
    _w.ready = true;
    const spinner = document.getElementById('wSpinner');
    spinner.classList.add('show');
    try {
        _w.data = await fetch('/api/analytics/women').then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    document.getElementById('wArea').style.display = '';
    document.getElementById('wWhich').addEventListener('click', e => {
        const b = e.target.closest('[data-w-which]');
        if (!b) return;
        _w.which = b.dataset.wWhich;
        document.querySelectorAll('#wWhich button').forEach(x => x.classList.toggle('active', x === b));
        renderWomenChart();
    });
    const partyKeys = Object.keys(_w.data.parties).sort((a, b) => b.split('-')[1] - a.split('-')[1] || (a < b ? 1 : -1));
    const sel = document.getElementById('wPartyElection');
    sel.innerHTML = partyKeys.map(k => { const [kind, y] = k.split('-'); return `<option value="${k}">${W_SHORT[kind]} ${y}.</option>`; }).join('');
    sel.addEventListener('change', () => renderWomenParties(sel.value));
    document.getElementById('wRows').addEventListener('click', e => {
        const tr = e.target.closest('[data-w-party]');
        if (!tr) return;
        sel.value = tr.dataset.wParty;
        renderWomenParties(sel.value);
        document.getElementById('wPartyChart').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    renderWomenTiles();
    renderWomenChart();
    renderWomenTable();
    renderWomenParties(partyKeys[0]);
    renderWomenMethod();
}

function renderWomenTiles() {
    const latest = kind => [..._w.data.elections].reverse().find(e => e.kind === kind && e.elected);
    const first = kind => _w.data.elections.find(e => e.kind === kind && e.elected);
    const tile = (kind, title, sub) => {
        const l = latest(kind), f = first(kind);
        return `<div class="col-sm-6 col-xl-3"><div class="card p-3 h-100 w-tile" style="border-left:4px solid ${W_COLORS[kind]};">
            <div class="small text-muted">${title} ${l.year}.</div>
            <div class="fs-3 fw-bold">${wPct(wShare(l.elected))}</div>
            <div class="small">${wNum(l.elected.f)} od ${wNum(wTotal(l.elected))} ${sub}</div>
            <div class="small text-muted">${f.year}.: ${wPct(wShare(f.elected))}</div></div></div>`;
    };
    const pres = _w.data.elections.filter(e => e.kind === 'predsjednicki');
    const won = pres.filter(e => e.elected && e.elected.f);
    document.getElementById('wTiles').innerHTML =
        tile('sabor', 'Zastupnice u Saboru', 'izabranih')
        + tile('eu', 'Zastupnice u Europskom parlamentu', 'izabranih')
        + tile('lokalni', 'Gradonačelnice, načelnice i županice', 'izabranih')
        + `<div class="col-sm-6 col-xl-3"><div class="card p-3 h-100 w-tile" style="border-left:4px solid ${W_COLORS.predsjednicki};">
            <div class="small text-muted">Predsjednički izbori</div>
            <div class="fs-3 fw-bold">${won.length} od ${pres.length}</div>
            <div class="small">izbora dobila je žena${won.length ? ` (${won.map(e => e.year + '.').join(', ')})` : ''}</div>
            <div class="small text-muted">kandidatkinja ukupno: ${pres.reduce((s, e) => s + (e.candidates ? e.candidates.f : 0), 0)}</div></div></div>`;
}

function renderWomenChart() {
    const which = _w.which;
    // Presidential elections elect one person: a 0 / 100 % line says nothing, so it is shown for candidates only.
    const kinds = _w.data.kinds.filter(k => which === 'candidates' || k.key !== 'predsjednicki');
    // A real time axis; a line breaks over an election of its kind with no figure
    // (Sabor 1992-2011 candidates: only some were published).
    const datasets = kinds.map(k => {
        const rows = _w.data.elections.filter(e => e.kind === k.key && (e.candidates || e.elected));
        return {
            label: W_SHORT[k.key], kind: k.key,
            data: rows.map(e => ({ x: e.year, y: e[which] ? wShare(e[which]) : null, c: e[which] })),
            borderColor: W_COLORS[k.key], backgroundColor: W_COLORS[k.key],
            borderWidth: 2, pointRadius: 4, pointHoverRadius: 6, spanGaps: false, tension: 0,
        };
    });
    const years = _w.data.elections.map(e => e.year);
    datasets.push({ label: 'Polovica (50 %)', data: [{ x: Math.min(...years), y: 50 }, { x: Math.max(...years), y: 50 }],
                    borderColor: '#adb5bd', borderDash: [5, 4], borderWidth: 1, pointRadius: 0, pointHoverRadius: 0 });
    document.getElementById('wChartTitle').textContent = which === 'elected' ? 'Udio žena među izabranima' : 'Udio žena među kandidatima';
    document.getElementById('wChartNote').textContent = which === 'elected'
        ? 'Sabor: zastupnici kako su izabrani (popis zastupnika, a od 2015. mandati prema glasovima), bez kasnijih zamjena; 1990. su sva tri vijeća zajedno. Za 2000. imena zastupnika nisu objavljena.'
        : 'Sabor: samo izbori na kojima su objavljeni svi kandidati na listama (1990. i od 2015.). Predsjednički izbori imaju malo kandidata, pa jedna kandidatkinja više ili manje jako mijenja postotak.';
    if (_w.chart) _w.chart.destroy();
    _w.chart = new Chart(document.getElementById('wChart'), {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true, maintainAspectRatio: false, interaction: { mode: 'nearest', intersect: false },
            scales: {
                y: { min: 0, max: 60, ticks: { callback: v => v + ' %' }, grid: { color: '#eef0f3' } },
                x: { type: 'linear', min: Math.min(...years) - 1, max: Math.max(...years) + 1,
                     afterBuildTicks: axis => { axis.ticks = [];
                         for (let y = Math.ceil(axis.min / 5) * 5; y <= axis.max; y += 5) axis.ticks.push({ value: y }); },
                     ticks: { callback: v => String(v) }, grid: { display: false } },
            },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltip: {
                    filter: item => item.raw && item.raw.c,
                    callbacks: {
                        title: items => items.length ? `${items[0].raw.x}.` : '',
                        label: item => {
                            const c = item.raw.c;
                            return `${item.dataset.label}: ${wPct(item.raw.y)} (${wNum(c.f)} od ${wNum(c.f + c.m)}${c.u ? `, ${c.u} nepoznato` : ''})`;
                        },
                    },
                },
            },
        },
    });
}

function renderWomenTable() {
    const cell = c => c ? `<b>${wPct(wShare(c))}</b><div class="small text-muted">${wNum(c.f)} od ${wNum(wTotal(c))}</div>` : '<span class="text-muted">–</span>';
    const rows = [..._w.data.elections].sort((a, b) => b.year - a.year || _w.data.kinds.findIndex(k => k.key === a.kind) - _w.data.kinds.findIndex(k => k.key === b.kind));
    document.getElementById('wRows').innerHTML = rows.map(e => {
        const pk = `${e.kind}-${e.year}`;
        const clickable = _w.data.parties[pk];
        return `<tr${clickable ? ` data-w-party="${pk}" class="w-clickable" title="Usporedi stranke na ovim izborima"` : ''}>
            <td><span class="w-dot" style="background:${W_COLORS[e.kind]}"></span>${W_SHORT[e.kind]} ${e.year}.${clickable ? ' <i class="bi bi-bar-chart text-muted small"></i>' : ''}</td>
            <td class="text-end">${cell(e.candidates)}</td>
            <td class="text-end">${cell(e.elected)}</td></tr>`;
    }).join('');
}

function renderWomenParties(key) {
    const rows = (_w.data.parties[key] || []).slice(0, 12);
    const label = name => name === 'NACIONALNE MANJINE' ? 'Nacionalne manjine' : predLabel(name);
    const share = c => wShare(c) ?? 0;
    const holder = document.querySelector('.w-party-chart');
    holder.style.height = `${Math.max(14, rows.length * 2.6 + 4)}rem`;
    if (_w.partyChart) _w.partyChart.destroy();
    _w.partyChart = new Chart(document.getElementById('wPartyChart'), {
        type: 'bar',
        data: {
            labels: rows.map(r => label(r.party)),
            datasets: [
                { label: 'Kandidatkinje', data: rows.map(r => share(r.candidates)), raw: rows.map(r => r.candidates), backgroundColor: '#a5b4fc', borderRadius: 4 },
                { label: 'Izabrane', data: rows.map(r => wTotal(r.elected) ? share(r.elected) : null), raw: rows.map(r => r.elected), backgroundColor: '#4338ca', borderRadius: 4 },
            ],
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: { x: { min: 0, max: 100, ticks: { callback: v => v + ' %' }, grid: { color: '#eef0f3' } }, y: { grid: { display: false } } },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltip: {
                    callbacks: {
                        title: items => rows[items[0].dataIndex].party,
                        label: item => {
                            const c = item.dataset.raw[item.dataIndex];
                            return wTotal(c) ? `${item.dataset.label}: ${wPct(item.raw)} (${wNum(c.f)} od ${wNum(c.f + c.m)})` : `${item.dataset.label}: nitko nije izabran`;
                        },
                    },
                },
            },
        },
    });
    const [kind] = key.split('-');
    document.getElementById('wPartyNote').textContent =
        `Stranka je prva navedena na listi (koalicija se pripisuje stranci koja ju je predvodila). Prikazane su liste s barem 10 kandidata ili s izabranima${kind === 'sabor' ? '; manjine su XII. izborna jedinica' : ''}.`;
}

function renderWomenMethod() {
    const p = _w.data.people;
    document.getElementById('wMethod').innerHTML =
        `<b>Kako je određen spol.</b> Podaci o izborima ne bilježe spol, pa se čita iz imena: ženska imena u hrvatskom završavaju na -a, osim muških poput Luka, Nikola ili Ivica, a neka ženska ne završavaju (Ines, Nives, Karmen) — oba su popisa ručno provjerena na svim imenima u bazi. `
        + `Imena koja nose i muškarci i žene ostavljena su kao nepoznata i ne ulaze u postotak: ${wNum(p.unknown)} od ${wNum(p.total)} osoba (${p.unknown_names.slice(0, 5).map(([n, c]) => `${n.charAt(0) + n.slice(1).toLowerCase()} ${c}`).join(', ')}). `
        + `Svaka se osoba na jednim izborima broji jednom. Izabrani na lokalnim izborima su pobjednici odlučujućeg kruga za gradonačelnika, načelnika ili župana; zamjenici nisu uključeni.`;
}
