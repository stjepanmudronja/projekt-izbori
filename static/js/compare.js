// Usporedi s: polling stations side by side.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// ---- Compare feature ----
const compareState = {
    stations: [],  // [{id, name, data}]
    maxCompare: 3,
};

const compareSearchInput = document.getElementById('compareSearchInput');
const compareDropdown = document.getElementById('compareDropdown');
let compareDebounce;

compareSearchInput.addEventListener('input', () => {
    clearTimeout(compareDebounce);
    const q = compareSearchInput.value.trim();
    if (q.length < 2) {
        compareDropdown.classList.remove('show');
        return;
    }
    compareDebounce = setTimeout(() => fetchCompareResults(q), 250);
});

async function fetchCompareResults(q) {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&type=station`);
    const data = await res.json();

    compareDropdown.innerHTML = '';
    if (data.length === 0) {
        compareDropdown.innerHTML = '<div class="dropdown-item-custom text-muted">Nema rezultata</div>';
        compareDropdown.classList.add('show');
        return;
    }

    data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'dropdown-item-custom';
        div.innerHTML = `${item.name} <small class="text-muted">- ${item.municipality}</small>`;
        div.addEventListener('click', () => {
            compareSearchInput.value = '';
            compareDropdown.classList.remove('show');
            addCompareStation(item.id, item.name, item.municipality);
        });
        compareDropdown.appendChild(div);
    });
    compareDropdown.classList.add('show');
}

async function addCompareStation(id, name, municipality) {
    // Check duplicates and max
    if (compareState.stations.find(s => s.id === id)) return;
    if (compareState.stations.length >= compareState.maxCompare) return;

    // Fetch data
    const res = await fetch(`/api/station/${id}`);
    const data = await res.json();

    compareState.stations.push({ id, name, municipality, data });
    renderComparisons();
    updateCompareUI();
}

function removeCompareStation(id) {
    compareState.stations = compareState.stations.filter(s => s.id !== id);
    renderComparisons();
    updateCompareUI();
}

function clearAllComparisons() {
    compareState.stations = [];
    renderComparisons();
    updateCompareUI();
}

function updateCompareUI() {
    const searchInput = document.getElementById('compareSearchInput');
    const clearBtn = document.getElementById('clearCompareBtn');

    if (compareState.stations.length >= compareState.maxCompare) {
        searchInput.disabled = true;
        searchInput.placeholder = 'Maksimalan broj biračkih mjesta (3)';
    } else {
        searchInput.disabled = false;
        searchInput.placeholder = 'Traži biračko mjesto...';
    }

    clearBtn.style.display = compareState.stations.length > 0 ? 'inline-block' : 'none';
}

function renderComparisons() {
    const container = document.getElementById('compareResults');

    if (compareState.stations.length === 0) {
        container.innerHTML = '';
        return;
    }

    // Build HTML first, then wire up bar charts
    container.innerHTML = compareState.stations.map(station => {
        const d = station.data;
        const elections = filterResults(d.elections || [], 'compare');

        const electionCards = elections.map((el, idx) => {
            const turnoutPct = el.registered_voters > 0
                ? (el.ballots_cast / el.registered_voters) * 100 : 0;
            const chartId = `cmp_${station.id}_${idx}`;

            return `
            <div class="compare-election-title">
                <span class="badge ${electionBadgeColor(el.election_type)} badge-election me-1" style="font-size:0.65rem;">${el.election_type}</span>
                <span class="badge bg-dark badge-election" style="font-size:0.65rem;">${el.date ? new Date(el.date).toLocaleDateString('hr-HR', { day: 'numeric', month: 'short', year: 'numeric' }) : el.year}</span>
                ${el.round > 1 ? `<span class="badge bg-warning text-dark badge-election" style="font-size:0.65rem;">${el.round}. krug</span>` : ''}
                <span class="text-muted ms-2" style="font-size:0.7rem;">Izlaznost: <strong>${formatPct(turnoutPct)}</strong></span>
            </div>
            <div class="bar-chart-area" id="barChart_${chartId}" data-election-idx="${chartId}"></div>
            <div class="d-flex justify-content-between align-items-center mt-1 mb-2">
                <div class="bar-drag-hint"><i class="bi bi-arrows-move me-1"></i>Povuci stupac za spajanje</div>
                <button class="btn btn-outline-secondary bar-reset-btn" onclick="resetBarChart('${chartId}')" style="display:none;" id="resetBtn_${chartId}">
                    <i class="bi bi-arrow-counterclockwise me-1"></i>Poništi
                </button>
            </div>`;
        }).join('');

        return `
        <div class="compare-card">
            <div class="compare-card-header">
                <h6><i class="bi bi-geo-alt me-1"></i>${station.name}</h6>
                <button class="btn btn-sm btn-outline-light" style="padding:0.1rem 0.4rem; font-size:0.7rem;" onclick="removeCompareStation(${station.id})">
                    <i class="bi bi-x"></i>
                </button>
            </div>
            <div class="compare-card-body">
                ${d.municipality ? `<small class="text-muted">${d.municipality}</small>` : ''}
                ${electionCards || '<p class="text-muted" style="font-size:0.8rem;">Nema podataka</p>'}
            </div>
        </div>`;
    }).join('');

    // Now wire up draggable bar charts for each election in each compare card
    compareState.stations.forEach(station => {
        const elections = filterResults(station.data.elections || [], 'compare');
        elections.forEach((el, idx) => {
            const chartId = `cmp_${station.id}_${idx}`;
            const hasCandidates = el.top_candidates && el.top_candidates.length > 0;
            const items = hasCandidates ? el.top_candidates : el.top_lists;
            if (items.length === 0) return;

            const originalItems = items.map((it, i) => ({
                name: it.name,
                votes: it.votes,
                color: barColors[i % barColors.length],
                origNames: [it.name],
            }));

            window._electionBarData[chartId] = {
                original: JSON.parse(JSON.stringify(originalItems)),
                current: originalItems,
                validBallots: el.valid_ballots,
            };

            buildBarChart(chartId);
        });
    });
}

// Close dropdowns on outside click
document.addEventListener('click', e => {
    if (!e.target.closest('.position-relative')) {
        document.querySelectorAll('.dropdown-results').forEach(d => d.classList.remove('show'));
    }
});
