# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Projekt Izbori" — a Croatian elections data platform. Imports results from 4 election types (presidential, sabor, EU parliament, local) into a unified PostgreSQL database. Enables cross-election politician search and analytics.

## Tech Stack

- **Backend**: Django 6.0 + PostgreSQL 16
- **Frontend/Analytics**: Flask (app.py) on port 5001 with SQLAlchemy, serving `templates/index.html`
- **Python**: 3.12 (via Homebrew), virtualenv at `./venv`
- **Data import**: Custom Django management commands with pandas/openpyxl
- **Database**: `projekt_izbori` (local PostgreSQL)
- **Frontend libs** (CDN): Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.7, SheetJS (XLSX), html2canvas 1.4.1, jsPDF 2.5.1

## Commands

```bash
source venv/bin/activate

# Run imports
python manage.py import_presidential
python manage.py import_eu_parliament                 # defaults to --year 2024
python manage.py import_eu_parliament --year 2019     # 2019+ live in {year}/CSV/
python manage.py import_eu_parliament --year 2014     # 2014 file has a different layout (see eu_parliament.py YEAR_CONFIG)
python manage.py import_eu_parliament --year 2013     # Croatia's first EP election (April 2013, 12 seats for partial term)
python manage.py import_sabor                         # defaults to --year 2024
python manage.py import_sabor --year 2020             # other years live in {year}/CSV/
python manage.py import_sabor --year 2015             # 2015 uses the 2020/2024 filename convention
python manage.py import_sabor --district 12 --wipe-district  # re-import single district (applies to --year)
python manage.py import_local
python manage.py set_election_dates [--dry-run]         # polling dates on elections + rounds
python manage.py normalize_persons [--dry-run]
python manage.py merge_person_aliases [--dry-run]      # curated same-person name variants
python manage.py merge_person_aliases --suggest        # list new middle-name splits for review
python manage.py normalize_municipalities [--dry-run]  # merge "GRAD X"/"OPĆINA X" dup munis
python manage.py clean_person_titles [--dry-run]       # strip academic titles from Person rows, merge with un-titled twin if one exists. `clean_candidate_name` (name_utils.py) handles dotted prefixes run-together or space-separated (mr.sc., prof. dr. sc.), trailing suffixes (, dipl.iur.), and spelled-out titles with no dot (akademik, akademkinja)

# Django
python manage.py runserver
python manage.py makemigrations elections
python manage.py migrate

# Flask analytics app
python app.py  # runs on port 5001
```

## Development Setup & Tooling

**There is no test suite, no linter, and no dependency manifest** — don't go looking for them. `elections/tests.py` is the untouched 3-line Django stub, so there is no "run a single test" command; `python manage.py test elections` runs zero tests. Verification in this project is done by querying the DB after an import and cross-checking against published results (see the invariant checks described under sabor.py, and the D'Hondt seat totals per year).

Dependencies are installed directly into `./venv` with no `requirements.txt` to reproduce them. Current versions: Django 6.0.3, Flask 3.1.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.48, pandas 3.0.1, openpyxl 3.1.5, psycopg2-binary 2.9.11.

`settings.py` configures PostgreSQL with only `NAME: projekt_izbori` — no host/user/password, so it connects over the local socket as the current OS user. There is no `.env` for the DB.

Two apps read the **same** PostgreSQL database through **two different ORMs**: Django owns the schema (models + migrations), while `app.py` re-declares the same tables as SQLAlchemy models pinned to Django's table names via `__tablename__` (e.g. `elections_electionround`). **A schema change therefore needs editing in both places** — add the Django field, migrate, then mirror the column on the SQLAlchemy model or Flask reads will fail. `ElectionRound.date` is the worked example.

Ad-hoc DB queries outside `manage.py` need Django bootstrapped explicitly:
```bash
DJANGO_SETTINGS_MODULE=projekt_izbori.settings python -c "import django; django.setup(); ..."
```

## Architecture

### Django App: `elections`

