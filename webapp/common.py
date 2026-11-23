"""Shared election facts and helpers: polling dates, seat counts per year,
which election types are which, and who won a Sabor seat in a round.
"""

import re
from collections import defaultdict
from types import SimpleNamespace
from sqlalchemy import any_, bindparam
from sqlalchemy.dialects.postgresql import ARRAY
from elections.importers.name_utils import strip_diacritics
from webapp.core import data_cache, db
from webapp.models import (
    Candidacy,
    CandidateResult,
    Election,
    ElectionRound,
    ElectionType,
    ElectoralDistrict,
    ElectoralList,
    ListResult,
    ParliamentMember,
    Person,
)


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
    'vijece_ij': 'Vijeće - izborne jedinice',
    'zup_skupstina_ij': 'Županijska skupština - izborne jedinice',
}

# Maps election_type.name → kind key used by the lokalni results module
# dropdown (selLokKind). Used to deep-link from a politician's badge/chart
# point, or a Prema lokaciji chart point, straight into the matching scope
# (county / muni + kind).
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
_SABOR_SEAT_WINNERS_CACHE = data_cache({})


def sabor_seat_winner_candidacy_ids(er_id):
    """Return the set of Candidacy.id that won a Sabor seat in this round.

    Mirrors the D'Hondt + preferential-vote allocation in sabor_seats() but
    tracks the chosen candidacies at the individual level so the politician
    page can flag who actually entered the Sabor."""
    hit = _SABOR_SEAT_WINNERS_CACHE.get(er_id)
    if hit is not None:
        return hit

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

    # Two grouped queries for the round instead of one per district and per
    # winning list: every list's votes, allocate, then the preferential votes
    # of the lists that won seats.
    # The round's lists first, then their votes by list id: summed in one
    # join instead, PostgreSQL misjudges the row count and scans all 5.6 M
    # ListResult rows (0.4 s a round against 0.04 s).
    lists_meta = (
        db.session.query(ElectoralList.id, ElectoralList.name, ElectoralList.district_id, ElectoralDistrict.number)
        .join(ElectoralDistrict, ElectoralDistrict.id == ElectoralList.district_id)
        .filter(ElectoralList.election_round_id == er_id)
        .all()
    )
    totals = dict(
        db.session.query(ListResult.electoral_list_id, db.func.sum(ListResult.votes))
        .filter(ListResult.electoral_list_id.in_([m.id for m in lists_meta]))
        .group_by(ListResult.electoral_list_id)
        .all()
    ) if lists_meta else {}
    # Lists with no result rows are left out, as the per-district join did.
    list_rows = [SimpleNamespace(id=m.id, name=m.name, district_id=m.district_id, number=m.number,
                                 total_votes=totals[m.id])
                 for m in lists_meta if m.id in totals]
    won_lists = []                               # (list id, seats, list votes)
    by_district = defaultdict(list)
    for r in list_rows:
        by_district[(r.district_id, r.number)].append(r)

    for (_dist_id, number), rows in by_district.items():
        if number in MINORITY_SEATS:
            n_seats = MINORITY_SEATS[number]
        elif number == 11:
            n_seats = diaspora_seats(year)
        elif number == 12:
            n_seats = 8
        else:
            n_seats = 14

        list_votes = [(r.name, r.total_votes) for r in rows]
        list_id_map = {r.name: r.id for r in rows}
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
            if list_id and seats_won:
                won_lists.append((list_id, seats_won, list_votes_by_name.get(list_name, 0)))

    # Candidates' preferential votes, for the lists that won seats only;
    # candidacies first, then their votes by id (the same planner trap).
    cand_by_list = defaultdict(list)
    if won_lists:
        cands = (db.session.query(Candidacy.id, Candidacy.electoral_list_id, Candidacy.position_on_list)
                 .filter(Candidacy.electoral_list_id.in_([l for l, _s, _v in won_lists])).all())
        personal = dict(
            db.session.query(CandidateResult.candidacy_id, db.func.sum(CandidateResult.votes))
            .filter(CandidateResult.candidacy_id.in_([c.id for c in cands]))
            .group_by(CandidateResult.candidacy_id)
            .all()
        ) if cands else {}
        for c in cands:
            cand_by_list[c.electoral_list_id].append(SimpleNamespace(
                id=c.id, position_on_list=c.position_on_list, personal_votes=personal.get(c.id, 0)))

    for list_id, seats_won, list_total_votes in won_lists:
        cand_rows = cand_by_list.get(list_id, [])
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


