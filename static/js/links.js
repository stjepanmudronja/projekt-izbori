// Links between pages: badges, names and places that open another module.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// Delegated handler: clicking the election-type/year badge group on any
// politician/party result card jumps to that election's results tab with the
// matching year preselected. Reuses izlNavigateTo().
document.addEventListener('click', (e) => {
    const link = e.target.closest('.result-badges-link');
    if (!link) return;
    const cat = link.dataset.cat;
    const year = parseInt(link.dataset.year, 10);
    if (cat && year) izlNavigateTo(cat, year, readLokDeepLink(link));
});

// Delegated handler: clicking a candidate name in a bar chart opens that
// politician's page (same view you'd see by searching for them).
document.addEventListener('click', (e) => {
    const link = e.target.closest('.bar-label-link');
    if (!link) return;
    const name = link.dataset.personName;
    if (name) navigateToPerson(name, link.dataset.personId);
});

// A politician link. With the person's id it opens that row directly, which
// matters for namesakes (see split_persons): a name search would land on
// whichever "Ante Jelavić" sorts first.
function personLinkHtml(name, personId) {
    const idAttr = personId ? ` data-person-id="${personId}"` : '';
    return `<span class="bar-label-link" data-person-name="${escapeHtml(name)}"${idAttr} title="Otvori stranicu političara: ${escapeHtml(name)}">${escapeHtml(name)}</span>`;
}

async function navigateToPerson(name, personId) {
    // No history entry for the bare module: loadDetail pushes the person's own link.
    if (!activateModule('person', { pushState: false, focusInput: false })) return;
    if (personId) {
        _compareItems.person = [];
        renderCompareTags('person');
        await loadDetail('person', parseInt(personId, 10));
        return;
    }
    try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(name)}&type=person`);
        const list = await res.json();
        if (!Array.isArray(list) || list.length === 0) return;
        // Prefer exact match on diacritics-stripped uppercase form.
        const norm = (s) => (s || '').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/Đ/g, 'D');
        const target = norm(name);
        const pick = list.find(p => norm(p.name) === target) || list[0];
        // Reset the person compare list so we land on a clean single-person view.
        _compareItems.person = [];
        renderCompareTags('person');
        await loadDetail('person', pick.id);
    } catch (err) {
        console.warn('navigateToPerson failed', err);
    }
}
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const link = e.target.closest && e.target.closest('.result-badges-link');
    if (!link) return;
    e.preventDefault();
    const cat = link.dataset.cat;
    const year = parseInt(link.dataset.year, 10);
    if (cat && year) izlNavigateTo(cat, year, readLokDeepLink(link));
});

// Extracts lokalni deep-link options (kind/county/muni) from a badge link's
// data-* attrs. Returns null for non-lokalni links so izlNavigateTo skips the
// preselect path.
function readLokDeepLink(link) {
    if (link.dataset.cat !== 'lokalni') return null;
    return {
        kind: link.dataset.kind || null,
        countyId: link.dataset.countyId ? parseInt(link.dataset.countyId, 10) : null,
        municipalityId: link.dataset.muniId ? parseInt(link.dataset.muniId, 10) : null,
    };
}

function izlNavigateTo(category, year, opts) {
    if (category === 'sabor') {
        const link = document.querySelector('.sidebar-nav a[data-module="sabor-analysis"]');
        if (link) link.click();
        // Wait for module init (fetches year list), then load that year.
        // Uses setSaborYears rather than btn.click() because the picker is
        // additive — a click would append to whatever was already selected.
        const tryLoad = (attempts = 0) => {
            const btn = document.querySelector(`.sa-year-btn[data-year="${year}"]`);
            if (btn) {
                setSaborYears([year]);
            } else if (attempts < 20) {
                setTimeout(() => tryLoad(attempts + 1), 100);
            }
        };
        tryLoad();
        return;
    }

    // predsjednicki, eu, lokalni → dedicated module with the right year preselected
    const link = document.querySelector(`.sidebar-nav a[data-module="results-${category}"]`);
    if (link) link.click();
    const tryLoad = (attempts = 0) => {
        const yearBtn = document.querySelector(
            `#module-results-${category} .results-year-btn[data-year="${year}"]`
        );
        if (yearBtn && category === 'lokalni') {
            setLokYears([+year]);   // a click would add the year to a comparison
        } else if (yearBtn) {
            yearBtn.click();
        } else if (attempts < 20) {
            setTimeout(() => tryLoad(attempts + 1), 100);
        }
    };
    tryLoad();

    // Lokalni: preselect županija / grad-općina / vrsta izbora dropdowns so
    // the user lands on the matching race instead of the empty default view.
    if (category === 'lokalni' && opts && (opts.countyId || opts.kind)) {
        lokalniPreselect(opts);
    }
}

// Drive the lokalni module's cascading dropdowns to a target scope. Each step
// is async (county change fetches munis; muni change fetches stations), so
// we poll for the next dropdown to be populated before setting its value.
function lokalniPreselect(opts) {
    const waitForOption = (sel, value, cb, attempts = 0) => {
        if (!value) { cb(); return; }
        if (!sel) { cb(); return; }
        const found = Array.from(sel.options).find(o => String(o.value) === String(value));
        if (found) cb();
        else if (attempts < 40) setTimeout(() => waitForOption(sel, value, cb, attempts + 1), 100);
        else cb();
    };
    const waitForEnabled = (sel, cb, attempts = 0) => {
        if (!sel || !sel.disabled) { cb(); return; }
        if (attempts < 40) setTimeout(() => waitForEnabled(sel, cb, attempts + 1), 100);
        else cb();
    };
    const start = (attempts = 0) => {
        const selC = document.getElementById('lokSelCounty');
        // Counties are loaded inside initLokalniModule (async). Wait until the
        // target county option exists before driving the change.
        if (!selC || selC.options.length <= 1) {
            if (attempts < 40) setTimeout(() => start(attempts + 1), 100);
            return;
        }
        waitForOption(selC, opts.countyId, () => {
            if (opts.countyId) {
                selC.value = String(opts.countyId);
                selC.dispatchEvent(new Event('change'));
            }
            const selM = document.getElementById('lokSelMuni');
            waitForOption(selM, opts.municipalityId, () => {
                if (opts.municipalityId) {
                    selM.value = String(opts.municipalityId);
                    selM.dispatchEvent(new Event('change'));
                }
                const selK = document.getElementById('lokSelKind');
                waitForEnabled(selK, () => {
                    if (opts.kind) {
                        selK.value = opts.kind;
                        selK.dispatchEvent(new Event('change'));
                    }
                });
            });
        });
    };
    start();
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[c]);
}
