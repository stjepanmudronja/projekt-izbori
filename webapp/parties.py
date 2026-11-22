"""Stranke (/api/stranke) and Snaga stranaka (/api/analytics/party-strength):
the official party register linked to the election lists.
"""

import re
from collections import defaultdict
from flask import jsonify, request
from elections.importers.name_utils import strip_diacritics
from webapp.core import app, db, static_cache
from webapp.models import Election, ElectionRound, ElectionType, ElectoralList, RegisteredParty
from webapp.municipality_map import _map_party, _map_payload, _split_party


# ---- Stranke: the official party register linked to the election lists ----
# Election types whose lists are parties (or coalitions of them). Executive
# races (a list per candidate) and the 1993/1997 wards ("NAME (PARTY)") are not.
PARTY_LIST_TYPES = ('sabor', 'eu_parliament', 'local_municipal_council', 'local_city_council',
                    'local_county_assembly', 'local_kotar_assembly', 'sabor_zupanijski',
                    'sabor_dpv', 'sabor_vo', 'sabor_vur')
_PARTY_CACHE = {}
# Town and municipal councils are one race in practice (the map shows them
# together); a party's page shows them as one row.
PARTY_KIND_MERGE = {'local_municipal_council': ('vijeca', 'Gradska i općinska vijeća'),
                    'local_city_council': ('vijeca', 'Gradska i općinska vijeća')}


def _norm_party(text):
    return re.sub(r'[^A-Z0-9]', '', strip_diacritics((text or '').upper()))


def _party_links():
    """Which register party each election list names, as leader (first-named)
    or partner, cached until the server restarts.

    A list's parties are its comma- or line-separated parts. Each is matched
    by, in turn: its whole name, its name without a trailing abbreviation
    ("HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ"), its abbreviation, its leading
    name; punctuation and spacing are ignored ("SOCIJALNO - LIBERALNA"). A
    party only matches an election held while it existed (registered by that
    year, and not ceased before it), which is what tells apart an abbreviation
    used twice ("MOŽEMO!", 2017 and 2019); a part still matching two parties is
    left unlinked."""
    if 'links' in _PARTY_CACHE:
        return _PARTY_CACHE['links']
    parties = RegisteredParty.query.all()
    by_key = defaultdict(set)
    for p in parties:
        keys = {_norm_party(p.name)}
        if p.short_name and len(p.short_name) <= 30:
            keys.add(_norm_party(p.short_name))
        for k in keys:
            if len(k) >= 2:
                by_key[k].add(p.id)
    alive = {p.id: ((p.registered_on.year if p.registered_on else 1989),
                    (p.status_on.year if p.status == 'PRESTANAK' and p.status_on else 9999))
             for p in parties}

    def match(part, year):
        head, abbr = _split_party(part)
        tries = [part]
        if abbr:
            tries.append(part[:part.rfind(' - ')])
            # A two-part abbreviation ("AUTOHTONA - HRVATSKA SELJAČKA STRANKA
            # - A - HSS" is A-HSS, not HSS): try it before its last letters.
            # Its last letters alone would name another party, so stop there.
            segs = part.split(' - ')
            if len(segs) > 2 and len(segs[-2].strip()) <= 3:
                tries += [' - '.join(segs[:-2]), ' - '.join(segs[-2:])]
            else:
                tries += [abbr, head]
        else:
            tries.append(head)
        for t in tries:
            ids = {i for i in by_key.get(_norm_party(t), ()) if alive[i][0] <= year <= alive[i][1]}
            if len(ids) == 1:
                return ids.pop()
            if ids:
                return None                       # two parties fit: leave it
        return None

    rows = (db.session.query(ElectoralList.id, ElectoralList.name, Election.year)
            .join(ElectionRound, ElectoralList.election_round_id == ElectionRound.id)
            .join(Election, ElectionRound.election_id == Election.id)
            .join(ElectionType, Election.election_type_id == ElectionType.id)
            .filter(ElectionType.slug.in_(PARTY_LIST_TYPES)).all())
    links = defaultdict(list)                    # party id -> [(list id, role)]
    for list_id, name, year in rows:
        parts = [x.strip() for x in re.split(r'\n|,\s+', name or '') if x.strip()]
        seen = set()
        for i, part in enumerate(parts):
            pid = match(part, year)
            if pid and pid not in seen:
                seen.add(pid)
                links[pid].append((list_id, 'leader' if i == 0 else 'partner'))
    _PARTY_CACHE['links'] = links
    return links


