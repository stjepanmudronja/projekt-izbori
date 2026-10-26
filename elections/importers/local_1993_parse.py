"""Parse the 1993 lokalni izbori reports (scanned PDFs, OCR'd).

1993 (7 February, the Županijski dom's day) was the first local election of
the new territorial order, and like 1997 a **mixed system**: part of each
council and county assembly from lists, part in single-member wards
("izborne jedinice", plurality). DIP's report is one scan per county,
`1993/1993_1_Rezultati_NN_<county>.pdf`, holding the county assembly and
every gradsko / općinsko vijeće in turn (Grad Zagreb's file holds its
Gradska skupština alone); `tools/pdf_ocr` with OCR_DESKEW=1 reads each into
`1993/ocr/<name>.tsv`. The scans are skewed by up to a degree or so, which
drifts a row by 8 points across the page, so every page is straightened
before it is read.

A body's section:

    GRADSKO VIJEĆE GRADA GOSPIĆA
    Ukupno birača: 14.043 / Glasovalo birača: 6.093 43,38% / Nevažećih listića: 732
        (or one line: "Ukupno birača: 2.511, glasovalo: 1.896 ili 76%, nevažećih …")
    Pojedine gradske liste dobile su slijedeći broj glasova:
    1. HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ                 5.357   87,98%
    U gradsko vijeće po gradskim listama izabrani su:          (members — not stored)
    U gradsko vijeće po izbornim jedinicama izabrani su:
    then either full wards —
        Izborna jedinica I
        Ukupno birača: 1.076, glasovalo: 700 ili 65,05%, nevažećih listića: 286 ili 40,86%
        1. kandidat   Mile Zalović        HNS        414
        Izabran je Mile Zalović
      ("Nisu održani izbori" where a ward did not vote: occupied territory)
    or, mostly in the općine, only the winners —
        I     Emil Badurina       HDZ

Checks, which the importer requires: list votes sum to cast − invalid
within `REPORT_GAP` (shares are printed of voters in some places and of
valid votes in others, so they repair misread counts but do not decide);
a full ward's candidates sum to its own cast − invalid and its stated
winner tops it.
"""
import itertools
import re
from difflib import SequenceMatcher
from pathlib import Path

from .local_1997_parse import (PARTY_CODES, REPORT_GAP, ROMAN, ROMAN_OF, _parties, _share_ok, _tokens, clean_party,
                               _variants, fold, number, percent)
from .local_1993_manual import (CONFIRMED_LISTS, CONFIRMED_WARDS, MANUAL_FIGURES, MANUAL_LISTS, MANUAL_LIST_VOTES,
                                MANUAL_WARD_FIGURES, MANUAL_WARDS)
from .ocr_rows import NUMERIC, Row, read, rows

YEAR = 1993

# OCR spells vijeće "VUECE", "VUJEĆE".
HEAD_RE = re.compile(r'^(zupan\w{0,3}sk\w*\s+skup|gradsk\w*\s+v[iu]\S*|op\S{0,3}insk\w*\s+v[iu]\S*|gradsk\w*\s+skup|kotarsk\w*\s+skup)')
WARD_RE = re.compile(r'^izborn\w*\s*jedinic\w*\s*(.*)$')
# "1. kandidat Mile Zalović"; Zadarsko-kninska prints "1. Viktor Jelečanin".
# The label as OCR reads it: "kandidat", "kadidat", "kandidai", "kandida".
# A fuzzy label needs its number ("Kardum" is a surname); bare "kandidat" not.
CAND_RE = re.compile(r'^\s*(?:(?P<a>\d{1,2})\s*[.,]?\s*ka\w{0,2}d\w{0,4}\b|kand\S{0,2}dat\S?|'
                     r'(?=\d{1,2}\s*[.,]\s*[A-ZČĆŠŽĐ])(?P<b>\d{1,2})\s*[.,])\s*(?P<name>.*)$', re.I)
WIN_RE = re.compile(r'^izabran\S?\s+je\s*:?\s*(.*)$', re.I)
# A Roman ward number heading a winners-only row, as OCR reads it.
ROMAN_CELL = re.compile(r'^[IVXLl1]{1,6}\.?$')
PAGE_HEADER = re.compile(r'^\s*[ivxl1]{1,6}\s*\.?\s*zupanij|^\s*\d{1,2}\s*\.\s*zupanij|^\s*xxi\s*\.?\s*grad zagreb')


def _text(cells):
    return ' '.join(t for _x, t, _c in cells).strip()


def _ffold(s):
    return fold(s).replace('ı', 'i')


def _skews(path):
    """{page: degrees} from the `page <TAB> skew <TAB> degrees` lines."""
    out = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        p = line.split('\t')
        if len(p) == 3 and p[1] == 'skew':
            out[int(p[0])] = float(p[2])
    return out


def _roman(s):
    s = s.strip(' .,:').upper().replace('L', 'I').replace('1', 'I')
    return ROMAN.get(s)


INLINE = {
    'registered': re.compile(r'ukupno\s*\S*\s*:?\s*([\d.,]+)'),
    'cast': re.compile(r'glasoval\w*\s*\S*?\s*:?\s*([\d.,]+)(?:\s*ili\s*([\d.,]+)\s*%)?'),
    'invalid': re.compile(r'nevaz\S*\s*\S*\s*:?\s*([\d.,]+)(?:\s*ili\s*([\d.,]+)\s*%)?'),
}


def inline_figures(text):
    """{registered, cast, invalid[, cast_pct, invalid_pct]} from a one-line
    turnout ("Ukupno birača: 1.076, glasovalo: 700 ili 65,05%, nevažećih
    listića: 286 ili 40,86%"). A figure the line leaves blank is absent."""
    f = _ffold(text)
    out = {}
    for key, rx in INLINE.items():
        m = rx.search(f)
        if not m:
            continue
        n = number(m.group(1).rstrip('.,'))
        if n is not None:
            out[key] = n
        if key != 'registered' and m.lastindex and m.lastindex >= 2 and m.group(2):
            p = percent(m.group(2) + '%')
            if p is None and re.fullmatch(r'\d{1,3}', m.group(2)):
                p = float(m.group(2))
            if p is not None:
                out[key + '_pct'] = p
    return out


