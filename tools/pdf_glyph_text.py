"""Dump the text of a PDF whose fonts carry no Unicode mapping.

The 2001 lokalni report was printed through a Windows PostScript driver that
embedded its TrueType fonts as Type 3 (and subset Type 1) fonts whose
encoding names each glyph by its index ("/G2C") and has no ToUnicode table.
PDFKit (`tools/pdf_text`) then returns raw codes as text — "/,ý.26(1-6.$"
for LIČKO-SENJSKA — and silently drops every code below 32, which in these
fonts are the space, the hyphen and the digits. This reads the content
streams itself:

- glyph fonts (`/Gxx` names): the glyph index is the TrueType one, so
  ASCII is glyph + 29 and the Croatian letters sit at fixed high indices
  (`GLYPHS`); an index not in the table prints as "{xx}" and makes the
  caller's checks fail rather than guess;
- standard fonts (Helvetica, Times): their /Differences glyph names;
- spaces: a TJ gap wider than a fifth of an em, or a gap between runs;
- lines: runs grouped by baseline, ordered left to right.

    python tools/pdf_glyph_text.py <pdf> > out.txt

Plain Python (zlib + re): the PDF is version 1.2 with no object streams.
"""
import re
import sys
import zlib

# TrueType glyph index -> character, beyond the ASCII run (glyph + 29).
# Read off words of known spelling (LIČKO, birača, skupština, Međimurska,
# "STRANKA – HSS"). Đ is drawn from a one-glyph substitute font at index 8,
# which in the text fonts would be "%" — never printed in them (percentages
# are set in Helvetica).
GLYPHS = {
    0x08: 'Đ', 0xB1: '-',
    0xE2: 'Š', 0xE3: 'š', 0xE4: 'Ž', 0xE5: 'ž',
    0xFB: 'Ć', 0xFC: 'ć', 0xFD: 'Č', 0xFE: 'č', 0xFF: 'đ',
}

# Advance widths (1/1000 em) of the base-14 fonts the report uses, from their
# AFM files, for the characters it sets in them; anything else counts 556.
# Only needed to tell whether a run that a substitute Đ follows ended with a
# gap ("MILAN ĐUKIĆ") or not ("ANĐELKO").
_HELV = dict(zip(' !"#$%&\'()*+,-./0123456789:;<=>?@',
                 [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278]
                 + [556] * 10 + [278, 278, 584, 584, 584, 556, 1015]))
_HELV.update(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                 [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
                  722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]))
_HELV.update(zip('abcdefghijklmnopqrstuvwxyz',
                 [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
                  556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500]))
_HELVB = dict(_HELV)
_HELVB.update(zip(' !"#$%&\'()*+,-./:;?',
                  [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 333, 333, 611]))
_HELVB.update(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                  [722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833,
                   722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]))
_HELVB.update(zip('abcdefghijklmnopqrstuvwxyz',
                  [556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889,
                   611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500]))
_TIMESB = {c: 500 for c in '0123456789'}
_TIMESB.update({' ': 250, '.': 250, ',': 250, ':': 333, '-': 333, '%': 1000})
_TIMESB.update(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                   [722, 667, 722, 722, 667, 611, 778, 778, 389, 500, 778, 667, 944,
                    722, 778, 611, 778, 722, 556, 667, 722, 722, 1000, 722, 722, 667]))
_TIMESB.update(zip('abcdefghijklmnopqrstuvwxyz',
                   [500, 556, 444, 556, 444, 333, 500, 556, 278, 333, 556, 278, 833,
                    556, 500, 556, 556, 444, 389, 333, 556, 500, 722, 500, 500, 444]))
BASE14 = {'Helvetica': _HELV, 'Helvetica-Bold': _HELVB, 'Times-Bold': _TIMESB}
for _w in BASE14.values():
    _w.update({c: _w[b] for c, b in zip('ŠšŽžČčĆćĐđ', 'SsZzCcCcDd')})

# Glyph names used by the standard fonts' /Differences.
NAMES = {
    'space': ' ', 'Scaron': 'Š', 'scaron': 'š', 'Zcaron': 'Ž', 'zcaron': 'ž',
    'Ccaron': 'Č', 'ccaron': 'č', 'Cacute': 'Ć', 'cacute': 'ć',
    'Dcroat': 'Đ', 'dcroat': 'đ', 'Eth': 'Đ', 'endash': '-', 'emdash': '-',
    'hyphen': '-', 'quotesingle': "'", 'quoteright': "'", 'quoteleft': "'",
    'quotedblleft': '"', 'quotedblright': '"', 'quotedblbase': '"', 'bullet': '',
}


