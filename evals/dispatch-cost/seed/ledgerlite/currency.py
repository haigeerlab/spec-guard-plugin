"""Fixed-rate currency conversion on integer minor units.

Every amount is an int number of *minor units*: cents for USD/EUR/GBP, whole
yen for JPY. Rates are exact fractions of USD cents per minor unit, so no
floating point is involved.
"""

# code -> (symbol, decimals, usd_cents_numerator, usd_cents_denominator)
# value of ONE minor unit of the currency, expressed in USD cents.
CURRENCIES = {
    "USD": ("$", 2, 1, 1),
    "EUR": ("€", 2, 108, 100),
    "GBP": ("£", 2, 127, 100),
    "JPY": ("¥", 0, 67, 100),
}


def supported():
    """Sorted list of supported currency codes."""
    return sorted(CURRENCIES)


def _lookup(code):
    if not isinstance(code, str) or code not in CURRENCIES:
        raise ValueError("unknown currency code: %r" % (code,))
    return CURRENCIES[code]


def _div_round(numerator, denominator):
    """Integer division rounding half away from zero (denominator > 0)."""
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    if remainder * 2 >= denominator:
        quotient += 1
    return sign * quotient


def convert(cents, src, dst):
    """Convert ``cents`` minor units of ``src`` into minor units of ``dst``."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise TypeError("cents must be an int")
    _, _, s_num, s_den = _lookup(src)
    _, _, d_num, d_den = _lookup(dst)
    return _div_round(cents * s_num * d_den, s_den * d_num)


def decimals(code):
    """Number of decimal places the currency displays."""
    return _lookup(code)[1]
