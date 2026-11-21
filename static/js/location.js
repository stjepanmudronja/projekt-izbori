// Prema lokaciji: county/municipality/station dropdowns and the county map.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// --- Cascading dropdown logic for Prema lokaciji ---
const selCounty = document.getElementById('selCounty');
const selMunicipality = document.getElementById('selMunicipality');
const selStation = document.getElementById('selStation');
const selStreet = document.getElementById('selStreet');
const btnShowResults = document.getElementById('btnShowResults');

// Load counties on page load
(async function loadCounties() {
    const res = await fetch('/api/counties');
    const data = await res.json();
    data.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        selCounty.appendChild(opt);
    });
})();

// --- Croatia SVG map interactivity ---
const mapWrap = document.getElementById('croatiaMapWrap');
const mapCountyLabel = document.getElementById('mapCountyLabel');
let mapPaths = [];

// Load SVG from file and inject inline
(async function loadCroatiaMap() {
    const res = await fetch('/static/croatia_map.svg');
    const svgText = await res.text();
    mapWrap.innerHTML = svgText;
    // Remove any embedded <style> from the SVG so our CSS takes over
    const embeddedStyle = mapWrap.querySelector('svg style');
    if (embeddedStyle) embeddedStyle.remove();
    // Remove title
    const svgTitle = mapWrap.querySelector('svg title');
    if (svgTitle) svgTitle.remove();

    mapPaths = mapWrap.querySelectorAll('path[data-county]');
    initMapInteraction();
})();

function highlightMapCounty(countyName) {
    mapPaths.forEach(p => p.classList.remove('selected'));
    if (countyName) {
        const target = mapWrap.querySelector(`path[data-county="${countyName}"]`);
        if (target) target.classList.add('selected');
        mapCountyLabel.textContent = countyName;
    } else {
        mapCountyLabel.textContent = '';
    }
}

function initMapInteraction() {
    mapPaths.forEach(path => {
        path.addEventListener('click', () => {
            const countyName = path.getAttribute('data-county');
            const options = selCounty.options;
            for (let i = 0; i < options.length; i++) {
                if (options[i].textContent.toUpperCase() === countyName.toUpperCase()) {
                    selCounty.value = options[i].value;
                    selCounty.dispatchEvent(new Event('change'));
                    highlightMapCounty(countyName);
                    break;
                }
            }
        });

        path.addEventListener('mouseenter', () => {
            if (!path.classList.contains('selected')) {
                mapCountyLabel.textContent = path.getAttribute('data-county');
            }
        });
        path.addEventListener('mouseleave', () => {
            const selected = mapWrap.querySelector('path.selected');
            mapCountyLabel.textContent = selected ? selected.getAttribute('data-county') : '';
        });
    });
}

// Dropdown change → highlight map
selCounty.addEventListener('change', () => {
    const selectedText = selCounty.options[selCounty.selectedIndex]?.textContent || '';
    if (!selectedText || selCounty.selectedIndex === 0) {
        highlightMapCounty(null);
        return;
    }
    // Direct match by uppercase name
    const match = [...mapPaths].find(p =>
        p.getAttribute('data-county').toUpperCase() === selectedText.toUpperCase()
    );
    highlightMapCounty(match ? match.getAttribute('data-county') : null);
});

selCounty.addEventListener('change', async () => {
    // Reset dependents
    selMunicipality.innerHTML = '<option value="">Odabir grada/općine...</option>';
    selStation.innerHTML = '<option value="">Odabir biračkog mjesta...</option>';
    selStreet.innerHTML = '<option value="">Odabir ulice...</option>';
    selMunicipality.disabled = true;
    selStation.disabled = true;
    selStreet.disabled = true;
    updateShowButton();

    const countyId = selCounty.value;
    if (!countyId) return;

    btnShowResults.disabled = false; // Can show county-level results

    const res = await fetch(`/api/municipalities/${countyId}`);
    const data = await res.json();
    data.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.id;
        opt.textContent = m.name;
        selMunicipality.appendChild(opt);
    });
    selMunicipality.disabled = false;
});

selMunicipality.addEventListener('change', async () => {
    selStation.innerHTML = '<option value="">Odabir biračkog mjesta...</option>';
    selStreet.innerHTML = '<option value="">Odabir ulice...</option>';
    selStation.disabled = true;
    selStreet.disabled = true;
    updateShowButton();

    const muniId = selMunicipality.value;
    if (!muniId) return;

    // Load stations and streets in parallel
    const [stationsRes, streetsRes] = await Promise.all([
        fetch(`/api/polling-stations/${muniId}`),
        fetch(`/api/streets/${muniId}`),
    ]);
    const stations = await stationsRes.json();
    const streets = await streetsRes.json();

    stations.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        opt.textContent = s.name;
        selStation.appendChild(opt);
    });
    selStation.disabled = false;

    streets.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.name;
        opt.textContent = s.name;
        selStreet.appendChild(opt);
    });
    selStreet.disabled = false;
});

selStation.addEventListener('change', () => {
    updateShowButton();
});
selStreet.addEventListener('change', async () => {
    if (selStreet.value && selMunicipality.value) {
        // Fetch stations matching this street and auto-select in biračko mjesto dropdown
        const res = await fetch(`/api/stations-by-street/${selMunicipality.value}?street=${encodeURIComponent(selStreet.value)}`);
        const stations = await res.json();
        if (stations.length === 1) {
            // Exact match — auto-select in station dropdown
            const matchOpt = [...selStation.options].find(o => o.value === String(stations[0].id));
            if (matchOpt) selStation.value = matchOpt.value;
        } else if (stations.length > 1) {
            // Multiple stations — reset station dropdown and populate with only matching ones
            selStation.innerHTML = '<option value="">Odabir biračkog mjesta...</option>';
            stations.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = s.name;
                selStation.appendChild(opt);
            });
            if (stations.length === 1) selStation.value = stations[0].id;
        }
    }
    updateShowButton();
});

function updateShowButton() {
    btnShowResults.disabled = !selCounty.value;
}

// Looked up on click: loadLocationResults is declared in results.js, which loads later.
btnShowResults.addEventListener('click', () => loadLocationResults());
