# Sabor 2024 polling station collision — root cause and fix

## Symptom

On the polling-station detail page, some stations showed candidate
percentages > 100% (e.g. SENECURA DOM ZA STARIJE I NEMOĆNE TREŠNJEVKA
at JEZERSKA ULICA 24A: TOMISLAV TOMAŠEVIĆ 30 votes out of 21 valid
ballots = 143%).

## Root cause (two-part bug in `SaborImporter`)

### 1. Station-number collision between file types

DIP's Sabor CSVs are split per district into three file types:

- `*_rezultati.csv` — main (regular) stations, numbered `001`…`NNN`.
- `*_rezultati_posebna.csv` — mobile/special stations (retirement
  homes, hospitals, prisons, ships, military bases), numbered
  `001`…`NNN` starting from 1 again.
- `*_rezultati_inozemstvo.csv` — stations abroad (embassies,
  consulates), also numbered from 1.

All three file types share the same `Grad/općina/država` label
per row. For Zagreb the label is `ZAGREB - VI. IZBORNA JEDINICA`
(a district label, not a real city). For other cities the label is
the real city name (SPLIT, OSIJEK, …). Either way, posebna station
`006` and main station `006` end up in the same `Municipality`.

The importer's `get_or_create_polling_station` keys stations by
`(municipality, number)`. With `number='006'` shared between a main
and posebna row in the same muni, **two different physical stations
collapse into one PollingStation row**. Example:

| File               | num | ps_name          | location                                   | address               | valid |
| ------------------ | --- | ---------------- | ------------------------------------------ | --------------------- | ----- |
| `02_06_rezultati`  | 006 | ČEHI             | PROSTORIJE MJESNOG ODBORA                  | ULICA SLAVKA ČORA 37  | 468   |
| `02_06_…_posebna`  | 006 | DOM 85, ZAGREB   | SENECURA DOM ZA STARIJE I NEMOĆNE TREŠNJ.  | JEZERSKA ULICA 24A    | 19    |

Both map to one row. The row's name/location/address come from
whichever file was processed first; results from both files are
partly kept, partly dropped by `ignore_conflicts=True` (see #2).

DOM 85 appears in **all 10 mainland district posebna files**
(residents of the home are registered in many districts), so the
same merged row also absorbs fragments of D1, D2, …, D10 data.

This collision affects every Croatian city where posebna stations
coexist with main stations — SPLIT had `001`…`005` overlap between
main and posebna; similar pattern in Zagreb, Osijek, Rijeka, etc.

### 2. Turnout silently dropped, results partially kept

`create_turnout` and `create_list_result` / `create_candidate_result`
all used `bulk_create(..., ignore_conflicts=True)` with unique
constraints on `(election_round, polling_station)` and
`(list/candidacy, polling_station)`.

With one PollingStation row shared between ČEHI and DOM 85:

- **Turnout**: the first file's row (say DOM 85, 21 valid)
  is inserted; subsequent inserts from the other files for
  the same `(er, ps)` key are silently ignored. Only one
  district's turnout survives.
- **List and candidate results**: each file's writes target
  different `ElectoralList`/`Candidacy` rows (one per district),
  so there's usually no conflict — all writes land on the same
  PollingStation row and accumulate. But when both ČEHI's D6
  main-file row and DOM 85's D6 posebna row target the SAME
  `ElectoralList` (D6 lists), only the first write survives.

End result: the merged row had ČEHI's D6 numbers (30 Tomašević,
63 Možemo list votes) AND DOM 85's D1–D5/D7–D10 posebna
fragments, AND DOM 85's D1 turnout (21). Candidate totals
(30 across ČEHI + partial DOM 85) vs. turnout (21, D1 only)
produced 143%.

## Fix

Two changes, both in `elections/importers/`:

### a) Disambiguate station numbers by file type (`sabor.py`)

Prefix the polling-station number with `P` for posebna files and
`I` for inozemstvo files before calling
`get_or_create_polling_station`. Regular (main) files keep the raw
number. So:

