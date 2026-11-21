"""Places: polling stations grouped into places, municipalities and their
pages (/api/place), and results by location (Prema lokaciji).
"""

import re
import time
from collections import defaultdict
from flask import jsonify, request
from elections.importers.name_utils import place_key, strip_diacritics
from webapp.core import app, db, static_cache
from webapp.models import (
    Candidacy,
    CandidateResult,
    County,
    Election,
    ElectionRound,
    ElectionType,
    ElectoralList,
    ListHolder,
    ListResult,
    Municipality,
    Person,
    PollingStation,
    TurnoutData,
)
from webapp.common import (
    any_of,
    LOKALNI_KIND_MAP,
    NUMBER_ONLY_ELECTIONS,
    round_date_iso,
    SABOR_1990_TYPE_NAMES,
)


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


PLACE_EXEC_TYPES = {'Načelnik', 'Gradonačelnik'}
PLACE_COUNCIL_TYPES = {'Općinsko vijeće', 'Gradsko vijeće', 'Kotarska skupština'}
_PROFILE_CACHE = {}     # muni id -> (time, payload); ten minutes, as _town_places


@app.route('/api/place/<int:muni_id>')
def place_profile(muni_id):
    hit = _PROFILE_CACHE.get(muni_id)
    if hit and time.time() - hit[0] < 600:
        return jsonify(hit[1])
    payload = _place_profile(muni_id)
    if isinstance(payload, tuple):           # an error response
        return payload
    _PROFILE_CACHE[muni_id] = (time.time(), payload)
    return jsonify(payload)


