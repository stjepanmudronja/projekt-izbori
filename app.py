from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy

from elections.importers.name_utils import normalize_person_name

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///projekt_izbori'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Models — reflect the existing Django tables

class Person(db.Model):
    __tablename__ = 'elections_person'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    normalized_name = db.Column(db.String)
    candidacies = db.relationship('Candidacy', backref='person', lazy=True)


class Party(db.Model):
    __tablename__ = 'elections_party'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    short_name = db.Column(db.String)


class ElectoralList(db.Model):
    __tablename__ = 'elections_electorallist'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    election_round_id = db.Column(db.Integer, db.ForeignKey('elections_electionround.id'))
    district_id = db.Column(db.Integer, db.ForeignKey('elections_electoraldistrict.id'))
    election_round = db.relationship('ElectionRound', backref='lists', lazy=True)
    district = db.relationship('ElectoralDistrict', backref='lists', lazy=True)


class Candidacy(db.Model):
    __tablename__ = 'elections_candidacy'
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('elections_person.id'))
    electoral_list_id = db.Column(db.Integer, db.ForeignKey('elections_electorallist.id'))
    position_on_list = db.Column(db.Integer)
    electoral_list = db.relationship('ElectoralList', backref='candidacies', lazy=True)


class ElectionRound(db.Model):
    __tablename__ = 'elections_electionround'
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer)
    election_id = db.Column(db.Integer, db.ForeignKey('elections_election.id'))
    election = db.relationship('Election', backref='rounds', lazy=True)


class Election(db.Model):
    __tablename__ = 'elections_election'
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    name = db.Column(db.String)
    date = db.Column(db.Date)
    election_type_id = db.Column(db.Integer, db.ForeignKey('elections_electiontype.id'))
    election_type = db.relationship('ElectionType', backref='elections', lazy=True)


class ElectionType(db.Model):
    __tablename__ = 'elections_electiontype'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String)
    name = db.Column(db.String)


class ElectoralDistrict(db.Model):
    __tablename__ = 'elections_electoraldistrict'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer)
    name = db.Column(db.String)


class ListResult(db.Model):
    __tablename__ = 'elections_listresult'
    id = db.Column(db.Integer, primary_key=True)
    electoral_list_id = db.Column(db.Integer, db.ForeignKey('elections_electorallist.id'))
    polling_station_id = db.Column(db.Integer, db.ForeignKey('elections_pollingstation.id'))
    votes = db.Column(db.Integer)
    electoral_list = db.relationship('ElectoralList', backref='results', lazy=True)


class CandidateResult(db.Model):
    __tablename__ = 'elections_candidateresult'
    id = db.Column(db.Integer, primary_key=True)
    candidacy_id = db.Column(db.Integer, db.ForeignKey('elections_candidacy.id'))
    polling_station_id = db.Column(db.Integer, db.ForeignKey('elections_pollingstation.id'))
    votes = db.Column(db.Integer)
    candidacy = db.relationship('Candidacy', backref='results', lazy=True)


class PollingStation(db.Model):
    __tablename__ = 'elections_pollingstation'
    id = db.Column(db.Integer, primary_key=True)
    municipality_id = db.Column(db.Integer, db.ForeignKey('elections_municipality.id'))
    number = db.Column(db.Integer)
    name = db.Column(db.String)
    location = db.Column(db.String)
    address = db.Column(db.String)
    municipality = db.relationship('Municipality', backref='polling_stations', lazy=True)


class Municipality(db.Model):
    __tablename__ = 'elections_municipality'
    id = db.Column(db.Integer, primary_key=True)
    county_id = db.Column(db.Integer, db.ForeignKey('elections_county.id'))
    name = db.Column(db.String)
    type = db.Column(db.String)
    county = db.relationship('County', backref='municipalities', lazy=True)


class County(db.Model):
    __tablename__ = 'elections_county'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String)
    name = db.Column(db.String)


class TurnoutData(db.Model):
    __tablename__ = 'elections_turnoutdata'
    id = db.Column(db.Integer, primary_key=True)
    election_round_id = db.Column(db.Integer, db.ForeignKey('elections_electionround.id'))
    polling_station_id = db.Column(db.Integer, db.ForeignKey('elections_pollingstation.id'))
    registered_voters = db.Column(db.Integer)
    ballots_cast = db.Column(db.Integer)
    valid_ballots = db.Column(db.Integer)
    invalid_ballots = db.Column(db.Integer)
    election_round = db.relationship('ElectionRound', backref='turnout_data', lazy=True)


# Routes

@app.route('/')
def index():
    return render_template('index.html')


# Pretty URLs per sidebar tab — the SPA reads window.location to switch tabs.
# Restricted to a known whitelist so we don't accidentally swallow /api/...
# or static asset paths.
SPA_ROUTES = {
    'politicar', 'stranka', 'prema-lokaciji', 'usporedba',
    'predsjednicki-izbori', 'eu-parlamentarni-izbori', 'lokalni-izbori',
    'rezultati-koalicije-sabor', 'izlaznost', 'karta',
}


@app.route('/<slug>')
def spa_route(slug):
    if slug in SPA_ROUTES:
        return render_template('index.html')
    return ('Not Found', 404)


