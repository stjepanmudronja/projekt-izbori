"""Sabor chambers and years stated rather than allocated: the Županijski dom
(1993, 1997), the mixed systems of 1992 and 1995, and the three 1990
chambers.
"""

from collections import defaultdict
from flask import jsonify
from webapp.core import app, db, static_cache
from webapp.models import (
    Candidacy,
    CandidateResult,
    Election,
    ElectionRound,
    ElectionType,
    ElectoralDistrict,
    ElectoralList,
    ListResult,
    ParliamentMember,
    Person,
    PollingStation,
    TurnoutData,
)
from webapp.common import round_date_iso, SABOR_1990_CHAMBERS


@app.route('/api/national/zupanijski-dom/<int:year>')
@static_cache
def zupanijski_dom_results(year):
    """Per-county results for the Sabor's upper house.

    Nothing is allocated here. Each county returned exactly 3 members and the
    DIP report names them, so the seats come from stored ParliamentMember rows
    rather than a D'Hondt pass — which is why this is its own endpoint and not
    a year of /api/national/sabor-seats.
    """
    etype = ElectionType.query.filter_by(slug='sabor_zupanijski').first()
    election = (Election.query.filter_by(election_type_id=etype.id, year=year).first()
                if etype else None)
    if not election:
        return jsonify({'error': 'No Županijski dom election for this year'}), 404
    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()

    members_by_district = defaultdict(list)
    for m, prs in (db.session.query(ParliamentMember, Person)
                   .join(Person, Person.id == ParliamentMember.person_id)
                   .filter(ParliamentMember.election_id == election.id).all()):
        members_by_district[m.district_id].append({
            'name': f'{prs.first_name} {prs.last_name}'.strip(),
            'person_id': prs.id,
            'list': m.party,
            # The importer stores "zamjenik: X" here; the label is the UI's job.
            'deputy': (m.note or '').replace('zamjenik:', '').strip(),
        })

    # Seats per list, per district, straight off the roster.
    seats_by_list = defaultdict(lambda: defaultdict(int))
    for did, rows in members_by_district.items():
        for row in rows:
            seats_by_list[did][row['list']] += 1

    counties, totals = [], {'registered': 0, 'cast': 0, 'valid': 0, 'invalid': 0}
    national_seats = defaultdict(int)
    for district in (ElectoralDistrict.query
                     .filter_by(election_id=election.id)
                     .order_by(ElectoralDistrict.number).all()):
        rows = (db.session.query(ElectoralList.id, ElectoralList.name,
                                 db.func.sum(ListResult.votes))
                .join(ListResult, ListResult.electoral_list_id == ElectoralList.id)
                .filter(ElectoralList.district_id == district.id)
                .group_by(ElectoralList.id, ElectoralList.name)
                .all())
        valid = sum(int(r[2] or 0) for r in rows)
        # Scope by station id, resolved first. Joining ListResult here instead
        # would emit one turnout row per list and multiply the electorate by
        # the number of lists that stood.
        station_ids = [sid for (sid,) in db.session.query(ListResult.polling_station_id)
                       .filter(ListResult.electoral_list_id.in_([r[0] for r in rows]))
                       .distinct().all()] if rows else []
        turnout = (db.session.query(
                        db.func.sum(TurnoutData.registered_voters),
                        db.func.sum(TurnoutData.ballots_cast),
                        db.func.sum(TurnoutData.valid_ballots),
                        db.func.sum(TurnoutData.invalid_ballots))
                   .filter(TurnoutData.election_round_id == er.id,
                           TurnoutData.polling_station_id.in_(station_ids))
                   .first()) if station_ids else (0, 0, 0, 0)
        seats = seats_by_list.get(district.id, {})
        for name, n in seats.items():
            national_seats[name] += n
        totals['registered'] += int(turnout[0] or 0)
        totals['cast'] += int(turnout[1] or 0)
        totals['valid'] += int(turnout[2] or 0)
        totals['invalid'] += int(turnout[3] or 0)
        counties.append({
            'number': district.number,
            'name': district.name,
            'registered': int(turnout[0] or 0),
            'cast': int(turnout[1] or 0),
            'valid': int(turnout[2] or 0),
            'invalid': int(turnout[3] or 0),
            'seats': sum(seats.values()),
            'lists': sorted(
                [{'name': r[1], 'votes': int(r[2] or 0),
                  'pct': round(int(r[2] or 0) / valid * 100, 2) if valid else 0,
                  'seats': seats.get(r[1], 0)} for r in rows],
                key=lambda x: -x['votes']),
            'members': sorted(members_by_district.get(district.id, []),
                              key=lambda m: m['name']),
        })

    # Group the national tally the way every other results page does: by the
    # first-named party of the list, so a joint ticket lands under its leader.
    grouped = defaultdict(int)
    for name, n in national_seats.items():
        grouped[name.split(',')[0].split(' i ')[0].strip()] += n

    return jsonify({
        'year': year,
        'date': round_date_iso(er, election) if er else None,
        'elected_seats': sum(national_seats.values()),
        # The constitutional cap on presidential appointees to this chamber,
        # the same for both its terms. How many were actually named is not in
        # the DIP report, which covers the election only — so the UI says
        # "up to", not "plus five".
        'appointed_seats': 5,
        'seats_per_county': 3,
        'totals': totals,
        'parties': sorted(({'name': k, 'seats': v} for k, v in grouped.items()),
                          key=lambda x: (-x['seats'], x['name'])),
        'counties': counties,
    })


