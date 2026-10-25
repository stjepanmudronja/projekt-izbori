"""Parse the 1997 lokalni izbori reports (scanned PDFs, OCR'd).

1997 (13 April, the day of the Županijski dom election) elected councils and
county assemblies under a **mixed system**: part of each body from lists
(proportional, as every later year), part in single-member wards ("izborne
jedinice", plurality). DIP's reports are scans — one per county for the
gradska / općinska vijeća (`1997_1_…_NN_<county>.pdf`), one per county for
the županijska skupština (`1997_2_…_NN_<county>.pdf`, Grad Zagreb's Gradska
skupština as `…_21_Grad_Zagreb.pdf`) — read by `tools/pdf_ocr` (PDFKit +
Vision) into `1997/ocr/<name>.tsv`, one box per text run with its position.
`ocr_rows.rows` rebuilds the printed rows.

A body's section:

    Gradsko vijeće grada Gospića
    Ukupno birača: 15.077 / Glasovalo birača: 7.628 50.59 % / Nevažećih listića: 209
    Pojedine kandidatske liste dobile su:
    1. Hrvatska demokratska zajednica (HDZ)          4.960   66.86 %
    …
    U gradsko vijeće po kandidatskim listama izabrani su:   (members — not stored)
    U gradsko vijeće po izbornim jedinicama izabrani su:
    I. Izborna jedinica
    [Ukupno birača: 5.252, glasovalo: 3.427, nevažećih listića: 105]   (assemblies only)
    1. Ivan Herman            HSP     133
    …
    Izabran(a) je: Ivica Puškarić, (HDZ)

Checks, which the importer requires: list votes match their printed share of
the valid votes and sum to cast − invalid (no valid figure is printed, as in
2001); every ward's stated winner is its top candidate; an assembly ward's
candidates sum to its cast − invalid.
"""
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from .ocr_rows import NUMERIC, read, rows

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9,
         'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17,
         'XVIII': 18, 'XIX': 19, 'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24,
         'XXV': 25, 'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29, 'XXX': 30}


