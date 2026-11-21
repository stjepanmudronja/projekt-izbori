// Općine i gradovi: one town's electoral history.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

let _placeShown = null;            // {id, name} of the town on show
let _placeInit = false;

function placePath(p) {
    return p ? `/mjesto/${p.id}-${urlSlug(p.name)}` : '/mjesto';
}
// A link to a town's page from anywhere ("KLIS" on a politician's office).
function placeLinkHtml(id, name) {
    if (!id) return escapeHtml(name || '');
    return `<a href="${placePath({ id, name })}" class="place-link" data-place-id="${id}" title="Otvori stranicu: ${escapeHtml(name)}">${escapeHtml(name)}</a>`;
}
document.addEventListener('click', e => {
    const a = e.target.closest && e.target.closest('.place-link');
    if (!a || e.metaKey || e.ctrlKey) return;          // a new tab opens the link itself
    e.preventDefault();
    if (!activateModule('place', { pushState: false, focusInput: false })) return;
    openPlace(parseInt(a.dataset.placeId, 10), { push: true });
});

async function initPlaceModule() {
    if (_placeInit) return;
    _placeInit = true;
    const selC = document.getElementById('placeCounty');
    const selM = document.getElementById('placeMuni');
    const counties = await (await fetch('/api/counties')).json();
    counties.forEach(c => selC.add(new Option(c.name, c.id)));
    selC.addEventListener('change', () => loadPlaceMunis(selC.value));
    selM.addEventListener('change', () => { if (selM.value) openPlace(parseInt(selM.value, 10), { push: true }); });
}
async function loadPlaceMunis(countyId, selectId) {
    const selM = document.getElementById('placeMuni');
    selM.innerHTML = '<option value="">Odabir grada/općine...</option>';
    selM.disabled = !countyId;
    if (!countyId) return;
    const munis = await (await fetch(`/api/municipalities/${countyId}`)).json();
    // County-level summary rows and pseudo-units are no town.
    munis.filter(m => !/SAŽETAK|sažetak/.test(m.name)).forEach(m => selM.add(new Option(m.name, m.id)));
    if (selectId) selM.value = String(selectId);
}
function clearPlace() {
    _placeShown = null;
    document.getElementById('placeContent').innerHTML = '';
}
async function openPlace(id, opts) {
    opts = opts || {};
    await initPlaceModule();
    const spinner = document.getElementById('placeSpinner');
    const content = document.getElementById('placeContent');
    spinner.classList.add('show');
    let d;
    try {
        const res = await fetch(`/api/place/${id}`);
        d = await res.json();
        if (!res.ok) throw new Error(d.error || res.status);
    } catch (err) {
        spinner.classList.remove('show');
        content.innerHTML = `<div class="alert alert-warning">${escapeHtml(err.message || 'Nema podataka za ovo mjesto.')}</div>`;
        return;
    }
    spinner.classList.remove('show');
    _placeShown = { id: d.id, name: d.name };
    content.innerHTML = renderPlace(d);
    // Keep the pickers on the town shown, also when it came from a link.
    const selC = document.getElementById('placeCounty');
    if (d.county_id && selC.value !== String(d.county_id)) {
        selC.value = String(d.county_id);
        await loadPlaceMunis(d.county_id, d.id);
    } else {
        document.getElementById('placeMuni').value = String(d.id);
    }
    const path = placePath(_placeShown);
    if (opts.push && window.location.pathname !== path) history.pushState({ mod: 'place' }, '', path);
}
function copyPlaceLink(btn) {
    navigator.clipboard.writeText(window.location.origin + placePath(_placeShown)).then(() => {
        btn.innerHTML = '<i class="bi bi-check2"></i>';
        setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg"></i>'; }, 1500);
    });
}

