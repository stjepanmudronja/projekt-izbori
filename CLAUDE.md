# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Projekt Izbori" — a Croatian elections data platform. Imports results from 4 election types (presidential, sabor, EU parliament, local) into a unified PostgreSQL database. Enables cross-election politician search and analytics.

## Tech Stack

- **Backend**: Django 6.0 + PostgreSQL 16
- **Python**: 3.12 (via Homebrew), virtualenv at `./venv`
- **Data import**: Custom Django management commands with pandas/openpyxl
- **Database**: `projekt_izbori` (local PostgreSQL)

## Commands

```bash
source venv/bin/activate

# Run imports
python manage.py import_presidential
python manage.py import_eu_parliament
python manage.py import_sabor
python manage.py import_local
python manage.py normalize_persons [--dry-run]

# Django
python manage.py runserver
python manage.py makemigrations elections
python manage.py migrate
```

## Architecture

### Django App: `elections`

Models split into 4 modules under `elections/models/`:
- **geography.py** — County (22), Municipality (604), PollingStation (7544)
- **elections.py** — ElectionType, Election, ElectionRound, ElectoralDistrict
- **participants.py** — Person (normalized_name for cross-election search), Party, ElectoralList, Candidacy
- **results.py** — TurnoutData, ListResult, CandidateResult

### Import Pipeline: `elections/importers/`
- **base.py** — BaseImporter with geography/person caches and bulk result insertion (batch size 5000)
- **presidential.py** — UTF-8 BOM CSV, semicolon delimited, title row + header + data
- **sabor.py** — windows-1250 CSV, 15 cols/list (1 list + 14 candidates), district 12 is individual candidates only
- **eu_parliament.py** — windows-1250 CSV, 13 cols/list (1 list + 12 candidates), multiline coalition names
- **local.py** — Excel .xlsx, 2-4 sheets per file, list-level results only (no per-candidate breakdown within lists)

### Key Design Decisions
- All election types share the same ListResult/CandidateResult tables
- Even single candidates (presidential, mayors) get an ElectoralList for uniformity
- Person.normalized_name (diacritics stripped, uppercase) enables cross-election search
- Bulk insert with `ignore_conflicts=True` for performance
- Geography and person caches in BaseImporter avoid repeated DB lookups

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
