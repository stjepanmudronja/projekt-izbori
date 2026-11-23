// Sabor: "Što ako? Druga izborna pravila" - the same votes, other rules.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.
//
// The reader picks a past election and changes the rules for the 140 seats of
// districts I-X: the counting method (D'Hondt, Sainte-Laguë, largest remainder),
// the threshold (0-10 %, in each district or nationally) and the districts
// (today's ten of 14 seats, or all of Croatia as one district of 140). The
// diaspora (XI) and the minorities (XII) keep the seats they had. Votes are
// the election's own, by list; a list's seats count for the party leading it
// (first named, `group` of /api/national/sabor-raw). With the real rules the
// seats must equal /api/national/sabor-seats party by party (browser check).

const SR_YEARS = [2024, 2020, 2016, 2015, 2011, 2007, 2003, 2000];
const SR_REAL = { method: 'dh', single: false, threshold: 5, national: false };
const SR_METHODS = { dh: "D'Hondt", sl: 'Sainte-Laguë', hare: 'Najveći ostatak (Hare)' };
const SR_MINORITIES = '__manjine';
const _saRules = { ready: false, year: null, raw: {}, rules: { ...SR_REAL }, coalition: new Set(),
                   colors: {}, fromLink: null };

// Seats for {name: votes} by one method. Ties go to the list with more votes.
function srAllocate(votes, seats, method) {
    const entries = Object.entries(votes).filter(([, v]) => v > 0);
    const out = Object.fromEntries(entries.map(([n]) => [n, 0]));
    if (!entries.length || seats <= 0) return out;
    if (method === 'hare') {
        const total = entries.reduce((s, [, v]) => s + v, 0);
        const quota = total / seats;
        let given = 0;
        const rest = entries.map(([n, v]) => {
            out[n] = Math.floor(v / quota);
            given += out[n];
            return { n, r: v / quota - out[n], v };
        }).sort((a, b) => b.r - a.r || b.v - a.v);
        for (let i = 0; given < seats; i = (i + 1) % rest.length, given++) out[rest[i].n] += 1;
        return out;
    }
    const divisor = method === 'sl' ? k => 2 * k + 1 : k => k + 1;     // k seats already won
    const quotients = [];
    for (const [n, v] of entries) for (let k = 0; k < seats; k++) quotients.push({ n, q: v / divisor(k), v });
    quotients.sort((a, b) => b.q - a.q || b.v - a.v);
    for (const { n } of quotients.slice(0, seats)) out[n] += 1;
    return out;
}

// Seats per leading party (and the minorities) under the given rules.
function srSeats(raw, rules) {
    const seats = {};
    const add = (group, n) => { if (n) seats[group] = (seats[group] || 0) + n; };
    const domestic = raw.districts.filter(d => !d.minority && d.seats === 14);
    // The threshold counts by list in a district; nationally by leading party,
    // the party a voter recognises on every district's ballot.
    const groupOf = {};
    const nationalVotes = {};
    let nationalTotal = 0;
    for (const d of domestic) for (const l of d.lists) {
        groupOf[l.name] = l.group || l.name;
        nationalVotes[groupOf[l.name]] = (nationalVotes[groupOf[l.name]] || 0) + l.votes;
        nationalTotal += l.votes;
    }
    const passesNationally = g => nationalVotes[g] >= nationalTotal * rules.threshold / 100;
    if (rules.single) {
        const eligible = Object.fromEntries(Object.entries(nationalVotes).filter(([g]) => passesNationally(g)));
        const won = srAllocate(eligible, domestic.reduce((s, d) => s + d.seats, 0), rules.method);
        for (const [g, n] of Object.entries(won)) add(g, n);
    } else {
        for (const d of domestic) {
            const total = d.lists.reduce((s, l) => s + l.votes, 0);
            const eligible = {};
            for (const l of d.lists) {
                const ok = rules.national ? passesNationally(groupOf[l.name]) : l.votes >= total * rules.threshold / 100;
                if (ok) eligible[l.name] = (eligible[l.name] || 0) + l.votes;
            }
            for (const [name, n] of Object.entries(srAllocate(eligible, d.seats, rules.method))) add(groupOf[name], n);
        }
    }
    // As at the election: the diaspora by D'Hondt without a threshold, the minorities' named seats.
    for (const d of raw.districts) {
        if (d.minority) { add(SR_MINORITIES, d.lists.reduce((s, l) => s + (l.fixed_seats || 1), 0)); continue; }
        if (d.seats === 14) continue;
        const votes = {};
        for (const l of d.lists) votes[l.name] = (votes[l.name] || 0) + l.votes;
        for (const [name, n] of Object.entries(srAllocate(votes, d.seats, 'dh'))) add(d.lists.find(l => l.name === name).group || name, n);
    }
    return { seats, nationalVotes, nationalTotal };
}

