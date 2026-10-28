"""Read the 1990 Vijeće udruženog rada report out of its OCR.

The DPV and Vijeće općina reports were transcribed by hand; this chamber's
is twice their length (152 pages + a 14-page supplement), so it is read from
`tools/pdf_ocr` output instead and written out as `sabor_1990_vur_data.py`,
which is what the importer reads — the same shape as the other two chambers'
data modules, so the result can be checked and corrected by hand there.

    OCR_DESKEW=1 tools/pdf_ocr <main pdf> > files/rezultati_sabor/1990/ocr/vur.tsv
    python -m elections.importers.sabor_1990_vur_parse --crops <ocr dir> <pdf dir> \
        | CROP_LINES=1 tools/pdf_ocr_crops > <ocr dir>/vur_crops.tsv
    python -m elections.importers.sabor_1990_vur_parse --missing-crops <ocr dir> <pdf dir> \
        | CROP_LINES=1 tools/pdf_ocr_crops >> <ocr dir>/vur_crops.tsv   # after a parser change
    python -m elections.importers.sabor_1990_vur_parse <ocr dir>          # checks
    python -m elections.importers.sabor_1990_vur_parse <ocr dir> --write  # data module

The scans are skewed by up to ~1°, so the OCR must be deskewed or a row's
boxes drift apart and the right-margin votes pair with the wrong candidate.

Every unit reads: "N. IZBORNA JEDINICA NAME", the numbered candidates
("01. NAME, RESIDENCE" with the nominating party on the following lines and
the votes at the right margin), "U izbornoj jedinici bilo je upisano R
birača. Glasalo je C birača, a nevažećih listića bilo je I.", then either the
winner ("izabran je kandidat NAME") or a repeat vote (Article 58(2)) whose
round 2 follows in the same shape. The page pass drops short numbers and
merges lines now and then, so every unit's figures and vote column are read a
second time from crops (`--crops`), and the remaining fixes live in
`sabor_1990_vur_manual.py`: what neither reading gets, read off the scan.
The 14-page supplement (13 units) OCRs too poorly to parse - most name lines
are lost - so it is transcribed whole there (`UNITS`).

Vision has no Croatian; it reads Czech/Polish and drops a diacritic now and
then ("BARBIROVIC", "CEPIN"). `restore` puts them back word by word from a
vocabulary of known spellings (every Person and municipality in the
database, the two transcribed 1990 chambers), and a surname ending "-IC" is
"-IĆ" when nothing else is known.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

from .name_utils import strip_diacritics
from .ocr_rows import read

PARTY_NAMES = {
    'SAVEZ KOMUNISTA HRVATSKE - STRANKA DEMOKRATSKIH PROMJENA': 'SKH-SDP',
    'HRVATSKA DEMOKRATSKA ZAJEDNICA': 'HDZ',
    'HRVATSKA DEMOKRATSKA STRANKA': 'HDS',
    'HRVATSKI SOCIJALNO LIBERALNI SAVEZ': 'HSLS',
    'HRVATSKI SOCIJALNO-LIBERALNI SAVEZ': 'HSLS',
    'HRVATSKA KRSCANSKA DEMOKRATSKA STRANKA': 'HKDS',
    'SOCIJALDEMOKRATSKA STRANKA HRVATSKE': 'SDSH',
    'HRVATSKA SELJACKA STRANKA': 'HSS',
    'SOCIJALISTICKI SAVEZ - SAVEZ SOCIJALISTA HRVATSKE': 'SSH',
    'SOCIJALISTICKI SAVEZ RADNOG NARODA HRVATSKE': 'SSH',
    'SAVEZ SOCIJALISTA HRVATSKE': 'SSH',
    'SAVEZ SOCIJALISTICKE OMLADINE HRVATSKE': 'SSOH',
    'SRPSKA DEMOKRATSKA STRANKA': 'SDS',
    'NEZAVISNI KANDIDAT': 'NK',
    'KOALICIJA NARODNOG SPORAZUMA': 'KNS',
    'ZELENA AKCIJA SPLIT': 'ZAS',
    'HRVATSKI MIROTVORNI POKRET': 'HMP',
    'SAVEZ ZELENIH HRVATSKE': 'SZH',
    'DEMOKRATSKI SAVEZ ALBANACA HRVATSKE': 'DSAH',
    'HRVATSKA STRANKA': 'HS',
    'POKRET ZA KONFEDERACIJU': 'PZK',
    'UDRUZENJE SAMOSTALNIH PRIVREDNIKA DURDEVAC': 'USPĐ',
    'UDRUZENJE SAMOSTALNIH PRIVREDNIKA SISAK': 'USPS',
    'SAVEZ UDRUZENJA SAMOSTALNIH PRIVREDNIKA SPLIT': 'SUSPS',
}

UNIT_RE = re.compile(r'^(\d{1,3})\s*[.,]?\s*[I1l]\S{3,8}\s*JEDINIC\S*\s*(.*)$')
CAND_RE = re.compile(r'^[a-z]?([0-9OoIlU]{1,2})\s*[.,]\s*(.+)$')
FIGURES_RE = re.compile(r'upisano\s+(\d+)\D+?(\d+)\D*?bil[oa]\s+je\s+(\d+)', re.I)
NUMBERLESS_RE = re.compile(r"(?:[DO]r\.?\s+)?(?:MR\s+)?[A-ZČĆŽŠĐŚŻ][A-ZČĆŽŠĐŚŻ -]+,\s*[A-ZČĆŽŠĐŚŻ][A-ZČĆŽŠĐŚŻ .-]+")
WINNER_RE = re.compile(r'kandidat\w*\s+(.+?)[.,]?\s*$', re.I)
VOTES_X = 480          # the votes sit at the right margin; text starts near 100-160
# Headings Vision misread as another unit's number, by page.
MISREAD_HEADINGS = {67: 63}     # "63. ... PEŠČENICA I" read "53."
LINE_TOLERANCE = 5     # boxes whose tops lie this close are one printed line


def lines(tsv):
    """{page: ([(y, text)], [(y, votes)])}: the printed lines in reading
    order, and the right-margin numbers apart."""
    out = {}
    for page, boxes in read(tsv).items():
        numbers, text = [], []
        for x, y, h, _conf, t in boxes:
            t = t.strip()
            if x > VOTES_X and re.fullmatch(r'\d{1,6}', t):
                numbers.append((y, int(t)))
            elif x > 80 and y < 780 and not re.match(r'^C\)\s*Vije', t):
                text.append((y, x, t))     # not the page number, header or margin specks
        text.sort()
        rows = []
        for y, x, t in text:
            if rows and y - rows[-1][0] <= LINE_TOLERANCE:
                rows[-1][1].append((x, t))
            else:
                rows.append((y, [(x, t)]))
        out[page] = ([(y, ' '.join(t for _x, t in sorted(cells))) for y, cells in rows],
                     sorted(numbers))
    return out


def units(tsv_files, crops=None):
    """Parse every unit; a unit repeated in a later file (the supplement)
    replaces the earlier one, and a unit printed twice in one file (158) keeps
    the reading that adds up."""
    out = {}
    for tsv in tsv_files:
        for unit in _units(tsv):
            unit['file'] = tsv.stem
            if crops is not None:
                apply_crops(unit, crops)
            finalize(unit)
            prev = out.get(unit['number'])
            if prev and prev['file'] == unit['file'] \
                    and len(problems_of(prev)) <= len(problems_of(unit)):
                continue
            out[unit['number']] = unit
    return out


def _units(tsv):
    unit = rnd = None
    for page, (rows, numbers) in sorted(lines(tsv).items()):
        for kind, y, value in _events(rows, numbers):
            if kind == 'unit':
                if unit is not None:
                    yield unit
                number, name = value
                number = MISREAD_HEADINGS.get(page, number)
                unit = {'number': number, 'name': name, 'rounds': [], 'winner': None,
                        'page': page, 'head_pos': (page, y)}
                rnd = None
                continue
            if unit is None:
                continue
            if kind in ('round', 'cand') and unit['winner'] and unit['rounds'] \
                    and unit['rounds'][-1]['figures'] is not None:
                # A unit whose winner is stated is closed: this is the next
                # unit, its heading lost (the crop above it reads it again).
                yield unit
                unit = {'number': unit['number'] + 1, 'name': '', 'rounds': [], 'winner': None,
                        'page': page, 'head_pos': (page, y - 40), 'heading_lost': True}
                rnd = None
            if kind == 'round' or (kind in ('cand', 'figures') and
                                   (rnd is None or rnd['figures'] is not None)):
                # A candidate or figures line after a closed round opens the
                # next one even when its "Na utvrđenoj listi" line was lost.
                rnd = {'candidates': [], 'figures': None, 'start': (page, y), 'orphans': []}
                unit['rounds'].append(rnd)
                if kind == 'round':
                    continue
            if kind == 'cand':
                value['pos'] = (page, y)
                rnd['candidates'].append(value)
            elif kind == 'party':
                if rnd and rnd['candidates']:
                    rnd['candidates'][-1]['party'].append(value)
            elif kind == 'orphan':
                if rnd is not None and rnd['figures'] is None:
                    rnd['orphans'].append(value)
            elif kind == 'figures':
                rnd['figures'], rnd['figures_pos'] = value, (page, y)
            elif kind == 'figures_raw':
                rnd['figures_pos'] = (page, y)
                rnd['figures_raw'] = value
            elif kind == 'winner':
                unit['winner'] = value
                unit['winner_pos'] = (page, y)
            elif kind == 'winner_raw':
                unit['winner_pos'] = (page, y)
    if unit is not None:
        yield unit


def _cand_no(text):
    digits = text.translate(str.maketrans('OoIlU', '00110'))
    return int(digits) if digits.isdigit() else None


def _events(rows, numbers):
    """The printed lines of one page (or crop) as parse events, in order:
    ('unit', y, (number, name)), ('round', y, None), ('cand', y, {...}),
    ('party', y, text), ('figures', y, (reg, cast, inv)), ('winner', y, name),
    and ('orphan', y, votes) for a right-margin number beside no candidate."""
    # Each right-margin number belongs to the candidate line nearest above
    # it (it is printed beside the name, or centred on name + party).
    cand_ys = [y for y, t in rows if CAND_RE.match(t) and ',' in t
               or _numberless(t)]
    vote_for, orphans = {}, []
    for y, votes in numbers:
        near = [c for c in cand_ys if c - 8 <= y <= c + 22 and c not in vote_for]
        if near:
            vote_for[min(near, key=lambda c: abs(c + 5 - y))] = votes
        else:
            orphans.append((y, votes))
    events = [(y, 'orphan', v) for y, v in orphans]
    mode, buffer, start = None, '', None
    for y, text in rows:
        # Vision reads this typeface's 7 as a slash ("11/45 birača").
        text = re.sub(r'(?<=\d)/(?=\d)|(?<=\s)/(?=\d)', '7', text)
        low = text.lower()
        if mode:
            buffer += ' ' + text
            if mode == 'figures':
                f = FIGURES_RE.search(buffer)
                if f:
                    events.append((start, 'figures', tuple(int(g) for g in f.groups())))
                    mode = None
                elif buffer.count(' ') > 30:
                    events.append((start, 'figures_raw', buffer))
                    mode = None
                continue
            w = WINNER_RE.search(buffer) if 'kandidat' in buffer.lower() else None
            if w and len(_key(w.group(1))) < 5:
                w = None
            if w:
                events.append((start, 'winner', w.group(1).strip(' .,')))
                mode = None
            elif buffer.count(' ') > 30:
                events.append((start, 'winner_raw', buffer))
                mode = None
            continue
        m = UNIT_RE.match(text)
        if m:
            events.append((y, 'unit', (int(m.group(1)), m.group(2).strip(' -'))))
            continue
        if low.startswith('na utvr') or 'listi bili su' in low:
            events.append((y, 'round', None))
            continue
        if 'upisano' in low:
            mode, buffer, start = 'figures', '', y
            buffer = text
            f = FIGURES_RE.search(buffer)
            if f:
                events.append((y, 'figures', tuple(int(g) for g in f.groups())))
                mode = None
            continue
        if re.match(r'^\W{0,2}(na|ya|n[az])\s*te\s*m', low) or 'izabran' in low:
            mode, buffer, start = 'winner', text, y
            w = WINNER_RE.search(buffer) if 'kandidat' in low else None
            if w:
                events.append((y, 'winner', w.group(1).strip(' .,')))
                mode = None
            continue
        m = CAND_RE.match(text)
        if m and ',' in text:
            name, _, residence = m.group(2).replace('_', ' ').partition(',')
            residence, votes = _glued_votes(residence.strip(' ."*\'_'), vote_for.get(y))
            events.append((y, 'cand', {'no': _cand_no(m.group(1)),
                                       'name': re.sub(r'\s+', ' ', name).strip(' .'),
                                       'residence': residence,
                                       'party': [], 'votes': votes}))
            continue
        if _numberless(text):
            # A candidate line whose number Vision lost: "NAME, PLACE" is
            # never a party, which has no comma.
            name, _, residence = text.replace('_', ' ').partition(',')
            events.append((y, 'cand', {'no': None, 'name': re.sub(r'\s+', ' ', name).strip(' .'),
                                       'residence': residence.strip(' ."*\'_'),
                                       'party': [], 'votes': vote_for.get(y)}))
            continue
        if ',' in text and '?' not in party_code([text.replace(',', ' ')]):
            text = text.replace(',', ' ')
        if re.fullmatch(r"[-A-Z \"'.()*:]+", strip_diacritics(text).upper()) \
                and len(re.sub(r'[^A-Za-z]', '', text)) >= 5 \
                and sum(ch.islower() for ch in text) <= 2:
            events.append((y, 'party', text))
    if mode == 'figures':
        events.append((start, 'figures_raw', buffer))
    elif mode == 'winner':
        events.append((start, 'winner_raw', buffer))
    events.sort(key=lambda e: e[0])
    return [(kind, y, value) for y, kind, value in events]


def _glued_votes(residence, votes):
    """The votes read into the residence ("ŠIBENIK 6297", "KARLOVAC 345!")
    when the row's boxes merged and no right-margin number was found."""
    m = re.fullmatch(r'(.*?\D)\s+(\d{2,5})\W*', residence)
    if m and votes is None:
        return m.group(1).strip(' .,'), int(m.group(2))
    return residence, votes