@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'person')

    if len(q) < 2:
        return jsonify([])

    if search_type == 'person':
        # Person.normalized_name is stored diacritic-stripped + uppercase;
        # apply the same normalization to the query so that "Milanović" and
        # "Milanovic" both match.
        normalized_q = normalize_person_name(q)
        persons = (
            Person.query
            .filter(Person.normalized_name.ilike(f'%{normalized_q}%'))
            .order_by(Person.last_name, Person.first_name)
            .limit(20)
            .all()
        )
        return jsonify([
            {'id': p.id, 'name': f'{p.first_name} {p.last_name}'}
            for p in persons
        ])
    elif search_type == 'party':
        # The elections_party table isn't populated — parties live as the
        # first line / first comma-segment of ElectoralList.name. Derive
        # distinct primary-party names from list names directly.
        rows = (
            db.session.query(ElectoralList.name)
            .filter(ElectoralList.name.ilike(f'%{q}%'))
            .all()
        )
        seen = set()
        out = []
        for (name,) in rows:
            primary = (name or '').split('\n', 1)[0].split(',', 1)[0].strip()
            if not primary or primary in seen:
                continue
            # Only keep ones that themselves match the query (so a coalition
            # mentioning HDZ as a member doesn't surface when the user types
            # the leader's name as their primary).
            if q.lower() not in primary.lower():
                continue
            seen.add(primary)
            out.append({'id': primary, 'name': primary})
            if len(out) >= 20:
                break
        out.sort(key=lambda x: x['name'])
        return jsonify(out)
    else:
        # Search polling stations by location + address, deduplicated
        stations = (
            db.session.query(
                db.func.min(PollingStation.id).label('id'),
                PollingStation.location,
                PollingStation.address,
                db.func.min(Municipality.name).label('municipality_name'),
            )
            .join(Municipality)
            .filter(
                db.or_(
                    PollingStation.address.ilike(f'%{q}%'),
                    PollingStation.location.ilike(f'%{q}%'),
                    PollingStation.name.ilike(f'%{q}%'),
                    Municipality.name.ilike(f'%{q}%'),
                )
            )
            .group_by(
                PollingStation.location,
                PollingStation.address,
            )
            .order_by(db.func.min(Municipality.name), PollingStation.location)
            .limit(20)
            .all()
        )
        return jsonify([
            {
                'id': s.id,
                'name': f'{s.location}, {s.address}',
                'municipality': s.municipality_name or '',
            }
            for s in stations
        ])


@app.route('/api/person/<int:person_id>')
def person_detail(person_id):
    person = Person.query.get_or_404(person_id)
    candidacies = (
        Candidacy.query
        .filter_by(person_id=person_id)
        .join(ElectoralList)
        .join(ElectionRound)
        .join(Election)
        .join(ElectionType)
        .order_by(
            Election.year.desc(),
            Election.date.desc().nullslast(),
            ElectionRound.round_number.desc(),
        )
        .all()
    )

    # Pre-compute finish rank so we can flag winners / runners-up. Each
    # election type ranks within the unit where candidates actually compete
    # head-to-head:
    #   - Predsjednički: round + district (district is null nation-wide)
    #   - Gradonačelnik / Načelnik: round + muni
    #   - Župan: round + county
    # Sabor / EU and lokalni list-races (Vijeće, Skupština) are intentionally
    # excluded — they're seat-allocation races where "vote count" doesn't
    # cleanly map to a winner.
    RANK_BY_DISTRICT = {'Predsjednički izbori'}
    RANK_BY_MUNI = {'Gradonačelnik', 'Načelnik'}
    RANK_BY_COUNTY = {'Župan'}
    LOKALNI_EXEC = RANK_BY_MUNI | RANK_BY_COUNTY

    # For lokalni execs we need the muni each candidacy ran in (and the
    # county for Župan). Batch the lookup so we don't issue N queries.
    lokalni_cands = [c for c in candidacies
                     if c.electoral_list.election_round.election.election_type.name in LOKALNI_EXEC]
    list_to_muni = {}
    muni_to_county = {}
    if lokalni_cands:
        list_ids = [c.electoral_list_id for c in lokalni_cands]
        muni_rows = (
            db.session.query(
                ElectoralList.id.label('list_id'),
                PollingStation.municipality_id.label('muni_id'),
            )
            .select_from(ElectoralList)
            .join(ListResult, ListResult.electoral_list_id == ElectoralList.id)
            .join(PollingStation, PollingStation.id == ListResult.polling_station_id)
            .filter(ElectoralList.id.in_(list_ids))
            .distinct()
            .all()
        )
        # Take the first muni seen per list (lokalni-exec lists belong to
        # exactly one muni in practice).
        for row in muni_rows:
            list_to_muni.setdefault(row.list_id, row.muni_id)
        muni_ids = list(set(list_to_muni.values()))
        if muni_ids:
            muni_to_county = dict(
                db.session.query(Municipality.id, Municipality.county_id)
                .filter(Municipality.id.in_(muni_ids))
                .all()
            )

    # Build scope key per candidacy and the unique-scope set.
    candidacy_scope = {}
    rank_scope_keys = set()
    for c in candidacies:
        etype = c.electoral_list.election_round.election.election_type.name
        rid = c.electoral_list.election_round_id
        scope = None
        if etype in RANK_BY_DISTRICT:
            scope = ('district', rid, c.electoral_list.district_id)
        elif etype in RANK_BY_MUNI:
            muni_id = list_to_muni.get(c.electoral_list_id)
            if muni_id:
                scope = ('muni', rid, muni_id)
        elif etype in RANK_BY_COUNTY:
            muni_id = list_to_muni.get(c.electoral_list_id)
            cnty_id = muni_to_county.get(muni_id) if muni_id else None
            if cnty_id:
                scope = ('county', rid, cnty_id)
        if scope:
            candidacy_scope[c.id] = scope
            rank_scope_keys.add(scope)

    rank_lookup = {}  # candidacy_id -> (rank, total_candidates)
    for scope in rank_scope_keys:
        scope_type, rid, sval = scope
        if scope_type == 'district':
            q = (
                db.session.query(
                    Candidacy.id,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('v'),
                )
                .select_from(Candidacy)
                .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
                .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .filter(ElectoralList.election_round_id == rid)
            )
            if sval is None:
                q = q.filter(ElectoralList.district_id.is_(None))
            else:
                q = q.filter(ElectoralList.district_id == sval)
        elif scope_type == 'muni':
            q = (
                db.session.query(
                    Candidacy.id,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('v'),
                )
                .select_from(Candidacy)
                .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
                .join(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .join(PollingStation, PollingStation.id == CandidateResult.polling_station_id)
                .filter(
                    ElectoralList.election_round_id == rid,
                    PollingStation.municipality_id == sval,
                )
            )
        else:  # 'county'
            q = (
                db.session.query(
                    Candidacy.id,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('v'),
                )
                .select_from(Candidacy)
                .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
                .join(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .join(PollingStation, PollingStation.id == CandidateResult.polling_station_id)
                .join(Municipality, Municipality.id == PollingStation.municipality_id)
                .filter(
                    ElectoralList.election_round_id == rid,
                    Municipality.county_id == sval,
                )
            )
        rows = q.group_by(Candidacy.id).all()
        rows.sort(key=lambda r: -int(r.v or 0))
        total = len(rows)
        for i, row in enumerate(rows, 1):
            rank_lookup[row.id] = (i, total)

    results = []
    for c in candidacies:
        el = c.electoral_list
        er = el.election_round
        election = er.election
        etype = election.election_type

        # Sum total votes for this candidacy across all polling stations
        total_votes = db.session.query(
            db.func.sum(CandidateResult.votes)
        ).filter_by(candidacy_id=c.id).scalar() or 0

        # Sum total list votes
        total_list_votes = db.session.query(
            db.func.sum(ListResult.votes)
        ).filter_by(electoral_list_id=el.id).scalar() or 0

        # Get total valid ballots for the same polling stations where this list got results
        # This scopes turnout to the correct district/area
        station_ids = db.session.query(
            ListResult.polling_station_id
        ).filter_by(electoral_list_id=el.id).subquery()

        total_valid_ballots = db.session.query(
            db.func.sum(TurnoutData.valid_ballots)
        ).filter(
            TurnoutData.election_round_id == er.id,
            TurnoutData.polling_station_id.in_(db.session.query(station_ids))
        ).scalar() or 0

        vote_share = round((total_votes / total_valid_ballots) * 100, 1) if total_valid_ballots > 0 else 0

        rank, total_cands = rank_lookup.get(c.id, (None, None))
        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': election.date.isoformat() if election.date else None,
            'round': er.round_number,
            'list_name': el.name,
            'position': c.position_on_list,
            'district': el.district.name if el.district else None,
            'candidate_votes': total_votes,
            'list_votes': total_list_votes,
            'total_valid_ballots': total_valid_ballots,
            'vote_share': vote_share,
            'rank': rank,
            'total_candidates_in_round': total_cands,
        })

    return jsonify({
        'id': person.id,
        'first_name': person.first_name,
        'last_name': person.last_name,
        'results': results,
    })


