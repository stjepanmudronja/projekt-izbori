// Žene u politici (Analitika): the share of women among candidates and the
// elected, per election (/api/analytics/women) and per party for list elections.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

const W_COLORS = { sabor: '#3b5bdb', eu: '#e8590c', lokalni: '#0ca678', predsjednicki: '#ae3ec9' };
const W_SHORT = { sabor: 'Sabor', eu: 'Europski parlament', lokalni: 'Gradonačelnici, načelnici i župani', predsjednicki: 'Predsjednički' };
const _w = { ready: false, data: null, which: 'elected', chart: null, partyChart: null, posChart: null, cwhich: 'elected' };
// County map: share of women, one hue light -> dark (the party chart's indigo).
const W_MAP_LO = [238, 240, 253], W_MAP_HI = [55, 48, 163], W_MAP_NONE = '#e9ecef';

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
    renderWomenOffices();
    initWomenPositions();
    renderWomenLeaders();
    initWomenCounties();
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

// ---- Executives by office ----
function renderWomenOffices() {
    const years = Object.keys(_w.data.by_office).sort().reverse();
    const cell = c => c && wTotal(c.elected)
        ? `<b>${wPct(wShare(c.elected))}</b> <span class="small text-muted">${wNum(c.elected.f)}/${wNum(c.elected.f + c.elected.m)}</span>`
          + `<div class="small text-muted">kandidatkinje ${wPct(wShare(c.candidates))}</div>`
        : '<span class="text-muted">–</span>';
    document.getElementById('wOffices').innerHTML = years.map(y => {
        const o = _w.data.by_office[y];
        return `<tr><td>${y}.</td><td class="text-end">${cell(o.opcina)}</td><td class="text-end">${cell(o.grad)}</td><td class="text-end">${cell(o.zupanija)}</td></tr>`;
    }).join('');
}

// ---- Place on the list (Sabor from 2015, EU) ----
const W_POS_LABEL = { '1': 'Nositelj/ica liste (1.)', '2-3': '2. i 3. mjesto', '4+': '4. mjesto i niže' };

function initWomenPositions() {
    const keys = Object.keys(_w.data.by_position).sort((a, b) => b.split('-')[1] - a.split('-')[1] || (a < b ? 1 : -1));
    const sel = document.getElementById('wPosElection');
    sel.innerHTML = keys.map(k => { const [kind, y] = k.split('-'); return `<option value="${k}">${W_SHORT[kind]} ${y}.</option>`; }).join('');
    sel.addEventListener('change', () => renderWomenPositions(sel.value));
    renderWomenPositions(keys[0]);
}

function renderWomenPositions(key) {
    const rows = _w.data.by_position[key] || [];
    if (_w.posChart) _w.posChart.destroy();
    _w.posChart = new Chart(document.getElementById('wPosChart'), {
        type: 'bar',
        data: {
            labels: rows.map(r => W_POS_LABEL[r.bucket]),
            datasets: [
                { label: 'Kandidatkinje', data: rows.map(r => wShare(r.candidates) ?? 0), raw: rows.map(r => r.candidates), backgroundColor: '#a5b4fc', borderRadius: 4 },
                { label: 'Izabrane', data: rows.map(r => wTotal(r.elected) ? wShare(r.elected) : null), raw: rows.map(r => r.elected), backgroundColor: '#4338ca', borderRadius: 4 },
            ],
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: { x: { min: 0, max: 60, ticks: { callback: v => v + ' %' }, grid: { color: '#eef0f3' } }, y: { grid: { display: false } } },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltip: {
                    callbacks: {
                        label: item => {
                            const c = item.dataset.raw[item.dataIndex];
                            return wTotal(c) ? `${item.dataset.label}: ${wPct(item.raw)} (${wNum(c.f)} od ${wNum(c.f + c.m)})` : `${item.dataset.label}: nitko s tog mjesta`;
                        },
                    },
                },
            },
        },
    });
    const lead = rows.find(r => r.bucket === '1'), rest = rows.find(r => r.bucket === '4+');
    const [kind] = key.split('-');
    document.getElementById('wPosNote').textContent =
        `Udio žena prema mjestu na listi. Žene su ${wPct(wShare(rest.candidates))} kandidata od 4. mjesta naniže, ali ${wPct(wShare(lead.candidates))} nositelja lista. `
        + (kind === 'sabor' ? 'Izabrani su prema mjestu na listi s kojeg su kandidirali, a manjinske liste (XII. izborna jedinica) nisu uključene.' : 'Izabrani su prema mjestu na listi s kojeg su kandidirali; preferencijski glasovi mogu nekoga izabrati i s niže pozicije.');
}

// ---- List leaders for councils and assemblies, 2001-2009 ----
function renderWomenLeaders() {
    const by = {};
    _w.data.leaders.forEach(l => { (by[l.year] = by[l.year] || {})[l.body] = l; });
    const cell = c => c && wTotal(c) ? `<b>${wPct(wShare(c))}</b><div class="small text-muted">${wNum(c.f)} od ${wNum(c.f + c.m)}</div>` : '<span class="text-muted">–</span>';
    document.getElementById('wLeaders').innerHTML = Object.keys(by).sort().reverse().map(y => {
        const v = by[y].vijeca || {}, a = by[y].skupstine || {};
        return `<tr><td>${y}.</td><td class="text-end">${cell(v.all)}</td><td class="text-end">${cell(v.first)}</td><td class="text-end">${cell(a.all)}</td><td class="text-end">${cell(a.first)}</td></tr>`;
    }).join('');
}

