// Predsjednički: "Simuliraj drugi krug" - the reader decides where the
// round-1 voters of the eliminated candidates go, and sees who would win.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.
//
// Model: each finalist keeps their round-1 voters, less the share the reader
// says stays home; each eliminated candidate's voters split between the two
// finalists by the reader's slider, less the share that stays home. Nothing
// else changes (no new voters). The defaults are neutral on purpose - an even
// split and nobody staying home - so the page assumes nothing for the reader.

const RS_YEARS = [2024, 2019, 2014, 2009, 2005, 2000];        // the elections with a runoff
const _rs = { ready: false, year: null, data: {}, finalists: [], others: [], finalStay: [0, 0],
              colors: ['#1f4ea8', '#e2231a'], fromLink: null };

const rsPct = v => (v ?? 0).toLocaleString('hr-HR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + ' %';
const rsNum = v => Math.round(v).toLocaleString('hr-HR');
const rsSurname = n => n.split(' ').slice(-1)[0];

async function initRunoff() {
    if (_rs.ready) return;
    _rs.ready = true;
    const sel = document.getElementById('rsYear');
    sel.innerHTML = RS_YEARS.map(y => `<option value="${y}">Predsjednički izbori ${y}.</option>`).join('');
    sel.addEventListener('change', () => loadRunoffYear(+sel.value));
    document.getElementById('rsResetBtn').addEventListener('click', () => {
        _rs.others.forEach(o => { o.toB = 50; o.stay = 0; });
        _rs.finalStay = [0, 0];
        renderRunoffRows();
    });
    document.getElementById('rsCopyBtn').addEventListener('click', copyRunoffLink);
    const link = readRunoffLink();
    if (link && RS_YEARS.includes(link.year)) sel.value = link.year;
    _rs.fromLink = link;
    await loadRunoffYear(+sel.value);
}

async function loadRunoffYear(year) {
    if (!_rs.data[year]) _rs.data[year] = await fetch(`/api/national/results/predsjednicki/${year}`).then(r => r.json());
    const d = _rs.data[year];
    const r1 = (d.elections || []).find(e => e.round === 1);
    const r2 = (d.elections || []).find(e => e.round === 2);
    if (!r1 || !r2) { document.getElementById('rsRows').innerHTML = '<tr><td colspan="4">Za ove izbore nema oba kruga.</td></tr>'; return; }
    _rs.year = year;
    const finalistNames = r2.top_candidates.map(c => c.name);
    const r1Votes = Object.fromEntries(r1.top_candidates.map(c => [c.name, c.votes]));
    // Finalist A is the round-1 leader.
    _rs.finalists = finalistNames.map(n => ({ name: n, votes: r1Votes[n] || 0, r2: r2.top_candidates.find(c => c.name === n).votes }))
        .sort((a, b) => b.votes - a.votes);
    _rs.others = r1.top_candidates.filter(c => !finalistNames.includes(c.name))
        .sort((a, b) => b.votes - a.votes)
        .map(c => ({ name: c.name, votes: c.votes, toB: 50, stay: 0 }));
    _rs.finalStay = [0, 0];
    _rs.r1 = r1; _rs.r2 = r2;
    // Each finalist's own colour; the second takes another where the two would look alike (Mesić, Budiša).
    const [a, b] = _rs.finalists.map(f => MAP_PARTY_COLORS[f.name]);
    const rgb = h => { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
    const close = (x, y) => Math.hypot(...rgb(x).map((v, i) => v - rgb(y)[i])) < 90;
    _rs.colors = [a || '#1f4ea8', b && !(a && close(a, b)) ? b : (a && close(a, '#1f4ea8') ? '#8e44ad' : '#1f4ea8')];
    if (a === undefined && _rs.colors[1] === '#1f4ea8') _rs.colors[0] = '#e2231a';
    // A shared link fills in its own choices (once).
    const link = _rs.fromLink;
    if (link && link.year === year) {
        link.others.forEach((o, i) => { if (_rs.others[i]) Object.assign(_rs.others[i], o); });
        if (link.finalStay) _rs.finalStay = link.finalStay;
        _rs.fromLink = null;
    }
    renderRunoffRows();
}

function renderRunoffRows() {
    const [A, B] = _rs.finalists;
    const sw = i => `<span class="rs-swatch" style="background:${_rs.colors[i]}"></span>`;
    const stayInput = (attr, v, who) => `<input type="number" class="form-control form-control-sm" min="0" max="100" step="1"
        value="${v}" ${attr} aria-label="Postotak birača koji ne izlaze: ${escapeHtml(who)}">`;
    document.getElementById('rsRows').innerHTML = _rs.finalists.map((f, i) => `<tr>
            <td>${sw(i)}<b>${escapeHtml(f.name)}</b> <span class="text-muted small">(u drugom krugu)</span></td>
            <td class="text-end">${rsNum(f.votes)} <span class="text-muted small">${rsPct(f.votes / _rs.r1.valid_ballots * 100)}</span></td>
            <td class="text-muted small">zadržava svoje birače</td>
            <td class="text-end">${stayInput(`data-rs-fstay="${i}"`, _rs.finalStay[i], f.name)}</td>
        </tr>`).join('') + _rs.others.map((o, i) => `<tr>
            <td>${escapeHtml(o.name)}</td>
            <td class="text-end">${rsNum(o.votes)} <span class="text-muted small">${rsPct(o.votes / _rs.r1.valid_ballots * 100)}</span></td>
            <td><input type="range" min="0" max="100" step="5" value="${o.toB}" data-rs-split="${i}"
                    aria-label="Udio birača kandidata ${escapeHtml(o.name)} koji idu kandidatu ${escapeHtml(B.name)}">
                <div class="rs-split"><span data-rs-left="${i}"></span><span data-rs-right="${i}"></span></div></td>
            <td class="text-end">${stayInput(`data-rs-stay="${i}"`, o.stay, o.name)}</td>
        </tr>`).join('');
    updateRunoff();
}

// Recomputed on every slider move; only the numbers change, so the control in use keeps focus.
function updateRunoff() {
    const [A, B] = _rs.finalists;
    let a = A.votes * (1 - _rs.finalStay[0] / 100);
    let b = B.votes * (1 - _rs.finalStay[1] / 100);
    _rs.others.forEach((o, i) => {
        const voting = o.votes * (1 - o.stay / 100);
        a += voting * (1 - o.toB / 100);
        b += voting * (o.toB / 100);
        const l = document.querySelector(`[data-rs-left="${i}"]`), r = document.querySelector(`[data-rs-right="${i}"]`);
        if (l) l.textContent = `${100 - o.toB} % ${rsSurname(A.name)}`;
        if (r) r.textContent = `${rsSurname(B.name)} ${o.toB} %`;
    });
    const total = a + b || 1;
    const pa = a / total * 100, pb = b / total * 100;
    const winner = a >= b ? A : B;
    const r2total = A.r2 + B.r2;
    const real = `Stvarni drugi krug: ${escapeHtml(A.name)} <b>${rsPct(A.r2 / r2total * 100)}</b> (${rsNum(A.r2)}) – ${escapeHtml(B.name)} <b>${rsPct(B.r2 / r2total * 100)}</b> (${rsNum(B.r2)})`;
    document.getElementById('rsResult').innerHTML = `
        <div class="rs-bar mb-2" role="img" aria-label="Simulacija: ${escapeHtml(A.name)} ${rsPct(pa)}, ${escapeHtml(B.name)} ${rsPct(pb)}">
            <div style="flex:${pa} 1 0; background:${_rs.colors[0]}">${pa >= 12 ? `${escapeHtml(rsSurname(A.name))} ${rsPct(pa)}` : ''}</div>
            <div style="flex:${pb} 1 0; background:${_rs.colors[1]}; justify-content:flex-end;">${pb >= 12 ? `${escapeHtml(rsSurname(B.name))} ${rsPct(pb)}` : ''}</div>
        </div>
        <div class="fs-6"><span class="badge ${Math.abs(a - b) < 1 ? 'bg-warning text-dark' : 'bg-success'} me-2">${Math.abs(a - b) < 1 ? 'Izjednačeno' : `Pobjednik: ${escapeHtml(winner.name)}`}</span>
            ${escapeHtml(A.name)} ${rsNum(a)} (${rsPct(pa)}) · ${escapeHtml(B.name)} ${rsNum(b)} (${rsPct(pb)}) · razlika ${rsNum(Math.abs(a - b))} glasova</div>
        <div class="small text-muted mt-1">Glasalo bi oko ${rsNum(total)} birača (${rsPct(total / _rs.r1.registered_voters * 100)} upisanih, samo važeći glasovi).</div>
        <div class="small mt-1">${real}</div>`;
    document.getElementById('rsNote').textContent =
        `Glasovi su iz prvog kruga izbora ${_rs.year}. Svaki finalist zadržava svoje birače osim onih koji ne izađu; birači ispalih kandidata dijele se između finalista prema klizaču, osim onih koji ne izađu. `
        + `Novi birači koji u prvom krugu nisu glasovali nisu uključeni, pa simulacija ne mora dati stvarni rezultat ni kad su postavke dobre.`;
}

document.addEventListener('input', e => {
    const t = e.target, ds = t.dataset || {};
    const clamp = v => Math.min(100, Math.max(0, Number.isFinite(v) ? v : 0));
    if (ds.rsSplit !== undefined) _rs.others[+ds.rsSplit].toB = clamp(+t.value);
    else if (ds.rsStay !== undefined) _rs.others[+ds.rsStay].stay = clamp(parseFloat(String(t.value).replace(',', '.')));
    else if (ds.rsFstay !== undefined) _rs.finalStay[+ds.rsFstay] = clamp(parseFloat(String(t.value).replace(',', '.')));
    else return;
    updateRunoff();
});

// Shareable: #drugi-krug=2024;o=50:0,70:20,...;f=0:10 (others in round-1 order)
function runoffHash() {
    return `#drugi-krug=${_rs.year};o=${_rs.others.map(o => `${o.toB}:${o.stay}`).join(',')};f=${_rs.finalStay.join(':')}`;
}

function readRunoffLink() {
    const h = window.location.hash || '';
    if (!h.startsWith('#drugi-krug=')) return null;
    const parts = h.slice('#drugi-krug='.length).split(';');
    const out = { year: parseInt(parts[0], 10), others: [], finalStay: null };
    for (const p of parts.slice(1)) {
        if (p.startsWith('o=')) out.others = p.slice(2).split(',').map(x => { const [toB, stay] = x.split(':').map(Number); return { toB, stay }; });
        if (p.startsWith('f=')) out.finalStay = p.slice(2).split(':').map(Number);
    }
    return out;
}

async function copyRunoffLink() {
    const url = `${window.location.origin}/predsjednicki-izbori${runoffHash()}`;
    history.replaceState(history.state, '', url);
    const btn = document.getElementById('rsCopyBtn');
    try {
        await navigator.clipboard.writeText(url);
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Poveznica kopirana';
    } catch (_) {
        btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Poveznica je u adresnoj traci';
    }
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Kopiraj poveznicu'; }, 2500);
}

// Built the first time the card is opened; a shared link opens it straight away.
document.addEventListener('shown.bs.collapse', e => { if (e.target.id === 'rsCollapse') initRunoff(); });
window.addEventListener('load', () => {
    if (!(window.location.hash || '').startsWith('#drugi-krug=')) return;
    const el = document.getElementById('rsCollapse');
    if (el && window.bootstrap) {
        bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }).show();
        setTimeout(() => document.getElementById('rsCard').scrollIntoView({ behavior: 'smooth', block: 'start' }), 600);
    }
});
