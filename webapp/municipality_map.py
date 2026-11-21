"""Karta općina (/api/map/*): every municipality coloured by one election.
"""

import re
from collections import defaultdict
from flask import jsonify, request
from webapp.core import app, db, static_cache
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
# One party under two names on the ballot, joined so the map colours it the
# same and the swing view can compare it across years (key -> canonical key).
# Only real renames: "Narodna stranka - Reformisti" is not HNS.
_MAP_KEY_ALIASES = {
    'DOMOVINSKI POKRET MIROSLAVA ŠKORE': 'DP',            # Sabor 2020; "DP" from 2021
    'HRVATSKI LABURISTI-STRANKA RADA': 'HRVATSKI LABURISTI',  # Sabor 2011
}
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
    if head.upper() in _MAP_KEY_ALIASES:
        key = _MAP_KEY_ALIASES[head.upper()]
        return key, key, first
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


def _map_votes(kind, year, rnd=1):
    """One election's votes per municipality and party key (`_map_party`),
    with the party labels, the national totals and turnout per municipality;
    shared by the map and the swing view, cached. None when there is no such
    election. Sabor's minority districts (121+) are left out and Zagreb's
    Sabor units count as Grad Zagreb."""
    cache_key = ('votes', kind, year, rnd)
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
    out = {'round_ids': round_ids, 'real': real, 'muni_of': muni_of, 'votes': votes,
           'labels': labels, 'fulls': fulls, 'national': national, 'turnout': turnout}
    _MAP_CACHE[cache_key] = out
    return out


def _map_payload(kind, year, rnd=1):
    """The map's figures for one election (see map_data), cached; None when
    there is no such election."""
    cache_key = (kind, year, rnd)
    if cache_key in _MAP_CACHE:
        return _MAP_CACHE[cache_key]
    mv = _map_votes(kind, year, rnd)
    if mv is None:
        return None
    round_ids, real, muni_of = mv['round_ids'], mv['real'], mv['muni_of']
    votes, national, turnout = mv['votes'], mv['national'], mv['turnout']
    labels, fulls = dict(mv['labels']), mv['fulls']   # a copy: the winner loop adds to labels
    sql = lambda q, **kw: db.session.execute(db.text(q), kw).fetchall()

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


@app.route('/api/map/swing')
@static_cache(maxsize=300)
def map_swing():
    """How one party's share (or turnout) changed per municipality between
    two elections: `kind`, `year`, `round` the later one, `base_kind`,
    `base_year`, `base_round` the earlier (any two, also of different
    kinds: a party is matched by its `_map_party` key, so HDZ is HDZ on
    every ballot), `party` a key or `__turnout`. Shares are of the
    municipality's list votes in each election; a party with no list in a
    town that voted counts 0 % there. Only towns with results in both
    elections get a change. Without `party`, the largest party present in
    both is shown."""
    a = request.args
    kind, year, rnd = a.get('kind'), a.get('year', type=int), a.get('round', 1, type=int)
    bkind, byear, brnd = a.get('base_kind'), a.get('base_year', type=int), a.get('base_round', 1, type=int)
    if kind not in MAP_KINDS or bkind not in MAP_KINDS or not year or not byear:
        return jsonify({'error': 'Nepoznati izbori.'}), 400
    new, old = _map_votes(kind, year, rnd), _map_votes(bkind, byear, brnd)
    if new is None or old is None:
        return jsonify({'error': 'Nema tih izbora.'}), 404

    def share(mv, key):
        total = sum(mv['national'].values()) or 1
        return round(mv['national'].get(key, 0) / total * 100, 2)
    # Parties on both ballots, with at least 0.5 % nationally in one of them.
    both = [k for k in set(new['national']) & set(old['national'])
            if max(share(new, k), share(old, k)) >= 0.5]
    both.sort(key=lambda k: -(new['national'][k] + old['national'][k]))
    parties = [{'key': k, 'label': new['labels'].get(k) or old['labels'].get(k) or k,
                'share': share(new, k), 'base_share': share(old, k)} for k in both]
    party = a.get('party') or (parties[0]['key'] if parties else '__turnout')
    if party != '__turnout' and party not in both:
        return jsonify({'error': 'Ta stranka nije na oba glasanja.'}), 404

    def values(mv):
        out = {}
        if party == '__turnout':
            for mid, (reg, cast) in mv['turnout'].items():
                if reg:
                    out[mid] = round(cast / reg * 100, 1)
        else:
            for mid, pv in mv['votes'].items():
                total = sum(pv.values())
                if total:
                    out[mid] = round(pv.get(party, 0) / total * 100, 1)
        return out
    now, before = values(new), values(old)
    real = new['real']
    munis = {mid: {'name': real[mid].name, 'county_id': real[mid].county_id,
                   'value': now[mid], 'base': before[mid], 'change': round(now[mid] - before[mid], 1)}
             for mid in set(now) & set(before) if mid in real}
    if party == '__turnout':
        def national_turnout(mv):
            reg = sum(r for r, _c in mv['turnout'].values())
            return round(sum(c for _r, c in mv['turnout'].values()) / reg * 100, 2) if reg else None
        nat_now, nat_before = national_turnout(new), national_turnout(old)
    else:
        nat_now, nat_before = share(new, party), share(old, party)
    return jsonify({
        'party': party, 'parties': parties,
        'national': {'value': nat_now, 'base': nat_before,
                     'change': round(nat_now - nat_before, 2) if nat_now is not None and nat_before is not None else None},
        'gained': sum(1 for m in munis.values() if m['change'] > 0),
        'lost': sum(1 for m in munis.values() if m['change'] < 0),
        'munis': munis,
    })
