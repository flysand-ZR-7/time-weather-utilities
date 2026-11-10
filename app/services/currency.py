"""Currency exchange and time-series trend analysis via Frankfurter API."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from app.cache import currency_list_cache, currency_rates_cache
from app.config import settings
from app.upstream import request_upstream


async def get_supported_currencies() -> Dict[str, str]:
    """Retrieve all supported currency codes and full names from Frankfurter with 24-hour cache."""
    cache_key = "currencies_list"
    if cache_key in currency_list_cache:
        return currency_list_cache[cache_key]

    url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/currencies"
    resp = await request_upstream("GET", url, is_open_meteo=False)
    data = resp.json()

    currency_list_cache[cache_key] = data
    return data


async def convert_currency(
    amount: float,
    from_currency: str,
    to_currencies: List[str],
    historical_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert an amount from a base currency to one or more target currencies (up to 10)."""
    base = from_currency.strip().upper()
    targets = [t.strip().upper() for t in to_currencies if t.strip()]

    if not base:
        raise ValueError("from_currency cannot be empty.")
    if not targets:
        raise ValueError("At least one target currency must be specified in to_currencies.")
    if len(targets) > 10:
        raise ValueError("Maximum 10 target currencies permitted per conversion request.")
    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    # Validate target currencies against supported list
    supported = await get_supported_currencies()
    if base not in supported:
        raise ValueError(f"Base currency '{base}' is not supported by ECB reference rates.")

    invalid_targets = [t for t in targets if t not in supported]
    if invalid_targets:
        raise ValueError(f"Unsupported target currency code(s): {', '.join(invalid_targets)}.")

    date_str = historical_date.strip() if historical_date else "latest"
    if date_str != "latest":
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"Invalid date format '{historical_date}'. Expected 'YYYY-MM-DD'.") from exc

    targets_sorted = sorted(list(set(targets)))
    symbols_param = ",".join(targets_sorted)

    cache_key = f"{base}:{symbols_param}:{date_str}"
    if cache_key in currency_rates_cache:
        raw_rates = currency_rates_cache[cache_key]["rates"]
        effective_date = currency_rates_cache[cache_key]["date"]
    else:
        # If target equals base only, no need to query external API
        if targets_sorted == [base]:
            raw_rates = {base: 1.0}
            effective_date = date_str if date_str != "latest" else str(date.today())
        else:
            # Query Frankfurter
            # Filter out base from symbols if querying Frankfurter (Frankfurter requires symbols != base)
            external_symbols = [t for t in targets_sorted if t != base]
            url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/{date_str}"
            params = {
                "base": base,
                "symbols": ",".join(external_symbols),
            }
            resp = await request_upstream("GET", url, is_open_meteo=False, params=params)
            data = resp.json()
            raw_rates = data.get("rates", {})
            if base in targets_sorted:
                raw_rates[base] = 1.0
            effective_date = data.get("date", date_str)

            currency_rates_cache[cache_key] = {
                "rates": raw_rates,
                "date": effective_date,
            }

    conversions: Dict[str, Dict[str, Any]] = {}
    for sym in targets:
        rate = raw_rates.get(sym)
        if rate is not None:
            converted_amount = round(amount * rate, 4)
            conversions[sym] = {
                "rate": rate,
                "converted_amount": converted_amount,
                "currency_name": supported.get(sym, sym),
            }

    return {
        "amount": amount,
        "base_currency": base,
        "base_currency_name": supported.get(base, base),
        "date": effective_date,
        "rates": {k: v["rate"] for k, v in conversions.items()},
        "conversions": conversions,
    }


async def get_currency_trend(
    from_currency: str,
    to_currency: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Calculate historical exchange rate trend and statistics for a currency pair (7 or 30 days)."""
    base = from_currency.strip().upper()
    target = to_currency.strip().upper()

    if days not in (7, 30):
        raise ValueError("Trend period must be either 7 or 30 days.")

    supported = await get_supported_currencies()
    if base not in supported:
        raise ValueError(f"Base currency '{base}' is not supported.")
    if target not in supported:
        raise ValueError(f"Target currency '{target}' is not supported.")

    if base == target:
        return {
            "from_currency": base,
            "to_currency": target,
            "days": days,
            "min_rate": 1.0,
            "max_rate": 1.0,
            "average_rate": 1.0,
            "change_percent": 0.0,
            "trend_direction": "flat",
            "rates_count": days,
            "daily_rates": {str(date.today() - timedelta(d)): 1.0 for d in range(days)},
        }

    end_d = date.today()
    start_d = end_d - timedelta(days=days)
    date_range_str = f"{start_d.strftime('%Y-%m-%d')}..{end_d.strftime('%Y-%m-%d')}"

    cache_key = f"trend:{base}:{target}:{date_range_str}"
    if cache_key in currency_rates_cache:
        return currency_rates_cache[cache_key]

    url = f"{settings.FRANKFURTER_BASE_URL.rstrip('/')}/{date_range_str}"
    params = {
        "base": base,
        "symbols": target,
    }
    resp = await request_upstream("GET", url, is_open_meteo=False, params=params)
    data = resp.json()

    raw_rates_by_date = data.get("rates", {})
    daily_rates: Dict[str, float] = {}
    for d_key in sorted(raw_rates_by_date.keys()):
        val = raw_rates_by_date[d_key].get(target)
        if val is not None:
            daily_rates[d_key] = float(val)

    if not daily_rates:
        raise ValueError(f"No exchange rate data returned for pair {base}/{target} over the last {days} days.")

    rate_values = list(daily_rates.values())
    min_r = min(rate_values)
    max_r = max(rate_values)
    avg_r = sum(rate_values) / len(rate_values)

    first_rate = rate_values[0]
    last_rate = rate_values[-1]
    pct_change = ((last_rate - first_rate) / first_rate) * 100.0

    if pct_change > 0.05:
        direction = "up"
    elif pct_change < -0.05:
        direction = "down"
    else:
        direction = "flat"

    trend_result = {
        "from_currency": base,
        "to_currency": target,
        "days": days,
        "start_date": list(daily_rates.keys())[0],
        "end_date": list(daily_rates.keys())[-1],
        "min_rate": round(min_r, 4),
        "max_rate": round(max_r, 4),
        "average_rate": round(avg_r, 4),
        "first_rate": round(first_rate, 4),
        "latest_rate": round(last_rate, 4),
        "change_percent": round(pct_change, 3),
        "trend_direction": direction,
        "rates_count": len(daily_rates),
        "daily_rates": daily_rates,
    }

    currency_rates_cache[cache_key] = trend_result
    return trend_result
