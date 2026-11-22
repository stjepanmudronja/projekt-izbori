// Prema lokaciji: "Moje područje" - several counties and towns added up.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.
//
// "Dodaj u moje područje" adds the town chosen in the dropdowns (or the
// county, when no town is), "Prikaži zbroj" asks /api/location-results for
// all their polling stations together (a county and a town inside it count
// once) and shows the result like one place. The area is shareable:
// /prema-lokaciji#podrucje=m:439,556;c:17

const _area = { items: [] };          // [{type: 'm' | 'c', id, name}]

function renderAreaChips() {
    document.getElementById('areaBox').style.display = _area.items.length ? '' : 'none';
    document.getElementById('areaChips').innerHTML = _area.items.map((it, i) => `<span class="area-chip">
            ${escapeHtml(it.name)} <span class="area-kind">${it.type === 'c' ? 'županija' : 'grad/općina'}</span>
            <button type="button" data-area-remove="${i}" title="Ukloni iz područja" aria-label="Ukloni ${escapeHtml(it.name)}">×</button>
        </span>`).join('');
}

function addCurrentPlaceToArea() {
    const muni = parseInt(selMunicipality.value, 10);
    const county = parseInt(selCounty.value, 10);
    const item = muni ? { type: 'm', id: muni, name: selMunicipality.options[selMunicipality.selectedIndex].textContent.trim() }
        : county ? { type: 'c', id: county, name: selCounty.options[selCounty.selectedIndex].textContent.trim() } : null;
    if (!item || _area.items.some(x => x.type === item.type && x.id === item.id)) return;
    _area.items.push(item);
    renderAreaChips();
}

function areaParams() {
    const params = new URLSearchParams();
    const m = _area.items.filter(x => x.type === 'm').map(x => x.id);
    const c = _area.items.filter(x => x.type === 'c').map(x => x.id);
    if (m.length) params.set('municipality_ids', m.join(','));
    if (c.length) params.set('county_ids', c.join(','));
    return params;
}

async function loadAreaResults() {
    if (!_area.items.length) return;
    const spinner = document.getElementById('locationSpinner');
    document.getElementById('locationDetailSection').style.display = 'none';
    document.getElementById('stationMapCard').style.display = 'none';
    spinner.classList.add('show');
    let data;
    try {
        data = await fetch(`/api/location-results?${areaParams()}`).then(r => r.json());
    } finally {
        spinner.classList.remove('show');
    }
    if (data.error) return;
    // The server's names and order (towns, then counties) are the area's.
    if (data.area && data.area.length) { _area.items = data.area; renderAreaChips(); }
    renderLocationData(data, null);
}

function areaHash() {
    const m = _area.items.filter(x => x.type === 'm').map(x => x.id);
    const c = _area.items.filter(x => x.type === 'c').map(x => x.id);
    return `#podrucje=${[m.length ? `m:${m.join(',')}` : '', c.length ? `c:${c.join(',')}` : ''].filter(Boolean).join(';')}`;
}

async function copyAreaLink() {
    const url = `${window.location.origin}/prema-lokaciji${areaHash()}`;
    history.replaceState(history.state, '', url);
    const btn = document.getElementById('btnCopyArea');
    try {
        await navigator.clipboard.writeText(url);
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Poveznica kopirana';
    } catch (_) {
        btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Poveznica je u adresnoj traci';
    }
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-link-45deg me-1"></i>Kopiraj poveznicu'; }, 2500);
}

// The add button follows the dropdowns: something to add once a county is picked.
const syncAreaButton = () => { document.getElementById('btnAddArea').disabled = !selCounty.value; };
selCounty.addEventListener('change', syncAreaButton);
selMunicipality.addEventListener('change', syncAreaButton);
document.getElementById('btnAddArea').addEventListener('click', () => addCurrentPlaceToArea());
document.getElementById('btnShowArea').addEventListener('click', () => loadAreaResults());
document.getElementById('btnCopyArea').addEventListener('click', () => copyAreaLink());
document.getElementById('btnClearArea').addEventListener('click', () => { _area.items = []; renderAreaChips(); });
document.getElementById('areaChips').addEventListener('click', e => {
    const b = e.target.closest('[data-area-remove]');
    if (!b) return;
    _area.items.splice(+b.dataset.areaRemove, 1);
    renderAreaChips();
});

// A shared area link opens it and shows the sum.
window.addEventListener('load', () => {
    const h = window.location.hash || '';
    if (!h.startsWith('#podrucje=')) return;
    for (const part of h.slice('#podrucje='.length).split(';')) {
        const [type, list] = part.split(':');
        if (!['m', 'c'].includes(type) || !list) continue;
        list.split(',').map(Number).filter(Boolean).forEach(id => _area.items.push({ type, id, name: '' }));
    }
    if (_area.items.length) loadAreaResults();
});
