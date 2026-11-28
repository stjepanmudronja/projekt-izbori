// Politicians: search, the compare list and loading a politician.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// Per-module chart instances
const moduleCharts = {};
let stationCharts = [];
window._electionBarData = {};

// Search logic — scoped per module
let debounceTimer;

document.querySelectorAll('.search-input').forEach(input => {
    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        const q = input.value.trim();
        const dropdown = input.closest('.position-relative').querySelector('.dropdown-results');
        if (q.length < 2) {
            dropdown.classList.remove('show');
            return;
        }
        debounceTimer = setTimeout(() => fetchResults(input, q), 250);
    });
});

async function fetchResults(input, q) {
    const type = input.dataset.type;
    const dropdown = input.closest('.position-relative').querySelector('.dropdown-results');
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&type=${type}`);
    const data = await res.json();

    dropdown.innerHTML = '';
    if (data.length === 0) {
        dropdown.innerHTML = '<div class="dropdown-item-custom text-muted">Nema rezultata</div>';
        dropdown.classList.add('show');
        return;
    }

    data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'dropdown-item-custom';
        if (item.municipality) {
            div.innerHTML = `${item.name} <small class="text-muted">- ${item.municipality}</small>`;
        } else if (item.label) {
            // A namesake: the label is what tells the rows apart.
            div.innerHTML = `${escapeHtml(item.name)} <small class="text-muted">(${escapeHtml(item.label)})</small>`;
        } else {
            div.textContent = item.name;
        }
        div.addEventListener('click', () => {
            input.value = '';
            dropdown.classList.remove('show');
            loadDetail(type, item.id);
        });
        dropdown.appendChild(div);
    });
    dropdown.classList.add('show');
}

function getModulePanel(type) {
    return document.getElementById(`module-${type}`);
}

// Compare list for the person module
const _compareItems = { person: [] };
const compareLineColors = [
    'rgb(15, 52, 96)', 'rgb(220, 53, 69)', 'rgb(25, 135, 84)', 'rgb(255, 152, 0)',
    'rgb(156, 39, 176)', 'rgb(0, 188, 212)', 'rgb(121, 85, 72)', 'rgb(233, 30, 99)',
    'rgb(63, 81, 181)', 'rgb(76, 175, 80)',
];
const compareMaxItems = { person: 10 };

function getCompareName(type, data) {
    return `${data.first_name} ${data.last_name}${data.label ? ` (${data.label})` : ''}`;
}

function renderCompareTags(type) {
    const items = _compareItems[type];
    const tagsContainer = document.getElementById(`${type}Tags`);
    const tagsList = document.getElementById(`${type}TagsList`);

    if (items.length === 0) {
        tagsContainer.style.display = 'none';
        return;
    }

    tagsContainer.style.display = 'block';
    tagsList.innerHTML = items.map((item, i) => {
        const color = compareLineColors[i % compareLineColors.length];
        return `<span class="compare-tag" style="background:${color};">
            ${item.name}
            <span class="tag-remove" onclick="removeCompareItem('${type}', ${item.id})"><i class="bi bi-x"></i></span>
        </span>`;
    }).join('');
}

function removeCompareItem(type, id) {
    _compareItems[type] = _compareItems[type].filter(it => it.id !== id);
    renderCompareTags(type);
    rerenderCompareModule(type);
    if (type === 'person') syncPersonUrl();
}

function clearCompareList(type) {
    _compareItems[type] = [];
    renderCompareTags(type);
    const panel = getModulePanel(type);
    panel.querySelector('.detail-section').style.display = 'none';
    if (type === 'person') syncPersonUrl();
}

function rerenderCompareModule(type) {
    const panel = getModulePanel(type);
    const detailSection = panel.querySelector('.detail-section');
    const detailResults = panel.querySelector('.detail-results');
    const items = _compareItems[type];

    if (items.length === 0) {
        detailSection.style.display = 'none';
        return;
    }

    detailSection.style.display = 'block';
    renderMultiLineChart(panel, type);

    // Render result cards for each item
    const votesKey = type === 'person' ? 'candidate_votes' : 'total_votes';
    detailResults.innerHTML = items.map((item, i) => {
        const color = compareLineColors[i % compareLineColors.length];
        const filtered = filterResults(item.data.results, type);
        const renderFn = renderPersonResultsHTML;
        return `<div class="mb-4">
            <h5 style="border-left:4px solid ${color}; padding-left:0.75rem;" class="fw-bold mb-3">
                ${type === 'person' ? '<i class="bi bi-person-circle me-2"></i>' : '<i class="bi bi-people-fill me-2"></i>'}${item.name}
                ${type === 'person' ? `<button class="btn btn-sm btn-link text-muted p-0 ms-2 align-baseline" title="Kopiraj poveznicu na ovog političara" onclick="copyPersonLink(${item.id}, ${escapeHtml(JSON.stringify(item.name))}, this)"><i class="bi bi-link-45deg"></i></button>` : ''}
                ${type === 'person' ? `<span class="loyalty-slot" data-loyalty="${item.id}"></span>` : ''}
            </h5>
            ${type === 'person' ? `<div class="loyalty-note" data-loyalty-note="${item.id}"></div>` : ''}
            ${type === 'person' ? officesSummaryHtml(item.data.offices, item.data.roles) : ''}
            ${renderFn(filtered)}
        </div>`;
    }).join('');
    if (type === 'person') items.forEach(fillLoyalty);
}

// ---- Medalja vjernosti: the same party for the last ten years, still standing ----
// /api/person/<id>/loyalty (webapp/switchers.py loyalty_of); fetched after the
// page is drawn, so a slow first read never holds up the results.
async function fillLoyalty(item) {
    if (item.loyalty === undefined) {
        item.loyalty = null;
        try {
            item.loyalty = (await fetch(`/api/person/${item.id}/loyalty`).then(r => r.json())).medal;
        } catch (e) {
            return;
        }
    }
    const m = item.loyalty;
    const slot = document.querySelector(`[data-loyalty="${item.id}"]`);
    const note = document.querySelector(`[data-loyalty-note="${item.id}"]`);
    if (!m || !slot || !note) return;
    const f = m.gender === 'F';
    const party = p => p.registry_number
        ? `<a href="#" class="loyalty-party" data-reg="${p.registry_number}" title="${escapeHtml(p.name)}">${escapeHtml(p.label)}</a>`
        : `<span title="${escapeHtml(p.name)}">${escapeHtml(p.label)}</span>`;
    const career = m.kind === 'career';
    // "Vjeran" / "Vjerna"; a name that tells neither gets the medal's own name.
    const title = m.gender === 'F' ? 'Vjerna stranci' : m.gender === 'M' ? 'Vjeran stranci' : 'Medalja vjernosti';
    slot.innerHTML = `<span class="loyalty-medal${career ? '' : ' since'}" title="Medalja vjernosti stranci">`
        + `<i class="bi bi-award-fill"></i> ${title}${career ? '' : ` od ${m.from}.`}</span>`;
    note.innerHTML = career
        ? `Na svih ${m.elections} izbora od ${m.from}. do ${m.to}. nastupi${f ? 'la' : 'o'} je uz ${party(m.party)} i nikad nije promijeni${f ? 'la' : 'o'} stranku.`
        : `Od ${m.from}. do ${m.to}. na svih ${m.elections} izbora uz ${party(m.party)}${m.before ? `; prije toga ${party(m.before)}` : ''}.`;
    note.title = 'Prema listama na izborima za Sabor i Europski parlament, popisima zastupnika i predlagateljima na lokalnim izborima (2009.–2025.); koalicija vrijedi za sve svoje stranke, a samostalna lokalna lista se ne računa. Vidi Analitika → Prelasci.';
}
document.addEventListener('click', e => {
    const a = e.target.closest('.loyalty-party');
    if (!a) return;
    e.preventDefault();
    if (activateModule('parties', { pushState: false, focusInput: false })) openParty(+a.dataset.reg, { push: true });
});

function mandateWord(n) {
    return (n % 10 === 1 && n % 100 !== 11) ? 'mandat' : 'mandata';
}

// "Na dužnosti · Načelnik, KLIS · od 2013. · 4 mandata": the offices a
// politician won, read off their results (see person_offices in app.py).
function officesSummaryHtml(offices, roles) {
    offices = offices || [];
    roles = roles || [];
    if (offices.length === 0 && roles.length === 0) return '';
    const total = offices.reduce((n, o) => n + o.years.length, 0);
    // Offices the Sabor gave rather than the voters: listed by term with
    // their dates, apart from the elected mandates counted above them.
    const roleRows = roles.map(x => {
        const s = SABOR_ROLE_STYLE[x.role] || SABOR_ROLE_STYLE.secretary;
        const when = roleDatesText(x);
        const current = x.start && !x.end;
        const terms = x.sazivi.map(y => `${y}.`).join(', ');
        return `<div class="mb-1">
            ${current ? '<span class="badge bg-success me-1">Na dužnosti</span>' : ''}<span class="role-dot" style="background:${s.bg};box-shadow:0 0 6px ${s.glow};"></span><strong>${escapeHtml(x.title)}</strong>
            <span class="text-muted"> · ${when || 'saziv ' + terms}${when ? ` · saziv ${terms}` : ''}</span>
        </div>`;
    }).join('');
    const rolesBlock = roleRows ? `<div class="fw-semibold mt-2 mb-1" style="color:#0f3460;"><i class="bi bi-bank me-1"></i>Dužnosti u Saboru i Vladi</div>${roleRows}` : '';
    if (offices.length === 0) {
        return `<div class="card p-3 mb-3" style="background:#f8f9fb;">${rolesBlock}</div>`;
    }
    const rows = offices.map(o => {
        const where = o.place ? `, ${placeLinkHtml(o.place_id, o.place)}` : '';
        const when = o.current
            ? `od ${o.since}.`
            : o.years.map(y => `${y}.`).join(', ');
        return `<div class="mb-1">
            ${o.current ? '<span class="badge bg-success me-1">Na dužnosti</span>' : ''}<strong>${escapeHtml(o.title)}</strong>${where}
            <span class="text-muted"> · ${when} · ${o.years.length} ${mandateWord(o.years.length)}</span>
        </div>`;
    }).join('');
    return `<div class="card p-3 mb-3" style="background:#f8f9fb;">
        <div class="fw-semibold mb-2" style="color:#0f3460;"><i class="bi bi-award me-1"></i>Dužnosti · izabran(a) ${total === 1 ? 'jednom' : `${total} puta`}</div>
        ${rows}
        <small class="text-muted fst-italic">Prema izbornim rezultatima; ostavke, zamjene i mirovanje mandata nisu uključeni.</small>
        ${rolesBlock}
    </div>`;
}

async function loadDetail(type, id) {
    const panel = getModulePanel(type);
    const spinner = panel.querySelector('.spinner-wrapper');

    // Check if already in list
    if (_compareItems[type].find(it => it.id === id)) return;
    if (_compareItems[type].length >= compareMaxItems[type]) return;

    spinner.classList.add('show');

    const urls = { person: `/api/person/${id}` };
    const res = await fetch(urls[type]);
    const data = await res.json();

    spinner.classList.remove('show');

    const name = getCompareName(type, data);
    if (type === 'person') {
        const fullName = `${data.first_name} ${data.last_name}`.toUpperCase();
        data.results.forEach(r => r._personFullName = fullName);
    }

    _compareItems[type].push({ id, name, data });
    // Also store in _rawData for filter compatibility
    _rawData[type] = { type, data };

    renderCompareTags(type);
    rerenderCompareModule(type);
    if (type === 'person') syncPersonUrl();
}
