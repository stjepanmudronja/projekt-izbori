// Opens the module the URL names (boot.js calls it once everything is loaded).
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.

// Restore the active tab from the URL on first paint and on back/forward.
function activateModuleFromUrl() {
    const parts = (window.location.pathname || '/').split('/').filter(Boolean);
    // /politicar alone (back from a politician's link) shows none.
    if (parts[0] === 'politicar') {
        activateModule('person', { pushState: false, focusInput: false });
        restorePersonsFromUrl(parts.slice(1));
        return;
    }
    if (parts[0] === 'stranke') {
        activateModule('parties', { pushState: false, focusInput: false });
        const n = parseInt(parts[1], 10);
        if (n > 0 && (!_partyShown || _partyShown.registry_number !== n)) openParty(n, { push: false });
        if (!(n > 0)) closeParty({ push: false });
        return;
    }
    if (parts[0] === 'mjesto') {
        activateModule('place', { pushState: false, focusInput: false });
        const id = parseInt(parts[1], 10);
        if (id > 0 && (!_placeShown || _placeShown.id !== id)) openPlace(id, { push: false });
        if (!(id > 0)) clearPlace();
        return;
    }
    const slug = (window.location.pathname || '/').replace(/^\//, '').replace(/\/$/, '');
    // The upper house lost its own sidebar tab once the Sabor year picker
    // offered 1997; the URL still resolves, to that year of that module.
    if (slug === 'zupanijski-dom') {
        izlNavigateTo('sabor', ZUP_DOM_YEARS[0]);
        return;
    }
    const mod = SLUG_TO_MODULE[slug] || 'home';
    activateModule(mod, { pushState: false, focusInput: false });
}