def any_of(column, ids):
    """`column = ANY(:ids)`, the id list sent as one PostgreSQL array.

    Use it instead of `column.in_(ids)` for long lists (a county's or a big
    town's polling stations): `IN (…)` with thousands of parameters makes
    PostgreSQL walk ListResult / CandidateResult by candidacy and check each
    row against the list (9.6 s for the 2,032 diaspora stations), while an
    array lets it read the rows by station (2.3 s)."""
    return column == any_(bindparam(None, list(ids), type_=ARRAY(db.Integer)))


def party_wording_key(name):
    """A printed party name's wording: case, punctuation, spacing, Croatian
    letters, a leading "KOALICIJA" label and a trailing abbreviation ("- HDZ",
    "- HSP-1861") set aside. Two printings with the same key are the same name;
    anything else is another name - and so another party (the data's owner's
    rule)."""
    name = re.sub(r'^(?:koalicija\s+|[^:]{0,60}koalicija:\s*)', '', (name or '').strip(), flags=re.I)
    parts = [x.strip() for x in name.split(' - ')]
    if len(parts) > 1 and re.fullmatch(r"[A-ZČĆŠŽĐ0-9!]+(?:-[A-ZČĆŠŽĐ0-9!]+)*", parts[-1]) and len(parts[-1]) <= 12:
        parts = parts[:-1]
    return re.sub(r'[^A-Z0-9]', '', strip_diacritics(' '.join(parts).upper()))


# Names a party ran under before its registration was renamed. A name change
# makes another party (the data's owner), but the register keeps one entry per
# registration, so these link to it and carry the name they ran under: Snaga
# stranaka and the map give each its own line, the party page says which name
# each election was won under. Wording key -> (register no., name).
PARTY_OLD_NAMES = {
    'HRVATSKANARODNASTRANKA': (45, 'Hrvatska narodna stranka'),                   # 1992-2005; HNS - Liberalni demokrati from 2007
    'MOSTNEZAVISNIHLISTA': (245, 'Most nezavisnih lista'),                        # 2013-2020; MOST from 2021
    'HRVATSKAGRADANSKASTRANKA': (212, 'Hrvatska građanska stranka'),              # 2011-2013; Željko Kerum - HGS from 2015
    'NAPRIJEDHRVATSKAPROGRESIVNISAVEZIVEJOSIPOVICA': (286, 'Naprijed Hrvatska! - Progresivni savez Ive Josipovića'),  # 2015
    'SOCIJALISTICKAPARTIJAHRVATSKELIJEVAALTERNATIVA': (174, 'Socijalistička partija Hrvatske - Lijeva alternativa'),  # 2005
    'POKRETOSTECENIKASTRANKAEKOLOSKISVJESNIHGRADANA': (126, 'Pokret oštećenika - Stranka ekološki svjesnih građana'),  # 2000
}
# Printings that are one registration's own name, damaged in the 1993 OCR
# ("DEMOKRATSKIH PROMJENA - SDP"): wording key -> register no. Register no. 70
# is "Socijaldemokratska partija Hrvatske - Stranka demokratskih promjena", a
# separate entry from today's SDP (no. 88).
PARTY_PRINTED_ALIASES = {
    'DEMOKRATSKIHPROMJENA': 70,
    'SOCIJALDEMOKRATSKAPARTIJAHRVATSKESTRANKADEMOKRATSKIH': 70,
}
# For the map, which keys parties by abbreviation: names that share an
# abbreviation with a later name but are another party (key -> label).
MAP_OWN_NAMES = {k: name for k, (_reg, name) in PARTY_OLD_NAMES.items()}
MAP_OWN_NAMES.update({
    'SOCIJALDEMOKRATSKAPARTIJAHRVATSKESTRANKADEMOKRATSKIHPROMJENA': 'SDP - Stranka demokratskih promjena',
    'DEMOKRATSKIHPROMJENA': 'SDP - Stranka demokratskih promjena',
    'SOCIJALDEMOKRATSKAPARTIJAHRVATSKESTRANKADEMOKRATSKIH': 'SDP - Stranka demokratskih promjena',
})