def load(path):
    data = open(path, 'rb').read()
    objs = {}
    for m in re.finditer(rb'(\d+)\s+0\s+obj(.*?)endobj', data, re.S):
        body, stream = m.group(2), None
        s = re.search(rb'stream\r?\n', body)
        if s and b'/Length' in body[:s.start()]:
            raw = body[s.end():]
            raw = raw[:raw.rfind(b'endstream')]
            stream = zlib.decompressobj().decompress(raw)
            body = body[:s.start()]
        objs[int(m.group(1))] = (body, stream)
    return objs


def ref(body, key):
    m = re.search(rb'/' + key + rb'\s+(\d+)\s+0\s+R', body)
    return int(m.group(1)) if m else None


def font_decoder(objs, num):
    body = objs[num][0]
    enc = ref(body, b'Encoding')
    table = {}
    if enc is not None:
        m = re.search(rb'/Differences\s*\[(.*?)\]', objs[enc][0], re.S)
        if m:
            code = 0
            for tok in re.findall(rb'\d+|/[^\s/\[\]]+', m.group(1)):
                if tok[:1] != b'/':
                    code = int(tok)
                    continue
                table[code] = tok[1:].decode('latin1')
                code += 1
    glyph_font = any(re.fullmatch(r'G[0-9A-F]{2}', n) for n in table.values())

    def char(c):
        name = table.get(c)
        if glyph_font:
            g = int(name[1:], 16) if name and name.startswith('G') else c
            if g in GLYPHS:
                return GLYPHS[g]
            return chr(g + 29) if 3 <= g <= 93 else '{%02X}' % g
        if name is not None:
            return NAMES.get(name, name if len(name) == 1 else bytes([c]).decode('cp1250'))
        return bytes([c]).decode('cp1250')

    # Advance widths in text space (em units at size 1).
    first = re.search(rb'/FirstChar\s+(\d+)', body)
    widths = re.search(rb'/Widths\s*\[(.*?)\]', body, re.S)
    matrix = re.search(rb'/FontMatrix\s*\[\s*([-\d.]+)', body)
    scale = float(matrix.group(1)) if matrix else 0.001
    base = re.search(rb'/BaseFont\s*/(\S+)', body)
    afm = BASE14.get(base.group(1).decode() if base else '')
    if widths:
        w = [float(x) for x in widths.group(1).split()]
        f0 = int(first.group(1))

        def width(c):
            return w[c - f0] * scale if 0 <= c - f0 < len(w) else 0.5
    else:
        def width(c):
            return (afm or {}).get(char(c), 556) / 1000

    def decode(raw):
        return ''.join(char(c) for c in raw)
    return decode, width


TOKEN = re.compile(rb'\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>|\[|\]|/[^\s/\[\]()<>]+|[-+]?\d*\.?\d+|[A-Za-z\'"*]+', re.S)


