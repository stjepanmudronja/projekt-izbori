"""National results per election type and year, and the EU Parliament seats.
"""

from flask import jsonify, request
from webapp.core import app, db
from webapp.models import (
    Candidacy,
    CandidateResult,
    County,
    Election,
    ElectionRound,
    ElectionType,
    ElectoralDistrict,
    ElectoralList,
    ListResult,
    Municipality,
    Person,
    PollingStation,
    TurnoutData,
)
from webapp.common import NUMBER_ONLY_ELECTIONS, round_date_iso
from webapp.places import station_place_ids


@app.route('/api/national/election-types')
def national_election_types():
    """Return available election categories with years."""
    # Group election types into 4 categories
    categories = {
        'predsjednicki': {
            'label': 'Predsjednički izbori',
            'types': ['Predsjednički izbori'],
        },
        'eu': {
            'label': 'EU parlamentarni izbori',
            'types': ['Izbori za Europski parlament'],
        },
        'sabor': {
            'label': 'Parlamentarni izbori (Sabor)',
            'types': ['Parlamentarni izbori'],
        },
        'lokalni': {
            'label': 'Lokalni izbori',
            'types': [
                'Župan', 'Županijska skupština', 'Gradonačelnik',
                'Gradsko vijeće', 'Načelnik', 'Općinsko vijeće',
                'Zamjenik župana', 'Zamjenik načelnika', 'Zamjenik gradonačelnika',
                'Local',
            ],
        },
    }

    result = []
    for key, cat in categories.items():
        years = (
            db.session.query(Election.year)
            .join(ElectionType, Election.election_type_id == ElectionType.id)
            .filter(ElectionType.name.in_(cat['types']))
            .distinct()
            .order_by(Election.year.desc())
            .all()
        )
        if years:
            result.append({
                'key': key,
                'label': cat['label'],
                'years': [y[0] for y in years],
            })
    return jsonify(result)


