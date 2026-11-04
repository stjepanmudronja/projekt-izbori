import re
import time
from collections import defaultdict

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy

from elections.importers.name_utils import normalize_person_name, place_key, strip_diacritics

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


# Routes

@app.after_request
def _no_store(resp):
    """Keep the browser from caching the app or its data.

    Flask sets no Cache-Control on a rendered template or on jsonify, which
    leaves both free to be cached. Two things then go wrong, and both look
    exactly like a missing feature rather than a caching problem: the 350KB
    SPA shell — all the markup and JS, rewritten with every change — keeps
    running against a newer API, and a year list fetched once keeps a newly
    imported year out of the picker. Nothing here is static: every response
    reflects the current import state. Only /static/ assets stay cacheable.
    """
    if not request.path.startswith('/static/'):
        resp.headers.setdefault('Cache-Control', 'no-store, must-revalidate')
    return resp


@app.route('/')
def index():
    return render_template('index.html')


# Pretty URLs per sidebar tab — the SPA reads window.location to switch tabs.
# Restricted to a known whitelist so we don't accidentally swallow /api/...
# or static asset paths.
SPA_ROUTES = {
    'politicar', 'stranka', 'prema-lokaciji', 'usporedba',
    'predsjednicki-izbori', 'eu-parlamentarni-izbori', 'lokalni-izbori',
    'rezultati-koalicije-sabor', 'zupanijski-dom', 'izlaznost', 'karta',
}


@app.route('/<slug>')
def spa_route(slug):
    if slug in SPA_ROUTES:
        return render_template('index.html')
    return ('Not Found', 404)


