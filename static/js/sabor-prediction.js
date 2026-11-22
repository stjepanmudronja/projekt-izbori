// Sabor: "Napravi svoju predikciju" - the reader's national result per party,
// projected onto the electoral districts and turned into seats.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.
//
// Model (proportional swing): a party's share in every district is scaled by
// the same factor as its national share, every other list by the factor of
// "Ostali", and each district is renormalised to its own total. Seats then go
// by computeDHondtClient (sabor-scope.js), the simulator's own allocation: 14
// per district I-X with a 5 % district threshold, the diaspora's seats in XI,
// and the minority seats of district XII exactly as in the base election.
// With every party left at its real result the seats are the election's own.

const PRED_YEARS = [2024, 2020, 2016, 2015, 2011, 2007, 2003];   // 2000 lacks districts XI and XII
const PRED_MIN_SHARE = 1;            // parties under 1 % nationally are part of "Ostali"
const PRED_OTHERS = '__ostali';
const PRED_MINORITIES = '__manjine';
const _saPred = { ready: false, year: null, raw: {}, groups: [], others: { base: 0, pred: 0 },
                coalition: new Set(), colors: {}, fromLink: null };

// "HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ" -> "HDZ"; a name with no abbreviation stays whole.
// "MOŽEMO! - POLITIČKA PLATFORMA" -> "MOŽEMO!" (the short name first).
function predLabel(group) {
    const parts = group.split(' - ').map(x => x.trim());
    const abbr = x => /^[A-ZČĆŠŽĐ0-9!]{2,10}$/.test(x);
    if (parts.length > 1 && abbr(parts[parts.length - 1])) return parts[parts.length - 1];
    if (parts.length > 1 && abbr(parts[0])) return parts[0];
    // "UMIROVLJENICI ZAJEDNO - POLITIČKA PLATFORMA - …" -> its first part.
    if (parts.length > 1 && parts[0].length <= 40) return parts[0];
    return group;
}

// Palette colours for parties without a fixed one: the palette sorted by how
// far each colour is from the colours already on the chart (the parties' own
// and the greys of "Ostali" and the minorities), most distinct first, so the
// palette's teal does not sit next to Možemo's green. Never runs out.
function predColorsFor(labels) {
    const rgb = h => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
    const dist = (a, b) => { const x = rgb(a), y = rgb(b); return Math.hypot(x[0] - y[0], x[1] - y[1], x[2] - y[2]); };
    const used = [...labels.map(l => MAP_PARTY_COLORS[l]).filter(Boolean), '#adb5bd', '#6c757d'];
    const free = [...MAP_PALETTE].sort((a, b) => Math.min(...used.map(u => dist(u, b))) - Math.min(...used.map(u => dist(u, a))));
    let next = 0;
    return labels.map(l => MAP_PARTY_COLORS[l] || free[next++ % free.length]);
}

const predPct = v => (v ?? 0).toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';

async function initPrediction() {
    if (_saPred.ready) return;
    _saPred.ready = true;
    const sel = document.getElementById('predBaseYear');
    sel.innerHTML = PRED_YEARS.map(y => `<option value="${y}">Sabor ${y}.</option>`).join('');
    sel.addEventListener('change', () => loadPredictionYear(+sel.value));
    document.getElementById('predResetBtn').addEventListener('click', () => {
        _saPred.groups.forEach(g => { g.pred = g.base; });
        renderPrediction();
    });
    document.getElementById('predCopyBtn').addEventListener('click', copyPredictionLink);
    const link = readPredictionLink();
    if (link && PRED_YEARS.includes(link.year)) sel.value = link.year;
    _saPred.fromLink = link;
    await loadPredictionYear(+sel.value);
}

