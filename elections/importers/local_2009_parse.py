"""Parse the 2009 lokalni izbori report (one text-layer PDF per county).

The 2009 results were published only as DIP's "Informacija o rezultatima
izbora" PDFs — one per county, one section per contest, with no per-station
breakdown. `tools/pdf_text.swift` dumps each PDF's text layer (PDFKit; no
poppler needed) and this module turns that text into contests. It imports
nothing from Django so it can be run and checked on its own:

    python -m elections.importers.local_2009_parse <dir-of-txt-files>

Every section is self-checking: the entries must match the vote lines one to
one, and the votes must sum to the section's valid ballots.
"""
import re
import sys
from collections import Counter
from pathlib import Path

# Section headings -> (election type slug, level). Zagreb's two contests are
# filed as city council and city mayor, as the Excel years do.
HEADINGS = [
    ('GRADSKA SKUPŠTINA GRADA ZAGREBA', 'local_city_council', 'muni'),
    ('GRADONAČELNIK GRADA ZAGREBA', 'local_city_mayor', 'muni'),
    ('ŽUPANIJSKA SKUPŠTINA ', 'local_county_assembly', 'county'),
    ('ŽUPAN ', 'local_county_prefect', 'county'),
    ('GRADSKO VIJEĆE GRADA ', 'local_city_council', 'muni'),
    ('GRADONAČELNIK GRADA ', 'local_city_mayor', 'muni'),
    ('OPĆINSKO VIJEĆE OPĆINE ', 'local_municipal_council', 'muni'),
    ('NAČELNIK OPĆINE ', 'local_mayor', 'muni'),
    # "OPĆINSKO VIJEĆE VINODOLSKA OPĆINA": the one općina whose name already
    # says "općina", so the report does not prefix it.
    ('OPĆINSKO VIJEĆE ', 'local_municipal_council', 'muni'),
    ('NAČELNIK ', 'local_mayor', 'muni'),
]
EXECUTIVE = {'local_city_mayor', 'local_county_prefect', 'local_mayor'}

HEADER_LINES = (
    'Informacija o rezultatima izbora članova predstavničkih tijela',
    'i općinskih načelnika, gradonačelnika, župana i gradonačelnika Grada Zagreba',
)
VOTES_RE = re.compile(r'\s*(\d{1,3}(?:\.\d{3})*) glasova(?:\s+\d+,\d+%)?')
ENTRY_RE = re.compile(r'^(\d+)\.\s+(.*)$')
FIGURES = {
    'Ukupno birača:': 'registered',
    'Glasovalo birača:': 'cast',
    'Važećih listića:': 'valid',
    'Nevažećih listića:': 'invalid',
}
# Lines that end the list of entries and start the "who was elected" part.
END_RE = re.compile(r'^(U .* izabran|Za .* izabran|Niti jedan kandidat|U drugom krugu)')


def fix_eth(text):
    """The report's font maps Đ/đ to "ð" (and, in title-case running text such
    as "Meñimurska", to "ñ"); inside an uppercase word it is Đ."""
    text = text.replace('ñ', 'đ')

    def repl(m):
        word = m.group(0)
        out = []
        for i, ch in enumerate(word):
            if ch != 'ð':
                out.append(ch)
                continue
            neighbours = word[max(i - 1, 0):i] + word[i + 1:i + 2]
            letters = [c for c in neighbours if c.isalpha() and c != 'ð']
            upper = (not letters and i == 0) or any(c.isupper() for c in letters) or i == 0
            out.append('Đ' if upper else 'đ')
        return ''.join(out)
    return re.sub(r'\w*ð\w*', repl, text)


def _num(s):
    return int(s.replace('.', ''))


def _clean_lines(text, county_title):
    lines = []
    for raw in fix_eth(text).splitlines():
        line = raw.strip()
        if not line or line.startswith('=====PAGE') or line.startswith(HEADER_LINES):
            continue
        if re.fullmatch(r'\d+', line):  # bare page number
            continue
        if county_title and (line == county_title
                             or re.fullmatch(re.escape(county_title) + r' \d+', line)):
            continue
        lines.append(line)
    return lines


def _heading(line):
    for prefix, slug, level in HEADINGS:
        if line == prefix.strip() or line.startswith(prefix):
            return slug, level, line[len(prefix):].strip()
    return None


def parse_text(text):
    """Return (county_title, [contest, ...]) for one county's text dump."""
    raw_lines = [l.strip() for l in fix_eth(text).splitlines() if l.strip()]
    # Footers repeat the county in title case with the page number
    # ("Ličko-senjska županija 3"), or alone on even pages.
    footers = Counter(m.group(1) for l in raw_lines
                      for m in [re.fullmatch(r'([^\d]*[a-zčćšžđ][^\d]*) \d+', l)] if m)
    county_title = footers.most_common(1)[0][0] if footers else None
    lines = _clean_lines(text, county_title)

    sections, cur = [], None
    for line in lines:
        h = _heading(line)
        if h and (cur is None or cur['figures'] or cur['body']):
            cur = {'slug': h[0], 'level': h[1], 'unit': h[2], 'round': 1,
                   'figures': {}, 'body': []}
            sections.append(cur)
            continue
        if cur is None:
            continue
        if line == '(prvi krug izbora)':
            cur['round'] = 1
        elif line == '(drugi krug izbora)':
            cur['round'] = 2
        elif line.startswith('(treći krug izbora'):
            # Zlatar-Bistrica and Udbina: runoffs tied, repeated 14 June 2009.
            cur['round'] = 3
        elif any(line.startswith(k) for k in FIGURES) and len(cur['figures']) < 4:
            for k, f in FIGURES.items():
                if line.startswith(k):
                    cur['figures'][f] = _num(line[len(k):].split()[0])
        else:
            cur['body'].append(line)
    return county_title, [_contest(s) for s in sections]


