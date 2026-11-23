"""The single-page app shell and its pretty URLs.
"""

from flask import render_template
from webapp.core import app


@app.route('/')
def index():
    return render_template('index.html')


# Pretty URLs per sidebar tab — the SPA reads window.location to switch tabs.
# Restricted to a known whitelist so we don't accidentally swallow /api/...
# or static asset paths.
SPA_ROUTES = {
    'politicar', 'prema-lokaciji', 'usporedba', 'stranke',
    'predsjednicki-izbori', 'eu-parlamentarni-izbori', 'lokalni-izbori',
    'rezultati-koalicije-sabor', 'zupanijski-dom', 'izlaznost', 'karta', 'mjesto', 'snaga-stranaka', 'zene-u-politici',
}


@app.route('/<slug>')
def spa_route(slug):
    if slug in SPA_ROUTES:
        return render_template('index.html')
    return ('Not Found', 404)


# Shareable links: /politicar/1952-jakov-vetma (more ids after further
# slashes compare them) and /mjesto/439-klis. Only the leading number of each
# segment counts; the name is there for people reading the link.
@app.route('/politicar/<path:rest>')
@app.route('/mjesto/<path:rest>')
@app.route('/stranke/<path:rest>')
def spa_deep_link(rest):
    return render_template('index.html')
