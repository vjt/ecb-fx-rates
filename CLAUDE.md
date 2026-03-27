# ecb-fx-rates

Async client for ECB daily reference exchange rates. Extracted from
[ibtax](https://github.com/vjt/ibtax) Italian tax report generator.

## What This Does

Fetches and parses ECB's eurofxref XML feeds into typed `EcbDailyRates`
objects. Consumers bring their own caching/storage — this library is
pure fetch + parse + return.

## Architecture

```
EcbRatesClient
  ├─ fetch_daily()        → eurofxref-daily.xml     → EcbDailyRates
  ├─ fetch_last_90_days() → eurofxref-hist-90d.xml  → [EcbDailyRates]
  ├─ fetch_history()      → eurofxref-hist.xml      → [EcbDailyRates]
  └─ fetch_year(year)     → 90d or hist, filtered   → [EcbDailyRates]
```

Three files, one concern each:
- `client.py` — HTTP fetch and XML parsing
- `models.py` — `EcbDailyRates` frozen dataclass
- `__init__.py` — public API exports

## Tech Stack

- **Python 3.12+**, async (`aiohttp`)
- **stdlib only** for XML parsing and Decimal
- No Pydantic, no caching layer, no database

## Engineering Standards

- **Zero ibtax dependencies.** Standalone library.
- **Minimal surface area.** Public API: `EcbRatesClient`, `EcbDailyRates`.
- **aiohttp is the only runtime dependency.** Keep it that way.
- Type annotations on all signatures.
- Tests use mocked HTTP responses, never hit the real ECB.

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -x -q
```
