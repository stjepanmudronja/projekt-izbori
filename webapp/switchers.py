"""Prelasci između stranaka (Analitika): politicians who stood for one party
and later for another.

Which party someone stood for is read off the list they were on, linked to
the party register as on Stranke (`_party_matcher`), so a renamed party is
one party (Most nezavisnih lista and MOST, HNS and HNS - Liberalni
demokrati): a new name is not a move. A printed party the register does not
match (Živi zid, Pametno) is a party of its own by its wording. Sources:
- Sabor and EU list candidacies (the 1990 chambers' and 1992/1995
  constituency candidates, whose "list" is their nominating party, included);
- the Sabor and Županijski dom rosters (ParliamentMember), whose party is
  printed with each member — the only source for 2003-2011, whose lists'
  candidates are not published.
- mayors, načelnici and župani 2009-2025: the parties that nominated them
  (ElectoralList.parties, from DIP's archive and the 2009 report; see
  set_local_nominators). Two local races in different counties are never
  compared: there a shared name is likelier two people than one who moved.

A list of several parties (a coalition) names its leader first. A move is
a step to a list whose leader was not on the previous list while the
previous leader is not on the new one (`moved`): someone from a junior party
on an HDZ-led list who then runs on their own party's list has not moved,
and a small partner on both sides of a switch does not hide it. That misses
a member of a coalition partner who joins its leader, which cannot be told
from the lists. Independent lists are their
own group ("Nezavisni"); a list that links to no registered party is
skipped, never read as a move.

People are matched by name across elections, as everywhere on the site, so
two people of one name can look like one who moved; the page shows those
elected at least once by default, where that is rare.
"""
from datetime import date
import functools
import re
from collections import defaultdict

from flask import jsonify

from elections.importers.name_utils import strip_diacritics
from webapp.common import party_wording_key, sabor_seat_winner_candidacy_ids
from webapp.core import app, data_cache, db, static_cache
from webapp.meta import name_case, party_case
from webapp.models import RegisteredParty
from webapp.municipality_map import _split_party
from webapp.incumbency import exec_races
from webapp.parties import _party_matcher

SWITCH_SLUGS = ('sabor', 'sabor_dpv', 'sabor_vo', 'sabor_vur', 'sabor_zupanijski', 'eu_parliament')
EXEC_SLUGS = ('local_mayor', 'local_city_mayor', 'local_county_prefect')
KIND_OF = {'sabor': 'sabor', 'sabor_dpv': 'sabor', 'sabor_vo': 'sabor', 'sabor_vur': 'sabor',
           'sabor_zupanijski': 'zd', 'eu_parliament': 'eu',
           'local_mayor': 'lokalni', 'local_city_mayor': 'lokalni', 'local_county_prefect': 'lokalni'}
KIND_LABEL = {'sabor': 'Sabor', 'zd': 'Županijski dom', 'eu': 'Europski parlament',
              'lokalni': 'Lokalni izbori'}