async function loadPredictionYear(year) {
    if (!_saPred.raw[year]) _saPred.raw[year] = await fetch(`/api/national/sabor-raw/${year}`).then(r => r.json());
    const raw = _saPred.raw[year];
    if (raw.error) { document.getElementById('predRows').innerHTML = `<tr><td colspan="5">${escapeHtml(raw.error)}</td></tr>`; return; }
    _saPred.year = year;
    // National shares by leading party, over the districts that elect by list.
    const votes = {};
    let total = 0;
    for (const d of raw.districts) {
        if (d.minority) continue;
        for (const l of d.lists) {
            votes[l.group || l.name] = (votes[l.group || l.name] || 0) + l.votes;
            total += l.votes;
        }
    }
    const share = v => Math.round(v / total * 1000) / 10;
    _saPred.groups = Object.entries(votes)
        .filter(([, v]) => share(v) >= PRED_MIN_SHARE)
        .sort((a, b) => b[1] - a[1])
        .map(([key, v]) => ({ key, label: predLabel(key), base: share(v), pred: share(v) }));
    _saPred.others.base = Math.round((100 - _saPred.groups.reduce((s, g) => s + g.base, 0)) * 10) / 10;
    _saPred.colors = {};
    const colors = predColorsFor(_saPred.groups.map(g => g.label));
    _saPred.groups.forEach((g, i) => { _saPred.colors[g.key] = colors[i]; });
    _saPred.colors[PRED_OTHERS] = '#adb5bd';
    _saPred.colors[PRED_MINORITIES] = '#6c757d';
    _saPred.coalition = new Set();
    // A shared link fills in its own numbers (once).
    const link = _saPred.fromLink;
    if (link && link.year === year) {
        for (const g of _saPred.groups) if (link.values[g.label] != null) g.pred = link.values[g.label];
        link.coalition.forEach(k => {
            const g = _saPred.groups.find(x => x.label === k);
            if (g) _saPred.coalition.add(g.key);
            if (k === 'manjine') _saPred.coalition.add(PRED_MINORITIES);
        });
        _saPred.fromLink = null;
    }
    renderPrediction();
}

// The base election's districts with every list's votes projected.
function predictedDistricts() {
    const raw = _saPred.raw[_saPred.year];
    const listed = Object.fromEntries(_saPred.groups.map(g => [g.key, g]));
    const others = Math.max(0, 100 - _saPred.groups.reduce((s, g) => s + g.pred, 0));
    const otherFactor = _saPred.others.base > 0 ? others / _saPred.others.base : 0;
    return raw.districts.map(d => {
        if (d.minority) return d;
        const total = d.lists.reduce((s, l) => s + l.votes, 0) || 1;
        // Listed parties as one entry each (a party may run several lists in a
        // district); everyone else keeps their own list and their own threshold.
        const scaled = {};
        for (const l of d.lists) {
            const g = listed[l.group || l.name];
            const factor = g ? (g.base > 0 ? g.pred / g.base : 0) : otherFactor;
            const name = g ? g.key : l.name;
            scaled[name] = (scaled[name] || 0) + l.votes * factor;
        }
        const sum = Object.values(scaled).reduce((s, v) => s + v, 0) || 1;
        return { ...d, lists: Object.entries(scaled).map(([name, v]) => ({ name, votes: v / sum * total })) };
    });
}

// Seats per row of the table: listed parties, "Ostali" and the minorities.
function predictionSeats(districts) {
    const { totalSeats } = computeDHondtClient(districts, {}, new Set(), new Set());
    const listed = new Set(_saPred.groups.map(g => g.key));
    const minorityNames = new Set(districts.filter(d => d.minority).flatMap(d => d.lists.map(l => l.name)));
    const out = {};
    for (const [name, n] of Object.entries(totalSeats)) {
        const key = listed.has(name) ? name : minorityNames.has(name) ? PRED_MINORITIES : PRED_OTHERS;
        out[key] = (out[key] || 0) + n;
    }
    return out;
}