SABOR_1995_NATIONAL_DISTRICT = 29
SABOR_1995_DIASPORA_DISTRICT = 30
SABOR_1995_ROMAN = [
    'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
    'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII',
]


def _strip_holder(list_name, person_full_name):
    """A list name with its candidate appended (" - IVAN HORVAT", added where
    one party ran several candidates in a contest) -> the party alone.

    Compared hyphen-insensitively: the list carries the name as the report
    spelled it ("ANTE-JOZO RAMIĆ"), the Person row may have matched an
    existing un-hyphenated spelling ("ANTE JOZO RAMIĆ")."""
    if ' - ' not in list_name:
        return list_name
    head, tail = list_name.rsplit(' - ', 1)
    norm = lambda x: ' '.join(x.replace('-', ' ').upper().split())
    return head if norm(tail) == norm(person_full_name) else list_name


def _mixed_contests(election):
    """Everything the 1992/1995 views need from the database, in one pass.

    Returns (districts by number, candidates by district id, list votes by
    district id, members by district id, winning candidacy ids, round 1).
    Candidates and list votes are summed over each district's pseudo
    station(s); members come from ParliamentMember, which is also how the
    winners of single-member contests are known.
    """
    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()
    districts = {d.number: d for d in
                 ElectoralDistrict.query.filter_by(election_id=election.id).all()}
    cand_rows = (
        db.session.query(Candidacy.id, Person, ElectoralList.name, ElectoralList.district_id,
                         db.func.coalesce(db.func.sum(CandidateResult.votes), 0))
        .join(Person, Person.id == Candidacy.person_id)
        .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
        .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
        .filter(ElectoralList.election_round_id == er.id)
        .group_by(Candidacy.id, Person.id, ElectoralList.name, ElectoralList.district_id)
        .all()
    )
    candidates = defaultdict(list)
    for cid, person, list_name, district_id, votes in cand_rows:
        full = f'{person.first_name} {person.last_name}'.strip()
        party = _strip_holder(list_name, full)
        candidates[district_id].append({'candidacy_id': cid, 'name': full.title(),
                                        'person_id': person.id,
                                        'list': party, 'votes': int(votes)})
    list_rows = (
        db.session.query(ElectoralList.district_id, ElectoralList.name,
                         ListResult.polling_station_id, db.func.sum(ListResult.votes))
        .join(ListResult, ListResult.electoral_list_id == ElectoralList.id)
        .filter(ElectoralList.election_round_id == er.id)
        .group_by(ElectoralList.district_id, ElectoralList.name, ListResult.polling_station_id)
        .all()
    )
    list_votes = defaultdict(lambda: defaultdict(dict))  # district -> station -> list -> votes
    for district_id, name, station_id, votes in list_rows:
        list_votes[district_id][station_id][name] = int(votes or 0)
    members = defaultdict(list)
    winners = set()
    for m, person in (db.session.query(ParliamentMember, Person)
                      .join(Person, Person.id == ParliamentMember.person_id)
                      .filter(ParliamentMember.election_id == election.id).all()):
        members[m.district_id].append({
            'name': f'{person.first_name} {person.last_name}'.strip(),
            'party': m.party, 'minority': m.minority, 'note': m.note or '',
        })
        if m.candidacy_id:
            winners.add(m.candidacy_id)
    return districts, candidates, list_votes, members, winners, er