def _is_toc(page_rows):
    """The county's contents page: headings followed by dot leaders and a
    page number (OCR keeps one or the other)."""
    heads = [r for r in page_rows if HEAD_RE.match(_ffold(_text(r)))]
    return len(heads) >= 3 and sum(1 for r in heads if '...' in _text(r)
                                   or re.search(r'\d{1,3}\s*$', _text(r))) >= 2


def _furniture(f, cells):
    if PAGE_HEADER.match(f):
        return True
    # A lone page number at the foot.
    return len(cells) == 1 and re.fullmatch(r'\d{1,3}', cells[0][1].strip()) is not None and cells[0][0] > 200


def toc_entries(path):
    """The headings a county's contents page lists, in order."""
    out = []
    for pg, boxes in sorted(read(path).items()):
        page_rows = rows(boxes)
        if _is_toc(page_rows):
            # One heading per box: OCR fuses two contents lines into a row.
            out += [t for r in page_rows for _x, t, _c in r if HEAD_RE.match(LEAD_JUNK.sub('', _ffold(t)))]
    return out


def parse_file(path):
    """Sections of one county's OCR'd report, in order."""
    pages = read(path)
    skews = _skews(path)
    sections, cur, phase, ward = [], None, None, None
    for pg in sorted(pages):
        page_rows = rows(pages[pg])
        if _is_toc(page_rows):
            continue
        for cells in page_rows:
            cells.page = pg
            text = _text(cells)
            f = _ffold(text)
            if not text or _furniture(f, cells):
                continue
            if HEAD_RE.match(LEAD_JUNK.sub('', f)) and 'izabran' not in f and 'liste' not in f:
                text, f = LEAD_JUNK.sub('', text), LEAD_JUNK.sub('', f)
                # A heading repeated at the top of a continuation page is the
                # same body.
                if cur and fold(cur['heading']) == f:
                    continue
                cur = {'heading': text, 'page': pg, 'top': cells.top, 'skew': skews.get(pg, 0),
                       'figures': {}, 'list_rows': [], 'lists': [], 'wards': []}
                sections.append(cur)
                phase, ward = 'figures', None
                continue
            if cur is None:
                continue
            if phase == 'figures' and 'nisu odrzani' in f:
                cur['not_held'] = True          # Kistanje: no candidates stood
                continue
            if f.startswith('pojedine'):
                if cur['list_rows']:
                    # A second list table: the next body's heading was lost.
                    cur.setdefault('problems', []).append(f'a second list table on page {pg}: heading lost')
                phase = 'lists'
                continue
            if f.startswith('u ') and re.search(r'izabran\w*\s+su\b', f):
                phase = 'wards' if 'jedinic' in f else 'members'
                ward = None
                continue
            if phase == 'figures':
                fig = inline_figures(text)
                if len(fig) >= 2 and 'ukupno' in f and ('glasoval' in f or 'nevaz' in f):
                    cur['figures'].update(fig)
                    if re.search(r'nevaz\S*\s+listi\S*\s*:?\s*$', f):
                        cur['invalid_blank'] = True
                    continue
                if re.search(r'^nevaz\S*\s+listi\S*\s*:?\s*$', f):
                    cur['invalid_blank'] = True
                    continue
                key = ('registered' if f.startswith('ukupno') else 'cast' if f.startswith('glasoval')
                       else 'invalid' if f.startswith('nevaz') else None)
                if key:
                    # The label and its count can share a box ("Glasovalo
                    # birača: 73.802"), so the count is the row's first
                    # number that is not a share.
                    rest = re.sub(r'\d{1,3}\s*[.,]\s*\d{1,2}\s*%', ' ', text.split(':', 1)[-1])
                    nums = [n for t in re.findall(r'\d[\d.,]*', rest) for n in [number(t.rstrip('.,'))]
                            if n is not None]
                    pcts = [p for _x, t, _c in cells for p in [percent(t)] if p is not None]
                    if nums:
                        cur['figures'][key] = nums[0]
                    if pcts:
                        cur['figures'][key + '_pct'] = pcts[0]
                continue
            if phase == 'lists':
                cur['list_rows'].append(cells)
                continue
            if phase != 'wards':
                continue
            m = WARD_RE.match(f)
            if m:
                ward = {'label': m.group(1), 'figures': {}, 'rows': [], 'page': pg, 'top': cells.top,
                        'skew': skews.get(pg, 0)}
                cur['wards'].append(ward)
                continue
            if f.startswith('nisu odrzani') or 'nisu odrzani' in f:
                if ward is not None:
                    ward['not_held'] = True
                continue
            first = cells[0][1].strip()
            # The numeral can share the name's box ("XIV Ante Bujić").
            # Only between wards: inside a full ward the same shape is a
            # garbled line ("V. Kando bira…", "L Kandidat Željko Gojšić").
            fm = re.match(r'^([IVXL]{1,6})\.?\s+([A-ZČĆŠŽĐ].*)$', first)
            if fm and _roman(fm.group(1)) and ward is None and not CAND_RE.match(text) \
                    and not re.search(r'\d|kand', fm.group(2), re.I):
                x0, _t, conf = cells[0]
                cells = Row(cells.top, [(x0, cells.top, 0, conf, fm.group(1)), (x0 + 30, cells.top, 0, conf, fm.group(2))]
                            + [(x, cells.top, 0, c, t) for x, t, c in cells[1:]])
                cells.page = pg
                first = fm.group(1)
            if ROMAN_CELL.match(first) and _roman(first) and len(cells) >= 2 and not CAND_RE.match(text):
                # A winners-only row: "IV  dipl.ing. Nenad Peranić  HSS,HSLS".
                ward = {'label': first, 'figures': {}, 'rows': [cells], 'page': pg, 'top': cells.top,
                        'skew': skews.get(pg, 0), 'winner_only': True}
                cur['wards'].append(ward)
                ward = None
                continue
            # A turnout or candidate line after a ward's "Izabran je" line (or
            # before any ward) starts the next ward, whose heading OCR lost
            # (Varaždin assembly I-II, Karlovac V at the top of a page); so
            # does a full turnout line under a ward that has candidates.
            opens = (TURNOUT_RE.search(f) and len(inline_figures(text)) >= 2) or \
                CAND_RE.match(LEAD_JUNK.sub('', text))
            if ward is None:
                closed = not any(w.get('winner_only') for w in cur['wards'])
            else:
                closed = any(_ffold(_text(r)).startswith('izabran') for r in ward['rows'])
            if (opens and closed and not WIN_RE.match(text.strip())) or (
                    ward is not None and TURNOUT_RE.search(f) and len(inline_figures(text)) >= 3 and any(
                    CAND_RE.match(LEAD_JUNK.sub('', _text(r))) for r in ward['rows'])):
                ward = {'label': '?', 'figures': {}, 'rows': [], 'page': pg, 'top': cells.top,
                        'skew': skews.get(pg, 0), 'heading_lost': True}
                cur['wards'].append(ward)
            if ward is None:
                continue
            ward['rows'].append(cells)
    for sec in sections:
        read_lists(sec)
        for w in sec['wards']:
            read_ward(w)
    return sections


