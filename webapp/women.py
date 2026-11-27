"""Žene u politici (Analitika): the share of women among candidates and
among those elected, per election and, for Sabor and EU lists, per party.

Gender is not in the data; it is read off the first name (`name_gender`).
Croatian makes that nearly mechanical — women's names end in -a — once the
men's names ending in -a (Luka, Nikola, Ivica…) and the women's names that do
not (Ines, Nives, Karmen…) are listed. Names that are used for both, or that
are not names (an initial), are "unknown" and are counted as such, never
guessed; the endpoint returns them so the page can say how many there are.

What each kind counts:
- Sabor: candidates where every list's candidates are published (2015 on,
  and the 1990 chambers, all single-member races), elected from the roster
  (ParliamentMember: 1990, 1992, 1995, 2003, 2007, 2011) or, from 2015, the
  seat winners computed from the votes. 2000 has no names, so it is left out.
- Europski parlament: every list candidate; elected = ElectedMandate.
- Predsjednički: candidates; elected = first in the last round.
- Gradonačelnici, načelnici i župani (2009 on): candidates; elected = first
  in the race's deciding (last) round, as on Početna.
People are counted once per election, however many rounds or lists they ran on.
"""
from collections import defaultdict

from flask import jsonify

from webapp.common import sabor_seat_winner_candidacy_ids
from webapp.core import app, db, static_cache

# Men's names ending in -a. Diminutives in -ica are listed one by one: most
# (Katica, Marica, Antica) are women's.
MALE_A = {
    'IVICA', 'NIKOLA', 'LUKA', 'ANDRIJA', 'ILIJA', 'MATIJA', 'SINIŠA', 'SINISA', 'JURICA', 'NIKICA',
    'NIKŠA', 'NIKSA', 'NEBOJŠA', 'NEBOJSA', 'PERICA', 'JAKŠA', 'JAKSA', 'TOMICA', 'TOMA', 'GRGA',
    'TADIJA', 'BORNA', 'NEMANJA', 'KUZMA', 'SAVA', 'JOŽA', 'ALJOŠA', 'ALEKSA', 'DOBRIŠA', 'ĐUKA',
    'ANTIŠA', 'ATILA', 'KOLJA', 'ALIJA', 'JURA', 'MIRZA', 'STEVICA', 'ĐURICA', 'DRAGIŠA', 'RELJA',
    'MUSTAFA', 'JOVICA', 'PERA', 'TUNA', 'RUDIKA', 'JAKICA', 'LUCA', 'MATA', 'ŠIMA', 'BARIŠA',
    'MIHA', 'MIŠA', 'KOSTA', 'JOSA', 'BOŽA', 'MILIŠA',
}
# Women's names not ending in -a.
FEMALE_OTHER = {
    'INES', 'NIVES', 'DOLORES', 'IRIS', 'KARMEN', 'INGRID', 'DORIS', 'MERI', 'IRENE', 'MELANI',
    'NANSI', 'ESTER', 'KETI', 'NENSI', 'ANET', 'FANI', 'ANI', 'ALIS', 'MIRIAM', 'MIRJAM', 'NATHALIE',
    'RUT', 'RUTH', 'EDIT', 'ELIZABET', 'NIKOL', 'MARGIT', 'BEATRIS', 'KRISTIN', 'ROZMARI', 'DŽENI',
    'LJUBOV', 'ANNE', 'MARIE', 'LILI', 'DIANE', 'KATE', 'NOEMI', 'ROZI', 'IVET',
}
# Used for both, or not certain enough to call.
AMBIGUOUS = {'SAŠA', 'SASA', 'VANJA', 'ANDREA', 'BELA', 'ŠIMICA', 'PETRICA', 'DANI'}


def name_gender(first_name):
    """'F', 'M' or None from a first name ("ANA-MARIJA", "Ivan", "MARIJA ANA")."""
    word = (first_name or '').strip().upper().split(' ')[0].split('-')[0]
    word = ''.join(ch for ch in word if ch.isalpha())
    if len(word) < 2 or word in AMBIGUOUS:
        return None
    if word in MALE_A:
        return 'M'
    if word in FEMALE_OTHER:
        return 'F'
    return 'F' if word.endswith('A') else 'M'


