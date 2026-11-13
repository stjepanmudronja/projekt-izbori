"""Build static/hr_municipalities.json, the outlines the municipality map draws.

Input: geoBoundaries' Croatian ADM2 layer ("Municipalities and Towns", 2021,
from OpenStreetMap, CC BY-SA), the simplified GeoJSON:
https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/HRV/ADM2/geoBoundaries-HRV-ADM2_simplified.geojson

    python tools/build_muni_map.py <geojson> [--osm extra.json] [--out static/hr_municipalities.json]

That layer lacks eight municipalities (Ivanska, Lišane Ostrovičke, Ljubešćica,
Rovišće, Stankovci, Tisno, Tribunj, Zrinski Topolovac) and draws Krk as one
island instead of its five. `--osm` takes those relations straight from
OpenStreetMap, as an Overpass `out geom;` result:

    [out:json];area["ISO3166-1"="HR"][admin_level=2]->.hr;
    rel(area.hr)["boundary"="administrative"]["admin_level"="7"]
       ["name"~"^(Općina |Grad )?(Ivanska|Lišane Ostrovičke|Ljubešćica|Rovišće|
        Stankovci|Tisno|Tribunj|Zrinski Topolovac|Krk|Baška|Dobrinj|Punat|Vrbnik)$"];
    out geom;

Their ways are joined into rings and simplified (Douglas-Peucker, ~100 m) to
the layer's level of detail; once Krk's municipalities are in, the layer's
"Otok Krk" outline is dropped so the island is not drawn twice.

Each feature ("Grad Bakar", "Općina Kapela") is matched to a Municipality row
of type grad/općina by name, without its prefix and with the hyphen/prefix
folding imports use (`normalize_municipality_name`). A name that two counties
share (Otok, Privlaka, ...) goes to the county whose other matched places lie
nearest. Outlines are projected (longitude scaled by cos of the mean
latitude), rounded to 0.1 of a 1000-unit-wide box and written as SVG paths,
so the page needs no map library. Unmatched features are reported, not kept.
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projekt_izbori.settings')

import django  # noqa: E402

django.setup()

from elections.importers.name_utils import normalize_municipality_name, strip_diacritics  # noqa: E402
from elections.models import Municipality  # noqa: E402

WIDTH = 1000.0
# OSM features whose name is not DIP's: typos, and islands the layer maps on
# their own instead of inside their municipality. Krk is one outline for five
# municipalities (Krk, Punat, Baška, Vrbnik, Dobrinj): `--osm` brings those in
# and drops it. The islets Plavnik and Zeča stay unassigned, drawn without data.
LOSINJ = 'MALI LOŠINJ'
KORNATI = 'MURTER - KORNATI'
ALIASES = {
    'Općina Hvratska Dubica': 'HRVATSKA DUBICA', 'Opicina Pirovac': 'PIROVAC',
    'Općina Veliki Pisanica': 'VELIKA PISANICA', 'Općina Magdenovac': 'MAGADENOVAC',
    'Općina Donji Kukuzari': 'DONJI KUKURUZARI', 'Opicina Muter-Kornati': KORNATI,
    'Otok Cres': 'CRES',
    'Otok Losinj': LOSINJ, 'Otok Susak': LOSINJ, 'Otok Ilovik': LOSINJ, 'Otok Unije': LOSINJ,
    'Otok Vele Srakane': LOSINJ, 'Otok Vele Orjule': LOSINJ,
    'Otok Kornat': KORNATI, 'Otok Zut': KORNATI, 'Otok Sit': KORNATI, 'Otok Piskera': KORNATI,
    'Otok Lavsa': KORNATI, 'Otok Leveraka': KORNATI, 'Otok Kurba Vela': KORNATI,
    'Otok Vela Smokvica': KORNATI, 'Otok Arta Vela': KORNATI,
}


def key(name):
    name = name.strip()
    for prefix in ('Grad ', 'Općina ', 'Opcina '):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return strip_diacritics(normalize_municipality_name(name.upper())).replace(' ', '')


def rings(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    return [ring for poly in polys for ring in poly]


def centroid(geom):
    pts = [p for ring in rings(geom) for p in ring]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def _simplify(pts, tol):
    """Douglas-Peucker on a list of (lon, lat)."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    far, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > far:
            far, idx = d, i
    if far <= tol:
        return [pts[0], pts[-1]]
    return _simplify(pts[:idx + 1], tol)[:-1] + _simplify(pts[idx:], tol)