def _party_list_votes():
    """Every party list's votes, its election, and each election's total of
    party-list votes (the share's denominator); Sabor's minority districts
    (121+) are a separate ballot and left out of both, and so are 1992's and
    1995's constituency races, cast on a second ballot beside the national
    list. Cached."""
    if 'votes' in _PARTY_CACHE:
        return _PARTY_CACHE['votes']
    sql = lambda q, **kw: db.session.execute(db.text(q), kw).fetchall()
    rows = sql("""
        select el.id, el.name, er.id, er.round_number, e.year, e.id, et.slug, et.name, coalesce(t.v, 0)
        from elections_electorallist el
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        left join elections_electoraldistrict ed on ed.id = el.district_id
        left join (select electoral_list_id, sum(votes) v from elections_listresult group by 1) t
               on t.electoral_list_id = el.id
        where et.slug in :types and (ed.number is null or ed.number < 121)
          -- 1992 and 1995: two ballots; only the national list (65 / 29) is the party vote
          and not (et.slug = 'sabor' and e.year = 1992 and coalesce(ed.number, 0) <> 65)
          and not (et.slug = 'sabor' and e.year = 1995 and coalesce(ed.number, 0) <> 29)""", types=PARTY_LIST_TYPES)
    lists, totals = {}, defaultdict(int)
    for lid, name, er_id, rnd, year, e_id, slug, tname, v in rows:
        slug, tname = PARTY_KIND_MERGE.get(slug, (slug, tname))
        lists[lid] = {'name': name, 'round_id': er_id, 'round': rnd, 'year': year,
                      'election_id': e_id, 'slug': slug, 'type': tname, 'votes': int(v)}
        totals[er_id] += int(v)
    _PARTY_CACHE['votes'] = (lists, totals)
    return lists, totals


def _party_summary(p, links, lists):
    elections = {(lists[l]['slug'], lists[l]['year']) for l, _ in links.get(p.id, []) if l in lists}
    years = [y for _, y in elections]
    return {
        'registry_number': p.registry_number, 'name': p.name, 'short_name': p.short_name,
        'city': (p.seat or '').split(',')[0].strip(), 'status': p.status,
        'registered_on': p.registered_on.isoformat() if p.registered_on else None,
        'status_on': p.status_on.isoformat() if p.status_on else None,
        'elections': len(elections), 'first_year': min(years) if years else None,
        'last_year': max(years) if years else None,
    }


@app.route('/api/stranke')
def parties_list():
    """Every party in the official register with how many elections it stood
    in (by the lists it led or joined)."""
    if 'list' not in _PARTY_CACHE:
        links = _party_links()
        lists, _ = _party_list_votes()
        _PARTY_CACHE['list'] = [_party_summary(p, links, lists)
                                for p in RegisteredParty.query.order_by(RegisteredParty.name)]
    return jsonify(_PARTY_CACHE['list'])