def _place_profile(muni_id):
    """One town's electoral history for the municipality page (an error
    response tuple when there is none): every round
    held there (turnout and who came first), the načelnik / gradonačelnik
    each election returned — before 2009, when the council chose one, the
    leader of the list with the most votes instead, marked as such — the
    council's leading lists, and who holds office now by the latest result.
    Covers the whole town (`town_muni_ids`: Grad Zagreb with its Sabor-only
    units)."""
    muni = Municipality.query.get(muni_id)
    if not muni:
        return jsonify({'error': 'To mjesto ne postoji.'}), 404
    munis = town_muni_ids(muni_id)
    station_ids = db.session.query(PollingStation.id).filter(PollingStation.municipality_id.in_(munis))
    if not station_ids.first():
        return jsonify({'error': 'Nema rezultata za ovo mjesto.'}), 404

    rounds = (
        db.session.query(
            ElectionRound.id.label('er_id'),
            db.func.sum(TurnoutData.registered_voters).label('registered'),
            db.func.sum(TurnoutData.ballots_cast).label('cast'),
            db.func.sum(TurnoutData.valid_ballots).label('valid'),
        )
        .join(ElectionRound, TurnoutData.election_round_id == ElectionRound.id)
        .join(Election, ElectionRound.election_id == Election.id)
        .filter(TurnoutData.polling_station_id.in_(station_ids))
        .group_by(ElectionRound.id)
        .order_by(db.func.min(Election.year).desc(), db.func.min(Election.date).desc().nullslast(),
                  db.func.min(ElectionRound.round_number).desc())
        .all()
    )
    # Council list leaders in this town, by (round, list name).
    holders = {}
    for er_id, name, pid, first, last in (
            db.session.query(ElectoralList.election_round_id, ElectoralList.name,
                             Person.id, Person.first_name, Person.last_name)
            .join(ListHolder, ListHolder.electoral_list_id == ElectoralList.id)
            .join(Person, Person.id == ListHolder.person_id)
            .filter(ListHolder.municipality_id.in_(munis))):
        holders[(er_id, name)] = {'name': f'{first} {last}', 'person_id': pid}

    # Every round's candidate and list totals in two grouped queries (one per
    # round took half a minute for Grad Zagreb's thousand-odd stations).
    round_ids = [td.er_id for td in rounds]
    cands_by_round, lists_by_round = {}, {}
    for rid, pid, first, last, votes in (
            db.session.query(ElectoralList.election_round_id, Person.id, Person.first_name,
                             Person.last_name, db.func.sum(CandidateResult.votes))
            .select_from(CandidateResult)
            .join(Candidacy, Candidacy.id == CandidateResult.candidacy_id)
            .join(Person, Person.id == Candidacy.person_id)
            .join(ElectoralList, ElectoralList.id == Candidacy.electoral_list_id)
            .filter(CandidateResult.polling_station_id.in_(station_ids),
                    ElectoralList.election_round_id.in_(round_ids))
            .group_by(ElectoralList.election_round_id, Person.id, Person.first_name, Person.last_name)):
        cands_by_round.setdefault(rid, []).append(
            type('C', (), {'id': pid, 'first_name': first, 'last_name': last, 'votes': votes}))
    for rid, name, votes in (
            db.session.query(ElectoralList.election_round_id, ElectoralList.name, db.func.sum(ListResult.votes))
            .select_from(ListResult)
            .join(ElectoralList, ElectoralList.id == ListResult.electoral_list_id)
            .filter(ListResult.polling_station_id.in_(station_ids),
                    ElectoralList.election_round_id.in_(round_ids))
            .group_by(ElectoralList.election_round_id, ElectoralList.name)):
        lists_by_round.setdefault(rid, []).append(type('L', (), {'name': name, 'votes': votes}))
    round_objs = {er.id: er for er in ElectionRound.query.filter(ElectionRound.id.in_(round_ids))}

    elections = []
    for td in rounds:
        er = round_objs[td.er_id]
        election, etype = er.election, er.election.election_type
        cands = sorted(cands_by_round.get(er.id, []), key=lambda c: -int(c.votes or 0))[:3]
        lists = sorted(lists_by_round.get(er.id, []), key=lambda l: -int(l.votes or 0))[:3]
        valid = int(td.valid or 0)
        share = lambda v: round(int(v or 0) / valid * 100, 1) if valid else None
        exec_race = etype.name in PLACE_EXEC_TYPES
        # A head-to-head race is won by a person; a list race by a list.
        if cands and (exec_race or etype.slug in ('presidential',) or not lists or etype.name in SABOR_1990_TYPE_NAMES):
            top = cands[0]
            winner = {'name': f'{top.first_name} {top.last_name}', 'person_id': top.id,
                      'votes': int(top.votes or 0), 'share': share(top.votes)}
        elif lists:
            winner = {'name': lists[0].name, 'person_id': None,
                      'votes': int(lists[0].votes or 0), 'share': share(lists[0].votes)}
        else:
            winner = None
        elections.append({
            'election_type': etype.name, 'slug': etype.slug, 'year': election.year,
            'date': round_date_iso(er, election), 'round': er.round_number,
            'registered': int(td.registered or 0), 'cast': int(td.cast or 0), 'valid': valid,
            'turnout_pct': round(int(td.cast or 0) / int(td.registered) * 100, 1) if td.registered else None,
            'winner': winner,
            'lists': [{'name': l.name, 'votes': int(l.votes or 0), 'share': share(l.votes),
                       'holder': holders.get((er.id, l.name))} for l in lists],
            '_er_id': er.id, '_election_id': election.id,
        })

    # Who each election made načelnik: the top of its last round here.
    last_round = {}
    for e in elections:
        if e['election_type'] in PLACE_EXEC_TYPES and e['winner']:
            if e['_election_id'] not in last_round or e['round'] > last_round[e['_election_id']]['round']:
                last_round[e['_election_id']] = e
    executives = [{'year': e['year'], 'date': e['date'], 'office': e['election_type'], 'round': e['round'],
                   'name': e['winner']['name'], 'person_id': e['winner']['person_id'],
                   'votes': e['winner']['votes'], 'share': e['winner']['share'], 'basis': 'izbori'}
                  for e in last_round.values()]
    elected_years = {x['year'] for x in executives}
    # Before 2009 the council chose; the leading list's holder is all the result says.
    for e in elections:
        if (e['election_type'] in PLACE_COUNCIL_TYPES and e['year'] < 2009 and e['year'] not in elected_years
                and e['lists'] and e['lists'][0]['holder']):
            h = e['lists'][0]['holder']
            executives.append({'year': e['year'], 'date': e['date'], 'office': None, 'round': None,
                               'name': h['name'], 'person_id': h['person_id'], 'votes': e['lists'][0]['votes'],
                               'share': e['lists'][0]['share'], 'basis': 'nositelj', 'list': e['lists'][0]['name']})
    executives.sort(key=lambda x: -x['year'])

    current = None
    direct = [x for x in executives if x['basis'] == 'izbori']
    if direct:
        latest = direct[0]
        since = latest['year']
        for x in direct[1:]:
            if x['person_id'] != latest['person_id']:
                break
            since = x['year']
        current = {**latest, 'since': since}

    councils = [e for e in elections if e['election_type'] in PLACE_COUNCIL_TYPES and e['round'] == 1]
    for e in elections:
        e.pop('_er_id', None)
        e.pop('_election_id', None)
    return {
        'id': muni.id, 'name': muni.name, 'type': muni.type,
        'county': muni.county.name if muni.county else None, 'county_id': muni.county_id,
        'current': current, 'executives': executives, 'councils': councils, 'elections': elections,
    }


