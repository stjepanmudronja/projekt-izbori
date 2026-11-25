"""Ponovni izbor (Analitika): do načelnici, gradonačelnici and župani win again?

Executive races are direct since 2009, so there are five elections (2009,
2013, 2017, 2021, 2025) and four chances to be re-elected. A race is a place:
a municipality (načelnik or gradonačelnik — a općina that became a grad is
the same race) or a county (župan); its district number is the place's
primary key, as on Početna. The winner is the first in the deciding (last)
round. The incumbent at an election is the previous election's winner there;
they either ran again for that place (and won or lost) or did not run.
From the results only: resignations, deaths and early elections between two
regular ones are not known, so "incumbent" means the last one elected.

By county: every race belongs to a county (a municipality's, or the
county's own župan race), so the same counts are given per county code
(01-21, as the map's HR-NN paths) for each election. Close calls: an
incumbent re-elected by under CLOSE_MARGIN points over the runner-up in
the deciding round.
"""
from collections import defaultdict

from flask import jsonify

from webapp.core import app, db, static_cache
from webapp.models import County, Municipality

EXEC_SLUGS = ('local_mayor', 'local_city_mayor', 'local_county_prefect')
OFFICE_KIND = {'local_mayor': 'opcina', 'local_city_mayor': 'grad', 'local_county_prefect': 'zupanija'}
OFFICE_TITLE = {'local_mayor': 'načelnik', 'local_city_mayor': 'gradonačelnik', 'local_county_prefect': 'župan'}
CLOSE_MARGIN = 2.0      # percentage points between the re-elected incumbent and the runner-up


def exec_races():
    """{(place_key, year): race} for every executive race, where place_key is
    ('m', municipality id) or ('c', county id) and race has the slug, the
    deciding round, its candidates (votes, person, name) best first, every
    person who stood in any round, and round 1's candidates."""
    rows = db.session.execute(db.text("""
        select e.year, et.slug, ed.number, er.round_number, c.person_id,
               p.first_name || ' ' || p.last_name, sum(lr.votes)
        from elections_listresult lr
        join elections_electorallist el on el.id = lr.electoral_list_id
        join elections_electoraldistrict ed on ed.id = el.district_id
        join elections_candidacy c on c.electoral_list_id = el.id
        join elections_person p on p.id = c.person_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug in :slugs
        group by 1, 2, 3, 4, 5, 6"""), {'slugs': EXEC_SLUGS}).fetchall()
    rounds = defaultdict(list)
    for year, slug, num, rnd, pid, name, votes in rows:
        place = ('c' if slug == 'local_county_prefect' else 'm', num)
        rounds[(place, year, slug, rnd)].append((int(votes or 0), pid, name))
    races = {}
    for (place, year, slug, rnd), cands in rounds.items():
        r = races.setdefault((place, year), {'slug': slug, 'round': 0, 'cands': [], 'stood': set(), 'first': []})
        r['stood'].update(c[1] for c in cands)
        if rnd == 1:
            r['first'] = sorted(cands, key=lambda c: -c[0])
        if rnd > r['round']:
            r['round'], r['cands'] = rnd, sorted(cands, key=lambda c: -c[0])
    return {k: r for k, r in races.items() if r['cands'] and r['cands'][0][0] > 0}


def _share(cands, i=0, digits=1):
    total = sum(c[0] for c in cands)
    return round(cands[i][0] / total * 100, digits) if total and len(cands) > i else None


