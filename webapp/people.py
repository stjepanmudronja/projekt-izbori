"""Politicians: search, the politician page (/api/person/<id>), the Sabor
and government roles from elections/sabor_roles.py, and offices won.
"""

from datetime import date as _date
from flask import jsonify, request
from elections.importers.name_utils import normalize_person_name
from elections.sabor_roles import SABOR_ROLES, ROLE_TITLES, ROLE_ORDER
from webapp.core import app, data_cache, db
from webapp.models import (
    Candidacy,
    CandidateResult,
    County,
    ElectedMandate,
    Election,
    ElectionRound,
    ElectionType,
    ElectoralDistrict,
    ElectoralList,
    ListHolder,
    ListResult,
    Municipality,
    ParliamentMember,
    Person,
    PollingStation,
    TurnoutData,
)
from webapp.common import (
    LOKALNI_KIND_MAP,
    LOKALNI_WARD_TYPES,
    person_labels,
    round_date_iso,
    SABOR_1990_TYPE_NAMES,
    sabor_seat_winner_candidacy_ids,
)


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
    # The 1990 chambers are a head-to-head race per unit and per round, so
    # they rank like a presidential round within its district.
    RANK_BY_DISTRICT = {'Predsjednički izbori'} | SABOR_1990_TYPE_NAMES | set(LOKALNI_WARD_TYPES.values())
    RANK_BY_MUNI = {'Gradonačelnik', 'Načelnik'}
    RANK_BY_COUNTY = {'Župan'}
    LOKALNI_EXEC = RANK_BY_MUNI | RANK_BY_COUNTY
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
            '_election_id': election.id,
            '_slug': etype.slug,
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
            '_election_id': election.id,
            '_slug': etype.slug,
        })
    # Council lists this person led (2001-2009): no personal vote, so the
    # row carries the list's result in that municipality and its place among
    # the lists, never a rank or seat badge. Before 2009 the council chose
    # the executive; leading the first list did not make anyone načelnik.
    held = (db.session.query(ListHolder, ElectoralList, Municipality)
            .join(ElectoralList, ElectoralList.id == ListHolder.electoral_list_id)
            .join(Municipality, Municipality.id == ListHolder.municipality_id)
            .filter(ListHolder.person_id == person_id).all())
    for h, el, muni in held:
        er = el.election_round
        election = er.election
        etype = election.election_type
        stations = db.session.query(PollingStation.id).filter(PollingStation.municipality_id == muni.id)
        by_list = dict(
            db.session.query(ListResult.electoral_list_id, db.func.sum(ListResult.votes))
            .join(ElectoralList, ElectoralList.id == ListResult.electoral_list_id)
            .filter(ElectoralList.election_round_id == er.id,
                    ListResult.polling_station_id.in_(stations))
            .group_by(ListResult.electoral_list_id).all())
        list_votes = int(by_list.get(el.id) or 0)
        valid = db.session.query(db.func.sum(TurnoutData.valid_ballots)).filter(
            TurnoutData.election_round_id == er.id,
            TurnoutData.polling_station_id.in_(stations)).scalar() or 0
        if not valid:
            valid = sum(int(v or 0) for v in by_list.values())
        ordered = sorted(by_list, key=lambda k: -int(by_list[k] or 0))
        county_level = muni.type == 'sažetak'
        results.append({
            'election': election.name or f'{etype.name} {election.year}',
            'election_type': etype.name,
            'year': election.year,
            'date': round_date_iso(er, election),
            'round': er.round_number,
            'list_name': el.name,
            'position': None,
            'district': muni.name.replace(' (SAŽETAK)', '') if county_level else muni.name,
            'candidate_votes': 0,
            'list_votes': list_votes,
            'total_valid_ballots': valid,
            'vote_share': 0,
            'rank': None,
            'total_candidates_in_round': None,
            'won_seat': False,
            'list_holder': True,
            'list_share': round(list_votes / valid * 100, 1) if valid else 0,
            'list_place': ordered.index(el.id) + 1 if el.id in ordered else None,
            'lists_in_race': len(ordered),
            'eu_mep': False,
            'eu_group': None,
            'lokalni_kind': LOKALNI_KIND_MAP.get(etype.name),
            'county_id': muni.county_id,
            'municipality_id': None if county_level else muni.id,
        })

    results.sort(key=lambda r: (-(r['year'] or 0), r['date'] or '', -(r['round'] or 0)))
    offices = person_offices(results)
    roles = person_roles(person)
    for r in results:
        if r.get('_slug') in SABOR_ROLE_SLUGS:
            held = [x for x in roles if r['year'] in x['sazivi']]
            if held:
                r['roles'] = held
    for r in results:
        r.pop('_election_id', None)
        r.pop('_slug', None)

    return jsonify({
        'id': person.id,
        'first_name': person.first_name,
        'last_name': person.last_name,
        'label': person_labels([person]).get(person.id, ''),
        'results': results,
        'offices': offices,
        'roles': sorted(roles, key=lambda x: (x['start'] or str(x['sazivi'][0]), ROLE_ORDER.index(x['role']))),
    })