def person_labels(persons):
    """Person id -> the label that tells namesakes apart, for persons whose
    name another Person row shares (see `split_persons`).

    A carved-off namesake carries its curated `disambiguation`; the unlabelled
    row every import matches is labelled by the years it holds instead, so
    "Ante Jelavić (2024.)" reads beside "Ante Jelavić (Split, 1990.)". A person
    with no namesake gets no entry.
    """
    names = {p.normalized_name for p in persons}
    if not names:
        return {}
    shared = {n for n, count in (
        db.session.query(Person.normalized_name, db.func.count(Person.id))
        .filter(Person.normalized_name.in_(names))
        .group_by(Person.normalized_name).all()) if count > 1}
    labels = {}
    for p in persons:
        if p.normalized_name not in shared:
            continue
        if p.disambiguation:
            labels[p.id] = p.disambiguation
            continue
        years = sorted({y for (y,) in (
            db.session.query(Election.year)
            .join(ElectionRound, ElectionRound.election_id == Election.id)
            .join(ElectoralList, ElectoralList.election_round_id == ElectionRound.id)
            .join(Candidacy, Candidacy.electoral_list_id == ElectoralList.id)
            .filter(Candidacy.person_id == p.id).distinct())})
        if years:
            labels[p.id] = (f'{years[0]}.' if years[0] == years[-1]
                            else f'{years[0]}.–{years[-1]}.')
    return labels


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
        labels = person_labels(persons)
        return jsonify([
            {'id': p.id, 'name': f'{p.first_name} {p.last_name}',
             'label': labels.get(p.id, '')}
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


def round_date_iso(er, election=None):
    """ISO polling date for a result badge, preferring the round's own date.

    A runoff is held weeks after the first round and can fall in the next
    calendar year (2019 presidential: 22 Dec 2019, runoff 5 Jan 2020), so the
    election-level date is only correct for round 1. Falls back to it for
    elections whose rounds predate `set_election_dates`, and returns None when
    neither is known — the frontend then shows the bare year.
    """
    if er is not None and er.date:
        return er.date.isoformat()
    if election is None:
        election = er.election if er is not None else None
    if election is not None and election.date:
        return election.date.isoformat()
    return None


# Diaspora (district XI) did not have a fixed seat count before 2011: the law
# converted diaspora votes at the domestic votes-per-seat rate, which gave 5
# seats in 2007. From 2011 on it is a fixed 3. Everything else has been stable
# across every year we import — 14 seats per district I-X, 8 for the minorities.
DIASPORA_SEATS_BY_YEAR = {2000: 6, 2003: 4, 2007: 5}

# District XII returned 5 members under the 1999 law and 8 from 2003 on.
MINORITY_SEATS_BY_YEAR = {2000: 5}

# Years whose imported results do not cover every electoral district, and what
# is missing. Turnout for such a year is not the national figure — 2000 is
# short district XI's ~400k diaspora voters — so anything presenting it as
# "Hrvatska" has to say so, or the number reads as simply wrong against the
# published total (4,046,488 registered against our 3,646,455).
# 1997's mixed system: besides the list part, each council and county
# assembly had single-member wards, stored as their own election types so
# ward votes never add into a list total (see local_1997.py).
LOKALNI_WARD_TYPES = {
    'vijece_ij': 'Vijeće — izborne jedinice',
    'zup_skupstina_ij': 'Županijska skupština — izborne jedinice',
}

# Elections whose per-station files give only the station's number, no name
# or address. A place shows one only where its town's number always meant
# that place (`rekey_stations`); elsewhere it counts in the town total only.
NUMBER_ONLY_ELECTIONS = [
    ('presidential', 2000, 'Predsjednički izbori 2000.'),
    ('presidential', 2005, 'Predsjednički izbori 2005.'),
    ('presidential', 2009, 'Predsjednički izbori 2009.'),
    ('sabor', 2000, 'Parlamentarni izbori 2000.'),
    ('sabor', 2003, 'Parlamentarni izbori 2003.'),
    ('sabor', 2007, 'Parlamentarni izbori 2007.'),
]

INCOMPLETE_COVERAGE = {
    ('sabor', 2000): 'bez XI. i XII. IJ',
    # 1995 has no per-station export at all — DIP published only summary
    # figures — so county, municipality and station views are empty for it.
    ('sabor', 1995): 'samo državni zbroj',
    # 1992 likewise: one decision per contest plus the list vote per unit.
    ('sabor', 1992): 'samo državni zbroj',
    # 1990: one figure per unit and round; the 2. krug covers only the 51
    # units that needed one.
    ('sabor_dpv', 1990): 'samo zbroj po izbornim jedinicama',
    ('sabor_vo', 1990): 'samo zbroj po izbornim jedinicama',
    ('sabor_vur', 1990): 'samo zbroj po izbornim jedinicama',
    # Lokalni 2009 exists only as DIP's PDF report: one figure per
    # municipality (and per county for its own contests), no stations.
    ('lokalni', 2009): 'samo zbroj po gradu/općini',
    ('lokalni', 2005): 'samo zbroj po gradu/općini',
    ('lokalni', 2001): 'samo zbroj po gradu/općini',
    ('lokalni', 1997): 'samo zbroj po gradu/općini',
    ('lokalni', 1993): 'samo zbroj po gradu/općini',
}

# The 1990 Sabor's chambers, each its own election type: key (as in the URL)
# -> slug, ElectionType.name and the chamber's short title. All are single-
# member units decided by majority over up to two rounds, with every winner
# stored as a ParliamentMember, so they share one endpoint and one seat rule.
SABOR_1990_CHAMBERS = {
    'dpv': ('sabor_dpv', 'Društveno-političko vijeće Sabora', 'Društveno-političko vijeće'),
    'vo': ('sabor_vo', 'Vijeće općina Sabora', 'Vijeće općina'),
    'vur': ('sabor_vur', 'Vijeće udruženog rada Sabora', 'Vijeće udruženog rada'),
}
SABOR_1990_SLUGS = {slug for slug, _n, _t in SABOR_1990_CHAMBERS.values()}
SABOR_1990_TYPE_NAMES = {name for _s, name, _t in SABOR_1990_CHAMBERS.values()}


def diaspora_seats(year):
    return DIASPORA_SEATS_BY_YEAR.get(year, 3)


def minority_seats(year):
    return MINORITY_SEATS_BY_YEAR.get(year, 8)


def sabor_total_seats(year):
    return 140 + diaspora_seats(year) + minority_seats(year)


# Cache of Sabor seat winners per election round (data is static after import).
_SABOR_SEAT_WINNERS_CACHE = {}


def sabor_seat_winner_candidacy_ids(er_id):
    """Return the set of Candidacy.id that won a Sabor seat in this round.

    Mirrors the D'Hondt + preferential-vote allocation in sabor_seats() but
    tracks the chosen candidacies at the individual level so the politician
    page can flag who actually entered the Sabor."""
    if er_id in _SABOR_SEAT_WINNERS_CACHE:
        return _SABOR_SEAT_WINNERS_CACHE[er_id]

    MINORITY_SEATS = {121: 3, 122: 1, 123: 1, 124: 1, 125: 1, 126: 1}
    PREF_THRESHOLD_PCT = 10.0
    winner_ids = set()
    year = (
        db.session.query(Election.year)
        .join(ElectionRound, ElectionRound.election_id == Election.id)
        .filter(ElectionRound.id == er_id)
        .scalar()
    )

    # 1995 is not allocated, it is recorded. That year ran 28 single-member
    # plurality districts, a countrywide list and 5 minority units — none of
    # which this D'Hondt pass models (it would hand every district 14 seats) —
    # and the DIP report names all 127 members, so the winners come straight
    # off the stored ParliamentMember rows. 1992 is the same story under a
    # different mix: 60 list seats, 60 single-member districts, 4 minority
    # units and 14 members taken from the lists, all 138 named in the report.
    etype_slug = (
        db.session.query(ElectionType.slug)
        .join(Election, Election.election_type_id == ElectionType.id)
        .join(ElectionRound, ElectionRound.election_id == Election.id)
        .filter(ElectionRound.id == er_id)
        .scalar()
    )
    # The 1990 chambers are majority races in single-member units (80 for the
    # Društveno-političko vijeće, 115 for the Vijeće općina, 160 for the
    # Vijeće udruženog rada), and their
    # winners are stored the same way.
    if year in (1992, 1995) or etype_slug in SABOR_1990_SLUGS:
        winner_ids = {
            cid for (cid,) in
            db.session.query(ParliamentMember.candidacy_id)
            .join(Election, Election.id == ParliamentMember.election_id)
            .join(ElectionRound, ElectionRound.election_id == Election.id)
            .filter(ElectionRound.id == er_id,
                    ParliamentMember.candidacy_id.isnot(None))
            .all()
        }
        _SABOR_SEAT_WINNERS_CACHE[er_id] = winner_ids
        return winner_ids

    districts = (
        db.session.query(ElectoralDistrict)
        .join(ElectoralList, ElectoralList.district_id == ElectoralDistrict.id)
        .filter(ElectoralList.election_round_id == er_id)
        .distinct()
        .all()
    )

    for dist in districts:
        if dist.number in MINORITY_SEATS:
            n_seats = MINORITY_SEATS[dist.number]
        elif dist.number == 11:
            n_seats = diaspora_seats(year)
        elif dist.number == 12:
            n_seats = 8
        else:
            n_seats = 14

        list_rows = (
            db.session.query(
                ElectoralList.id,
                ElectoralList.name,
                db.func.sum(ListResult.votes).label('total_votes'),
            )
            .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
            .filter(
                ElectoralList.election_round_id == er_id,
                ElectoralList.district_id == dist.id,
            )
            .group_by(ElectoralList.id, ElectoralList.name)
            .all()
        )
        if not list_rows:
            continue

        list_votes = [(r.name, r.total_votes) for r in list_rows]
        list_id_map = {r.name: r.id for r in list_rows}
        total_district_votes = sum(v for _, v in list_votes)

        is_standard = n_seats == 14
        if is_standard:
            threshold = total_district_votes * 0.05
            eligible = [(name, votes) for name, votes in list_votes if votes >= threshold]
        else:
            eligible = list(list_votes)

        quotients = []
        for list_name, votes in eligible:
            for divisor in range(1, n_seats + 1):
                quotients.append((votes / divisor, list_name))
        quotients.sort(key=lambda x: -x[0])
        seat_winners = quotients[:n_seats]

        dist_seats = {}
        for _, list_name in seat_winners:
            dist_seats[list_name] = dist_seats.get(list_name, 0) + 1

        list_votes_by_name = {name: votes for name, votes in list_votes}

        for list_name, seats_won in dist_seats.items():
            list_id = list_id_map.get(list_name)
            if not list_id or seats_won == 0:
                continue

            cand_rows = (
                db.session.query(
                    Candidacy.id,
                    Candidacy.position_on_list,
                    db.func.coalesce(db.func.sum(CandidateResult.votes), 0).label('personal_votes'),
                )
                .outerjoin(CandidateResult, CandidateResult.candidacy_id == Candidacy.id)
                .filter(Candidacy.electoral_list_id == list_id)
                .group_by(Candidacy.id, Candidacy.position_on_list)
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
                chosen.append(c.id)
                seen.add(c.id)
            for c in sorted(cand_rows, key=lambda c: (c.position_on_list or 0)):
                if len(chosen) >= seats_won:
                    break
                if c.id in seen:
                    continue
                chosen.append(c.id)
                seen.add(c.id)
            winner_ids.update(chosen)

    _SABOR_SEAT_WINNERS_CACHE[er_id] = winner_ids
    return winner_ids


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
    # The 1990 chambers are a head-to-head race per unit and per round, so
    # they rank like a presidential round within its district.
    RANK_BY_DISTRICT = {'Predsjednički izbori'} | SABOR_1990_TYPE_NAMES | set(LOKALNI_WARD_TYPES.values())
    RANK_BY_MUNI = {'Gradonačelnik', 'Načelnik'}
    RANK_BY_COUNTY = {'Župan'}
    LOKALNI_EXEC = RANK_BY_MUNI | RANK_BY_COUNTY
    # Maps election_type.name → kind key used by the lokalni results module
    # dropdown (selLokKind). Used to deep-link from a politician's badge/chart
    # point straight into the matching scope (county / muni + kind).
    LOKALNI_KIND_MAP = {
        'Gradonačelnik': 'nacelnik',
        'Načelnik': 'nacelnik',
        'Gradsko vijeće': 'vijece',
        'Općinsko vijeće': 'vijece',
        'Kotarska skupština': 'vijece',
        'Župan': 'zupan',
        'Županijska skupština': 'zup_skupstina',
        LOKALNI_WARD_TYPES['vijece_ij']: 'vijece_ij',
        LOKALNI_WARD_TYPES['zup_skupstina_ij']: 'zup_skupstina_ij',
    }
    ALL_LOKALNI = set(LOKALNI_KIND_MAP.keys())

    # For lokalni we need the muni each candidacy ran in (and the
    # county for county-level races). Batch the lookup so we don't issue
    # N queries — covers both exec races (used for ranking) and list races
    # (used for the deep-link payload only).
    lokalni_cands = [c for c in candidacies
                     if c.electoral_list.election_round.election.election_type.name in ALL_LOKALNI]
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

    # Flag Sabor candidacies that actually won a seat (green dot). Compute the
    # winner set once per distinct Sabor round this person ran in.
    sabor_round_ids = {
        c.electoral_list.election_round_id
        for c in candidacies
        if c.electoral_list.election_round.election.election_type.name
        in {'Parlamentarni izbori'} | SABOR_1990_TYPE_NAMES
    }
    sabor_winner_ids = set()
    for rid in sabor_round_ids:
        sabor_winner_ids |= sabor_seat_winner_candidacy_ids(rid)

    # Blue dot: candidacies explicitly recorded as having taken a seat
    # (ElectedMandate table) — used for EU MEPs, where the seated set can't be
    # computed from votes. Maps candidacy_id -> EP political group.
    mandate_groups = dict(
        db.session.query(ElectedMandate.candidacy_id, ElectedMandate.group)
        .join(Candidacy, Candidacy.id == ElectedMandate.candidacy_id)
        .filter(Candidacy.person_id == person_id)
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

        # Fallback denominator: the votes cast in the same district. Needed for
        # 1995, whose 28 single-member districts and 5 minority units carry no
        # TurnoutData — the same voters are counted by the national list, so
        # storing it there too would double the electorate (see sabor_1995.py).
        # Summing the district's lists gives the right base for a plurality
        # race, and for the 3-seat minority unit it reproduces the report's own
        # denominator, which is votes cast rather than ballots.
        if not total_valid_ballots and el.district_id:
            total_valid_ballots = db.session.query(
                db.func.sum(ListResult.votes)
            ).join(
                ElectoralList, ElectoralList.id == ListResult.electoral_list_id
            ).filter(
                ElectoralList.election_round_id == er.id,
                ElectoralList.district_id == el.district_id,
            ).scalar() or 0

        vote_share = round((total_votes / total_valid_ballots) * 100, 1) if total_valid_ballots > 0 else 0

        rank, total_cands = rank_lookup.get(c.id, (None, None))
        # Deep-link payload for the lokalni results module: kind + county +
        # (for muni-level kinds) the muni id. Lets the frontend preselect
        # all four dropdowns when the badge/chart point is clicked.
        lokalni_kind = LOKALNI_KIND_MAP.get(etype.name)
        muni_id = list_to_muni.get(el.id) if lokalni_kind else None
        county_id = muni_to_county.get(muni_id) if muni_id else None
        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': round_date_iso(er, election),
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
            'won_seat': c.id in sabor_winner_ids,
            'eu_mep': c.id in mandate_groups and etype.name == 'Izbori za Europski parlament',
            'eu_group': mandate_groups.get(c.id) if etype.name == 'Izbori za Europski parlament' else None,
            'lokalni_kind': lokalni_kind,
            'county_id': county_id,
            'municipality_id': muni_id,
        })

    # Sabor convocations this person sat in without a candidacy to hang the
    # result on — pre-2015 years published no candidate names for districts
    # I-XI, and mid-term replacements never appear in a result at all. Emit a
    # vote-less row so the politician page shows the mandate instead of a gap.
    # (District XII members do have a candidacy and are already covered above.)
    covered_elections = {
        c.electoral_list.election_round.election.id for c in candidacies
    }
    memberships = (
        db.session.query(ParliamentMember, Election, ElectionType, ElectoralDistrict)
        .join(Election, Election.id == ParliamentMember.election_id)
        .join(ElectionType, ElectionType.id == Election.election_type_id)
        .outerjoin(ElectoralDistrict, ElectoralDistrict.id == ParliamentMember.district_id)
        .filter(ParliamentMember.person_id == person_id)
        .all()
    )
    for m, election, etype, mdistrict in memberships:
        if election.id in covered_elections:
            continue
        er = (
            ElectionRound.query
            .filter_by(election_id=election.id, round_number=1)
            .first()
        )
        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': round_date_iso(er, election) if er else None,
            'round': er.round_number if er else 1,
            'list_name': m.party,
            'position': None,
            # A roster published per district names one (2003's Sabor, every
            # Županijski dom county); a national roll does not.
            'district': (mdistrict.name if mdistrict else
                         ('XII. IJ - nacionalne manjine' if m.minority else None)),
            'candidate_votes': 0,
            'list_votes': 0,
            'total_valid_ballots': 0,
            'vote_share': 0,
            'rank': None,
            'total_candidates_in_round': None,
            'won_seat': True,
            'mandate_only': True,
            # Why there is no personal result differs by chamber: the Sabor
            # had no preferential vote before 2015, while the Županijski dom
            # was abolished in 2001 and never had one at all.
            'mandate_reason': ('sabor' if etype.slug == 'sabor' else 'list_only'),
            'note': m.note or '',
            'eu_mep': False,
            'eu_group': None,
            'lokalni_kind': None,
            'county_id': None,
            'municipality_id': None,
        })
    results.sort(key=lambda r: (-(r['year'] or 0), r['date'] or '', -(r['round'] or 0)))

    return jsonify({
        'id': person.id,
        'first_name': person.first_name,
        'last_name': person.last_name,
        'label': person_labels([person]).get(person.id, ''),
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
            'date': round_date_iso(er, election),
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
            'date': round_date_iso(er, election),
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
    sibling_ids = station_place_ids(station)

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
            'date': round_date_iso(er, election),
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
        .filter(~Municipality.id.in_(zagreb_sabor_units()))
        .order_by(Municipality.name)
        .all()
    )
    return jsonify([{'id': m.id, 'name': m.name} for m in munis])


# A polling station is shown as a place, never by number: DIP renumbers
# stations between elections, so a place can hold rows under several numbers
# (`station_for_place`, `rekey_stations`). Rows of one place share a
# `place_key`; rows naming no place (bare-number exports) stand alone.
def _row_place(s):
    return place_key(s.name, s.location, s.address) or f'#{s.id}'


# A building's rooms are one place: DIP lists "BIRALIŠTE 1/2/3, PROSTORIJE
# VI. OSNOVNE ŠKOLE", "IV. OSNOVNA ŠKOLA I/II", "O.Š. KEFELJA - PROSTOR BR. 2",
# "DOM KULTURE - ULAZ LIJEVO" at one address as separate stations.
_ROOM = re.compile(r'\b(?:BIRALI[SŠ]TE|BIR)\b\.?\s*(?:\d+|[IVX]+\b)\.?'
                   r'|\b(?:PROSTOR(?:IJA)?|U[CČ]IONICA)\s+(?:BR(?:OJ)?\.?\s*)?\d+\.?'
                   r'|\b(?:ULAZ\s+)?(?:LIJEVO|DESNO)\b'
                   r'|\([^)]*DVORAN[^)]*\)')


def _strip_rooms(location):
    """The building of a station's location, its room markers taken out."""
    s = _ROOM.sub(' ', location or '')
    s = re.sub(r'\s*[-,]\s*(?=[-,]|$)', '', s)               # separators left dangling
    return ' '.join(s.split()).strip(' ,-')


def _building_words(location):
    """A building's name as word stems, so its grammatical case does not
    matter ("VI. OSNOVNA ŠKOLA" / "PROSTORIJE VI. OSNOVNE ŠKOLE")."""
    words = re.findall(r'[A-Z]+', strip_diacritics(_strip_rooms(location).upper()))
    return {w[:4] for w in words if len(w) >= 4 and not re.fullmatch(r'[IVX]+', w)}


_PLACE_CACHE = {}


_STREET_TYPES = {'ULICA', 'UL', 'CESTA', 'TRG', 'PUT', 'BB', 'KBR', 'BR', 'BROJ',
                 'NASELJE', 'ODVOJAK', 'PROLAZ', 'SETALISTE', 'OBALA'}


def _address_sig(address, town_words):
    """(house numbers, street words cut to 5 letters) of an address, the
    town's own name left out — as `rekey_stations._street` reads it."""
    a = strip_diacritics((address or '').upper())
    numbers = set()
    for digits, slash, letter in re.findall(r'(\d+)\s*(?:/\s*([A-Z0-9]+)|([A-Z])\b)?', a):
        numbers |= {digits, slash or letter} - {''}
    words = {w[:5] for w in re.findall(r'[A-Z]+', a)
             if len(w) >= 3 and w not in town_words and w not in _STREET_TYPES}
    return frozenset(numbers), words


def _town_places(muni_ids):
    """Station id -> place key for a town's rows. Rows of one place_key are
    one place, and so is a building: rows at the same house numbers and street
    ("D. DEMETRA 13" / "DIMITRIJE DEMETRA 13"), whatever their rooms; where the
    source gives only the village ("KLENOVNIK"), rows of that village whose
    building names are the same once room markers and the town's name are
    dropped — "OSNOVNA ŠKOLA - BIR.1/2/3", but not Ivanec's SREDNJA and
    OSNOVNA ŠKOLA, nor its OSNOVNA ŠKOLA and Salinovec's OSNOVNA ŠKOLA
    SALINOVEC. Cached for ten minutes; `rekey_stations` changes this."""
    cache_key = tuple(sorted(muni_ids))
    hit = _PLACE_CACHE.get(cache_key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    rows = PollingStation.query.filter(PollingStation.municipality_id.in_(muni_ids)).all()
    town_words = set()
    for m in Municipality.query.filter(Municipality.id.in_(muni_ids)):
        town_words |= set(re.findall(r'[A-Z]+', strip_diacritics(m.name.upper())))
    parent = {}

    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    town_stems = {w[:4] for w in town_words}
    # "HRVATSKA" holds every town's mobile stations, so one address there can
    # be two towns.
    mixed = {m.id for m in Municipality.query.filter(Municipality.id.in_(muni_ids),
                                                    Municipality.name == 'HRVATSKA')}
    buckets = defaultdict(list)
    for r in rows:
        find(_row_place(r))
        if r.municipality_id in mixed:
            continue
        # Some sources put the room in the address ("BIRALIŠTE II").
        address = _strip_rooms(r.address)
        if not address or (r.location or '').startswith('sažetak'):
            continue
        numbers, street = _address_sig(address, town_words)
        plain = re.sub(r'[^0-9A-Z]', '', strip_diacritics(address.upper()))
        # Without a house number the building's name decides, and the town's
        # own name in it ("CENTAR ZA KULTURU KORČULA") says nothing.
        building = _building_words(r.location) if numbers else _building_words(r.location) - town_stems
        buckets[numbers or plain].append((r, street, building, bool(numbers)))
    # A row whose address was only its room ("BIRALIŠTE II", "PROSTORIJA 2")
    # is at its village or town: compared with the rows whose address is the
    # station's name ("SALINOVEC") or the town's ("KORČULA").
    muni_names = {m.id: m.name for m in Municipality.query.filter(Municipality.id.in_(muni_ids))}
    for r in rows:
        if r.address and not _strip_rooms(r.address) and r.location and r.municipality_id not in mixed:
            entry = (r, set(), _building_words(r.location) - town_stems, False)
            for where in (r.name, muni_names[r.municipality_id]):
                buckets[re.sub(r'[^0-9A-Z]', '', strip_diacritics((where or '').upper()))].append(entry)
    for group in buckets.values():
        for i, (r1, s1, b1, numbered) in enumerate(group):
            for r2, s2, b2, _ in group[i + 1:]:
                # A street and house number is one building whatever its
                # rooms are called (Kastav's PRIZEMLJE / SUTEREN); a bare
                # village or town needs the building's name to agree too.
                if not numbered and not (b1 and b1 == b2):
                    continue
                if s1 != s2 and not (s1 and s2 and (s1 <= s2 or s2 <= s1)):
                    continue
                a, b = find(_row_place(r1)), find(_row_place(r2))
                if a != b:
                    parent[max(a, b)] = min(a, b)
    places = {r.id: find(_row_place(r)) for r in rows}
    _PLACE_CACHE[cache_key] = (time.time(), places)
    return places


_ZAGREB_UNITS = None


def zagreb_sabor_units():
    """Sabor files Zagreb's stations under its electoral districts ("ZAGREB
    - VI. IZBORNA JEDINICA", "ZAGREB-JUGOISTOK") rather than GRAD ZAGREB.
    Every other municipality of county 21 is one of those."""
    global _ZAGREB_UNITS
    if _ZAGREB_UNITS is None:
        _ZAGREB_UNITS = [m.id for m in Municipality.query.join(County)
                         .filter(County.code == '21', Municipality.name != 'GRAD ZAGREB')
                         .filter(~Municipality.name.like('%SAŽETAK%'))]
    return _ZAGREB_UNITS


def town_muni_ids(municipality_id):
    """The municipality as a town: GRAD ZAGREB with its Sabor districts, whose
    stations `rekey_stations` spells as the Grad Zagreb place they are."""
    units = zagreb_sabor_units()
    if not units:
        return [municipality_id]
    zagreb = Municipality.query.filter_by(name='GRAD ZAGREB').first()
    if zagreb and (municipality_id == zagreb.id or municipality_id in units):
        return [zagreb.id] + units
    return [municipality_id]


def station_place_ids(station):
    """Every station row of `station`'s place, in its town."""
    places = _town_places(town_muni_ids(station.municipality_id))
    key = places.get(station.id, _row_place(station))
    return [sid for sid, k in places.items() if k == key] or [station.id]


def _place_options(rows):
    """Dropdown entries, one per place: the first row's id, its name(s) and
    building. Left out: summary pseudo stations (location "sažetak…"), which
    hold whole-town or county totals, and rows whose source named no place
    (a bare number) — picking the town already includes both."""
    town = _town_places({r.municipality_id for r in rows}) if rows else {}
    places = {}
    for r in sorted(rows, key=lambda r: r.id):
        if (r.location or '').startswith('sažetak') or not place_key(r.name, r.location, r.address):
            continue
        places.setdefault(town.get(r.id, _row_place(r)), []).append(r)
    out = []
    for key, group in places.items():
        # "VARAŽDIN - 25", "IVANEC - 3": a station number in the name.
        names = list(dict.fromkeys(re.sub(r'\s*-\s*\d+\.?$', '', r.name)
                                   for r in group if r.name))
        built = next((r for r in group if r.location or r.address), group[0])
        location, address = built.location, built.address
        if len({(r.location, r.address) for r in group}) > 1:
            address = _strip_rooms(address)
        if len({r.location for r in group if r.location}) > 1:
            # Several rooms: name the building, not one of its rooms.
            location = _strip_rooms(built.location)
            romans = {m.group(1) for r in group
                      if (m := re.search(r'\s([IVX]+)\.?$', _strip_rooms(r.location)))}
            if len(romans) > 1:                   # "IV. OSNOVNA ŠKOLA I" / "... II"
                location = re.sub(r'\s[IVX]+\.?$', '', location)
        # The address too: Varaždin has four "BIRALIŠTE 2, PROSTORIJE DJEČJEG
        # VRTIĆA", one per kindergarten, told apart only by their street.
        label = ', '.join(x for x in (' / '.join(names), location, address) if x)
        out.append({'id': group[0].id,
                    'name': label or f'{group[0].number}. (naziv nije objavljen)',
                    '_sort': (not label, strip_diacritics(label).upper())})
    out.sort(key=lambda o: o.pop('_sort'))
    return out


@app.route('/api/polling-stations/<int:municipality_id>')
def list_polling_stations(municipality_id):
    return jsonify(_place_options(PollingStation.query.filter(
        PollingStation.municipality_id.in_(town_muni_ids(municipality_id))).all()))


@app.route('/api/streets/<int:municipality_id>')
def list_streets(municipality_id):
    streets = (
        db.session.query(PollingStation.address)
        .filter(PollingStation.municipality_id.in_(town_muni_ids(municipality_id)))
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
    return jsonify(_place_options(PollingStation.query.filter(
        PollingStation.municipality_id.in_(town_muni_ids(municipality_id)),
        PollingStation.address == street).all()))


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
        query = query.filter(PollingStation.id.in_(station_place_ids(station)))
    elif street:
        query = query.filter_by(address=street)
        if municipality_id:
            query = query.filter(PollingStation.municipality_id.in_(town_muni_ids(municipality_id)))
    elif municipality_id:
        query = query.filter(PollingStation.municipality_id.in_(town_muni_ids(municipality_id)))
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

    shown = set()
    elections = []
    for td in turnout_rows:
        er = ElectionRound.query.get(td.er_id)
        shown.add((er.election.election_type.slug, er.election.year))
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
            'date': round_date_iso(er, election),
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
        # For one place: the number-only elections it has no result for.
        'number_only_missing': [name for slug, year, name in NUMBER_ONLY_ELECTIONS
                                if station_id and (slug, year) not in shown],
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
        ps = PollingStation.query.get_or_404(station_id)
        scope_station_ids = db.session.query(PollingStation.id).filter(
            PollingStation.id.in_(station_place_ids(ps)))
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

    return jsonify({
        'year': year,
        'total_seats': sabor_total_seats(year),
        'parties': seat_list,
        'candidates': ordered_candidates,
        'members': members,
        'districts': district_details,
    })


@app.route('/api/national/zupanijski-dom/<int:year>')
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
        'number': d.number, 'label': label or d.name.replace(' - ', ' — '),
        'registered': reg, 'cast': cast, 'invalid': inv, 'valid': cast - inv,
        'turnout_pct': round(cast / reg * 100, 2) if reg else 0,
        'candidates': rows,
        'winners': [c for c in rows if c['won']],
    }
    out.update(extra or {})
    return out


@app.route('/api/national/sabor-1995')
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
        'diaspora': proportional(SABOR_1995_DIASPORA_DISTRICT, 'Posebne liste — dijaspora'),
        'districts': single,
        'minorities': minorities,
        'parties': sorted(({'name': k, 'seats': v} for k, v in seat_tally.items()),
                          key=lambda x: (-x['seats'], x['name'])),
    })


