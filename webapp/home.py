"""Početna (/api/home): headline counts, highlights, the presidents and
well-known people with their career charts; cached and rebuilt in the
background, plus the start-up warm-up of the slow caches.
"""

import threading
import time
from collections import defaultdict
from flask import jsonify
from elections.importers.name_utils import normalize_person_name
from webapp.core import after_data_change, app, data_cache, data_generation, db
from webapp.models import County, Election, ElectionRound, ElectionType, Municipality, Person
from webapp.common import SABOR_1990_SLUGS, sabor_seat_winner_candidacy_ids
from webapp.people import person_detail
from webapp.parties import _party_links, _party_list_votes


_HOME_CACHE = data_cache({})  # one payload; emptied when the data changes
HOME_EXEC_SLUGS = ('local_mayor', 'local_city_mayor', 'local_county_prefect')
HOME_OFFICE = {'local_mayor': 'Načelnik', 'local_city_mayor': 'Gradonačelnik',
               'local_county_prefect': 'Župan'}


HOME_CACHE_SECONDS = 6 * 3600
_HOME_LOCK = threading.Lock()                 # one rebuild at a time


def _rebuild_home():
    """Recompute the home payload unless another thread is already at it;
    a caller that finds it busy waits for that result instead."""
    if not _HOME_LOCK.acquire(blocking=False):
        with _HOME_LOCK:                      # wait for the running rebuild
            return
    try:
        with app.app_context():
            for _attempt in range(3):         # data changed mid-build: build again
                generation = data_generation()
                payload = (time.time(), _home_highlights())
                if generation == data_generation():
                    _HOME_CACHE['payload'] = payload
                    break
    finally:
        _HOME_LOCK.release()


@app.route('/api/home')
def home_highlights():
    """Cached; once the copy is older than HOME_CACHE_SECONDS it is still
    served while a background thread rebuilds it, so no visitor waits ~7 s.
    Only the very first request after a start (before the warm-up thread is
    done) waits, and then for that thread rather than a second computation."""
    hit = _HOME_CACHE.get('payload')
    if hit:
        if time.time() - hit[0] >= HOME_CACHE_SECONDS and not _HOME_LOCK.locked():
            threading.Thread(target=_rebuild_home, daemon=True).start()
        return jsonify(hit[1])
    _rebuild_home()
    hit = _HOME_CACHE.get('payload')
    if hit is None:                           # the other thread's rebuild failed (or new data)
        hit = _HOME_CACHE['payload'] = (time.time(), _home_highlights())
    return jsonify(hit[1])


