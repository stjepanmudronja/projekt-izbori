"""Parse the 2001 lokalni izbori report (one PDF per county, `2001/ZN.pdf`).

The same DIP "Informacija o rezultatima izbora" as 2005, for the
representative bodies only (20 županijske skupštine, the gradska / općinska
vijeća and Zagreb's Gradska skupština, 20 May 2001). Its fonts carry no
Unicode mapping, so the text is dumped by `tools/pdf_glyph_text.py` rather
than PDFKit; that dump keeps each printed line whole, the votes at its end.

What differs from 2005: the report prints **no valid-ballot figure** — only
registered voters, voters who voted and invalid ballots — so a contest's
valid votes are the sum of its lists, and the check is against
`cast - invalid` (see `check`). Coalition partners are printed one per line,
some without their abbreviation ("SOCIJALDEMOKRATSKA PARIJA HRVATSKE").

    python -m elections.importers.local_2001_parse <dir-of-txt-files>
"""
import re
import sys
from pathlib import Path

import difflib
from collections import Counter, defaultdict

from .local_2009_parse import FIGURES, _heading, _num

# Votes end whichever line of the entry the layout put them on; one is
# printed without its thousands dot (Vukovar-Srijem HSP "7210").
VOTES_RE = re.compile(r'\s+(\d{1,3}(?:\.\d{3})+|\d+)$')
# "5 NEZAVISNA OPĆINSKA LISTA": Tordinci drops the dot once.
ENTRY_RE = re.compile(r'^(\d+)\.?\s+(.*)$')
# Party names that end in a number, which is not a vote count.
NUMBERED_PARTIES = re.compile(r'(HSP|PRAVA|HPSS|STRANKA)[ -](1861|1904)$')
END_RE = re.compile(r'^U .* izabran')
FURNITURE_RE = re.compile(r'^(Informacija o rezultatima izbora|=====PAGE)')


def _county_footer(line):
    # "Ličko-senjska županija", "Grad Zagreb", running unit headers
    # "Grad Gospić" / "grad Split".
    return bool(re.fullmatch(r'([A-ZČĆŠŽĐ][a-zčćšžđ]+(-[a-zčćšžđ]+)? županija|Grad Zagreb'
                             r'|([Gg]rad|[Oo]pćina) \S.*[a-zčćšžđ].*)', line))


# "Nositelj liste:", typed by hand per municipality: "Nostielj liste:",
# "Nositelj Liste:", "Nositelj lista:", "NOSITEL LISTE:", "Nositelj liste.",
# "Nositelj liste -", "Nositelj liste :".
HOLDER_RE = re.compile(r'(?:Nositelj|Nostielj|Nostitelj|Nositel)\s+list[ae]\s*[:.\-]\s*', re.I)
PARTY_WORDS = re.compile(r'STRANK|LISTA|SAVEZ|UNIJA|ZAJEDNICA|CENTAR|SABOR|PARTIJA|POKRET|'
                         r'AKCIJA|FORUM|BLOK|DEMOKR|ZELEN|RED\b|KOALICIJ')


def _split_holder(lines):
    holder, rest = '', []
    for line in lines:
        m = HOLDER_RE.search(line)
        if m:
            holder = line[m.end():].strip()
            if line[:m.start()].strip():
                rest.append(line[:m.start()].strip())
        else:
            rest.append(line)
    # Sračinec prints one holder with no label at all.
    if not holder and len(rest) > 1 and not PARTY_WORDS.search(rest[-1]) \
            and re.fullmatch(r"[A-ZČĆŠŽĐ' -]+(,.*)?", rest[-1]):
        holder = rest.pop()
    return holder, rest