# ---- lists ------------------------------------------------------------------

LEAD_RE = re.compile(r'^\s*(\d{1,2})\s*[.,]\s*(.*)$')
RIGHT_X = 360


def read_lists(sec, votes=None, pcts=None):
    """A list block paired by order: numbered name lines in printed order
    (continuation lines join the entry above), counts and shares top to
    bottom. `votes` / `pcts` replace the page's column when a re-read
    supplies them."""
    entries, right, closed = [], [], True
    for r in sec['list_rows']:
        line = ' '.join(t for x, t, _c in r if not (x >= RIGHT_X and NUMERIC.match(t))).strip()
        # A count fused onto the name box ("HRVATSKA STRANKA PRAVA - HSP 7.670").
        line = re.sub(r'(?<!BR\.)(?<!BR)\s+\d{1,3}(?:[.,]\d{3})*\.?(?:\s+\d{1,3}[.,]\d{1,2}\s*%)?\s*$', '', line)
        line = line.replace('STRAKA', 'STRANKA')          # Zagreb's and Podgorač's SNS
        # A count and its share can share a box ("1.764 58,31%").
        counts = [tok for x, t, _c in r if x >= RIGHT_X and NUMERIC.match(t)
                  for tok in re.findall(r'[\d.,]+\s*%?', t.replace(' %', '%'))]
        right += counts
        if not line:
            continue
        # A list's count is printed on its last line, so the line after a
        # count starts the next list even when OCR lost its number.
        m = LEAD_RE.match(line)
        if m and m.group(2) and (int(m.group(1)) == len(entries) + 1 or not entries):
            entries.append([m.group(2)])
        elif entries and (not closed or re.match(r'^\W*nos(itelj)?\b', line, re.I)):
            # A holder line ("nositelj Rudi Debelec") follows its list's count.
            entries[-1].append(line)
        else:
            entries.append([m.group(2) if m and m.group(2) else line])
        closed = bool(counts)
    if votes is None:
        votes = [number(t) for t in right if '%' not in t and number(t) is not None]
    if pcts is None:
        pcts = [percent(t) for t in right if percent(t) is not None]
    sec['lists'] = [{'lines': lines, 'votes': votes[i] if len(votes) == len(entries) else None,
                     'pct': pcts[i] if len(pcts) == len(entries) else None}
                    for i, lines in enumerate(entries)]
    sec['list_columns'] = (len(entries), len(votes), len(pcts))


def share_fits(votes, base, pct):
    """A printed share agrees with votes / base, rounded or cut to the
    precision it is printed with (whole, one or two decimals)."""
    if not base:
        return False
    a = 100 * votes / base
    step = 1.0 if pct == int(pct) and pct >= 10 else 0.1 if round(pct, 1) == pct else 0.01
    return pct - step / 2 - 1e-9 <= a < pct + step + 1e-9


def settle_lists(sec):
    """Problems with the list part, after repairing a misread count from its
    share where exactly one count fits."""
    lists, fig = sec['lists'], sec['figures']
    if not lists:
        return []
    valid = fig['cast'] - fig['invalid'] if {'cast', 'invalid'} <= fig.keys() else None
    if any(e['votes'] is None for e in lists):
        n, nv, npct = sec.get('list_columns', (0, 0, 0))
        return [f'{n} lists but {nv} counts / {npct} shares read']
    total = sum(e['votes'] for e in lists)
    # A count paired with the wrong list can leave the sum right; its share
    # then fits another list's count. (A share fitting nothing is common
    # and the report's own: Gospić prints 5.357 as 87,98 %, of no total.)
    bases = [b for b in (total, valid, fig.get('cast')) if b]
    fits = lambda v, p: any(share_fits(v, b, p) for b in bases)
    off = [e for e in lists if e['pct'] is not None and not fits(e['votes'], e['pct'])
           and any(fits(o['votes'], e['pct']) for o in lists if o is not e)]
    if off:
        return [f'{len(off)} list count(s) do not fit their printed share '
                f'({", ".join(str(e["votes"]) + " / " + str(e["pct"]) + "%" for e in off)})']
    if valid is not None and abs(total - valid) <= REPORT_GAP:
        return []
    # Lists a few dozen votes off cast − invalid with every count confirmed
    # — by its printed share, or by the crop reading it the same — is the
    # report's own gap (as in 2001), not a misread.
    if valid is not None and abs(total - valid) <= 0.01 * valid + REPORT_GAP and all(
            (e['pct'] is not None and any(share_fits(e['votes'], b, e['pct']) for b in (total, valid, fig['cast'])))
            or e.get('confirmed') for e in lists):
        sec.setdefault('notes', []).append(f'lists sum {total}, cast - invalid {valid}: the report\'s own gap')
        return []
    if valid is None and 'cast' in fig and 'invalid' not in fig:
        # The report leaves the invalid count blank (Ljubeščica, Gornji
        # Kneginec) or prints none (Bibinje): the lists can only be checked
        # against the voters.
        if total <= fig['cast'] and all(e['pct'] is None or any(
                share_fits(e['votes'], b, e['pct']) for b in (total, fig['cast'])) for e in lists):
            sec.setdefault('notes', []).append('invalid count left blank in the report' if sec.get('invalid_blank')
                                               else 'no invalid count printed')
            return []
    # One count misread: the one-digit change of one count that makes the
    # lists sum to cast − invalid and agrees with its printed share.
    if valid is not None:
        fixes = []
        for e in lists:
            for v in _variants(e['votes']):
                if total - e['votes'] + v == valid and (e['pct'] is None or any(
                        _share_ok(v, base, e['pct']) for base in (valid, fig['cast']))):
                    fixes.append((e, v))
        if len(fixes) == 1:
            e, v = fixes[0]
            sec.setdefault('notes', []).append(f'list {e["lines"][0][:30]!r} {e["votes"]} -> {v}')
            e['votes'] = v
            return []
    return [f'lists sum {total} != cast - invalid {valid}']