def _home_highlights():
    """What the home page shows: headline counts and a handful of rankings
    worth a look, read off the stored results.

    Executive races (načelnik, gradonačelnik, župan; direct since 2009) are
    judged on their deciding round, the last one held: a runoff decides, so
    round 1 of a race that went to one is never a 'win'. A race's district
    number is its municipality's (or for a župan its county's) primary key.
    Careers count elections a person stood in; names are matched across
    years as everywhere else, so a long gap may be two namesakes and is not
    ranked."""
    sql = lambda q, **kw: db.session.execute(db.text(q), kw).fetchall()

    rows = sql("""
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
        group by 1, 2, 3, 4, 5, 6""", slugs=HOME_EXEC_SLUGS)
    rounds = defaultdict(list)
    for year, slug, num, rnd, pid, name, votes in rows:
        rounds[(year, slug, num, rnd)].append((int(votes or 0), pid, name))
    deciding = {}
    for (year, slug, num, rnd), cands in rounds.items():
        if (year, slug, num) not in deciding or rnd > deciding[(year, slug, num)][0]:
            deciding[(year, slug, num)] = (rnd, sorted(cands, key=lambda c: -c[0]))

    munis = {m.id: m for m in Municipality.query.filter(Municipality.type.in_(('grad', 'općina')))}
    counties = {c.id: c.name for c in County.query}

    def place(slug, num):
        if slug == 'local_county_prefect':
            return {'name': counties.get(num), 'place_id': None}
        m = munis.get(num)
        return {'name': m.name if m else None, 'place_id': m.id if m else None}

    def person(c):
        return {'name': c[2], 'person_id': c[1], 'votes': c[0]}

    races = []
    for (year, slug, num), (rnd, cands) in deciding.items():
        total = sum(c[0] for c in cands)
        if not total:
            continue
        races.append({'year': year, 'office': HOME_OFFICE[slug], 'round': rnd, **place(slug, num),
                      'candidates': len(cands), 'total': total,
                      'first': person(cands[0]), 'second': person(cands[1]) if len(cands) > 1 else None,
                      'share': round(cands[0][0] / total * 100, 1),
                      '_key': (slug, num), '_tie': len(cands) > 1 and cands[0][0] == cands[1][0]})
    contested = [r for r in races if r['second']]
    closest = sorted(contested, key=lambda r: (r['first']['votes'] - r['second']['votes'], -r['total']))[:12]
    for r in closest:
        r['margin'] = r['first']['votes'] - r['second']['votes']
        r['tie'] = r['_tie']
    landslides = sorted(contested, key=lambda r: -r['share'])[:12]
    unopposed = defaultdict(int)
    for r in races:
        if r['candidates'] == 1:
            unopposed[r['year']] += 1

    # Unbroken runs: won every direct election from 2009 to the latest one.
    exec_years = sorted({r['year'] for r in races})
    wins = defaultdict(dict)                       # (slug, num, person) -> {year: race}
    for r in races:
        if not r['_tie']:
            wins[(*r['_key'], r['first']['person_id'])][r['year']] = r
    streaks = []
    for key, by_year in wins.items():
        run = 0
        for y in reversed(exec_years):
            if y not in by_year:
                break
            run += 1
        if run == len(exec_years):
            latest = by_year[exec_years[-1]]
            streaks.append({'name': latest['first']['name'], 'person_id': latest['first']['person_id'],
                            'office': latest['office'], 'place': latest['name'], 'place_id': latest['place_id'],
                            'wins': run, 'since': exec_years[0], 'share': latest['share'],
                            'votes': latest['first']['votes']})
    streaks.sort(key=lambda s: -s['votes'])
    for r in races:
        r.pop('_key', None)
        r.pop('_tie', None)

    careers = sql("""
        select p.id, p.first_name || ' ' || p.last_name, count(distinct e.id), min(e.year), max(e.year),
               count(distinct case when et.slug like 'local%%' then 'local'
                                   when et.slug like 'sabor%%' then 'sabor' else et.slug end)
        from elections_person p
        join elections_candidacy c on c.person_id = p.id
        join elections_electorallist el on el.id = c.electoral_list_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        group by p.id order by 3 desc, 6 desc, 2 limit 12""")

    def top_preferences(slug):
        latest = sql("""select max(e.year) from elections_election e
                        join elections_electiontype et on et.id = e.election_type_id where et.slug = :s""", s=slug)[0][0]
        rows = sql("""
            select p.id, p.first_name || ' ' || p.last_name, el.name, sum(cr.votes) v
            from elections_candidateresult cr
            join elections_candidacy c on c.id = cr.candidacy_id
            join elections_person p on p.id = c.person_id
            join elections_electorallist el on el.id = c.electoral_list_id
            join elections_electionround er on er.id = el.election_round_id
            join elections_election e on e.id = er.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug = :s and e.year = :y
            group by 1, 2, 3 order by v desc limit 10""", s=slug, y=latest)
        def short(lst):     # first party of the list, as its abbreviation where given
            first = (lst or '').split('\n', 1)[0].split(',', 1)[0].strip()
            return first.rsplit(' - ', 1)[-1] if ' - ' in first else first
        return {'year': latest, 'items': [{'person_id': pid, 'name': name, 'list': short(lst),
                                           'votes': int(v)} for pid, name, lst, v in rows]}

    # Turnout records: the latest local election's councils, towns of 300+ voters.
    local_year = max(exec_years) if exec_years else None
    turnout = sql("""
        select m.id, m.name, sum(t.registered_voters) reg, sum(t.ballots_cast) cast_
        from elections_turnoutdata t
        join elections_pollingstation ps on ps.id = t.polling_station_id
        join elections_municipality m on m.id = ps.municipality_id
        join elections_electionround er on er.id = t.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug in ('local_municipal_council', 'local_city_council') and e.year = :y
              and er.round_number = 1 and m.type in ('grad', 'općina')
        group by 1, 2 having sum(t.registered_voters) >= 300""", y=local_year)
    turnout = sorted(({'place_id': mid, 'name': name, 'registered': int(reg), 'cast': int(c),
                       'pct': round(int(c) / int(reg) * 100, 1)} for mid, name, reg, c in turnout if reg),
                     key=lambda t: -t['pct'])

    presidential = _home_presidential(sql)
    public_figures = _home_public_figures()

    counts = sql("""select (select count(*) from elections_person),
                           (select count(*) from elections_election),
                           (select min(year) from elections_election), (select max(year) from elections_election),
                           (select count(*) from elections_municipality where type in ('grad', 'općina')),
                           (select count(*) from elections_candidacy)""")[0]
    return {
        'stats': {'persons': counts[0], 'elections': counts[1], 'first_year': counts[2],
                  'last_year': counts[3], 'places': counts[4], 'candidacies': counts[5]},
        'closest': closest,
        'landslides': landslides,
        'streaks': {'since': exec_years[0] if exec_years else None, 'count': len(streaks),
                    'items': streaks[:15]},
        'unopposed': [{'year': y, 'count': unopposed[y]} for y in exec_years],
        'careers': [{'person_id': pid, 'name': name, 'elections': n, 'from': a, 'to': b, 'kinds': k}
                    for pid, name, n, a, b, k in careers],
        'preferences': {'sabor': top_preferences('sabor'), 'eu': top_preferences('eu_parliament')},
        'turnout': {'year': local_year, 'top': turnout[:10]},
        'presidential': presidential,
        'public_figures': public_figures,
    }