def _numberless(text):
    """A "NAME, PLACE" line whose number was lost - unless it is a party
    name with a stray comma read into it ("HRVATSKA, DEMOKRATSKA ZAJEDNICA")."""
    return bool(NUMBERLESS_RE.fullmatch(text.strip(' .*'))) \
        and '?' in party_code([text.replace(',', ' ')])


def party_code(lines_):
    """Abbreviation(s) for a candidate's printed party lines: one party per
    line, and "- KOALICIJA NARODNOG SPORAZUMA" closing a joint candidacy."""
    codes = []
    import difflib
    for line in lines_:
        text = re.sub(r'\s+', ' ', strip_diacritics(line).upper()).strip(' -.')
        text = text.replace('KOMUNISIA', 'KOMUNISTA')
        if not text:
            continue
        best = difflib.get_close_matches(text, PARTY_NAMES, n=1, cutoff=0.8)
        if best:
            codes.append(PARTY_NAMES[best[0]])
        elif codes and not codes[-1].startswith('?'):
            # A long name wrapped onto a second line.
            codes.append(f'?{text}')
        else:
            codes.append(f'?{text}')
    # "SOCIJALISTICKI SAVEZ - SAVEZ SOCIJALISTA HRVATSKE" can wrap as two
    # lines that each look like a party; fold repeats.
    out = []
    for c in codes:
        if c not in out:
            out.append(c)
    return ','.join(out)