OFFICE = {'local_mayor': 'načelnik', 'local_city_mayor': 'gradonačelnik', 'local_county_prefect': 'župan'}
INDEPENDENT = 'NEZ'
# One party under successive registrations: the register gives each its own
# entry (SKH-SDP 1990, SDPH, SDP - Stranka demokratskih promjena, then SDP),
# but standing for the next one is not a move. Register no. -> the latest.
LINEAGE = {1: 88, 48: 88, 70: 88}
# Printed names of a registration that the register does not list, so the
# matcher leaves them out: party no. 362 was registered in March 2020 and stood
# that July as "Domovinski pokret Miroslava Škore"; it is the same
# registration as the later Domovinski pokret, so standing for both is no move.
# The 1990 rosters' "SKH-SDP" is register no. 1, entered a month after that
# election, so the matcher (a party only matches while it exists) skips it.
SWITCH_ALIASES = {'DOMOVINSKI POKRET MIROSLAVA ŠKORE - DOMOVINSKI POKRET': 362, 'SKH-SDP': 1}
# "NK" is how the 1990 rosters print an independent (nezavisni kandidat).
# Nezavisna platforma sjevera and (Neovisni) Nezavisni za Hrvatsku are parties.
_INDEPENDENT_RE = re.compile(r'^\s*(?!NEZAVISNA PLATFORMA|NEZAVISNI ZA HRVATSKU|NEOVISNI ZA HRVATSKU)(NEZAVISN|NEOVISN|KANDIDACIJSKA LISTA GRUPE|LISTA GRUPE BIRAČA|GRUPA BIRAČA|KANDIDATI? GRUPE BIRAČA|NK\s*$)', re.I)
# A local candidate standing alone: "DR. NENAD PANIAN - NEZAVISNA LISTA - … - NL"
# (2025), "DINO DEBELJUH - NEZAVISNI KANDIDAT" (2009), "KANDIDAT GRUPE BIRAČA".
_OWN_LIST_RE = re.compile(r'\bNEZAVISN[AI] (LISTA|KANDIDAT)\b|GRUPE BIRAČA', re.I)


def _rows(q, **kw):
    return db.session.execute(db.text(q), kw).fetchall()


def _norm(text):
    return re.sub(r'[^A-Z0-9]', '', strip_diacritics((text or '').upper()))


def _parts(name):
    return [x.strip() for x in re.split(r'\n|,\s*', name or '') if x.strip()]


def neutral(ev):
    """A local race on the candidate's own independent list (alone or with
    partners: "IVAN PENAVA NEZAVISNA LISTA - IP-NL, HKS") says nothing about
    the party they belong to — the leader of DP ran so in Vukovar 2021 — so
    it neither breaks nor makes a move."""
    return ev['source'] == 'local' and INDEPENDENT in ev['parties']


def moved(a, b):
    """A step from list a to list b is a move when neither leader stood on the
    other's list: a junior partner then standing on its own list has not
    moved (its party was on the first), and a small party on both sides of a
    big switch (HKS with HDZ in 2017 and with DP in 2020) does not hide it."""
    return a['parties'][0] not in b['parties'] and b['parties'][0] not in a['parties']


def party_moves(path):
    """[{'year', 'from', 'to'}] along a person's path (events with parties,
    in order). Two local races in different counties are not compared: there
    one name is likelier two people than one who moved."""
    moves, prev = [], None
    for ev in path:
        if neutral(ev):
            continue
        if prev and not (prev['county'] and ev['county'] and prev['county'] != ev['county']) and moved(prev, ev):
            moves.append({'year': ev['year'], 'from': prev['parties'][0], 'to': ev['parties'][0]})
        prev = ev
    return moves


_PATHS = data_cache({})