async function initRules() {
    if (_saRules.ready) return;
    _saRules.ready = true;
    const sel = document.getElementById('srYear');
    sel.innerHTML = SR_YEARS.map(y => `<option value="${y}">Sabor ${y}.${y === 2000 ? ' (bez XI. i XII.)' : ''}</option>`).join('');
    sel.addEventListener('change', () => loadRulesYear(+sel.value));
    document.getElementById('srControls').addEventListener('change', readRulesControls);
    document.getElementById('srThreshold').addEventListener('input', readRulesControls);
    document.getElementById('srPresets').addEventListener('click', e => {
        const b = e.target.closest('[data-sr-preset]');
        if (!b) return;
        const presets = {
            real: SR_REAL,
            p3: { ...SR_REAL, threshold: 3 },
            p0: { ...SR_REAL, threshold: 0 },
            sl: { ...SR_REAL, method: 'sl' },
            one: { ...SR_REAL, single: true, national: true },
        };
        _saRules.rules = { ...presets[b.dataset.srPreset] };
        writeRulesControls();
        renderRules();
    });
    document.getElementById('srCopyBtn').addEventListener('click', copyRulesLink);
    const link = readRulesLink();
    if (link) {
        if (SR_YEARS.includes(link.year)) sel.value = link.year;
        _saRules.rules = link.rules;
        _saRules.fromLink = link;
    }
    writeRulesControls();
    await loadRulesYear(+sel.value);
}

async function loadRulesYear(year) {
    if (!_saRules.raw[year]) _saRules.raw[year] = await fetch(`/api/national/sabor-raw/${year}`).then(r => r.json());
    const raw = _saRules.raw[year];
    if (raw.error) { document.getElementById('srRows').innerHTML = `<tr><td colspan="5">${escapeHtml(raw.error)}</td></tr>`; return; }
    _saRules.year = year;
    _saRules.coalition = new Set();
    const link = _saRules.fromLink;
    if (link && link.year === year) {
        link.coalition.forEach(label => {
            if (label === 'manjine') { _saRules.coalition.add(SR_MINORITIES); return; }
            const g = Object.keys(srSeats(raw, SR_REAL).nationalVotes).find(k => predLabel(k) === label);
            if (g) _saRules.coalition.add(g);
        });
        _saRules.fromLink = null;
    }
    renderRules();
}

function readRulesControls() {
    const r = _saRules.rules;
    r.method = document.querySelector('input[name="srMethod"]:checked').value;
    r.single = document.getElementById('srSingle').checked;
    r.threshold = +document.getElementById('srThreshold').value;
    r.national = r.single || document.getElementById('srNational').checked;
    writeRulesControls();
    renderRules();
}

function writeRulesControls() {
    const r = _saRules.rules;
    document.querySelector(`input[name="srMethod"][value="${r.method}"]`).checked = true;
    document.getElementById('srSingle').checked = r.single;
    document.getElementById('srTen').checked = !r.single;
    document.getElementById('srThreshold').value = r.threshold;
    document.getElementById('srThresholdVal').textContent = predPct(r.threshold).replace(',0 %', ' %');
    document.getElementById('srNational').checked = r.national;
    document.getElementById('srLocal').checked = !r.national;
    // One district: "in the district" and "nationally" are the same thing.
    document.getElementById('srLocal').disabled = r.single;
    const isReal = r.method === SR_REAL.method && r.single === SR_REAL.single && r.threshold === SR_REAL.threshold && r.national === SR_REAL.national;
    document.getElementById('srRealNote').style.display = isReal ? '' : 'none';
}