def valid_name(name):
    words = re.sub(r'^(DR|MR|PROF)\.?\s+', '', name.upper()).split()
    return len(_key(name)) >= 6 and 2 <= len(words) <= 4 and 'KANDID' not in name.upper()


def read_twice(r):
    """Every count and the figures read the same by the page and its crop."""
    return r.get('figures_read2') and all(c.get('read2') for c in r['candidates'])


def _drop_paired_orphans(r):
    """A number the page left unpaired that the crop has since given to a
    candidate is no longer unaccounted for."""
    taken = [c['votes'] for c in r['candidates']]
    left = []
    for v in r.get('orphans', []):
        if v in taken:
            taken.remove(v)
        else:
            left.append(v)
    r['orphans'] = left


def finalize(u):
    """Settle the winner: the deciding round's candidate the winner line
    names (page or crop reading, spelling tolerated). A winner missing from
    that round is the candidate whose line was lost, holding the round's one
    unpaired number; where no winner line reads at all, the round's leader
    is taken and the unit marked so."""
    if not u['rounds']:
        return
    for r in u['rounds']:
        _drop_paired_orphans(r)
        _recover_lost(r)
    last = u['rounds'][-1]
    read = [w for w in (u['winner'], u.get('winner_alt')) if w]
    for w in read:
        match = next((c for c in last['candidates'] if _same_person(c['name'], w)), None)
        if match:
            u['winner'] = match['name']
            return
    if read and len(last.get('orphans', [])) == 1:
        earlier = next((c for r in u['rounds'][:-1] for c in r['candidates']
                        if _same_person(c['name'], read[0])), None)
        if earlier:
            last['candidates'].insert(0, {
                'no': None, 'name': earlier['name'], 'residence': earlier['residence'],
                'party': list(earlier['party']), 'votes': last['orphans'].pop()})
            u['winner'] = earlier['name']
            u['recovered'] = earlier['name']
            return
    if not read and last['candidates'] and all(c['votes'] is not None for c in last['candidates']):
        u['winner'] = max(last['candidates'], key=lambda c: c['votes'])['name']
        u['winner_derived'] = True