def party_paths():
    """Everyone's party path, cached until the data changes:
    {'paths': {person id: [event, ...] in date order, events with parties only},
     'label': key -> short label, 'name': key -> full name, 'reg': key -> register no.,
     'roster_years': [...]}. An event is {'year', 'kind', 'parties' (leader
    first), 'list' (printed), 'elected', 'source' (list / roster / local), 'county'}."""
    if 'v' in _PATHS:
        return _PATHS['v']
    match = _party_matcher()
    reg = {p.id: p for p in RegisteredParty.query}
    by_number = {p.registry_number: p.id for p in reg.values()}
    successor = {p.id: by_number[LINEAGE[p.registry_number]] for p in reg.values() if p.registry_number in LINEAGE}
    aliases = {party_wording_key(name): by_number[n] for name, n in SWITCH_ALIASES.items() if n in by_number}
    unregistered = {}               # 'w:<wording key>' -> label

    def parties_of(name, year, own_name=None):
        """A list's (or a roster entry's) parties, its first-named first:
        register ids, or 'w:<name>' for a printed party the register does not
        match (Živi zid, Pametno), so a list is never credited to a partner
        just because its leader is unmatched. A list named for the candidate
        alone (a minority seat, an independent) names no party."""
        if _INDEPENDENT_RE.match(name or ''):
            return [INDEPENDENT]
        out = []
        for part in _parts((name or '').replace('"', '')):
            pid, head = resolve(part, year)
            if isinstance(pid, str) and pid.startswith('w:') and own_name and own_name in head:
                continue                                       # "dr. sc. Milorad Pupovac"
            if pid and pid not in out:
                out.append(pid)
        return out

    @functools.lru_cache(maxsize=None)
    def resolve(part, year):
        """One printed party name -> (party key, its leading name normalised)."""
        if ':' in part:                     # "BRUNA ESIH - ZLATKO HASANBEGOVIĆ: NEOVISNI ZA HRVATSKU"
            part = part.split(':', 1)[1].strip()
        wk = party_wording_key(part)
        pid = aliases.get(wk) or match(part, year)
        pid = successor.get(pid, pid)
        if pid or len(wk) < 2:
            return pid, ''
        head, abbr = _split_party(part)
        segs = [x.strip() for x in part.split(' - ')]
        if abbr and len(segs) > 2 and len(segs[-2]) <= 3:
            abbr = f'{segs[-2]}-{abbr}'                        # "AUTOHTONA - … - A - HSP" is A-HSP, not HSP
        short = abbr or head
        key = 'w:' + _norm(short)
        unregistered.setdefault(key, short if re.fullmatch(r'[A-ZČĆŠŽĐ0-9!-]{2,8}', short) else party_case(short))
        return key, _norm(head)

    # Every candidacy: person, election, list.
    cands = _rows("""
        select c.id, c.person_id, et.slug, e.id, e.year, coalesce(e.date, make_date(e.year, 1, 1)), el.id, el.name,
               p.first_name || ' ' || p.last_name
        from elections_candidacy c
        join elections_person p on p.id = c.person_id
        join elections_electorallist el on el.id = c.electoral_list_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug in :slugs""", slugs=SWITCH_SLUGS)

    # Who was elected: rosters, EU mandates, Sabor seats off the votes (2015 on).
    elected_cands = {cid for (cid,) in _rows('select candidacy_id from elections_electedmandate')}
    roster = _rows("""
        select pm.person_id, pm.candidacy_id, pm.party, et.slug, e.id, e.year, coalesce(e.date, make_date(e.year, 1, 1))
        from elections_parliamentmember pm
        join elections_election e on e.id = pm.election_id
        join elections_electiontype et on et.id = e.election_type_id""")
    roster_elections = {r[4] for r in roster}
    elected_cands |= {r[1] for r in roster if r[1]}
    for (er_id,) in _rows("""
            select er.id from elections_electionround er join elections_election e on e.id = er.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug = 'sabor' and e.year >= 2015"""):
        elected_cands |= set(sabor_seat_winner_candidacy_ids(er_id))

    # Events: (person) -> {(date, kind): {'year', 'kind', 'parties': [...], 'list', 'elected'}}.
    events = defaultdict(dict)

    def add(pid, date, year, slug, parties, label, elected, source, county=None):
        kind = KIND_OF[slug]
        ev = events[pid].setdefault((date, kind), {'year': year, 'kind': kind, 'parties': [], 'list': label,
                                                   'elected': False, 'source': source, 'county': county})
        for p in parties:
            if p not in ev['parties']:
                ev['parties'].append(p)
        ev['elected'] = ev['elected'] or elected

    for cid, pid, slug, eid, year, date, list_id, list_name, person_name in cands:
        parties = parties_of(list_name, year, _norm(person_name))
        add(pid, date, year, slug, parties, (list_name or '').replace('\n', ', '), cid in elected_cands, 'list')
    # Roster members with no candidacy behind them: their printed party.
    for pid, cid, party, slug, eid, year, date in roster:
        if cid:
            continue
        parties = parties_of(party, year)
        # A roster's party can be the member's at the end of the term
        # (Jadranka Kosor 2011: elected for HDZ, listed as independent).
        add(pid, date, year, slug, parties, party or '', True, 'roster')

    # Mayors, načelnici and župani 2009-2025: the parties that nominated them
    # (ElectoralList.parties, filled by set_local_nominators), round 1's list.
    winners = {(key, y): r['cands'][0][1] for (key, y), r in exec_races().items()}

    @functools.lru_cache(maxsize=None)
    def local_parties(names, year):
        out = []
        for name in names.split('\n'):
            for p in ([INDEPENDENT] if _OWN_LIST_RE.search(name) else parties_of(name, year)):
                if p not in out:
                    out.append(p)
        return tuple(out)
    muni_county = dict(_rows('select m.id, c.code from elections_municipality m join elections_county c on c.id = m.county_id'))
    county_code = dict(_rows('select id, code from elections_county'))
    places = dict(_rows('select id, name from elections_municipality'))
    places.update({('c', i): n for i, n in _rows('select id, name from elections_county')})
    for pid, slug, year, date, num, names in _rows("""
            select c.person_id, et.slug, e.year, coalesce(e.date, make_date(e.year, 1, 1)), ed.number,
                   string_agg(pa.name, E'\n' order by lp.id)
            from elections_candidacy c
            join elections_electorallist el on el.id = c.electoral_list_id
            join elections_electorallist_parties lp on lp.electorallist_id = el.id
            join elections_party pa on pa.id = lp.party_id
            join elections_electoraldistrict ed on ed.id = el.district_id
            join elections_electionround er on er.id = el.election_round_id
            join elections_election e on e.id = er.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug in :slugs and er.round_number = 1
            group by 1, 2, 3, 4, 5""", slugs=EXEC_SLUGS):
        prefect = slug == 'local_county_prefect'
        parties = local_parties(names, year)
        place = places.get(('c', num) if prefect else num) or ''
        label = f"{OFFICE[slug]}, {party_case(place) if prefect else name_case(place)}: {names.replace(chr(10), ', ')}"
        add(pid, date, year, slug, list(parties), label, winners.get((('c' if prefect else 'm', num), year)) == pid, 'local',
            county_code.get(num) if prefect else muni_county.get(num))

    def reg_label(p):
        return p.short_name if p.short_name and len(p.short_name) <= 14 else party_case(p.name)
    registered_labels = {reg_label(p) for p in reg.values()}

    def label(pid):
        if pid == INDEPENDENT:
            return 'Nezavisni'
        if pid in unregistered:
            # 1990's KNS (Koalicija narodnog sporazuma) is not 1992's KNS
            # (Kršćanska narodna stranka): a printed name shared with a
            # registered party says it is outside the register.
            own = unregistered[pid]
            return f'{own} (izvan registra)' if own in registered_labels else own
        return reg_label(reg[pid])

    paths = {}
    for pid, evs in events.items():
        path = [ev for _, ev in sorted(evs.items(), key=lambda kv: (kv[0][0], kv[0][1])) if ev['parties']]
        if path:
            paths[pid] = path
    keys = {k for path in paths.values() for ev in path for k in ev['parties']}
    _PATHS['v'] = {
        'paths': paths,
        'label': {k: label(k) for k in keys},
        'name': {k: 'Nezavisne liste i kandidati' if k == INDEPENDENT else
                    'Nije pronađena u registru stranaka' if k in unregistered else party_case(reg[k].name) for k in keys},
        'reg': {k: reg[k].registry_number for k in keys if k in reg},
        'roster_years': sorted({r[5] for r in roster}),
    }
    return _PATHS['v']