// ---- By county: map + table ----
const wCountyName = code => docPartyCase(_w.data.counties[code] || '').replace(/ županija$/, '');

async function initWomenCounties() {
    const years = Object.keys(_w.data.by_county).sort().reverse();
    const sel = document.getElementById('wCountyYear');
    sel.innerHTML = years.map(y => `<option value="${y}">${y}.</option>`).join('')
        + `<option value="all">Svi izbori ${years[years.length - 1]}.–${years[0]}.</option>`;
    sel.addEventListener('change', renderWomenCounties);
    document.getElementById('wCountyWhich').addEventListener('click', e => {
        const b = e.target.closest('[data-w-cwhich]');
        if (!b) return;
        _w.cwhich = b.dataset.wCwhich;
        document.querySelectorAll('#wCountyWhich button').forEach(x => x.classList.toggle('active', x === b));
        renderWomenCounties();
    });
    const holder = document.getElementById('wMap');
    try {
        holder.innerHTML = await fetch('/static/croatia_map.svg').then(r => r.text());
        const svg = holder.querySelector('svg');
        svg.querySelectorAll('style, title').forEach(x => x.remove());   // its global "path" rule would leak
        svg.removeAttribute('width');
        svg.removeAttribute('height');
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', 'Karta županija: udio žena');
        const tip = document.getElementById('wMapTip');
        const wrap = holder.parentElement;
        svg.querySelectorAll('path[id^="HR-"]').forEach(path => {
            const code = path.id.slice(3);
            path.addEventListener('mousemove', e => {
                const c = wCountyCounts()[code];
                const line = (label, x) => `${label}: ${wPct(wShare(x))} (${wNum(x.f)} od ${wNum(x.f + x.m)})`;
                tip.innerHTML = `<b>${escapeHtml(docPartyCase(_w.data.counties[code] || ''))}</b><br>`
                    + (c ? `${line('Izabrane', c.elected)}<br>${line('Kandidatkinje', c.candidates)}` : 'Nema podataka');
                const box = wrap.getBoundingClientRect();
                tip.style.display = 'block';
                tip.style.left = Math.min(e.clientX - box.left + 14, box.width - tip.offsetWidth - 4) + 'px';
                tip.style.top = (e.clientY - box.top + 14) + 'px';
            });
            path.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
        });
    } catch (e) {
        holder.innerHTML = '';     // the table still has every figure
    }
    renderWomenCounties();
}

function wCountyCounts() {
    const year = document.getElementById('wCountyYear').value;
    if (year !== 'all') return _w.data.by_county[year] || {};
    const out = {};
    Object.values(_w.data.by_county).forEach(per => Object.entries(per).forEach(([code, c]) => {
        const t = out[code] = out[code] || { candidates: { f: 0, m: 0, u: 0 }, elected: { f: 0, m: 0, u: 0 } };
        ['candidates', 'elected'].forEach(w => Object.keys(t[w]).forEach(k => { t[w][k] += c[w][k]; }));
    }));
    return out;
}

function wMapColor(v, lo, hi) {
    if (v == null) return W_MAP_NONE;
    const t = hi > lo ? Math.min(1, Math.max(0, (v - lo) / (hi - lo))) : 1;
    return `rgb(${W_MAP_LO.map((a, i) => Math.round(a + (W_MAP_HI[i] - a) * t)).join(',')})`;
}

function renderWomenCounties() {
    const counts = wCountyCounts();
    const rows = Object.keys(_w.data.counties).sort().map(code => {
        const c = counts[code];
        return { code, c, v: c ? wShare(c[_w.cwhich]) : null };
    });
    const vals = rows.map(r => r.v).filter(v => v != null);
    const lo = vals.length ? Math.floor(Math.min(...vals) / 5) * 5 : 0;
    const hi = vals.length ? Math.max(lo + 5, Math.ceil(Math.max(...vals) / 5) * 5) : 100;
    rows.forEach(r => { r.color = wMapColor(r.v, lo, hi); });
    document.querySelectorAll('#wMap path[id^="HR-"]').forEach(path => {
        const r = rows.find(x => x.code === path.id.slice(3));
        path.style.fill = r ? r.color : W_MAP_NONE;
    });
    const grad = [0, .5, 1].map(t => wMapColor(lo + (hi - lo) * t, lo, hi)).join(',');
    document.getElementById('wMapLegend').innerHTML =
        `<span>${lo} %</span><span class="bar" style="background:linear-gradient(90deg,${grad})"></span><span>${hi} %</span>`
        + `<span class="ms-2">${_w.cwhich === 'elected' ? 'žena među izabranima' : 'žena među kandidatima'}</span>`;
    rows.sort((a, b) => (b.v ?? -1) - (a.v ?? -1) || wCountyName(a.code).localeCompare(wCountyName(b.code), 'hr'));
    const cell = (x, bold) => x && wTotal(x) ? `${bold ? '<b>' : ''}${wPct(wShare(x))}${bold ? '</b>' : ''} <span class="text-muted small">${wNum(x.f)}/${wNum(x.f + x.m)}</span>` : '–';
    document.getElementById('wCounties').innerHTML = rows.map(r => `<tr>
            <td><span class="inc-swatch" style="background:${r.color}"></span>${escapeHtml(wCountyName(r.code))}</td>
            <td class="text-end">${cell(r.c && r.c.elected, _w.cwhich === 'elected')}</td>
            <td class="text-end">${cell(r.c && r.c.candidates, _w.cwhich === 'candidates')}</td></tr>`).join('');
}