function renderRules() {
    const raw = _saRules.raw[_saRules.year];
    if (!raw || raw.error) return;
    const real = srSeats(raw, SR_REAL);
    const now = srSeats(raw, _saRules.rules);
    const share = g => g === SR_MINORITIES ? null : (real.nationalVotes[g] || 0) / real.nationalTotal * 100;
    // Rows: every party with a seat either way, then the rest as one line.
    const keys = [...new Set([...Object.keys(real.seats), ...Object.keys(now.seats)])].filter(k => k !== SR_MINORITIES)
        .sort((a, b) => (real.seats[b] || 0) - (real.seats[a] || 0) || (now.seats[b] || 0) - (now.seats[a] || 0) || share(b) - share(a));
    if (real.seats[SR_MINORITIES]) keys.push(SR_MINORITIES);
    const restShare = Object.keys(real.nationalVotes).filter(g => !keys.includes(g)).reduce((s, g) => s + share(g), 0);
    const labelOf = k => k === SR_MINORITIES ? 'Nacionalne manjine' : predLabel(k);
    const partyKeys = keys.filter(k => k !== SR_MINORITIES);
    const colors = predColorsFor(partyKeys.map(predLabel));
    _saRules.colors = Object.fromEntries(partyKeys.map((k, i) => [k, colors[i]]));
    _saRules.colors[SR_MINORITIES] = '#6c757d';

    const total = Object.values(now.seats).reduce((s, v) => s + v, 0);
    const realTotal = Object.values(real.seats).reduce((s, v) => s + v, 0);
    const majority = Math.floor(total / 2) + 1;
    const diff = k => {
        const d = (now.seats[k] || 0) - (real.seats[k] || 0);
        return d ? `<span class="${d > 0 ? 'text-success' : 'text-danger'} fw-semibold">${d > 0 ? '+' : '−'}${Math.abs(d)}</span>` : '<span class="text-muted">–</span>';
    };
    const swatch = k => `<span class="pred-swatch" style="background:${_saRules.colors[k]}"></span>`;
    const check = k => `<input class="form-check-input" type="checkbox" data-sr-coal="${escapeHtml(k)}" ${_saRules.coalition.has(k) ? 'checked' : ''} aria-label="U koaliciji: ${escapeHtml(labelOf(k))}">`;
    document.getElementById('srRows').innerHTML = keys.map(k => `<tr>
            <td>${check(k)}</td>
            <td title="${escapeHtml(k === SR_MINORITIES ? 'XII. izborna jedinica' : k)}">${swatch(k)}${escapeHtml(labelOf(k).length > 40 ? labelOf(k).slice(0, 38) + '…' : labelOf(k))}</td>
            <td class="text-end text-muted">${k === SR_MINORITIES ? 'XII.' : predPct(share(k))}</td>
            <td class="text-end">${real.seats[k] || 0}</td>
            <td class="text-end"><b>${now.seats[k] || 0}</b></td>
            <td class="text-end">${diff(k)}</td>
        </tr>`).join('') + (restShare > 0.05 ? `<tr class="pred-others"><td></td><td>Ostale liste</td>
            <td class="text-end">${predPct(restShare)}</td><td class="text-end">0</td><td class="text-end">0</td><td></td></tr>` : '');

    // Hemicycle: the coalition from the left, then the rest by seats.
    const order = keys.filter(k => now.seats[k])
        .sort((a, b) => (_saRules.coalition.has(b) - _saRules.coalition.has(a)) || (now.seats[b] - now.seats[a]))
        .flatMap(k => Array(now.seats[k]).fill(k));
    const { positions, svgW, svgH, cx, cy, dotR } = hemicycleLayout(order.length);
    const inCoal = k => _saRules.coalition.has(k);
    document.getElementById('srHemicycle').innerHTML = `
        <svg viewBox="0 0 ${svgW} ${svgH}" style="width:100%; max-width:620px; display:block; margin:0 auto;" role="img"
             aria-label="Raspodjela mandata po novim pravilima: ${keys.filter(k => now.seats[k]).map(k => `${labelOf(k)} ${now.seats[k]}`).join(', ')}">
            ${positions.map((pos, i) => order[i] ? `<circle cx="${pos.x.toFixed(1)}" cy="${pos.y.toFixed(1)}" r="${dotR}"
                fill="${_saRules.colors[order[i]]}" stroke="${inCoal(order[i]) ? '#1a1a2e' : 'white'}" stroke-width="${inCoal(order[i]) ? 2 : 1.5}">
                <title>${escapeHtml(labelOf(order[i]))}: ${now.seats[order[i]]} mandata</title></circle>` : '').join('')}
            <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="28" font-weight="bold" fill="#1a1a2e">${total}</text>
            <text x="${cx}" y="${cy + 8}" text-anchor="middle" font-size="12" fill="#6c757d">mandata · većina ${majority}</text>
        </svg>`;

    // What changed, in words.
    const parties = s => Object.keys(s).filter(k => k !== SR_MINORITIES && s[k] > 0).length;
    const biggest = s => Object.keys(s).filter(k => k !== SR_MINORITIES).sort((a, b) => s[b] - s[a])[0];
    const b = biggest(now.seats);
    const coalSeats = [..._saRules.coalition].reduce((s, k) => s + (now.seats[k] || 0), 0);
    const coalReal = [..._saRules.coalition].reduce((s, k) => s + (real.seats[k] || 0), 0);
    const names = [..._saRules.coalition].map(labelOf).join(' + ');
    document.getElementById('srSummary').innerHTML = `
        <div>Stranaka u Saboru: <b>${parties(now.seats)}</b> <span class="text-muted">(stvarno ${parties(real.seats)})</span>
            · najveća: <b>${escapeHtml(labelOf(b))} ${now.seats[b]}</b> <span class="text-muted">(stvarno ${real.seats[b] || 0})</span></div>
        <div class="mt-2">${!_saRules.coalition.size
            ? '<span class="text-muted">Označi stranke u stupcu „Koal.” i vidi bi li po ovim pravilima imale većinu.</span>'
            : `<span class="badge ${coalSeats >= majority ? 'bg-success' : 'bg-secondary'} fs-6">${coalSeats >= majority ? 'Većina' : `Nedostaje ${majority - coalSeats}`}: ${coalSeats} od ${total}</span>
               <span class="small text-muted ms-1">stvarno ${coalReal} od ${realTotal} · ${escapeHtml(names)}</span>`}</div>`;
    const r = _saRules.rules;
    const xi = raw.districts.find(d => !d.minority && d.seats !== 14);
    document.getElementById('srMethodNote').innerHTML =
        `Glasovi su s izbora za Sabor ${_saRules.year}. Mijenjaju se samo pravila za ${raw.districts.filter(d => !d.minority && d.seats === 14).length * 14} mandata izbornih jedinica I.–X.: `
        + `${r.single ? 'jedna izborna jedinica za cijelu Hrvatsku' : 'deset jedinica po 14 mandata'}, ${SR_METHODS[r.method]}, `
        + `${r.threshold ? `prag ${predPct(r.threshold).replace(',0 %', ' %')} ${r.national ? 'na razini države (zbroj lista koje stranka predvodi)' : 'u svakoj jedinici'}` : 'bez praga'}. `
        + `${xi ? `Dijaspora (XI., ${xi.seats} mandata) i ` : ''}${raw.districts.some(d => d.minority) ? 'nacionalne manjine (XII.) zadržavaju mandate kao na izborima. ' : ''}`
        + `Mandati liste pripisuju se stranci koja ju je predvodila (prva navedena u koaliciji). `
        + `Pretpostavka je da bi birači glasovali jednako i po drugim pravilima — u stvarnosti bi se stranke i birači prilagodili (npr. manje glasova za stranke koje ne bi prešle prag).`;
}