@app.route('/api/national/results/<category>/<int:year>')
def national_results(category, year):
    """Return aggregated results for a category and year.

    Optional scope query params:
      - station_id: narrow to a single polling station
      - municipality_id: narrow to all stations in this muni
      - county_id: narrow to all stations in this county
    With no scope params, returns Croatia-wide totals (the default).
    """
    type_map = {
        'predsjednicki': ['Predsjednički izbori'],
        'eu': ['Izbori za Europski parlament'],
        'sabor': ['Parlamentarni izbori'],
        'lokalni': [
            'Župan', 'Županijska skupština', 'Gradonačelnik',
            'Gradsko vijeće', 'Načelnik', 'Općinsko vijeće',
            'Zamjenik župana', 'Zamjenik načelnika', 'Zamjenik gradonačelnika',
            'Local',
        ],
    }

    type_names = type_map.get(category, [])
    if not type_names:
        return jsonify({'error': 'Unknown category'}), 400

    station_id = request.args.get('station_id', type=int)
    muni_id = request.args.get('municipality_id', type=int)
    county_id = request.args.get('county_id', type=int)
    district_id = request.args.get('district_id', type=int)  # sabor only

    # Build a station-id subquery for the chosen scope (or None for national).
    scope_station_ids = None
    scope_label = 'Republika Hrvatska'
    if station_id:
        ps = PollingStation.query.get_or_404(station_id)
        scope_station_ids = db.session.query(PollingStation.id).filter(
            PollingStation.id.in_(station_place_ids(ps)))
        ps = PollingStation.query.get(station_id)
        if ps:
            scope_label = f'{ps.number} - {ps.location or ps.name or ""}'.strip(' -')
    elif muni_id:
        scope_station_ids = db.session.query(PollingStation.id).filter(
            PollingStation.municipality_id == muni_id
        )
        m = Municipality.query.get(muni_id)
        if m:
            scope_label = m.name
    elif county_id:
        scope_station_ids = (
            db.session.query(PollingStation.id)
            .join(Municipality, Municipality.id == PollingStation.municipality_id)
            .filter(Municipality.county_id == county_id)
        )
        c = County.query.get(county_id)
        if c:
            scope_label = c.name
    elif district_id and category == 'sabor':
        # Sabor scope = polling stations whose ListResults reference lists in this district
        scope_station_ids = (
            db.session.query(ListResult.polling_station_id)
            .join(ElectoralList, ElectoralList.id == ListResult.electoral_list_id)
            .filter(ElectoralList.district_id == district_id)
            .distinct()
        )
        d = ElectoralDistrict.query.get(district_id)
        if d:
            scope_label = d.name

    rounds = (
        db.session.query(ElectionRound)
        .join(Election, ElectionRound.election_id == Election.id)
        .join(ElectionType, Election.election_type_id == ElectionType.id)
        .filter(Election.year == year, ElectionType.name.in_(type_names))
        .order_by(ElectionType.name, ElectionRound.round_number)
        .all()
    )

    elections = []
    for er in rounds:
        election = er.election
        etype = election.election_type

        turnout_q = db.session.query(
            db.func.sum(TurnoutData.registered_voters),
            db.func.sum(TurnoutData.ballots_cast),
            db.func.sum(TurnoutData.valid_ballots),
            db.func.sum(TurnoutData.invalid_ballots),
        ).filter(TurnoutData.election_round_id == er.id)
        if scope_station_ids is not None:
            turnout_q = turnout_q.filter(TurnoutData.polling_station_id.in_(scope_station_ids))
        turnout = turnout_q.first()

        registered = turnout[0] or 0
        ballots = turnout[1] or 0
        valid = turnout[2] or 0
        invalid = turnout[3] or 0

        lists_q = (
            db.session.query(
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(ElectoralList.election_round_id == er.id)
        )
        if scope_station_ids is not None:
            lists_q = lists_q.filter(ListResult.polling_station_id.in_(scope_station_ids))
        top_lists = lists_q.group_by(ElectoralList.name).order_by(db.func.sum(ListResult.votes).desc()).all()

        cands_q = (
            db.session.query(
                Person.first_name,
                Person.last_name,
                db.func.sum(CandidateResult.votes).label('total_votes'),
                ElectoralList.name.label('list_name'),
            )
            .join(Candidacy, CandidateResult.candidacy_id == Candidacy.id)
            .join(Person, Candidacy.person_id == Person.id)
            .join(ElectoralList, Candidacy.electoral_list_id == ElectoralList.id)
            .filter(ElectoralList.election_round_id == er.id)
        )
        if scope_station_ids is not None:
            cands_q = cands_q.filter(CandidateResult.polling_station_id.in_(scope_station_ids))
        top_candidates = (
            cands_q.group_by(Person.first_name, Person.last_name, ElectoralList.name)
            .order_by(db.func.sum(CandidateResult.votes).desc())
            .all()
        )

        elections.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': round_date_iso(er, election),
            'round': er.round_number,
            'registered_voters': registered,
            'ballots_cast': ballots,
            'valid_ballots': valid,
            'invalid_ballots': invalid,
            'top_lists': [
                {'name': name, 'votes': votes}
                for name, votes in top_lists
            ],
            'top_candidates': [
                {
                    'name': f'{first} {last}',
                    'votes': votes,
                    'list_name': list_name,
                }
                for first, last, votes, list_name in top_candidates
            ],
        })

    # A place with no result in an election published per station number
    # only (NUMBER_ONLY_ELECTIONS): say so instead of a card of zeros.
    slug = {'predsjednicki': 'presidential', 'sabor': 'sabor'}.get(category)
    if (station_id and (slug, year) in {(s, y) for s, y, _ in NUMBER_ONLY_ELECTIONS}
            and not any(e['ballots_cast'] for e in elections)):
        return jsonify({
            'category': category,
            'year': year,
            'scope_label': scope_label,
            'scope': 'station',
            'elections': [],
            'error': 'Nema rezultata za ovo biračko mjesto.',
        })

    return jsonify({
        'category': category,
        'year': year,
        'scope_label': scope_label,
        'scope': 'station' if station_id else ('municipality' if muni_id else ('county' if county_id else 'national')),
        'elections': elections,
    })