function renderPrediction() {
    const raw = _saPred.raw[_saPred.year];
    const baseSeats = predictionSeats(raw.districts.map(d => d.minority ? d : {
        ...d, lists: Object.values(d.lists.reduce((acc, l) => {
            const key = _saPred.groups.some(g => g.key === (l.group || l.name)) ? (l.group || l.name) : l.name;
            acc[key] = acc[key] || { name: key, votes: 0 };
            acc[key].votes += l.votes;
            return acc;
        }, {})),
    }));
    const seats = predictionSeats(predictedDistricts());
    const totalSeats = Object.values(seats).reduce((s, v) => s + v, 0);
    const majority = Math.floor(totalSeats / 2) + 1;
    const listedSum = _saPred.groups.reduce((s, g) => s + g.pred, 0);
    const others = Math.round((100 - listedSum) * 10) / 10;

    const seatCell = key => {
        const n = seats[key] || 0, b = baseSeats[key] || 0, d = n - b;
        const diff = d ? `<span class="pred-diff ${d > 0 ? 'text-success' : 'text-danger'}">(${d > 0 ? '+' : ''}${d})</span>` : '';
        return `<b>${n}</b>${diff}`;
    };
    const check = key => `<input class="form-check-input" type="checkbox" data-pred-coal="${escapeHtml(key)}" ${_saPred.coalition.has(key) ? 'checked' : ''}>`;
    const swatch = key => `<span class="pred-swatch" style="background:${_saPred.colors[key]}"></span>`;
    document.getElementById('predRows').innerHTML = _saPred.groups.map((g, i) => `<tr>
            <td>${check(g.key)}</td>
            <td title="${escapeHtml(g.key)}">${swatch(g.key)}${escapeHtml(g.label.length > 40 ? g.label.slice(0, 38) + '…' : g.label)}</td>
            <td class="text-end text-muted">${predPct(g.base)}</td>
            <td class="text-end"><input type="number" class="form-control form-control-sm" min="0" max="100" step="0.1"
                value="${g.pred}" data-pred-idx="${i}" aria-label="Predikcija za ${escapeHtml(g.label)} u postocima"></td>
            <td class="text-end">${seatCell(g.key)}</td>
        </tr>`).join('') + `
        <tr class="pred-others"><td>${check(PRED_OTHERS)}</td><td>${swatch(PRED_OTHERS)}Ostali</td>
            <td class="text-end">${predPct(_saPred.others.base)}</td><td class="text-end">${predPct(Math.max(0, others))}</td>
            <td class="text-end">${seatCell(PRED_OTHERS)}</td></tr>
        <tr class="pred-others"><td>${check(PRED_MINORITIES)}</td><td>${swatch(PRED_MINORITIES)}Nacionalne manjine</td>
            <td class="text-end" colspan="2">kao na izborima</td><td class="text-end">${seatCell(PRED_MINORITIES)}</td></tr>`;
    document.getElementById('predSumNote').innerHTML = others < 0
        ? `<span class="text-danger"><i class="bi bi-exclamation-triangle me-1"></i>Zbroj prelazi 100 % za ${predPct(-others)}: ostale liste dobivaju 0 %, a udjeli se u svakoj jedinici svode na 100 %.</span>`
        : `<span class="text-muted">Ostali (sve ostale liste) dobivaju preostalih ${predPct(others)}. U zagradi: promjena mandata prema izborima ${_saPred.year}.</span>`;

    // Hemicycle: the coalition from the left, then the rest by seats.
    const keys = [..._saPred.groups.map(g => g.key), PRED_OTHERS, PRED_MINORITIES].filter(k => seats[k]);
    keys.sort((a, b) => (_saPred.coalition.has(b) - _saPred.coalition.has(a)) || (seats[b] - seats[a]));
    const order = keys.flatMap(k => Array(seats[k]).fill(k));
    const { positions, svgW, svgH, cx, cy, dotR } = hemicycleLayout(order.length);
    const labelOf = k => k === PRED_OTHERS ? 'Ostali' : k === PRED_MINORITIES ? 'Nacionalne manjine'
        : (_saPred.groups.find(g => g.key === k) || {}).label || k;
    const coalSeats = [..._saPred.coalition].reduce((s, k) => s + (seats[k] || 0), 0);
    document.getElementById('predHemicycle').innerHTML = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:620px; display:block; margin:0 auto;" role="img"
             aria-label="Predviđena raspodjela mandata: ${keys.map(k => `${labelOf(k)} ${seats[k]}`).join(', ')}">
            ${positions.map((pos, i) => order[i] ? `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}"
                fill="${_saPred.colors[order[i]]}" stroke="${_saPred.coalition.has(order[i]) ? '#1a1a2e' : 'white'}" stroke-width="${_saPred.coalition.has(order[i]) ? 2 : 1.5}">
                <title>${escapeHtml(labelOf(order[i]))}: ${seats[order[i]]} mandata</title></circle>` : '').join('')}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">${totalSeats}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="12" fill="#6c757d">mandata · većina ${majority}</text>
        </svg>`;
    const names = [..._saPred.coalition].map(labelOf);
    document.getElementById('predMajority').innerHTML = !_saPred.coalition.size
        ? '<span class="text-muted">Označi stranke u stupcu „Koal.” i vidi bi li imale većinu.</span>'
        : coalSeats >= majority
            ? `<span class="badge bg-success fs-6">Koalicija ima većinu: ${coalSeats} od ${totalSeats}</span><div class="small text-muted mt-1">${escapeHtml(names.join(' + '))}</div>`
            : `<span class="badge bg-secondary fs-6">Koaliciji nedostaje ${majority - coalSeats} ${majority - coalSeats === 1 ? 'mandat' : 'mandata'} do većine (${coalSeats} od ${totalSeats})</span><div class="small text-muted mt-1">${escapeHtml(names.join(' + '))}</div>`;
    document.getElementById('predMethodNote').innerHTML =
        `Polazište: izbori za Sabor ${_saPred.year}. Stranci se pripisuju glasovi lista koje je predvodila (prva navedena u koaliciji). `
        + `Udio stranke u svakoj izbornoj jedinici mijenja se u istom omjeru kao njezin ukupni udio, a udjeli se u jedinici svode na 100 %; `
        + `ostale liste mijenjaju se zajedno, svaka zadržava svoj prag. Mandati: D'Hondt, 14 po jedinici I.–X. uz prag od 5 %, dijaspora (XI.) ${_saPred.year === 2003 ? '4' : _saPred.year === 2007 ? '5' : '3'}, `
        + `a 8 mandata nacionalnih manjina kao na izborima. Ovo je model, ne anketa: stvarni rezultati ovise i o tome gdje se glasovi pomaknu.`;
}