def _contest(sec):
    entries, votes, in_entries, done = [], [], False, False
    # A long candidate line can carry the running mate after it
    # ("ŽELJKO VILJEVAC, dipl.ing. Zamjenik kandidata ANTUN KAŠIĆ, …").
    body = [part for line in sec['body']
            for part in re.split(r'\s+(?=Zamjenik kandidata )', line)]
    for line in body:
        for m in VOTES_RE.finditer(line):
            votes.append(_num(m.group(1)))
        line = VOTES_RE.sub('', line).strip()
        if line.startswith('Pojedin'):  # "Pojedine kandidacijske liste/kandidati dobili su…"
            in_entries = True
            continue
        if not in_entries or done or not line:
            continue
        if END_RE.match(line):
            done = True
            continue
        m = ENTRY_RE.match(line)
        if m and int(m.group(1)) == len(entries) + 1:
            entries.append({'lines': [m.group(2)]})
        elif entries:
            entries[-1]['lines'].append(line)
    exec_ = sec['slug'] in EXECUTIVE
    parsed = [(_exec_entry if exec_ else _list_entry)(e['lines']) for e in entries]
    for p, v in zip(parsed, votes):
        p['votes'] = v
    return {
        'slug': sec['slug'], 'level': sec['level'], 'unit': sec['unit'],
        'round': sec['round'], **sec['figures'],
        'entries': parsed, 'n_votes': len(votes),
    }


def _split_holder(lines):
    """Pull "Nositelj liste: X" out of the entry's lines (inline or alone)."""
    holder, rest = '', []
    for line in lines:
        if 'Nositelj liste:' in line:
            before, _, after = line.partition('Nositelj liste:')
            holder = after.strip()
            if before.strip():
                rest.append(before.strip())
        else:
            rest.append(line)
    return holder, rest


# Party names too long for one line, by how their first line ends.
WRAPPED_TAILS = ('PRIMORJA, GORSKOG', 'FORO SOCIAL DEMOCRATICO', 'SVEKOLIKOG RAZVOJA GRADA', '- JADRANSKI')


def _parties(lines):
    """One party per line, with wrapped names re-joined and the report's
    "koalicija stranaka" annotations dropped."""
    out = []
    for line in lines:
        if line == 'Koalicija stranaka':
            continue
        if out and (out[-1].endswith(',') or out[-1].endswith(WRAPPED_TAILS)
                    or line[:1].islower()):
            out[-1] = f'{out[-1]} {line}'
        else:
            out.append(line)
    return [re.sub(r'\s*-\s*koalicija stranaka$', '', p) for p in out]


def _list_entry(lines):
    holder, parties = _split_holder(lines)
    return {'parties': _parties(parties), 'holder': holder}


def _exec_entry(lines):
    name, deputies, parties = lines[0], [], []
    for line in lines[1:]:
        if line.startswith('Zamjenik kandidata'):
            deputies.append(line[len('Zamjenik kandidata'):].strip())
        else:
            parties.append(line)
    return {'name': name, 'deputies': deputies, 'parties': _parties(parties)}


def list_name(entry):
    """The council list's name as the Excel years write it: coalition
    partners comma-joined. An independent list carries its holder, since
    "NEZAVISNA GRADSKA LISTA" alone names a dozen different lists."""
    name = ', '.join(entry['parties'])
    if name.startswith('NEZAVISN') and entry['holder'] and entry['holder'] not in name:
        name = f"{name} - {entry['holder']}"
    return name


def check(contest):
    """Problems with one contest, as strings (empty when it reconciles)."""
    problems = []
    n = len(contest['entries'])
    if n == 0:
        problems.append('no entries')
    if contest['n_votes'] != n:
        problems.append(f'{n} entries but {contest["n_votes"]} vote lines')
    if not all(k in contest for k in ('registered', 'cast', 'valid', 'invalid')):
        problems.append('missing turnout figures')
    elif sum(e.get('votes', 0) for e in contest['entries']) != contest['valid']:
        problems.append(f'votes sum {sum(e.get("votes", 0) for e in contest["entries"])} '
                        f'!= valid {contest["valid"]}')
    return problems


def main(folder):
    total, bad = 0, 0
    for path in sorted(Path(folder).glob('*.txt')):
        title, contests = parse_text(path.read_text())
        for c in contests:
            total += 1
            p = check(c)
            if p:
                bad += 1
                print(f'{path.name} {c["slug"]} r{c["round"]} {c["unit"]}: {"; ".join(p)}')
    print(f'{total} contests, {bad} with problems')


if __name__ == '__main__':
    main(sys.argv[1])