@app.route('/api/national/eu-seats/<int:year>')
def eu_seats(year):
    """D'Hondt seat allocation for the EU parliament election (Croatia).

    Croatia is a single nationwide constituency for EU elections, with a 5%
    threshold of total valid votes and 12 seats (number per Election year
    can be overridden via EU_SEATS_BY_YEAR if it ever changes).
    """
    EU_SEATS_BY_YEAR = {2013: 12, 2014: 11, 2019: 12, 2024: 12}
    THRESHOLD_PCT = 5.0

    etype = ElectionType.query.filter_by(name='Izbori za Europski parlament').first()
    if not etype:
        return jsonify({'error': 'No EU election type'}), 404

    election = Election.query.filter_by(election_type_id=etype.id, year=year).first()
    if not election:
        return jsonify({'error': 'No EU election for this year'}), 404

    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()
    if not er:
        return jsonify({'error': 'No round 1'}), 404

    n_seats = EU_SEATS_BY_YEAR.get(year, 12)

    # Optional scope filters — narrow list/candidate counts to a single area.
    station_id = request.args.get('station_id', type=int)
    muni_id = request.args.get('municipality_id', type=int)
    county_id = request.args.get('county_id', type=int)
    scope_station_ids = None
    scope_label = 'Republika Hrvatska'
    if station_id:
        ps = PollingStation.query.get_or_404(station_id)
        scope_station_ids = db.session.query(PollingStation.id).filter(
            PollingStation.id.in_(station_place_ids(ps)))
        ps = PollingStation.query.get(station_id)
        if ps:
            scope_label = f'{ps.number} - {ps.location or ps.name or ""}'.strip(' -')
    elif muni_id:
        scope_station_ids = db.session.query(PollingStation.id).filter(PollingStation.municipality_id == muni_id)
        m = Municipality.query.get(muni_id)
        if m:
            scope_label = m.name
    elif county_id:
        scope_station_ids = (
            db.session.query(PollingStation.id)
            .join(Municipality, Municipality.id == PollingStation.municipality_id)
            .filter(Municipality.county_id == county_id)
        )
        c = County.query.get(county_id)
        if c:
            scope_label = c.name

    list_q = (
        db.session.query(
            ElectoralList.id,
            ElectoralList.name,
            db.func.sum(ListResult.votes).label('total_votes'),
        )
        .join(ListResult, ListResult.electoral_list_id == ElectoralList.id)
        .filter(ElectoralList.election_round_id == er.id)
    )
    if scope_station_ids is not None:
        list_q = list_q.filter(ListResult.polling_station_id.in_(scope_station_ids))
    list_rows = (
        list_q.group_by(ElectoralList.id, ElectoralList.name)
        .order_by(db.func.sum(ListResult.votes).desc())
        .all()
    )
    if not list_rows:
        return jsonify({'error': 'No list results'}), 404

    total_votes = sum(r.total_votes or 0 for r in list_rows)
    threshold_votes = total_votes * THRESHOLD_PCT / 100.0

    def primary_party(full_name):
        # EU coalitions are stored as multi-line cells (one party per line);
        # Sabor coalitions use comma-separated single line. Handle both.
        first_line = full_name.split('\n', 1)[0]
        return first_line.split(',', 1)[0].strip()

    # Filter eligible (>= 5% threshold) and apply D'Hondt
    eligible = [(r.id, r.name, r.total_votes or 0) for r in list_rows if (r.total_votes or 0) >= threshold_votes]
    quotients = []
    for list_id, list_name, votes in eligible:
        for divisor in range(1, n_seats + 1):
            quotients.append((votes / divisor, list_id, list_name))
    quotients.sort(key=lambda x: -x[0])
    winners = quotients[:n_seats]

    seats_by_list = {}  # list_id -> seat count
    for _, list_id, _ in winners:
        seats_by_list[list_id] = seats_by_list.get(list_id, 0) + 1

    # Build party rows: include EVERY list (even below threshold) for transparency,
    # but only eligible ones can have seats.
    parties = []
    for r in list_rows:
        votes = r.total_votes or 0
        seats = seats_by_list.get(r.id, 0)
        parties.append({
            'name': primary_party(r.name),
            'full_name': r.name,
            'votes': votes,
            'votes_pct': (votes / total_votes * 100.0) if total_votes else 0.0,
            'seats': seats,
            'eligible': votes >= threshold_votes,
        })
    # Group rows that share the same primary_party (defensive — usually 1:1 here)
    grouped = {}
    for p in parties:
        if p['name'] not in grouped:
            grouped[p['name']] = {'name': p['name'], 'votes': 0, 'votes_pct': 0.0, 'seats': 0, 'eligible': False}
        g = grouped[p['name']]
        g['votes'] += p['votes']
        g['votes_pct'] += p['votes_pct']
        g['seats'] += p['seats']
        g['eligible'] = g['eligible'] or p['eligible']
    party_list = sorted(grouped.values(), key=lambda x: (-x['seats'], -x['votes']))

    # Pull every candidacy's personal preferential vote total across all lists,
    # narrowed to the chosen scope when one is set.
    cand_q = (
        db.session.query(
            Candidacy.id,
            Candidacy.person_id,
            Person.first_name,
            Person.last_name,
            Candidacy.position_on_list,
            ElectoralList.id.label('list_id'),
            ElectoralList.name.label('list_name'),
            db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('personal_votes'),
        )
        .join(Person, Person.id == Candidacy.person_id)
        .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
        .outerjoin(CandidateResult, db.and_(
            CandidateResult.candidacy_id == Candidacy.id,
            *([CandidateResult.polling_station_id.in_(scope_station_ids)] if scope_station_ids is not None else []),
        ))
        .filter(ElectoralList.election_round_id == er.id)
    )
    cand_rows = (
        cand_q.group_by(Candidacy.id, Candidacy.person_id, Person.first_name, Person.last_name,
                        Candidacy.position_on_list, ElectoralList.id, ElectoralList.name)
        .all()
    )

    # Group candidacies by list for the within-list seat assignment below.
    by_list = {}
    for r in cand_rows:
        by_list.setdefault(r.list_id, []).append(r)

    # Apply Croatian preferential-vote rule to map list-level seats to specific
    # candidates: any candidate whose personal preferential votes reach
    # PREF_THRESHOLD_PCT of the list's votes is promoted ahead of the list-position
    # order, in descending order of preferential votes. Remaining seats then go
    # by list position, skipping candidates already promoted.
    PREF_THRESHOLD_PCT = 10.0
    winner_candidacy_ids = set()
    list_total_votes = {next(iter(by_list)): 0}  # placeholder, real values below
    for list_id, list_name, votes in eligible:
        seats_won = seats_by_list.get(list_id, 0)
        if seats_won == 0:
            continue
        members = by_list.get(list_id, [])
        list_total = votes  # total list votes from D'Hondt input
        pref_floor = list_total * PREF_THRESHOLD_PCT / 100.0
        promoted = sorted(
            [m for m in members if m.personal_votes >= pref_floor],
            key=lambda m: -m.personal_votes,
        )
        chosen = []
        seen = set()
        for m in promoted:
            if len(chosen) >= seats_won:
                break
            chosen.append(m.id)
            seen.add(m.id)
        for m in sorted(members, key=lambda m: m.position_on_list):
            if len(chosen) >= seats_won:
                break
            if m.id in seen:
                continue
            chosen.append(m.id)
            seen.add(m.id)
        winner_candidacy_ids.update(chosen)

    # Return every candidate; the frontend handles initial display + "show more".
    candidates = []
    for r in cand_rows:
        candidates.append({
            'candidacy_id': r.id,
            'person_id': r.person_id,
            'name': f"{r.first_name} {r.last_name}",
            'party': primary_party(r.list_name),
            'list_name': r.list_name,
            'list_position': r.position_on_list,
            'personal_votes': int(r.personal_votes),
            'personal_pct': (r.personal_votes / total_votes * 100.0) if total_votes else 0.0,
            'is_winner': r.id in winner_candidacy_ids,
        })
    candidates.sort(key=lambda c: -c['personal_votes'])

    return jsonify({
        'year': year,
        'total_seats': n_seats,
        'total_votes': total_votes,
        'threshold_pct': THRESHOLD_PCT,
        'threshold_votes': int(round(threshold_votes)),
        'parties': party_list,
        'candidates': candidates,
        'scope': 'station' if station_id else ('municipality' if muni_id else ('county' if county_id else 'national')),
        'scope_label': scope_label,
    })