def literal(tok):
    s, out, i = tok[1:-1], bytearray(), 0
    while i < len(s):
        c = s[i]
        if c == 0x5C:  # backslash
            i += 1
            n = s[i:i + 1]
            if n.isdigit():
                j = i
                while j < len(s) and j < i + 3 and s[j:j + 1].isdigit():
                    j += 1
                out.append(int(s[i:j], 8) & 0xFF)
                i = j
                continue
            out.extend({b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f'}.get(n, n))
        else:
            out.append(c)
        i += 1
    return bytes(out)


def page_runs(objs, page):
    body = objs[page][0]
    res = objs[ref(body, b'Resources')][0]
    fonts = {}
    fm = re.search(rb'/Font\s*<<(.*?)>>', res, re.S)
    if fm:
        for name, num in re.findall(rb'/(\w+)\s+(\d+)\s+0\s+R', fm.group(1)):
            fonts[name] = font_decoder(objs, int(num))
    cm = re.search(rb'/Contents\s*(\[.*?\]|\d+\s+0\s+R)', body, re.S).group(1)
    content = b''.join(objs[int(n)][1] or b'' for n in re.findall(rb'(\d+)\s+0\s+R', cm))

    runs, stack = [], []
    decode, width, size, leading = None, None, 1.0, 0.0
    tm = [1, 0, 0, 1, 0, 0]
    lm = tm[:]

    def show(parts):
        text, advance = [], 0.0
        for p in parts:
            if isinstance(p, bytes):
                text.append(decode(p) if decode else p.decode('cp1250'))
                advance += sum(width(c) for c in p) if width else 0.5 * len(p)
            else:
                advance -= p / 1000
                if p < -180:
                    text.append(' ')
        em = abs(lm[0] * size)
        runs.append((round(lm[5], 1), lm[4], ''.join(text), em, lm[4] + advance * em))

    for tok in TOKEN.findall(content):
        if tok[:1] == b'(':
            stack.append(literal(tok))
        elif tok[:1] == b'<':
            stack.append(bytes.fromhex(tok[1:-1].decode()))
        elif tok == b'[':
            stack.append('[')
        elif tok == b']':
            i = len(stack) - 1 - stack[::-1].index('[')
            arr = stack[i + 1:]
            del stack[i:]
            stack.append(arr)
        elif tok[:1] == b'/':
            stack.append(tok[1:])
        elif re.fullmatch(rb'[-+]?\d*\.?\d+', tok):
            stack.append(float(tok))
        else:
            op = tok
            if op == b'BT':
                tm, lm = [1, 0, 0, 1, 0, 0], [1, 0, 0, 1, 0, 0]
            elif op == b'Tf' and len(stack) >= 2:
                decode, width = fonts.get(stack[-2], (None, None))
                size = stack[-1]
            elif op == b'Tm' and len(stack) >= 6:
                tm = [float(x) for x in stack[-6:]]
                lm = tm[:]
            elif op in (b'Td', b'TD') and len(stack) >= 2:
                tx, ty = stack[-2], stack[-1]
                if op == b'TD':
                    leading = -ty
                lm = [lm[0], lm[1], lm[2], lm[3],
                      lm[4] + tx * lm[0] + ty * lm[2], lm[5] + tx * lm[1] + ty * lm[3]]
                tm = lm[:]
            elif op == b'TL' and stack:
                leading = stack[-1]
            elif op == b'T*':
                lm = [lm[0], lm[1], lm[2], lm[3], lm[4] - leading * lm[2], lm[5] - leading * lm[3]]
            elif op == b'Tj' and stack:
                show([stack[-1]])
            elif op == b'TJ' and stack and isinstance(stack[-1], list):
                show(stack[-1])
            elif op in (b"'", b'"') and stack:
                lm = [lm[0], lm[1], lm[2], lm[3], lm[4] - leading * lm[2], lm[5] - leading * lm[3]]
                show([stack[-1]])
            stack.clear()
    return runs


def lines(runs):
    """Runs on one baseline (within 2pt), left to right, top to bottom; a
    space between two runs only where the page shows a gap."""
    rows = []
    for run in sorted(runs, key=lambda r: (-r[0], r[1])):
        if rows and abs(rows[-1][0] - run[0]) <= 2:
            rows[-1][1].append(run)
        else:
            rows.append([run[0], [run]])
    result = []
    for _y, parts in rows:
        parts.sort(key=lambda r: r[1])
        line, end = '', None
        for _y2, x, text, em, run_end in parts:
            if not text.strip():
                continue
            if line and (end is None or x - end > 0.15 * em
                         or line.endswith(' ') or text.startswith(' ')):
                line += ' '
            line += text
            end = run_end
        line = re.sub(r'\s+', ' ', line).strip()
        if line:
            result.append(line)
    return result


def pages(path):
    objs = load(path)
    # Page order: the /Kids arrays of the page tree, depth first.
    root = next(k for k, (b, _s) in objs.items() if re.search(rb'/Type\s*/Catalog', b))
    order = []

    def walk(n):
        b = objs[n][0]
        if re.search(rb'/Type\s*/Page\b', b):
            order.append(n)
            return
        kids = re.search(rb'/Kids\s*\[(.*?)\]', b, re.S)
        for k in re.findall(rb'(\d+)\s+0\s+R', kids.group(1)):
            walk(int(k))
    walk(ref(objs[root][0], b'Pages'))
    return [lines(page_runs(objs, p)) for p in order]


if __name__ == '__main__':
    for i, page in enumerate(pages(sys.argv[1]), 1):
        print(f'=====PAGE {i}')
        for line in page:
            print(line)