@app.route('/api/location-results')
@static_cache(maxsize=500)
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

    # Where a chart point should open the Lokalni page: the town in scope (a
    # station's or street's town, or the town itself), else just the county.
    nav_muni = (PollingStation.query.get(station_id).municipality_id if station_id
                else municipality_id)
    nav_county = (Municipality.query.get(nav_muni).county_id if nav_muni else county_id)

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

    # Every round's lists, candidates and list leaders in one grouped query
    # each, top five per round picked here: a query per round re-read the
    # same stations' results ~60 times (Grad Zagreb took ~25 s, now ~2 s).
    er_ids = [td.er_id for td in turnout_rows]
    rounds = {er.id: er for er in ElectionRound.query.filter(ElectionRound.id.in_(er_ids))} if er_ids else {}

    def top5(rows, key):
        by_round = defaultdict(list)
        for r in rows:
            by_round[r[0]].append(r)
        return {er_id: sorted(rs, key=key)[:5] for er_id, rs in by_round.items()}

    list_rows = (
        db.session.query(
            ElectoralList.election_round_id, ElectoralList.name,
            db.func.sum(ListResult.votes).label('total_votes'),
        )
        .join(ElectoralList, ListResult.electoral_list_id == ElectoralList.id)
        .filter(any_of(ListResult.polling_station_id, station_ids),
                any_of(ElectoralList.election_round_id, er_ids))
        .group_by(ElectoralList.election_round_id, ElectoralList.name)
        .all()
    ) if er_ids else []
    # Ties (equal votes) in name order; the database used to return them in no set order.
    top_lists = top5(list_rows, key=lambda r: (-(r.total_votes or 0), r.name or ''))

    cand_rows = (
        db.session.query(
            ElectoralList.election_round_id, Person.first_name, Person.last_name,
            db.func.sum(CandidateResult.votes).label('total_votes'),
            ElectoralList.name.label('list_name'), Person.id,
        )
        .join(Candidacy, CandidateResult.candidacy_id == Candidacy.id)
        .join(Person, Candidacy.person_id == Person.id)
        .join(ElectoralList, Candidacy.electoral_list_id == ElectoralList.id)
        .filter(any_of(CandidateResult.polling_station_id, station_ids),
                any_of(ElectoralList.election_round_id, er_ids))
        .group_by(ElectoralList.election_round_id, Person.id, Person.first_name,
                  Person.last_name, ElectoralList.name)
        .all()
    ) if er_ids else []
    top_candidates = top5(cand_rows, key=lambda r: (-(r.total_votes or 0), r.first_name or '', r.last_name or ''))

    # 2001-2009 councils: each list's nositelj in this place (see
    # ListHolder), where the place has exactly one for that list. A
    # county view adds up many towns' councils, where no one leads; its
    # own assembly is the one body it can name a leader for.
    holders = defaultdict(dict)                  # round id -> list name -> [leaders]
    if er_ids:
        for er_id, name, first, last, pid, slug in (
                db.session.query(ElectoralList.election_round_id, ElectoralList.name,
                                 Person.first_name, Person.last_name, Person.id, ElectionType.slug)
                .join(ListHolder, ListHolder.electoral_list_id == ElectoralList.id)
                .join(Person, Person.id == ListHolder.person_id)
                .join(ElectionRound, ElectionRound.id == ElectoralList.election_round_id)
                .join(Election, Election.id == ElectionRound.election_id)
                .join(ElectionType, ElectionType.id == Election.election_type_id)
                .filter(any_of(ElectoralList.election_round_id, er_ids),
                        ListHolder.municipality_id.in_(
                            db.session.query(PollingStation.municipality_id)
                            .filter(any_of(PollingStation.id, station_ids))))):
            if station_id or municipality_id or slug == 'local_county_assembly':
                holders[er_id].setdefault(name, []).append({'name': f'{first} {last}', 'person_id': pid})

    shown = set()
    elections = []
    for td in turnout_rows:
        er = rounds[td.er_id]
        shown.add((er.election.election_type.slug, er.election.year))
        election = er.election
        etype = election.election_type
        round_holders = holders.get(er.id, {})

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
            'lokalni_kind': LOKALNI_KIND_MAP.get(etype.name),
            'county_id': nav_county,
            'municipality_id': nav_muni,
            'top_lists': [
                {'name': r.name, 'votes': r.total_votes,
                 'holder': round_holders[r.name][0] if len(round_holders.get(r.name, [])) == 1 else None}
                for r in top_lists.get(er.id, [])
            ],
            'top_candidates': [
                {
                    'name': f'{r.first_name} {r.last_name}',
                    'votes': r.total_votes,
                    'list_name': r.list_name,
                    'person_id': r.id,
                }
                for r in top_candidates.get(er.id, [])
            ],
        })

    return jsonify({
        'label': label,
        'elections': elections,
        # For one place: the number-only elections it has no result for.
        'number_only_missing': [name for slug, year, name in NUMBER_ONLY_ELECTIONS
                                if station_id and (slug, year) not in shown],
    })