def _station_turnout(er, station_ids):
    """Summed TurnoutData over the given stations: (registered, cast, invalid, valid)."""
    row = (db.session.query(db.func.sum(TurnoutData.registered_voters),
                            db.func.sum(TurnoutData.ballots_cast),
                            db.func.sum(TurnoutData.invalid_ballots),
                            db.func.sum(TurnoutData.valid_ballots))
           .filter(TurnoutData.election_round_id == er.id,
                   TurnoutData.polling_station_id.in_(list(station_ids)))
           .one())
    return tuple(int(x or 0) for x in row)


def _mixed_race(d, cands, winners, group_of, label=None, extra=None):
    """A single-member contest (or a multi-seat minority unit) from the DB.

    Percentages are shares of all votes cast for candidates — for a one-seat
    contest that is the valid ballots, and for 1995's three-seat Serbian unit
    it is the report's own base (votes, not ballots)."""
    total = sum(c['votes'] for c in cands)
    rows = sorted(
        [{'name': c['name'], 'person_id': c['person_id'],
          'list': c['list'], 'group': group_of(c['list']),
          'votes': c['votes'], 'pct': round(c['votes'] / total * 100, 2) if total else 0,
          'won': c['candidacy_id'] in winners}
         for c in cands],
        key=lambda c: -c['votes'])
    reg, cast, inv = d.registered_voters or 0, d.ballots_cast or 0, d.invalid_ballots or 0
    out = {
        'number': d.number, 'label': label or d.name,
        'registered': reg, 'cast': cast, 'invalid': inv, 'valid': cast - inv,
        'turnout_pct': round(cast / reg * 100, 2) if reg else 0,
        'candidates': rows,
        'winners': [c for c in rows if c['won']],
    }
    out.update(extra or {})
    return out