def problems_of(u):
    problems = []
    number = u['number']
    for i, r in enumerate(u['rounds'], 1):
        if not r['candidates']:
            problems.append(f'{number} r{i}: no candidates')
            continue
        if r['figures'] is None:
            problems.append(f'{number} r{i}: no figures ({r.get("figures_raw", "")[:90]!r})')
            continue
        reg, cast, inv = r['figures']
        missing = [c['name'] for c in r['candidates'] if c['votes'] is None]
        if u.get('no_votes'):
            # Votes illegible on the scan (manual `NO_VOTES`): figures,
            # candidates and the winner only.
            if len(missing) != len(r['candidates']):
                problems.append(f'{number} r{i}: some votes kept in a NO_VOTES unit')
        elif missing:
            problems.append(f'{number} r{i}: missing votes for ' + ', '.join(missing))
            continue
        else:
            if r.get('orphans'):
                problems.append(f'{number} r{i}: unpaired numbers {r["orphans"]}')
            total = sum(c['votes'] for c in r['candidates'])
            # A round read identically twice keeps whatever gap the report has.
            trusted = read_twice(r) or r.get('confirmed')
            if total + inv > cast and not trusted:
                problems.append(f'{number} r{i}: votes {total} + invalid {inv} > cast {cast}')
            elif cast - inv - total > max(50, 0.02 * cast) and not trusted:
                problems.append(f'{number} r{i}: votes {total} short of cast-invalid {cast - inv} '
                                f'by {cast - inv - total}')
        if cast > reg:
            problems.append(f'{number} r{i}: cast {cast} > registered {reg}')
        for c in r['candidates']:
            if '?' in party_code(c['party']) or not c['party']:
                problems.append(f'{number} r{i}: party {c["party"]}')
            if not valid_name(c['name']):
                problems.append(f'{number} r{i}: name {c["name"]!r}')
    if not u['rounds']:
        problems.append(f'{number}: no rounds')
    if not u['name']:
        problems.append(f'{number}: heading lost (number inferred)')
    if not u['winner']:
        problems.append(f'{number}: no winner')
    elif u['rounds'] and u['rounds'][-1]['candidates']:
        last = u['rounds'][-1]['candidates']
        if all(c['votes'] is not None for c in last):
            top = max(last, key=lambda c: c['votes'])
            if not _same_person(top['name'], u['winner']):
                problems.append(f'{number}: winner {u["winner"]!r} but top is {top["name"]!r}')
            if len(u['rounds']) == 1 and top['votes'] * 2 <= sum(c['votes'] for c in last):
                problems.append(f'{number}: one round but no majority')
    return problems


def _key(name):
    return re.sub(r'[^A-Z]', '', strip_diacritics(name).upper())


def check(all_units, absent=()):
    problems = []
    for number, u in sorted(all_units.items()):
        problems += problems_of(u)
    numbers = sorted(all_units)
    gaps = [n for n in range(1, max(numbers) + 1) if n not in all_units and n not in absent]
    if gaps:
        problems.append(f'missing units: {gaps}')
    return problems


# ---- second readings from crops --------------------------------------------

PDFS = {'vur': '1990_1_5_Sabor_Rezultati_Vijece_udruzenog_rada.pdf'}


