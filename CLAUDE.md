# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run development server** (http://localhost:5000, debug mode):
```bash
python app.py
```

**Run tests:**
```bash
pytest tests/
```

**Run a single test file:**
```bash
pytest tests/test_csv_parser.py
pytest tests/test_repricer.py
```

**Run a single test by name:**
```bash
pytest tests/test_repricer.py::test_function_name
```

**Production server:**
```bash
gunicorn app:app --bind 0.0.0.0:8000
```

## Architecture

EnergyMonitor is a Flask web app for Texas electricity users to import Smart Meter Texas usage CSVs, visualize consumption, and compare costs across Power to Choose electricity plans.

**App entry point:** `app.py` — defines `create_app()` factory and all Flask routes. Routes return either rendered Jinja2 templates or JSON for API endpoints.

**Database models** (`models.py`):
- `UsageRecord` — daily kWh consumption per ESIID (meter ID)
- `ElectricityPlan` — plan pricing tiers fetched from Power to Choose API

**Services layer** (`services/`):
- `csv_parser.py` — parses Smart Meter Texas exports (both daily and 15-minute interval formats), aggregates intervals to daily totals, upserts into DB
- `ptc_client.py` — fetches plans from Power to Choose API by ZIP code, persists with upsert logic
- `repricer.py` — aggregates daily usage into monthly totals and estimates cost under each plan

**Data flow:**
```
Smart Meter Texas CSV → csv_parser → UsageRecord (DB) → repricer → cost estimates
Power to Choose API   → ptc_client → ElectricityPlan (DB) → repricer → cost estimates
```

**Frontend:** Jinja2 templates in `templates/` with `base.html` as the layout parent. Chart.js 4 (CDN) renders charts via helpers in `static/js/charts.js`.

**Configuration** (`config.py`): reads `SECRET_KEY` and `DATABASE_URL` from environment (`.env` file via python-dotenv). Defaults to SQLite `energy.db`. See `.env.example`.

**Testing:** pytest with an in-memory SQLite `TestConfig`, a Flask test client fixture, and pre-seeded data (90 days of usage + 1 plan) defined in `tests/test_repricer.py`.