@app.route('/api/national/sabor-1995')
@static_cache
def sabor_1995_results():
    """The 1995 Zastupnički dom, which four contests elected at once.

    Its own endpoint rather than a year of /api/national/sabor-seats because
    nothing here is allocated: 80 seats came off a countrywide list, 12 off the
    diaspora lists, 28 from single-member plurality districts and 7 from five
    minority units, and the DIP report names every member. Running the generic
    D'Hondt pass over this data would hand each single-member district 14
    seats and invent a parliament that never sat.

    Read entirely from the database. The national list and the diaspora carry
    TurnoutData; the 28 districts and 5 minority units carry their published
    electorate on ElectoralDistrict instead, because those contests count the
    same voters again and must not add to the national turnout.
    """
    etype = ElectionType.query.filter_by(name='Parlamentarni izbori').first()
    election = (Election.query.filter_by(election_type_id=etype.id, year=1995).first()
                if etype else None)
    if not election:
        return jsonify({'error': 'No 1995 sabor election'}), 404
    districts, candidates, list_votes, members, winners, er = _mixed_contests(election)

    # The report writes party names in full on the two proportional ballots
    # ("Hrvatska demokratska zajednica - HDZ") and as bare abbreviations on the
    # district ones ("HDZ"), so fold the short form onto the long one before
    # tallying or HDZ lands in the table twice.
    canon = {}
    for number in (SABOR_1995_NATIONAL_DISTRICT, SABOR_1995_DIASPORA_DISTRICT):
        d = districts.get(number)
        for station in (list_votes.get(d.id, {}) if d else {}).values():
            for name in station:
                first = name.split(',')[0].strip()
                if ' - ' in first:
                    canon[first.rsplit(' - ', 1)[1].strip()] = first

    def group_of(name):
        """First-named party of a list, the grouping key used site-wide."""
        first = name.split(',')[0].strip()
        return canon.get(first, first)

    seat_tally = defaultdict(int)

    def proportional(number, label):
        d = districts.get(number)
        if not d:
            return {'label': label, 'seats': 0, 'lists': [], 'members': [],
                    'members_by_list': []}
        stations = list_votes.get(d.id, {})
        reg, cast, inv, valid = _station_turnout(er, stations.keys())
        votes = defaultdict(int)
        for per_list in stations.values():
            for name, v in per_list.items():
                votes[name] += v
        by_party = defaultdict(list)
        for m in members.get(d.id, []):
            by_party[m['party']].append(m['name'])
        for party, names in by_party.items():
            seat_tally[group_of(party)] += len(names)
        rows = sorted(
            [{'name': name, 'votes': v,
              'pct': round(v / valid * 100, 2) if valid else 0,
              'seats': len(by_party.get(name, [])), 'group': group_of(name)}
             for name, v in votes.items()],
            key=lambda r: -r['votes'])
        return {
            'label': label,
            'seats': sum(len(n) for n in by_party.values()),
            'registered': reg, 'cast': cast, 'valid': valid, 'invalid': inv,
            'lists': rows,
            'members': sorted(m['name'] for m in members.get(d.id, [])),
            'members_by_list': sorted(
                ({'list': party, 'seats': len(names), 'group': group_of(party),
                  'names': sorted(n.title() for n in names)}
                 for party, names in by_party.items()),
                key=lambda g: -g['seats']),
        }

    def race(d, extra=None):
        out = _mixed_race(d, candidates.get(d.id, []), winners, group_of, extra=extra)
        for c in out['winners']:
            seat_tally[c['group']] += 1
        return out

    single = [race(districts[n]) for n in sorted(districts) if 1 <= n <= 28]
    minorities = []
    for n in sorted(districts):
        if n < 121:
            continue
        d = districts[n]
        seats = len(members.get(d.id, []))
        minorities.append(race(d, extra={
            'minority': d.name.split(' - ', 1)[1] if ' - ' in d.name else '',
            'seats': seats,
            # The 5th unit elects three, so a ballot carries up to three votes
            # and the votes exceed the valid ballots.
            'multi_vote': seats > 1}))

    return jsonify({
        'year': 1995,
        'date': round_date_iso(er, election) if er else None,
        'total_seats': sum(len(v) for v in members.values()),
        'national': proportional(SABOR_1995_NATIONAL_DISTRICT, 'Državna lista'),
        'diaspora': proportional(SABOR_1995_DIASPORA_DISTRICT, 'Posebne liste - dijaspora'),
        'districts': single,
        'minorities': minorities,
        'parties': sorted(({'name': k, 'seats': v} for k, v in seat_tally.items()),
                          key=lambda x: (-x['seats'], x['name'])),
    })