def skews(tsv):
    out = {}
    with open(tsv, encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) == 3 and p[1] == 'skew':
                out[int(p[0])] = p[2]
    return out


PAGE_BOTTOM = 782


def crop_specs(ocr_dir, pdf_dir, only_failing=True):
    """Every unit the page pass does not reconcile, read again in pieces,
    each rendered alone: its heading (H), each round's candidate block (B,
    one crop per page it spans), the round's figures sentence (F) and the
    winner sentence (W)."""
    for stem, pdf in PDFS.items():
        tsv = Path(ocr_dir) / f'{stem}.tsv'
        if not tsv.exists():
            continue
        sk = skews(tsv)
        pdf = Path(pdf_dir) / pdf

        def spec(u, rnd, kind, pg, y0, y1, x0=90, x1=600):
            y0, y1 = max(30, y0), min(PAGE_BOTTOM, y1)
            return (f'{stem}|{u["number"]}|{rnd}|{kind}|{pg}', pdf, pg,
                    x0, round(y0, 1), x1 - x0, round(y1 - y0, 1), sk.get(pg, ''))

        for u in _units(tsv):
            if only_failing and not problems_of(u):
                continue
            pg, y = u['head_pos']
            yield spec(u, 0, 'H', pg, y - 5, y + 16)
            for i, r in enumerate(u['rounds'], 1):
                p0, y0 = r['start']
                end = r.get('figures_pos') or (
                    r['candidates'][-1]['pos'][0], r['candidates'][-1]['pos'][1] + 40) \
                    if r['candidates'] else (p0, y0 + 60)
                p1, y1 = end
                for pg in range(p0, p1 + 1):
                    yield spec(u, i, 'B', pg, y0 + 8 if pg == p0 else 30,
                               y1 - 2 if pg == p1 else PAGE_BOTTOM)
                if r.get('figures_pos'):
                    pg, y = r['figures_pos']
                    yield spec(u, i, 'F', pg, y - 4, y + 28)
            if u.get('winner_pos'):
                pg, y = u['winner_pos']
                yield spec(u, 0, 'W', pg, y - 4, y + 28)


def read_crops(ocr_dir):
    """{(stem, unit, round, kind): {page: [(y, x, text)]}}"""
    out = defaultdict(lambda: defaultdict(list))
    path = Path(ocr_dir) / 'vur_crops.tsv'
    if not path.exists():
        return out
    with open(path, encoding='utf-8') as f:
        for line in f:
            p = line.rstrip('\n').split('\t')
            if len(p) < 5:
                continue
            stem, unit, rnd, kind, pg = p[0].split('|')
            out[(stem, int(unit), int(rnd), kind)][int(pg)].append((float(p[2]), float(p[4]), p[3]))
    return out


def _crop_events(pages):
    """Parse events of a crop's lines, page by page, through `_events`."""
    events = []
    for pg in sorted(pages):
        rows, numbers = [], []
        for y, x, t in sorted(pages[pg]):
            t = t.strip()
            if x > VOTES_X and re.fullmatch(r'\d{1,6}', t):
                numbers.append((y, int(t)))
            elif x > VOTES_X - 40 and re.fullmatch(r'\d{1,3}\.\d{3}|\d{1,6}', t):
                numbers.append((y, int(t.replace('.', ''))))
            elif rows and y - rows[-1][0] <= LINE_TOLERANCE:
                rows[-1][1].append((x, t))     # Vision split one printed line
            else:
                rows.append((y, [(x, t)]))
        rows = [(y, ' '.join(t for _x, t in sorted(cells))) for y, cells in rows]
        events += [(pg, kind, y, v) for kind, y, v in _events(rows, numbers)]
    return events


def apply_crops(u, crops):
    """Merge the crop readings into the page reading: figures and winner
    where the page lost them (an alternative where both read), and each
    round's candidates by their printed number, the crop supplying a
    candidate the page lost and an alternative count where they differ."""
    key = (u['file'], u['number'])
    head = [v for _pg, kind, _y, v in _crop_events(crops.get(key + (0, 'H'), {})) if kind == 'unit']
    if head and (head[0][0] == u['number'] or u.get('heading_lost')) \
            and len(head[0][1]) >= len(u['name']):
        u['number'], u['name'] = head[0]
    win = [v for _pg, kind, _y, v in _crop_events(crops.get(key + (0, 'W'), {})) if kind == 'winner']
    if win:
        u['winner_alt'] = win[0]
        if not u['winner']:
            u['winner'] = win[0]
    for i, r in enumerate(u['rounds'], 1):
        fig = [v for _pg, kind, _y, v in _crop_events(crops.get(key + (i, 'F'), {}))
               if kind == 'figures']
        if fig:
            if r['figures'] == fig[0]:
                r['figures_read2'] = True
            if r['figures'] is None:
                r['figures'] = fig[0]
            elif r['figures'] != fig[0]:
                r['figures_alt'] = fig[0]
        cands, last = [], None
        for pg, kind, y, v in _crop_events(crops.get(key + (i, 'B'), {})):
            if kind == 'cand':
                v['pos'] = (pg, y)
                cands.append(v)
                last = v
            elif kind == 'party' and last is not None:
                last['party'].append(v)
        _merge_candidates(r, cands)
        _settle(u, r)


