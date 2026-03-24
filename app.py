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

        vote_share = round((total_votes / total_valid_ballots) * 100, 1) if total_valid_ballots > 0 else 0

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
        .order_by(db.func.min(Election.date), db.func.min(ElectionRound.round_number))
        .all()
    )

    elections = []
    for td in turnout_rows:
        er = ElectionRound.query.get(td.er_id)
        election = er.election
        etype = election.election_type

        # Get top 5 lists by votes across all sibling stations
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

        # Also get top 5 candidates if available
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


if __name__ == '__main__':
    app.run(debug=True, port=5001)