# Key offices held during a Sabor saziv (elections/sabor_roles.py): Prime
# Minister, Speaker, deputy speakers, Secretary. Matched to the unlabelled
# Person of the name, so a namesake split off by split_persons never gets one.
# They badge the person's Sabor result(s) of that saziv — the 1990 Sabor is
# its three chambers — and list in the offices card.
SABOR_ROLE_SLUGS = {'sabor', 'sabor_dpv', 'sabor_vo', 'sabor_vur'}
_ROLES_BY_NAME = {}
for _entry in SABOR_ROLES:
    _role, _name, _sazivi, _start, _end, _party = _entry[:6]
    _title = _entry[6] if len(_entry) > 6 else ROLE_TITLES[_role]
    _held = _ROLES_BY_NAME.setdefault(normalize_person_name(_name), [])
    # A term carried into the next cabinet (Granić through four HDZ
    # governments, Polančec from Sanader's into Kosor's) is one stretch in
    # office: joined when the same office starts again within a week of the
    # last ending.
    _prev = next((x for x in reversed(_held) if x['role'] == _role and x['title'] == _title), None)
    if (_prev and _prev['end'] and _start
            and 0 <= (_date.fromisoformat(_start) - _date.fromisoformat(_prev["end"])).days <= 7):
        _prev['end'] = _end
        _prev['sazivi'] = sorted(set(_prev['sazivi']) | set(_sazivi))
        continue
    _held.append({
        'role': _role, 'title': _title, 'sazivi': list(_sazivi),
        'start': _start, 'end': _end, 'party': _party,
    })

# A role names a national figure, so it goes only to a Person with a
# national record (Sabor or one of its chambers, EU, presidential): where the
# only Person of that name stood in local elections, it is far likelier a
# namesake than the minister (Ivica Kirin, Predrag Šustar…), and is left out.
NATIONAL_SLUGS = SABOR_ROLE_SLUGS | {'sabor_zupanijski', 'eu_parliament', 'presidential'}
_national_cache = data_cache({})


def _has_national_record(person_id):
    if person_id not in _national_cache:
        cand = (db.session.query(Candidacy.id)
                .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
                .join(ElectionRound, ElectionRound.id == ElectoralList.election_round_id)
                .join(Election, Election.id == ElectionRound.election_id)
                .join(ElectionType, ElectionType.id == Election.election_type_id)
                .filter(Candidacy.person_id == person_id, ElectionType.slug.in_(NATIONAL_SLUGS))
                .first())
        member = (db.session.query(ParliamentMember.id)
                  .filter(ParliamentMember.person_id == person_id).first()) if not cand else None
        _national_cache[person_id] = bool(cand or member)
    return _national_cache[person_id]


def person_roles(person):
    if person.disambiguation or person.normalized_name not in _ROLES_BY_NAME:
        return []
    if not _has_national_record(person.id):
        return []
    return sorted(_ROLES_BY_NAME[person.normalized_name],
                  key=lambda x: (ROLE_ORDER.index(x['role']), x['start'] or ''))


def saziv_roles_by_person(person_ids, year):
    """{person id: [roles held in the saziv elected in `year`]}."""
    if not person_ids:
        return {}
    names = set(_ROLES_BY_NAME)
    out = {}
    for prs in Person.query.filter(Person.id.in_(person_ids),
                                   Person.normalized_name.in_(names)).all():
        held = [x for x in person_roles(prs) if year in x['sazivi']]
        if held:
            out[prs.id] = held
    return out


# Offices a result can win, by election type slug.
EXEC_OFFICES = {'local_mayor': 'Načelnik', 'local_city_mayor': 'Gradonačelnik',
                'local_county_prefect': 'Župan'}
SEAT_OFFICES = {'sabor': 'Zastupnik u Saboru',
                'sabor_zupanijski': 'Zastupnik u Županijskom domu Sabora',
                'sabor_dpv': 'Zastupnik u Društveno-političkom vijeću Sabora',
                'sabor_vo': 'Zastupnik u Vijeću općina Sabora',
                'sabor_vur': 'Zastupnik u Vijeću udruženog rada Sabora',
                'eu_parliament': 'Zastupnik u Europskom parlamentu'}