def fold(s):
    """Lowercase without diacritics, for matching OCR text against labels."""
    s = unicodedata.normalize('NFKD', s.replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


NUM_RE = re.compile(r'^[\d.,OoIl]+$')


def number(text):
    """An OCR'd count ("4.960", "1,086", "1.O86", "*817") as int, else None."""
    t = text.strip().strip('*,;:').replace(' ', '')
    if not t or not NUM_RE.match(t) or not re.search(r'\d', t):
        return None
    t = t.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
    if re.fullmatch(r'\d{1,3}([.,]\d{3})+', t):
        return int(re.sub(r'[.,]', '', t))
    if re.fullmatch(r'\d+', t):
        return int(t)
    return None


def percent(text):
    m = re.fullmatch(r'\s*(\d{1,3})[.,](\d{1,2})\s*%?\s*', text.replace(' ', ''))
    if m and '%' in text:
        return float(f'{m.group(1)}.{m.group(2)}')
    return None


# ---- rows -> sections -------------------------------------------------------

# "Opéinsko vijeće": OCR reads ć as é now and then.
HEAD_RE = re.compile(r'^(gradsko vijec|op\S{1,2}insko vijec|gradska skupstin|zupanijska skupstin)')
ENTRY_RE = re.compile(r'^(\d{1,2})\s*[.,]?\s*(.*)$')
# "II. Izborna jedinica", OCR'd as "Il.", "IIl.", "1." or "NV." — the numeral
# is not trusted; wards are numbered in order.
WARD_RE = re.compile(r'^(.{0,10}?)\s*izborna\s*jedinica', re.I)   # also "Izbornajedinica"   # "• Vill. Izborna jedinica"
FOOTER_UNIT_RE = re.compile(r'^(grad|opcina|općina)\s+(.+)$', re.I)


def _text(cells):
    return ' '.join(t for _x, t, _c in cells).strip()


# "Istarska žunaniia", "Zadarska župarija", "Istarska Yunaniia": the county
# footer however OCR spells its "županija".
COUNTY_FOOTER = re.compile(r'(ska|cka|nska)[\s-]+[zy2]\w{4,7}a\b')


def _is_furniture(f):
    # The page header, however OCR spells it ("rezuitatima", "rezulíatima",
    # "izbore", "gradskitvopdinskih").
    return (f.startswith('informac') or re.search(r'rezu\S{0,3}atima', f) is not None
            or ('clanova' in f and 'vijec' in f) or f.startswith('stranica')
            or re.match(r'^\d{1,2}\s*\.\s*\S+([\s-]+\S+)?[\s-]+zupani[ij]', f) is not None
            or (COUNTY_FOOTER.search(f) is not None and len(f.split()) <= 4))


def _footer_unit(cells):
    """The page footer's unit ("grad Novalja"), from its right-hand cell."""
    for x, t, _c in cells:
        m = FOOTER_UNIT_RE.match(t.strip())
        if x > 380 and m:
            return t.strip()
    return None


def _split_cells(cells, name_max=260, votes_min=430):
    """(lead number, name, party, votes, pct) of an entry/candidate row."""
    name, party, votes, pct = [], [], None, None
    for x, t, _c in cells:
        p = percent(t)
        if p is not None:
            pct = p
            continue
        n = number(t)
        if n is not None and x >= votes_min:
            votes = n if votes is None else votes
            continue
        (name if x < name_max else party).append(t)
    text = ' '.join(name).strip()
    m = ENTRY_RE.match(text)
    lead = int(m.group(1)) if m and m.group(2) else None
    if m and m.group(2):
        text = m.group(2)
    elif m and not m.group(2):
        lead, text = int(m.group(1)), ''
    return lead, text.strip(), ' '.join(party).strip(), votes, pct


# (file, page) where a unit resumes after its first pages are missing from
# the scan, with the unit's heading; `ward_offset` is how many of its wards
# were on the missing pages.
MISSING_FIRST_PAGES = {
    ('1997_1_Rezultati_gradska_opcinska_vijeca_16_Vukovarsko-srijemska.tsv', 4):
        'Gradsko vijeće grada Vinkovci',
}


def parse_file(path):
    """Sections of one OCR'd report, in order. A county-assembly report
    (`1997_2_…`) is one body whose heading every page repeats."""
    single = Path(path).name.startswith('1997_2_')
    pages = read(path)
    sections, cur, phase, ward = [], None, None, None
    for pg in sorted(pages):
        page_rows = rows(pages[pg])
        footer = next((u for r in page_rows for u in [_footer_unit(r)] if u), None)
        # The scan of Vukovar-Srijem jumps from page 483 (Ilok) to 486:
        # Vinkovci's first two pages — heading, figures, lists, wards I-II —
        # are missing, and its surviving wards III-VII would join Ilok's.
        if (Path(path).name, pg) in MISSING_FIRST_PAGES:
            head = MISSING_FIRST_PAGES[(Path(path).name, pg)]
            cur = {'heading': head, 'name_line': head, 'footer': footer, 'page': pg, 'top': 0,
                   'figures': {}, 'lists': [], 'wards': [], 'first_page_missing': True,
                   'ward_offset': 2}
            sections.append(cur)
            phase, ward = 'wards', None
        for cells in page_rows:
            cells.page = pg
            text = _text(cells)
            f = fold(text)
            if not text or _is_furniture(f) or _footer_unit(cells):
                continue
            if HEAD_RE.match(f) and single and cur:
                continue
            if HEAD_RE.match(f) and not (cur and cur['name_line'] == text):
                cur = {'heading': text, 'name_line': text, 'footer': footer, 'page': pg,
                       'top': cells.top, 'figures': {}, 'lists': [], 'wards': []}
                sections.append(cur)
                phase, ward = 'figures', None
                continue
            if cur is None:
                continue
            # A heading OCR lost: a second "Ukupno birača" / "Pojedine …" in a
            # section that already has lists starts the next unit, named by
            # the page footer.
            if (f.startswith('ukupno') and phase != 'wards' or f.startswith('pojedine')) and cur['lists']:
                name = f'{cur["heading"].split()[0]} {cur["heading"].split()[1]} {footer or "?"}'
                cur = {'heading': name, 'name_line': name, 'footer': footer, 'page': pg,
                       'top': cells.top, 'figures': {}, 'lists': [], 'wards': [],
                       'heading_from_footer': True}
                sections.append(cur)
                phase, ward = 'figures', None
            if f.startswith('pojedine'):
                phase = 'lists'
                continue
            if 'izabrani su' in f or 'izabrani' in f and 'jedinicama' in f:
                phase = 'wards' if 'jedinic' in f else 'members'
                continue
            nums = [n for _x, t, _c in cells for n in [number(t)] if n is not None]
            if phase == 'figures' or (phase in (None, 'lists') and f.startswith(('ukupno', 'glasovalo', 'nevaz'))):
                key = ('registered' if f.startswith('ukupno') else 'cast' if f.startswith('glasovalo')
                       else 'invalid' if f.startswith('nevaz') else None)
                if key and nums:
                    cur['figures'][key] = nums[0]
                    pcts = [p for _x, t, _c in cells for p in [percent(t)] if p is not None]
                    if pcts:
                        cur['figures'][key + '_pct'] = pcts[0]
                continue
            if phase == 'lists':
                cur.setdefault('list_rows', []).append(cells)
                lead, name, party, votes, pct = _split_cells(cells, name_max=380, votes_min=380)
                # A list's count is on its first line, so a row with a count
                # or a share starts one even when OCR lost its "3." number.
                # A count OCR put on a row of its own pairs with the list next
                # to it that has none.
                if not name and lead is None and votes is not None and pct is None:
                    if cur['lists'] and cur['lists'][-1]['votes'] is None:
                        cur['lists'][-1]['votes'] = votes
                    else:
                        cur['pending_votes'] = votes
                    continue
                if votes is None and cur.get('pending_votes') is not None and (lead or pct is not None):
                    votes = cur.pop('pending_votes')
                prev = cur['lists'][-1] if cur['lists'] else None
                # A coalition still listing partners ("…(HSS),"), or a row
                # holding only the count/share its list lacks, continues it.
                continues = prev is not None and lead is None and (
                    (prev['lines'] and prev['lines'][-1].rstrip().endswith(','))
                    or (votes is None and pct is not None and prev['pct'] is None and prev['votes'] is not None)
                    or (pct is None and votes is not None and prev['votes'] is None and prev['pct'] is not None))
                if continues:
                    if name:
                        prev['lines'].append(name)
                    if prev['votes'] is None and votes is not None:
                        prev['votes'] = votes
                    if prev['pct'] is None and pct is not None:
                        prev['pct'] = pct
                    continue
                if (lead is not None and lead == len(cur['lists']) + 1) or votes is not None or pct is not None:
                    cur['lists'].append({'lines': [name] if name else [], 'votes': votes, 'pct': pct})
                elif cur['lists']:
                    e = cur['lists'][-1]
                    if name:
                        e['lines'].append(name)
                    if e['votes'] is None and votes is not None:
                        e['votes'] = votes
                    if e['pct'] is None and pct is not None:
                        e['pct'] = pct
                continue
            if phase == 'wards':
                m = WARD_RE.match(f)
                if m:
                    ward = {'label': m.group(1), 'figures': {}, 'candidates': [], 'winner': None,
                            'page': pg, 'top': cells.top}
                    cur['wards'].append(ward)
                    continue
                if ward is None:
                    continue
                if f.startswith('izabran'):
                    # On a skewed page the last candidate's party and count
                    # can sit on this row; realign_ward takes them from here.
                    winner = ' '.join(t for x, t, _c in cells if x < 260).split(':', 1)[-1].strip()
                    # Cut at the party's closing bracket: a skewed row can
                    # carry the next line's text after it.
                    ward['winner'] = winner[:winner.index(')') + 1] if ')' in winner else winner
                    ward['winner_row'] = cells
                    ward.setdefault('rows_all', []).append(cells)
                    continue
                if f.startswith('ukupno') or 'glasovalo' in f:
                    # "Ukupno birača: 5.252, glasovalo: 3.427, nevažećih listića: 105";
                    # split across rows on a skewed page, it is kept with the
                    # ward's rows for strip_ward_turnout to collect.
                    if len(nums) >= 3:
                        ward['figures'] = dict(zip(('registered', 'cast', 'invalid'), nums[:3]))
                        continue
                    ward.setdefault('rows', []).append(cells)
                    ward.setdefault('rows_all', []).append(cells)
                    continue
                ward.setdefault('rows', []).append(cells)
                ward.setdefault('rows_all', []).append(cells)
                lead, name, party, votes, _pct = _split_cells(cells)
                name_x = min((x for x, t, _c in cells if x < 260), default=None)
                party_x = min((x for x, t, _c in cells if 260 <= x < 430), default=None)
                ward['candidates'].append({'lead': lead, 'name': name, 'party': party,
                                           'votes': votes, 'top': cells.top, 'name_x': name_x,
                                           'party_x': party_x})
    for sec in sections:
        realign_lists(sec)
        for ward in sec['wards']:
            if ward.get('rows') and any(w in fold(b[4]) for r in ward['rows'] for b in r.boxes
                                        for w in TURNOUT_WORDS) or single:
                strip_ward_turnout(ward)
                ward['candidates'] = [_row_candidate(r) for r in ward.get('rows', [])]
            realign_ward(ward)
    return sections


def _row_candidate(cells):
    lead, name, party, votes, _pct = _split_cells(cells)
    return {'lead': lead, 'name': name, 'party': party, 'votes': votes, 'top': cells.top,
            'name_x': min((x for x, t, _c in cells if x < 260), default=None),
            'party_x': min((x for x, t, _c in cells if 260 <= x < 430), default=None)}


# ---- order-based pairing ------------------------------------------------------
#
# Some scans are skewed: the lines tilt, so a count on the right sits up to
# half a line below its name on the left (Biograd na Moru), and matching by
# height pairs them wrongly. The report numbers its lists and candidates, so
# a block can instead be read column by column — numbered name lines in
# printed order, counts / shares / parties top to bottom — and paired one to
# one wherever the counts agree. Where they do not, the row reading stands
# and the checks decide.

# A list or candidate number, readable ("3.") or not (".", "-.", "1." for 4).
LEAD_SPLIT = re.compile(r'\s+(?=[-\d]{0,2}\s*\.\s+[A-ZČĆŠŽĐ])')
LEAD_RE = re.compile(r'^([-\d]{0,2})\s*\.\s+(.*)$')


def _left_lines(boxes, x_max):
    """Left-column boxes merged into groups (same top within 4 pt — one
    printed line, or two Vision fused into one tall box), each group split
    into units wherever a second "N. Name" starts."""
    left = sorted((b for b in boxes if b[0] < x_max and not NUMERIC.match(b[4])), key=lambda b: b[1])
    groups = []
    for b in left:
        if groups and b[1] - groups[-1][0] <= 4:
            groups[-1][1].append(b)
        else:
            groups.append([b[1], [b]])
    out = []
    for top, bs in groups:
        text = ' '.join(t for _x, _y, _h, _c, t in sorted(bs))
        out.append((top, [part.strip() for part in LEAD_SPLIT.split(text) if part.strip()]))
    return out


def _ordered_entries(groups):
    """[(lines, top)] in printed order. A unit opening with a number-like mark,
    or not continuing a partner list that ended in a comma, starts an entry.
    Within a fused group a readable number decides the order only if it fits
    the expected position; otherwise the group's own order stands."""
    entries = []
    for top, units in groups:
        heads, conts = [], []
        for u in units:
            m = LEAD_RE.match(u)
            prev_open = (heads[-1][1][-1] if heads else (entries[-1][0][-1] if entries else '')).endswith(',')
            if not m and prev_open:
                (heads[-1][1] if heads else entries[-1][0]).append(u)
                continue
            lead = int(m.group(1)) if m and m.group(1).isdigit() else None
            heads.append((lead, [m.group(2).strip() if m else u]))
        k = len(entries) + 1
        slots = list(range(k, k + len(heads)))
        placed = {}
        for lead, lines in heads:
            if lead in slots and lead not in placed:
                placed[lead] = lines
        rest = [lines for lead, lines in heads if not (lead in placed and placed[lead] is lines)]
        for slot in slots:
            if slot not in placed:
                placed[slot] = rest.pop(0)
        entries.extend((placed[slot], top) for slot in slots)
    return entries


def realign_lists(sec, votes=None, pcts=None):
    """Pair a list block by order; `votes` / `pcts` replace the page's own
    column when a re-read supplies them. True when it paired."""
    boxes = [b for r in sec.get('list_rows', []) for b in r.boxes]
    if not boxes:
        return False
    entries = _ordered_entries(_left_lines(boxes, 380))
    n = len(entries)
    right = sorted((b for b in boxes if b[0] >= 380), key=lambda b: b[1])
    if votes is None:
        votes = [number(b[4]) for b in right if '%' not in b[4] and number(b[4]) is not None]
    if pcts is None or len(pcts) != n:
        pcts = [percent(b[4]) for b in right if percent(b[4]) is not None]
    if n < 1 or len(votes) != n or len(pcts) not in (0, n):
        return False
    sec['lists'] = [{'lines': lines, 'votes': votes[i], 'pct': pcts[i] if pcts else None}
                    for i, (lines, _top) in enumerate(entries)]
    sec['realigned'] = True
    return True


TURNOUT_WORDS = ('ukupno', 'birac', 'glasovalo', 'nevaz', 'listic')


def strip_ward_turnout(ward):
    """An assembly ward's turnout line ("Ukupno birača: 62.083, glasovalo:
    40.662, nevažećih listića: 938"), found by its labels or its comma-ended
    numbers wherever OCR put it: read into the ward's figures and its boxes
    taken out of the candidate rows. Without this a skewed or misread line
    became candidates (Sisak-Moslavina V had two nameless ones with its
    electorate and voters as votes)."""
    rows_ = ward.get('rows', [])
    boxes = [b for r in rows_ for b in r.boxes]
    marks = [b for b in boxes if any(w in fold(b[4]) for w in TURNOUT_WORDS)
             or re.fullmatch(r'\s*\d{1,3}(\.\d{3})*\s*,[\s.]*', b[4])]
    if not marks:
        return
    y0, y1 = min(b[1] for b in marks) - 4, max(b[1] + b[2] for b in marks) + 2
    band = [b for b in boxes if y0 <= b[1] + b[2] / 2 <= y1]
    # Numbers anywhere in the band's text: OCR fuses them with the labels
    # ("16.143,. glasovalo:") and adds specks (". 448").
    nums = [int(n.replace('.', '')) for b in sorted(band)
            for n in re.findall(r'\d{1,3}(?:\.\d{3})+|\d+', b[4].replace(' ', ''))]
    if len(nums) >= 3 and not ward.get('figures'):
        ward['figures'] = dict(zip(('registered', 'cast', 'invalid'), nums[:3]))
    drop = set(map(id, band))
    for r in rows_:
        r.boxes = [b for b in r.boxes if id(b) not in drop]
        r[:] = sorted((b[0], b[4], b[3]) for b in r.boxes)
    ward['rows'] = [r for r in rows_ if r.boxes]


def realign_ward(ward, votes_override=None):
    """Pair a ward by order; `votes_override` replaces its count column."""
    boxes = [b for r in ward.get('rows', []) for b in r.boxes]
    if ward.get('winner_row') is not None:
        boxes += [b for b in ward['winner_row'].boxes if b[0] >= 260]
    if not boxes:
        return
    entries = _ordered_entries(_left_lines(boxes, 260))
    n = len(entries)
    by_top = sorted(boxes, key=lambda b: b[1])
    parties = [b for b in by_top if 260 <= b[0] < 430]
    votes = [b[4] for b in by_top if b[0] >= 430 and number(b[4]) is not None]
    if votes_override is not None:
        votes = [str(v) for v in votes_override]
    if n < 1 or len(parties) != n or len(votes) not in (0, n) or (not votes and n > 1):
        return False
    name_x = min(b[0] for b in boxes if b[0] < 260)
    ward['candidates'] = [{
        'lead': i + 1, 'name': ' '.join(lines), 'party': parties[i][4],
        'votes': number(votes[i]) if votes else None,
        'top': top, 'name_x': name_x, 'party_x': parties[i][0]}
        for i, (lines, top) in enumerate(entries)]
    ward['realigned'] = True
    return True


# ---- checks and repairs -----------------------------------------------------

def _share_matches(votes, valid, pct):
    """The report rounds some shares and cuts others (Gospić's invalid
    209 / 7.419 = 2.817 % is printed 2.81 %): accept either."""
    if valid <= 0:
        return False
    a = 100 * votes / valid
    return pct - 0.005 <= a < pct + 0.01 + 1e-9


# Largest gap between a body's (or assembly ward's) votes and its
# cast - invalid taken as the report's own rather than a misread.
REPORT_GAP = 5


def settle_lists(section):
    """Fill or confirm list votes against their printed shares. The shares
    are of the lists' own total (Sunja prints 4.333 voted and 276 invalid,
    but its two lists sum to 4.207 and their 76.80 / 23.20 % are of that), so
    the total is the one integer under which every read (votes, share) pair
    reproduces exactly; a missing or contradicted count is then the one
    integer its share allows, and the lists must sum to the total.
    Returns problems as strings."""
    lists = section['lists']
    if not lists:
        return []
    for e in lists:
        e['source'] = 'ocr'
    pairs = [(e['votes'], e['pct']) for e in lists if e['votes'] and e['pct']]
    if not pairs:
        # County assemblies and Zagreb print no shares: the lists must then
        # sum to cast - invalid exactly.
        fig = section['figures']
        if any(e['votes'] is None for e in lists):
            return [f'{sum(e["votes"] is None for e in lists)} list(s) without votes (no shares printed)']
        # A few votes short or over is the report's own (as in 2001: voters
        # signed off, ballots not counted); more means a misread.
        if {'cast', 'invalid'} <= fig.keys() and abs(sum(e['votes'] for e in lists) - (fig['cast'] - fig['invalid'])) > REPORT_GAP:
            return [f'lists sum {sum(e["votes"] for e in lists)} != cast - invalid '
                    f'{fig["cast"] - fig["invalid"]} (no shares printed)']
        return []
    # Candidate totals from each pair; keep the one most pairs agree with.
    guesses = sorted({round(v * 100 / p) + d for v, p in pairs if p for d in range(-3, 4)})
    known_sum = sum(e['votes'] for e in lists if e['votes'] is not None)
    best = max(guesses, key=lambda b: (sum(_share_matches(v, b, p) for v, p in pairs),
                                       b == known_sum))
    # The lists' own total wins whenever every read share fits it (Rijeka:
    # 86.983 fits all nine, and so did a total 17 lower).
    if all(e['votes'] is not None for e in lists) and all(_share_matches(v, known_sum, p) for v, p in pairs):
        best = known_sum
    for e in lists:
        if e['pct'] is None:
            continue
        if e['votes'] is not None and _share_matches(e['votes'], best, e['pct']):
            continue
        fits = [v for v in range(int(best * e['pct'] / 100) - 3, int(best * e['pct'] / 100) + 4)
                if _share_matches(v, best, e['pct'])]
        if len(fits) == 1:
            e['votes'], e['source'] = fits[0], 'share'
        elif e['votes'] is not None and e['votes'] in fits:
            pass
        else:
            e['votes'] = None
    missing = [e for e in lists if e['votes'] is None]
    rest = best - sum(e['votes'] for e in lists if e['votes'] is not None)
    # Only a positive remainder is a count; zero means the shares already
    # make 100 % without it (Novi Vinodolski prints SDP with no count at all).
    if len(missing) == 1 and rest > 0:
        missing[0]['votes'] = rest
        missing[0]['source'] = 'sum'
    if any(e['votes'] is None for e in lists):
        return [f'{sum(e["votes"] is None for e in lists)} list(s) without votes']
    total = sum(e['votes'] for e in lists)
    if total != best:
        return [f'lists sum {total} but their shares say {best}']
    shares = [e['pct'] for e in lists if e['pct'] is not None]
    if len(shares) == len(lists) and abs(sum(shares) - 100) > 0.05 * len(lists):
        return [f'shares sum to {sum(shares):.2f} %: a list is missing']
    if len(shares) < len(lists):
        # Some shares unread: the found counts must still be the whole total.
        pass
    return []


def _share_ok(num, den, pct):
    """A printed share matches its counts. Some places print every share as
    a whole percent ("78.00 %" for Ogulin's 78.40 %), others are exact with
    the same look (Zrinski Topolovac: 696 of 800 is 87.00 %), so ".00" is
    allowed a point either way — and `repair_figures` never leans on it."""
    if not den or pct is None:
        return False
    if pct == int(pct):
        return abs(100 * num / den - pct) <= 1.0
    # Turnout lines are a hundredth off either way now and then (Vrbovec:
    # 9.207 / 11.243 = 81.89 %, printed 81.90 %).
    return abs(100 * num / den - pct) <= 0.015


def _figure_checks(fig, lists):
    """Which of the three constraints hold: turnout share, invalid share (of
    those who voted, of the valid votes or of the electorate — the report
    uses all three bases), and cast - invalid = the lists' sum."""
    reg, cast, inv = fig.get('registered'), fig.get('cast'), fig.get('invalid')
    out = {}
    if reg and cast is not None and 'cast_pct' in fig:
        out['turnout'] = _share_ok(cast, reg, fig['cast_pct'])
    if cast and inv is not None and 'invalid_pct' in fig:
        out['invalid'] = any(_share_ok(inv, base, fig['invalid_pct'])
                             for base in (cast, cast - inv, reg) if base)
    if cast is not None and inv is not None and lists:
        out['sum'] = cast - inv == lists
    return out


def _variants(n):
    """Every number one digit substitution, or one swap of neighbouring
    digits, away from n (Vrbovec prints 926 invalid for 296: its 3.20 % and
    9.207 voted - 8.911 in lists both say 296)."""
    d = str(n)
    for i, ch in enumerate(d):
        for r in '0123456789':
            if r != ch and not (i == 0 and r == '0'):
                yield int(d[:i] + r + d[i + 1:])
    for i in range(len(d) - 1):
        if d[i] != d[i + 1] and not (i == 0 and d[i + 1] == '0'):
            yield int(d[:i] + d[i + 1] + d[i] + d[i + 2:])


def repair_figures(section):
    """Fix a misread (or misprinted) voter or invalid count: when the
    figures fail a check, try every one-digit change of each and keep the one
    change (if exactly one) under which every check holds (Gornja Stubica:
    OCR read 2.426 voted; 3.426 is 75.48 % of its electorate as printed and
    exactly its lists plus invalid)."""
    fig = section['figures']
    lists = sum(e['votes'] or 0 for e in section['lists'])
    checks = _figure_checks(fig, lists)
    # Only a failing printed share starts a repair: a sum a vote or two out
    # is as often the report's own gap (Domašinec, Karojba).
    if not checks or (checks.get('turnout', True) and checks.get('invalid', True)):
        return []
    fixes = []
    # Only figures two checks pin: cast (turnout share and the lists' sum)
    # and invalid (its share and the sum). The electorate is in the turnout
    # share alone, so a doubtful one goes to MANUAL_FIGURES after a look.
    for key in ('cast', 'invalid'):
        if fig.get(key) is None:
            continue
        # Both of the key's checks must be readable, or the sum alone would
        # rewrite a printed count (Tounj's invalid share went unread).
        needs = {'cast': ('turnout', 'sum'), 'invalid': ('invalid', 'sum')}[key]
        share = fig.get('cast_pct' if key == 'cast' else 'invalid_pct')
        if not all(k in checks for k in needs) or share is None or share == int(share):
            continue
        for v in _variants(fig[key]):
            trial = _figure_checks({**fig, key: v}, lists)
            if len(trial) == len(checks) and all(trial.values()):
                fixes.append((key, v))
    if len(fixes) != 1:
        return []
    key, v = fixes[0]
    note = f'{key} {fig[key]} -> {v} (the only one-digit change that makes every printed share and the lists agree)'
    fig[key] = v
    return [note]


def turnout_notes(section):
    """Checks the figures still fail after repair — the report's own slips or
    OCR misreads to review; not fatal."""
    fig = section['figures']
    lists = sum(e['votes'] or 0 for e in section['lists'])
    # The lists falling a few votes short of cast - invalid is the report's
    # own (as in 2001), so only the printed shares are checked here.
    checks = _figure_checks(fig, lists)
    failed = [k for k, ok in checks.items() if not ok and k != 'sum']
    # An invalid count the lists confirm (cast - invalid = lists) is right
    # whatever its printed share says.
    if checks.get('sum') and failed == ['invalid']:
        return []
    if not failed:
        return []
    return [f'{", ".join(failed)} check fails: registered {fig.get("registered")}, '
            f'cast {fig.get("cast")} ({fig.get("cast_pct")}%), invalid {fig.get("invalid")} '
            f'({fig.get("invalid_pct")}%), lists {lists}']


NOISE_RE = re.compile(r'^[\W\d_]*$')


def clean_name(name):
    name = re.sub(r'^[\s:.,;•*·\-]+', '', name).strip()
    return re.sub(r'\s+', ' ', name)


def _similar(a, b):
    return SequenceMatcher(None, fold(a), fold(b)).ratio()


def settle_ward(ward):
    """Drop noise rows, repair names from the "Izabran(a) je" line and an
    independent's "NK <name>" label, and check the stated winner tops the
    ward. Returns problems as strings."""
    cands = []
    for c in ward['candidates']:
        name = clean_name(c['name'])
        if c['votes'] is None and not c['party']:
            # A name-only row: a second reading of the next/previous name,
            # or a name whose votes/party sit on a row of their own.
            if cands and not cands[-1]['name'] and name:
                cands[-1]['name'] = name
            continue
        if not name and cands and c['votes'] is None and c['party']:
            continue
        cands.append({**c, 'name': name, 'party': c['party'].strip(' .,')})
    for c in cands:
        if fold(c['party']).startswith('nk ') and (not c['name'] or _similar(c['name'], c['party'][3:]) < 0.75):
            c['name'] = c['party'][3:].strip()
    ward['candidates'] = cands
    problems = []
    winner = ward.get('winner') or ''
    m = winner and re.match(r'(.*?),?\s*\(([^)]*)\)\s*$', winner)
    win_name, win_party = (clean_name(m.group(1)).rstrip(','), m.group(2)) if m else (winner, '')
    ward['winner_name'], ward['winner_party'] = win_name, win_party
    if not cands:
        return ['no candidates']
    if len(cands) == 1:
        c = cands[0]
        if _similar(c['name'], win_name) < 0.6:
            c['name'] = win_name or c['name']
        return problems                     # unopposed: votes may be absent
    if any(c['votes'] is None for c in cands):
        if ward.get('manual'):
            return problems          # the report itself leaves a count blank
        problems.append('candidate without votes')
        return problems
    top = max(cands, key=lambda c: c['votes'])
    if sum(1 for c in cands if c['votes'] == top['votes']) > 1:
        problems.append('tie for first')
    if win_name and _similar(top['name'], win_name) < 0.6:
        if fold(top['party']).replace(' ', '') == fold(win_party).replace(' ', '') or not top['name']:
            top['name'] = win_name           # the winner line is the better reading
        else:
            problems.append(f'stated winner {win_name!r} is not the top candidate {top["name"]!r}')
    fig = ward.get('figures') or {}
    if {'cast', 'invalid'} <= fig.keys() and abs(sum(c['votes'] for c in cands) - (fig['cast'] - fig['invalid'])) > REPORT_GAP:
        problems.append(f'candidates sum {sum(c["votes"] for c in cands)} != cast - invalid '
                        f'{fig["cast"] - fig["invalid"]}')
    return problems


# ---- vote column re-read ---------------------------------------------------
#
# For a list block or ward that fails its checks, the vote column alone is
# read again from a crop (tools/pdf_ocr_crops, CROP_LINES=1): rendered large
# and isolated, it yields the short numbers the page pass skips ("5", "122").
# The re-read counts are used only when there is exactly one per entry, and
# the block must then pass the same checks.

def _blocks(sec):
    """(kind, block id suffix, rows, x0) of a section's list and ward blocks."""
    out = []
    if sec.get('list_rows'):
        out.append(('L', 'L', sec['list_rows'], 380))
    for i, w in enumerate(sec['wards'], 1):
        if w.get('rows_all'):
            out.append(('W', f'W{i}', w['rows_all'], 430))
    return out


def column_specs(folder, pdf_dir):
    """Crop specs for the vote column of every block that fails a check."""
    _contests, _problems, _notes, failed = _parse_all(folder, None)
    specs = []
    for (file, si, block_id), (rows_, x0) in failed.items():
        pdf = Path(pdf_dir) / file.replace('.tsv', '.pdf')
        by_page = {}
        for r in rows_:
            by_page.setdefault(r.page, []).append(r.top)
        for pg, tops in by_page.items():
            y0, y1 = min(tops) - 4, max(tops) + 16
            specs.append(f'{file}|{si}|{block_id}\t{pdf}\t{pg}\t{x0}\t{y0:.1f}\t{570 - x0}\t{y1 - y0:.1f}')
    return specs


def read_columns(folder):
    path = Path(folder) / 'columns.tsv'
    out = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            parts = line.split('\t')
            if len(parts) >= 4:
                out.setdefault(parts[0], []).append((float(parts[2]), parts[3]))
    return out


def apply_columns(sec, file, si, columns):
    """Replace a failing block's counts with its re-read column, in order."""
    lists = sec['lists']
    key = f'{file}|{si}|L'
    if key in columns and lists:
        col = sorted(columns[key])
        votes = [number(t) for _y, t in col if '%' not in t and number(t) is not None]
        pcts = [percent(t) for _y, t in col if percent(t) is not None]
        if realign_lists(sec, votes, pcts):
            sec['column_reread'] = True
        elif len(votes) == len(lists):
            for e, v in zip(lists, votes):
                e['votes'] = v
            if len(pcts) == len(lists):
                for e, p in zip(lists, pcts):
                    e['pct'] = p
            sec['column_reread'] = True
    for i, w in enumerate(sec['wards'], 1):
        key = f'{file}|{si}|W{i}'
        if key not in columns or w.get('manual'):
            continue
        votes = [number(t) for _y, t in sorted(columns[key]) if number(t) is not None]
        cands = [c for c in w['candidates'] if c['votes'] is not None or c['party']]
        if votes and realign_ward(w, votes):
            w['column_reread'] = True
        elif votes and len(votes) == len(cands):
            for c, v in zip(cands, votes):
                c['votes'] = v
            w['candidates'] = cands
            w['column_reread'] = True


# ---- whole report -----------------------------------------------------------

ROMAN_OF = {v: k for k, v in ROMAN.items()}

# Sections whose check fails for a reason the report itself gives, by
# (county code, unit or slug): filled in as the data is verified.
KNOWN_PROBLEMS = {}

from .local_1997_manual import (BLANK_BODIES, CONFIRMED_LISTS, CONFIRMED_WARDS, MANUAL_FIGURES,
                                MANUAL_LISTS, MANUAL_WARD_FIGURES, MANUAL_WARDS, NAMES_CHECKED)


def _classify(heading):
    """(slug, level, unit) from "Gradsko vijeće grada Gospića" and kin."""
    f = fold(heading)
    words = heading.split()
    if f.startswith('zupanijska skupstina'):
        return 'local_county_assembly', 'county', ''
    if f.startswith('gradska skupstina'):
        return 'local_city_council', 'muni', ''          # Grad Zagreb
    slug = 'local_city_council' if f.startswith('gradsk') else 'local_municipal_council'
    # Drop "Gradsko vijeće grada" / "Općinsko vijeće općine" (OCR may garble
    # the third word but not its position).
    unit = ' '.join(words[3:]) if len(words) > 3 else ''
    unit = re.sub(r'^[Ll]l(?=[a-zčćšžđ])', 'Il', unit)    # "lloka": OCR's l for I
    return slug, 'muni', unit.upper().strip(' .,')


def _parties(lines):
    """One partner per printed line ("Hrvatska narodna stranka (HNS),"),
    without OCR's leading noise ("• ", ".", "2: ", "CONG: 5. ") or a
    trailing colon or stray count."""
    out = []
    for line in lines:
        line = re.sub(r'^[^A-Za-zČĆŠŽĐčćšžđ]*(?:[A-Z]{1,5}:\s*)?(?:\d{1,2}\s*[.:]\s*)?', '', line.strip())
        line = re.sub(r'[\s:]+(\d{1,2}\.)?$', '', line)
        line = line.strip().rstrip(',:').strip()
        if not line:
            continue
        if out and (line[:1].islower() or out[-1].endswith(('-', ' i'))):
            out[-1] = f'{out[-1]} {line}'
        else:
            out.append(line)
    return [re.sub(r'\(\s+', '(', p).upper() for p in out]


def parse_report(folder):
    """([(county code, contest)], problems, notes) for every OCR'd file in
    `folder`, applying `columns.tsv` re-reads when present."""
    contests, problems, notes, _failed = _parse_all(folder, read_columns(folder))
    return contests, problems, notes


def _parse_all(folder, columns):
    contests, problems, notes, failed = [], [], [], {}
    name_cols = read_name_columns(folder) if columns is not None else {}
    for path in sorted(Path(folder).glob('1997_*.tsv')):
        code = re.search(r'_(\d{2})_', path.name).group(1)
        for si, sec in enumerate(parse_file(path)):
            if columns:
                apply_columns(sec, path.name, si, columns)
            slug, level, unit = _classify(sec['heading'])
            if code == '21':
                # Zagreb's Gradska skupština, filed as its city council like
                # every later year (the report heads it "Županijska skupština").
                slug, level, unit = 'local_city_council', 'muni', ''
            where = f'{path.name[:7]} {code} {unit or slug}'
            known = KNOWN_PROBLEMS.get((code, unit or slug), ())
            if (code, unit) in BLANK_BODIES:
                sec['lists'] = []    # figures and counts unprinted
            manual_lists = MANUAL_LISTS.get((code, unit))
            if manual_lists:
                sec['lists'] = [{'lines': name.split(' / '), 'votes': v, 'pct': None, 'manual': True}
                                for name, v in manual_lists]
                p = []
            else:
                p = [x for x in settle_lists(sec) if x not in known]
                if (code, unit) in CONFIRMED_LISTS:
                    p = [x for x in p if not x.startswith('lists sum')]
            blocks = {b[1]: (b[2], b[3]) for b in _blocks(sec)}
            if p and 'L' in blocks:
                failed[(path.name, si, 'L')] = blocks['L']
            for i, ward in enumerate(sec['wards'], 1):
                manual = MANUAL_WARDS.get((code, unit, i))
                if manual:
                    ward['candidates'] = [{'lead': n, 'name': name, 'party': party, 'votes': votes}
                                          for n, (name, party, votes) in enumerate(manual, 1)]
                    ward['manual'] = True
                if (code, unit, i) in NAMES_CHECKED:
                    ward['names_checked'] = True
                if (code, unit, i) in MANUAL_WARD_FIGURES:
                    ward['figures'] = dict(zip(('registered', 'cast', 'invalid'),
                                               MANUAL_WARD_FIGURES[(code, unit, i)]))
                wp = [f'ward {i}: {x}' for x in settle_ward(ward) if f'ward {i}: {x}' not in known]
                if (code, unit, i) in CONFIRMED_WARDS:
                    wp = [x for x in wp if 'candidates sum' not in x]
                if not ward.get('manual') and f'{path.name}|{si}|W{i}' in name_cols:
                    lines = name_cols[f'{path.name}|{si}|W{i}']
                    if attach_name_column(ward, lines) and not ward.get('rebuilt'):
                        # Check the stated winner again against the order-paired
                        # names: a row-shifted page reading can pass the first
                        # check with the wrong person on top.
                        page_names = [c['name'] for c in ward['candidates']]
                        for c in ward['candidates']:
                            c['name'] = ' '.join(_tokens(c['crop_name'])) or c['name']
                        wp = [f'ward {i}: {x}' for x in settle_ward(ward)]
                        if (code, unit, i) in CONFIRMED_WARDS:
                            wp = [x for x in wp if 'candidates sum' not in x]
                        for c, n in zip(ward['candidates'], page_names):
                            c.setdefault('page_name', n)
                    # The column numbers its candidates: a ward that lost one
                    # can still pass the winner check (Poličnik IV, Sinj I).
                    n_col = name_column_count(lines)
                    if n_col > len(ward['candidates']) and rebuild_from_columns(
                            ward, lines, name_cols.get(f'{path.name}|{si}|W{i}|P')):
                        wp = [f'ward {i}: {x}' for x in settle_ward(ward)]
                    if n_col > len(ward["candidates"]) and (code, unit, i) not in CONFIRMED_WARDS:
                        wp.append(f'ward {i}: name column numbers {n_col} candidates, parsed '
                                  f'{len(ward["candidates"])}')
                if not ward.get('manual') and f'{path.name}|{si}|W{i}|P' in name_cols:
                    attach_party_column(ward, name_cols[f'{path.name}|{si}|W{i}|P'])
                if not ward.get('manual'):
                    wp += [f'ward {i}: {x}' for x in name_problems(ward)]
                if wp and f'W{i}' in blocks:
                    failed[(path.name, si, f'W{i}')] = blocks[f'W{i}']
                p += wp
            checked = MANUAL_FIGURES.get((code, unit)) or MANUAL_FIGURES.get((code, unit or slug))
            if checked:
                sec['figures'].update(zip(('registered', 'cast', 'invalid'), checked))
            else:
                notes += [f'{where}: fixed {x}' for x in repair_figures(sec)]
                p += [f'{x} — read the scan into MANUAL_FIGURES' for x in turnout_notes(sec)]
            problems += [f'{where}: {x}' for x in p]
            fig = sec['figures']
            entries = [{'parties': _parties(e['lines']), 'holder': '', 'votes': e['votes'],
                        'source': e.get('source')} for e in sec['lists']]
            contests.append((code, {
                'slug': slug, 'level': level, 'unit': unit, 'round': 1,
                'registered': fig.get('registered'), 'cast': fig.get('cast'),
                'invalid': fig.get('invalid'),
                'valid': sum(e['votes'] or 0 for e in entries),
                'entries': entries, 'wards': sec['wards'], 'page': sec['page'], 'top_y': sec.get('top'),
                'ward_offset': sec.get('ward_offset', 0),
                'file': path.name,
            }))
    return contests, problems, notes, failed


# ---- second reading of ward names ----------------------------------------

LETTERS = 'A-Za-zČĆŠŽĐčćšžđ'
NAME_TOKEN = re.compile(rf"^[{LETTERS}][{LETTERS}'-]*[,.]?$")
CROATIAN_MARKS = set('čćšžđČĆŠŽĐ')
FOREIGN = str.maketrans({'ś': 'š', 'Ś': 'Š', 'ź': 'ž', 'ż': 'ž', 'Ż': 'Ž', 'Ź': 'Ž', 'é': 'ć',
                         'ł': 'l', 'Ł': 'L', 'ń': 'n', 'ó': 'o', 'ę': 'e', 'ą': 'a', 'ř': 'r',
                         'ě': 'e', 'ů': 'u', 'ý': 'y', 'á': 'a', 'í': 'i', 'ú': 'u',
                         'q': 'g'})                         # no q in Croatian: "Ostroqonac"


def name_column_specs(folder, pdf_dir):
    """One crop per ward of its name column (all candidate rows), for a
    second reading paired in order — position-free, like the counts."""
    specs = []
    for path in sorted(Path(folder).glob('1997_*.tsv')):
        for si, sec in enumerate(parse_file(path)):
            for wi, w in enumerate(sec['wards'], 1):
                rows_ = w.get('rows') or []
                if not rows_:
                    continue
                xs = [b[0] for r in rows_ for b in r.boxes if b[0] < 260]
                ps = [b[0] for r in rows_ for b in r.boxes if 260 <= b[0] < 430]
                if not xs:
                    continue
                x0, x1 = min(xs) - 3, (min(ps) - 3) if ps else min(xs) + 190
                by_page = {}
                for r in rows_:
                    by_page.setdefault(r.page, []).append(r.top)
                pdf = Path(pdf_dir) / path.name.replace('.tsv', '.pdf')
                for pg, tops in by_page.items():
                    y0, y1 = min(tops) - 3, max(tops) + 14
                    specs.append(f'{path.name}|{si}|W{wi}\t{pdf}\t{pg}\t{x0:.1f}\t{y0:.1f}\t'
                                 f'{x1 - x0:.1f}\t{y1 - y0:.1f}')
                    if ps:
                        # The party column, read the same way, up to the counts.
                        vx = [b[0] for r in rows_ for b in r.boxes if b[0] >= 430 and number(b[4]) is not None]
                        right = (min(vx) - 4) if vx else 470
                        specs.append(f'{path.name}|{si}|W{wi}|P\t{pdf}\t{pg}\t{min(ps) - 3:.1f}\t'
                                     f'{y0:.1f}\t{right - min(ps) + 3:.1f}\t{y1 - y0:.1f}')
    return specs


def read_name_columns(folder):
    path = Path(folder) / 'names.tsv'
    out = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            parts = line.split('\t')
            if len(parts) >= 4:
                out.setdefault(parts[0], []).append((float(parts[2]), parts[3]))
    return out


PARTY_CODES = {
    'HDZ', 'HSS', 'HSLS', 'SDP', 'HNS', 'HKDU', 'HSP', 'HSU', 'ASH', 'IDS', 'PGS', 'HČSP', 'SBHS',
    'HSP-1861', 'KDM', 'HGSS', 'HKDS', 'IDF-FDI', 'HP', 'HND', 'SDU', 'DA', 'SDAH', 'HSZ', 'ZDS',
    'HSRS', 'NSH', 'HDD', 'HOP', 'HSNZ', 'SDR', 'IS', 'LUH', 'HDSS', 'SDSS', 'SNS', 'HSD', 'HDS',
    'HRZ', 'HSDP', 'HS', 'SHDP', 'NLGZ', 'ZZ', 'HKDS', 'DC', 'LS', 'HČSP', 'HDDSS', 'MS', 'TDZ-UDI',
    'HOR', 'RPS', 'DGS', 'NSP', 'SDA',
}


def clean_party(text):
    """A ward candidate's party label, normalised, or None when it does not
    read as one: every code must be a known party (OCR noise — "HSLSR" from a
    speck, "HCSP" for HČSP — is folded first), or it is "NK <name>"."""
    t = text.translate(str.maketrans('ŞşŢţİı', 'SsTtIi')).strip(' .,:;•®')
    if re.match(r'^(NK|SK)\s+[A-ZČĆŠŽĐ]', t):
        return 'NK ' + t[3:].strip()
    if re.match(r'^(NOL \(|nezavisni$)', t):
        return t                          # an independent list / "nezavisni", as printed
    t = t.replace('SDA Hrvatske', 'SDA')
    t = t.replace('HCSP', 'HČSP').replace(';', ',').replace('. ', ', ')
    t = re.sub(r'HSP\s*-\s*1861', 'HSP-1861', t)
    codes = [c.strip() for c in re.split(r'[,\s]+', t) if c.strip()]
    out = []
    for c in codes:
        c = c.upper()
        if c not in PARTY_CODES and c.endswith('R') and c[:-1] in PARTY_CODES:
            c = c[:-1]
        if c not in PARTY_CODES:
            return None
        out.append(c)
    return ', '.join(out) if out else None


def attach_party_column(ward, lines):
    """Re-read party column, in order, when it has one line per candidate;
    per candidate the re-read label wins if it reads as parties, else the
    page's if that does, else whatever the page had."""
    parties = [t for _y, t in sorted(lines)
               if not re.search(r'\d{2}|nevaz|izabran', fold(t)) and re.search(r'[A-ZČĆŠŽĐ]{2}', t)]
    # A long coalition wraps: "HNS, SDP, SBHS, HSS," / "HKDU".
    joined = []
    for t in parties:
        if joined and joined[-1].rstrip().endswith(','):
            joined[-1] = f'{joined[-1]} {t}'
        else:
            joined.append(t)
    parties = joined
    cands = ward['candidates']
    for c in cands:
        # Turnout text an assembly ward's row picked up is no party.
        if re.search(r'\d{2}|nevaz', fold(c['party'])):
            c['party'] = ''
        c['party'] = clean_party(c['party']) or c['party']
    if len(parties) != len(cands):
        return False
    # The column is paired by order, the page's labels by height: the crop
    # wins, cleaned if it reads as parties, raw otherwise.
    for c, t in zip(cands, parties):
        c['party'] = clean_party(t) or t.strip(' .,:;•')
    return True


def name_column_count(lines):
    """Candidates the re-read name column numbers ("1. …", "2. …")."""
    return sum(1 for _y, t in lines if re.match(r'^\s*\d{1,2}\s*[.,:]\s*[A-ZČĆŠŽĐa-zčćšžđ]', t)
               and not COUNTY_FOOTER.search(fold(t)))


def rebuild_from_columns(ward, name_lines, party_lines=None):
    """Rebuild a ward that lost a candidate: names from the re-read name
    column (numbered), parties and counts from every row of the ward — the
    winner row too, where a skewed page leaves the last candidate's cells.
    Only when all three columns agree on the count."""
    names = sorted((y, t) for y, t in name_lines
                   if re.match(r'^\s*\d{1,2}\s*[.,:]\s*[A-ZČĆŠŽĐa-zčćšžđ]', t) and not COUNTY_FOOTER.search(fold(t)))
    boxes = [b for r in ward.get('rows_all', []) for b in r.boxes]
    by_top = sorted(boxes, key=lambda b: b[1])
    n = len(names)
    # The re-read party column first (Vision can fuse two stacked labels on
    # the page — Poličnik's HDZ / HSLS came out as one "HBTS"), else the page.
    parties = []
    for _y, t in sorted(party_lines or []):
        if re.search(r'\d{2}|nevaz|izabran', fold(t)) or not re.search(r'[A-ZČĆŠŽĐ]{2}', t):
            continue
        if parties and parties[-1].rstrip().endswith(','):
            parties[-1] = f'{parties[-1]} {t}'
        else:
            parties.append(t)
    if len(parties) != n:
        parties = [b[4] for b in by_top if 260 <= b[0] < 430
                   and not fold(b[4]).startswith(('izabran', 'nevaz', 'glasov'))]
    votes = [number(b[4]) for b in by_top if b[0] >= 430 and number(b[4]) is not None]
    if not n or len(parties) != n or len(votes) not in (n, 0):
        return False
    ward['candidates'] = [{'lead': i + 1, 'name': re.sub(r'^\s*\d{1,2}\s*[.,:]\s*', '', t),
                           'crop_name': t, 'party': clean_party(parties[i]) or parties[i],
                           'votes': votes[i] if votes else None, 'top': y}
                          for i, (y, t) in enumerate(names)]
    ward['rebuilt'] = True
    return True


def final_words(cand):
    """The name words the importer will store: the crop reading's, else the
    page's; an independent's "NK <name>" label repeats the name."""
    words = _tokens(cand.get('crop_name') or '') or _tokens(cand['name'])
    if len(words) < 2 and fold(cand.get('party', '')).startswith('nk '):
        words = _tokens(cand['party'][3:])
    return words


def name_problems(ward):
    """Candidates without a full name, or one name twice in a ward — both
    pass the count checks, so they are checked here."""
    out, seen = [], set()
    for n, c in enumerate(ward['candidates'], 1):
        words = final_words(c)
        if len(words) < 2:
            out.append(f'candidate {n} has no full name ({" ".join(words)!r})')
        key = fold(' '.join(words))
        if ward.get('names_checked'):
            break
        # A row shift between the readings: this candidate's crop name is a
        # neighbour's page name (Umag VI had every name one row down).
        crop = fold(' '.join(_tokens(c.get('crop_name') or '')))
        for m in (n - 2, n):
            if crop and 0 <= m < len(ward['candidates']) and m != n - 1:
                page = fold(' '.join(_tokens(ward['candidates'][m].get('page_name')
                                             or ward['candidates'][m]['name'])))
                own = fold(' '.join(_tokens(c.get('page_name') or c['name'])))
                if page and SequenceMatcher(None, crop, page).ratio() > 0.85 and \
                        SequenceMatcher(None, crop, own).ratio() < 0.6:
                    out.append(f'candidate {n}: name readings shifted by a row')
                    break
        if COUNTY_FOOTER.search(key):
            out.append(f'candidate {n} is a page footer ({" ".join(words)!r})')
        if key in seen:
            out.append(f'name {" ".join(words)!r} twice')
        seen.add(key)
    return out


def attach_name_column(ward, lines):
    """Give each candidate its line of the re-read name column, in order,
    when the column has exactly one name line per candidate."""
    # A name line holds two capitalised words; the crop's edges add junk
    # ("lanhunal-1", "--") from the "Izabran(a) je" row below.
    cands = ward['candidates']
    # The numbered lines ("3. Ivan Pasini, dr.") when they alone match — the
    # crop's edges can catch the winner line's name too.
    numbered = [t for _y, t in sorted(lines)
                if re.match(r'^\s*\d{1,2}\s*[.,:]\s*[A-ZČĆŠŽĐa-zčćšžđ]', t) and not COUNTY_FOOTER.search(fold(t))]
    names = numbered if len(numbered) == len(cands) else [
        t for _y, t in sorted(lines)
        if re.search(r'[A-ZČĆŠŽĐ][a-zčćšžđ]+[\s-]+(\S+\s+)?[A-ZČĆŠŽĐ][a-zčćšžđ]', t)
        and not fold(t).startswith('izabran') and not COUNTY_FOOTER.search(fold(t))]
    if len(names) == len(cands):
        for c, t in zip(cands, names):
            c['crop_name'] = t
        return True
    return False


def _tokens(name):
    """A reading's name words: numbering, junk and titles after a comma cut."""
    name = name.translate(FOREIGN)
    name = re.sub(r'^[\W\d_]*\d+\s*[.,:]\s*', '', name)          # "2. "
    # Leading academic titles ("mr. sc.", "dr.", "prof. dr.") are not name words.
    # (A title ends in a dot or a space: "Dragutin" keeps its "Dr".)
    name = re.sub(r'^(?:(?:mr|dr|prof|doc|sc|dipl|ing|akademik)(?:\.\s*|\s+))+', '', name, flags=re.I)
    name = re.sub(r'^[^A-Za-zČĆŠŽĐčćšžđ]+', '', name)
    name = re.sub(r'\s+-\s+', '-', name)                   # "Tobias - Stjepan" is one name
    words = []
    for t in name.split():
        if t[:1] == 'l' and t[1:2].islower():
            t = 'I' + t[1:]                                      # "llic" -> "Ilic"
        if not NAME_TOKEN.match(t) or (words and t[:1].islower() and words[-1][-1:] != ','):
            break
        words.append(t)
        if t.endswith(','):
            break
    words = [w.rstrip(',.') for w in words]
    # "lvan" -> "Ivan": OCR reads a capital I as l before a lowercase letter.
    return [('I' + w[1:]) if w[:1] == 'l' and w[1:2].islower() else w for w in words]


def choose_name(page, crop, first_names, last_names):
    """The better of two readings of one printed name, word by word: a
    spelling the database already knows wins; between spellings that agree
    once diacritics are stripped, the one with more Croatian marks; else the
    crop's (rendered larger, read alone). `first_names` / `last_names` are
    upper-case words with diacritics. The page reading's title suffix
    (", dipl. oec.") is kept."""
    a, b = _tokens(page), _tokens(crop or '')
    suffix = page.split(',', 1)[1].strip() if ',' in page else ''
    # Readings naming different people (a row shifted on a skewed page): the
    # crop column, paired in order like the counts, is the right one.
    if a and b and SequenceMatcher(None, fold(' '.join(a)), fold(' '.join(b))).ratio() < 0.6:
        crop_suffix = crop.split(',', 1)[1].strip() if ',' in crop else ''
        return ' '.join(b) + (f', {crop_suffix}' if crop_suffix else '')
    def known(i, n, w):
        pool = first_names if i == 0 else last_names
        return w.upper() in pool or (i == n - 1 and w.upper() in last_names)
    if not b:
        words = a
    elif not a or len(a) != len(b):
        score = lambda ws: sum(known(i, len(ws), w) for i, w in enumerate(ws)) - (len(ws) < 2)
        words = b if score(b) >= score(a) else a
    else:
        words = []
        for i, (x, y) in enumerate(zip(a, b)):
            kx, ky = known(i, len(a), x), known(i, len(b), y)
            if kx != ky:
                words.append(x if kx else y)
            elif fold(x) == fold(y):
                words.append(max((y, x), key=lambda w: sum(ch in CROATIAN_MARKS for ch in w)))
            else:
                words.append(y)
    name = ' '.join(words) or page
    return f'{name}, {suffix}' if suffix and words else name


def main(folder):
    contests, problems, notes = parse_report(folder)
    print(f'{len(contests)} bodies, {sum(len(c["wards"]) for _k, c in contests)} wards, '
          f'{len(problems)} problems')
    for p in problems:
        print(' ', p)
    print(f'{len(notes)} turnout notes')
    for n in notes:
        print(' ', n)


if __name__ == '__main__':
    import sys
    if sys.argv[1] == '--columns':
        # python -m … --columns <ocr dir> <pdf dir> > crops.tsv
        print('\n'.join(column_specs(sys.argv[2], sys.argv[3])))
    elif sys.argv[1] == '--names':
        # python -m … --names <ocr dir> <pdf dir> > crops.tsv; then
        # CROP_LINES=1 tools/pdf_ocr_crops < crops.tsv > <ocr dir>/names.tsv
        print('\n'.join(name_column_specs(sys.argv[2], sys.argv[3])))
    else:
        main(sys.argv[1])
