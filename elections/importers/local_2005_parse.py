"""Parse the 2005 lokalni izbori report (one text-layer PDF per county).

2005 is the last year before mayors and župani were elected directly, so the
report holds representative bodies only: one županijska skupština per county,
every gradsko / općinsko vijeće, and Zagreb's Gradska skupština. It is the
same DIP "Informacija o rezultatima izbora" as 2009 and is dumped the same way
(`tools/pdf_text`), but laid out differently enough to need its own parser:

- votes are a bare number column ("13.226", not "13.226 glasova"), which the
  text layer interleaves with the entries — standalone, at the end of an
  entry's line, or in a run after the "izabrani su" line — always in entry
  order, so they are the first *n* bare numbers of the section;
- the seat blocks that follow repeat each winning list's votes, which are
  cross-checked against the first pass;
- coalition partners are run together, on one line or wrapped anywhere
  ("HRVATSKA DEMOKRATSKA ZAJEDNICA - HDZ DEMOKRATSKI CENTAR - DC"), and are
  cut after each " - ABBR" (`_parties`);
- each page repeats the unit in title case ("Grad Gospić") as a running
  header.

Runnable on its own, like the 2009 parser:

    python -m elections.importers.local_2005_parse <dir-of-txt-files>
"""
import re
import sys
from pathlib import Path

from .local_2009_parse import FIGURES, _heading, _num, _split_holder, fix_eth, check

# A vote count: a bare number in thousands format, alone on its line or
# ending it after a space (so "HPSS-1904" is not one).
BARE_VOTES_RE = re.compile(r'(?:^|\s)(\d{1,3}(?:\.\d{3})*)$')
ENTRY_RE = re.compile(r'^(\d+)\.\s+(.*)$')
SEATS_RE = re.compile(r'\s*\d+ mjest[oa]$')
END_RE = re.compile(r'^U .* izabran')
# Sections whose printed figures disagree with themselves, by (county code,
# unit): list votes minus valid ballots. Bilje's eleven lists sum to 2,441
# against 2,430 valid, while 2,430 + 54 invalid = 2,484 cast holds, so the
# excess is the report's own; stored as printed.
KNOWN_EXCESS = {('14', 'BILJE'): 11}
RUNNING_HEADER_RE = re.compile(r'(Grad|Općina) \S.*[a-zčćšžđ].*')


def _is_furniture(line):
    """Page headers, footers and running headers: "Informacija o …",
    "Ličko-senjska županija 3", "Ličko-senjska županija", "Grad Gospić"."""
    return (line.startswith('=====PAGE') or line.startswith('Informacija o rezultatima izbora')
            or re.fullmatch(r'[A-ZČĆŠŽĐ][a-zčćšžđ]+(-[a-zčćšžđ]+)? županija( \d+)?', line)
            or re.fullmatch(r'Grad Zagreb( \d+)?', line)
            or RUNNING_HEADER_RE.fullmatch(line))


def _lines(text):
    raw = [l.strip().replace('–', '-') for l in fix_eth(text).splitlines()]
    raw = [l for l in raw if l]
    out, page = [], 0
    for i, line in enumerate(raw):
        if line.startswith('=====PAGE'):
            page = int(line.split()[1])
        # The page number: a bare number equal to it, next to the furniture.
        if line == str(page) and any(0 <= j < len(raw) and _is_furniture(raw[j])
                                     for j in (i - 1, i + 1)):
            continue
        if _is_furniture(line) or line == '(KOALICIJA)':
            continue
        out.append(line)
    return out


