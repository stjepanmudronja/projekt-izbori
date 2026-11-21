"""Lokalni izbori: years, 1993/1997 wards and per-station/municipality/county
results for councils, mayors and župani.
"""

import re
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
    ListHolder,
    ListResult,
    Municipality,
    Person,
    PollingStation,
    TurnoutData,
)
from webapp.common import LOKALNI_WARD_TYPES
from webapp.places import station_place_ids


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
            return jsonify({'error': f'{type_name}: {year}. nije bilo neposrednih izbora - '
                                     'načelnike, gradonačelnike i župane neposredno se bira od 2009. '
                                     'Nositelja liste s najviše glasova prikazuje '
                                     + ('Županijska skupština.' if kind == 'zupan' else 'Vijeće.')}), 404
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
        'holder': None,
    } for r in list_rows]

    # Before 2009 the council chose the executive, so the result names only
    # each list's nositelj (2001, 2005; 2009 too). Council lists are shared across
    # municipalities, so a leader is looked up within the scope's own.
    if is_county_kind:
        scope_munis = db.session.query(Municipality.id).filter(Municipality.county_id == county.id)
    else:
        scope_munis = db.session.query(Municipality.id).filter(Municipality.id == muni.id)
    holders = {}
    for h, p in (db.session.query(ListHolder, Person)
                 .join(Person, Person.id == ListHolder.person_id)
                 .filter(ListHolder.electoral_list_id.in_([r.id for r in list_rows]),
                         ListHolder.municipality_id.in_(scope_munis))):
        holders.setdefault(h.electoral_list_id, []).append(
            {'name': f'{p.first_name} {p.last_name}', 'person_id': p.id})
    for r, item in zip(list_rows, items):
        if len(holders.get(r.id, [])) == 1:
            item['holder'] = holders[r.id][0]

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
        'station_label': f'{station.number} - {station.location or station.name or ""}'.strip(' -') if station else None,
        'station_address': (station.address if station else '') or '',
        'municipality': muni.name if muni else None,
        'municipality_id': muni.id if muni else None,
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