@app.route('/api/national/sabor-1992')
@static_cache
def sabor_1992_results():
    """The 1992 Zastupnički dom: 138 members, none of them allocated here.

    60 came off one countrywide list (D'Hondt, 3% threshold — the report's own
    working, not recomputed), 60 from single-member plurality districts, 4 from
    special units for the smaller minorities, and 13 + 1 were declared elected
    from the lists to give the Serb community its census share and the smaller
    minorities their guaranteed five.

    Read from the database: list votes per unit from ListResult, the national
    electorate from TurnoutData, each district's electorate from
    ElectoralDistrict, members from ParliamentMember. The only thing taken
    from the data module is `ABBR_TO_LIST`, the reference table tying a
    district ballot's party abbreviation to that party's national list.
    """
    from elections.importers.sabor_1992_data import LISTS, ABBR_TO_LIST, ROMAN

    etype = ElectionType.query.filter_by(name='Parlamentarni izbori').first()
    election = (Election.query.filter_by(election_type_id=etype.id, year=1992).first()
                if etype else None)
    if not election:
        return jsonify({'error': 'No 1992 sabor election'}), 404
    districts, candidates, list_votes, members, winners, er = _mixed_contests(election)
    nat = districts.get(65)

    def group_of(party):
        """A district ballot's nominator -> the national list it groups with.
        Joint candidacies ("KNS - HSS") group under the first-named party."""
        if party.startswith('NK'):
            return 'Nezavisni kandidat'
        first = party.split(' - ')[0].split()[0]
        idx = ABBR_TO_LIST.get(first)
        return LISTS[idx] if idx is not None else first

    # The national result: one TurnoutData row, list votes summed over units.
    reg, cast, inv, valid = _station_turnout(
        er, [t.polling_station_id for t in
             TurnoutData.query.filter_by(election_round_id=er.id).all()])
    stations = list_votes.get(nat.id, {}) if nat else {}
    national_votes = defaultdict(int)
    for per_list in stations.values():
        for name, v in per_list.items():
            national_votes[name] += v
    list_names = sorted(national_votes, key=lambda n: -national_votes[n])

    nat_members = members.get(nat.id, []) if nat else []
    seats = defaultdict(list)
    serbs = defaultdict(list)
    extra = None
    for m in nat_members:
        if not m['minority']:
            seats[m['party']].append(m['name'].title())
        elif m['note'].startswith('srpska'):
            serbs[m['party']].append(m['name'].title())
        else:
            extra = {'list': m['party'], 'name': m['name'].title(),
                     'community': m['note'].split(' zajednica')[0]}

    seat_tally = defaultdict(int)
    for name in list_names:
        seat_tally[name] += len(seats.get(name, [])) + len(serbs.get(name, []))
    if extra:
        seat_tally[extra['list']] += 1

    lists = [{'name': name, 'votes': national_votes[name],
              'pct': round(national_votes[name] / valid * 100, 2) if valid else 0,
              'seats': len(seats.get(name, [])),
              'minority_seats': len(serbs.get(name, [])) + (1 if extra and extra['list'] == name else 0)}
             for name in list_names]

    # The list vote per unit, one pseudo station each. Station names are the
    # importer's labels ("Državna lista - XII. IJ Bjelovar"), which carry the
    # unit number back out.
    roman_to_int = {r: i for i, r in enumerate(ROMAN, 1)}
    station_names = dict(db.session.query(PollingStation.id, PollingStation.name)
                         .filter(PollingStation.id.in_(list(stations))).all())
    by_unit = {}
    units = []
    for sid in sorted(stations):
        label = station_names.get(sid, '').replace('Državna lista - ', '', 1)
        label = label[:1].upper() + label[1:]
        number = None
        head = label.split(' ', 1)[0].rstrip('.')
        if head in roman_to_int and ' IJ ' in label:
            number = roman_to_int[head]
        elif 'posebna IJ' in label and head.isdigit():
            number = 60 + int(head)
        votes = [stations[sid].get(name, 0) for name in list_names]
        if number:
            by_unit[number] = votes
        units.append({'number': number, 'label': label, 'valid': sum(votes), 'votes': votes})
    units.sort(key=lambda u: (u['number'] is None, u['number'] or 0, u['label']))

    def race(d, extra_fields=None):
        out = _mixed_race(d, candidates.get(d.id, []), winners, group_of, extra=extra_fields)
        for c in out['winners']:
            seat_tally[c['group']] += 1
        # The list ballot in the same unit, so a district can be read against
        # how its voters split on the countrywide list.
        unit_no = d.number if d.number <= 60 else d.number - 60
        if unit_no in by_unit:
            v = by_unit[unit_no]
            total = sum(v)
            out['list_vote'] = sorted(
                [{'name': list_names[i], 'votes': x,
                  'pct': round(x / total * 100, 2) if total else 0}
                 for i, x in enumerate(v)], key=lambda r: -r['votes'])[:4]
        return out

    district_rows = [race(districts[n]) for n in sorted(districts) if 1 <= n <= 60]
    minority_rows = [race(districts[n], {'seats': 1,
                                         'minority': districts[n].name.split(' - ', 1)[-1]})
                     for n in sorted(districts) if n >= 121]

    return jsonify({
        'year': 1992,
        'date': round_date_iso(er, election) if er else None,
        'total_seats': sum(len(v) for v in members.values()),
        'lists': list_names,
        'national': {
            'label': 'Državna lista', 'seats': sum(len(v) for v in seats.values()),
            'registered': reg, 'cast': cast, 'valid': valid, 'invalid': inv,
            'lists': lists,
            'members_by_list': sorted(
                ({'list': name, 'seats': len(names), 'names': sorted(names)}
                 for name, names in seats.items()), key=lambda g: -g['seats']),
        },
        'serb_seats': [{'list': name, 'names': sorted(names)} for name, names in serbs.items()],
        'extra_minority_seat': extra,
        'units': units,
        'districts': district_rows,
        'minorities': minority_rows,
        'parties': sorted(({'name': k, 'seats': v} for k, v in seat_tally.items() if v),
                          key=lambda x: (-x['seats'], x['name'])),
    })