Models split into 4 modules under `elections/models/`:
- **geography.py** — County (23), Municipality (638), PollingStation (9416). County rows are keyed by a 2-char `code`: `01`–`21` are the real counties (`21` = Grad Zagreb), `00` = **inozemstvo** (diaspora, whose "municipalities" are countries), and `99` = `REPUBLIKA HRVATSKA (sažetak)`, a national-summary pseudo-county. Note the diaspora's primary key happens to be **id 22** — older notes calling it "county 22" mean the id, not the code.
- **elections.py** — ElectionType, Election, ElectionRound, ElectoralDistrict. **Dates live on both**: `Election.date` is the first round, `ElectionRound.date` the round's own polling day — a runoff sits weeks later and can cross into the next calendar year (2019 presidential: 22 Dec 2019, runoff 5 Jan 2020), so the election-level date mislabels round 2. Seed both with `set_election_dates` (official dates for all 25 elections / 34 rounds live in that command; add new years there). Result badges show a full date via `round_date_iso(er, election)` in app.py, which prefers the round date and falls back to the election's, then to the bare year — a missing date degrades silently, which is why every year except EU 2024 used to show only "2016".
- **participants.py** — Person (normalized_name for cross-election search), Party, ElectoralList, Candidacy
- **results.py** — TurnoutData, ListResult, CandidateResult

### Election Polling Dates

Every date currently in the DB, as seeded by `set_election_dates` (that command is the source of truth — change it, not this table). Round 2 is the runoff; **bold** ones fall in the calendar year *after* the election's `year`, which is why `ElectionRound.date` exists.

| Type | Year | Round 1 | Round 2 |
|---|---|---|---|
| Predsjednički | 1992 | 2 Aug 1992 | — |
| Predsjednički | 1997 | 15 Jun 1997 | — |
| Predsjednički | 2000 | 24 Jan 2000 | 7 Feb 2000 |
| Predsjednički | 2005 | 2 Jan 2005 | 16 Jan 2005 |
| Predsjednički | 2009 | 27 Dec 2009 | **10 Jan 2010** |
| Predsjednički | 2014 | 28 Dec 2014 | **11 Jan 2015** |
| Predsjednički | 2019 | 22 Dec 2019 | **5 Jan 2020** |
| Predsjednički | 2024 | 29 Dec 2024 | **12 Jan 2025** |
| Sabor | 2015 | 8 Nov 2015 | — |
| Sabor | 2016 | 11 Sep 2016 | — |
| Sabor | 2020 | 5 Jul 2020 | — |
| Sabor | 2024 | 17 Apr 2024 | — |
| EU parlament | 2013 | 14 Apr 2013 | — |
| EU parlament | 2014 | 25 May 2014 | — |
| EU parlament | 2019 | 26 May 2019 | — |
| EU parlament | 2024 | 9 Jun 2024 | — |
| Lokalni (all 9 types) | 2025 | 18 May 2025 | 1 Jun 2025 |

Sabor and EU parlament are single-round by law. Lokalni share one polling day across all 9 sub-types, but only the executive offices (`local_mayor`, `local_city_mayor`, `local_county_prefect`) actually hold a runoff — councils and assemblies are decided in round 1, so only those three have a round-2 row in the DB. **Provenance**: EU 2024, presidential 1992/1997/2024 and lokalni 2025 were already stored before this table existed and agreed with it; the other 12 were added from public record and are worth spot-checking if a badge ever looks wrong.

