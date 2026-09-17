"""Normalizer agent: turns whatever a page printed into (minor units, ISO currency).

Storefronts print money in a dozen ways. Everything downstream (history, alerts, the
dashboard) assumes `price_cents` is an int in the store's currency. This is the only place
that should know about currency symbols and locale formatting.
"""
from __future__ import annotations

import re
from typing import Optional

SYMBOLS = {
    "$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "kr": "SEK", "¥": "JPY", "CHF": "CHF",
}
CODES = {"USD", "EUR", "GBP", "INR", "SEK", "NOK", "DKK", "JPY", "CHF", "CAD", "AUD"}


def detect_currency(text: str, default: Optional[str] = None) -> Optional[str]:
    t = text.strip()
    for code in CODES:
        if re.search(rf"\b{code}\b", t):
            return code
    for sym, code in sorted(SYMBOLS.items(), key=lambda kv: -len(kv[0])):
        if sym in t:
            return code
    return default


def parse_money(text: str, default_currency: Optional[str] = None) -> tuple[Optional[int], Optional[str]]:
    """Parse a printed price like "$1,299.00" or "937,20 €" into minor units.

    Returns (None, currency) when no number is present.
    """
    if text is None:
        return None, default_currency
    currency = detect_currency(text, default_currency)
    digits = re.sub(r"[^\d,\.]", "", text).strip()
    if not digits or digits in {".", ","}:
        return None, currency

    # Handle European formatting first: 937,20 -> 937.20 ; 1.234,56 -> 1234.56.
    if "," in digits and "." not in digits:
        if digits.count(",") > 1:
            digits = digits.replace(",", "")
        else:
            left, right = digits.split(",", 1)
            if len(right) in (1, 2):
                digits = f"{left}.{right}"
            else:
                digits = digits.replace(",", "")
    elif "," in digits and "." in digits:
        if digits.rfind(",") > digits.rfind("."):
            digits = digits.replace(".", "").replace(",", ".")
        else:
            digits = digits.replace(",", "")
    elif "." in digits:
        parts = digits.split(".")
        if len(parts) > 1 and len(parts[-1]) in (1, 2):
            pass
        else:
            digits = "".join(parts)

    try:
        amount = float(digits)
    except ValueError:
        return None, currency
    return int(round(amount * 100)), currency


def unit_price(price_cents: Optional[int], pack_size: int) -> Optional[int]:
    if price_cents is None or pack_size <= 1:
        return None
    return int(round(price_cents / pack_size))