@app.route('/api/national/sabor-dpv/<int:year>')
def sabor_dpv_results(year):
    return sabor_1990_results('dpv', year)


@app.route('/api/national/sabor-1990/<chamber>/<int:year>')
@static_cache
def sabor_1990_results(chamber, year):
    """A 1990 chamber — the Društveno-političko vijeće (80 units), the
    Vijeće općina (115) or the Vijeće udruženog rada (160) — elected in
    single-member units over two rounds.

    Read entirely from the database: candidates and votes from Candidacy /
    CandidateResult, each unit's electorate per round from its TurnoutData row
    (or, for a unit whose voters are counted elsewhere too, from its
    ElectoralDistrict), winners from ParliamentMember. Seats group by the
    winner's first nominating party; a joint candidacy run under the Koalicija
    narodnog sporazuma groups as KNS, the coalition it stood for.
    """
    from elections.importers.sabor_1990_vo_data import PARTIES as VO_PARTIES
    from elections.importers.sabor_1990_vur_data import PARTIES as VUR_PARTIES
    PARTIES = {**VO_PARTIES, **VUR_PARTIES}

    if chamber not in SABOR_1990_CHAMBERS:
        return jsonify({'error': f'Unknown 1990 chamber: {chamber}'}), 404
    slug, _type_name, title = SABOR_1990_CHAMBERS[chamber]
    etype = ElectionType.query.filter_by(slug=slug).first()
    election = (Election.query.filter_by(election_type_id=etype.id, year=year).first()
                if etype else None)
    if not election:
        return jsonify({'error': f'No {title} election for this year'}), 404
    rounds = {er.round_number: er for er in
              ElectionRound.query.filter_by(election_id=election.id).all()}
    round_by_id = {er.id: n for n, er in rounds.items()}
    districts = {d.id: d for d in
                 ElectoralDistrict.query.filter_by(election_id=election.id).all()}

    rows = (
        db.session.query(Candidacy, Person, ElectoralList,
                         CandidateResult.polling_station_id,
                         db.func.coalesce(db.func.sum(CandidateResult.votes), 0))
        .join(Person, Person.id == Candidacy.person_id)
        .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
        .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
        .filter(ElectoralList.election_round_id.in_(round_by_id))
        .group_by(Candidacy.id, Person.id, ElectoralList.id,
                  CandidateResult.polling_station_id)
        .all()
    )
    turnout = {(t.election_round_id, t.polling_station_id): t for t in
               TurnoutData.query.filter(TurnoutData.election_round_id.in_(round_by_id)).all()}
    # A unit whose votes the report lost (VUR 91) has no results to name its
    # station; the importer labels station and district alike.
    station_by_name = {ps.name: ps.id for ps in PollingStation.query.filter(
        PollingStation.id.in_({station for _r, station in turnout})).all()}
    winners = {m.candidacy_id for m in
               ParliamentMember.query.filter_by(election_id=election.id).all()}

    def base_list(list_name, person):
        return _strip_holder(list_name, f'{person.first_name} {person.last_name}'.strip())

    def group_of(label):
        if label.endswith(' - KNS'):
            return PARTIES['KNS']
        first = label.split(', ')[0]
        return PARTIES.get(first, first)

    # (district_id, round) -> {'station': id, 'candidates': [...]}
    contests = defaultdict(lambda: {'station': None, 'candidates': []})
    for cand, person, el, station_id, votes in rows:
        key = (el.district_id, round_by_id[el.election_round_id])
        contests[key]['station'] = contests[key]['station'] or station_id
        label = base_list(el.name, person)
        contests[key]['candidates'].append({
            'name': f'{person.first_name} {person.last_name}'.strip().title(),
            'person_id': person.id,
            'residence': cand.residence or '',
            'list': label, 'group': group_of(label),
            'votes': int(votes) if station_id is not None else None,
            'won': cand.id in winners,
        })

    seat_tally = defaultdict(int)
    totals = {n: {'registered': 0, 'cast': 0, 'invalid': 0, 'valid': 0} for n in rounds}
    units = []
    for d in sorted(districts.values(), key=lambda d: d.number):
        out_rounds = []
        for rn in sorted(rounds):
            c = contests.get((d.id, rn))
            if not c:
                continue
            station = c['station'] or station_by_name.get(d.name)
            t = turnout.get((rounds[rn].id, station))
            votes_known = all(x['votes'] is not None for x in c['candidates'])
            valid = (sum(x['votes'] for x in c['candidates']) if votes_known
                     else (t.valid_ballots if t else 0))
            # No turnout row means the unit's voters are counted in other
            # units too: show its own electorate, keep it out of the totals.
            overlapping = t is None and d.registered_voters is not None
            reg = t.registered_voters if t else (d.registered_voters or 0)
            cast = t.ballots_cast if t else (d.ballots_cast or 0)
            inv = t.invalid_ballots if t else (d.invalid_ballots or 0)
            if not overlapping:
                for k, v in (('registered', reg), ('cast', cast), ('invalid', inv), ('valid', valid)):
                    totals[rn][k] += v
            for x in c['candidates']:
                x['pct'] = (round(x['votes'] / valid * 100, 2) if valid else 0) \
                    if x['votes'] is not None else None
            out_rounds.append({
                'round': rn,
                'date': rounds[rn].date.isoformat() if rounds[rn].date else None,
                'registered': reg, 'cast': cast, 'invalid': inv, 'valid': valid,
                'turnout_pct': round(cast / reg * 100, 2) if reg else None,
                'overlapping': overlapping, 'votes_known': votes_known,
                'candidates': sorted(c['candidates'], key=lambda x: -(x['votes'] or 0)),
            })
        winner = next((x for r in out_rounds for x in r['candidates'] if x['won']), None)
        if winner:
            seat_tally[winner['group']] += 1
        name = d.name.split(' - ', 1)[1] if ' - ' in d.name else d.name
        units.append({'number': d.number, 'name': name,
                      'label': f'{d.number}. izborna jedinica - {name}',
                      'winner': winner, 'decided_in_round': len(out_rounds),
                      'rounds': out_rounds})

    return jsonify({
        'year': year,
        'chamber': title,
        'chamber_key': chamber,
        'chambers': [{'key': k, 'title': t} for k, (_s, _n, t) in SABOR_1990_CHAMBERS.items()],
        'total_seats': len(units),
        # Unit numbers the report skips (VUR: 83, 141, 148, 151).
        'missing_units': sorted(set(range(1, max((u['number'] for u in units), default=0) + 1))
                                - {u['number'] for u in units}),
        'runoffs': sum(1 for u in units if u['decided_in_round'] == 2),
        'round_totals': totals,
        'parties': sorted(({'name': k, 'seats': v} for k, v in seat_tally.items()),
                          key=lambda x: (-x['seats'], x['name'])),
        'units': units,
    })