@app.route('/api/analytics/switchers')
@static_cache
def party_switchers():
    pp = party_paths()

    used = set()
    people = []
    list_index = {}                 # a list's printed name, sent once: path events give its index
    for pid, path in pp['paths'].items():
        if len(path) < 2:
            continue
        moves = party_moves(path)
        if not moves:
            continue
        ever_elected = any(ev['elected'] for ev in path)
        for ev in path:
            used.update(ev['parties'])
        people.append({'person_id': pid, 'elected': ever_elected, 'moves': moves,
                       'path': [{'year': ev['year'], 'kind': ev['kind'], 'parties': ev['parties'],
                                 'list': list_index.setdefault(ev['list'], len(list_index)),
                                 'elected': ev['elected'], 'source': ev['source'], 'county': ev['county'],
                                 'neutral': neutral(ev)} for ev in path]})

    names = {}
    if people:
        for pid, fn, ln, dis in _rows('select id, first_name, last_name, disambiguation from elections_person where id = any(:ids)',
                                      ids=[p['person_id'] for p in people]):
            names[pid] = (name_case(f'{fn} {ln}'), dis or '')
    for p in people:
        p['name'], p['label'] = names.get(p['person_id'], ('?', ''))
    people.sort(key=lambda p: (-len(p['moves']), -p['moves'][-1]['year'], p['name']))

    return jsonify({
        'parties': {str(k): {'label': pp['label'][k], 'name': pp['name'][k], 'registry_number': pp['reg'].get(k)}
                    for k in used},
        'kinds': KIND_LABEL,
        'lists': list(list_index),
        'people': people,
        'roster_years': pp['roster_years'],
    })