def osm_features(path, tol=0.001):
    """GeoJSON-like features from an Overpass `out geom;` result of boundary
    relations: each relation's outer and inner ways joined end to end."""
    out = []
    for rel in json.load(open(path, encoding='utf-8'))['elements']:
        polys = {'outer': [], 'inner': []}
        for role in polys:
            ways = [[(p['lon'], p['lat']) for p in m['geometry']]
                    for m in rel.get('members', []) if m['type'] == 'way' and m.get('role') == role]
            while ways:
                ring = ways.pop(0)
                while ring[0] != ring[-1]:
                    for i, w in enumerate(ways):
                        if w[0] == ring[-1]:
                            ring += w[1:]
                        elif w[-1] == ring[-1]:
                            ring += w[::-1][1:]
                        elif w[-1] == ring[0]:
                            ring = w[:-1] + ring
                        elif w[0] == ring[0]:
                            ring = w[::-1][:-1] + ring
                        else:
                            continue
                        ways.pop(i)
                        break
                    else:
                        break                     # an open ring: closed below
                # A closed ring's ends coincide, which Douglas-Peucker cannot
                # measure against: split it at the point farthest from its start.
                k = max(range(len(ring)), key=lambda i: math.dist(ring[0], ring[i]))
                ring = _simplify(ring[:k + 1], tol)[:-1] + _simplify(ring[k:], tol)
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                if len(ring) >= 4:
                    polys[role].append([list(p) for p in ring])
        # Holes are rare at this level; each outer ring is its own polygon.
        coords = [[ring] for ring in polys['outer']]
        if coords:
            out.append({'properties': {'shapeName': rel['tags']['name']},
                        'geometry': {'type': 'MultiPolygon', 'coordinates': coords}})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('geojson')
    ap.add_argument('--osm', help='Overpass result with the relations the layer lacks')
    ap.add_argument('--out', default=os.path.join(ROOT, 'static', 'hr_municipalities.json'))
    args = ap.parse_args()
    features = json.load(open(args.geojson, encoding='utf-8'))['features']
    if args.osm:
        extra = osm_features(args.osm)
        names = {f['properties']['shapeName'] for f in extra}
        if 'Grad Krk' in names:
            features = [f for f in features if f['properties']['shapeName'] != 'Otok Krk']
        features += extra
        print(f'added {len(extra)} outlines from OpenStreetMap: {sorted(names)}')

    by_key = defaultdict(list)
    for m in Municipality.objects.filter(type__in=('grad', 'općina')).select_related('county'):
        keys = {key(m.name)}
        if ' - ' in m.name:                  # Istrian bilingual names: "PULA - POLA"
            keys.add(key(m.name.split(' - ')[0]))
        for k in keys:
            by_key[k].append(m)

    matched, ambiguous, missing = {}, [], []
    for f in features:
        name = f['properties']['shapeName']
        cands = by_key.get(key(ALIASES.get(name, name)), [])
        if len(cands) == 1:
            matched[id(f)] = cands[0]
        elif cands:
            ambiguous.append((f, cands))
        else:
            missing.append(name)

    # Shared names: the county whose matched places' centre lies nearest.
    centres = defaultdict(list)
    for f in features:
        if id(f) in matched:
            centres[matched[id(f)].county_id].append(centroid(f['geometry']))
    centre = {c: (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
              for c, pts in centres.items()}
    taken = {m.id for m in matched.values()}
    for f, cands in ambiguous:
        cx, cy = centroid(f['geometry'])
        free = [m for m in cands if m.id not in taken] or cands
        best = min(free, key=lambda m: math.dist((cx, cy), centre.get(m.county_id, (99, 99))))
        matched[id(f)] = best
        taken.add(best.id)
        print(f"  shared name {f['properties']['shapeName']!r} -> {best.name} ({best.county.name})")

    # Projection over the whole country.
    pts = [p for f in features for ring in rings(f['geometry']) for p in ring]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    kx = math.cos(math.radians((lat0 + lat1) / 2))
    scale = WIDTH / ((lon1 - lon0) * kx)
    height = round((lat1 - lat0) * scale, 1)

    def path(geom):
        out = []
        for ring in rings(geom):
            prev, cmds = None, []
            for lon, lat in ring:
                x = round((lon - lon0) * kx * scale, 1)
                y = round((lat1 - lat) * scale, 1)
                if (x, y) != prev:
                    cmds.append(f'{x:g},{y:g}')
                    prev = (x, y)
            if len(cmds) >= 3:
                out.append('M' + 'L'.join(cmds) + 'Z')
        return ''.join(out)

    # Unassigned outlines are kept without an id, drawn as "no data", so the
    # map has no holes.
    shapes = [{'id': matched[id(f)].id if id(f) in matched else None,
               'name': matched[id(f)].name if id(f) in matched else f['properties']['shapeName'],
               'd': path(f['geometry'])}
              for f in features]
    payload = {
        'viewBox': f'0 0 {WIDTH:g} {height:g}',
        'source': 'geoBoundaries (HRV ADM2, 2021) / © OpenStreetMap contributors, CC BY-SA',
        'shapes': shapes,
    }
    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'))
    db_ids = set(Municipality.objects.filter(type__in=('grad', 'općina')).values_list('id', flat=True))
    print(f'{len(matched)} of {len(features)} outlines matched, {len(missing)} drawn without data: {missing}')
    print(f'{len(db_ids - {s["id"] for s in shapes})} grad/općina rows without an outline '
          '(places merged away before 2021 have none)')
    print(f'wrote {args.out} ({os.path.getsize(args.out) // 1024} KB)')


if __name__ == '__main__':
    main()
