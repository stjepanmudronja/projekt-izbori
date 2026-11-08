"""Import the 2001 lokalni izbori from DIP's per-county PDF report.

`2001/ZN.pdf` (N = county code) holds the representative bodies elected on
20 May 2001: 20 županijske skupštine, the gradska / općinska vijeća and
Zagreb's Gradska skupština. Its fonts have no Unicode mapping, so the text
is dumped by `tools/pdf_glyph_text.py` into `2001/text/ZNN.txt`; parsing and
the party-name folding live in `local_2001_parse.py`. Stored as 2005 and
2009 are (`Local2009Importer`), with one difference: the report prints no
valid-ballot figure, so a contest's valid votes are the sum of its lists.
"""
from .local_2009 import Local2009Importer
from .local_2001_parse import check, parse_dir


# List leaders the report prints surname-first, so the stored name is turned
# round. Five Virovitičko-podravska sections print every leader that way
# ("KUMRIĆ ŽELJKO"); elsewhere a single name is. Each confirmed by the same
# person standing first-name-first in that place in another year (Željko
# Kumrić, Suhopolje nositelj 2005 and načelnik 2009; Ivica Lulić, Špišić
# Bukovica načelnik 2009; Anđelko Novoselnik, Crnac načelnik 2009; Zdravko
# Dijaković, Pitomača načelnik 2021; Vladimir Janečić, Voćin načelnik 2009;
# Dušan Hrelja, Buje nositelj 2005), and in the rest by the order alone:
# a given name second ("RENGEL ĐURO", "VUKOVIĆ BOŽO", "PAVIŠIĆ SLAVKO").
SURNAME_FIRST_SECTIONS = {'CRNAC', 'PITOMAČA', 'SUHOPOLJE', 'ŠPIŠIĆ BUKOVICA', 'VOĆIN'}
SURNAME_FIRST_NAMES = {('BUJE - BUIE', 'HRELJA DUŠAN'), ('VRSAR - ORSERA', 'PAVIŠIĆ SLAVKO')}


class Local2001Importer(Local2009Importer):

    year = 2001
    text_glob = 'Z*.txt'
    store_holders = True

    def _holder_order(self, name, municipality):
        if municipality.name in SURNAME_FIRST_SECTIONS or (municipality.name, name) in SURNAME_FIRST_NAMES:
            words = name.split()
            if len(words) != 2:
                raise RuntimeError(f'{municipality.name}: cannot turn round "{name}"')
            return f'{words[1]} {words[0]}'
        return name

    def _county_code(self, path):
        return f'{int(path.stem[1:]):02d}'

    def _parse(self, code, text):
        # Party names are folded across the whole report, so every file is
        # parsed up front and handed out by county.
        if not hasattr(self, '_by_county'):
            from .local import LocalImporter
            self._by_county = {}
            for _stem, c in parse_dir(LocalImporter.DATA_DIR / '2001' / 'text'):
                self._by_county.setdefault(c['county'], []).append(c)
        return [(c, check(c)) for c in self._by_county.get(code, [])]
