"""Karta općina (/api/map/*): every municipality coloured by one election.
"""

import re
from collections import defaultdict
from flask import jsonify, request
from webapp.core import app, db
from webapp.models import (
    Election,
    ElectionRound,
    ElectionType,
    ElectoralList,
    Municipality,
    PollingStation,
    TurnoutData,
)
from webapp.places import zagreb_sabor_units


# ---- Municipality map (Analitika → Karta općina) ----
# Each kind is a set of election types whose results are reported per
# municipality; the map colours every općina/grad by them.
MAP_KINDS = {
    'predsjednicki': {'label': 'Predsjednički izbori', 'slugs': ('presidential',)},
    'sabor': {'label': 'Parlamentarni izbori (Sabor)', 'slugs': ('sabor',)},
    'eu': {'label': 'Izbori za Europski parlament', 'slugs': ('eu_parliament',)},
    'vijece': {'label': 'Lokalni izbori - gradska i općinska vijeća',
               'slugs': ('local_municipal_council', 'local_city_council')},
}
MAP_TOP_PARTIES = 10
_MAP_CACHE = {}
_INDEPENDENT_PREFIXES = ('NEZAVISN', 'NEOVISN', 'KANDIDACIJSKA LISTA GRUPE', 'LISTA GRUPE BIRAČA', 'GRUPA BIRAČA')


_NOT_ABBREVIATIONS = {'STRANKA', 'LISTA', 'NL'}
_MAP_HEAD_ABBR = {}


def _split_party(first):
    """("HRVATSKA DEMOKRATSKA ZAJEDNICA", "HDZ") from a list's first party;
    the abbreviation only where the last " - " part is one (short, capitals)."""
    parts = [p.strip() for p in first.split(' - ')]
    last = parts[-1] if len(parts) > 1 else ''
    abbr = last if re.fullmatch(r"[A-ZČĆŠŽĐ0-9!]{2,8}", last) and last not in _NOT_ABBREVIATIONS else None
    return parts[0], abbr


def _map_party(list_name):
    """A list's party for the map: its first-named party (coalitions go under
    their leader, as everywhere on the site) by its abbreviation ("HDZ") —
    borrowed from another year's spelling where a list omits it (1993's
    "SOCIJALDEMOKRATSKA PARTIJA HRVATSKE") — else by its leading name
    ("MOŽEMO!", a presidential candidate). Lists headed "Nezavisna …" with no
    abbreviation are one group; Nezavisna platforma sjevera (NPS) is a party."""
    if not _MAP_HEAD_ABBR:
        seen = defaultdict(lambda: defaultdict(int))
        for (name,) in db.session.query(ElectoralList.name).distinct():
            head, abbr = _split_party((name or '').split('\n', 1)[0].split(',', 1)[0].strip())
            if abbr:
                seen[head.upper()][abbr] += 1
        _MAP_HEAD_ABBR.update({h: max(c, key=c.get) for h, c in seen.items()})
    first = (list_name or '').split('\n', 1)[0].split(',', 1)[0].strip()
    head, abbr = _split_party(first)
    abbr = abbr or _MAP_HEAD_ABBR.get(head.upper())
    if abbr:
        return abbr, abbr, first
    if head.upper().startswith(_INDEPENDENT_PREFIXES):
        return 'NEZAVISNI', 'Nezavisne liste', 'Nezavisne liste'
    return head.upper(), head, first


def _map_rounds(kind, year=None):
    slugs = MAP_KINDS[kind]['slugs']
    q = (db.session.query(ElectionRound.id, Election.year, ElectionRound.round_number)
         .join(Election, ElectionRound.election_id == Election.id)
         .join(ElectionType, Election.election_type_id == ElectionType.id)
         .filter(ElectionType.slug.in_(slugs)))
    if year:
        q = q.filter(Election.year == year)
    return q.all()


@app.route('/api/map/elections')
def map_elections():
    """The elections the map can show: per kind, the years (and rounds) with
    results in real municipalities — 1992/1995 Sabor and 1992/1997
    presidential exist only as national totals and are left out."""
    if 'elections' in _MAP_CACHE:
        return jsonify(_MAP_CACHE['elections'])
    with_munis = {r for (r,) in db.session.query(TurnoutData.election_round_id)
                  .join(PollingStation, PollingStation.id == TurnoutData.polling_station_id)
                  .join(Municipality, Municipality.id == PollingStation.municipality_id)
                  .filter(Municipality.type.in_(('grad', 'općina'))).distinct()}
    out = []
    for kind, spec in MAP_KINDS.items():
        years = defaultdict(set)
        for er_id, year, rnd in _map_rounds(kind):
            if er_id in with_munis:
                years[year].add(rnd)
        out.append({'kind': kind, 'label': spec['label'],
                    'years': [{'year': y, 'rounds': sorted(r)} for y, r in sorted(years.items())]})
    _MAP_CACHE['elections'] = out
    return jsonify(out)


@app.route('/api/map/data')
def map_data():
    """One election, per municipality: the leading party (or presidential
    candidate) with its share, the shares of the parties that lead
    nationally, and turnout. Shares are of the municipality's list votes;
    Sabor's minority districts (121+) are left out, being a separate ballot.
    Zagreb's Sabor districts count as Grad Zagreb."""
    kind = request.args.get('kind')
    year = request.args.get('year', type=int)
    rnd = request.args.get('round', 1, type=int)
    if kind not in MAP_KINDS or not year:
        return jsonify({'error': 'Nepoznati izbori.'}), 400
    payload = _map_payload(kind, year, rnd)
    if payload is None:
        return jsonify({'error': 'Nema tih izbora.'}), 404
    return jsonify(payload)