# ---- Vjernost stranci: the medal on a politician's page ----
LOYAL_MIN_ELECTIONS = 3     # elections with a known party in the loyal run
LOYAL_YEARS = 10            # the run began at least this many years before today
LOYAL_ACTIVE = 5            # ... and its last election is at most this many years old


def _common(events):
    """The party on every one of these lists, the one leading them most often
    first; never "independent", which is no party to be loyal to."""
    common = set(events[0]['parties']).intersection(*(ev['parties'] for ev in events[1:])) - {INDEPENDENT}
    if not common:
        return None
    lead = lambda k: sum(1 for ev in events if ev['parties'][0] == k)
    return max(common, key=lambda k: (lead(k), -events[0]['parties'].index(k)))


def loyalty_of(path, year=None):
    """{'kind': 'career' | 'since', 'party', 'from', 'to', 'elections', 'before'}
    or None. The medal is for the same party for the last LOYAL_YEARS years up
    to today (`year`, default this year): the unbroken run of elections at the
    end of the path that shares one party (local races on their own
    independent list aside) began LOYAL_YEARS or more years ago, has at least
    LOYAL_MIN_ELECTIONS elections, and its last one is no older than
    LOYAL_ACTIVE years — so someone who retired loyal gets none. Career: the
    run is the whole path; since: they stood for another party before."""
    year = year or date.today().year
    events = [ev for ev in path if not neutral(ev)]
    if len(events) < LOYAL_MIN_ELECTIONS or events[-1]['year'] < year - LOYAL_ACTIVE:
        return None
    i = len(events) - 1
    while i > 0 and _common(events[i - 1:]):
        i -= 1
    run = events[i:]
    party = _common(run)
    if not party or len(run) < LOYAL_MIN_ELECTIONS or run[0]['year'] > year - LOYAL_YEARS:
        return None
    return {'kind': 'since' if i else 'career', 'party': party, 'from': run[0]['year'], 'to': run[-1]['year'],
            'elections': len(run), 'before': events[i - 1]['parties'][0] if i else None}


@app.route('/api/person/<int:person_id>/loyalty')
def person_loyalty(person_id):
    """The medal for one politician, or {'medal': None}. Reads the cached
    party paths, so only the first call after a data change is slow."""
    from webapp.women import name_gender
    pp = party_paths()
    m = loyalty_of(pp['paths'].get(person_id, []))
    if m:
        first = db.session.execute(db.text('select first_name from elections_person where id = :i'), {'i': person_id}).scalar()
        m['gender'] = name_gender(first)          # for the wording: "vjeran" / "vjerna"
        for k in ('party', 'before'):
            if m[k] is not None:
                m[k] = {'label': pp['label'][m[k]], 'name': pp['name'][m[k]], 'registry_number': pp['reg'].get(m[k])}
    return jsonify({'medal': m})
