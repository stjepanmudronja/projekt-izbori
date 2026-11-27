"""Prelasci između stranaka (Analitika): politicians who stood for one party
and later for another, in the national elections.

Which party someone stood for is read off the list they were on, linked to
the party register as on Stranke (`_party_matcher`), so a renamed party is
one party (Most nezavisnih lista and MOST, HNS and HNS - Liberalni
demokrati): a new name is not a move. A printed party the register does not
match (Živi zid, Pametno) is a party of its own by its wording. Sources, all national:
- Sabor and EU list candidacies (the 1990 chambers' and 1992/1995
  constituency candidates, whose "list" is their nominating party, included);
- the Sabor and Županijski dom rosters (ParliamentMember), whose party is
  printed with each member — the only source for 2003-2011, whose lists'
  candidates are not published.
Mayors and župani are left out: their results name the candidate only, not
who nominated them.

A list of several parties (a coalition) stands for all of them, so a move
is a step to a list that shares **no** party with the one before: someone
from a junior party on an HDZ-led list who then runs on their own party's
list has not moved. That misses a member of a coalition partner who joins
its leader, which cannot be told from the lists. Independent lists are their
own group ("Nezavisni"); a list that links to no registered party is
skipped, never read as a move.

People are matched by name across elections, as everywhere on the site, so
two people of one name can look like one who moved; the page shows those
elected at least once by default, where that is rare.
"""
import re
from collections import defaultdict

from flask import jsonify

from elections.importers.name_utils import strip_diacritics
from webapp.common import party_wording_key, sabor_seat_winner_candidacy_ids
from webapp.core import app, db, static_cache
from webapp.meta import name_case, party_case
from webapp.models import RegisteredParty
from webapp.municipality_map import _split_party
from webapp.parties import _party_matcher

SWITCH_SLUGS = ('sabor', 'sabor_dpv', 'sabor_vo', 'sabor_vur', 'sabor_zupanijski', 'eu_parliament')
KIND_OF = {'sabor': 'sabor', 'sabor_dpv': 'sabor', 'sabor_vo': 'sabor', 'sabor_vur': 'sabor',
           'sabor_zupanijski': 'zd', 'eu_parliament': 'eu'}
KIND_LABEL = {'sabor': 'Sabor', 'zd': 'Županijski dom', 'eu': 'Europski parlament'}
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
_INDEPENDENT_RE = re.compile(r'^\s*(?!NEZAVISNA PLATFORMA|NEZAVISNI ZA HRVATSKU|NEOVISNI ZA HRVATSKU)(NEZAVISN|NEOVISN|KANDIDACIJSKA LISTA GRUPE|LISTA GRUPE BIRAČA|GRUPA BIRAČA|NK\s*$)', re.I)


def _rows(q, **kw):
    return db.session.execute(db.text(q), kw).fetchall()


def _norm(text):
    return re.sub(r'[^A-Z0-9]', '', strip_diacritics((text or '').upper()))


def _parts(name):
    return [x.strip() for x in re.split(r'\n|,\s*', name or '') if x.strip()]


@app.route('/api/analytics/switchers')
@static_cache
def party_switchers():
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
            wk = party_wording_key(part)
            pid = aliases.get(wk) or match(part, year)
            pid = successor.get(pid, pid)
            if not pid and len(wk) >= 2:
                head, abbr = _split_party(part)
                if own_name and own_name in _norm(head):          # "dr. sc. Milorad Pupovac"
                    continue
                segs = [x.strip() for x in part.split(' - ')]
                if abbr and len(segs) > 2 and len(segs[-2]) <= 3:
                    abbr = f'{segs[-2]}-{abbr}'                    # "AUTOHTONA - … - A - HSP" is A-HSP, not HSP
                short = abbr or head
                pid = 'w:' + _norm(short)
                unregistered.setdefault(pid, short if re.fullmatch(r'[A-ZČĆŠŽĐ0-9!-]{2,8}', short) else party_case(short))
            if pid and pid not in out:
                out.append(pid)
        return out

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

    def add(pid, date, year, slug, parties, label, elected, source):
        kind = KIND_OF[slug]
        ev = events[pid].setdefault((date, kind), {'year': year, 'kind': kind, 'parties': [], 'list': label,
                                                   'elected': False, 'source': source})
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

    used = set()
    people = []
    list_index = {}                 # a list's printed name, sent once: path events give its index
    for pid, evs in events.items():
        path = [ev for _, ev in sorted(evs.items(), key=lambda kv: (kv[0][0], kv[0][1])) if ev['parties']]
        if len(path) < 2:
            continue
        moves = []
        for a, b in zip(path, path[1:]):
            if not set(a['parties']) & set(b['parties']):
                moves.append({'year': b['year'], 'from': a['parties'][0], 'to': b['parties'][0]})
        if not moves:
            continue
        ever_elected = any(ev['elected'] for ev in path)
        for ev in path:
            used.update(ev['parties'])
        people.append({'person_id': pid, 'elected': ever_elected, 'moves': moves,
                       'path': [{'year': ev['year'], 'kind': ev['kind'], 'parties': ev['parties'],
                                 'list': list_index.setdefault(ev['list'], len(list_index)),
                                 'elected': ev['elected'], 'source': ev['source']} for ev in path]})

    names = {}
    if people:
        for pid, fn, ln, dis in _rows('select id, first_name, last_name, disambiguation from elections_person where id = any(:ids)',
                                      ids=[p['person_id'] for p in people]):
            names[pid] = (name_case(f'{fn} {ln}'), dis or '')
    for p in people:
        p['name'], p['label'] = names.get(p['person_id'], ('?', ''))
    people.sort(key=lambda p: (-len(p['moves']), -p['moves'][-1]['year'], p['name']))

    return jsonify({
        'parties': {str(k): {'label': label(k),
                             'name': 'Nezavisne liste i kandidati' if k == INDEPENDENT else
                                     'Nije pronađena u registru stranaka' if k in unregistered else party_case(reg[k].name),
                             'registry_number': reg[k].registry_number if k in reg else None}
                    for k in used},
        'kinds': KIND_LABEL,
        'lists': list(list_index),
        'people': people,
        'roster_years': sorted({r[5] for r in roster}),
    })