# ---- wards ------------------------------------------------------------------

PARTY_X, VOTES_X = 250, 330


def _lead(m):
    lead = m.group('a') or m.group('b')
    return int(lead) if lead else None


def _cells_split(cells):
    """(label, name, party, votes) of a candidate row."""
    name, party, votes = [], [], None
    for x, t, _c in cells:
        n = number(t)
        if n is not None and x >= VOTES_X:
            votes = n if votes is None else votes
            continue
        (name if x < PARTY_X else party).append(t)
    return ' '.join(name).strip(), ' '.join(party).strip(), votes


# Specks before a row's first word ("......, 1. kandidat").
LEAD_JUNK = re.compile(r'^[^\w]+')


# A ward's turnout line, however garbled ("V. kano bira a 692 Sposovalo: 597
# li 86. 21%. nevažecih lisića").
TURNOUT_RE = re.compile(r'ukupno|glasov|sovalo|nevaz|listic|lisic|bira\S*\s*:?\s*\d|\d\s*%')


# A winners-only row can say the ward returned no one instead of a name.
NO_WINNER = re.compile(r'nisu\s+(provedeni|odrzani)|izbori\s+nisu|nema\s+kandidata|nije\s+(izabran|bilo|se\s+glasovalo)|nitko\s+nije|nisu\s+istaknuti|provedeni\s+izbor|nisu\s+glasoval|nije\s+predlozen|ponavlja|bez\s+predlozenih'
                       r'|glasovalo\s+0|nije\s+glasovano')
# A title and its lowercase continuations ("dr.stom.", "dipl.ing."); not the
# name glued after it ("Dr.Juraj Medved").
TITLE_IN_NAME = re.compile(r'(?<!\S)(?:prim\.\s*dr|prim|dr|mr|prof|dipl|dip|ing|stom|oec|iur|med|vet|sc|mag|bacc|el)\.'
                           r'(?:[a-zčćšž]+\.)*\s*', re.I)


PARTY_START = re.compile(r'\s+(?=(?:[A-ZČĆŠŽĐ]{2,}[\d-]*|Nezavisn\w*|NEZAVISN\w*)(?:[\s,.-]|$))')


def split_name_party(text):
    """(name, party) of a winners-only row's text after its numeral: the
    party starts at the first all-capitals code ("HSS,HSLS", "HDZ") or
    "Nezavisni". Columns cannot decide it — the party column moves from page
    to page."""
    parts = PARTY_START.split(text.strip(), maxsplit=1)
    name = parts[0].strip(' ,;')
    party = parts[1].strip(' .,;:') if len(parts) > 1 else ''
    return name, party


# Letters Vision's Czech / Polish / Romanian models put for Croatian ones.
OCR_LETTERS = str.maketrans({'ň': 'n', 'ş': 's', 'Ş': 'S', 'ţ': 't', 'ř': 'r', 'ě': 'e', 'ů': 'u',
                             'ľ': 'l', 'ĺ': 'l', 'ŕ': 'r'})


def clean_person(name):
    """A printed name made tokenisable: dotless ı, a title glued on after
    a comma ("Cekol,dipl.ing."), titles inside the name ("Krešo dr.stom.
    Kovačiček")."""
    name = name.replace('ı', 'i').replace('İ', 'I').translate(OCR_LETTERS).replace('*', '')
    name = re.sub(r'\bpok\.\s*\S+\s*', '', name)          # "Miho pok. Miha Bego"
    name = re.sub(r'^izabran\S?\s+je\s*:?\s*', '', name, flags=re.I)
    # Nicknames: "Antun (Tugo) Bakija", 'Ivan Dabo "Đono"'.
    name = re.sub(r'\s*\([^)]*\)|\s*"[^"]*"|\s*„[^"“”]*["“”]', '', name)
    name = re.sub(r',(?=\S)', ', ', name)
    head, sep, tail = name.partition(',')
    head = TITLE_IN_NAME.sub('', head).strip()
    return f'{head}{sep}{tail}' if sep else head


def read_ward(w, votes_override=None):
    if w.get('winner_only'):
        cells = w['rows'][0]
        rest = [(x, t, c) for x, t, c in cells[1:]]
        if NO_WINNER.search(_ffold(_text(rest))):
            w['not_held'] = True
            w['candidates'] = []
            return
        name, party = split_name_party(_text(rest))
        w['candidates'] = [{'name': clean_person(name), 'party': party, 'votes': None}]
        w['winner_name'] = name
        return
    cands, winner = [], None
    for cells in w['rows']:
        top, page = cells.top, cells.page
        text = _text(cells)
        f = _ffold(text)
        if TURNOUT_RE.search(f):
            turnout = [c for c in cells if TURNOUT_RE.search(_ffold(c[1]))]
            fig = inline_figures(' '.join(t for _x, t, _c in turnout))
            if fig and not w['figures']:
                w['figures'] = fig
            # Vision can fuse the turnout line with the first candidate's
            # into one tall box row: the rest of the row is that candidate.
            cells = [c for c in cells if c not in turnout]
            if not any(CAND_RE.match(t) for _x, t, _c in cells):
                continue
            text = _text(cells)
            f = _ffold(text)
        m = WIN_RE.match(text.strip())
        if m or f.startswith('izabran'):
            win_cells = [(x, t, c) for x, t, c in cells if x < PARTY_X]
            winner = re.sub(r'^\s*izabran\S?\s+je\s*:?\s*', '', ' '.join(t for _x, t, _c in win_cells),
                            flags=re.I).strip()
            continue
        name, party, votes = _cells_split(cells)
        name = LEAD_JUNK.sub('', name)
        # Two candidate lines fused into one box ("Josip Mikan 3. kandidat
        # Dragica Mrakuzić"): the first keeps the row's party and count only
        # if the second has none of its own, which a fused box cannot tell,
        # so both are left without and the crops supply them.
        parts = re.split(r'\s+(?=\d{1,2}\s*[.,]\s*kand\S{0,2}dat)', name)
        if len(parts) > 1 and CAND_RE.match(parts[0]):
            for part in parts:
                pm = CAND_RE.match(part)
                cands.append({'lead': _lead(pm) if pm else None,
                              'name': clean_person((pm.group('name') if pm else part).strip()),
                              'party': '', 'votes': None, 'top': top, 'page': page})
            continue
        cm = CAND_RE.match(name)
        if cm:
            cands.append({'lead': _lead(cm), 'name': clean_person(cm.group('name').strip()),
                          'party': party, 'votes': votes, 'top': top, 'page': page})
        elif cands and not cands[-1]['name'] and name and votes is None:
            cands[-1]['name'] = clean_person(name)
        elif cands and votes is not None and cands[-1]['votes'] is None and not name:
            cands[-1]['votes'] = votes
            cands[-1]['party'] = cands[-1]['party'] or party
    if not cands and winner:
        # Only the winner is printed, under the ward's turnout (Nova
        # Gradiška): "Izabran je Ante Solić   HDZ".
        win_row = next(r for r in w['rows'] if _ffold(_text(r)).startswith('izabran'))
        name = clean_person(winner)
        if NO_WINNER.search(_ffold(name)):
            w['not_held'] = True
        else:
            party = ' '.join(t for x, t, _c in win_row if x >= PARTY_X)
            cands = [{'lead': 1, 'name': name, 'party': party, 'votes': None, 'top': win_row.top,
                      'page': win_row.page}]
            w['winner_only'] = True
    if votes_override is not None and len(votes_override) == len(cands):
        for c, v in zip(cands, votes_override):
            c['votes'] = v
    w['candidates'] = cands
    w['winner_name'] = winner or ''


