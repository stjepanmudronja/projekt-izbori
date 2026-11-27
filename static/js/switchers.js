// Prelasci između stranaka (Analitika): who stood for one party and later for
// another in the national elections (/api/analytics/switchers).
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

const SW_KIND_SHORT = { sabor: 'Sabor', zd: 'Žup. dom', eu: 'EU', lokalni: 'Lokalni' };
const SW_PAGE = 60;
// who: elected at least once / every candidate; filter: a move ("from>to") or a party key.
const _sw = { ready: false, data: null, who: 'elected', filter: null, shown: SW_PAGE };

const swLabel = k => (_sw.data.parties[k] || {}).label || k;
// A party's chip colour: the map's colour for the main parties, else grey.
const swColor = k => MAP_PARTY_COLORS[swLabel(k).toUpperCase()] || '#adb5bd';

async function initSwitchers() {
    if (_sw.ready) return;
    _sw.ready = true;
    const spinner = document.getElementById('swSpinner');
    spinner.classList.add('show');
    try {
        _sw.data = await fetch('/api/analytics/switchers').then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    document.getElementById('swArea').style.display = '';
    document.getElementById('swWho').addEventListener('click', e => {
        const b = e.target.closest('[data-sw-who]');
        if (!b) return;
        _sw.who = b.dataset.swWho;
        _sw.shown = SW_PAGE;
        document.querySelectorAll('#swWho button').forEach(x => x.classList.toggle('active', x === b));
        renderSwitchers();
    });
    document.getElementById('swSearch').addEventListener('input', () => { _sw.shown = SW_PAGE; renderSwPeople(); });
    document.getElementById('swFlows').addEventListener('click', e => {
        const tr = e.target.closest('[data-sw-flow]');
        if (tr) setSwFilter(tr.dataset.swFlow);
    });
    document.getElementById('swParties').addEventListener('click', e => {
        const tr = e.target.closest('[data-sw-party]');
        if (tr && !e.target.closest('.sw-reg')) setSwFilter(tr.dataset.swParty);
        const reg = e.target.closest('.sw-reg');
        if (reg && activateModule('parties', { pushState: false, focusInput: false })) openParty(+reg.dataset.reg, { push: true });
    });
    document.getElementById('swFilter').addEventListener('click', e => { if (e.target.closest('.badge')) setSwFilter(null); });
    document.getElementById('swMore').addEventListener('click', e => {
        if (e.target.closest('button')) { _sw.shown += SW_PAGE * 2; renderSwPeople(); }
    });
    renderSwMethod();
    renderSwitchers();
}

function setSwFilter(f) {
    _sw.filter = f && f !== _sw.filter ? f : null;
    _sw.shown = SW_PAGE;
    renderSwFlows();
    renderSwParties();
    renderSwPeople();
    if (_sw.filter) document.getElementById('swPeople').closest('.card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

const swPeople = () => _sw.data.people.filter(p => _sw.who === 'all' || p.elected);

function renderSwitchers() {
    renderSwTiles();
    renderSwFlows();
    renderSwParties();
    renderSwPeople();
}

// Moves and per-party counts for whoever is shown.
function swCounts() {
    const flows = {}, left = {}, joined = {};
    swPeople().forEach(p => p.moves.forEach(m => {
        const k = `${m.from}>${m.to}`;
        (flows[k] = flows[k] || new Set()).add(p.person_id);
        (left[m.from] = left[m.from] || new Set()).add(p.person_id);
        (joined[m.to] = joined[m.to] || new Set()).add(p.person_id);
    }));
    return { flows, left, joined };
}

function renderSwTiles() {
    const people = swPeople();
    const moves = people.reduce((s, p) => s + p.moves.length, 0);
    const many = people.filter(p => p.moves.length >= 3).length;
    const { flows } = swCounts();
    const top = Object.entries(flows).sort((a, b) => b[1].size - a[1].size)[0];
    const tile = (title, big, sub) => `<div class="col-sm-6 col-xl-3"><div class="card p-3 h-100">
        <div class="small text-muted">${title}</div><div class="fs-3 fw-bold">${big}</div><div class="small">${sub}</div></div></div>`;
    const [f, t] = top ? top[0].split('>') : [];
    document.getElementById('swTiles').innerHTML =
        tile('Promijenili stranku', people.length.toLocaleString('hr-HR'), _sw.who === 'elected' ? 'političara koji su barem jednom izabrani' : 'kandidata')
        + tile('Prelazaka ukupno', moves.toLocaleString('hr-HR'), 'od jedne liste do druge bez zajedničke stranke')
        + tile('Tri ili više prelazaka', many.toLocaleString('hr-HR'), 'ljudi')
        + tile('Najčešći prelazak', top ? `${escapeHtml(swLabel(f))} → ${escapeHtml(swLabel(t))}` : '–', top ? `${top[1].size} ljudi` : '');
}

function swPartyHtml(k) {
    return `<span class="sw-dot" style="background:${swColor(k)}"></span>${escapeHtml(swLabel(k))}`;
}

function renderSwFlows() {
    const { flows } = swCounts();
    const rows = Object.entries(flows).sort((a, b) => b[1].size - a[1].size || swLabel(a[0].split('>')[0]).localeCompare(swLabel(b[0].split('>')[0]), 'hr')).slice(0, 40);
    document.getElementById('swFlows').innerHTML = rows.map(([k, set]) => {
        const [f, t] = k.split('>');
        return `<tr data-sw-flow="${escapeHtml(k)}" class="sw-click${_sw.filter === k ? ' selected' : ''}" title="Prikaži te ljude">
            <td>${swPartyHtml(f)}</td><td class="text-muted">→</td><td>${swPartyHtml(t)}</td><td class="text-end">${set.size}</td></tr>`;
    }).join('') || '<tr><td colspan="4" class="text-muted">Nitko.</td></tr>';
}

function renderSwParties() {
    const { left, joined } = swCounts();
    const keys = [...new Set([...Object.keys(left), ...Object.keys(joined)])];
    const n = (o, k) => (o[k] ? o[k].size : 0);
    keys.sort((a, b) => (n(left, b) + n(joined, b)) - (n(left, a) + n(joined, a)) || swLabel(a).localeCompare(swLabel(b), 'hr'));
    document.getElementById('swParties').innerHTML = keys.slice(0, 40).map(k => {
        const p = _sw.data.parties[k] || {};
        const diff = n(joined, k) - n(left, k);
        return `<tr data-sw-party="${escapeHtml(k)}" class="sw-click${_sw.filter === k ? ' selected' : ''}" title="${escapeHtml(p.name || '')}">
            <td>${swPartyHtml(k)}${p.registry_number ? ` <i class="bi bi-box-arrow-up-right text-muted sw-reg" data-reg="${p.registry_number}" title="Otvori stranicu stranke"></i>` : ''}</td>
            <td class="text-end">${n(left, k)}</td><td class="text-end">${n(joined, k)}</td>
            <td class="text-end ${diff > 0 ? 'text-success' : diff < 0 ? 'text-danger' : 'text-muted'}">${diff > 0 ? '+' : ''}${diff}</td></tr>`;
    }).join('') || '<tr><td colspan="4" class="text-muted">Nitko.</td></tr>';
}

function swMatches(p) {
    const f = _sw.filter;
    if (f && f.includes('>')) {
        const [a, b] = f.split('>');
        if (!p.moves.some(m => String(m.from) === a && String(m.to) === b)) return false;
    } else if (f && !p.moves.some(m => String(m.from) === f || String(m.to) === f)) {
        return false;
    }
    const q = partyFold(document.getElementById('swSearch').value);
    if (!q) return true;
    return partyFold(p.name).includes(q) || p.path.some(e => e.parties.some(k => partyFold(swLabel(k)).includes(q)));
}

function renderSwPeople() {
    const rows = swPeople().filter(swMatches);
    const f = _sw.filter;
    document.getElementById('swListTitle').textContent = `Političari (${rows.length.toLocaleString('hr-HR')})`;
    document.getElementById('swFilter').innerHTML = f
        ? ` <span class="badge text-bg-light border" role="button" title="Prikaži sve">${f.includes('>') ? f.split('>').map(k => escapeHtml(swLabel(k))).join(' → ') : escapeHtml(swLabel(f))} <i class="bi bi-x"></i></span>`
        : '';
    document.getElementById('swPeople').innerHTML = rows.slice(0, _sw.shown).map(p => {
        const steps = p.path.map((e, i) => {
            const moved = i > 0 && p.moves.some(m => m.year === e.year && String(m.to) === String(e.parties[0]))
                && !p.path[i - 1].parties.some(k => e.parties.includes(k));
            const more = e.parties.length > 1 ? ` <span class="text-muted">+${e.parties.length - 1}</span>` : '';
            const tip = `${e.year}. ${_sw.data.kinds[e.kind]}: ${_sw.data.lists[e.list]}`
                + (e.source === 'roster' ? ' (popis zastupnika; stranka može biti ona s kraja mandata)' : '')
                + (e.source === 'local' ? ' (predlagatelji)' : '')
                + (e.elected ? ' · izabran/a' : '');
            return (i ? `<i class="bi ${moved ? 'bi-arrow-right sw-move' : 'bi-dot text-muted'}"></i>` : '')
                + `<span class="sw-step${e.elected ? ' won' : ''}" style="border-left-color:${swColor(e.parties[0])}" title="${escapeHtml(tip)}">`
                + `<span class="text-muted">${e.year}. ${SW_KIND_SHORT[e.kind]}</span> ${escapeHtml(swLabel(e.parties[0]))}${more}</span>`;
        }).join('');
        return `<tr><td class="text-nowrap">${personLinkHtml(p.name, p.person_id)}${p.label ? ` <span class="text-muted small">${escapeHtml(p.label)}</span>` : ''}</td>
            <td><div class="sw-path">${steps}</div></td><td class="text-end">${p.moves.length}</td></tr>`;
    }).join('') || '<tr><td colspan="3" class="text-muted">Nitko.</td></tr>';
    document.getElementById('swMore').innerHTML = rows.length > _sw.shown
        ? `<button type="button" class="btn btn-sm btn-outline-secondary">Prikaži još (${(rows.length - _sw.shown).toLocaleString('hr-HR')})</button>` : '';
}

function renderSwMethod() {
    const years = _sw.data.roster_years;
    document.getElementById('swMethod').innerHTML =
        `<b>Kako se čita.</b> Stranka je s liste na kojoj je osoba bila kandidat (Sabor, Europski parlament, 1990.–1995. i pojedinačni kandidati), a za Sabor ${years[0]}.–${years[years.length - 1]}. i iz popisa zastupnika, `
        + `jedinog izvora za 2003.–2011., kad imena kandidata na listama nisu objavljena; stranka u popisu može biti ona s kraja mandata. `
        + `Lista više stranaka (koalicija) vrijedi za sve njih: prelazak je tek kad nova lista nema nijednu stranku s prethodne, pa član manjeg partnera koji kasnije nastupi na listi svoje stranke nije prešao — a ne vidi se ni kad partner prijeđe u stranku koja je koaliciju predvodila. U tablicama se prelazak pripisuje stranci koja je listu predvodila. `
        + `Preimenovana stranka ista je stranka (Most nezavisnih lista i Most; SKH-SDP i SDP; Domovinski pokret Miroslava Škore i Domovinski pokret), a nezavisne liste su jedna skupina. `
        + `Za načelnike, gradonačelnike i župane (2009.–2025.) stranka je predlagatelj kandidata, iz arhive rezultata Državnog izbornog povjerenstva (za 2009. iz izvješća o rezultatima); kandidat grupe birača i nezavisna lista ubrajaju se u nezavisne. Dvoje lokalnih izbora u različitim županijama ne uspoređuju se: tamo je isto ime vjerojatnije dvije osobe. Za vijeća i skupštine kandidati na listama nisu poznati, pa nisu uključeni. `
        + `Osobe se povezuju po imenu, pa dvije osobe istog imena mogu izgledati kao jedna koja je prešla; zato su zadano prikazani samo oni koji su barem jednom izabrani.`;
}
