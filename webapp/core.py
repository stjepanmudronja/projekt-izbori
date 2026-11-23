"""The Flask app and its database handle, shared by every module.

`app.py` at the project root imports the route modules and runs the server;
the app's root is the project folder, so `templates/` and `static/` are found
where they always were.
"""
import functools
import os
import threading
import time
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


# Data caches: cleared by themselves when the database changes
#
# Everything the site computes from the data may be kept until the data
# changes, which happens on an import (or a fix-up command, or the admin).
# The import runs in another process, so it cannot empty this one's caches;
# instead every few seconds a request asks PostgreSQL how many rows have ever
# been written (pg_stat_user_tables), and when that number has moved since
# the last look, every registered cache is emptied and the warm-up runs again.
# Postgres counts the writes of every client, so nothing has to remember to
# signal; a command's counts arrive when its transaction ends.

_DATA_CACHES = []        # functions that empty one cache each
_AFTER_CLEAR = []        # run once all are empty (the warm-up)
DATA_CHECK_SECONDS = 3
_data_check = {'version': None, 'at': 0.0, 'cleared': 0}
_data_check_lock = threading.Lock()


def data_cache(cache):
    """Register a module-level dict (`_X_CACHE = data_cache({})`) to be
    emptied when the data changes; returns it."""
    _DATA_CACHES.append(cache.clear)
    return cache


def after_data_change(fn):
    """Run `fn()` after the caches were emptied (a decorator)."""
    _AFTER_CLEAR.append(fn)
    return fn


def clear_data_caches():
    """Empty every registered cache, then run the after-clear hooks."""
    for clear in _DATA_CACHES:
        clear()
    _data_check['cleared'] += 1
    for fn in _AFTER_CLEAR:
        fn()


def data_generation():
    """How many times the caches were cleared: a computation that started
    before a clear and finishes after it holds old data and must not be kept."""
    return _data_check['cleared']


def data_version():
    """Rows ever inserted, updated or deleted in this database. Any import
    moves it; it may also go back (a stats reset), which counts as a change."""
    with db.engine.connect() as conn:
        return conn.exec_driver_sql(
            'SELECT coalesce(sum(n_tup_ins + n_tup_upd + n_tup_del), 0) FROM pg_stat_user_tables').scalar()


def check_data_changed(force=False):
    """Clear the caches when the data version moved; at most once every
    DATA_CHECK_SECONDS unless forced. Returns True when it cleared."""
    now = time.monotonic()
    if not force and now - _data_check['at'] < DATA_CHECK_SECONDS:
        return False
    if not _data_check_lock.acquire(blocking=False):
        return False                          # another request is checking
    try:
        _data_check['at'] = now
        version = data_version()
        previous, _data_check['version'] = _data_check['version'], version
        if previous is None or version == previous:
            return False                      # the first look only sets the mark
        app.logger.info('data changed (%s -> %s writes): caches cleared', previous, version)
        clear_data_caches()
        return True
    finally:
        _data_check_lock.release()


@app.before_request
def _clear_caches_on_new_data():
    if request.path.startswith('/static/'):
        return
    try:
        check_data_changed()
    except Exception as exc:                  # never fail a page over the check
        app.logger.warning('data change check failed: %s', exc)


def static_cache(view=None, *, maxsize=None):
    """Remember a view's successful JSON response until the data changes
    (see data_cache), keyed by its path arguments and its query string. For
    endpoints whose result depends only on those and the database.

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
        _DATA_CACHES.append(cache.clear)
        return wrapper
    return decorate(view) if view else decorate
