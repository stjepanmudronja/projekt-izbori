"""Import the 2005 lokalni izbori from DIP's per-county PDF report.

The same report as 2009 (`2005/i_06_NN_0000.pdf`, dumped to `2005/text/` by
`tools/pdf_text`) for the last year before direct elections of mayors and
župani: it holds only the representative bodies — 20 županijske skupštine,
549 gradska / općinska vijeća and Zagreb's Gradska skupština, all in one
round on 15 May 2005. Parsed by `local_2005_parse.py`; stored exactly as
2009 is (`Local2009Importer`): one `000` pseudo station per municipality,
county assemblies on the `<ŽUPANIJA> (SAŽETAK)` pseudo-municipality, list
names comma-joined and shared, independent lists suffixed with their holder.
Elected council members are not stored, as in every other year.
"""
from .local_2009 import Local2009Importer
from .local_2005_parse import parse_text, problems


class Local2005Importer(Local2009Importer):

    year = 2005

    def _parse(self, code, text):
        return [(c, problems(code, c)) for c in parse_text(text)]
