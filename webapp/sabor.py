"""Sabor (Zastupnički dom) 2000-2024: D'Hondt seats, raw list votes and the
izborne jedinice scope.
"""

from flask import jsonify, request
from webapp.core import app, db, static_cache
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
    ParliamentMember,
    Person,
    PollingStation,
)
from webapp.common import diaspora_seats, sabor_total_seats
from webapp.people import saziv_roles_by_person


@app.route('/api/national/sabor-seats/<int:year>')
@static_cache
def sabor_seats(year):
    """Calculate Sabor seat distribution using D'Hondt method."""
    etype = ElectionType.query.filter_by(name='Parlamentarni izbori').first()
    if not etype:
        return jsonify({'error': 'No sabor election type'}), 404

    election = Election.query.filter_by(election_type_id=etype.id, year=year).first()
    if not election:
        return jsonify({'error': 'No sabor election for this year'}), 404

    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()
    if not er:
        return jsonify({'error': 'No round 1'}), 404

    # Get all districts
    districts = (
        db.session.query(ElectoralDistrict)
        .join(ElectoralList, ElectoralList.district_id == ElectoralDistrict.id)
        .filter(ElectoralList.election_round_id == er.id)
        .distinct()
        .order_by(ElectoralDistrict.id)
        .all()
    )

    total_seats = {}  # list_name -> seat count
    all_candidates = []  # [{name, party_group, district}]
    district_details = []

    def primary_party(full_name):
        """Extract the first party/candidate name as grouping key."""
        return full_name.split(',')[0].strip()

    # Minority sub-district seat counts (district numbers 121-126)
    MINORITY_SEATS = {121: 3, 122: 1, 123: 1, 124: 1, 125: 1, 126: 1}

    for dist in districts:
        # Determine seats for this district
        if dist.number in MINORITY_SEATS:
            n_seats = MINORITY_SEATS[dist.number]
        elif dist.number == 11:
            n_seats = diaspora_seats(year)  # diaspora: 5 in 2007, 3 since 2011
        elif dist.number == 12:
            n_seats = 8  # old monolithic district 12 (legacy)
        else:
            n_seats = 14  # standard districts I-X

        # Get votes per list in this district (need list IDs for candidate lookup)
        list_rows = (
            db.session.query(
                ElectoralList.id,
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(
                ElectoralList.election_round_id == er.id,
                ElectoralList.district_id == dist.id,
            )
            .group_by(ElectoralList.id, ElectoralList.name)
            .order_by(db.func.sum(ListResult.votes).desc())
            .all()
        )

        if not list_rows:
            continue

        list_votes = [(r.name, r.total_votes) for r in list_rows]
        list_id_map = {}  # list_name -> list_id
        for r in list_rows:
            list_id_map[r.name] = r.id

        total_district_votes = sum(v for _, v in list_votes)

        # Apply 5% threshold for standard districts (I-X)
        is_standard = n_seats == 14
        if is_standard:
            threshold = total_district_votes * 0.05
            eligible = [(name, votes) for name, votes in list_votes if votes >= threshold]
        else:
            eligible = [(name, votes) for name, votes in list_votes]

        # D'Hondt method
        quotients = []
        for list_name, votes in eligible:
            for divisor in range(1, n_seats + 1):
                quotients.append((votes / divisor, list_name))

        quotients.sort(key=lambda x: -x[0])
        winners = quotients[:n_seats]

        is_minority = dist.number in MINORITY_SEATS
        dist_seats = {}
        for _, list_name in winners:
            dist_seats[list_name] = dist_seats.get(list_name, 0) + 1
            # Group all minority sub-district seats under one key
            seat_key = 'NACIONALNE MANJINE' if is_minority else list_name
            total_seats[seat_key] = total_seats.get(seat_key, 0) + 1

        # Map list_name -> total list votes for the preferential-vote threshold.
        list_votes_by_name = {name: votes for name, votes in list_votes}

        # Croatian Sabor uses an open-list system: any candidate whose personal
        # preferential votes reach PREF_THRESHOLD_PCT of the list's total votes
        # is promoted ahead of the list-position order. Remaining seats then go
        # by list position (skipping candidates already promoted).
        PREF_THRESHOLD_PCT = 10.0

        # Get candidates for lists that won seats
        for list_name, seats_won in dist_seats.items():
            list_id = list_id_map.get(list_name)
            if not list_id or seats_won == 0:
                continue

            cand_rows = (
                db.session.query(
                    Candidacy.id,
                    Candidacy.person_id,
                    Person.first_name,
                    Person.last_name,
                    Candidacy.position_on_list,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('personal_votes'),
                )
                .join(Person, Person.id == Candidacy.person_id)
                .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .filter(Candidacy.electoral_list_id == list_id)
                .group_by(Candidacy.id, Candidacy.person_id, Person.first_name,
                          Person.last_name, Candidacy.position_on_list)
                .all()
            )

            list_total_votes = list_votes_by_name.get(list_name, 0)
            pref_floor = list_total_votes * PREF_THRESHOLD_PCT / 100.0

            promoted = sorted(
                [c for c in cand_rows if int(c.personal_votes or 0) >= pref_floor],
                key=lambda c: -int(c.personal_votes or 0),
            )
            chosen = []
            seen = set()
            for c in promoted:
                if len(chosen) >= seats_won:
                    break
                chosen.append(c)
                seen.add(c.id)
            for c in sorted(cand_rows, key=lambda c: c.position_on_list):
                if len(chosen) >= seats_won:
                    break
                if c.id in seen:
                    continue
                chosen.append(c)
                seen.add(c.id)

            is_minority = dist.number in MINORITY_SEATS
            group = 'NACIONALNE MANJINE' if is_minority else primary_party(list_name)
            for c in chosen:
                all_candidates.append({
                    'name': f"{c.first_name} {c.last_name}",
                    'person_id': c.person_id,
                    'party': group,
                    'district': dist.name,
                })

            # Seats the list won but for which we hold no candidate row. Before
            # 2015 there was no preferential voting, so DIP published only list
            # totals for districts I-XI and no candidate names exist at all for
            # e.g. 2011. Emit an explicit placeholder rather than repeating the
            # party name in a person field — the frontend would otherwise print
            # a party under "Ime i prezime" and link it to a politician search.
            for _ in range(seats_won - len(chosen)):
                all_candidates.append({
                    'name': None,
                    'placeholder': True,
                    'party': group,
                    'district': dist.name,
                })

        district_details.append({
            'district': dist.name,
            'seats': n_seats,
            'results': [
                {'name': name, 'votes': votes, 'seats': dist_seats.get(name, 0)}
                for name, votes in list_votes
            ],
        })

    # Group coalitions by primary party
    grouped_seats = {}
    for full_name, seats in total_seats.items():
        key = primary_party(full_name)
        if key not in grouped_seats:
            grouped_seats[key] = {'name': key, 'seats': 0}
        grouped_seats[key]['seats'] += seats

    # Sort by seats descending
    seat_list = sorted(grouped_seats.values(), key=lambda x: -x['seats'])

    # Group candidates by party, matching seat_list order
    party_candidates = {}
    for c in all_candidates:
        party_candidates.setdefault(c['party'], []).append(c)

    # Build ordered candidate list matching party order
    ordered_candidates = []
    for p in seat_list:
        cands = party_candidates.get(p['name'], [])
        for c in cands:
            ordered_candidates.append(c)

    # Curated roster of who actually sat in this convocation. Present for
    # years where the seat holders can't be derived (no candidate names were
    # published before preferential voting) — see ParliamentMember. Ordered
    # by caucus size, then surname, so the table groups the way the hemicycle
    # legend does.
    member_rows = (
        db.session.query(ParliamentMember, Person)
        .join(Person, Person.id == ParliamentMember.person_id)
        .filter(ParliamentMember.election_id == election.id)
        .all()
    )
    party_size = {}
    for m, _ in member_rows:
        party_size[m.party] = party_size.get(m.party, 0) + 1
    member_rows.sort(key=lambda row: (
        -party_size[row[0].party], row[0].party,
        row[1].last_name or '', row[1].first_name or '',
    ))
    members = [{
        'name': f'{prs.first_name} {prs.last_name}'.strip(),
        'person_id': prs.id,
        'party': m.party,
        'minority': bool(m.minority),
        'note': m.note or '',
        # Only rosters published per electoral district carry one (2003 does,
        # 2007 and 2011 are a single national roll).
        'district': m.district.name if m.district else '',
    } for m, prs in member_rows]

    # Key offices of this saziv (PM, Speaker, deputies), for the badge by a
    # name in either table.
    role_ids = {c['person_id'] for c in ordered_candidates if c.get('person_id')} | \
               {m['person_id'] for m in members}
    year_roles = saziv_roles_by_person(role_ids, year)
    for row in ordered_candidates + members:
        if row.get('person_id') in year_roles:
            row['roles'] = year_roles[row['person_id']]

    return jsonify({
        'year': year,
        'total_seats': sabor_total_seats(year),
        'parties': seat_list,
        'candidates': ordered_candidates,
        'members': members,
        'districts': district_details,
    })


@app.route('/api/national/sabor-raw/<int:year>')
@static_cache
def sabor_raw(year):
    """Return raw vote data per list per district for client-side D'Hondt."""
    etype = ElectionType.query.filter_by(name='Parlamentarni izbori').first()
    if not etype:
        return jsonify({'error': 'No sabor election type'}), 404

    election = Election.query.filter_by(election_type_id=etype.id, year=year).first()
    if not election:
        return jsonify({'error': 'No sabor election for this year'}), 404

    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()
    if not er:
        return jsonify({'error': 'No round 1'}), 404

    districts = (
        db.session.query(ElectoralDistrict)
        .join(ElectoralList, ElectoralList.district_id == ElectoralDistrict.id)
        .filter(ElectoralList.election_round_id == er.id)
        .distinct()
        .order_by(ElectoralDistrict.id)
        .all()
    )

    MINORITY_SEATS = {121: 3, 122: 1, 123: 1, 124: 1, 125: 1, 126: 1}

    result_districts = []
    minority_total_votes = 0
    minority_winners = []  # collect winners across all minority sub-districts

    for dist in districts:
        if dist.number in MINORITY_SEATS:
            n_seats = MINORITY_SEATS[dist.number]
        elif dist.number == 11:
            n_seats = diaspora_seats(year)
        elif dist.number == 12:
            n_seats = 8
        else:
            n_seats = 14

        list_votes = (
            db.session.query(
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(
                ElectoralList.election_round_id == er.id,
                ElectoralList.district_id == dist.id,
            )
            .group_by(ElectoralList.name)
            .order_by(db.func.sum(ListResult.votes).desc())
            .all()
        )

        total_votes = sum(v for _, v in list_votes)

        # Minority sub-districts: collect winners, merge into single district later
        if dist.number in MINORITY_SEATS:
            minority_total_votes += total_votes
            for name, votes in list_votes[:n_seats]:
                minority_winners.append({'name': name, 'votes': votes, 'seats': 1})
            continue

        def primary_party(full_name):
            return full_name.split(',')[0].strip()

        lists = [{'name': name, 'votes': votes, 'group': primary_party(name)}
                 for name, votes in list_votes]

        result_districts.append({
            'name': dist.name,
            'seats': n_seats,
            'total_votes': total_votes,
            'lists': lists,
        })

    # Add minority district — each winner gets their own entry so they
    # can be individually dragged into coalitions in the simulation.
    if minority_winners:
        result_districts.append({
            'name': 'XII. IZBORNA JEDINICA - NACIONALNE MANJINE',
            'seats': 8,
            'total_votes': minority_total_votes,
            'lists': [{'name': w['name'], 'votes': w['votes'],
                        'group': 'NACIONALNE MANJINE', 'fixed_seats': w['seats']}
                       for w in minority_winners],
            'minority': True,
        })

    return jsonify({
        'year': year,
        'districts': result_districts,
    })


# --- Sabor: izborne jedinice & per-district scope ---

@app.route('/api/sabor/districts/<int:year>')
def sabor_districts(year):
    """List Sabor electoral districts that have results for this year.
    Returns id, number, name. Skips minority sub-districts (121-126) — they're
    handled separately in the seat-allocation logic and aren't useful as a
    geographic filter for the bar-chart view."""
    rows = (
        db.session.query(ElectoralDistrict.id, ElectoralDistrict.number, ElectoralDistrict.name)
        .join(ElectoralList, ElectoralList.district_id == ElectoralDistrict.id)
        .join(ElectionRound, ElectionRound.id == ElectoralList.election_round_id)
        .join(Election, Election.id == ElectionRound.election_id)
        .join(ElectionType, ElectionType.id == Election.election_type_id)
        .filter(ElectionType.name == 'Parlamentarni izbori', Election.year == year,
                ElectoralDistrict.number < 121)
        .distinct()
        .order_by(ElectoralDistrict.number)
        .all()
    )
    return jsonify([{'id': r.id, 'number': r.number, 'name': r.name} for r in rows])


@app.route('/api/sabor/district-municipalities/<int:district_id>')
def sabor_district_municipalities(district_id):
    """Municipalities with meaningful polling results in this Sabor district.

    Diaspora pseudo-munis (e.g. ALBANIJA, ARGENTINA) typically have 1–9 votes
    in every district, so we threshold at >= 50 votes in this district to keep
    the dropdown focused. Sorted by vote count descending so biggest first.
    """
    year = request.args.get('year', type=int)
    MIN_VOTES = 50
    q = (
        db.session.query(
            Municipality.id, Municipality.name, County.name.label('county_name'),
            db.func.sum(ListResult.votes).label('total_votes'),
        )
        .join(PollingStation, PollingStation.municipality_id == Municipality.id)
        .join(ListResult, ListResult.polling_station_id == PollingStation.id)
        .join(ElectoralList, ElectoralList.id == ListResult.electoral_list_id)
        .join(ElectionRound, ElectionRound.id == ElectoralList.election_round_id)
        .join(Election, Election.id == ElectionRound.election_id)
        .join(ElectionType, ElectionType.id == Election.election_type_id)
        .outerjoin(County, County.id == Municipality.county_id)
        .filter(ElectionType.name == 'Parlamentarni izbori',
                ElectoralList.district_id == district_id)
    )
    if year:
        q = q.filter(Election.year == year)
    rows = (
        q.group_by(Municipality.id, Municipality.name, County.name)
        .having(db.func.sum(ListResult.votes) >= MIN_VOTES)
        .order_by(db.func.sum(ListResult.votes).desc())
        .all()
    )
    return jsonify([
        {'id': r.id, 'name': r.name, 'county': r.county_name, 'votes': int(r.total_votes or 0)}
        for r in rows
    ])
