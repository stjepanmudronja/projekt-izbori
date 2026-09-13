"""Import the 2000 Sabor election (3 January 2000).

A fourth export dialect, closest to 2003 — same six-column geo block, same
"Grad/ općina" / "Broj biračkog mjesta" labels, numbers with a thousands dot —
so this subclasses `Sabor2003Importer` and changes only what differs:

  * **Two header rows**, not three: a spanning "Stranka/Koalicija" banner and
    then the real labels.
  * **The result columns are numbered, not named.** The header reads
    `1;2;3;…;31` and the list names live in a **separate legend file**,
    `ijNN_Stranke.csv`, one numbered group per list: the numbered row and any
    rows under it are the parties in the coalition, and the last row of the
    group is the list holder ("Ivica Račan"). So the roster is read from the
    legend and joined to the data by column number.
  * **No subtotal rows and no mixed-station files** — every row is a station.

**Only districts I-X are present.** 2000 ran under the 1999 constituency law,
which also created district XI for voters abroad and district XII for the
minorities, and both returned members (6 and 5 respectively, for a 151-seat
Zastupnički dom). No file for either was supplied, so this import covers the
140 domestic seats and `sabor_seats` will allocate only those; the hemicycle
still reports 151 because `sabor_total_seats` knows the full size.

### The district V legend

`ij05_Stranke.csv` lists 26 lists where `ij05_ij05.csv` has 25 columns, so one
legend entry has no column and every entry after it is shifted by one. Which
one cannot be read off the file, but it is tightly bounded:

  * The 25 columns sum **exactly** to the valid ballots, so no column carrying
    votes is missing — the gap is a list that took no column at all.
  * It is not the last entry. Under a straight 1:1 mapping the SDP-HSLS
    column would hold 1,611 votes in a district where SDP-HSLS is the second
    party, and the 70,935-vote column would belong to SDSS. Shifting puts
    70,935 on SDP-HSLS and 10,667 on SDSS, which is the only reading
    consistent with the national result.
  * It is not before #10 either: that would put 16,700 votes on Paraga's
    HSP-1861 rather than on HSP, and 50,982 on HSNZ rather than the HSS-led
    Šestorka list.

That leaves entries 14-18 — HR, KSU and three lists all literally called
NEOVISNA LISTA. Comparing each hypothesis against the same parties' shares in
the nine unambiguous districts ranks the three NEOVISNA entries first, but by
0.005 percentage points, which decides nothing; a concentration test (an
independent's vote is local, a fringe party's is spread) is equally flat.
`LEGEND_OMISSIONS` therefore records the assumption in one place rather than
burying it. **Nothing that matters turns on it**: districts, seats and every
named party are identical under all five readings, and the uncertainty is
confined to which of four small lists — 4,788 votes, 1.8% of the district —
carries columns 14-17.
"""
import csv
import re

from .sabor_2003 import Sabor2003Importer


# (year, district) -> the legend entry that has no column in the data file.
# See the module docstring: only district V needs one, and the choice moves
# 4,788 votes between four small lists without touching a seat.
LEGEND_OMISSIONS = {(2000, 5): 16}