def _map_payload(kind, year, rnd=1):
    """The map's figures for one election (see map_data), cached; None when
    there is no such election."""
    cache_key = (kind, year, rnd)
    if cache_key in _MAP_CACHE:
        return _MAP_CACHE[cache_key]
    round_ids = [r for r, _, n in _map_rounds(kind, year) if n == rnd]
    if not round_ids:
        return None

    real = {m.id: m for m in Municipality.query.filter(Municipality.type.in_(('grad', 'općina')))}
    zagreb = Municipality.query.filter_by(name='GRAD ZAGREB').first()
    remap = {u: zagreb.id for u in zagreb_sabor_units()} if zagreb else {}
    muni_of = lambda mid: remap.get(mid, mid)

    sql = lambda q, **kw: db.session.execute(db.text(q), kw).fetchall()
    rows = sql("""
        select ps.municipality_id, el.name, sum(lr.votes)
        from elections_listresult lr
        join elections_electorallist el on el.id = lr.electoral_list_id
        left join elections_electoraldistrict ed on ed.id = el.district_id
        join elections_pollingstation ps on ps.id = lr.polling_station_id
        where el.election_round_id in :rounds and (ed.number is null or ed.number < 121)
        group by 1, 2""", rounds=tuple(round_ids))
    votes = defaultdict(lambda: defaultdict(int))        # muni -> party key -> votes
    labels, fulls, national = {}, defaultdict(lambda: defaultdict(int)), defaultdict(int)
    for mid, name, v in rows:
        mid = muni_of(mid)
        if mid not in real or not v:
            continue
        key, short, full = _map_party(name)
        votes[mid][key] += int(v)
        national[key] += int(v)
        labels[key] = short
        fulls[key][full] += int(v)
    turnout = {}
    for mid, reg, cast in sql("""
            select ps.municipality_id, sum(t.registered_voters), sum(t.ballots_cast)
            from elections_turnoutdata t
            join elections_pollingstation ps on ps.id = t.polling_station_id
            where t.election_round_id in :rounds group by 1""", rounds=tuple(round_ids)):
        mid = muni_of(mid)
        if mid in real and reg:
            r, c = turnout.get(mid, (0, 0))
            turnout[mid] = (r + int(reg), c + int(cast or 0))

    # Sabor: the district a town votes in, for opening it on the Sabor page.
    # Mobile and special stations put a handful of a town's votes into other
    # districts (in July 2020, holidaymakers: Krk 78 %), so it is the district holding at least 70 % of the town's
    # votes; a town split for real (Zagreb's units, mapped to Grad Zagreb) gets
    # none and the map opens the town's page instead.
    sabor_district = {}
    if kind == 'sabor':
        by_district = defaultdict(lambda: defaultdict(int))
        for mid, did, v in sql("""
                select ps.municipality_id, el.district_id, sum(lr.votes)
                from elections_listresult lr
                join elections_electorallist el on el.id = lr.electoral_list_id
                join elections_electoraldistrict ed on ed.id = el.district_id
                join elections_pollingstation ps on ps.id = lr.polling_station_id
                where el.election_round_id in :rounds and ed.number < 121
                group by 1, 2""", rounds=tuple(round_ids)):
            mid = muni_of(mid)
            if mid in real and v:
                by_district[mid][did] += int(v)
        for mid, dv in by_district.items():
            did = max(dv, key=dv.get)
            if dv[did] >= 0.7 * sum(dv.values()):
                sabor_district[mid] = did

    total = sum(national.values()) or 1
    top = sorted(national, key=lambda k: -national[k])[:MAP_TOP_PARTIES]
    parties = [{'key': k, 'label': labels[k], 'name': max(fulls[k], key=fulls[k].get),
                'votes': national[k], 'share': round(national[k] / total * 100, 2)} for k in top]
    munis = {}
    for mid in set(votes) | set(turnout):
        pv = votes.get(mid, {})
        all_votes = sum(pv.values())
        entry = {'name': real[mid].name, 'county_id': real[mid].county_id}
        if mid in sabor_district:
            entry['district_id'] = sabor_district[mid]
        if all_votes:
            win = max(pv, key=pv.get)
            entry.update(winner=win, winner_label=labels[win],
                         winner_share=round(pv[win] / all_votes * 100, 1),
                         shares={k: round(pv.get(k, 0) / all_votes * 100, 1) for k in top},
                         votes=all_votes)
            labels.setdefault(win, win)
        if mid in turnout and turnout[mid][0]:
            entry['turnout'] = round(turnout[mid][1] / turnout[mid][0] * 100, 1)
        munis[mid] = entry
    winners = defaultdict(int)
    for e in munis.values():
        if 'winner' in e:
            winners[e['winner']] += 1
    payload = {'kind': kind, 'year': year, 'round': rnd, 'parties': parties,
               'winners': sorted(({'key': k, 'label': labels[k], 'count': n} for k, n in winners.items()),
                                 key=lambda w: -w['count']),
               'munis': munis}
    _MAP_CACHE[cache_key] = payload
    return payload