def _same_person(a, b, cutoff=0.8):
    import difflib
    ka, kb = _key(a), _key(b)
    return bool(ka and kb) and difflib.SequenceMatcher(None, ka, kb).ratio() >= cutoff


def _merge_candidates(r, crop):
    """Pair each crop candidate with the page's by name, else by printed
    number (01, 02, … in each round); a crop candidate matching neither is
    one the page lost. A count both readings agree on is marked read twice."""
    page = r['candidates']
    extra = []
    for c in crop:
        p = next((p for p in page if _same_person(p['name'], c['name'])), None)
        if p is None:
            p = next((p for p in page if p['no'] and p['no'] == c['no']), None)
            if p is not None and _key(p['name']) and _key(c['name']) \
                    and not _same_person(p['name'], c['name'], 0.5):
                p = None
        if p is None:
            if c['no'] and c['votes'] is not None and _key(c['name']):
                extra.append(c)
            continue
        if p['votes'] is None:
            p['votes'] = c['votes']
        elif c['votes'] is not None:
            if c['votes'] == p['votes']:
                p['read2'] = True
            else:
                p['votes_alt'] = c['votes']
        if (not p['party'] or '?' in party_code(p['party'])) \
                and c['party'] and '?' not in party_code(c['party']):
            p['party'] = c['party']
        p['name_alt'], p['residence_alt'] = c['name'], c['residence']
        if valid_name(c['name']) and (not valid_name(p['name'])
                                      or len(_key(c['name'])) > len(_key(p['name'])) + 1):
            p['name'] = c['name']
    # A candidate only the crop reads is one the page lost — or noise read
    # as a line. Take it only while the page's count falls short of the
    # round's valid votes by about its count, and its number is free.
    if extra and r['figures'] and all(c['votes'] is not None for c in page):
        import itertools
        _reg, cast, inv = r['figures']
        taken = {c['no'] for c in page}
        extra = [c for c in extra if c['no'] not in taken][:8]
        short = cast - inv - sum(p['votes'] for p in page)
        fits = [combo for n in range(len(extra), 0, -1)
                for combo in itertools.combinations(extra, n)
                if len({c['no'] for c in combo}) == n
                and 0 <= short - sum(c['votes'] for c in combo) <= max(50, 0.02 * cast)]
        if fits:
            page.extend(fits[0])
    elif extra and not page:
        page.extend(extra)
    page.sort(key=lambda c: c.get('pos') or (99, 0))
    _recover_lost(r)


def _recover_lost(r):
    """A lone number the page could not pair, beside a candidate that has
    none, is that candidate's."""
    missing = [c for c in r['candidates'] if c['votes'] is None]
    if len(missing) == 1 and len(r.get('orphans', [])) == 1:
        missing[0]['votes'] = r['orphans'][0]
        r['orphans'] = []


DIGIT_SWAPS = {'1': '7', '7': '1'}


def _variants(n):
    """n with one digit changed the way Vision misreads this typeface (1/7)."""
    t = str(n)
    return [int(t[:i] + DIGIT_SWAPS[d] + t[i + 1:]) for i, d in enumerate(t) if d in DIGIT_SWAPS]


def _settle(u, r):
    """Where the page and crop readings disagree, take the combination that
    reconciles: votes + invalid within cast, the smallest gap winning. Where
    no reading reconciles, one figure or count with a single 1/7 swapped may,
    if exactly one such swap brings the round within the usual gap."""
    import itertools
    if r['figures'] is None or any(c['votes'] is None for c in r['candidates']):
        return
    figs = [r['figures']] + ([r['figures_alt']] if r.get('figures_alt') else [])
    choices = [[c['votes']] + ([c['votes_alt']] if 'votes_alt' in c else [])
               for c in r['candidates']]

    def best_of(figs, choices):
        best = None
        for fig in figs:
            reg, cast, inv = fig
            for combo in itertools.product(*choices):
                gap = cast - inv - sum(combo)
                if gap < 0 or cast > reg:
                    continue
                score = (gap, combo != tuple(c['votes'] for c in r['candidates']))
                if best is None or score < best[0]:
                    best = (score, fig, combo)
        return best

    best = best_of(figs, choices)
    tolerance = lambda fig: max(50, 0.02 * fig[1])
    if best is None or best[0][0] > tolerance(best[1]):
        fixes = []
        fig, combo = figs[0], [c[0] for c in choices]
        for i in range(3):
            for v in _variants(fig[i]):
                f2 = tuple(v if j == i else x for j, x in enumerate(fig))
                b2 = best_of([f2], [[x] for x in combo])
                if b2 and b2[0][0] <= tolerance(f2):
                    fixes.append(b2)
        for k in range(len(combo)):
            for v in _variants(combo[k]):
                b2 = best_of([fig], [[v] if j == k else [x] for j, x in enumerate(combo)])
                if b2 and b2[0][0] <= tolerance(fig):
                    fixes.append(b2)
        if len(fixes) == 1:
            best = fixes[0]
            r['digit_fixed'] = True
    if best:
        _score, r['figures'], combo = best
        for c, v in zip(r['candidates'], combo):
            c['votes'] = v


# ---- writing the data module -----------------------------------------------