def settle_ward(w):
    if w.get('not_held'):
        return []
    cands = w['candidates']
    if not cands:
        return ['no candidates']
    if w.get('winner_only'):
        c = cands[0]
        if len(_tokens(c['name'])) < 2 and c.get('crop_name'):
            crop = c['crop_name']
            # The crop spans the row: party codes follow the name.
            crop = re.split(r'\s+(?=[A-ZČĆŠŽĐ]{2,}(?:[\s,-]|$))', crop)[0]
            c['name'] = crop
        return [] if len(_tokens(c['name'])) >= 2 else [f'winner {c["name"]!r} has no full name']
    problems = []
    fig = w['figures']
    if len(cands) == 1 and cands[0]['votes'] is None:
        return problems
    if any(c['votes'] is None for c in cands):
        return ['candidate without votes']
    top = max(cands, key=lambda c: c['votes'])
    if sum(1 for c in cands if c['votes'] == top['votes']) > 1:
        problems.append('tie for first')
    win = ' '.join(_tokens(clean_person(w.get('winner_name') or '')))
    # Order-free: some winner lines put the surname first ("Bakija Antun").
    key = lambda n: ' '.join(sorted(fold(n).split()))
    if win and key(' '.join(_tokens(top['name']))) != key(win):
        from difflib import SequenceMatcher
        if SequenceMatcher(None, key(top['name']), key(win)).ratio() < 0.6:
            problems.append(f'stated winner {win!r} is not the top candidate {top["name"]!r}')
    if {'cast', 'invalid'} <= fig.keys():
        s = sum(c['votes'] for c in cands)
        if abs(s - (fig['cast'] - fig['invalid'])) > REPORT_GAP:
            problems.append(f'candidates sum {s} != cast - invalid {fig["cast"] - fig["invalid"]}')
    for n, c in enumerate(cands, 1):
        if len(_tokens(c['name'])) < 2:
            problems.append(f'candidate {n} has no full name ({c["name"]!r})')
    return problems


# ---- second readings from crops --------------------------------------------
#
# Vision skips some short numbers on a full page and cuts a long turnout line
# short ("Ukupno birača: 1.905" and nothing more), so every ward's count,
# name and party columns and its turnout line, and every list block's count
# column, are read again from crops (`tools/pdf_ocr_crops`, CROP_LINES=1),
# cut from the same straightened page. `--crops` prints the specs; the
# readings go to `<ocr dir>/crops.tsv`.

def _by_page(rows_):
    out = {}
    for r in rows_:
        out.setdefault(r.page, []).append(r)
    return out


def _ward_layout(w):
    """(candidate rows, winner row, figures row, party x, count x) of a full ward."""
    cand_rows, win_row, fig_row = [], None, None
    for r in w['rows']:
        f = _ffold(_text(r))
        if TURNOUT_RE.search(f) and fig_row is None:
            fig_row = r
            if any(CAND_RE.match(t) for _x, t, _c in r):
                cand_rows.append(r)
        elif f.startswith('izabran'):
            win_row = r
        elif CAND_RE.match(LEAD_JUNK.sub('', ' '.join(t for x, t, _c in r if x < PARTY_X))):
            cand_rows.append(r)
    party_x = min((x for r in cand_rows for x, t, _c in r if PARTY_X <= x and number(t) is None), default=None)
    count_x = min((x for r in cand_rows for x, t, _c in r if x >= VOTES_X and number(t) is not None), default=None)
    return cand_rows, win_row, fig_row, party_x, count_x


def section_crops(sec):
    """[(suffix, page, x, y, w, h)] of a section's crops: "L" its list
    counts, "W<n>|F|N|P" ward n's turnout line, names, and parties with
    counts."""
    out = []
    for pg, rs in _by_page(sec['list_rows']).items():
        out.append(('L', pg, RIGHT_X - 10, min(r.top for r in rs) - 3, 585 - RIGHT_X + 10,
                    max(r.top for r in rs) - min(r.top for r in rs) + 17))
    count_xs = [x for w in sec['wards'] if not w.get('winner_only')
                for x in [_ward_layout(w)[4]] if x is not None]
    sec_count_x = min(count_xs) if count_xs else 380
    for wi, w in enumerate(sec['wards'], 1):
        wk = f'W{wi}'
        if w.get('winner_only'):
            r = next((r for r in w['rows'] if _ffold(_text(r)).startswith('izabran')), w['rows'][0])
            out.append((f'{wk}|N', r.page, 40, r.top - 3, 545, 17))
            continue
        cand_rows, win_row, fig_row, party_x, count_x = _ward_layout(w)
        if fig_row is not None:
            out.append((f'{wk}|F', fig_row.page, 40, fig_row.top - 3, 545, 17))
        if not cand_rows:
            continue
        party_x = party_x or 265
        count_x = min(count_x or sec_count_x, sec_count_x) - 12
        for pg, rs in _by_page(cand_rows).items():
            y0 = min(r.top for r in rs) - 3
            y1 = max(r.top for r in rs) + 14
            if win_row is not None and win_row.page == pg and win_row.top > y1:
                y1 = win_row.top - 1
            out.append((f'{wk}|N', pg, 40, y0, party_x - 43, y1 - y0))
            # Parties and counts in one crop: a crop of digits alone gives
            # Vision nothing to orient by, and it reads some upside down
            # (899 / 876 as "668" / "9L8").
            out.append((f'{wk}|P', pg, party_x - 3, y0, 588 - party_x, y1 - y0))
    return out