def parse_text(text):
    sections, cur = [], None
    for line in _lines(text):
        h = _heading(line)
        if h and (cur is None or cur['figures'] or cur['body']):
            cur = {'slug': h[0], 'level': h[1], 'unit': h[2], 'round': 1,
                   'figures': {}, 'body': []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        if any(line.startswith(k) for k in FIGURES) and len(cur['figures']) < 4:
            for k, f in FIGURES.items():
                if line.startswith(k):
                    cur['figures'][f] = _num(line[len(k):].split()[0])
        else:
            cur['body'].append(line)
    return [_contest(s) for s in sections]


def _contest(sec):
    entries, numbers, phase = [], [], 'pre'
    repeated = []             # winning lists' votes, repeated in the seat blocks
    for line in sec['body']:
        if line.startswith('Pojedin'):
            phase = 'entries'
            continue
        if phase == 'pre':
            continue
        m = BARE_VOTES_RE.search(line)
        number = _num(m.group(1)) if m else None
        text = line[:m.start()].strip() if m else line
        if phase == 'entries' and END_RE.match(text):
            phase = 'seats'
            if number is not None:
                numbers.append(number)
            continue
        if phase == 'entries':
            if number is not None:
                numbers.append(number)
            if not text:
                continue
            e = ENTRY_RE.match(text)
            if e and int(e.group(1)) == len(entries) + 1:
                entries.append([e.group(2)])
            elif entries:
                entries[-1].append(text)
            continue
        # Seat blocks: "N. LIST [k mjesta]", members, then the list's votes.
        # Until all n votes are in, a bare number is still the vote column.
        # Their order does not follow the blocks (Vinica prints block 2's
        # votes after block 3), so they are only checked as a set.
        if number is not None:
            if len(numbers) < len(entries) and not text:
                numbers.append(number)
            else:
                repeated.append(number)

    parsed = [_list_entry(lines) for lines in entries]
    for p, v in zip(parsed, numbers):
        p['votes'] = v
    votes = {p.get('votes') for p in parsed}
    mismatched = sorted({v for v in repeated if v not in votes})
    return {
        'slug': sec['slug'], 'level': sec['level'], 'unit': sec['unit'],
        'round': 1, **sec['figures'],
        'entries': parsed, 'n_votes': len(numbers),
        'seat_mismatch': mismatched,
    }


# Labels a coalition is printed under, before its partners; dropped when
# partners follow, kept when they are the list's only name.
COALITION_LABELS = ('KOALICIJSKA KANDIDACIJSKA LISTA', 'KOALICIJSKA LISTA',
                    'KOALICIJA STRANAKA -', 'KOALICIJA STRANAKA', 'KOALICIJA')
# Abbreviations of more than one word; every other one is a single token.
MULTIWORD_ABBRS = ('ABECEDA HGSS', 'SNA-POKRET ZELENIH', 'HRVATSKI BLOK', 'SLAVONSKA RAVNICA',
                   'SDA HRVATSKE', 'JADRANSKI SOCIJALDEMOKRATI', 'ZELENI HR', 'BV-TREĆI BLOK')


def _parties(lines):
    """Partners as "NAME - ABBR", in order. Line breaks are only where the
    page ran out ("… - HRVATSKI" / "BLOK HRVATSKA ČISTA …", "… OTOKA I" /
    "RIJEKE - ARS"), so the lines are joined and cut after each abbreviation."""
    text = ' '.join(lines).replace('(KOALICIJA)', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    for label in COALITION_LABELS:
        if text.startswith(label + ' ') and ' - ' in text[len(label):]:
            text = text[len(label):].strip()
            break
    parts = text.split(' - ')
    if len(parts) == 1:
        return [text]
    parties, name = [], parts[0]
    for part in parts[1:-1]:
        abbr = next((a for a in MULTIWORD_ABBRS if part == a or part.startswith(a + ' ')),
                    part.split(' ', 1)[0])
        parties.append(f'{name} - {abbr}')
        name = part[len(abbr):].strip()
    parties.append(f'{name} - {parts[-1]}')
    return parties


def _list_entry(lines):
    holder, rest = _split_holder(lines)
    return {'parties': _parties(rest), 'holder': holder}


def problems(code, contest):
    """`check` plus the seat-block cross-check, allowing KNOWN_EXCESS."""
    excess = KNOWN_EXCESS.get((code, contest['unit']), 0)
    p = check({**contest, 'valid': contest.get('valid', 0) + excess})
    if contest['seat_mismatch']:
        p.append(f'seat blocks repeat votes no entry has: {contest["seat_mismatch"]}')
    return p


def main(folder):
    total, bad = 0, 0
    for path in sorted(Path(folder).glob('*.txt')):
        for c in parse_text(path.read_text()):
            total += 1
            p = problems(path.stem.split('_')[2], c)
            if p:
                bad += 1
                print(f'{path.name} {c["slug"]} {c["unit"]}: {"; ".join(p)}')
    print(f'{total} contests, {bad} with problems')


if __name__ == '__main__':
    main(sys.argv[1])
