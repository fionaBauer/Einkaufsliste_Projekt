from decimal import Decimal

# Units that can't be meaningfully converted to g/ml
DISCRETE_UNITS = {"pcs", "pkg", ""}

# 1 EL = 10ml/10g, 1 TL = 5ml/5g
SPOON_TO_ML = {"el": Decimal("10"), "tl": Decimal("5")}
SPOON_TO_G = {"el": Decimal("10"), "tl": Decimal("5")}


def to_base_unit(quantity, unit):
    """Konvertiert alles in Basis-Einheiten (g, ml, pcs, pkg)."""
    if unit == "kg":
        return quantity * Decimal("1000"), "g"
    if unit == "l":
        return quantity * Decimal("1000"), "ml"
    # el/tl bleiben als el/tl — Konvertierung passiert beim Zusammenführen
    return quantity, unit


def from_base_unit(quantity, unit):
    """Konvertiert zurück in schönere Einheit."""
    if unit == "g" and quantity >= 1000:
        return quantity / Decimal("1000"), "kg"
    if unit == "ml" and quantity >= 1000:
        return quantity / Decimal("1000"), "l"
    return quantity, unit


def merge_units(qty_a, unit_a, qty_b, unit_b):
    """
    Führt zwei Mengen mit möglicherweise unterschiedlichen Einheiten zusammen.
    Regeln:
    - Gleiche Einheit → einfach addieren
    - el/tl + g/ml → el/tl in g/ml umrechnen (1el=10g/ml, 1tl=5g/ml)
    - el/tl + pcs/pkg → el/tl unverändert lassen, pcs/pkg unverändert (getrennt speichern)
    - Inkompatible Einheiten → erste Einheit gewinnt, nichts addieren
    """
    if unit_a == unit_b:
        return qty_a + qty_b, unit_a

    # Spoon → weight/volume conversion
    spoon_units = {"el", "tl"}
    weight_units = {"g", "kg"}
    volume_units = {"ml", "l"}
    measurable = weight_units | volume_units

    # Normalize to base first
    base_a, base_unit_a = to_base_unit(qty_a, unit_a)
    base_b, base_unit_b = to_base_unit(qty_b, unit_b)

    # Both are already base units and match
    if base_unit_a == base_unit_b:
        total, unit = from_base_unit(base_a + base_b, base_unit_a)
        return total, unit

    # One is spoon, other is measurable
    if unit_a in spoon_units and base_unit_b in measurable:
        if base_unit_b in {"g"} | weight_units:
            converted = base_a * SPOON_TO_G[unit_a]
        else:
            converted = base_a * SPOON_TO_ML[unit_a]
        total, unit = from_base_unit(converted + base_b, base_unit_b)
        return total, unit

    if unit_b in spoon_units and base_unit_a in measurable:
        if base_unit_a in {"g"} | weight_units:
            converted = base_b * SPOON_TO_G[unit_b]
        else:
            converted = base_b * SPOON_TO_ML[unit_b]
        total, unit = from_base_unit(base_a + converted, base_unit_a)
        return total, unit

    # One or both are discrete (pcs, pkg) — can't merge, return first unchanged
    return qty_a, unit_a