### Import Pipeline: `elections/importers/`
- **base.py** — BaseImporter with geography/person caches and bulk result insertion (batch size 5000). `get_or_create_municipality()` matches on a **prefix-/hyphen-normalized name** (`normalize_municipality_name` in `name_utils.py`) so the same place isn't split when one year's file says `DUGO SELO` and another says `GRAD DUGO SELO`. Legacy split rows were merged by the one-off `normalize_municipalities` command (repoints polling stations — merging by station number on collision — plus turnout/list/candidate result rows, then deletes the empty dup; guarded against merging genuine grad-vs-općina pairs). This split is why per-municipality views previously showed zeros for some election years (e.g. predsjednički 2005 in Dugo Selo). A further set of **presidential-only** name-variant splits (not prefix-based, so unreachable by the command) was merged by hand: "SVETI X" vs "SV. X" abbreviations, Istrian Croatian/Italian **bilingual** names added from 2014 on (`PULA` → `PULA - POLA`, etc.), and disambiguators (`OTOK (VINKOVCI)`, `DONJI MARTIJANEC`). For diaspora (county 22) only pure abbreviations + the Macedonia rename were merged; **`SRBIJA I CRNA GORA` (2005) is intentionally kept separate** from `SRBIJA`/`CRNA GORA` as a real historical entity. Turnout is buffered in a dict keyed on `(election_round, polling_station)` and **summed** across repeated calls, flushed via `bulk_create(update_conflicts=True)` — this handles Sabor mobile/abroad stations that appear in all 10 district files.
- **presidential.py** — UTF-8 BOM CSV, semicolon delimited, title row + header + data. Covers 2000-2024. **1992 and 1997 are national-summary-only** (own commands, `import_presidential_1992` / `_1997`): no per-station data exists for them, so each is stored as a *single* TurnoutData row hanging off one pseudo-station under county `99 REPUBLIKA HRVATSKA (sažetak)` (1992: 3,575,032 registered / 74.90% turnout; 1997: 4,061,479 / 54.62%). Nothing is double-counted — those years have no real stations to also sum — but any per-station, per-muni or per-county view will legitimately come back empty for them, and national aggregates must not treat `99` as a 23rd county alongside the real ones.
- **sabor.py** — windows-1250 CSV. Districts 1-10: fixed 15 cols/list (1 list + 14 candidates). District 11 (diaspora): **variable-width** list groups (parties may nominate fewer than 14 candidates), parsed in `_parse_list_groups_variable()` by finding the list-name columns and treating everything between two of them as the first one's candidates. Two layers decide what a list name is: (1) `_is_list_name()` — party punctuation (` - `, `!`, `"`) or a `LIST_KEYWORDS` hit, else *not* `looks_like_person_name()`. A bare comma is deliberately **not** a list signal, because 2015/2016 CSVs put academic titles in candidate columns ("IVANA BUNTIĆ, mag. iur.") — treating those as lists shattered the groups and stored candidates as electoral lists (2016 d11 had 26 lists, 12 of them people). (2) `_repair_list_cols()` — a data-driven backstop: a preferential vote only counts for the list it was cast on, so candidate votes can never outnumber their list's votes. Where a group violates that, the column at which the running candidate total overruns the list total is a missed list start (2016's "AKCIJA MLADIH" — a real party that reads like a person's name). Only violating groups get split, so correct boundaries survive. Needs column totals, so `_import_district()` makes a pre-pass with `_column_totals()` for d11 only. All four years now parse with zero invariant violations (2015: 11 lists, 2016: 14, 2020: 11, 2024: 8). District 12 (minorities): split into 6 sub-districts (121-126, one per minority group: Serbian 3 seats, others 1 each = 8 total). Year-aware: `SaborImporter(year=YYYY)` reads from `{BASE_DIR}/{year}/CSV/`; the column layout has been stable across 2015, 2016, 2020 and 2024 so no per-year layout config needed. **Filenames differ by year, though**: 2015/2020/2024 name files `XX_DD_rezultati*.csv` (district in the 2nd field, e.g. `02_01`; d12 subs `13_12`…`63_12`), but 2016 swaps the fields — `DDD_00_rezultati*.csv` (district in the 1st field, e.g. `001_00`; d12 subs `012_13`…`012_63`). `_get_files_for_district()` falls back to a first-field glob when the second-field pattern finds nothing, and `_import_district_12()` picks whichever of the first two fields is a known sub-district code, so both conventions work transparently. Supports `--year`, `--district N`, and `--wipe-district` flags for targeted re-import (wipe is year-scoped). **Station-number prefixing**: `_station_number_prefix()` adds `P` for posebna (mobile) and `I` for inozemstvo (abroad) files so that e.g. main station `006` (ČEHI) and mobile station `006` (DOM 85) in the same muni label do not collapse into one PollingStation row. See `docs/sabor_polling_station_fix.md` for full root-cause analysis. **District 12 turnout is skipped on import** — d12 CSVs report minority-only voter counts (subset of station total), so real turnout comes from districts 1-10. The `--wipe-district 12` path likewise preserves existing TurnoutData rows. Candidate names pass through `clean_candidate_name` so academic titles don't split persons across years (same pattern as eu_parliament.py).
- **eu_parliament.py** — windows-1250 CSV; per-year layout in `YEAR_CONFIG` (file path, geo-column count, candidates-per-list, named column offsets). `EUParliamentImporter(year=YYYY)` selects the right config. 2024/2019 share one shape (13 geo cols, 12 candidates/list, in `{year}/CSV/rezultati_eupa.csv`); 2014 has 19 geo cols (extra Rbr GČ / MO / IJ between muni and station — skipped), 11 candidates/list (Croatia had 11 EP seats then), and lives at `2014/rezultati_eupa_interno_rezultati_eupa.csv` (no CSV subdir); 2013 (Croatia's first EP election, partial term, 12 seats) is at `2013/EUP2013_rezultati_po_BM_Work.csv` and matches the 2019/2024 shape. Adding a new year = add a `YEAR_CONFIG` entry. Candidate names pass through `clean_candidate_name` so academic titles ("mr.sc. ", ", dipl.iur.", "struč.spec.oec.", …) — heavily used in older CSVs — don't end up in the stored Person name and split cross-year matching. The "blue-dot" MEP badge (`ElectedMandate`) is seeded **per saziv** via `set_eu_mandates --year YYYY`; rosters live in `MEPS_BY_YEAR` (currently 2024 + 2019 + 2014). Each year is authoritative for its own term — re-running the command for one year touches only that year's mandate rows. The badge tooltip shows `saziv {year}.` dynamically from the result's `r.year`.
- **local.py** — Excel .xlsx, 2-4 sheets per file, list-level results only (no per-candidate breakdown within lists)

### Flask Analytics App (`app.py`)
Single-page app with multiple modules, served at port 5001:
- **Politician search** — cross-election search by name
- **Polling station search** — by location (county → municipality → station)
- **Interactive Croatia map** — SVG map (`static/croatia_map.svg`) with county selection
- **National results** — aggregated results by election type and year
- **Multi-compare** — side-by-side comparison of candidates/lists
- **Politician status badges** (`/api/person/<id>` per result + chart points): 🥇 winner (rank 1) / 🥈 runner-up (rank 2) for head-to-head races; 🟢 `won_seat` for Sabor seats (computed via `sabor_seat_winner_candidacy_ids()` — D'Hondt + 10% preferential); 🔵 `eu_mep` for sitting MEPs. The EU MEP set **can't be computed** (some elected candidates ceded their seat to the next on the preferential list), so it's stored in the **`ElectedMandate` table** (`elections_electedmandate`, OneToOne→Candidacy, optional `group` = EP political group). Seed/refresh via `python manage.py set_eu_mandates` (the curated 12-name list lives in that command); also editable in Django admin. `person_detail` reads the table per candidacy.
- **Lokalni izbori per-station / per-muni / per-županija results** (`/api/lokalni/station-results`): one endpoint, four kinds — `vijece`, `nacelnik` (muni-level, need `municipality_id` or `station_id`) and `zupan`, `zup_skupstina` (county-level, need `county_id`). Shared `scope_stations` subquery aggregates votes/turnout, returns per-station turnout breakdown for any non-single-station scope. See `docs/lokalni_county_level_kinds.md`.
- **Lokalni deep-linking from politician pages**: clicking a politician's lokalni badge or chart circle preselects the županija/grad-općina/vrsta-izbora dropdowns instead of landing on the empty default. `person_detail` emits `lokalni_kind` (`nacelnik`/`vijece`/`zupan`/`zup_skupstina`), `county_id`, and `municipality_id` per result (derived from the list's first polling-station muni); `izlNavigateTo(cat, year, opts)` + `lokalniPreselect(opts)` drive the cascading dropdowns by polling for each option to appear before dispatching its `change` event (each step is async — county-change fetches munis, muni-change fetches stations).
- **Person hyperlinks on lokalni bar charts**: `LOK_PERSON_KINDS = {nacelnik, zupan}` — for those kinds, lists are 1:1 with a candidate so `renderLokResultCard` sets `kind: 'person'` on `_electionBarData`. `buildBarChart` already turns those labels into `.bar-label-link` → `navigateToPerson(name)` (fuzzy-search by normalized name). Vijeće / županijska skupština labels are party tickets, intentionally non-linkable.
- **Person hyperlinks on Sabor/EU Zastupnici tables**: same `.bar-label-link` span pattern is applied directly to candidate-name `<td>`s in three places — `renderCandidateList` (Sabor simulation Zastupnici), the Konačni rezultati `saActualCandidateList` block, and the EU `buildRow` per-candidate row in `renderEuView`. One delegated `click` handler on `.bar-label-link` covers all of them.
- **Sabor muni dropdown**: `/api/sabor/district-municipalities` still returns vote counts (used for the ≥50-vote threshold that hides diaspora pseudo-munis like ALBANIJA), but the frontend ignores them — labels show plain names sorted alphabetically with `localeCompare('hr')` so Š/Ž/Č land correctly. Same backend payload as before; render-only change.
- **Horizontal-scroll wrapper for all line charts** (`applyChartScroll` / `ensureChartScrollWrap`): the izlaznost, station-winner, single-politician and compare line charts now share a generic helper that wraps the canvas in `chart-scroll-wrap > chart-scroll-outer > chart-scroll-inner`, sizes the inner to `labelCount × 95px + 80px` of padding, and adds floating left/right chevron buttons (top-right of the wrap, *outside* the scrolling area so they stay pinned). **Must be called before `new Chart(ctx, …)`** — Chart.js measures the parent on creation, so a later `chart.resize()` doesn't widen an already-pinned chart.
- **Sabor analysis** (`/api/national/sabor-seats/<year>`, `/api/national/sabor-raw/<year>`):
  - **Konačni rezultati**: D'Hondt seat allocation with hemicycle visualization and candidate list
  - **Složi svoju koaliciju — simulacija**: Client-side D'Hondt with drag-to-merge coalitions, 5% threshold toggle, and "Aktiviraj skakače" (manual seat transfers between parties)
  - **Electoral district map** (`static/croatia_districts.svg`): Interactive SVG showing districts I-X, displayed next to hemicycle in both sections
  - **Exports**: XLSX (SheetJS) and PDF (html2canvas + jsPDF) with hemicycle visuals
- Coalition variants (e.g., "HDZ, HSLS" vs "HDZ, HSLS, HDS") are grouped by `primary_party()` (first name before comma)
- Minority district returns individual winners with `group: "NACIONALNE MANJINE"` for unified display, but `fixed_seats` per candidate for correct allocation (no D'Hondt — seats assigned directly from sub-district results)

### Key Design Decisions
- All election types share the same ListResult/CandidateResult tables
- Even single candidates (presidential, mayors) get an ElectoralList for uniformity
- Person.normalized_name (diacritics stripped, uppercase) enables cross-election search
- **Middle-name splits are curated, never automatic** (`merge_person_aliases`): DIP records a middle name in some years and not others, so the same person lands in two Person rows ("IVAN SINČIĆ" in the 2014 presidential/EU and 2015 sabor files vs "IVAN VILIBOR SINČIĆ" from 2016 on). `normalize_persons` can't catch these — it only merges exact normalized-name matches — and they can't be merged by rule either, because genuinely different people also differ by one middle token (ŽELJKA BARIČEVIĆ vs ŽELJKA ILIJAŠ BARIČEVIĆ, both sabor 2024, different parties and districts). Each merge in `KNOWN_ALIASES` carries its evidence; `--suggest` lists new candidates after an import and flags any pair sharing an election type+year as near-certainly two people, since nobody stands twice in one election. Currently merged: Sinčić, Predrag Fred Matić, Natalia Tafra Bazina. **7 pairs are deliberately left unmerged** — 4 confirmed distinct, 3 (Marija Brajdić Vuković, Ana-Marija Barnjak Lovrić, Ivana Ocvirek Orlić) unresolved added-surname cases awaiting evidence.
- Bulk insert with `ignore_conflicts=True` for performance
- Geography and person caches in BaseImporter avoid repeated DB lookups
- District 12 minorities use sub-districts 121-126 in DB, merged to single "NACIONALNE MANJINE" group in API responses
- Raw API includes `group` field per list for client-side coalition grouping

### Data Files (not in git)
Located in `files/` directory:
- `Rezultati_predsjednicki_izbori_2024/` — 2 CSV files
- `Rezultati_eu_parlamet_2024/{2024,2019}/CSV/` + `{2014,2013}/` — 2 CSV files per year (2014/2013 live directly under their year folder with their own filenames; parent folder kept its original 2024-only name)
- `rezultati_sabor_2024/{2024,2020,2016,2015}/CSV/` — 11 districts × 3 file types + 6 district 12 files × 3 = 51 per year for 2024/2020; 2016 and 2015 have 50, missing district 11's inozemstvo file (d11 *is* the diaspora district, so it ships only `rezultati` + `posebna`). Parent folder kept its original 2024-only name. 2016 uses a swapped filename convention (see sabor.py note above). 2016/2015 also ship the source `Excel/` alongside `CSV/`.
- `Rezultati_lokalni_izbori_2025/` — 697 Excel files across krug-1 and krug-2

## Workflow Rules

- **Commit frequently**: After completing any meaningful unit of work, commit changes to git with a clear, descriptive commit message.
- **Push to GitHub**: Always push commits to the remote GitHub repository so work is never lost.
- **Clean commit messages**: Use concise commit messages that explain *what* changed and *why*. Follow conventional style (e.g., "Add election data parser", "Fix vote counting logic").
- **Update CLAUDE.md**: When key decisions are made (architecture choices, tech stack, design patterns, major features), update this file so future sessions have full context.
