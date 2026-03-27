"""Data types for ECB reference exchange rates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EcbDailyRates:
    """ECB reference rates for a single publication date.

    The ECB publishes one set of reference rates per business day,
    covering ~30 currencies against EUR.

    Attributes:
        date: The publication date (ECB business day).
        rates: Mapping of ISO 4217 currency code to EUR/X rate.
            Example: {"USD": Decimal("1.0842")} means 1 EUR = 1.0842 USD.
            To convert X to EUR: eur_amount = x_amount / rate.
    """

    date: date
    rates: dict[str, Decimal]

    def get(self, currency: str) -> Decimal | None:
        """Get the EUR/currency rate, or None if not published."""
        if currency == "EUR":
            return Decimal("1")
        return self.rates.get(currency)