def crop_id(file, pg, x, y, w, h):
    """A crop's key in `crops.tsv`: its file and box, so a crop whose box a
    parser change leaves alone keeps its reading."""
    return f'{file}|{pg}|{x:.1f}|{y:.1f}|{w:.1f}|{h:.1f}'


def crop_specs(folder, pdf_dir, missing_only=False):
    done = set(read_crops(folder)) if missing_only else set()
    specs = []
    for path in sorted(Path(folder).glob(f'{YEAR}_*.tsv')):
        pdf = Path(pdf_dir) / path.name.replace('.tsv', '.pdf')
        skews = _skews(path)
        for sec in parse_file(path):
            for _suffix, pg, x, y, w, h in section_crops(sec):
                cid = crop_id(path.name, pg, x, y, w, h)
                if cid not in done:
                    specs.append(f'{cid}\t{pdf}\t{pg}\t{x:.1f}\t{y:.1f}\t{w:.1f}\t{h:.1f}\t{skews.get(pg, 0)}')
                    done.add(cid)
    return specs


def read_crops(folder):
    """{key: [(y, text)]} from `crops.tsv`, in page order."""
    path = Path(folder) / 'crops.tsv'
    out = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            p = line.split('\t')
            # Confidence 0.3 is Vision's noise: the edge of a neighbouring
            # line, specks ("-.a.", "=-larmnfan -e").
            if len(p) >= 4 and float(p[1]) > 0.3:
                out.setdefault(p[0], []).append((float(p[2]), p[3]))
                if len(p) >= 5:
                    out.setdefault('__x__', {}).setdefault(p[0], []).append((float(p[4]), p[3]))
    return out


def _party_count_lines(lines):
    """(parties, counts) from a party-and-count crop, top to bottom. A
    count fused to its party ("HDZ 876") is split off; a long coalition
    wrapping onto a second line ("HSLS,HNS," / "HKDS") is joined."""
    parties, counts = [], []
    for _y, t in sorted(lines):
        t = t.strip()
        m = re.match(r'^(.*?)\s*(\d{1,3}(?:[.,]\d{3})*|\d+)\s*$', t)
        if m and number(m.group(2)) is not None:
            counts.append(number(m.group(2)))
            t = m.group(1).strip()
        t = t.strip(' .,;:')
        if not t or not re.search(r'[A-ZČĆŠŽĐ]{2}|[Nn]ezavis', t) or fold(t).startswith('izabran'):
            continue
        if parties and parties[-1].endswith(','):
            parties[-1] = f'{parties[-1]} {t}'
        else:
            parties.append(t)
    return parties, counts


def _crop_counts(lines):
    return [n for _y, t in sorted(lines) for n in [number(t.replace(' ', ''))] if n is not None]


def _ward_ok(cands, fig):
    if any(c['votes'] is None for c in cands):
        return False
    if {'cast', 'invalid'} <= fig.keys():
        return abs(sum(c['votes'] for c in cands) - (fig['cast'] - fig['invalid'])) <= REPORT_GAP
    return True