@app.route('/api/analytics/incumbency')
@static_cache
def incumbency():
    races = exec_races()
    years = sorted({y for (_, y) in races})
    munis = {m.id: m for m in Municipality.query}
    county_rows = list(County.query)
    counties = {c.id: c.name for c in county_rows}
    county_code = {c.id: c.code for c in county_rows}

    def county_of(key):
        kind, num = key
        cid = num if kind == 'c' else (munis[num].county_id if num in munis else None)
        code = county_code.get(cid)
        return code if code and '01' <= code <= '21' else None

    def place(key):
        kind, num = key
        if kind == 'c':
            return {'name': counties.get(num), 'place_id': None}
        m = munis.get(num)
        return {'name': m.name if m else None, 'place_id': m.id if m else None}

    def person(c, cands, digits=1):
        return {'name': c[2], 'person_id': c[1], 'share': _share(cands, cands.index(c), digits)}

    # Election by election: what happened to the incumbent.
    per_year, defeated, close = [], defaultdict(list), defaultdict(list)
    by_county = {}
    new_counts = lambda: {'races': 0, 'won': 0, 'won_first_round': 0, 'lost': 0, 'did_not_run': 0}
    for prev, year in zip(years, years[1:]):
        counts = defaultdict(new_counts)
        county_counts = defaultdict(lambda: defaultdict(new_counts))
        for (key, y), r in races.items():
            if y != year or (key, prev) not in races:
                continue
            kind = OFFICE_KIND[r['slug']]
            inc = races[(key, prev)]['cands'][0]
            code = county_of(key)
            buckets = [counts[kind], counts['sve']]
            if code:
                buckets += [county_counts[code][kind], county_counts[code]['sve']]
            for c in buckets:
                c['races'] += 1
                if r['cands'][0][1] == inc[1]:
                    c['won'] += 1
                    if r['round'] == 1:
                        c['won_first_round'] += 1
                elif inc[1] in r['stood']:
                    c['lost'] += 1
                else:
                    c['did_not_run'] += 1
            if r['cands'][0][1] != inc[1] and inc[1] in r['stood']:
                # Where they stood in the deciding round, or went out in round 1.
                mine = next((c for c in r['cands'] if c[1] == inc[1]), None)
                pool = r['cands'] if mine else r['first']
                mine = mine or next(c for c in r['first'] if c[1] == inc[1])
                defeated[year].append({
                    **place(key), 'office': OFFICE_TITLE[r['slug']], 'kind': kind, 'county': code,
                    'incumbent': person(mine, pool), 'winner': person(r['cands'][0], r['cands']),
                    'round': r['round'] if mine in r['cands'] else 1,
                    'out_in_first_round': mine not in r['cands'],
                    'won_before': _share(races[(key, prev)]['cands']),
                })
            if r['cands'][0][1] == inc[1] and len(r['cands']) > 1:
                total = sum(c[0] for c in r['cands'])
                margin = (r['cands'][0][0] - r['cands'][1][0]) / total * 100 if total else None
                if margin is not None and margin < CLOSE_MARGIN:
                    close[year].append({
                        **place(key), 'office': OFFICE_TITLE[r['slug']], 'kind': kind, 'county': code,
                        # Two decimals: a race decided by 18 votes reads 50.0 : 50.0 at one.
                        'incumbent': person(r['cands'][0], r['cands'], 2), 'runner_up': person(r['cands'][1], r['cands'], 2),
                        'margin': round(margin, 2), 'votes_ahead': r['cands'][0][0] - r['cands'][1][0], 'round': r['round'],
                    })
        per_year.append({'year': year, 'previous': prev, 'by_kind': counts})
        by_county[year] = {code: dict(k) for code, k in county_counts.items()}

    # Unbroken runs of today's holders: how many elections in a row they won there.
    latest = years[-1]
    terms = defaultdict(lambda: defaultdict(int))
    long_serving = []
    for (key, y), r in races.items():
        if y != latest:
            continue
        pid = r['cands'][0][1]
        n = 1
        while (key, latest - 4 * n) in races and races[(key, latest - 4 * n)]['cands'][0][1] == pid:
            n += 1
        kind = OFFICE_KIND[r['slug']]
        terms[kind][n] += 1
        terms['sve'][n] += 1
        if n == len(years):
            long_serving.append({**place(key), 'office': OFFICE_TITLE[r['slug']], 'kind': kind, 'county': county_of(key),
                                 'person': person(r['cands'][0], r['cands']), 'round': r['round'],
                                 'unopposed': len(r['cands']) == 1})

    for y in defeated:
        defeated[y].sort(key=lambda d: (d['kind'] != 'zupanija', d['kind'] != 'grad', d['name'] or ''))
    long_serving.sort(key=lambda d: (d['kind'] != 'zupanija', d['kind'] != 'grad', d['name'] or ''))
    for y in close:
        close[y].sort(key=lambda d: d['margin'])
    return jsonify({
        'years': years,
        'per_year': per_year,
        'terms': {'year': latest, 'by_kind': {k: dict(v) for k, v in terms.items()}},
        'defeated': defeated,
        'long_serving': long_serving,
        'counties': {county_code[i]: name for i, name in counties.items() if '01' <= (county_code[i] or '') <= '21'},
        'by_county': by_county,
        'close': close,
        'close_margin': CLOSE_MARGIN,
    })
