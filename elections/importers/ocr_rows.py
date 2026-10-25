"""Rebuild printed rows from `tools/pdf_ocr` output.

Vision returns one box per text run with its position; a printed row is the
boxes whose top edges lie within a few points of the row's first box, read
left to right. Tops, not centres: Vision sometimes merges two printed lines
into one tall box, whose centre then falls on the next row. Each cell keeps its x so callers can tell columns apart (a ward
candidate's name, party and votes; a list's name and votes).
"""
import csv
import re
from collections import defaultdict


def read(path):
    """{page: [(x, y_top, height, confidence, text)]}"""
    pages = defaultdict(list)
    with open(path, encoding='utf-8') as f:
        for row in csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
            if len(row) < 7:
                continue
            page, x, y, w, h, conf = int(row[0]), *map(float, row[1:6])
            pages[page].append((x, y, h, conf, '\t'.join(row[6:]).strip()))
    return pages


NUMERIC = re.compile(r'^[*]?[\d.,OoIl ]*\d[\d.,OoIl ]*%?[,.;]?$')


def rows(boxes, tolerance=4.5, anchor_x=380):
    """[[(x, text, confidence), ...], ...] top to bottom, each left to right.

    The right-hand figures (votes, shares) anchor the rows: every other box
    joins the anchor its vertical span overlaps most — the nearest-topped one
    when a merged box spans two — and boxes overlapping no anchor are grouped
    among themselves by their top edge.
    """
    anchors, rest = [], []
    for b in boxes:
        (anchors if b[0] >= anchor_x and NUMERIC.match(b[4]) else rest).append(b)
    # Anchors of one row (votes and share) are merged first.
    groups = []
    for b in sorted(anchors, key=lambda b: b[1]):
        if groups and b[1] - groups[-1][0] <= tolerance:
            groups[-1][2].append(b)
            groups[-1][1] = max(groups[-1][1], b[1] + b[2])
        else:
            groups.append([b[1], b[1] + b[2], [b]])
    loose = []
    for b in rest:
        top, bottom = b[1], b[1] + b[2]
        best = None
        for g in groups:
            overlap = min(bottom, g[1]) - max(top, g[0])
            if overlap > 0.5 * min(b[2], g[1] - g[0]):
                key = abs(top - g[0])
                if best is None or key < best[0]:
                    best = (key, g)
        if best:
            best[1][2].append(b)
        else:
            loose.append(b)
    out = [[g[0], g[2]] for g in groups]
    for b in sorted(loose, key=lambda b: b[1]):
        row = next((r for r in out if not any(NUMERIC.match(c[4]) and c[0] >= anchor_x for c in r[1])
                    and abs(r[0] - b[1]) <= tolerance), None)
        if row:
            row[1].append(b)
        else:
            out.append([b[1], [b]])
    out.sort(key=lambda r: r[0])
    return [Row(top, cells) for top, cells in out]


class Row(list):
    """A row's cells as (x, text, confidence), left to right, plus its top
    edge in page points and its raw boxes (x, top, height, confidence, text)."""
    def __init__(self, top, boxes):
        super().__init__(sorted((x, text, conf) for x, _t, _h, conf, text in boxes))
        self.top = top
        self.boxes = boxes