def apply_crops(sec, file, all_crops):
    # This section's readings under their logical keys; a block spanning
    # two pages reads in page order.
    crops, crops_x, key = {}, {}, 'S'
    for suffix, pg, x, y, w, h in section_crops(sec):
        cid = crop_id(file, pg, x, y, w, h)
        crops.setdefault(f'{key}|{suffix}', []).extend(
            (pg * 10000 + yy, t) for yy, t in all_crops.get(cid, []))
        crops_x.setdefault(f'{key}|{suffix}', []).extend(all_crops.get('__x__', {}).get(cid, []))
    crops = {k: v for k, v in crops.items() if v}
    if f'{key}|L' in crops and sec['lists']:
        col = sorted(crops[f'{key}|L'])
        votes = [number(t) for _y, t in col if '%' not in t and number(t) is not None]
        pcts = [percent(t) for _y, t in col if percent(t) is not None]
        page = [dict(e) for e in sec['lists']]
        if len(votes) == len(page):
            for e, v in zip(sec['lists'], votes):
                e['confirmed'] = e['votes'] == v
            trial = [dict(e, votes=v) for e, v in zip(page, votes)]
            fig = sec['figures']
            valid = fig['cast'] - fig['invalid'] if {'cast', 'invalid'} <= fig.keys() else None
            page_ok = all(e['votes'] is not None for e in page) and valid is not None and \
                abs(sum(e['votes'] for e in page) - valid) <= REPORT_GAP
            if not page_ok:
                sec['lists'] = trial
                if len(pcts) == len(page):
                    for e, p in zip(sec['lists'], pcts):
                        e['pct'] = p
                sec['list_reread'] = True
    for wi, w in enumerate(sec['wards'], 1):
        wk = f'{key}|W{wi}'
        if w.get('winner_only'):
            if f'{wk}|N' in crops and w['candidates']:
                # Left to right; the numeral first.
                text = ' '.join(t for _x, t in sorted(crops_x.get(f'{wk}|N', [])))
                m = re.match(r'^\s*[IVXLl1]{1,6}\.?\s+(.*)$', text)
                name, party = split_name_party(m.group(1) if m else text)
                c = w['candidates'][0]
                c['crop_name'] = clean_person(name)
                c['crop_party'] = party
            continue
        if f'{wk}|F' in crops:
            fig = inline_figures(' '.join(t for _y, t in sorted(crops[f'{wk}|F'])))
            w['crop_figures'] = fig
            if len(fig) > len({k: v for k, v in w['figures'].items() if not k.endswith('_pct')}) or \
                    not {'registered', 'cast', 'invalid'} <= w['figures'].keys():
                if {'registered', 'cast', 'invalid'} <= fig.keys():
                    w['figures'] = fig
        cands = w['candidates']
        parties, votes = _party_count_lines(crops.get(f'{wk}|P', []))
        if f'{wk}|P' in crops and cands:
            w['crop_votes'] = votes
            if len(votes) == len(cands):
                trial = [dict(c, votes=v) for c, v in zip(cands, votes)]
                if not _ward_ok(cands, w['figures']) and _ward_ok(trial, w['figures']):
                    w['candidates'] = cands = trial
                    w['counts_reread'] = True
                elif not _ward_ok(cands, w['figures']) and w.get('crop_figures') and \
                        _ward_ok(trial, w['crop_figures']):
                    w['candidates'], w['figures'] = trial, w['crop_figures']
                    cands = trial
                    w['counts_reread'] = True
                elif not _ward_ok(cands, w['figures']):
                    # Each reading wrong somewhere: take each count from
                    # either, and keep the one combination that adds up.
                    options = [sorted({v for v in (c['votes'], cv) if v is not None})
                               for c, cv in zip(cands, votes)]
                    fits = {combo for combo in itertools.product(*options)
                            if _ward_ok([dict(c, votes=v) for c, v in zip(cands, combo)], w['figures'])}
                    if len(fits) == 1:
                        w['candidates'] = cands = [dict(c, votes=v) for c, v in zip(cands, fits.pop())]
                        w['counts_reread'] = True
        if f'{wk}|N' in crops:
            names = [t for _y, t in sorted(crops[f'{wk}|N'])]
            names = [CAND_RE.match(t).group('name').strip() if CAND_RE.match(t) else t for t in names
                     if CAND_RE.match(t) or re.search(r'[A-ZČĆŠŽĐ][a-zčćšžđ]+\s+\S', t)]
            names = [clean_person(t) for t in names if t and not _ffold(t).startswith('izabran')
                     and not TURNOUT_RE.search(_ffold(t))]
            w['crop_names'] = names
            if len(names) == len(cands):
                for c, t in zip(cands, names):
                    c['crop_name'] = clean_person(t)
                    if len(_tokens(c['name'])) < 2:
                        c['name'] = c['crop_name']
        if len(parties) == len(cands):
            for c, t in zip(cands, parties):
                c['crop_party'] = t
        # A candidate the page lost: the name crop numbers more of them. The
        # ward is rebuilt from the crops when all three columns agree.
        crop_names = w.get('crop_names') or []
        if len(crop_names) > len(cands) and len(parties) == len(crop_names) == len(votes):
            rebuilt = [{'lead': i + 1, 'name': n, 'crop_name': n, 'party': pt, 'crop_party': pt,
                        'votes': v} for i, (n, pt, v) in enumerate(zip(crop_names, parties, votes))]
            if _ward_ok(rebuilt, w['figures']):
                w['candidates'] = rebuilt
                w['rebuilt'] = True


HOLDER_RE = re.compile(r'\s*-?\s*\bnos(?:itelj)?\b\.?\s*(?:liste)?\s*:?\s*(.+)$', re.I)


def split_holder(lines):
    """(lines, holder) of a list entry: an independent list names its
    holder after "nositelj:" ("NEZAVISNA OPĆINSKA LISTA nositelj: Rade
    Rajnović", "NEZAVISNA LISTA - nos. Striga")."""
    text = ' '.join(lines)
    m = HOLDER_RE.search(text)
    if not m or not fold(text).startswith('nezavisn'):
        return lines, ''
    return [text[:m.start()].strip(' -,')], m.group(1).strip(' .,')


def ward_numbers(wards):
    """Each ward's number: its printed numeral where it reads as the next
    one up, else one more than the ward before (a lost heading, or OCR's
    "Il" / "1"). Numbering by position would shift every ward after a
    lost one."""
    out, prev = [], 0
    for w in wards:
        n = _roman(w.get('label') or '')
        out.append(n if n and n > prev else prev + 1)
        prev = out[-1]
    return out


# 1997's party codes plus those only 1993 used.
PARTY_CODES_1993 = PARTY_CODES | {'SDH', 'SSH', 'SDU', 'KNS', 'HRZ', 'HSNZ', 'DA', 'RIDS', 'SND', 'SSOH',
                                  'HKDS', 'HDS', 'SBHS', 'HSD', 'HČSP', 'IDS', 'DS', 'SRH'}


def _final_party(c):
    """The crop's party label if it reads as known parties, else the
    page's if that does; else the known party codes either reading holds
    (OCR wraps them in noise: "AITYTAT Želiko Klobučar HD7"), "Nezavisni
    kandidat", or a printed name of a party without a code ("Dalmatinska
    akcija"). Never noise."""
    for t in (c.get('crop_party'), c['party']):
        if t and clean_party(t):
            return clean_party(t)
    for t in (c['party'], c.get('crop_party')):
        codes = []
        for tok in re.findall(r'[A-ZČĆŠŽĐ0-9-]{2,}|RiDS', t or ''):
            tok = tok.upper() if tok == 'RiDS' else tok
            tok = re.sub(r'(?<=HD)7$', 'Z', tok)          # "HD7"
            if tok in PARTY_CODES_1993 and tok not in codes:
                codes.append(tok)
        if codes:
            return ', '.join(codes)
    for t in (c['party'], c.get('crop_party')):
        if re.search(r'n[ae]z[ae]vi[sc]n|bandidat|kandidat', fold(t or '')):
            return 'Nezavisni kandidat'
    raw = (c['party'] or '').strip(' .,;:')
    # A printed party name (lowercase words, no noise) stands as printed.
    return raw if re.fullmatch(r'[A-ZČĆŠŽĐ][a-zčćšžđ]+(?:[ ,-]+(?:i|[A-ZČĆŠŽĐa-zčćšžđ][a-zčćšžđ]*|[A-Z]{2,5}))*', raw) else ''


# ---- whole report -----------------------------------------------------------

# Headings OCR misread in a way the municipality match cannot absorb.
UNIT_FIXES = {'KARLOYCA': 'KARLOVCA'}


