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
python manage.py import_eu_parliament
python manage.py import_sabor                         # all districts
python manage.py import_sabor --district 12 --wipe-district  # re-import single district
python manage.py import_local
python manage.py normalize_persons [--dry-run]
python manage.py normalize_municipalities [--dry-run]  # merge "GRAD X"/"OPĆINA X" dup munis

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
- **eu_parliament.py** — windows-1250 CSV, 13 cols/list (1 list + 12 candidates), multiline coalition names
- **local.py** — Excel .xlsx, 2-4 sheets per file, list-level results only (no per-candidate breakdown within lists)

### Flask Analytics App (`app.py`)
Single-page app with multiple modules, served at port 5001:
- **Politician search** — cross-election search by name
- **Polling station search** — by location (county → municipality → station)
- **Interactive Croatia map** — SVG map (`static/croatia_map.svg`) with county selection
- **National results** — aggregated results by election type and year
- **Multi-compare** — side-by-side comparison of candidates/lists
- **Lokalni izbori per-station / per-muni / per-županija results** (`/api/lokalni/station-results`): one endpoint, four kinds — `vijece`, `nacelnik` (muni-level, need `municipality_id` or `station_id`) and `zupan`, `zup_skupstina` (county-level, need `county_id`). Shared `scope_stations` subquery aggregates votes/turnout, returns per-station turnout breakdown for any non-single-station scope. See `docs/lokalni_county_level_kinds.md`.
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
- `Rezultati_eu_parlamet_2024/CSV/` — 2 CSV files
- `rezultati_sabor_2024/CSV/` — 51 CSV files (11 districts × 3 file types + 6 district 12 files × 3)
- `Rezultati_lokalni_izbori_2025/` — 697 Excel files across krug-1 and krug-2

## Workflow Rules

- **Commit frequently**: After completing any meaningful unit of work, commit changes to git with a clear, descriptive commit message.
- **Push to GitHub**: Always push commits to the remote GitHub repository so work is never lost.
- **Clean commit messages**: Use concise commit messages that explain *what* changed and *why*. Follow conventional style (e.g., "Add election data parser", "Fix vote counting logic").
- **Update CLAUDE.md**: When key decisions are made (architecture choices, tech stack, design patterns, major features), update this file so future sessions have full context.