# Czech/Polish letters Vision reads in place of Croatian ones.
OCR_LETTERS = str.maketrans({'Ś': 'Š', 'Ż': 'Ž', 'Ź': 'Ž', 'Ę': 'E', 'Á': 'A', 'Í': 'I',
                             'Ó': 'O', 'Ú': 'U', 'Ý': 'Y', 'Ř': 'R', 'Ň': 'N', 'Ě': 'E',
                             'Ů': 'U', 'Ł': 'L', 'Ń': 'N', 'Ť': 'T', 'Ď': 'Đ'})
LOWER_WORDS = {'NA', 'PRI', 'U', 'KOD', 'OD', 'I', 'NAD', 'POD', 'DO', 'KRAJ'}


class Vocabulary:
    """Spellings known from every Person and municipality in the database and
    the two transcribed 1990 chambers: `freq` counts each upper-case word,
    `best` maps a word stripped of diacritics to its commonest spelling."""

    def __init__(self, texts):
        from collections import Counter
        self.freq = Counter(w for t in texts for w in re.findall(r"[^\W\d_]+", t.upper()))
        self.best = {}
        for w, n in self.freq.most_common():
            self.best.setdefault(strip_diacritics(w), w)
        # Sources that print no diacritics at all make a plain spelling
        # common; a marked one at a third of its count is the real one.
        for w, n in self.freq.items():
            k = strip_diacritics(w)
            b = self.best[k]
            if w != k and b == k and n * 3 >= self.freq[b]:
                self.best[k] = w
        # Plain forms with more than one common spelling (SIMIC: Simić and
        # Šimić), which a reading without diacritics cannot decide.
        self.spellings = defaultdict(list)
        for w, n in self.freq.items():
            k = strip_diacritics(w)
            if n * 4 >= self.freq[self.best[k]]:
                self.spellings[k].append(w)
        self.ambiguous = set()
        self.by_len = defaultdict(list)
        for w, n in self.freq.items():
            if n >= 3:
                self.by_len[len(w)].append(w)

    def word(self, w, alt=None, fuzzy=False):
        """One OCR'd word -> its spelling. A reading with a diacritic kept
        it from the page (Vision drops them, it rarely invents one), so the
        first such reading that is attested, or failing that is a known
        spelling's plain form, stands. A reading with none takes the
        commonest attested spelling of its plain form. An unknown word stays
        as read, unless `fuzzy` (first names and places), when it may take
        the nearest frequent word of its length."""
        import difflib
        options = [o for o in (w, alt) if o]
        marked = [o for o in options if o != strip_diacritics(o)]
        for o in marked:
            if o in self.freq:
                return o
        plain = strip_diacritics(w)
        if plain in self.best or (alt and strip_diacritics(alt) in self.best):
            k = plain if plain in self.best else strip_diacritics(alt)
            if not marked and len(self.spellings[k]) > 1:
                self.ambiguous.add(k)
            return self.best[k]
        if marked:
            return marked[0]
        if fuzzy and len(w) >= 4:
            near = difflib.get_close_matches(w, self.by_len[len(w)], n=1, cutoff=0.8)
            if near:
                return near[0]
        return w


def vocabulary():
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projekt_izbori.settings')
    import django
    django.setup()
    from elections.models import Municipality, Person
    from . import sabor_1990_dpv_data, sabor_1990_vo_data

    texts = [f'{f} {l}' for f, l in Person.objects.values_list('first_name', 'last_name')]
    texts += list(Municipality.objects.values_list('name', flat=True))
    for mod in (sabor_1990_dpv_data, sabor_1990_vo_data):
        for u in mod.DISTRICTS.values():
            texts.append(u['name'])
            for r in u['rounds']:
                for name, res, _p, _v in r['candidates']:
                    texts += [name, res]
    return Vocabulary(texts)


TITLE_RE = re.compile(r'^(DR|OR|MR|PROF)(?:\.?\s+|\.?(?=MARIJAN|IVAN|JOSIP|ANTE|STJEPAN|MATO|ZVONKO|BRANKO))')


def _words(text):
    text = text.upper().translate(OCR_LETTERS)
    return re.sub(r'\s+', ' ', text).strip(' .,*"\'').split(' ')


def restore(text, vocab, surname=False, alt=None):
    """Upper-case OCR text -> its Croatian spelling, title-cased. `alt` is
    the crop's reading of the same text, consulted word by word when both
    have as many words; a person's first names (not the surname) and every
    word of a place name may be corrected to a near frequent word."""
    title = ''
    m = TITLE_RE.match(text.upper())
    if m:
        title = {'OR': 'Dr'}.get(m.group(1), m.group(1).title()) + ' '
        text = text[m.end():]
        if alt:
            alt = TITLE_RE.sub('', alt.upper())
    words = _words(text)
    alts = _words(alt) if alt else []
    if len(alts) != len(words):
        alts = [None] * len(words)
    out = []
    for i, (w, a) in enumerate(zip(words, alts)):
        last = i == len(words) - 1
        parts = []
        a_parts = a.split('-') if a and a.count('-') == w.count('-') else [None] * (w.count('-') + 1)
        for part, a_part in zip(w.split('-'), a_parts):
            sp = vocab.word(part, a_part, fuzzy=not (surname and last))
            if sp not in vocab.freq and surname and last and sp.endswith('IC'):
                sp = sp[:-1] + 'Ć'
            parts.append(sp)
        w = '-'.join(parts)
        out.append(w.lower() if i and w in LOWER_WORDS else
                   '-'.join(p[:1] + p[1:].lower() for p in w.split('-')))
    return title + ' '.join(out)


