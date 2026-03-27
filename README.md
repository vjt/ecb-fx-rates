# ecb-fx-rates

Async Python client for [ECB daily reference exchange rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html).

Fetches and parses the ECB's XML feeds into typed Python objects. No caching, no storage — bring your own persistence layer.

## Installation

```bash
pip install -e path/to/ecb-fx-rates
```

Requires Python 3.12+ and `aiohttp`.

## Usage

```python
import aiohttp
from ecb_fx_rates import EcbRatesClient, EcbDailyRates

async def main():
    client = EcbRatesClient()

    async with aiohttp.ClientSession() as session:
        # Today's rates
        today: EcbDailyRates = await client.fetch_daily(session)
        print(today.date)              # date(2025, 12, 31)
        print(today.get("USD"))        # Decimal("1.0842")
        print(today.get("EUR"))        # Decimal("1") — always

        # All rates for a specific year
        year_2025 = await client.fetch_year(session, 2025)
        # ~250 EcbDailyRates, one per ECB business day

        # Last 90 calendar days (~60 business days)
        recent = await client.fetch_last_90_days(session)

        # Full history since 1999 (~6MB download)
        everything = await client.fetch_history(session)
```

## API

### `EcbRatesClient`

| Method | Returns | Feed used |
|--------|---------|-----------|
| `fetch_daily(session)` | `EcbDailyRates` | `eurofxref-daily.xml` (~5KB) |
| `fetch_last_90_days(session)` | `list[EcbDailyRates]` | `eurofxref-hist-90d.xml` (~50KB) |
| `fetch_history(session)` | `list[EcbDailyRates]` | `eurofxref-hist.xml` (~6MB) |
| `fetch_year(session, year)` | `list[EcbDailyRates]` | 90d or hist, filtered to year |

### `EcbDailyRates`

| Attribute | Type | Description |
|-----------|------|-------------|
| `date` | `date` | ECB publication date |
| `rates` | `dict[str, Decimal]` | Currency code → EUR/X rate |

| Method | Returns | Description |
|--------|---------|-------------|
| `get(currency)` | `Decimal \| None` | Rate for currency. EUR always returns `Decimal("1")`. |

Rate semantics: `1 EUR = rate units of currency`. To convert foreign currency to EUR: `eur = amount / rate`.

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -x -q
```

## License

MIT
