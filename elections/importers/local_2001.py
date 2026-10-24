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


class Local2001Importer(Local2009Importer):

    year = 2001
    text_glob = 'Z*.txt'

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