@app.route('/api/party/<path:name>')
def party_detail_by_name(name):
    """Aggregate results across every ElectoralList whose primary-party label
    matches `name`. Used in place of the legacy id-based detail because the
    elections_party table is empty — parties live inside list-name strings."""
    target = (name or '').strip()
    if not target:
        return jsonify({'error': 'missing name'}), 400

    lists = ElectoralList.query.filter(ElectoralList.name.ilike(f'%{target}%')).all()
    matching = []
    for el in lists:
        primary = (el.name or '').split('\n', 1)[0].split(',', 1)[0].strip()
        if primary == target:
            matching.append(el)

    results = []
    for el in matching:
        er = el.election_round
        election = er.election if er else None
        etype = election.election_type if election else None
        total_votes = db.session.query(db.func.sum(ListResult.votes)).filter_by(
            electoral_list_id=el.id
        ).scalar() or 0
        results.append({
            'election': (election.name if election else None) or (
                f"{etype.name if etype else ''} {election.year if election else ''}".strip()
            ),
            'election_type': etype.name if etype else '',
            'year': election.year if election else None,
            'date': election.date.isoformat() if election and election.date else None,
            'round': er.round_number if er else None,
            'list_name': el.name,
            'district': el.district.name if el.district else None,
            'total_votes': int(total_votes),
        })
    results.sort(key=lambda r: ((r['year'] or 0) * -1, r['date'] or '', -(r['round'] or 0)))
    return jsonify({
        'id': target,
        'name': target,
        'short_name': None,
        'results': results,
    })


@app.route('/api/party/<int:party_id>')
def party_detail(party_id):
    party = Party.query.get_or_404(party_id)

    # Find all electoral lists associated with this party
    list_party = db.Table(
        'elections_electorallist_parties',
        db.metadata,
        db.Column('electorallist_id', db.Integer),
        db.Column('party_id', db.Integer),
        autoload_with=db.engine,
    )

    lists = (
        ElectoralList.query
        .join(list_party, ElectoralList.id == list_party.c.electorallist_id)
        .filter(list_party.c.party_id == party_id)
        .join(ElectionRound)
        .join(Election)
        .join(ElectionType)
        .order_by(
            Election.year.desc(),
            Election.date.desc().nullslast(),
            ElectionRound.round_number.desc(),
        )
        .all()
    )

    results = []
    for el in lists:
        er = el.election_round
        election = er.election
        etype = election.election_type

        total_votes = db.session.query(
            db.func.sum(ListResult.votes)
        ).filter_by(electoral_list_id=el.id).scalar() or 0

        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': election.date.isoformat() if election.date else None,
            'round': er.round_number,
            'list_name': el.name,
            'district': el.district.name if el.district else None,
            'total_votes': total_votes,
        })

    return jsonify({
        'id': party.id,
        'name': party.name,
        'short_name': party.short_name,
        'results': results,
    })