- Main-file ČEHI: `(muni=602, num='006')` → PollingStation A
- Posebna-file DOM 85: `(muni=602, num='P006')` → PollingStation B

DOM 85's rows from all 10 mainland districts still collapse to
one row (same `muni=602, num='P006'`) — which is correct, because
it IS one physical location. Turnout across those 10 districts
then needs to sum, handled by (b).

Implemented as `SaborImporter._station_number_prefix(filepath)`,
called at the top of `_import_file` and `_import_file_d12`.

### b) Sum turnout across duplicate `(er, ps)` writes (`base.py`)

Change `_turnout_buffer` from a list to a dict keyed on
`(election_round_id, polling_station_id)`. When `create_turnout`
is called with a key already in the buffer, **add** the new
`registered`/`cast`/`valid`/`invalid` onto the existing object.
`_flush_turnout` uses `bulk_create(update_conflicts=True, ...)`
and never clears the buffer, so repeated flushes keep the latest
cumulative total in the DB and are idempotent.

This makes DOM 85's turnout correctly equal to the sum of its
ten district-specific counts (reg=55, cast=46, valid=46 instead
of reg=27, cast=21, valid=21).

## Scope

- **Sabor 2024**: ~6741 stations had wrong data. Fixed.
- **Presidential 2024**: unaffected — mobile stations use 9NN
  numbering, no collision with main 0NN.
- **EU 2024**: unaffected — single CSV file covers everything.
- **Local 2025**: unaffected — each municipality's data is in
  its own file, no cross-file station sharing.

## Re-import procedure

Orphaned PollingStation rows created by the buggy import need
to be removed so the new (prefixed) rows can be reused cleanly:

```python
# Wipe Sabor 2024 data
from elections.models import Election, TurnoutData, PollingStation, ListResult, CandidateResult
from django.db.models import Exists, OuterRef

sabor = Election.objects.filter(election_type__slug='sabor', year=2024).first()
if sabor:
    TurnoutData.objects.filter(election_round__election=sabor).delete()
    sabor.delete()  # cascades rounds → lists → candidacies → results

# Delete orphan polling stations (no turnout / list / candidate data anywhere)
PollingStation.objects.annotate(
    has_t=Exists(TurnoutData.objects.filter(polling_station=OuterRef('pk'))),
    has_l=Exists(ListResult.objects.filter(polling_station=OuterRef('pk'))),
    has_c=Exists(CandidateResult.objects.filter(polling_station=OuterRef('pk'))),
).filter(has_t=False, has_l=False, has_c=False).delete()
```

Then `python manage.py import_sabor`.

## Verification

After fix, for station SENECURA / JEZERSKA 24A (DOM 85):

- Station row: id=8062, `num='P006'`, muni `ZAGREB - VI. IZBORNA JEDINICA`.
- Turnout (Sabor 2024): reg=55, cast=46, valid=46 (sum across 10 districts).
- Top candidate: ANDREJ PLENKOVIĆ 2 votes (4%). No more >100%.

ČEHI (main-file) is now a separate row with its own turnout
(reg=713, valid=468) and D6 results intact.

## Known residual issue (separate)

After the fix, 288 `CandidateResult` rows still show `votes >
station_valid`. All are D12 minority sub-district candidates
(121 "Srpska" minority: 261 cases; 122/124/125/126: the rest).

This is NOT caused by station-key collision. Minority voters cast
an ADDITIONAL ballot separate from the regular district ballot, and
minority votes can be cast at any station regardless of where the
voter is registered for the regular election. So the denominator
`TurnoutData.valid_ballots` (regular ballots, from D1–10 main files)
is the wrong denominator for minority-candidate percentages — the
correct denominator is per-minority-sub-district turnout from the
`*_12_rezultati*.csv` files, which the importer currently skips
("IMPORTANT: Skip turnout — d12 files have minority-only voter
counts, not station totals" — see `_import_file_d12`).

Fixing this correctly requires either:
- Tracking minority turnout as a separate per-(station, sub-district)
  TurnoutData row; or
- Excluding minority candidates from percentage displays in the
  polling-station detail view and showing absolute counts only.
