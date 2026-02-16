from decimal import Decimal, ROUND_HALF_UP


_PERIODS_PER_YEAR = {
    "daily": 360,
    "monthly": 12,
    "bimonthly": 6,
    "quarterly": 4,
    "semiannual": 2,
    "annual": 1,
}


def _round2(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _periods_per_year(period):
    try:
        return _PERIODS_PER_YEAR[period]
    except KeyError as exc:
        raise ValueError(f"Unsupported period: {period}") from exc


def _effective_rate_per_period(
    rate,
    rate_type,
    payment_period,
    capitalization=None,
    rate_period=None,
):
    rate_type_normalized = rate_type.strip().lower()
    payment_periods = _periods_per_year(payment_period)
    rate_periods = _periods_per_year(rate_period) if rate_period else None

    if rate_type_normalized in {"tea", "effective_annual", "ea"}:
        return (1 + rate) ** (1 / payment_periods) - 1

    if rate_type_normalized in {"tem", "effective_monthly"}:
        rate_periods = _periods_per_year("monthly")
        annual_effective = (1 + rate) ** rate_periods - 1
        return (1 + annual_effective) ** (1 / payment_periods) - 1

    if rate_type_normalized in {"effective", "effective_period"}:
        rate_period = rate_period or payment_period
        rate_periods = _periods_per_year(rate_period)
        if rate_period == payment_period:
            return rate
        annual_effective = (1 + rate) ** rate_periods - 1
        return (1 + annual_effective) ** (1 / payment_periods) - 1

    if rate_type_normalized in {"nominal", "nominal_rate"}:
        if not rate_period:
            raise ValueError("rate_period is required for nominal rates (e.g., 'monthly' or 'annual')")
        if not capitalization:
            raise ValueError("capitalization is required for nominal rates")
        rate_periods = _periods_per_year(rate_period)
        cap_periods = _periods_per_year(capitalization)
        m = cap_periods / rate_periods
        effective_rate_for_rate_period = (1 + rate / m) ** m - 1
        if rate_period == payment_period:
            return effective_rate_for_rate_period
        annual_effective = (1 + effective_rate_for_rate_period) ** rate_periods - 1
        return (1 + annual_effective) ** (1 / payment_periods) - 1

    raise ValueError(f"Unsupported rate_type: {rate_type}")


def generate_french_schedule(
    principal,
    rate,
    rate_type,
    n_periods,
    payment_period="monthly",
    capitalization=None,
    rate_period=None,
):
    """
    Metodo Frances (vencido ordinario): cuota constante, intereses al final del periodo.
    Usa redondeo a 2 decimales, ajustando la ultima cuota para saldo final 0.00.
    """
    if principal <= 0:
        raise ValueError("principal must be > 0")
    if n_periods <= 0:
        raise ValueError("n_periods must be > 0")

    period_rate = _effective_rate_per_period(
        rate=rate,
        rate_type=rate_type,
        payment_period=payment_period,
        capitalization=capitalization,
        rate_period=rate_period,
    )

    if period_rate == 0:
        cuota_base = principal / n_periods
    else:
        factor = (1 + period_rate) ** n_periods
        cuota_base = principal * (period_rate * factor) / (factor - 1)

    saldo = principal
    cronograma = []

    for periodo in range(1, n_periods + 1):
        saldo_inicial = saldo
        interes = saldo_inicial * period_rate

        if periodo == n_periods:
            amortizacion = saldo_inicial
            cuota = interes + amortizacion
            saldo_final = 0.0
        else:
            cuota = cuota_base
            amortizacion = cuota - interes
            saldo_final = saldo_inicial - amortizacion

        saldo_final_redondeado = _round2(saldo_final)
        if abs(saldo_final_redondeado) < 0.005:
            saldo_final_redondeado = 0.0

        cronograma.append(
            {
                "periodo": periodo,
                "saldo_inicial": _round2(saldo_inicial),
                "cuota": _round2(cuota),
                "interes": _round2(interes),
                "amortizacion": _round2(amortizacion),
                "saldo_final": 0.0 if periodo == n_periods else saldo_final_redondeado,
            }
        )

        saldo = saldo_final

    return cronograma
