import pytest

from app.services.amortization import generate_french_schedule


def test_french_schedule_effective_tea_monthly():
    principal = 100000
    rate = 0.12
    n_periods = 12

    schedule = generate_french_schedule(
        principal=principal,
        rate=rate,
        rate_type="TEA",
        n_periods=n_periods,
        payment_period="monthly",
    )

    expected_rate = (1 + rate) ** (1 / 12) - 1

    assert len(schedule) == n_periods
    assert schedule[-1]["saldo_final"] == 0.0
    assert schedule[0]["interes"] == pytest.approx(principal * expected_rate, abs=0.01)
    assert schedule[0]["cuota"] == schedule[1]["cuota"]
    assert sum(row["amortizacion"] for row in schedule) == pytest.approx(principal, abs=0.02)
    assert len({row["cuota"] for row in schedule[:-1]}) == 1


def test_french_schedule_nominal_monthly_daily_cap():
    principal = 50000
    nominal_rate = 0.03
    n_periods = 6

    schedule = generate_french_schedule(
        principal=principal,
        rate=nominal_rate,
        rate_type="NOMINAL",
        n_periods=n_periods,
        payment_period="monthly",
        capitalization="daily",
        rate_period="monthly",
    )

    expected_rate = (1 + nominal_rate / 30) ** 30 - 1

    assert len(schedule) == n_periods
    assert schedule[-1]["saldo_final"] == 0.0
    assert schedule[0]["interes"] == pytest.approx(principal * expected_rate, abs=0.01)


def test_french_schedule_nominal_requires_rate_period():
    with pytest.raises(ValueError):
        generate_french_schedule(
            principal=1000,
            rate=0.12,
            rate_type="NOMINAL",
            n_periods=12,
            payment_period="monthly",
            capitalization="daily",
        )
