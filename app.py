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
    else:
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
        .order_by(Election.year.desc())
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

        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'round': er.round_number,
            'list_name': el.name,
            'position': c.position_on_list,
            'district': el.district.name if el.district else None,
            'candidate_votes': total_votes,
            'list_votes': total_list_votes,
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
        .order_by(Election.year.desc())
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