document.addEventListener('input', e => {
    const idx = e.target.dataset && e.target.dataset.predIdx;
    if (idx === undefined) return;
    const v = parseFloat(String(e.target.value).replace(',', '.'));
    _saPred.groups[+idx].pred = Number.isFinite(v) ? Math.min(100, Math.max(0, v)) : 0;
    const active = document.activeElement === e.target, pos = e.target.selectionStart;
    renderPrediction();
    // Keep typing in the same box after the table is redrawn.
    if (active) {
        const again = document.querySelector(`[data-pred-idx="${idx}"]`);
        if (again) { again.focus(); try { again.setSelectionRange(pos, pos); } catch (_) { /* number inputs */ } }
    }
});
document.addEventListener('change', e => {
    const key = e.target.dataset && e.target.dataset.predCoal;
    if (key === undefined) return;
    if (e.target.checked) _saPred.coalition.add(key); else _saPred.coalition.delete(key);
    renderPrediction();
});

// Shareable: #predikcija=2024;HDZ:35;SDP:27.5;...;k:HDZ,manjine
function predictionHash() {
    const values = _saPred.groups.map(g => `${encodeURIComponent(g.label)}:${g.pred}`);
    const coal = [..._saPred.coalition].map(k => k === PRED_MINORITIES ? 'manjine' : k === PRED_OTHERS ? 'ostali'
        : encodeURIComponent((_saPred.groups.find(g => g.key === k) || {}).label || ''));
    return `#predikcija=${_saPred.year};${values.join(';')}${coal.length ? `;k:${coal.join(',')}` : ''}`;
}

function readPredictionLink() {
    const h = window.location.hash || '';
    if (!h.startsWith('#predikcija=')) return null;
    const parts = h.slice('#predikcija='.length).split(';');
    const out = { year: parseInt(parts[0], 10), values: {}, coalition: [] };
    for (const p of parts.slice(1)) {
        if (p.startsWith('k:')) { out.coalition = p.slice(2).split(',').map(decodeURIComponent); continue; }
        const i = p.lastIndexOf(':');
        if (i > 0) out.values[decodeURIComponent(p.slice(0, i))] = parseFloat(p.slice(i + 1));
    }
    return out;
}

async function copyPredictionLink() {
    const url = `${window.location.origin}/rezultati-koalicije-sabor${predictionHash()}`;
    history.replaceState(history.state, '', url);
    const btn = document.getElementById('predCopyBtn');
    try {
        await navigator.clipboard.writeText(url);
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Poveznica kopirana';
    } catch (_) {
        btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Poveznica je u adresnoj traci';
    }
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Kopiraj poveznicu'; }, 2500);
}

// Built the first time the card is opened; a shared link opens it straight away.
document.addEventListener('shown.bs.collapse', e => { if (e.target.id === 'saPredCollapse') initPrediction(); });
window.addEventListener('load', () => {
    if (!(window.location.hash || '').startsWith('#predikcija=')) return;
    const el = document.getElementById('saPredCollapse');
    if (el && window.bootstrap) {
        bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }).show();
        setTimeout(() => document.getElementById('saPredCard').scrollIntoView({ behavior: 'smooth', block: 'start' }), 600);
    }
});