@app.route('/api/national/sabor-1992')
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
                      'label': f'{d.number}. izborna jedinica — {name}',
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
    # 1993's two kotari (Glina, Knin) are stored as municipalities of type kotar.
    'vijece': {'grad': 'Gradsko vijeće', 'općina': 'Općinsko vijeće', 'kotar': 'Kotarska skupština'},
    'nacelnik': {'grad': 'Gradonačelnik', 'općina': 'Načelnik'},
}
LOKALNI_COUNTY_KIND_TO_TYPE = {
    'zupan': 'Župan',
    'zup_skupstina': 'Županijska skupština',
}


@app.route('/api/lokalni/years')
def lokalni_years():
    """Years with lokalni results, newest first — the module's year picker."""
    years = (db.session.query(Election.year).join(ElectionType)
             .filter(ElectionType.slug.like('local%')).distinct().all())
    return jsonify(sorted((y for (y,) in years), reverse=True))


@app.route('/api/lokalni/wards')
def lokalni_wards():
    """1993's and 1997's single-member wards (izborne jedinice) of one
    council (`municipality_id`) or one county assembly (`county_id`): each
    ward's candidates with party, votes and share, the winner, and the ward's
    printed electorate where the report gives one. `winner_only` marks a ward
    whose report names only the winner (many 1993 općine)."""
    year = request.args.get('year', type=int) or 1997
    muni_id = request.args.get('municipality_id', type=int)
    county_id = request.args.get('county_id', type=int)
    if county_id:
        type_name = LOKALNI_WARD_TYPES['zup_skupstina_ij']
        scope = (db.session.query(PollingStation.id)
                 .join(Municipality, Municipality.id == PollingStation.municipality_id)
                 .filter(Municipality.county_id == county_id))
        number_base = county_id
    elif muni_id:
        type_name = LOKALNI_WARD_TYPES['vijece_ij']
        scope = db.session.query(PollingStation.id).filter(PollingStation.municipality_id == muni_id)
        number_base = muni_id
    else:
        return jsonify({'error': 'municipality_id or county_id required'}), 400
    election = (Election.query.join(ElectionType)
                .filter(ElectionType.name == type_name, Election.year == year).first())
    if not election:
        return jsonify({'error': f'Izborne jedinice postoje samo za 1993. i 1997.; {year}. su '
                                 'vijeća birana samo po listama.'}), 404
    er = ElectionRound.query.filter_by(election_id=election.id, round_number=1).first()
    # Ward numbers are place_pk * 100 + ward, so one place's wards are a range.
    districts = (ElectoralDistrict.query
                 .filter(ElectoralDistrict.election_id == election.id,
                         ElectoralDistrict.number >= number_base * 100,
                         ElectoralDistrict.number < number_base * 100 + 100)
                 .order_by(ElectoralDistrict.number).all())
    rows = (db.session.query(ElectoralList.district_id, ElectoralList.name, Candidacy.person_id,
                             db.func.sum(CandidateResult.votes).label('votes'))
            .join(Candidacy, Candidacy.electoral_list_id == ElectoralList.id)
            .outerjoin(CandidateResult, db.and_(CandidateResult.candidacy_id == Candidacy.id,
                                                CandidateResult.polling_station_id.in_(scope)))
            .filter(ElectoralList.election_round_id == er.id,
                    ElectoralList.district_id.in_([d.id for d in districts]))
            .group_by(ElectoralList.district_id, ElectoralList.name, Candidacy.person_id)
            .all())
    by_district = {}
    for r in rows:
        # Ward lists are named "NAME (PARTY)".
        m = re.match(r'^(.*?)\s*\(([^()]*)\)$', r.name)
        name, party = (m.group(1), m.group(2)) if m else (r.name, '')
        by_district.setdefault(r.district_id, []).append({
            'name': name, 'person_id': r.person_id, 'party': party,
            'votes': int(r.votes) if r.votes is not None else None,
        })
    wards = []
    for d in districts:
        cands = sorted(by_district.get(d.id, []), key=lambda c: -(c['votes'] or 0))
        total = sum(c['votes'] or 0 for c in cands)
        for i, c in enumerate(cands):
            c['votes_pct'] = (c['votes'] / total * 100.0) if total and c['votes'] is not None else None
            c['winner'] = i == 0
        wards.append({
            'name': d.name, 'number': d.number % 100,
            'registered_voters': d.registered_voters, 'ballots_cast': d.ballots_cast,
            'invalid_ballots': d.invalid_ballots, 'unopposed': len(cands) == 1,
            # 1993 prints no count for an unopposed candidate in a full ward,
            # so there a count-less single candidate is always winners-only
            # (Nova Gradiška prints the turnout, then only the winner).
            'winner_only': (len(cands) == 1 and cands[0]['votes'] is None
                            and (year == 1993 or d.registered_voters is None)),
            'total_votes': total, 'candidates': cands,
        })
    return jsonify({'election_type': type_name, 'year': year, 'wards': wards})


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
        if not muni or muni.type not in LOKALNI_KIND_TO_TYPE[kind]:
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
        # Before 2009 mayors and župani were chosen by the councils, so 2005
        # has only vijeća and skupštine.
        if year and int(year) < 2009 and kind in ('nacelnik', 'zupan'):
            return jsonify({'error': f'{type_name}: {year}. nije bilo neposrednih izbora — '
                                     'načelnike, gradonačelnike i župane neposredno se bira od 2009.'}), 404
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
        scope_stations = db.session.query(PollingStation.id).filter(
            PollingStation.id.in_(station_place_ids(station)))
    else:
        scope_stations = db.session.query(PollingStation.id).filter(
            PollingStation.municipality_id == muni.id
        )
    list_rows = (
        db.session.query(
            ElectoralList.id,
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
    # Executive races have one candidate per list; their person id lets a bar
    # open that exact person, where a name search could pick a namesake.
    person_by_list = dict(
        db.session.query(Candidacy.electoral_list_id, Candidacy.person_id)
        .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
        .filter(ElectoralList.election_round_id == er.id).all())
    items = [{
        'name': r.name,
        'person_id': person_by_list.get(r.id),
        'votes': int(r.votes or 0),
        'votes_pct': (r.votes / total * 100.0) if total else 0.0,
    } for r in list_rows]

    # Turnout over the same scope as the votes: the county, the station's
    # place, or the municipality.
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
    elif station_id:
        # Every row of the station's place (it may sit under several numbers).
        agg_q = agg_q.filter(PollingStation.id.in_(station_place_ids(station)))
    else:
        agg_q = agg_q.filter(PollingStation.municipality_id == muni.id)
    agg = agg_q.first()
    turnout_data = {
        'registered_voters': int(agg[0] or 0),
        'ballots_cast': int(agg[1] or 0),
        'valid_ballots': int(agg[2] or 0),
        'invalid_ballots': int(agg[3] or 0),
    } if agg and (agg[0] or not station_id) else None    # a station with no turnout row: none

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
    # The Sabor's upper house, 1993-2001. Kept apart from 'sabor' on purpose:
    # it is a different chamber, and merging the two would add its 63 county
    # seats to a Zastupnički dom total and double-count 1997's electorate.
    'zupanijski_dom': {
        'label': 'Županijski dom Sabora',
        'short': 'Županijski dom',
        'types': ['Županijski dom Sabora'],
    },
    # The 1990 Sabor's socio-political chamber — a third chamber again, kept
    # apart for the same reason as the Županijski dom.
    'sabor_dpv': {
        'label': 'Društveno-političko vijeće Sabora (1990.)',
        'short': 'DPV Sabora',
        'types': ['Društveno-političko vijeće Sabora'],
    },
    # Its council of municipalities, elected the same day. Its 115 units are
    # not a partition: the city-wide Zagreb unit's voters also voted in their
    # own Zagreb općina, so that unit carries no turnout row (see sabor_1990.py).
    'sabor_vo': {
        'label': 'Vijeće općina Sabora (1990.)',
        'short': 'Vijeće općina',
        'types': ['Vijeće općina Sabora'],
    },
    # Its council of associated labour, elected the same day by the employed
    # at their workplaces: 160 units, a partition of that electorate.
    'sabor_vur': {
        'label': 'Vijeće udruženog rada Sabora (1990.)',
        'short': 'VUR Sabora',
        'types': ['Vijeće udruženog rada Sabora'],
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
            # Round date first — a 2. krug card must show the runoff's own day,
            # not the first round's. Election.date covers rounds with no date.
            db.func.coalesce(ElectionRound.date, Election.date),
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
        # Display only — filters are keyed on `id`, never the label.
        gap = INCOMPLETE_COVERAGE.get((g['category'], g['year']))
        g['coverage_note'] = gap
        g['label'] = (f"{g['category_label']} {g['year']}{round_suffix}"
                      + (f" ({gap})" if gap else ""))
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
