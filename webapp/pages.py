"""The single-page app shell and its pretty URLs.
"""

from flask import render_template, request, send_from_directory
from webapp.core import app
from webapp.meta import PAGE_META, page_meta

PAGE_TITLES = {slug: t for slug, (t, _) in PAGE_META.items()}


def _shell():
    return render_template('index.html', meta=page_meta(request.path), page_titles=PAGE_TITLES)


@app.route('/')
def index():
    return _shell()


# Pretty URLs per sidebar tab — the SPA reads window.location to switch tabs.
# Restricted to a known whitelist so we don't accidentally swallow /api/...
# or static asset paths.
SPA_ROUTES = {
    'politicar', 'prema-lokaciji', 'usporedba', 'stranke',
    'predsjednicki-izbori', 'eu-parlamentarni-izbori', 'lokalni-izbori',
    'rezultati-koalicije-sabor', 'zupanijski-dom', 'izlaznost', 'karta', 'mjesto', 'snaga-stranaka', 'zene-u-politici', 'ponovni-izbor',
}


@app.route('/<slug>')
def spa_route(slug):
    if slug in SPA_ROUTES:
        return _shell()
    return ('Not Found', 404)


# Shareable links: /politicar/1952-jakov-vetma (more ids after further
# slashes compare them) and /mjesto/439-klis. Only the leading number of each
# segment counts; the name is there for people reading the link.
@app.route('/politicar/<path:rest>')
@app.route('/mjesto/<path:rest>')
@app.route('/stranke/<path:rest>')
def spa_deep_link(rest):
    return _shell()


# Browsers and crawlers ask for /favicon.ico whatever the page links; the
# 32-px PNG answers it (every browser reads a PNG there).
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon-32.png', mimetype='image/png', max_age=86400)