WARD_OFFICES = {'local_council_ward': 'Vijećnik (izborna jedinica)',
                'local_county_assembly_ward': 'Vijećnik županijske skupštine (izborna jedinica)'}


def _later_round(election_id, round_no, muni_id=None, county_id=None):
    """Whether the race went on past `round_no` in that place (a runoff,
    or 2021's repeat in Kraljevec na Sutli)."""
    q = (db.session.query(CandidateResult.id)
         .join(Candidacy, Candidacy.id == CandidateResult.candidacy_id)
         .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
         .join(ElectionRound, ElectionRound.id == ElectoralList.election_round_id)
         .join(PollingStation, PollingStation.id == CandidateResult.polling_station_id)
         .filter(ElectionRound.election_id == election_id, ElectionRound.round_number > round_no))
    if muni_id:
        q = q.filter(PollingStation.municipality_id == muni_id)
    elif county_id:
        q = q.join(Municipality, Municipality.id == PollingStation.municipality_id) \
             .filter(Municipality.county_id == county_id)
    return q.first() is not None


def person_offices(results):
    """The offices a person won, by office and place, from their results:
    načelnik / gradonačelnik / župan (first in the round that decided the
    race), president (first in the last round), a Sabor, Županijski dom,
    1990 chamber or EU seat, and a 1990s ward. `current` when the win was
    the latest election of that kind on record; `since` is the first of the
    unbroken run of wins up to the last one. From election results only:
    resignations, replacements and a mandate put on hold are not known."""
    wins = {}          # (title, place, slug) -> set of years
    place_ids = {}     # (title, place, slug) -> municipality id, for its page

    def add(title, place, slug, year, place_id=None):
        wins.setdefault((title, place, slug), set()).add(year)
        if place_id:
            place_ids[(title, place, slug)] = place_id

    races = {}         # executive / presidential: election -> its last-round row
    for r in results:
        slug = r.get('_slug')
        if slug in EXEC_OFFICES or slug == 'presidential':
            key = (r['_election_id'], r.get('municipality_id') if slug != 'local_county_prefect' else r.get('county_id'))
            if key not in races or r['round'] > races[key]['round']:
                races[key] = r
        elif slug in SEAT_OFFICES and (r.get('won_seat') or r.get('eu_mep')):
            if slug != 'eu_parliament' or r.get('eu_mep'):
                add(SEAT_OFFICES[slug], None, slug, r['year'])
        elif slug in WARD_OFFICES and r.get('rank') == 1:
            add(WARD_OFFICES[slug], (r.get('district') or '').split(',')[0] or None, slug, r['year'])
    for r in races.values():
        if r.get('rank') != 1:
            continue
        slug = r['_slug']
        if slug == 'presidential':
            if not _later_round(r['_election_id'], r['round']):
                add('Predsjednik Republike', None, slug, r['year'])
            continue
        if slug == 'local_county_prefect':
            if not r.get('county_id') or _later_round(r['_election_id'], r['round'], county_id=r['county_id']):
                continue
            county = County.query.get(r['county_id'])
            add(EXEC_OFFICES[slug], county.name if county else None, slug, r['year'])
        else:
            if not r.get('municipality_id') or _later_round(r['_election_id'], r['round'], muni_id=r['municipality_id']):
                continue
            muni = Municipality.query.get(r['municipality_id'])
            add(EXEC_OFFICES[slug], muni.name if muni else None, slug, r['year'], muni.id if muni else None)

    if not wins:
        return []
    years_by_slug = {}
    for slug, year in (db.session.query(ElectionType.slug, Election.year)
                       .join(Election, Election.election_type_id == ElectionType.id)
                       .filter(ElectionType.slug.in_({k[2] for k in wins})).distinct()):
        years_by_slug.setdefault(slug, set()).add(year)
    offices = []
    for (title, place, slug), years in wins.items():
        held = sorted(years)
        record = sorted(years_by_slug.get(slug, set()))
        since = held[-1]
        while since in record and record.index(since) > 0 and record[record.index(since) - 1] in years:
            since = record[record.index(since) - 1]
        # The 1990 chambers, the Županijski dom and the 1990s wards are gone:
        # winning their last election is not holding office now.
        still_elected = slug in EXEC_OFFICES or slug in ('sabor', 'eu_parliament', 'presidential')
        offices.append({'title': title, 'place': place, 'place_id': place_ids.get((title, place, slug)),
                        'years': held, 'since': since,
                        'current': still_elected and bool(record) and held[-1] == record[-1]})
    offices.sort(key=lambda o: (not o['current'], -o['years'][-1], o['title']))
    return offices
