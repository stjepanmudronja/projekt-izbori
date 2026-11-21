"""The Flask app and its database handle, shared by every module.

`app.py` at the project root imports the route modules and runs the server;
the app's root is the project folder, so `templates/` and `static/` are found
where they always were.
"""
import functools
import os
from collections import OrderedDict
from pathlib import Path

from flask import Flask, request, url_for
from flask_sqlalchemy import SQLAlchemy

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = Flask(__name__, root_path=str(PROJECT_ROOT))
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///projekt_izbori'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Routes

@app.after_request
def _no_store(resp):
    """Keep the browser from caching the app or its data.

    Flask sets no Cache-Control on a rendered template or on jsonify, which
    leaves both free to be cached. Two things then go wrong, and both look
    exactly like a missing feature rather than a caching problem: the 350KB
    SPA shell — all the markup and JS, rewritten with every change — keeps
    running against a newer API, and a year list fetched once keeps a newly
    imported year out of the picker. Nothing here is static: every response
    reflects the current import state. Only /static/ assets stay cacheable.
    """
    if not request.path.startswith('/static/'):
        resp.headers.setdefault('Cache-Control', 'no-store, must-revalidate')
    return resp


@app.context_processor
def _asset_urls():
    """`asset('js/home.js')` in a template: the static URL with the file's
    modification time, so a browser that cached an older copy fetches the new
    one after an edit (static files stay cacheable, see _no_store)."""
    def asset(filename):
        try:
            version = int(os.path.getmtime(PROJECT_ROOT / 'static' / filename))
        except OSError:
            version = 0
        return url_for('static', filename=filename, v=version)
    return {'asset': asset}


def static_cache(view=None, *, maxsize=None):
    """Remember a view's successful JSON response until the server restarts,
    keyed by its path arguments and its query string. For endpoints whose
    result depends only on those and the database, which changes only on an
    import (restart the server after one, as for every other cache here).

    `@static_cache` or `@static_cache(maxsize=N)`: with a size, the oldest
    entries go first once N are held — for views with a key per place, of
    which there are thousands."""
    def decorate(view):
        cache = OrderedDict()

        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())), tuple(sorted(request.args.items(multi=True))))
            if key in cache:
                cache.move_to_end(key)
            else:
                res = app.make_response(view(*args, **kwargs))
                if res.status_code != 200:
                    return res
                cache[key] = (res.get_data(), res.mimetype)
                if maxsize and len(cache) > maxsize:
                    cache.popitem(last=False)
            data, mimetype = cache[key]
            return app.response_class(data, mimetype=mimetype)
        wrapper.cache = cache
        return wrapper
    return decorate(view) if view else decorate
