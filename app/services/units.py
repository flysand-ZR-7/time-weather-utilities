"""Unit conversion service using Pint with temperature offset handling and digital storage support."""

from typing import Any, Dict, List
import pint

# Initialize Pint Unit Registry
ureg = pint.UnitRegistry()
# Enable autoconvert for offset units like Celsius and Fahrenheit
ureg.default_as_delta = False

# Common user aliases to canonical Pint unit strings
UNIT_ALIASES: Dict[str, str] = {
    # Temperature
    "c": "degC",
    "celsius": "degC",
    "centigrade": "degC",
    "f": "degF",
    "fahrenheit": "degF",
    "k": "kelvin",
    "kelvin": "kelvin",
    "r": "rankine",
    "rankine": "rankine",
    # Speed
    "kph": "kilometer / hour",
    "kmh": "kilometer / hour",
    "km/h": "kilometer / hour",
    "mph": "mile / hour",
    "mi/h": "mile / hour",
    "mps": "meter / second",
    "m/s": "meter / second",
    "knot": "knot",
    "knots": "knot",
    "kn": "knot",
    # Length
    "km": "kilometer",
    "kilometer": "kilometer",
    "m": "meter",
    "meter": "meter",
    "meters": "meter",
    "cm": "centimeter",
    "centimeter": "centimeter",
    "mm": "millimeter",
    "millimeter": "millimeter",
    "um": "micrometer",
    "micrometer": "micrometer",
    "mi": "mile",
    "mile": "mile",
    "miles": "mile",
    "yd": "yard",
    "yard": "yard",
    "ft": "foot",
    "foot": "foot",
    "feet": "foot",
    "in": "inch",
    "inch": "inch",
    "inches": "inch",
    "nmi": "nautical_mile",
    # Mass
    "kg": "kilogram",
    "kilogram": "kilogram",
    "kilograms": "kilogram",
    "g": "gram",
    "gram": "gram",
    "grams": "gram",
    "mg": "milligram",
    "milligram": "milligram",
    "lb": "pound",
    "lbs": "pound",
    "pound": "pound",
    "pounds": "pound",
    "oz": "ounce",
    "ounce": "ounce",
    "ounces": "ounce",
    "ton": "metric_ton",
    "tonne": "metric_ton",
    # Digital storage
    "b": "byte",
    "byte": "byte",
    "bytes": "byte",
    "bit": "bit",
    "bits": "bit",
    "kb": "kilobyte",
    "kib": "kibibyte",
    "mb": "megabyte",
    "mib": "mebibyte",
    "gb": "gigabyte",
    "gib": "gibibyte",
    "tb": "terabyte",
    "tib": "tebibyte",
    "pb": "petabyte",
    "pib": "pebibyte",
    # Area
    "sqm": "meter**2",
    "sqkm": "kilometer**2",
    "sqft": "foot**2",
    "sqin": "inch**2",
    "acre": "acre",
    "acres": "acre",
    "hectare": "hectare",
    "ha": "hectare",
    # Volume
    "l": "liter",
    "liter": "liter",
    "liters": "liter",
    "ml": "milliliter",
    "milliliter": "milliliter",
    "gal": "gallon",
    "gallon": "gallon",
    "gallons": "gallon",
    "qt": "quart",
    "pt": "pint",
    "cup": "cup",
    "fl_oz": "fluid_ounce",
    "floz": "fluid_ounce",
    # Pressure
    "pa": "pascal",
    "kpa": "kilopascal",
    "bar": "bar",
    "mbar": "millibar",
    "psi": "psi",
    "atm": "atmosphere",
    "torr": "torr",
    # Energy
    "j": "joule",
    "joule": "joule",
    "kj": "kilojoule",
    "cal": "calorie",
    "calorie": "calorie",
    "kcal": "kilocalorie",
    "wh": "watt_hour",
    "kwh": "kilowatt_hour",
    "btu": "btu",
}


def canonicalize_unit(unit_str: str) -> str:
    """Normalize user unit string to a canonical Pint unit expression."""
    clean = unit_str.strip().lower()
    return UNIT_ALIASES.get(clean, unit_str.strip())


