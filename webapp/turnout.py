"""Izlaznost (/api/analytics/*): turnout across elections and scopes.
"""

from flask import jsonify, request
from webapp.core import app, db
from webapp.models import (
    County,
    Election,
    ElectionRound,
    ElectionType,
    Municipality,
    PollingStation,
    TurnoutData,
)
from webapp.common import INCOMPLETE_COVERAGE


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
        round_suffix = f" - {g['round_number']}. krug" if g['round_number'] > 1 else ""
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
                    'name': f"{r[1]} - {r[3] or r[2] or ''}".strip(' -'),
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