WOMEN_KINDS = [
    {'key': 'sabor', 'label': 'Sabor', 'slugs': ('sabor', 'sabor_dpv', 'sabor_vo', 'sabor_vur')},
    {'key': 'eu', 'label': 'Europski parlament', 'slugs': ('eu_parliament',)},
    {'key': 'lokalni', 'label': 'Gradonačelnici, načelnici i župani', 'slugs': ('local_mayor', 'local_city_mayor', 'local_county_prefect')},
    {'key': 'predsjednicki', 'label': 'Predsjednički izbori', 'slugs': ('presidential',)},
]
# Sabor years whose candidates are all published (the rest name only some).
SABOR_FULL_CANDIDATES = lambda slug, year: slug != 'sabor' or year >= 2015


def _rows(q, **kw):
    return db.session.execute(db.text(q), kw).fetchall()


def _count(person_ids, gender):
    out = {'f': 0, 'm': 0, 'u': 0}
    for pid in person_ids:
        out[{'F': 'f', 'M': 'm'}.get(gender.get(pid), 'u')] += 1
    return out


EXEC_KIND = {'local_mayor': 'opcina', 'local_city_mayor': 'grad', 'local_county_prefect': 'zupanija'}
# Places on a list: the leader, the next two, the rest.
POSITION_BUCKETS = [('1', 1, 1), ('2-3', 2, 3), ('4+', 4, 99)]
HOLDER_BODY = {'local_municipal_council': 'vijeca', 'local_city_council': 'vijeca', 'local_county_assembly': 'skupstine'}


def _depth(cand_by_id, position, elected_cands, race_cands, race_winner, holders, gender):
    """The finer cuts: executives by office and by county, women by place on
    Sabor and EU lists, and the women who led council and assembly lists
    2001-2009 (the only local lists whose candidates are named are the
    leaders: DIP's reports print the "nositelj liste", not the rest)."""
    from webapp.models import County, Municipality
    muni_county = {m.id: m.county_id for m in Municipality.query}
    code = {c.id: c.code for c in County.query}

    def county_of(slug, dnum):
        c = code.get(dnum if slug == 'local_county_prefect' else muni_county.get(dnum))
        return c if c and '01' <= c <= '21' else None

    # Executive races by office and by county: who stood, who won, per election.
    office = defaultdict(lambda: {'cand': set(), 'won': set()})
    county = defaultdict(lambda: {'cand': set(), 'won': set()})
    for race, pids in race_cands.items():
        slug, year, dnum = race
        if slug not in EXEC_KIND:
            continue
        won = race_winner.get(race)
        buckets = [office[(year, EXEC_KIND[slug])]]
        cc = county_of(slug, dnum)
        if cc:
            buckets.append(county[(year, cc)])
        for b in buckets:
            b['cand'] |= pids
            if won:
                b['won'].add(won)
    by_office = defaultdict(dict)
    for (year, kind), b in office.items():
        by_office[year][kind] = {'candidates': _count(b['cand'], gender), 'elected': _count(b['won'], gender)}
    by_county = defaultdict(dict)
    for (year, cc), b in county.items():
        by_county[year][cc] = {'candidates': _count(b['cand'], gender), 'elected': _count(b['won'], gender)}

    # Place on the list (Sabor from 2015 and EU; Sabor's minority seats, one
    # candidate a list, are left out).
    pos = defaultdict(lambda: defaultdict(lambda: {'cand': set(), 'won': set()}))
    for cid, (key, pid, _name, dnum, slug) in cand_by_id.items():
        if not ((slug == 'sabor' and key[1] >= 2015 and not (dnum and dnum >= 121)) or slug == 'eu_parliament'):
            continue
        p = position.get(cid)
        b = next((label for label, lo, hi in POSITION_BUCKETS if p and lo <= p <= hi), None)
        if not b:
            continue
        pos[f'{key[0]}-{key[1]}'][b]['cand'].add(pid)
        if cid in elected_cands:
            pos[f'{key[0]}-{key[1]}'][b]['won'].add(pid)
    by_position = {ek: [{'bucket': label, 'candidates': _count(g[label]['cand'], gender),
                         'elected': _count(g[label]['won'], gender)} for label, _, _ in POSITION_BUCKETS]
                   for ek, g in pos.items()}

    # List leaders 2001-2009: all of them, and those whose list came first there.
    best = defaultdict(int)
    for slug, year, pid, muni, list_id, votes in holders:
        k = (HOLDER_BODY[slug], year, muni)
        best[k] = max(best[k], votes)
    lead = defaultdict(lambda: {'all': set(), 'first': set()})
    for slug, year, pid, muni, list_id, votes in holders:
        if not pid:
            continue
        body = HOLDER_BODY[slug]
        # A person counts once per body and year, wherever they led a list.
        lead[(year, body)]['all'].add(pid)
        if votes and votes == best[(body, year, muni)]:
            lead[(year, body)]['first'].add(pid)
    leaders = [{'year': y, 'body': body, 'all': _count(b['all'], gender), 'first': _count(b['first'], gender)}
               for (y, body), b in sorted(lead.items())]
    return {'by_office': by_office, 'by_county': by_county, 'by_position': by_position, 'leaders': leaders,
            'counties': {c.code: c.name for c in County.query if '01' <= (c.code or '') <= '21'}}