@app.route('/api/station/<int:station_id>')
def station_detail(station_id):
    station = PollingStation.query.get_or_404(station_id)
    municipality = station.municipality
    county = municipality.county if municipality else None

    # Find all polling stations at the same location/address (across elections)
    sibling_ids = [
        s.id for s in
        PollingStation.query
        .filter_by(
            location=station.location,
            address=station.address,
        )
        .all()
    ]

    # Get all election rounds that have turnout data for these stations
    turnout_rows = (
        db.session.query(
            ElectionRound.id.label('er_id'),
            db.func.sum(TurnoutData.registered_voters).label('registered_voters'),
            db.func.sum(TurnoutData.ballots_cast).label('ballots_cast'),
            db.func.sum(TurnoutData.valid_ballots).label('valid_ballots'),
            db.func.sum(TurnoutData.invalid_ballots).label('invalid_ballots'),
        )
        .join(ElectionRound, TurnoutData.election_round_id == ElectionRound.id)
        .join(Election, ElectionRound.election_id == Election.id)
        .filter(TurnoutData.polling_station_id.in_(sibling_ids))
        .group_by(ElectionRound.id)
        .order_by(
            db.func.min(Election.year).desc(),
            db.func.min(Election.date).desc().nullslast(),
            db.func.min(ElectionRound.round_number).desc(),
        )
        .all()
    )

    elections = []
    for td in turnout_rows:
        er = ElectionRound.query.get(td.er_id)
        election = er.election
        etype = election.election_type

        # All lists by votes across all sibling stations
        top_lists = (
            db.session.query(
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(
                ListResult.polling_station_id.in_(sibling_ids),
                ElectoralList.election_round_id == er.id,
            )
            .group_by(ElectoralList.name)
            .order_by(db.func.sum(ListResult.votes).desc())
            .limit(5)
            .all()
        )

        # All candidates
        top_candidates = (
            db.session.query(
                Person.first_name,
                Person.last_name,
                db.func.sum(CandidateResult.votes).label('total_votes'),
                ElectoralList.name.label('list_name'),
            )
            .join(Candidacy, CandidateResult.candidacy_id == Candidacy.id)
            .join(Person, Candidacy.person_id == Person.id)
            .join(ElectoralList, Candidacy.electoral_list_id == ElectoralList.id)
            .filter(
                CandidateResult.polling_station_id.in_(sibling_ids),
                ElectoralList.election_round_id == er.id,
            )
            .group_by(Person.first_name, Person.last_name, ElectoralList.name)
            .order_by(db.func.sum(CandidateResult.votes).desc())
            .limit(5)
            .all()
        )

        elections.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': election.date.isoformat() if election.date else None,
            'round': er.round_number,
            'registered_voters': td.registered_voters,
            'ballots_cast': td.ballots_cast,
            'valid_ballots': td.valid_ballots,
            'invalid_ballots': td.invalid_ballots,
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

    return jsonify({
        'id': station.id,
        'name': f'{station.location}, {station.address}',
        'location': station.location,
        'address': station.address,
        'municipality': municipality.name if municipality else None,
        'county': county.name if county else None,
        'elections': elections,
    })


# --- Location filter APIs ---

@app.route('/api/counties')
def list_counties():
    # Codes >= 90 are reserved for synthetic geography (e.g. the 1997 summary
    # PDF lives under a "REPUBLIKA HRVATSKA (sažetak)" county) — keep them
    # out of the scope picker so users don't accidentally select them.
    counties = (
        County.query
        .filter(db.or_(County.code < '90', County.code.is_(None)))
        .order_by(County.name)
        .all()
    )
    return jsonify([{'id': c.id, 'name': c.name} for c in counties])


@app.route('/api/municipalities/<int:county_id>')
def list_municipalities(county_id):
    """Munis in this county, excluding the Sabor-only "ZAGREB - N. IZBORNA
    JEDINICA" pseudo-munis (those exist solely so the parliamentary import
    can split Zagreb across multiple electoral districts; for every other
    election GRAD ZAGREB is the meaningful unit). Sabor's own scope picker
    uses /api/sabor/district-municipalities instead and isn't affected.
    """
    munis = (
        Municipality.query
        .filter(Municipality.county_id == county_id)
        .filter(~Municipality.name.like('%IZBORNA JEDINICA%'))
        .order_by(Municipality.name)
        .all()
    )
    return jsonify([{'id': m.id, 'name': m.name} for m in munis])


@app.route('/api/polling-stations/<int:municipality_id>')
def list_polling_stations(municipality_id):
    stations = (
        db.session.query(
            db.func.min(PollingStation.id).label('id'),
            PollingStation.number,
            PollingStation.name,
            PollingStation.location,
            PollingStation.address,
        )
        .filter(PollingStation.municipality_id == municipality_id)
        .group_by(PollingStation.number, PollingStation.name,
                  PollingStation.location, PollingStation.address)
        .order_by(PollingStation.number)
        .all()
    )
    return jsonify([
        {'id': s.id, 'name': f'{s.number}. {s.name}, {s.location}'}
        for s in stations
    ])


@app.route('/api/streets/<int:municipality_id>')
def list_streets(municipality_id):
    streets = (
        db.session.query(PollingStation.address)
        .filter(PollingStation.municipality_id == municipality_id)
        .distinct()
        .order_by(PollingStation.address)
        .all()
    )
    return jsonify([{'name': s.address} for s in streets if s.address])


@app.route('/api/stations-by-street/<int:municipality_id>')
def stations_by_street(municipality_id):
    """Return polling stations that match a given street (address) in a municipality."""
    street = request.args.get('street', '').strip()
    if not street:
        return jsonify([])
    stations = (
        db.session.query(
            db.func.min(PollingStation.id).label('id'),
            PollingStation.number,
            PollingStation.name,
            PollingStation.location,
            PollingStation.address,
        )
        .filter(PollingStation.municipality_id == municipality_id, PollingStation.address == street)
        .group_by(PollingStation.number, PollingStation.name,
                  PollingStation.location, PollingStation.address)
        .order_by(PollingStation.number)
        .all()
    )
    return jsonify([
        {'id': s.id, 'name': f'{s.number}. {s.name}, {s.location}'}
        for s in stations
    ])


@app.route('/api/location-results')
def location_results():
    """Aggregated results for a location filter.
    Params: county_id, municipality_id, station_id (optional), street (optional)
    """
    county_id = request.args.get('county_id', type=int)
    municipality_id = request.args.get('municipality_id', type=int)
    station_id = request.args.get('station_id', type=int)
    street = request.args.get('street', '').strip()

    # Build list of station IDs matching the filter
    query = PollingStation.query

    if station_id:
        # Specific station — find siblings at same location/address
        station = PollingStation.query.get_or_404(station_id)
        query = query.filter_by(location=station.location, address=station.address)
    elif street:
        query = query.filter_by(address=street)
        if municipality_id:
            query = query.filter_by(municipality_id=municipality_id)
    elif municipality_id:
        query = query.filter_by(municipality_id=municipality_id)
    elif county_id:
        muni_ids = [m.id for m in Municipality.query.filter_by(county_id=county_id).all()]
        query = query.filter(PollingStation.municipality_id.in_(muni_ids))
    else:
        return jsonify({'error': 'No filter provided'}), 400

    station_ids = [s.id for s in query.all()]

    if not station_ids:
        return jsonify({'elections': [], 'label': ''})

    # Build label
    if station_id:
        station = PollingStation.query.get(station_id)
        label = f'{station.location}, {station.address}'
    elif street and municipality_id:
        # Show biračko mjesto name(s) for the street, not the street itself
        locations = (
            db.session.query(PollingStation.location, PollingStation.address)
            .filter(PollingStation.municipality_id == municipality_id, PollingStation.address == street)
            .distinct()
            .all()
        )
        if locations:
            label = ', '.join(f'{loc.location}, {loc.address}' for loc in locations)
        else:
            muni = Municipality.query.get(municipality_id)
            label = f'{street}, {muni.name if muni else ""}'
    elif municipality_id:
        muni = Municipality.query.get(municipality_id)
        label = muni.name if muni else ''
    else:
        county = County.query.get(county_id)
        label = county.name if county else ''

    # Aggregate turnout
    turnout_rows = (
        db.session.query(
            ElectionRound.id.label('er_id'),
            db.func.sum(TurnoutData.registered_voters).label('registered_voters'),
            db.func.sum(TurnoutData.ballots_cast).label('ballots_cast'),
            db.func.sum(TurnoutData.valid_ballots).label('valid_ballots'),
            db.func.sum(TurnoutData.invalid_ballots).label('invalid_ballots'),
        )
        .join(ElectionRound, TurnoutData.election_round_id == ElectionRound.id)
        .join(Election, ElectionRound.election_id == Election.id)
        .filter(TurnoutData.polling_station_id.in_(station_ids))
        .group_by(ElectionRound.id)
        .order_by(
            db.func.min(Election.year).desc(),
            db.func.min(Election.date).desc().nullslast(),
            db.func.min(ElectionRound.round_number).desc(),
        )
        .all()
    )

    elections = []
    for td in turnout_rows:
        er = ElectionRound.query.get(td.er_id)
        election = er.election
        etype = election.election_type

        # All lists (no limit)
        all_lists = (
            db.session.query(
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(
                ListResult.polling_station_id.in_(station_ids),
                ElectoralList.election_round_id == er.id,
            )
            .group_by(ElectoralList.name)
            .order_by(db.func.sum(ListResult.votes).desc())
            .limit(5)
            .all()
        )

        # All candidates (no limit)
        all_candidates = (
            db.session.query(
                Person.first_name,
                Person.last_name,
                db.func.sum(CandidateResult.votes).label('total_votes'),
                ElectoralList.name.label('list_name'),
            )
            .join(Candidacy, CandidateResult.candidacy_id == Candidacy.id)
            .join(Person, Candidacy.person_id == Person.id)
            .join(ElectoralList, Candidacy.electoral_list_id == ElectoralList.id)
            .filter(
                CandidateResult.polling_station_id.in_(station_ids),
                ElectoralList.election_round_id == er.id,
            )
            .group_by(Person.first_name, Person.last_name, ElectoralList.name)
            .order_by(db.func.sum(CandidateResult.votes).desc())
            .limit(5)
            .all()
        )

        elections.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': election.date.isoformat() if election.date else None,
            'round': er.round_number,
            'registered_voters': td.registered_voters,
            'ballots_cast': td.ballots_cast,
            'valid_ballots': td.valid_ballots,
            'invalid_ballots': td.invalid_ballots,
            'top_lists': [
                {'name': name, 'votes': votes}
                for name, votes in all_lists
            ],
            'top_candidates': [
                {
                    'name': f'{first} {last}',
                    'votes': votes,
                    'list_name': list_name,
                }
                for first, last, votes, list_name in all_candidates
            ],
        })

    return jsonify({
        'label': label,
        'elections': elections,
    })


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
        scope_station_ids = db.session.query(PollingStation.id).filter(
            PollingStation.id == station_id
        )
        ps = PollingStation.query.get(station_id)
        if ps:
            scope_label = f'{ps.number} — {ps.location or ps.name or ""}'.strip(' —')
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
            'date': election.date.isoformat() if election.date else None,
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

    return jsonify({
        'category': category,
        'year': year,
        'scope_label': scope_label,
        'scope': 'station' if station_id else ('municipality' if muni_id else ('county' if county_id else 'national')),
        'elections': elections,
    })


