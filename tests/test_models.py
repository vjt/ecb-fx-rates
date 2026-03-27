"""Tests for EcbDailyRates model."""

from datetime import date
from decimal import Decimal

from ecb_fx_rates import EcbDailyRates


class TestEcbDailyRates:
    def test_get_existing_currency(self) -> None:
        rates = EcbDailyRates(
            date=date(2025, 12, 31),
            rates={"USD": Decimal("1.0842"), "GBP": Decimal("0.8574")},
        )
        assert rates.get("USD") == Decimal("1.0842")

    def test_get_eur_always_returns_one(self) -> None:
        rates = EcbDailyRates(date=date(2025, 12, 31), rates={})
        assert rates.get("EUR") == Decimal("1")

    def test_get_missing_currency_returns_none(self) -> None:
        rates = EcbDailyRates(date=date(2025, 12, 31), rates={"USD": Decimal("1.08")})
        assert rates.get("JPY") is None

    def test_frozen(self) -> None:
        rates = EcbDailyRates(date=date(2025, 1, 1), rates={})
        try:
            rates.date = date(2025, 1, 2)  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass
