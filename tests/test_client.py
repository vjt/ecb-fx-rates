"""Tests for EcbRatesClient — XML parsing, fetch logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from ecb_fx_rates import EcbDailyRates, EcbRatesClient

# -- Sample XML responses -----------------------------------------------

ECB_DAILY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <Cube>
    <Cube time="2025-12-31">
      <Cube currency="USD" rate="1.0842"/>
      <Cube currency="GBP" rate="0.8574"/>
      <Cube currency="JPY" rate="161.42"/>
      <Cube currency="CHF" rate="0.9612"/>
    </Cube>
  </Cube>
</gesmes:Envelope>"""

ECB_MULTI_DAY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2025-12-31">
      <Cube currency="USD" rate="1.0842"/>
      <Cube currency="GBP" rate="0.8574"/>
    </Cube>
    <Cube time="2025-12-30">
      <Cube currency="USD" rate="1.0800"/>
      <Cube currency="GBP" rate="0.8550"/>
    </Cube>
    <Cube time="2025-12-29">
      <Cube currency="USD" rate="1.0790"/>
      <Cube currency="GBP" rate="0.8540"/>
    </Cube>
    <Cube time="2024-12-31">
      <Cube currency="USD" rate="1.0350"/>
    </Cube>
  </Cube>
</gesmes:Envelope>"""

ECB_EMPTY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
  </Cube>
</gesmes:Envelope>"""

ECB_BAD_RATE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2025-12-31">
      <Cube currency="USD" rate="not_a_number"/>
      <Cube currency="GBP" rate="0.8574"/>
    </Cube>
  </Cube>
</gesmes:Envelope>"""


# -- Mock helpers --------------------------------------------------------

def _mock_response(text: str) -> MagicMock:
    resp = AsyncMock()
    resp.raise_for_status = MagicMock()
    resp.text = AsyncMock(return_value=text)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _mock_session(text: str) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=_mock_response(text))
    return session


# -- Tests ---------------------------------------------------------------


class TestFetchDaily:
    async def test_parses_single_day(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_daily(_mock_session(ECB_DAILY_XML))

        assert result.date == date(2025, 12, 31)
        assert result.get("USD") == Decimal("1.0842")
        assert result.get("GBP") == Decimal("0.8574")
        assert result.get("JPY") == Decimal("161.42")
        assert result.get("CHF") == Decimal("0.9612")
        assert len(result.rates) == 4

    async def test_empty_feed_raises(self) -> None:
        client = EcbRatesClient()
        with pytest.raises(RuntimeError, match="no rates"):
            await client.fetch_daily(_mock_session(ECB_EMPTY_XML))


class TestFetchLast90Days:
    async def test_returns_sorted_ascending(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_last_90_days(_mock_session(ECB_MULTI_DAY_XML))

        assert len(result) == 4
        assert result[0].date == date(2024, 12, 31)
        assert result[1].date == date(2025, 12, 29)
        assert result[-1].date == date(2025, 12, 31)

    async def test_each_day_has_rates(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_last_90_days(_mock_session(ECB_MULTI_DAY_XML))

        for day in result:
            assert len(day.rates) > 0
            assert isinstance(day.date, date)


class TestFetchYear:
    async def test_filters_to_requested_year(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_year(_mock_session(ECB_MULTI_DAY_XML), 2025)

        assert len(result) == 3
        assert all(d.date.year == 2025 for d in result)

    async def test_different_year(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_year(_mock_session(ECB_MULTI_DAY_XML), 2024)

        assert len(result) == 1
        assert result[0].date == date(2024, 12, 31)

    async def test_year_with_no_data(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_year(_mock_session(ECB_MULTI_DAY_XML), 2023)

        assert result == []


class TestParsing:
    async def test_skips_invalid_rates(self) -> None:
        client = EcbRatesClient()
        result = await client.fetch_daily(_mock_session(ECB_BAD_RATE_XML))

        # USD had invalid rate, should be skipped
        assert result.get("USD") is None
        # GBP was valid
        assert result.get("GBP") == Decimal("0.8574")

    async def test_network_error_raises(self) -> None:
        session = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("network down"))
        ctx.__aexit__ = AsyncMock(return_value=False)
        session.get = MagicMock(return_value=ctx)

        client = EcbRatesClient()
        with pytest.raises(RuntimeError, match="ECB feed unavailable"):
            await client.fetch_daily(session)