def _home_presidential(sql):
    """Every presidential election — who won, in which round and by how
    much — and the records across them. The deciding round is the last one
    held (1992 and 1997 were won outright in round 1). `year` is the
    election's, which for a runoff in January is the year before its date."""
    rows = sql("""
        select e.year, er.round_number, er.date, p.id, p.first_name || ' ' || p.last_name, sum(lr.votes)
        from elections_listresult lr
        join elections_electorallist el on el.id = lr.electoral_list_id
        join elections_candidacy c on c.electoral_list_id = el.id
        join elections_person p on p.id = c.person_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug = 'presidential'
        group by 1, 2, 3, 4, 5""")
    turnout = {(y, r): (int(reg), int(cast)) for y, r, reg, cast in sql("""
        select e.year, er.round_number, sum(t.registered_voters), sum(t.ballots_cast)
        from elections_turnoutdata t
        join elections_electionround er on er.id = t.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug = 'presidential' group by 1, 2""") if reg}
    rounds = defaultdict(list)
    dates = {}
    for year, rnd, date, pid, name, votes in rows:
        rounds[(year, rnd)].append({'person_id': pid, 'name': name, 'votes': int(votes or 0)})
        dates[(year, rnd)] = date.isoformat() if date else None
    for cands in rounds.values():
        total = sum(c['votes'] for c in cands) or 1
        cands.sort(key=lambda c: -c['votes'])
        for c in cands:
            c['share'] = round(c['votes'] / total * 100, 2)

    def pct(year, rnd):
        reg, cast = turnout.get((year, rnd), (0, 0))
        return round(cast / reg * 100, 2) if reg else None

    elections, seen_winners = [], {}
    for year in sorted({y for y, _ in rounds}):
        last = max(r for y, r in rounds if y == year)
        decided, first = rounds[(year, last)], rounds[(year, 1)]
        winner = decided[0]
        term = seen_winners.get(winner['person_id'], 0) + 1
        seen_winners[winner['person_id']] = term
        elections.append({
            'year': year, 'date': dates[(year, last)], 'rounds': last, 'term': term,
            'winner': winner, 'runner_up': decided[1] if len(decided) > 1 else None,
            'first_round': {'winner': first[0], 'candidates': len(first)},
            'turnout': pct(year, last),
        })

    runoffs = [e for e in elections if e['rounds'] > 1]
    all_rounds = [(y, r) for (y, r) in rounds if pct(y, r) is not None]
    top_votes = max(((y, r, c) for (y, r), cs in rounds.items() for c in cs[:1]), key=lambda x: x[2]['votes'])
    records = []
    if runoffs:
        close = min(runoffs, key=lambda e: e['winner']['share'])
        margin = f"{close['winner']['votes'] - close['runner_up']['votes']:,}".replace(',', '.')
        records.append({'kind': 'Najtješnji drugi krug', 'year': close['year'],
                        'value': f"{close['winner']['share']:.2f} : {close['runner_up']['share']:.2f}".replace('.', ','),
                        'name': close['winner']['name'], 'person_id': close['winner']['person_id'],
                        'text': f"protiv: {close['runner_up']['name']}, razlika {margin} glasova"})
    big = max(elections, key=lambda e: e['winner']['share'])
    records.append({'kind': 'Najuvjerljivija pobjeda', 'year': big['year'],
                    'value': f"{big['winner']['share']:.2f} %".replace('.', ','),
                    'name': big['winner']['name'], 'person_id': big['winner']['person_id'],
                    'text': f"{big['rounds']}. krug izbora {big['year']}."})
    if all_rounds:
        hi = max(all_rounds, key=lambda k: pct(*k))
        lo = min(all_rounds, key=lambda k: pct(*k))
        records.append({'kind': 'Najveća izlaznost', 'year': hi[0], 'value': f"{pct(*hi):.2f} %".replace('.', ','),
                        'text': f"{hi[1]}. krug izbora {hi[0]}."})
        records.append({'kind': 'Najmanja izlaznost', 'year': lo[0], 'value': f"{pct(*lo):.2f} %".replace('.', ','),
                        'text': f"{lo[1]}. krug izbora {lo[0]}."})
    most = max(elections, key=lambda e: e['first_round']['candidates'])
    records.append({'kind': 'Najviše kandidata', 'year': most['year'], 'value': str(most['first_round']['candidates']),
                    'text': f"u 1. krugu izbora {most['year']}."})
    records.append({'kind': 'Najviše glasova u jednom krugu', 'year': top_votes[0],
                    'value': f"{top_votes[2]['votes']:,}".replace(',', '.'),
                    'name': top_votes[2]['name'], 'person_id': top_votes[2]['person_id'],
                    'text': f"{top_votes[1]}. krug izbora {top_votes[0]}."})
    return {'elections': elections[::-1], 'records': records,
            'careers': {pid: _home_career(pid) for pid in seen_winners}}


# Well-known people from outside politics who stood in an election, for the
# home page: (stored name, what they are known for, name to show). Each was
# checked against their candidacies; a namesake on the same row is split off
# in `split_persons` first (Sandra Perković's 1997 Ližnjan ward). Matched to
# the unlabelled Person of the name. Not here: namesakes of the famous (the
# 2020 diaspora "Marko Perković", the 2015 "Zvonimir Boban", Knin's "Dario
# Šimić"). Zlatko Vitez was considered and left out by the data's owner.
HOME_PUBLIC_FIGURES = [
    ('MIROSLAV ŠKORO', 'glazbenik', None),
    ('MIROSLAV BLAŽEVIĆ', 'nogometni trener', None),
    ('BORIS MIKŠIĆ', 'poduzetnik', None),
    ('MILAN KEKIN', 'glazbenik (Hladno pivo); na listi kao Milan Kekin', 'MILE KEKIN'),
    ('SINIŠA VUCO', 'pjevač', None),
    ('BORIS DVORNIK', 'glumac', None),
    ('ŽELJKO PERVAN', 'glumac i komičar', None),
    ('HLOVERKA NOVAK SRZIĆ', 'televizijska voditeljica', None),
    ('SANDRA PERKOVIĆ', 'bacačica diska', None),
]


def _home_public_figures():
    """HOME_PUBLIC_FIGURES with each one's career series, the most recently
    standing first. A name no longer in the data is skipped."""
    out = []
    for stored, known_as, shown in HOME_PUBLIC_FIGURES:
        person = Person.query.filter_by(normalized_name=normalize_person_name(stored), disambiguation='').first()
        if not person:
            continue
        career = _home_career(person.id)
        if career:
            out.append({'person_id': person.id, 'name': shown or f'{person.first_name} {person.last_name}',
                        'known_as': known_as, 'career': career})
    out.sort(key=lambda f: -max(c['year'] for c in f['career']))
    return out


def _home_career(person_id):
    """A president's vote share in every election they stood in, oldest
    first — the politician page's chart, in miniature, for the home cards.
    Read through `person_detail`, so both charts plot the same points."""
    results = sorted(person_detail(person_id).get_json()['results'],
                     key=lambda r: (r['year'], r['date'] or '', r['round']))
    return [{'type': r['election_type'], 'year': r['year'], 'date': r['date'], 'round': r['round'],
             'district': r['district'], 'share': r['vote_share'] or 0, 'votes': r['candidate_votes'],
             'valid': r['total_valid_ballots'] or 0, 'lokalni_kind': r['lokalni_kind'],
             'county_id': r['county_id'], 'municipality_id': r['municipality_id']}
            for r in results if (r.get('candidate_votes') or 0) > 0]


def _warm_home_cache():
    """At server start, in the background: the home page's highlights (~7 s),
    then the caches the first visitors would otherwise fill — every Sabor
    round's seat winners (politician pages) and the party register links
    (Stranke, Snaga stranaka)."""
    try:
        _rebuild_home()
    except Exception as exc:                  # the endpoint retries on demand
        app.logger.warning('home highlights not precomputed: %s', exc)
    with app.app_context():
        try:
            rounds = (db.session.query(ElectionRound.id)
                      .join(Election, ElectionRound.election_id == Election.id)
                      .join(ElectionType, Election.election_type_id == ElectionType.id)
                      .filter(ElectionType.slug.in_(['sabor', *SABOR_1990_SLUGS])).all())
            for (er_id,) in rounds:
                sabor_seat_winner_candidacy_ids(er_id)
            _party_links()
            _party_list_votes()
        except Exception as exc:
            app.logger.warning('caches not precomputed: %s', exc)


@after_data_change
def _rewarm_after_import():
    """New data: fill the same caches again in the background, so the first
    visitor after an import does not wait for them."""
    threading.Thread(target=_warm_home_cache, daemon=True).start()