class Sabor2000Importer(Sabor2003Importer):
    YEARS = (2000,)
    HEADER_ROWS = 2

    def __init__(self, year=2000, stdout=None):
        super().__init__(year=year, stdout=stdout)
        self.data_dir = self.BASE_DIR / str(year) / 'RezultatiPoBM' / 'CSV'
        self._legend = {}

    # ---- file discovery ----------------------------------------------

    def _files_for(self, district_tag):
        """The one result file per district. `ijNN_Stranke.csv` is the legend,
        not results, so it must not be imported as one."""
        tag = district_tag.lower()
        return [fp for fp in sorted(self.data_dir.glob('*.csv'))
                if self._norm_filename(fp) == f'{tag}_{tag}.csv']

    @staticmethod
    def _is_main_file(filepath):
        return True

    @classmethod
    def _station_prefix(cls, filepath):
        return ''

    def _read_header(self, filepath):
        """The column labels are on the *second* row — the first is a banner
        spanning the result columns with the single word "Stranka/Koalicija"."""
        with open(filepath, encoding=self.ENCODING, newline='') as fh:
            rows = csv.reader(fh, delimiter=';')
            next(rows, None)
            return next(rows)

    # ---- the legend ----------------------------------------------------

    def _read_legend(self, district_num):
        """Column number -> list name, from `ijNN_Stranke.csv`.

        A group is a numbered row plus the unnumbered rows beneath it; all but
        the last are the parties on the list, the last is the holder. Holders
        matter because a district can run several lists all called NEOVISNA
        LISTA, exactly as in 2003 and 2011 — `_list_names` appends the holder
        whenever a base name repeats, so they do not pool their votes.
        """
        path = self.data_dir / f'ij{district_num:02d}_Stranke.csv'
        groups, current = {}, None
        with open(path, encoding=self.ENCODING, newline='') as fh:
            for row in list(csv.reader(fh, delimiter=';'))[1:]:
                if len(row) < 2:
                    continue
                number, text = row[0].strip().rstrip('.'), row[1].strip()
                if number.isdigit():
                    current = int(number)
                    groups[current] = []
                if text and current is not None:
                    groups[current].append(text)
        return groups

    def _legend_for(self, district_num, n_columns):
        """Column number -> "<parties>, <holder>" label, aligned to the data.

        Where the legend has one entry more than the file has columns, the
        entry named in LEGEND_OMISSIONS is dropped and everything after it
        shifts down one.
        """
        groups = self._read_legend(district_num)
        omit = LEGEND_OMISSIONS.get((self.year, district_num))
        if len(groups) != n_columns and omit is None:
            self.log(f'  district {district_num}: legend has {len(groups)} lists for '
                     f'{n_columns} columns and no LEGEND_OMISSIONS entry — skipped')
            return {}
        names, column = {}, 0
        for index in sorted(groups):
            if index == omit:
                self.log(f'  district {district_num}: legend #{index} '
                         f'({groups[index][0][:40]}) has no column, assumed omitted')
                continue
            column += 1
            parts = groups[index]
            parties, holder = (parts[:-1], parts[-1]) if len(parts) > 1 else (parts, '')
            names[column] = f"{', '.join(parties)}, {holder}" if holder else ', '.join(parties)
        return names

    def _list_names(self, cols):
        """The parent reads list names out of the header; 2000's header holds
        only column numbers, so they come from the legend read for this
        district instead. Coalition-and-holder labels are then split by the
        inherited 2003 rule, which also handles the repeated-name suffix."""
        parsed = {i: self._split_list_label(self._legend.get(int(raw), ''))
                  for i, raw in cols if raw.strip().isdigit()}
        from collections import Counter
        counts = Counter(base for base, _ in parsed.values() if base)
        from .name_utils import clean_candidate_name
        return {i: (f'{base} - {clean_candidate_name(holder)}'
                    if base and counts[base] > 1 and holder else base)
                for i, (base, holder) in parsed.items()}

    # ---- districts -----------------------------------------------------

    def run(self, only_district=None):
        self._split_stations = 0
        election_type = self.get_or_create_election_type('sabor', 'Parlamentarni izbori')
        election = self.get_or_create_election(
            election_type, self.year, f'Parlamentarni izbori {self.year}')
        election_round = self.get_or_create_round(election, 1)
        self._build_muni_index()

        for district_num in range(1, 11):
            if only_district is not None and district_num != only_district:
                continue
            self._import_district(election, election_round, district_num)

        self.flush_all()
        if self._unresolved:
            self.log('Municipality names that could not be resolved to a county:')
            for name, n in sorted(self._unresolved.items(), key=lambda kv: -kv[1]):
                self.log(f'  {name!r} ({n} rows)')
        self.log('Districts XI (dijaspora) and XII (nacionalne manjine) returned '
                 '6 and 5 members in 2000 but no file for either was supplied, so '
                 '140 of the 151 seats are covered.')

    def _import_district(self, election, election_round, district_num):
        files = self._files_for(f'ij{district_num:02d}')
        if not files:
            self.log(f'No files found for district {district_num}')
            return
        header = self._read_header(files[0])
        info = self._parse_header(header)
        cols = self._result_columns(header, info['first_result'])
        self._legend = self._legend_for(district_num, len(cols))
        if not self._legend:
            return

        roman = self._roman(district_num)
        district = self.get_or_create_district(
            election, district_num, f'{roman}. IZBORNA JEDINICA')

        list_objs = {}
        for name in self._list_names(cols).values():
            if name and name not in list_objs:
                list_objs[name] = self.get_or_create_electoral_list(
                    election_round, name, district)
        self.log(f'District {district_num}: {len(list_objs)} lists')
        for fp in files:
            self._import_file(election_round, district, fp, list_objs, district_num)
