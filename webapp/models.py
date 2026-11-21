"""SQLAlchemy models of the tables Django owns (elections_*).

The schema lives in the Django app (`elections/models/`): a new column is
added there, migrated, and mirrored here, or Flask reads fail.
"""

from webapp.core import db


# Models — reflect the existing Django tables

class Person(db.Model):
    __tablename__ = 'elections_person'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    normalized_name = db.Column(db.String)
    disambiguation = db.Column(db.String)
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
    residence = db.Column(db.String)
    electoral_list = db.relationship('ElectoralList', backref='candidacies', lazy=True)


class ListHolder(db.Model):
    """Nositelj liste of a council list in one municipality (2001-2009);
    mirrors the Django model, see participants.py."""
    __tablename__ = 'elections_listholder'
    id = db.Column(db.Integer, primary_key=True)
    electoral_list_id = db.Column(db.Integer, db.ForeignKey('elections_electorallist.id'))
    municipality_id = db.Column(db.Integer, db.ForeignKey('elections_municipality.id'))
    person_id = db.Column(db.Integer, db.ForeignKey('elections_person.id'))
    printed_name = db.Column(db.String)


class RegisteredParty(db.Model):
    """A party in the official register; mirrors the Django model, see
    participants.py."""
    __tablename__ = 'elections_registeredparty'
    id = db.Column(db.Integer, primary_key=True)
    registry_number = db.Column(db.Integer)
    name = db.Column(db.String)
    short_name = db.Column(db.String)
    oib = db.Column(db.String)
    seat = db.Column(db.String)
    status = db.Column(db.String)
    registered_on = db.Column(db.Date)
    status_on = db.Column(db.Date)


class ElectedMandate(db.Model):
    __tablename__ = 'elections_electedmandate'
    id = db.Column(db.Integer, primary_key=True)
    candidacy_id = db.Column(db.Integer, db.ForeignKey('elections_candidacy.id'))
    group = db.Column(db.String)


class ParliamentMember(db.Model):
    __tablename__ = 'elections_parliamentmember'
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections_election.id'))
    person_id = db.Column(db.Integer, db.ForeignKey('elections_person.id'))
    party = db.Column(db.String)
    minority = db.Column(db.Boolean)
    note = db.Column(db.String)
    candidacy_id = db.Column(db.Integer, db.ForeignKey('elections_candidacy.id'))
    district_id = db.Column(db.Integer, db.ForeignKey('elections_electoraldistrict.id'))
    district = db.relationship('ElectoralDistrict', lazy=True)
    person = db.relationship('Person', backref='parliament_memberships', lazy=True)


class ElectionRound(db.Model):
    __tablename__ = 'elections_electionround'
    id = db.Column(db.Integer, primary_key=True)
    round_number = db.Column(db.Integer)
    date = db.Column(db.Date)
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
    # Districts are per election — the same number means a different area in
    # different years, and 1997's are counties rather than izborne jedinice.
    election_id = db.Column(db.Integer, db.ForeignKey('elections_election.id'))
    # Published per-contest electorate (1992/1995 districts) — display only.
    registered_voters = db.Column(db.Integer)
    ballots_cast = db.Column(db.Integer)
    invalid_ballots = db.Column(db.Integer)


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