@app.route('/api/national/sabor-seats/<int:year>')
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
            n_seats = 3  # diaspora
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
                    Person.first_name,
                    Person.last_name,
                    Candidacy.position_on_list,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('personal_votes'),
                )
                .join(Person, Person.id == Candidacy.person_id)
                .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .filter(Candidacy.electoral_list_id == list_id)
                .group_by(Candidacy.id, Person.first_name, Person.last_name, Candidacy.position_on_list)
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
                    'party': group,
                    'district': dist.name,
                })

            for i in range(seats_won - len(chosen)):
                all_candidates.append({
                    'name': group,
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

    return jsonify({
        'year': year,
        'total_seats': 151,
        'parties': seat_list,
        'candidates': ordered_candidates,
        'districts': district_details,
    })


@app.route('/api/national/sabor-raw/<int:year>')
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
            n_seats = 3
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
        scope_station_ids = db.session.query(PollingStation.id).filter(PollingStation.id == station_id)
        ps = PollingStation.query.get(station_id)
        if ps:
            scope_label = f'{ps.number} — {ps.location or ps.name or ""}'.strip(' —')
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
        cand_q.group_by(Candidacy.id, Person.first_name, Person.last_name,
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


# --- Lokalni: per-station list/candidate results ---

# Muni-level kinds map to the ElectionType chosen by the muni's type
# ('grad' → Grad*, 'općina' → Općin*). The two county-level kinds always map
# to a single ElectionType regardless of any muni-type lookup.
LOKALNI_KIND_TO_TYPE = {
    'vijece': {'grad': 'Gradsko vijeće', 'općina': 'Općinsko vijeće'},
    'nacelnik': {'grad': 'Gradonačelnik', 'općina': 'Načelnik'},
}
LOKALNI_COUNTY_KIND_TO_TYPE = {
    'zupan': 'Župan',
    'zup_skupstina': 'Županijska skupština',
}


@app.route('/api/lokalni/station-results')
def lokalni_station_results():
    """Local-election list/candidate results.

    Query params:
      - station_id: PollingStation.id (narrow to one station), OR
      - municipality_id: Municipality.id (aggregate across the whole muni)
      - kind: 'vijece' or 'nacelnik' (required)
      - year: defaults to most recent local-election year
      - round: defaults to 1; 2 only meaningful for nacelnik (mayor runoff)
    """
    station_id = request.args.get('station_id', type=int)
    muni_id = request.args.get('municipality_id', type=int)
    county_id = request.args.get('county_id', type=int)
    kind = (request.args.get('kind') or '').strip()
    year = request.args.get('year', type=int)
    round_num = request.args.get('round', default=1, type=int)

    is_county_kind = kind in LOKALNI_COUNTY_KIND_TO_TYPE
    if not is_county_kind and kind not in LOKALNI_KIND_TO_TYPE:
        valid = list(LOKALNI_KIND_TO_TYPE) + list(LOKALNI_COUNTY_KIND_TO_TYPE)
        return jsonify({'error': f'kind must be one of {valid}'}), 400

    if is_county_kind:
        if not county_id:
            return jsonify({'error': 'county_id required for county-level kind'}), 400
        county = County.query.get(county_id)
        if not county:
            return jsonify({'error': 'county not found'}), 404
        muni = None
        station = None
        type_name = LOKALNI_COUNTY_KIND_TO_TYPE[kind]
    else:
        if not station_id and not muni_id:
            return jsonify({'error': 'station_id or municipality_id required'}), 400
        station = None
        if station_id:
            station = PollingStation.query.get(station_id)
            if not station:
                return jsonify({'error': 'station not found'}), 404
            muni = station.municipality
        else:
            muni = Municipality.query.get(muni_id)
            if not muni:
                return jsonify({'error': 'municipality not found'}), 404
        if not muni or muni.type not in ('grad', 'općina'):
            return jsonify({'error': f'muni type {muni.type if muni else "?"} unsupported for kind={kind}'}), 400
        county = muni.county
        type_name = LOKALNI_KIND_TO_TYPE[kind][muni.type]
    etype = ElectionType.query.filter_by(name=type_name).first()
    if not etype:
        return jsonify({'error': f'no election type "{type_name}"'}), 404

    eq = Election.query.filter_by(election_type_id=etype.id)
    if year:
        eq = eq.filter_by(year=year)
    election = eq.order_by(Election.year.desc()).first()
    if not election:
        return jsonify({'error': f'no election for type "{type_name}" year={year}'}), 404

    er = ElectionRound.query.filter_by(election_id=election.id, round_number=round_num).first()
    if not er:
        return jsonify({'error': f'no round {round_num} for election {election.id}'}), 404

    rounds_available = sorted([
        r.round_number for r in ElectionRound.query.filter_by(election_id=election.id).all()
    ])

    # Vote totals — filtered to whatever stations are in scope.
    if is_county_kind:
        scope_stations = db.session.query(PollingStation.id).join(
            Municipality, Municipality.id == PollingStation.municipality_id
        ).filter(Municipality.county_id == county.id)
    elif station_id:
        scope_stations = db.session.query(PollingStation.id).filter(PollingStation.id == station_id)
    else:
        scope_stations = db.session.query(PollingStation.id).filter(
            PollingStation.municipality_id == muni.id
        )
    list_rows = (
        db.session.query(
            ElectoralList.name,
            db.func.coalesce(db.func.sum(ListResult.votes), 0).label('votes'),
        )
        .outerjoin(ListResult, db.and_(
            ListResult.electoral_list_id == ElectoralList.id,
            ListResult.polling_station_id.in_(scope_stations),
        ))
        .filter(ElectoralList.election_round_id == er.id)
        .group_by(ElectoralList.id, ElectoralList.name)
        .order_by(db.func.sum(ListResult.votes).desc().nullslast())
        .all()
    )
    total = sum(r.votes or 0 for r in list_rows)
    items = [{
        'name': r.name,
        'votes': int(r.votes or 0),
        'votes_pct': (r.votes / total * 100.0) if total else 0.0,
    } for r in list_rows]

    # Turnout — uses the same station-scope subquery as votes.
    if station_id and not is_county_kind:
        turnout_row = TurnoutData.query.filter_by(
            election_round_id=er.id, polling_station_id=station_id
        ).first()
        turnout_data = {
            'registered_voters': turnout_row.registered_voters if turnout_row else 0,
            'ballots_cast': turnout_row.ballots_cast if turnout_row else 0,
            'valid_ballots': turnout_row.valid_ballots if turnout_row else 0,
            'invalid_ballots': turnout_row.invalid_ballots if turnout_row else 0,
        } if turnout_row else None
    else:
        agg_q = (
            db.session.query(
                db.func.coalesce(db.func.sum(TurnoutData.registered_voters), 0),
                db.func.coalesce(db.func.sum(TurnoutData.ballots_cast), 0),
                db.func.coalesce(db.func.sum(TurnoutData.valid_ballots), 0),
                db.func.coalesce(db.func.sum(TurnoutData.invalid_ballots), 0),
            )
            .join(PollingStation, PollingStation.id == TurnoutData.polling_station_id)
            .filter(TurnoutData.election_round_id == er.id)
        )
        if is_county_kind:
            agg_q = agg_q.join(Municipality, Municipality.id == PollingStation.municipality_id) \
                         .filter(Municipality.county_id == county.id)
        else:
            agg_q = agg_q.filter(PollingStation.municipality_id == muni.id)
        agg = agg_q.first()
        turnout_data = {
            'registered_voters': int(agg[0] or 0),
            'ballots_cast': int(agg[1] or 0),
            'valid_ballots': int(agg[2] or 0),
            'invalid_ballots': int(agg[3] or 0),
        } if agg else None

    # Per-station turnout breakdown — only for non-station scopes. For
    # county-level kinds, list every station in the county; for muni scopes,
    # only that muni's stations.
    stations_breakdown = None
    if is_county_kind or not station_id:
        sb_q = (
            db.session.query(
                PollingStation.id,
                PollingStation.number,
                PollingStation.name,
                PollingStation.location,
                PollingStation.address,
                db.func.coalesce(TurnoutData.registered_voters, 0),
                db.func.coalesce(TurnoutData.ballots_cast, 0),
                db.func.coalesce(TurnoutData.valid_ballots, 0),
                db.func.coalesce(TurnoutData.invalid_ballots, 0),
            )
            .outerjoin(TurnoutData, db.and_(
                TurnoutData.polling_station_id == PollingStation.id,
                TurnoutData.election_round_id == er.id,
            ))
        )
        if is_county_kind:
            sb_q = sb_q.join(Municipality, Municipality.id == PollingStation.municipality_id) \
                       .filter(Municipality.county_id == county.id)
        else:
            sb_q = sb_q.filter(PollingStation.municipality_id == muni.id)
        sb_rows = sb_q.order_by(PollingStation.number).all()
        stations_breakdown = [{
            'id': r[0],
            'number': r[1],
            'name': r[2] or '',
            'location': r[3] or '',
            'address': r[4] or '',
            'registered_voters': int(r[5] or 0),
            'ballots_cast': int(r[6] or 0),
            'valid_ballots': int(r[7] or 0),
            'invalid_ballots': int(r[8] or 0),
            'turnout_pct': (float(r[6]) / float(r[5]) * 100.0) if (r[5] and r[5] > 0) else 0.0,
        } for r in sb_rows]

    if is_county_kind:
        scope_kind = 'county'
    elif station_id:
        scope_kind = 'station'
    else:
        scope_kind = 'municipality'

    return jsonify({
        'scope': scope_kind,
        'station_id': station_id,
        'station_label': f'{station.number} — {station.location or station.name or ""}'.strip(' —') if station else None,
        'station_address': (station.address if station else '') or '',
        'municipality': muni.name if muni else None,
        'municipality_type': muni.type if muni else None,
        'county': county.name if county else '',
        'kind': kind,
        'election_type': type_name,
        'year': election.year,
        'round': round_num,
        'rounds_available': rounds_available,
        'total_votes': total,
        'turnout': turnout_data,
        'items': items,
        'stations': stations_breakdown,
    })


# --- Analytics: Izlaznost (turnout) ---

ANALYTICS_CATEGORIES = {
    'predsjednicki': {
        'label': 'Predsjednički izbori',
        'short': 'Predsjednički',
        'types': ['Predsjednički izbori'],
    },
    'sabor': {
        'label': 'Parlamentarni izbori (Sabor)',
        'short': 'Sabor',
        'types': ['Parlamentarni izbori'],
    },
    'eu': {
        'label': 'EU parlamentarni izbori',
        'short': 'EU parlament',
        'types': ['Izbori za Europski parlament'],
    },
    'lokalni': {
        'label': 'Lokalni izbori',
        'short': 'Lokalni',
        'types': [
            'Župan', 'Županijska skupština', 'Gradonačelnik',
            'Gradsko vijeće', 'Načelnik', 'Općinsko vijeće',
            'Zamjenik župana', 'Zamjenik načelnika', 'Zamjenik gradonačelnika',
            'Local',
        ],
        # Per-round canonical types for turnout. Each voter participates in
        # multiple local races simultaneously (assembly + executive +
        # municipal/city council), so summing all types double-counts. The
        # canonical pairs below are mutually exclusive at the polling-station
        # level — every Croatian polling place is in exactly one općina or
        # one grad, never both — so summing them gives the true electorate.
        'canonical_types_by_round': {
            1: ['Općinsko vijeće', 'Gradsko vijeće'],
            2: ['Načelnik', 'Gradonačelnik'],
        },
    },
}


def _category_for_type(type_name):
    for key, cat in ANALYTICS_CATEGORIES.items():
        if type_name in cat['types']:
            return key
    return None


@app.route('/api/analytics/elections')
def analytics_elections():
    """List all election rounds available for the Izlaznost filter UI."""
    rows = (
        db.session.query(
            ElectionRound.id,
            ElectionRound.round_number,
            Election.id,
            Election.year,
            Election.name,
            Election.date,
            ElectionType.name,
        )
        .join(Election, ElectionRound.election_id == Election.id)
        .join(ElectionType, Election.election_type_id == ElectionType.id)
        .order_by(Election.year.desc(), ElectionType.name, ElectionRound.round_number)
        .all()
    )

    # Group by (category, year, round_number) — collapses local-election sub-types
    # (Općinsko vijeće + Gradsko vijeće) into a single "Lokalni 2025" filter card.
    # For categories with `canonical_types_by_round`, only canonical types
    # contribute to the turnout aggregation (avoids double-counting voters
    # who participate in multiple simultaneous local races).
    grouped = {}
    for er_id, round_num, el_id, year, el_name, el_date, type_name in rows:
        cat = _category_for_type(type_name)
        if not cat:
            continue
        canonical = ANALYTICS_CATEGORIES[cat].get('canonical_types_by_round')
        if canonical is not None and type_name not in canonical.get(round_num, []):
            continue
        key = (cat, year, round_num)
        if key not in grouped:
            grouped[key] = {
                'category': cat,
                'category_label': ANALYTICS_CATEGORIES[cat]['short'],
                'year': year,
                'round_number': round_num,
                'round_ids': [],
                'date': el_date.isoformat() if el_date else None,
            }
        grouped[key]['round_ids'].append(er_id)
        if el_date and (grouped[key]['date'] is None or el_date.isoformat() < grouped[key]['date']):
            grouped[key]['date'] = el_date.isoformat()

    result = sorted(
        grouped.values(),
        key=lambda g: (-g['year'], g['category'], g['round_number']),
    )
    for i, g in enumerate(result):
        g['id'] = f"{g['category']}-{g['year']}-{g['round_number']}"
        round_suffix = f" — {g['round_number']}. krug" if g['round_number'] > 1 else ""
        g['label'] = f"{g['category_label']} {g['year']}{round_suffix}"
    return jsonify(result)


@app.route('/api/analytics/turnout')
def analytics_turnout():
    """Aggregated turnout per filter group at the requested geo level.

    Query params:
      - groups: comma-separated filter ids from /api/analytics/elections
      - level: national | county | municipality | station
      - parent_id: county.id (when level=municipality) or municipality.id (when level=station)
    """
    groups_param = request.args.get('groups', '').strip()
    level = request.args.get('level', 'national').strip()
    parent_id = request.args.get('parent_id', type=int)

    if not groups_param:
        return jsonify({'level': level, 'parent_id': parent_id, 'groups': []})

    # Resolve filter ids back to round-id sets via /elections data
    elections_resp = analytics_elections().get_json()
    by_id = {g['id']: g for g in elections_resp}
    selected = [by_id[gid] for gid in groups_param.split(',') if gid in by_id]
    if not selected:
        return jsonify({'level': level, 'parent_id': parent_id, 'groups': []})

    if level == 'national':
        groups_out = []
        for g in selected:
            row = (
                db.session.query(
                    db.func.sum(TurnoutData.registered_voters),
                    db.func.sum(TurnoutData.ballots_cast),
                    db.func.sum(TurnoutData.valid_ballots),
                    db.func.sum(TurnoutData.invalid_ballots),
                )
                .filter(TurnoutData.election_round_id.in_(g['round_ids']))
                .first()
            )
            groups_out.append({
                'id': g['id'],
                'label': g['label'],
                'category': g['category'],
                'year': g['year'],
                'round_number': g['round_number'],
                'rows': [{
                    'id': 'hr',
                    'name': 'Hrvatska',
                    'registered': row[0] or 0,
                    'cast': row[1] or 0,
                    'valid': row[2] or 0,
                    'invalid': row[3] or 0,
                }],
            })
        return jsonify({'level': level, 'parent_id': parent_id, 'groups': groups_out})

    if level == 'county':
        # All counties for each group
        groups_out = []
        for g in selected:
            rows = (
                db.session.query(
                    County.id, County.name,
                    db.func.sum(TurnoutData.registered_voters),
                    db.func.sum(TurnoutData.ballots_cast),
                    db.func.sum(TurnoutData.valid_ballots),
                    db.func.sum(TurnoutData.invalid_ballots),
                )
                .join(Municipality, Municipality.county_id == County.id)
                .join(PollingStation, PollingStation.municipality_id == Municipality.id)
                .join(TurnoutData, TurnoutData.polling_station_id == PollingStation.id)
                .filter(TurnoutData.election_round_id.in_(g['round_ids']))
                .group_by(County.id, County.name)
                .order_by(County.name)
                .all()
            )
            groups_out.append({
                'id': g['id'], 'label': g['label'], 'category': g['category'],
                'year': g['year'], 'round_number': g['round_number'],
                'rows': [{
                    'id': r[0], 'name': r[1],
                    'registered': r[2] or 0, 'cast': r[3] or 0,
                    'valid': r[4] or 0, 'invalid': r[5] or 0,
                } for r in rows],
            })
        return jsonify({'level': level, 'parent_id': parent_id, 'groups': groups_out})

    if level == 'municipality':
        if not parent_id:
            return jsonify({'error': 'parent_id (county) required'}), 400
        groups_out = []
        for g in selected:
            rows = (
                db.session.query(
                    Municipality.id, Municipality.name,
                    db.func.sum(TurnoutData.registered_voters),
                    db.func.sum(TurnoutData.ballots_cast),
                    db.func.sum(TurnoutData.valid_ballots),
                    db.func.sum(TurnoutData.invalid_ballots),
                )
                .join(PollingStation, PollingStation.municipality_id == Municipality.id)
                .join(TurnoutData, TurnoutData.polling_station_id == PollingStation.id)
                .filter(
                    TurnoutData.election_round_id.in_(g['round_ids']),
                    Municipality.county_id == parent_id,
                )
                .group_by(Municipality.id, Municipality.name)
                .order_by(Municipality.name)
                .all()
            )
            groups_out.append({
                'id': g['id'], 'label': g['label'], 'category': g['category'],
                'year': g['year'], 'round_number': g['round_number'],
                'rows': [{
                    'id': r[0], 'name': r[1],
                    'registered': r[2] or 0, 'cast': r[3] or 0,
                    'valid': r[4] or 0, 'invalid': r[5] or 0,
                } for r in rows],
            })
        return jsonify({'level': level, 'parent_id': parent_id, 'groups': groups_out})

    if level == 'station':
        # Either parent_id (= municipality.id, returns all stations in muni) OR
        # station_ids (= explicit comma-separated list, used by the multi-station
        # comparison flow which can span multiple municipalities) is required.
        station_ids_param = request.args.get('station_ids', '').strip()
        explicit_ids = None
        if station_ids_param:
            try:
                explicit_ids = [int(x) for x in station_ids_param.split(',') if x.strip()]
            except ValueError:
                return jsonify({'error': 'Invalid station_ids'}), 400
            if not explicit_ids:
                return jsonify({'level': level, 'station_ids': [], 'groups': []})
        elif not parent_id:
            return jsonify({'error': 'parent_id (municipality) or station_ids required'}), 400

        groups_out = []
        for g in selected:
            q = (
                db.session.query(
                    PollingStation.id,
                    PollingStation.number,
                    PollingStation.name,
                    PollingStation.location,
                    PollingStation.address,
                    db.func.sum(TurnoutData.registered_voters),
                    db.func.sum(TurnoutData.ballots_cast),
                    db.func.sum(TurnoutData.valid_ballots),
                    db.func.sum(TurnoutData.invalid_ballots),
                )
                .join(TurnoutData, TurnoutData.polling_station_id == PollingStation.id)
                .filter(TurnoutData.election_round_id.in_(g['round_ids']))
            )
            if explicit_ids is not None:
                q = q.filter(PollingStation.id.in_(explicit_ids))
            else:
                q = q.filter(PollingStation.municipality_id == parent_id)
            rows = (
                q.group_by(
                    PollingStation.id, PollingStation.number,
                    PollingStation.name, PollingStation.location, PollingStation.address,
                )
                .order_by(PollingStation.number)
                .all()
            )
            groups_out.append({
                'id': g['id'], 'label': g['label'], 'category': g['category'],
                'year': g['year'], 'round_number': g['round_number'],
                'rows': [{
                    'id': r[0],
                    'name': f"{r[1]} — {r[3] or r[2] or ''}".strip(' —'),
                    'address': r[4] or '',
                    'registered': r[5] or 0, 'cast': r[6] or 0,
                    'valid': r[7] or 0, 'invalid': r[8] or 0,
                } for r in rows],
            })
        out = {'level': level, 'groups': groups_out}
        if explicit_ids is not None:
            out['station_ids'] = explicit_ids
        else:
            out['parent_id'] = parent_id
        return jsonify(out)

    return jsonify({'error': f'Unknown level: {level}'}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5001)