def _spellings(u, vocab, fixes={}):
    """{id(candidate): (name, residence)}, one spelling per person per unit:
    whichever of the person's readings across rounds carries the most
    diacritics, which OCR drops far more often than it invents."""
    cands = [c for r in u['rounds'] for c in r['candidates']]
    # Candidates typed in from the scan (`exact`) are kept as written, and
    # win over any OCR reading of the same person.
    read = {id(c): (c['name'], c['residence']) if c.get('exact') else
            (restore(c['name'], vocab, surname=True, alt=c.get('name_alt')),
             restore(c['residence'], vocab, alt=c.get('residence_alt'))) for c in cands}
    marks = lambda t: sum(ch != strip_diacritics(ch) for ch in t)
    out = {}
    # Two candidates of one round are never the same person ("MILAN PEIC"
    # and "MILAN DESIC" are close enough to fool the fuzzy match).
    round_of = {id(c): i for i, r in enumerate(u['rounds']) for c in r['candidates']}
    for c in cands:
        same = [o for o in cands if o is c or round_of[id(o)] != round_of[id(c)]
                and _same_person(o['name'], c['name'])]
        exact = [read[id(o)] for o in same if o.get('exact')]
        if exact:
            out[id(c)] = exact[0]
            continue
        same = [read[id(o)] for o in same]
        name = max((n for n, _r in same), key=marks)
        residence = max((r for _n, r in same), key=marks)
        out[id(c)] = (fixes.get(name, name), fixes.get(residence, residence))
    return out


def write(all_units, path, vocab, fixes={}):
    """`fixes`: restored spelling -> the printed one, for names and places
    the vocabulary gets wrong (manual `SPELLINGS`)."""
    lines_ = []
    for number, u in sorted(all_units.items()):
        spelled = _spellings(u, vocab, fixes)
        last = u['rounds'][-1]['candidates']
        winner = next((c for c in last if c['name'] == u['winner']), None) \
            or next(c for c in last if _same_person(c['name'], u['winner']))
        lines_.append(f"    {number}: {{'name': {unit_name(u['name'], vocab)!r}, 'rounds': [")
        for r in u['rounds']:
            reg, cast, inv = r['figures']
            lines_.append(f"        {{'registered': {reg}, 'cast': {cast}, 'invalid': {inv}, 'candidates': [")
            for c in r['candidates']:
                name, res = spelled[id(c)]
                lines_.append(f"            ({name!r}, {res!r}, {party_code(c['party'])!r}, {c['votes']}),")
            lines_.append('        ]},')
        lines_.append(f"    ], 'winner': {spelled[id(winner)][0]!r}}},")
    body = '\n'.join(lines_)
    text = Path(path).read_text(encoding='utf-8')
    start = text.index('DISTRICTS = {') + len('DISTRICTS = {')
    end = text.index('\n}\n', start)
    Path(path).write_text(text[:start] + '\n' + body + text[end:], encoding='utf-8')


def unit_name(name, vocab):
    """'ZAGREB - CRNOMEREC II' -> 'Zagreb - Črnomerec II'."""
    name = _roman(name)
    m = re.match(r'^(.*?)\s+([IVX]+)$', name)
    base, num = (m.group(1), ' ' + m.group(2)) if m else (name, '')
    return ' - '.join(restore(p, vocab) for p in re.split(r'\s*-\s*', base)) + num


def _roman(name):
    """Unit names end in a Roman numeral that OCR reads as "1", "!", "Y", "ПI"."""
    name = re.sub(r'\s+', ' ', name).strip(' .-')
    m = re.match(r'^(.*?)\s+([IVXYLl1!П|]{1,4}I*)$', name)
    if not m:
        return name
    num = m.group(2).replace('1', 'I').replace('l', 'I').replace('!', 'I').replace('|', 'I') \
        .replace('Y', 'V').replace('П', 'II')
    return f'{m.group(1)} {num}'



if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ocr_dir = Path(args[0])
    if '--crops' in sys.argv or '--missing-crops' in sys.argv:
        done = set()
        if '--missing-crops' in sys.argv and (ocr_dir / 'vur_crops.tsv').exists():
            with open(ocr_dir / 'vur_crops.tsv', encoding='utf-8') as f:
                done = {line.split('\t', 1)[0] for line in f}
        for spec in crop_specs(ocr_dir, Path(args[1])):
            if spec[0] not in done:
                print('\t'.join(str(s) for s in spec))
        sys.exit()
    all_units = units([ocr_dir / 'vur.tsv'], read_crops(ocr_dir))
    rounds = sum(len(u['rounds']) for u in all_units.values())
    cands = sum(len(r['candidates']) for u in all_units.values() for r in u['rounds'])
    print(f'{len(all_units)} units, {rounds} rounds, {cands} candidacies')
    from . import sabor_1990_vur_manual as manual
    manual.apply(all_units)
    problems = check(all_units, manual.ABSENT)
    for p in problems:
        print(' ', p)
    if '--write' in sys.argv:
        if problems:
            sys.exit(f'{len(problems)} problems left after the manual fixes; not writing')
        target = Path(__file__).with_name('sabor_1990_vur_data.py')
        write(all_units, target, vocabulary(), manual.SPELLINGS)
        print(f'wrote {target}')