@app.route('/api/analytics/women')
@static_cache
def women_in_politics():
    slugs = tuple(s for k in WOMEN_KINDS for s in k['slugs'])
    kind_of = {s: k['key'] for k in WOMEN_KINDS for s in k['slugs']}

    # Every candidacy of these elections: who, in which election, round, list and district.
    cand = _rows("""
        select et.slug, e.id, e.year, er.id, er.round_number, c.id, c.person_id, el.id, el.name, ed.number, c.position_on_list
        from elections_candidacy c
        join elections_electorallist el on el.id = c.electoral_list_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        left join elections_electoraldistrict ed on ed.id = el.district_id
        where et.slug in :slugs""", slugs=slugs)

    # An election is (kind, year): the three 1990 chambers are one Sabor.
    candidates = defaultdict(set)
    cand_by_id = {}
    rounds_of = defaultdict(set)                 # (kind, year) -> election round ids
    position = {}
    for slug, eid, year, er_id, rnd, cid, pid, list_id, list_name, dnum, pos in cand:
        key = (kind_of[slug], year)
        cand_by_id[cid] = (key, pid, list_name, dnum, slug)
        position[cid] = pos
        rounds_of[(slug, year)].add(er_id)
        if SABOR_FULL_CANDIDATES(slug, year):
            candidates[key].add(pid)

    elected = defaultdict(set)
    elected_cands = set()                        # candidacy ids that won (for the party breakdown)
    # Rosters (Sabor 1990-2011).
    for slug, year, pid, cid in _rows("""
            select et.slug, e.year, pm.person_id, pm.candidacy_id from elections_parliamentmember pm
            join elections_election e on e.id = pm.election_id
            join elections_electiontype et on et.id = e.election_type_id
            where et.slug in ('sabor', 'sabor_dpv', 'sabor_vo', 'sabor_vur')"""):
        elected[('sabor', year)].add(pid)
        if cid:
            elected_cands.add(cid)
    roster_years = {k[1] for k in elected}
    # Sabor from 2015: the seat winners off the votes.
    for (slug, year), er_ids in rounds_of.items():
        if slug == 'sabor' and year >= 2015 and year not in roster_years:
            for er_id in er_ids:
                for cid in sabor_seat_winner_candidacy_ids(er_id):
                    if cid in cand_by_id:
                        elected[('sabor', year)].add(cand_by_id[cid][1])
                        elected_cands.add(cid)
    # EU: the stored mandates.
    for (cid,) in _rows("select candidacy_id from elections_electedmandate"):
        if cid in cand_by_id:
            key, pid = cand_by_id[cid][:2]
            elected[key].add(pid)
            elected_cands.add(cid)
    # Head-to-head races: first in the deciding (last) round of each race.
    votes = _rows("""
        select et.slug, e.year, ed.number, er.round_number, c.person_id, sum(lr.votes)
        from elections_listresult lr
        join elections_electorallist el on el.id = lr.electoral_list_id
        left join elections_electoraldistrict ed on ed.id = el.district_id
        join elections_candidacy c on c.electoral_list_id = el.id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        where et.slug in ('presidential', 'local_mayor', 'local_city_mayor', 'local_county_prefect')
        group by 1, 2, 3, 4, 5""")
    races = defaultdict(lambda: (0, []))
    race_cands = defaultdict(set)                # executive race -> everyone who stood in any round
    for slug, year, dnum, rnd, pid, v in votes:
        race = (slug, year, dnum if slug != 'presidential' else None)
        race_cands[race].add(pid)
        last, cands = races[race]
        if rnd > last:
            races[race] = (rnd, [(int(v or 0), pid)])
        elif rnd == last:
            cands.append((int(v or 0), pid))
    race_winner = {}
    for race, (_, cands) in races.items():
        if cands and max(cands)[0] > 0:
            elected[(kind_of[race[0]], race[1])].add(max(cands)[1])
            race_winner[race] = max(cands)[1]

    holders = _rows("""
        select et.slug, e.year, lh.person_id, lh.municipality_id, lh.electoral_list_id,
               coalesce(sum(lr.votes) filter (where ps.municipality_id = lh.municipality_id), 0)
        from elections_listholder lh
        join elections_electorallist el on el.id = lh.electoral_list_id
        join elections_electionround er on er.id = el.election_round_id
        join elections_election e on e.id = er.election_id
        join elections_electiontype et on et.id = e.election_type_id
        left join elections_listresult lr on lr.electoral_list_id = el.id
        left join elections_pollingstation ps on ps.id = lr.polling_station_id
        group by 1, 2, 3, 4, 5""")

    # Gender of everyone counted, roster members with no candidacy and list leaders included.
    persons = ({r[6] for r in cand} | {pid for ps in elected.values() for pid in ps}
               | {h[2] for h in holders if h[2]})
    gender, first = {}, {}
    for pid, fn in _rows("select id, first_name from elections_person where id = any(:ids)", ids=list(persons)):
        gender[pid] = name_gender(fn)
        first[pid] = (fn or '').strip().upper().split(' ')[0]

    elections = []
    for k in WOMEN_KINDS:
        years = sorted({y for (kk, y) in set(candidates) | set(elected) if kk == k['key']})
        for y in years:
            c, e = candidates.get((k['key'], y)), elected.get((k['key'], y))
            elections.append({'kind': k['key'], 'year': y,
                              'candidates': _count(c, gender) if c else None,
                              'elected': _count(e, gender) if e else None})

    # Per party (lists only: Sabor from 2015, EU), by the list's first-named party.
    def party_of(list_name, dnum, slug):
        if slug == 'sabor' and dnum and dnum >= 121:
            return 'NACIONALNE MANJINE'
        return list_name.split('\n', 1)[0].split(',', 1)[0].strip()

    by_party = defaultdict(lambda: defaultdict(lambda: {'cand': set(), 'won': set()}))
    for cid, (key, pid, list_name, dnum, slug) in cand_by_id.items():
        if (slug == 'sabor' and key[1] >= 2015) or slug == 'eu_parliament':
            row = by_party[f'{key[0]}-{key[1]}'][party_of(list_name, dnum, slug)]
            row['cand'].add(pid)
            if cid in elected_cands:
                row['won'].add(pid)
    parties = {}
    for ek, groups in by_party.items():
        rows = [{'party': name, 'candidates': _count(g['cand'], gender), 'elected': _count(g['won'], gender)}
                for name, g in groups.items() if len(g['cand']) >= 10 or g['won']]
        parties[ek] = sorted(rows, key=lambda r: (-sum(r['elected'].values()), -sum(r['candidates'].values())))

    depth = _depth(cand_by_id, position, elected_cands, race_cands, race_winner, holders, gender)

    unknown = defaultdict(int)
    for pid in persons:
        if gender.get(pid) is None:
            unknown[first.get(pid) or '?'] += 1
    return jsonify({
        'kinds': [{'key': k['key'], 'label': k['label']} for k in WOMEN_KINDS],
        'elections': elections,
        'parties': parties,
        **depth,
        'people': {'total': len(persons), 'unknown': sum(unknown.values()),
                   'unknown_names': sorted(unknown.items(), key=lambda x: -x[1])[:30]},
    })
