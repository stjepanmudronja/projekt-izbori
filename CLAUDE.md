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
python manage.py import_sabor                         # all districts
python manage.py import_sabor --district 12 --wipe-district  # re-import single district
python manage.py import_local
python manage.py normalize_persons [--dry-run]
python manage.py normalize_municipalities [--dry-run]  # merge "GRAD X"/"OPĆINA X" dup munis
python manage.py clean_person_titles [--dry-run]       # strip academic titles (mr.sc., dipl.iur., …) from Person rows, merge with un-titled twin if one exists

# Django
python manage.py runserver
python manage.py makemigrations elections
python manage.py migrate

# Flask analytics app
python app.py  # runs on port 5001
```

## Architecture

### Django App: `elections`

Models split into 4 modules under `elections/models/`:
- **geography.py** — County (22), Municipality (604), PollingStation (7544)
- **elections.py** — ElectionType, Election, ElectionRound, ElectoralDistrict
- **participants.py** — Person (normalized_name for cross-election search), Party, ElectoralList, Candidacy
- **results.py** — TurnoutData, ListResult, CandidateResult

### Import Pipeline: `elections/importers/`
- **base.py** — BaseImporter with geography/person caches and bulk result insertion (batch size 5000). `get_or_create_municipality()` matches on a **prefix-/hyphen-normalized name** (`normalize_municipality_name` in `name_utils.py`) so the same place isn't split when one year's file says `DUGO SELO` and another says `GRAD DUGO SELO`. Legacy split rows were merged by the one-off `normalize_municipalities` command (repoints polling stations — merging by station number on collision — plus turnout/list/candidate result rows, then deletes the empty dup; guarded against merging genuine grad-vs-općina pairs). This split is why per-municipality views previously showed zeros for some election years (e.g. predsjednički 2005 in Dugo Selo). A further set of **presidential-only** name-variant splits (not prefix-based, so unreachable by the command) was merged by hand: "SVETI X" vs "SV. X" abbreviations, Istrian Croatian/Italian **bilingual** names added from 2014 on (`PULA` → `PULA - POLA`, etc.), and disambiguators (`OTOK (VINKOVCI)`, `DONJI MARTIJANEC`). For diaspora (county 22) only pure abbreviations + the Macedonia rename were merged; **`SRBIJA I CRNA GORA` (2005) is intentionally kept separate** from `SRBIJA`/`CRNA GORA` as a real historical entity. Turnout is buffered in a dict keyed on `(election_round, polling_station)` and **summed** across repeated calls, flushed via `bulk_create(update_conflicts=True)` — this handles Sabor mobile/abroad stations that appear in all 10 district files.
- **presidential.py** — UTF-8 BOM CSV, semicolon delimited, title row + header + data
- **sabor.py** — windows-1250 CSV. Districts 1-10: fixed 15 cols/list (1 list + 14 candidates). District 11 (diaspora): **variable-width** list groups (parties may nominate fewer than 14 candidates), parsed via `_is_list_name()` keyword heuristic in `_parse_list_groups_variable()`. District 12 (minorities): split into 6 sub-districts (121-126, one per minority group: Serbian 3 seats, others 1 each = 8 total). Supports `--district N` and `--wipe-district` flags for targeted re-import. **Station-number prefixing**: `_station_number_prefix()` adds `P` for posebna (mobile) and `I` for inozemstvo (abroad) files so that e.g. main station `006` (ČEHI) and mobile station `006` (DOM 85) in the same muni label do not collapse into one PollingStation row. See `docs/sabor_polling_station_fix.md` for full root-cause analysis. **District 12 turnout is skipped on import** — d12 CSVs report minority-only voter counts (subset of station total), so real turnout comes from districts 1-10. The `--wipe-district 12` path likewise preserves existing TurnoutData rows.
- **eu_parliament.py** — windows-1250 CSV; per-year layout in `YEAR_CONFIG` (file path, geo-column count, candidates-per-list, named column offsets). `EUParliamentImporter(year=YYYY)` selects the right config. 2024/2019 share one shape (13 geo cols, 12 candidates/list, in `{year}/CSV/rezultati_eupa.csv`); 2014 has 19 geo cols (extra Rbr GČ / MO / IJ between muni and station — skipped), 11 candidates/list (Croatia had 11 EP seats), and lives at `2014/rezultati_eupa_interno_rezultati_eupa.csv` (no CSV subdir). Adding a new year = add a `YEAR_CONFIG` entry. Candidate names pass through `clean_candidate_name` so academic titles ("mr.sc. ", ", dipl.iur.", "struč.spec.oec.", …) — heavily used in older CSVs — don't end up in the stored Person name and split cross-year matching. The "blue-dot" MEP badge (`ElectedMandate`) is seeded **per saziv** via `set_eu_mandates --year YYYY`; rosters live in `MEPS_BY_YEAR` (currently 2024 + 2019 + 2014). Each year is authoritative for its own term — re-running the command for one year touches only that year's mandate rows. The badge tooltip shows `saziv {year}.` dynamically from the result's `r.year`.
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
- Bulk insert with `ignore_conflicts=True` for performance
- Geography and person caches in BaseImporter avoid repeated DB lookups
- District 12 minorities use sub-districts 121-126 in DB, merged to single "NACIONALNE MANJINE" group in API responses
- Raw API includes `group` field per list for client-side coalition grouping

### Data Files (not in git)
Located in `files/` directory:
- `Rezultati_predsjednicki_izbori_2024/` — 2 CSV files
- `Rezultati_eu_parlamet_2024/{2024,2019}/CSV/` + `2014/` — 2 CSV files per year (2014 lives directly under `2014/` with filename `rezultati_eupa_interno_rezultati_eupa.csv`; parent folder kept its original 2024-only name)
- `rezultati_sabor_2024/CSV/` — 51 CSV files (11 districts × 3 file types + 6 district 12 files × 3)
- `Rezultati_lokalni_izbori_2025/` — 697 Excel files across krug-1 and krug-2

## Workflow Rules

- **Commit frequently**: After completing any meaningful unit of work, commit changes to git with a clear, descriptive commit message.
- **Push to GitHub**: Always push commits to the remote GitHub repository so work is never lost.
- **Clean commit messages**: Use concise commit messages that explain *what* changed and *why*. Follow conventional style (e.g., "Add election data parser", "Fix vote counting logic").
- **Update CLAUDE.md**: When key decisions are made (architecture choices, tech stack, design patterns, major features), update this file so future sessions have full context.