document.addEventListener('change', e => {
    const key = e.target.dataset && e.target.dataset.srCoal;
    if (key === undefined) return;
    if (e.target.checked) _saRules.coalition.add(key); else _saRules.coalition.delete(key);
    renderRules();
});

// Shareable: #pravila=2024;m:sl;j:1;p:3;o:d;k:HDZ,DP
function rulesHash() {
    const r = _saRules.rules;
    const coal = [..._saRules.coalition].map(k => k === SR_MINORITIES ? 'manjine' : encodeURIComponent(predLabel(k)));
    return `#pravila=${_saRules.year};m:${r.method};j:${r.single ? 1 : 10};p:${r.threshold};o:${r.national ? 'd' : 'j'}${coal.length ? `;k:${coal.join(',')}` : ''}`;
}

function readRulesLink() {
    const h = window.location.hash || '';
    if (!h.startsWith('#pravila=')) return null;
    const parts = h.slice('#pravila='.length).split(';');
    const rules = { ...SR_REAL };
    const out = { year: parseInt(parts[0], 10), rules, coalition: [] };
    for (const p of parts.slice(1)) {
        const [k, v] = [p.slice(0, p.indexOf(':')), p.slice(p.indexOf(':') + 1)];
        if (k === 'm' && SR_METHODS[v]) rules.method = v;
        if (k === 'j') rules.single = v === '1';
        if (k === 'p' && Number.isFinite(+v)) rules.threshold = Math.min(10, Math.max(0, +v));
        if (k === 'o') rules.national = v === 'd';
        if (k === 'k') out.coalition = v.split(',').map(decodeURIComponent);
    }
    if (rules.single) rules.national = true;
    return out;
}

async function copyRulesLink() {
    const url = `${window.location.origin}/rezultati-koalicije-sabor${rulesHash()}`;
    history.replaceState(history.state, '', url);
    const btn = document.getElementById('srCopyBtn');
    try {
        await navigator.clipboard.writeText(url);
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Poveznica kopirana';
    } catch (_) {
        btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Poveznica je u adresnoj traci';
    }
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Kopiraj poveznicu'; }, 2500);
}

// Built the first time the card is opened; a shared link opens it straight away.
document.addEventListener('shown.bs.collapse', e => { if (e.target.id === 'srCollapse') initRules(); });
window.addEventListener('load', () => {
    if (!(window.location.hash || '').startsWith('#pravila=')) return;
    const el = document.getElementById('srCollapse');
    if (el && window.bootstrap) {
        bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }).show();
        setTimeout(() => document.getElementById('srCard').scrollIntoView({ behavior: 'smooth', block: 'start' }), 600);
    }
});
