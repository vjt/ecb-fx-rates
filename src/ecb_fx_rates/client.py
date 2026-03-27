"""Async client for ECB daily reference exchange rates.

Fetches EUR/X rates from the ECB's public XML feeds:
- Daily: today's rates only
- Last 90 days: ~60 business days of rates
- Full history: every business day since 1999 (~6MB XML)

All feeds are freely available without authentication.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import aiohttp

from ecb_fx_rates.models import EcbDailyRates

logger = logging.getLogger(__name__)

_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
_HIST_90D_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
_HIST_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"

_ECB_NS = {"ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class EcbRatesClient:
    """Async client for ECB reference exchange rates.

    Fetches and parses ECB XML feeds into EcbDailyRates objects.
    Does not cache — consumers handle storage.

    Usage::

        async with aiohttp.ClientSession() as session:
            client = EcbRatesClient()
            rates = await client.fetch_daily(session)
            usd_rate = rates.get("USD")  # Decimal("1.0842")
    """

    async def fetch_daily(self, session: aiohttp.ClientSession) -> EcbDailyRates:
        """Fetch today's ECB reference rates (single day).

        Returns one EcbDailyRates for the latest publication date.
        Raises RuntimeError if the feed is unavailable or unparseable.
        """
        all_days = await self._fetch_and_parse(session, _DAILY_URL)
        if not all_days:
            raise RuntimeError("ECB daily feed returned no rates")
        return all_days[0]

    async def fetch_last_90_days(
        self, session: aiohttp.ClientSession,
    ) -> list[EcbDailyRates]:
        """Fetch the last ~90 calendar days of ECB rates.

        Returns a list sorted by date ascending. Typically ~60 business
        days (ECB publishes on TARGET2 business days only).
        """
        return await self._fetch_and_parse(session, _HIST_90D_URL)

    async def fetch_history(
        self, session: aiohttp.ClientSession,
    ) -> list[EcbDailyRates]:
        """Fetch the complete ECB rate history since 1999.

        Warning: the XML is ~6MB. Use fetch_year() if you only need
        a specific year.
        """
        return await self._fetch_and_parse(session, _HIST_URL)

    async def fetch_year(
        self, session: aiohttp.ClientSession, year: int,
    ) -> list[EcbDailyRates]:
        """Fetch ECB rates for a specific calendar year.

        Uses the 90-day feed if the year is recent enough, otherwise
        falls back to the full history feed. Filters to only include
        dates within the requested year.

        Returns a list sorted by date ascending.
        """
        today = date.today()

        if year == today.year:
            # Current year: 90-day feed likely has enough coverage
            all_days = await self._fetch_and_parse(session, _HIST_90D_URL)
            year_days = [d for d in all_days if d.date.year == year]
            if len(year_days) >= 20:
                return year_days
            # Insufficient coverage, fall through to full history

        all_days = await self._fetch_and_parse(session, _HIST_URL)
        return [d for d in all_days if d.date.year == year]

    async def _fetch_and_parse(
        self, session: aiohttp.ClientSession, url: str,
    ) -> list[EcbDailyRates]:
        """Fetch an ECB XML feed and parse into EcbDailyRates."""
        try:
            async with session.get(url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except Exception as e:
            raise RuntimeError(f"ECB feed unavailable ({url}): {e}") from e

        return _parse_ecb_xml(text)


def _parse_ecb_xml(xml_text: str) -> list[EcbDailyRates]:
    """Parse ECB eurofxref XML into a sorted list of EcbDailyRates.

    The ECB XML structure is:
        <Cube>
          <Cube time="2025-12-31">
            <Cube currency="USD" rate="1.0842"/>
            <Cube currency="GBP" rate="0.8574"/>
            ...
          </Cube>
          ...
        </Cube>
    """
    root = ET.fromstring(xml_text)
    results: list[EcbDailyRates] = []

    for day_cube in root.findall(".//ecb:Cube[@time]", _ECB_NS):
        time_str = day_cube.get("time", "")
        try:
            day_date = datetime.strptime(time_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning("Skipping unparseable ECB date: %s", time_str)
            continue

        rates: dict[str, Decimal] = {}
        for rate_cube in day_cube.findall("ecb:Cube[@currency]", _ECB_NS):
            currency = rate_cube.get("currency", "")
            rate_str = rate_cube.get("rate", "")
            if currency and rate_str:
                try:
                    rates[currency] = Decimal(rate_str)
                except InvalidOperation:
                    logger.warning(
                        "Skipping invalid rate: %s=%s on %s",
                        currency, rate_str, time_str,
                    )

        if rates:
            results.append(EcbDailyRates(date=day_date, rates=rates))

    results.sort(key=lambda d: d.date)

    if results:
        logger.info(
            "Parsed %d ECB rate days (%s to %s)",
            len(results), results[0].date, results[-1].date,
        )

    return results