function renderPlace(d) {
    const fmtDate = (e) => e.date
        ? new Date(e.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' })
        : `${e.year}.`;
    const pct = v => (v === null || v === undefined) ? '' : formatPct(v);
    const who = w => !w ? '' : (w.person_id ? personLinkHtml(w.name, w.person_id) : escapeHtml(w.name));
    const officeName = d.type === 'grad' ? 'Gradonačelnik' : 'Načelnik';

    const current = d.current ? `
        <div class="card result-card p-3 mb-3">
            <div class="text-muted small mb-1">${escapeHtml(d.current.office || officeName)}</div>
            <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="badge bg-success">Na dužnosti</span>
                <span class="fw-bold" style="font-size:1.15rem;">${personLinkHtml(d.current.name, d.current.person_id)}</span>
                <span class="text-muted">· od ${d.current.since}. · izabran(a) ${d.current.year}. s ${formatNumber(d.current.votes)} glasova (${pct(d.current.share)})${d.current.round > 1 ? `, ${d.current.round}. krug` : ''}</span>
            </div>
            <small class="text-muted fst-italic mt-1">Prema izbornim rezultatima; ostavke i prijevremeni izbori nisu uključeni.</small>
        </div>` : '';

    const anyHolder = d.executives.some(x => x.basis === 'nositelj');
    const execRows = d.executives.map(x => `<tr>
            <td>${x.year}.</td>
            <td>${personLinkHtml(x.name, x.person_id)}${x.basis === 'nositelj' ? ' <span class="text-muted">*</span>' : ''}</td>
            <td class="text-muted small">${x.basis === 'nositelj' ? 'nositelj liste s najviše glasova' : (x.round > 1 ? `${x.round}. krug` : '1. krug')}</td>
            <td class="text-end">${formatNumber(x.votes)} <span class="text-muted small">(${pct(x.share)})</span></td>
        </tr>`).join('');
    const execs = d.executives.length ? `
        <div class="card result-card p-3 mb-3">
            <h6 class="fw-bold mb-2" style="color:#0f3460;"><i class="bi bi-person-badge me-1"></i>${d.type === 'grad' ? 'Gradonačelnici' : 'Načelnici'} kroz godine</h6>
            <div class="table-responsive"><table class="table table-sm mb-1">
                <thead><tr><th>Izbori</th><th>Ime</th><th></th><th class="text-end">Glasovi</th></tr></thead>
                <tbody>${execRows}</tbody>
            </table></div>
            ${anyHolder ? `<small class="text-muted fst-italic">* ${LIST_HOLDER_NOTE}</small>` : ''}
        </div>` : '';

    const councilRows = d.councils.map(c => {
        const [a, b] = c.lists;
        return `<tr>
            <td>${c.year}.</td>
            <td>${a ? `${escapeHtml(a.name)} <span class="text-muted small">${pct(a.share)}</span>` : ''}${a && a.holder ? `<div class="small text-muted">nositelj: ${personLinkHtml(a.holder.name, a.holder.person_id)}</div>` : ''}</td>
            <td class="small">${b ? `${escapeHtml(b.name)} <span class="text-muted">${pct(b.share)}</span>` : ''}</td>
            <td class="text-end">${pct(c.turnout_pct)}</td>
        </tr>`;
    }).join('');
    const councils = d.councils.length ? `
        <div class="card result-card p-3 mb-3">
            <h6 class="fw-bold mb-2" style="color:#0f3460;"><i class="bi bi-people me-1"></i>${d.type === 'grad' ? 'Gradsko' : 'Općinsko'} vijeće kroz godine</h6>
            <div class="table-responsive"><table class="table table-sm mb-0">
                <thead><tr><th>Izbori</th><th>Lista s najviše glasova</th><th>Druga lista</th><th class="text-end">Izlaznost</th></tr></thead>
                <tbody>${councilRows}</tbody>
            </table></div>
        </div>` : '';

    const allRows = d.elections.map(e => `<tr>
            <td class="small" style="white-space:nowrap;">${fmtDate(e)}</td>
            <td class="small">${escapeHtml(e.election_type)}${e.round > 1 ? ` <span class="badge bg-warning text-dark">${e.round}. krug</span>` : ''}</td>
            <td class="small">${who(e.winner)}</td>
            <td class="text-end small">${e.winner ? pct(e.winner.share) : ''}</td>
            <td class="text-end small">${pct(e.turnout_pct)}</td>
        </tr>`).join('');
    const all = `
        <details class="card result-card p-3 mb-3">
            <summary class="fw-bold" style="color:#0f3460; cursor:pointer;"><i class="bi bi-list-ul me-1"></i>Svi izbori u mjestu (${d.elections.length})</summary>
            <div class="table-responsive mt-2"><table class="table table-sm table-hover mb-0">
                <thead><tr><th>Datum</th><th>Izbori</th><th>Prvo mjesto</th><th class="text-end">Udio</th><th class="text-end">Izlaznost</th></tr></thead>
                <tbody>${allRows}</tbody>
            </table></div>
        </details>`;

    return `
        <div class="d-flex align-items-baseline gap-2 flex-wrap mb-3">
            <h4 class="fw-bold mb-0">${escapeHtml(d.name)}</h4>
            <span class="badge bg-secondary">${d.type === 'grad' ? 'grad' : d.type === 'općina' ? 'općina' : escapeHtml(d.type || '')}</span>
            <span class="text-muted">${escapeHtml(d.county || '')}</span>
            <button class="btn btn-sm btn-link text-muted p-0" title="Kopiraj poveznicu na ovo mjesto" onclick="copyPlaceLink(this)"><i class="bi bi-link-45deg"></i></button>
        </div>
        ${current}${execs}${councils}${all}`;
}
