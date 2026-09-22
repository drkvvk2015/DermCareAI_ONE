from __future__ import annotations

def _require_range(value: float, low: float, high: float, name: str) -> float:
    numeric = float(value)
    if numeric < low or numeric > high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return numeric

def pasi_component(erythema: float, induration: float, desquamation: float, area: float) -> float:
    e = _require_range(erythema,0,4,"erythema")
    i = _require_range(induration,0,4,"induration")
    d = _require_range(desquamation,0,4,"desquamation")
    a = _require_range(area,0,6,"area")
    return round((e+i+d)*a,4)

def vasi_component(depigmented_area_percent: float) -> float:
    return round(_require_range(depigmented_area_percent,0,100,"depigmented_area_percent"),4)

def salt_component(hair_loss_percent: float) -> float:
    return round(_require_range(hair_loss_percent,0,100,"hair_loss_percent"),4)

def scorable_percentage(numerator: float, denominator: float) -> float:
    denominator = float(denominator)
    numerator = float(numerator)
    if denominator <= 0:
        raise ValueError("denominator must be greater than zero")
    if numerator < 0 or numerator > denominator:
        raise ValueError("numerator must be within denominator range")
    return round((numerator/denominator)*100.0,4)
