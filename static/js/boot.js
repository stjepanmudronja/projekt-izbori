// Starts the app: opens the module the URL names. Must load last.
// Part of the site script, split from templates/index.html; the files load
// in the order index.html lists them and share one global scope.
//
// Everything above has run by now, so every module's top-level state (`lok`,
// `_resultsModuleInitialized`, `_saState`, …) exists. This used to sit in the
// middle of one big script, where calling it straight away hit the temporal
// dead zone of `const`s declared further down; that is also why it must not
// move into an earlier file. DOMContentLoaded fires once the parser is done,
// after these scripts; the timer is the original belt-and-braces second call.

window.addEventListener('popstate', activateModuleFromUrl);
document.addEventListener('DOMContentLoaded', activateModuleFromUrl);
setTimeout(activateModuleFromUrl, 0);