def _classify(heading):
    """(slug, level, unit) from "Gradsko vijeće grada Gospića" and kin."""
    f = _ffold(heading)
    words = heading.split()
    if f.startswith('zupan'):
        return 'local_county_assembly', 'county', ''
    if f.startswith('kotarsk'):
        # Kotarska skupština kotara Glina / Knin: the two kotari of the 1992
        # law, special districts for the Serb-majority areas.
        return 'local_kotar_assembly', 'kotar', 'KOTAR ' + words[-1].upper().strip(' .,')
    if f.startswith('gradsk') and 'skup' in f.split()[1]:
        return 'local_city_council', 'muni', ''          # Grad Zagreb's Gradska skupština
    slug = 'local_city_council' if f.startswith('gradsk') else 'local_municipal_council'
    unit = ' '.join(words[3:]) if len(words) > 3 else ''
    unit = re.sub(r'^[Ll]l(?=[a-zčćšžđ])', 'Il', unit)
    unit = unit.upper().strip(' .,')
    return slug, 'muni', UNIT_FIXES.get(unit, unit)


def parse_report(folder):
    contests, problems, notes = [], [], []
    crops = read_crops(folder)
    for path in sorted(Path(folder).glob(f'{YEAR}_*.tsv')):
        code = re.search(r'_(\d{2})_', path.name).group(1)
        sections = parse_file(path)
        toc = toc_entries(path)
        # Only a shortfall matters: OCR drops contents lines (Dubrava,
        # Štefanje), never adds a body.
        if toc and len(toc) > len(sections):
            problems.append(f'{code}: contents page lists {len(toc)} bodies, parsed {len(sections)}')
        for sec in sections:
            apply_crops(sec, path.name, crops)
            slug, level, unit = _classify(sec['heading'])
            where = f'{code} {unit or slug}'
            if sec.get('not_held') and not sec['list_rows'] and not sec['wards']:
                notes.append(f'{where}: no election held (no candidates)')
                continue
            key = (code, unit or slug)
            if key in MANUAL_FIGURES:
                sec['figures'].update({k: v for k, v in zip(('registered', 'cast', 'invalid'), MANUAL_FIGURES[key])
                                       if v is not None})
            if key in MANUAL_LISTS:
                sec['lists'] = [{'lines': name.split(' / '), 'votes': v, 'pct': None}
                                for name, v in MANUAL_LISTS[key]]
            if key in MANUAL_LIST_VOTES:
                if len(MANUAL_LIST_VOTES[key]) != len(sec['lists']):
                    raise ValueError(f'{key}: {len(sec["lists"])} lists parsed, '
                                     f'{len(MANUAL_LIST_VOTES[key])} manual counts')
                for e, v in zip(sec['lists'], MANUAL_LIST_VOTES[key]):
                    e['votes'], e['pct'] = v, None
            p = settle_lists(sec) + sec.get('problems', [])
            if key in CONFIRMED_LISTS or key in MANUAL_LISTS or key in MANUAL_LIST_VOTES:
                p = [x for x in p if not x.startswith('lists sum')]
            notes += [f'{where}: {n}' for n in sec.get('notes', [])]
            for i, w in zip(ward_numbers(sec['wards']), sec['wards']):
                w['number'] = i
                w['winner_name'] = clean_person(w.get('winner_name') or '')
                for c in w['candidates']:
                    c['party'] = _final_party(c)
                    # The straightened page reads rows reliably; a crop that
                    # names someone else caught its neighbours' noise (a
                    # winners-only crop spans the row: "TT 1 Stjepan
                    # Ključarić anrrrar"), so it may only refine the spelling.
                    page = ' '.join(_tokens(c['name']))
                    crop = ' '.join(_tokens(c.get('crop_name') or ''))
                    if c.get('crop_name') and len(page.split()) >= 2 and \
                            SequenceMatcher(None, fold(page), fold(crop)).ratio() < 0.75:
                        c['crop_name'] = None
                if MANUAL_WARDS.get((*key, i)) == []:
                    w['not_held'], w['candidates'] = True, []     # "Izbori nisu održani"
                elif (*key, i) in MANUAL_WARDS:
                    w['candidates'] = [{'lead': n, 'name': name, 'party': party, 'votes': v}
                                       for n, (name, party, v) in enumerate(MANUAL_WARDS[(*key, i)], 1)]
                    w['manual'] = True
                    w['winner_only'] = w.get('winner_only') and len(w['candidates']) == 1
                if (*key, i) in MANUAL_WARD_FIGURES:
                    w['figures'] = {k: v for k, v in zip(('registered', 'cast', 'invalid'),
                                                         MANUAL_WARD_FIGURES[(*key, i)]) if v is not None}
                wp = settle_ward(w)
                if (*key, i) in CONFIRMED_WARDS or w.get('manual'):
                    wp = [x for x in wp if 'candidates sum' not in x and 'stated winner' not in x]
                p += [f'ward {i}: {x}' for x in wp]
            problems += [f'{where}: {x}' for x in p]
            fig = sec['figures']
            entries = [{'parties': _parties(lines), 'holder': holder, 'votes': e['votes']}
                       for e in sec['lists'] for lines, holder in [split_holder(e['lines'])]]
            contests.append((code, {
                'slug': slug, 'level': level, 'unit': unit, 'round': 1,
                'registered': fig.get('registered'), 'cast': fig.get('cast'),
                'invalid': fig.get('invalid'), 'valid': sum(e['votes'] or 0 for e in entries),
                'entries': entries, 'wards': [w for w in sec['wards'] if not w.get('not_held')],
                'not_held': sum(1 for w in sec['wards'] if w.get('not_held')),
                'page': sec['page'], 'file': path.name,
            }))
    return contests, problems, notes


def main(folder):
    contests, problems, notes = parse_report(folder)
    print(f'{len(contests)} bodies, {sum(len(c["wards"]) for _k, c in contests)} wards, '
          f'{len(problems)} problems')
    for p in problems:
        print(' ', p)
    for n in notes:
        print('  note:', n)


if __name__ == '__main__':
    import sys
    if sys.argv[1] in ('--crops', '--missing-crops'):
        # python -m … --crops <ocr dir> <pdf dir> | CROP_LINES=1 tools/pdf_ocr_crops > <ocr dir>/crops.tsv
        # (--missing-crops: only boxes crops.tsv lacks, to append to it)
        print('\n'.join(crop_specs(sys.argv[2], sys.argv[3], sys.argv[1] == '--missing-crops')))
    else:
        main(sys.argv[1])