def convert_measurement(value: float, from_unit_input: str, to_unit_input: str) -> Dict[str, Any]:
    """Convert a numeric value between measurement units using Pint.
    
    Raises:
        ValueError if units are incompatible or unrecognized.
    """
    from_canon = canonicalize_unit(from_unit_input)
    to_canon = canonicalize_unit(to_unit_input)

    try:
        quantity = ureg.Quantity(value, from_canon)
    except Exception as exc:
        raise ValueError(f"Unrecognized source unit: '{from_unit_input}'") from exc

    try:
        converted = quantity.to(to_canon)
    except pint.DimensionalityError as dim_err:
        raise ValueError(
            f"Cannot convert between incompatible dimensions: from '{from_unit_input}' to '{to_unit_input}'."
        ) from dim_err
    except Exception as exc:
        raise ValueError(f"Unrecognized target unit: '{to_unit_input}'") from exc

    raw_val = float(converted.magnitude)
    # Clean rounding for presentation
    if abs(raw_val) >= 1e-4 and abs(raw_val) < 1e10:
        rounded_val = round(raw_val, 6)
    else:
        rounded_val = raw_val

    # Generate formula / explanation
    explanation = f"{value} {from_unit_input} = {rounded_val} {to_unit_input}"
    if "deg" in from_canon or "deg" in to_canon or from_canon == "kelvin" or to_canon == "kelvin":
        if "c" in from_unit_input.lower() and "f" in to_unit_input.lower():
            explanation += " (T(°F) = T(°C) × 9/5 + 32)"
        elif "f" in from_unit_input.lower() and "c" in to_unit_input.lower():
            explanation += " (T(°C) = (T(°F) - 32) × 5/9)"
        elif "c" in from_unit_input.lower() and "k" in to_unit_input.lower():
            explanation += " (T(K) = T(°C) + 273.15)"

    return {
        "from_value": value,
        "from_unit": from_unit_input,
        "to_value": rounded_val,
        "to_unit": to_unit_input,
        "canonical_from": str(quantity.units),
        "canonical_to": str(converted.units),
        "explanation": explanation,
    }


def get_supported_categories() -> Dict[str, Any]:
    """Return dictionary of supported measurement categories with common units and examples."""
    return {
        "temperature": {
            "description": "Temperature scales including offset conversions",
            "units": ["celsius (°C, c)", "fahrenheit (°F, f)", "kelvin (K, k)", "rankine (R)"],
            "example": "100 c to f",
        },
        "length": {
            "description": "Metric and imperial distance and dimensions",
            "units": ["meter (m)", "kilometer (km)", "centimeter (cm)", "millimeter (mm)", "mile (mi)", "yard (yd)", "foot (ft)", "inch (in)", "nautical_mile (nmi)"],
            "example": "10 miles to km",
        },
        "mass": {
            "description": "Weight and mass measurements",
            "units": ["kilogram (kg)", "gram (g)", "milligram (mg)", "pound (lb, lbs)", "ounce (oz)", "metric_ton (tonne)"],
            "example": "150 lbs to kg",
        },
        "speed": {
            "description": "Velocity and wind speeds",
            "units": ["km/h (kph)", "mph", "m/s", "knot (kn)"],
            "example": "60 mph to km/h",
        },
        "digital_storage": {
            "description": "Decimal and binary byte measurements",
            "units": ["byte (B)", "kilobyte (KB)", "kibibyte (KiB)", "megabyte (MB)", "mebibyte (MiB)", "gigabyte (GB)", "gibibyte (GiB)", "terabyte (TB)", "tebibyte (TiB)"],
            "example": "1 GB to MiB",
        },
        "volume": {
            "description": "Liquid and dry volume capacities",
            "units": ["liter (L)", "milliliter (mL)", "gallon (gal)", "quart (qt)", "pint (pt)", "cup", "fluid_ounce (fl_oz)"],
            "example": "1 gallon to liters",
        },
        "area": {
            "description": "Surface area calculations",
            "units": ["sqm (m²)", "sqkm (km²)", "sqft (ft²)", "sqin (in²)", "acre", "hectare (ha)"],
            "example": "1 acre to sqm",
        },
        "pressure": {
            "description": "Atmospheric, fluid, and mechanical pressure",
            "units": ["pascal (Pa)", "kilopascal (kPa)", "bar", "millibar (mbar)", "psi", "atmosphere (atm)", "torr"],
            "example": "32 psi to bar",
        },
        "energy": {
            "description": "Work, heat, and electrical energy",
            "units": ["joule (J)", "kilojoule (kJ)", "calorie (cal)", "kilocalorie (kcal)", "watt_hour (Wh)", "kilowatt_hour (kWh)", "btu"],
            "example": "500 kcal to kJ",
        },
    }