def parse_text(text):
    sections, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line or FURNITURE_RE.match(line) or _county_footer(line):
            continue
        h = _heading(line)
        if h and (cur is None or cur['figures'] or cur['body']):
            # "BUKOVLJE *": its footnote says the Constitutional Court annulled
            # the decision (U-VII-1483/2001, 4 July 2001); the votes stand.
            unit = h[2].rstrip(' *')
            cur = {'slug': h[0], 'level': h[1], 'unit': unit, 'figures': {}, 'body': []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        hit = next((k for k in FIGURES if line.startswith(k)), None)
        if hit and FIGURES[hit] not in cur['figures']:
            fields = line[len(hit):].split()
            cur['figures'][FIGURES[hit]] = _num(fields[0])
            if len(fields) > 1:
                cur['figures'][FIGURES[hit] + '_pct'] = float(fields[1].rstrip('%').replace(',', '.'))
        else:
            cur['body'].append(line)
    return [_contest(s) for s in sections]


def _contest(sec):
    entries, phase = [], 'pre'
    for line in sec['body']:
        if line.startswith('Pojedin'):
            phase = 'entries'
            continue
        if phase != 'entries':
            continue
        if END_RE.match(line):
            break
        m = ENTRY_RE.match(line)
        # Ferdinandovac's numbering skips 6; its lists still sum exactly.
        new = m and len(entries) + 1 <= int(m.group(1)) <= len(entries) + 2 \
            and m.group(2)[:1].isupper() and not m.group(2).startswith(('Nositelj',))
        if not new and not entries:
            continue
        text = m.group(2) if new else line
        v = VOTES_RE.search(text)
        if v and NUMBERED_PARTIES.search(text):
            v = None
        if v:
            text = text[:v.start()]
        if new:
            entries.append({'lines': [text], 'votes': None})
        else:
            entries[-1]['lines'].append(text)
        if v:
            if entries[-1]['votes'] is not None:
                entries[-1]['two_votes'] = True
            entries[-1]['votes'] = _num(v.group(1))
    parsed = []
    for e in entries:
        holder, rest = _split_holder(e['lines'])
        parsed.append({'parties': _parties(rest), 'holder': holder, 'votes': e['votes'],
                       'two_votes': e.get('two_votes', False)})
    return {'slug': sec['slug'], 'level': sec['level'], 'unit': sec['unit'], 'round': 1,
            **sec['figures'], 'entries': parsed}


def _parties(lines):
    """One partner per line; a line that continues a wrapped name (lowercase,
    or after a trailing comma / dash) is joined to the one before."""
    out = []
    for line in lines:
        if line in ('(KOALICIJA)', 'KOALICIJA', '(KOALICIJA STRANAKA)', 'KOALICIJA STRANAKA'):
            continue
        if out and (line[:1].islower() or out[-1].endswith((',', '-', ' I')) or line == 'I'):
            out[-1] = f'{out[-1]} {line}'
        else:
            out.append(line)
    return out


# ---- party names ---------------------------------------------------------
#
# The report was typed municipality by municipality, so one party appears as
# "HRVATSKA SELJAČKA STRANKA - HSS", "… -HSS", "…(HSS)", "…, HSS", "… STRANKA"
# and "HRVATSKA SELJČAKA STRANKA". Council lists are shared by name across
# municipalities, so each variant would be its own list and a county total
# would split one party in several. `canonicalize` folds them: every partner
# is split into name and abbreviation, names are clustered on their letters
# (plus a close fuzzy match for typos, never across a difference in digits —
# HSP vs HSP 1861), and each cluster is written in its most common spelling
# with its most common abbreviation.

ABBR_RE = re.compile(r'^(.*?)(?:\s*[-–]\s*|\s*,\s*|\s*\(\s*)([A-ZČĆŠŽĐ][A-ZČĆŠŽĐa-z0-9-]{1,11})\)?\.?$')
# A coalition written on one line: "HDZ, HRVATSKA PUČKA STRANKA - HPS, …",
# "HRVATSKA NARODNA STRANKA I LIBERALNA STRANKA".
JOIN_RE = re.compile(r',\s+(?=[A-ZČĆŠŽĐ.]{3,}\s+[A-ZČĆŠŽĐ])|(?:(?<=STRANKA)|(?<=CENTAR)|(?<=SAVEZ)) I (?=[A-ZČĆŠŽĐ])')


def _split_abbr(party):
    """("HRVATSKA SELJAČKA STRANKA", "HSS") from any of the printed forms."""
    party = re.sub(r'\s+', ' ', party).strip().rstrip('.').strip()
    party = re.sub(r'\b(HSP|PRAVA)\s*-?\s*1861\b', r'\1-1861', party)
    m = ABBR_RE.match(party)
    if m and len(m.group(1)) > len(m.group(2)) + 3 and ' ' in m.group(1):
        abbr = m.group(2).upper()
        # "… PRAVA-1861" is part of the name, not an abbreviation; a word that
        # is the name's own last word ("… DEMOKRATSKI - DEMOKRŠĆANI") is fine.
        if not abbr.isdigit() and not party.startswith(('NEZAVISN', 'OPĆINSKA NEZAVISNA')):
            return m.group(1).strip(' -,'), re.sub(r'\s+', '-', abbr)
    return party, ''


def _key(name):
    return re.sub(r'[^A-ZČĆŠŽĐ0-9]', '', name.upper())


def canonicalize(contests):
    """Rewrite every entry's parties in place to one spelling per party."""
    def parts(e):
        out = []
        for p in e['parties']:
            out.extend(x for x in JOIN_RE.split(p) if x and x.strip())
        return [_split_abbr(p) for p in out]

    seen = Counter()
    abbrs = defaultdict(Counter)
    for c in contests:
        for e in c['entries']:
            e['_parts'] = parts(e)
            for name, abbr in e['_parts']:
                seen[name] += 1
                if abbr:
                    abbrs[_key(name)][abbr] += 1

    # Cluster: letters-only key first, then typos onto a more common key.
    by_key = defaultdict(Counter)
    for name, n in seen.items():
        by_key[_key(name)][name] += n
    keys = sorted(by_key, key=lambda k: -sum(by_key[k].values()))
    root = {}
    for i, k in enumerate(keys):
        digits = re.sub(r'\D', '', k)
        match = next((r for r in keys[:i] if root[r] == r and re.sub(r'\D', '', r) == digits
                      and difflib.SequenceMatcher(None, k, r).ratio() >= 0.93), None)
        root[k] = match or k
    # Then names sharing an abbreviation of 3+ letters ("SOCIJALDEMOKRATSKA
    # PARTIJA - SDP" and "… PARTIJA HRVATSKE - SDP") join its commonest one;
    # two-letter ones are ambiguous (DA is Dalmatinska and Demokratska akcija).
    owner = {}
    for k in keys:
        top = abbrs.get(k) and abbrs[k].most_common(1)[0][0]
        if top and len(top) >= 3 and root[k] == k:
            if top in owner:
                root[k] = owner[top]
            else:
                owner[top] = k
    for k in keys:
        while root[root[k]] != root[k]:
            root[k] = root[root[k]]
    spelling, abbr_of = {}, {}
    members = defaultdict(list)
    for k in keys:
        members[root[k]].append(k)
    for r, ks in members.items():
        names = Counter()
        a = Counter()
        for k in ks:
            names.update(by_key[k])
            a.update(abbrs.get(k, {}))
        # Prefer the commonest spelling among the most frequent key's.
        spelling[r] = by_key[r].most_common(1)[0][0]
        abbr_of[r] = a.most_common(1)[0][0] if a else ''
    for c in contests:
        for e in c['entries']:
            canon = []
            for name, _abbr in e.pop('_parts'):
                r = root[_key(name)]
                full = spelling[r] + (f' - {abbr_of[r]}' if abbr_of[r] else '')
                if full not in canon:
                    canon.append(full)
            e['parties'] = canon
    return contests


def list_name(entry):
    """As 2005/2009 name a council list: partners comma-joined, independent
    lists suffixed with their holder."""
    name = ', '.join(entry['parties'])
    if name.startswith('NEZAVISN') and entry['holder'] and entry['holder'] not in name:
        name = f"{name} - {entry['holder']}"
    return name


# Where the printed turnout disagrees with the printed counts, by (county
# code, unit). Brodsko-posavska's "61.450" voted is a misprint of 69,450: the
# printed 46,75% of 148,554 registered is 69,449, and 69,450 - 3,004 invalid
# is exactly its lists' 66,446, so `CAST_MISPRINTS` corrects it. In the other
# three the percentage is what is wrong or nothing settles it, so the counts
# are kept as printed: Veliki Bukovec (776 voted, 18 invalid, lists 758 —
# consistent; 53,17% would be 703), Pleternica (lists exact; 62,24% for
# 63,24%) and Lobor (lists equal the voted figure, as in five other
# municipalities that seem to print valid ballots there; 39,94% fits neither).
TURNOUT_MISPRINTS = {('12', 'BRODSKO-POSAVSKE ŽUPANIJE'), ('05', 'VELIKI BUKOVEC'),
                     ('11', 'PLETERNICE'), ('02', 'LOBOR')}
CAST_MISPRINTS = {('12', 'BRODSKO-POSAVSKE ŽUPANIJE'): (61450, 69450)}


def check(contest):
    """Problems with one contest. With no valid figure printed, the lists
    must not exceed `cast - invalid`; how far they fall short is reported
    by the caller."""
    problems = []
    if not contest['entries']:
        problems.append('no entries')
    if any(e['votes'] is None for e in contest['entries']):
        problems.append('entry without votes')
    if any(e['two_votes'] for e in contest['entries']):
        problems.append('entry with two vote figures')
    if not all(k in contest for k in ('registered', 'cast', 'invalid')):
        problems.append('missing turnout figures')
        return problems
    # The printed turnout pins the number who voted; some are cut to a whole
    # percent ("37.0%" for 36,66, "44.0%" for 44,78).
    # (The invalid share is printed against different bases by different
    # counties, so only turnout is checked.)
    for key, num, den in (('cast_pct', 'cast', 'registered'),):
        tolerance = 1.0 if key in contest and contest[key] == int(contest[key]) else 0.06
        if (contest.get('county'), contest['unit']) in TURNOUT_MISPRINTS:
            continue
        if key in contest and contest[den] and abs(100 * contest[num] / contest[den] - contest[key]) > tolerance:
            problems.append(f'{num} {contest[num]} is {100 * contest[num] / contest[den]:.2f}% '
                            f'of {den}, printed {contest[key]}%')
    return problems


def parse_dir(folder):
    """[(file stem, contest)] for every dump in `folder`, parties canonical."""
    out = [(path.stem, c) for path in sorted(Path(folder).glob('*.txt'))
           for c in parse_text(path.read_text())]
    for stem, c in out:
        c['county'] = f'{int(stem[1:]):02d}'   # Z9 / Z09 -> "09"
        fix = CAST_MISPRINTS.get((c['county'], c['unit']))
        if fix and c.get('cast') == fix[0]:
            c['cast'] = fix[1]
        # No valid figure is printed: the lists are the valid votes.
        if all(e['votes'] is not None for e in c['entries']):
            c['valid'] = sum(e['votes'] for e in c['entries'])
    canonicalize([c for _s, c in out])
    return out


def main(folder):
    total, bad, gaps = 0, 0, []
    for stem, c in parse_dir(folder):
        if True:
            path = Path(stem + '.txt')
            total += 1
            p = check(c)
            if p:
                bad += 1
                print(f'{path.name} {c["slug"]} {c["unit"]}: {"; ".join(p)}')
                continue
            gaps.append((c['cast'] - c['invalid'] - sum(e['votes'] for e in c['entries']),
                         path.name, c['unit'] or c['slug']))
    print(f'{total} contests, {bad} with problems')
    exact = sum(1 for g, *_ in gaps if g == 0)
    print(f'{exact} with lists == cast - invalid; the rest:')
    for g, name, unit in sorted(gaps, key=lambda t: abs(t[0]), reverse=True):
        if g:
            print(f'  {g:+6d} {name} {unit}')


if __name__ == '__main__':
    main(sys.argv[1])
