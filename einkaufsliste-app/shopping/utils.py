from decimal import Decimal


def to_base_unit(quantity, unit):
    """Konvertiert alles in Basis-Einheiten (g, ml, pcs)"""
    if unit == "kg":
        return quantity * Decimal("1000"), "g"
    if unit == "l":
        return quantity * Decimal("1000"), "ml"

    return quantity, unit


def from_base_unit(quantity, unit):
    """Konvertiert zurück in schönere Einheit"""
    if unit == "g" and quantity >= 1000:
        return quantity / Decimal("1000"), "kg"
    if unit == "ml" and quantity >= 1000:
        return quantity / Decimal("1000"), "l"

    return quantity, unit