@app.route('/api/stranke/<int:registry_number>')
@static_cache
def party_page(registry_number):
    """One registered party: its register entry and, per election it stood in,
    the votes and share of the lists it led, the lists it joined as a partner,
    and for local councils in how many municipalities its list came first."""
    p = RegisteredParty.query.filter_by(registry_number=registry_number).first()
    if not p:
        return jsonify({'error': 'Ta stranka nije u registru.'}), 404
    links = _party_links()
    lists, totals = _party_list_votes()
    rows = defaultdict(lambda: {'led_votes': 0, 'led_lists': 0, 'partner_votes': 0,
                                'partner_lists': 0, 'round_ids': set(), 'map_keys': set(), 'top_list': None})
    for list_id, role in links.get(p.id, []):
        info = lists.get(list_id)
        if not info or info['round'] != 1:
            continue
        r = rows[(info['slug'], info['type'], info['year'])]
        r['round_ids'].add(info['round_id'])
        if role == 'leader':
            r['led_votes'] += info['votes']
            r['led_lists'] += 1
            r['map_keys'].add(_map_party(info['name'])[0])
            if not r['top_list'] or info['votes'] > r['top_list'][1]:
                r['top_list'] = (info['name'], info['votes'])
        else:
            r['partner_votes'] += info['votes']
            r['partner_lists'] += 1
    history = []
    for (slug, tname, year), r in rows.items():
        total = sum(totals[i] for i in r['round_ids'])
        won = None
        if slug == 'vijeca' and r['map_keys']:
            payload = _map_payload('vijece', year)
            if payload:
                won = sum(w['count'] for w in payload['winners'] if w['key'] in r['map_keys'])
        history.append({
            'slug': slug, 'election_type': tname, 'year': year,
            'led_votes': r['led_votes'], 'led_lists': r['led_lists'],
            'led_share': round(r['led_votes'] / total * 100, 2) if total and r['led_votes'] else None,
            'partner_votes': r['partner_votes'], 'partner_lists': r['partner_lists'],
            'top_list': r['top_list'][0] if r['top_list'] else None,
            'municipalities_won': won,
        })
    history.sort(key=lambda h: (-h['year'], h['election_type']))
    return jsonify({**_party_summary(p, links, lists), 'seat': p.seat, 'oib': p.oib, 'history': history})


# Party strength over time: which elections each kind covers. A party's
# share is the votes of the lists it led (first-named, so a coalition counts
# for its leader) over all party-list votes of that election's round 1, as on
# its Stranke page; local councils add up every municipality in the country.
PARTY_STRENGTH_KINDS = {
    'sabor': {'label': 'Sabor', 'slugs': ('sabor',)},
    'eu': {'label': 'Europski parlament', 'slugs': ('eu_parliament',)},
    'vijeca': {'label': 'Gradska i općinska vijeća', 'slugs': ('vijeca',)},
    'skupstine': {'label': 'Županijske skupštine', 'slugs': ('local_county_assembly',)},
}


# Every registration is its own party, renamed or not (the data's owner: a
# name change makes a different party). So the 1992 list "Socijaldemokratska
# partija Hrvatske - Stranka demokratskih promjena" is register no. 70, not
# today's SDP (no. 88), and 2011's Hrvatski rast (no. 218) is not 2012's
# HRAST - Pokret za uspješnu Hrvatsku (no. 246).
# Kinds decided on one national ballot, where a coalition is one agreement in
# every district (see party_strength).
PARTY_STRENGTH_NATIONAL = ('sabor', 'eu')


