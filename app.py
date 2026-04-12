from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy

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


@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'person')

    if len(q) < 2:
        return jsonify([])

    if search_type == 'person':
        # Search by normalized name (uppercase, no diacritics) for better matching
        normalized_q = q.upper()
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
        parties = (
            Party.query
            .filter(
                db.or_(
                    Party.name.ilike(f'%{q}%'),
                    Party.short_name.ilike(f'%{q}%')
                )
            )
            .order_by(Party.name)
            .limit(20)
            .all()
        )
        return jsonify([
            {'id': p.id, 'name': f'{p.short_name} — {p.name}' if p.short_name else p.name}
            for p in parties
        ])
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
        .order_by(Election.date.desc(), ElectionRound.round_number.desc())
        .all()
    )

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

        vote_share = round((total_votes / total_valid_ballots) * 100) if total_valid_ballots > 0 else 0

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
        })

    return jsonify({
        'id': person.id,
        'first_name': person.first_name,
        'last_name': person.last_name,
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
        .order_by(Election.date.desc(), ElectionRound.round_number.desc())
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
        .order_by(db.func.min(Election.date).desc(), db.func.min(ElectionRound.round_number).desc())
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
    counties = County.query.order_by(County.name).all()
    return jsonify([{'id': c.id, 'name': c.name} for c in counties])


@app.route('/api/municipalities/<int:county_id>')
def list_municipalities(county_id):
    munis = (
        Municipality.query
        .filter_by(county_id=county_id)
        .order_by(Municipality.name)
        .all()
    )
    return jsonify([{'id': m.id, 'name': m.name} for m in munis])


@app.route('/api/polling-stations/<int:municipality_id>')
def list_polling_stations(municipality_id):
    stations = (
        db.session.query(
            db.func.min(PollingStation.id).label('id'),
            PollingStation.location,
            PollingStation.address,
        )
        .filter(PollingStation.municipality_id == municipality_id)
        .group_by(PollingStation.location, PollingStation.address)
        .order_by(PollingStation.location)
        .all()
    )
    return jsonify([
        {'id': s.id, 'name': f'{s.location}, {s.address}'}
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
            PollingStation.location,
            PollingStation.address,
        )
        .filter(PollingStation.municipality_id == municipality_id, PollingStation.address == street)
        .group_by(PollingStation.location, PollingStation.address)
        .order_by(PollingStation.location)
        .all()
    )
    return jsonify([
        {'id': s.id, 'name': f'{s.location}, {s.address}'}
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
        .order_by(db.func.min(Election.date).desc(), db.func.min(ElectionRound.round_number).desc())
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
    """Return national-level aggregated results for a category and year."""
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

    # Find election rounds
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

        # Aggregate turnout nationally
        turnout = db.session.query(
            db.func.sum(TurnoutData.registered_voters),
            db.func.sum(TurnoutData.ballots_cast),
            db.func.sum(TurnoutData.valid_ballots),
            db.func.sum(TurnoutData.invalid_ballots),
        ).filter(TurnoutData.election_round_id == er.id).first()

        registered = turnout[0] or 0
        ballots = turnout[1] or 0
        valid = turnout[2] or 0
        invalid = turnout[3] or 0

        # Top lists (all, no limit for national view)
        top_lists = (
            db.session.query(
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(ElectoralList.election_round_id == er.id)
            .group_by(ElectoralList.name)
            .order_by(db.func.sum(ListResult.votes).desc())
            .all()
        )

        # Top candidates
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
            .filter(ElectoralList.election_round_id == er.id)
            .group_by(Person.first_name, Person.last_name, ElectoralList.name)
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

        # Get candidates for lists that won seats
        for list_name, seats_won in dist_seats.items():
            list_id = list_id_map.get(list_name)
            if not list_id or seats_won == 0:
                continue

            candidates = (
                db.session.query(Person.first_name, Person.last_name, Candidacy.position_on_list)
                .join(Candidacy, Person.id == Candidacy.person_id)
                .filter(Candidacy.electoral_list_id == list_id)
                .order_by(Candidacy.position_on_list)
                .limit(seats_won)
                .all()
            )

            is_minority = dist.number in MINORITY_SEATS
            group = 'NACIONALNE MANJINE' if is_minority else primary_party(list_name)
            for c in candidates:
                all_candidates.append({
                    'name': f"{c.first_name} {c.last_name}",
                    'party': group,
                    'district': dist.name,
                })

            for i in range(seats_won - len(candidates)):
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
                        'group': w['name'], 'fixed_seats': w['seats']}
                       for w in minority_winners],
            'minority': True,
        })

    return jsonify({
        'year': year,
        'districts': result_districts,
    })


if __name__ == '__main__':
    app.run(debug=True, port=5001)