@app.route('/api/analytics/party-strength')
def party_strength():
    """Every registered party's share in every election of the chosen kinds
    (`kind` = one of PARTY_STRENGTH_KINDS, or `sve` for all of them), ready
    for one line per party. Parties come sorted by their best share; the
    frontend shows the strongest few and lets the rest be switched on."""
    kind = request.args.get('kind', 'sabor')
    kinds = list(PARTY_STRENGTH_KINDS) if kind == 'sve' else [kind]
    if any(k not in PARTY_STRENGTH_KINDS for k in kinds):
        return jsonify({'error': 'Nepoznata vrsta izbora.'}), 400
    key = ('strength', kind)
    if key in _PARTY_CACHE:
        return jsonify(_PARTY_CACHE[key])
    slug_kind = {s: k for k in kinds for s in PARTY_STRENGTH_KINDS[k]['slugs']}
    links = _party_links()
    lists, totals = _party_list_votes()

    elections = {}                               # (kind, year) -> round-1 round ids
    for info in lists.values():
        k = slug_kind.get(info['slug'])
        if k and info['round'] == 1:
            elections.setdefault((k, info['year']), set()).add(info['round_id'])
    total = {e: sum(totals[r] for r in rids) for e, rids in elections.items()}

    parties = {p.id: p for p in RegisteredParty.query.all()}
    owner = {pid: pid for pid in parties}          # every registration is its own party
    label = lambda pid: parties[pid].short_name or parties[pid].name

    # Each round-1 list of these kinds: its parties, leader first.
    members = defaultdict(list)                  # list id -> [(party, is leader)]
    for pid, plist in links.items():
        for list_id, role in plist:
            info = lists.get(list_id)
            if info and info['round'] == 1 and info['slug'] in slug_kind:
                members[list_id].append((owner[pid], role == 'leader'))
    leader_of = {}
    for list_id, ms in members.items():
        lead = [pid for pid, is_lead in ms if is_lead]
        if lead:
            leader_of[list_id] = lead[0]
    # A national ballot's coalition is one agreement however each district
    # printed it: 2000's SDP-HSLS list reads "HSLS, SDP" in some districts.
    # One set of parties in one election gets one leader, the one heading
    # most of its votes. Local coalitions are agreed town by town, so there
    # whoever is named first leads.
    coalition_votes = defaultdict(lambda: defaultdict(int))
    for list_id, lead in leader_of.items():
        info = lists[list_id]
        if slug_kind[info['slug']] in PARTY_STRENGTH_NATIONAL and len(members[list_id]) > 1:
            ckey = (info['slug'], info['year'], frozenset(pid for pid, _ in members[list_id]))
            coalition_votes[ckey][lead] += info['votes']
    for list_id in leader_of:
        info = lists[list_id]
        ckey = (info['slug'], info['year'], frozenset(pid for pid, _ in members[list_id]))
        if ckey in coalition_votes:
            leader_of[list_id] = max(coalition_votes[ckey].items(), key=lambda kv: kv[1])[0]

    led, led_top = defaultdict(lambda: defaultdict(int)), defaultdict(dict)
    joined_by = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))   # party, election, leader -> votes
    joined_lists = defaultdict(lambda: defaultdict(dict))                    # party, election, leader -> biggest list
    for list_id, lead in leader_of.items():
        info = lists[list_id]
        e = (slug_kind[info['slug']], info['year'])
        for pid in {pid for pid, _ in members[list_id]}:
            if pid == lead:
                led[pid][e] += info['votes']
                if info['votes'] > led_top[pid].get(e, ('', -1, None))[1]:
                    led_top[pid][e] = (info['name'], info['votes'], lead)
            else:
                joined_by[pid][e][lead] += info['votes']
                if info['votes'] > joined_lists[pid][e].get(lead, ('', -1))[1]:
                    joined_lists[pid][e][lead] = (info['name'], info['votes'])
    # A partner's votes: on a national ballot the one coalition it joined (the
    # biggest, should a misread list name put it in two); locally, every list
    # it joined anywhere in the country.
    joined, joined_top = defaultdict(dict), defaultdict(dict)
    for pid, by_e in joined_by.items():
        for e, by_lead in by_e.items():
            lead = max(by_lead, key=by_lead.get)
            joined[pid][e] = by_lead[lead] if e[0] in PARTY_STRENGTH_NATIONAL else sum(by_lead.values())
            joined_top[pid][e] = (joined_lists[pid][e][lead][0], 0, lead)

    def point(pid, e, v, top):
        k, y = e
        name, _, lead = top[pid][e]
        pt = {'kind': k, 'year': y, 'votes': v, 'share': round(v / total[e] * 100, 2), 'top_list': name}
        if lead != pid:
            pt['leader'] = label(lead)
        return pt

    order = lambda e: (e[1], e[0])
    series = []
    for pid in set(led) | set(joined):
        points = [point(pid, e, v, led_top) for e, v in sorted(led[pid].items(), key=lambda kv: order(kv[0]))
                  if v and total.get(e)]
        # Partner only where the party led nothing that election, or it would vanish.
        partner = [point(pid, e, v, joined_top) for e, v in sorted(joined[pid].items(), key=lambda kv: order(kv[0]))
                   if v and total.get(e) and not led[pid].get(e)]
        if not points and not partner:
            continue
        p = parties[pid]
        series.append({
            'registry_number': p.registry_number, 'name': p.name, 'short_name': p.short_name or '',
            'active': p.status != 'PRESTANAK', 'peak': max((pt['share'] for pt in points), default=0),
            'points': points, 'partner_points': partner,
        })
    series.sort(key=lambda s: -s['peak'])
    payload = {
        'kind': kind,
        'kinds': [{'key': k, 'label': v['label']} for k, v in PARTY_STRENGTH_KINDS.items()],
        'elections': [{'kind': k, 'year': y, 'votes': total[(k, y)]} for k, y in sorted(total, key=lambda e: (e[1], e[0]))],
        'parties': series[:40],
    }
    _PARTY_CACHE[key] = payload
    return jsonify(payload)
