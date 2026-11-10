"""Weather, forecast, air quality, astronomy, and lifestyle advice services."""

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from app.cache import (
    air_quality_cache,
    forecast_cache,
    round_coord,
    weather_cache,
)
from app.config import settings
from app.services.geocode import resolve_location
from app.services.wmo import degrees_to_compass, get_weather_description
from app.upstream import request_upstream

ATTRIBUTION_STATEMENT = (
    "Weather data by Open-Meteo.com (non-commercial free tier). "
    "For commercial use, a paid license is required."
)


def calculate_moon_phase(target_date: date) -> Dict[str, Any]:
    """Calculate the lunar phase and illumination percentage for a given calendar date."""
    # Reference epoch: New Moon on 2000-01-06
    epoch = date(2000, 1, 6)
    days_diff = (target_date - epoch).days
    synodic_month = 29.53058867
    cycle_pos = (days_diff % synodic_month) / synodic_month

    if cycle_pos < 0.03 or cycle_pos >= 0.97:
        phase_name = "New Moon"
    elif cycle_pos < 0.22:
        phase_name = "Waxing Crescent"
    elif cycle_pos < 0.28:
        phase_name = "First Quarter"
    elif cycle_pos < 0.47:
        phase_name = "Waxing Gibbous"
    elif cycle_pos < 0.53:
        phase_name = "Full Moon"
    elif cycle_pos < 0.72:
        phase_name = "Waning Gibbous"
    elif cycle_pos < 0.78:
        phase_name = "Last Quarter"
    else:
        phase_name = "Waning Crescent"

    # Illumination: 0% at New Moon, 100% at Full Moon
    illumination = round((1.0 - math.cos(cycle_pos * 2.0 * math.pi)) / 2.0 * 100.0, 1)

    return {
        "phase_name": phase_name,
        "phase_fraction": round(cycle_pos, 3),
        "illumination_percentage": illumination,
    }


def generate_forecast_summary(daily_data: Dict[str, Any], temp_unit: str) -> str:
    """Generate a readable plain-language weather overview from daily forecast metrics."""
    dates = daily_data.get("time", [])
    max_temps = daily_data.get("temperature_2m_max", [])
    min_temps = daily_data.get("temperature_2m_min", [])
    precip_sums = daily_data.get("precipitation_sum", [])
    weather_codes = daily_data.get("weather_code", [])

    if not dates or not max_temps:
        return "Weather forecast data currently unavailable."

    num_days = len(dates)
    unit_sym = "°F" if temp_unit.lower() == "fahrenheit" else "°C"

    highest_temp = max(max_temps)
    lowest_temp = min(min_temps)

    # Count rainy/snowy days
    rain_days = []
    for idx, (p, code) in enumerate(zip(precip_sums, weather_codes)):
        if (p is not None and p > 1.0) or code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 97, 99):
            d_obj = datetime.strptime(dates[idx], "%Y-%m-%d").date()
            rain_days.append(d_obj.strftime("%A"))

    summary_parts = [
        f"Forecast for the next {num_days} days: Daytime highs between {round(lowest_temp, 1)}{unit_sym} and {round(highest_temp, 1)}{unit_sym}."
    ]

    if rain_days:
        if len(rain_days) == 1:
            summary_parts.append(f"Precipitation expected on {rain_days[0]}.")
        elif len(rain_days) <= 3:
            summary_parts.append(f"Precipitation likely on {', '.join(rain_days)}.")
        else:
            summary_parts.append("Frequent rain or showers expected throughout the period.")
    else:
        summary_parts.append("Predominantly dry conditions expected with little to no rain.")

    dominant_code = weather_codes[0] if weather_codes else 0
    today_cond = get_weather_description(dominant_code)
    summary_parts.append(f"Primary pattern: {today_cond}.")

    return " ".join(summary_parts)


async def get_current_weather(
    location_query: str,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> Dict[str, Any]:
    """Retrieve current weather conditions for a resolved location with 10-minute caching."""
    loc = await resolve_location(location_query)
    lat_r = round_coord(loc["latitude"])
    lon_r = round_coord(loc["longitude"])

    cache_key = f"{lat_r}:{lon_r}:{temperature_unit}:{wind_speed_unit}:{precipitation_unit}"
    if cache_key in weather_cache:
        cached_result = dict(weather_cache[cache_key])
        cached_result["location"] = loc
        return cached_result

    # Request ONLY the variables needed for current weather
    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,rain,showers,snowfall,weather_code,cloud_cover,"
            "pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        ),
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": precipitation_unit,
    }

    resp = await request_upstream(
        method="GET",
        url=settings.OPEN_METEO_FORECAST_URL,
        is_open_meteo=True,
        params=params,
    )
    raw = resp.json()
    curr = raw.get("current", {})
    curr_units = raw.get("current_units", {})

    w_code = curr.get("weather_code", 0)
    w_desc = get_weather_description(w_code)
    wind_deg = curr.get("wind_direction_10m", 0.0)
    wind_comp = degrees_to_compass(wind_deg)

    result = {
        "location": loc,
        "current": {
            "time": curr.get("time"),
            "temperature": curr.get("temperature_2m"),
            "apparent_temperature": curr.get("apparent_temperature"),
            "relative_humidity": curr.get("relative_humidity_2m"),
            "is_day": bool(curr.get("is_day", 1)),
            "precipitation": curr.get("precipitation", 0.0),
            "rain": curr.get("rain", 0.0),
            "showers": curr.get("showers", 0.0),
            "snowfall": curr.get("snowfall", 0.0),
            "weather_code": w_code,
            "weather_description": w_desc,
            "cloud_cover": curr.get("cloud_cover", 0),
            "pressure_msl": curr.get("pressure_msl"),
            "surface_pressure": curr.get("surface_pressure"),
            "wind_speed": curr.get("wind_speed_10m"),
            "wind_direction_degrees": wind_deg,
            "wind_direction_compass": wind_comp,
            "wind_gusts": curr.get("wind_gusts_10m"),
        },
        "units": {
            "temperature": curr_units.get("temperature_2m", "°C"),
            "relative_humidity": curr_units.get("relative_humidity_2m", "%"),
            "precipitation": curr_units.get("precipitation", "mm"),
            "wind_speed": curr_units.get("wind_speed_10m", "km/h"),
            "pressure": curr_units.get("pressure_msl", "hPa"),
        },
        "source": "Open-Meteo.com",
        "attribution": ATTRIBUTION_STATEMENT,
    }

    weather_cache[cache_key] = result
    return result


async def get_forecast(
    location_query: str,
    forecast_days: int = 7,
    forecast_hours: Optional[int] = None,
    include_hourly: bool = False,
    include_astronomy: bool = False,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> Dict[str, Any]:
    """Retrieve 1 to 16-day forecast with optional hourly breakdowns, plain language summary, and astronomy."""
    loc = await resolve_location(location_query)
    lat_r = round_coord(loc["latitude"])
    lon_r = round_coord(loc["longitude"])

    cache_key = (
        f"{lat_r}:{lon_r}:{forecast_days}:{forecast_hours}:"
        f"{include_hourly}:{include_astronomy}:{temperature_unit}:{wind_speed_unit}:{precipitation_unit}"
    )

    if cache_key in forecast_cache:
        cached_res = dict(forecast_cache[cache_key])
        cached_res["location"] = loc
        return cached_res

    daily_vars = (
        "weather_code,temperature_2m_max,temperature_2m_min,"
        "apparent_temperature_max,apparent_temperature_min,sunrise,sunset,"
        "uv_index_max,precipitation_sum,precipitation_probability_max,"
        "wind_speed_10m_max,wind_gusts_10m_max"
    )
    if include_astronomy:
        daily_vars += ",daylight_duration,sunshine_duration"

    params: Dict[str, Any] = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "daily": daily_vars,
        "timezone": "auto",
        "forecast_days": min(max(forecast_days, 1), 16),
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": precipitation_unit,
    }

    if include_hourly or forecast_hours:
        params["hourly"] = (
            "temperature_2m,apparent_temperature,precipitation_probability,"
            "precipitation,weather_code,wind_speed_10m,relative_humidity_2m"
        )
        if forecast_hours:
            params["forecast_hours"] = min(max(forecast_hours, 1), 168)

    resp = await request_upstream(
        method="GET",
        url=settings.OPEN_METEO_FORECAST_URL,
        is_open_meteo=True,
        params=params,
    )
    raw = resp.json()

    daily_raw = raw.get("daily", {})
    daily_units = raw.get("daily_units", {})
    hourly_raw = raw.get("hourly")
    hourly_units = raw.get("hourly_units")

    # Format daily entries
    formatted_daily: List[Dict[str, Any]] = []
    times = daily_raw.get("time", [])

    for idx, dt_str in enumerate(times):
        code = daily_raw.get("weather_code", [])[idx] if idx < len(daily_raw.get("weather_code", [])) else 0
        d_entry: Dict[str, Any] = {
            "date": dt_str,
            "weather_code": code,
            "weather_description": get_weather_description(code),
            "temperature_max": daily_raw.get("temperature_2m_max", [])[idx],
            "temperature_min": daily_raw.get("temperature_2m_min", [])[idx],
            "apparent_temperature_max": daily_raw.get("apparent_temperature_max", [])[idx],
            "apparent_temperature_min": daily_raw.get("apparent_temperature_min", [])[idx],
            "precipitation_sum": daily_raw.get("precipitation_sum", [])[idx],
            "precipitation_probability_max": daily_raw.get("precipitation_probability_max", [])[idx],
            "wind_speed_max": daily_raw.get("wind_speed_10m_max", [])[idx],
            "wind_gusts_max": daily_raw.get("wind_gusts_10m_max", [])[idx],
            "uv_index_max": daily_raw.get("uv_index_max", [])[idx],
            "sunrise": daily_raw.get("sunrise", [])[idx] if "sunrise" in daily_raw else None,
            "sunset": daily_raw.get("sunset", [])[idx] if "sunset" in daily_raw else None,
        }

        if include_astronomy:
            target_d = datetime.strptime(dt_str, "%Y-%m-%d").date()
            moon = calculate_moon_phase(target_d)
            d_entry["astronomy"] = {
                "moon_phase": moon["phase_name"],
                "moon_illumination": moon["illumination_percentage"],
                "daylight_duration_seconds": daily_raw.get("daylight_duration", [])[idx] if "daylight_duration" in daily_raw else None,
                "sunshine_duration_seconds": daily_raw.get("sunshine_duration", [])[idx] if "sunshine_duration" in daily_raw else None,
            }

        formatted_daily.append(d_entry)

    # Format hourly entries if present
    formatted_hourly: Optional[List[Dict[str, Any]]] = None
    if hourly_raw and "time" in hourly_raw:
        formatted_hourly = []
        h_times = hourly_raw.get("time", [])
        for idx, h_time in enumerate(h_times):
            h_code = hourly_raw.get("weather_code", [])[idx] if idx < len(hourly_raw.get("weather_code", [])) else 0
            formatted_hourly.append({
                "time": h_time,
                "temperature": hourly_raw.get("temperature_2m", [])[idx],
                "apparent_temperature": hourly_raw.get("apparent_temperature", [])[idx],
                "precipitation_probability": hourly_raw.get("precipitation_probability", [])[idx],
                "precipitation": hourly_raw.get("precipitation", [])[idx],
                "relative_humidity": hourly_raw.get("relative_humidity_2m", [])[idx],
                "wind_speed": hourly_raw.get("wind_speed_10m", [])[idx],
                "weather_code": h_code,
                "weather_description": get_weather_description(h_code),
            })

    summary = generate_forecast_summary(daily_raw, temperature_unit)

    result = {
        "location": loc,
        "summary": summary,
        "daily": formatted_daily,
        "daily_units": daily_units,
        "hourly": formatted_hourly,
        "hourly_units": hourly_units,
        "source": "Open-Meteo.com",
        "attribution": ATTRIBUTION_STATEMENT,
    }

    forecast_cache[cache_key] = result
    return result


def categorize_aqi(aqi_value: float) -> tuple[str, str]:
    """Map numeric AQI value to level category and health tip."""
    if aqi_value <= 50:
        return "Good", "Air quality is satisfactory and poses little or no risk. Enjoy outdoor activities."
    elif aqi_value <= 100:
        return "Moderate", "Air quality is acceptable. Very sensitive individuals may consider reducing prolonged outdoor exertion."
    elif aqi_value <= 150:
        return "Unhealthy for Sensitive Groups", "Members of sensitive groups (asthma, heart/lung disease, elderly, children) should reduce prolonged outdoor exertion."
    elif aqi_value <= 200:
        return "Unhealthy", "Everyone may begin to experience health effects. Sensitive groups should avoid prolonged outdoor exertion."
    elif aqi_value <= 300:
        return "Very Unhealthy", "Health alert: The risk of health effects is increased for everyone. Avoid prolonged outdoor activities."
    else:
        return "Hazardous", "Health warning of emergency conditions: Everyone is more likely to be affected. Remain indoors with air filtration."


async def get_air_quality(location_query: str) -> Dict[str, Any]:
    """Retrieve current air quality indexes, pollutants, UV index, and pollen from Open-Meteo."""
    loc = await resolve_location(location_query)
    lat_r = round_coord(loc["latitude"])
    lon_r = round_coord(loc["longitude"])

    cache_key = f"{lat_r}:{lon_r}"
    if cache_key in air_quality_cache:
        cached_res = dict(air_quality_cache[cache_key])
        cached_res["location"] = loc
        return cached_res

    params = {
        "latitude": loc["latitude"],
        "longitude": loc["longitude"],
        "current": (
            "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,"
            "ozone,dust,uv_index,european_aqi,us_aqi,"
            "alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen"
        ),
    }

    resp = await request_upstream(
        method="GET",
        url=settings.OPEN_METEO_AIR_QUALITY_URL,
        is_open_meteo=True,
        params=params,
    )
    raw = resp.json()
    curr = raw.get("current", {})
    curr_units = raw.get("current_units", {})

    us_aqi = curr.get("us_aqi")
    european_aqi = curr.get("european_aqi")
    primary_aqi = us_aqi if us_aqi is not None else (european_aqi if european_aqi is not None else 30)

    category, health_tip = categorize_aqi(primary_aqi)

    # Collect pollen if present
    pollen_types = ["alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen", "olive_pollen", "ragweed_pollen"]
    pollen_data = {k: curr.get(k) for k in pollen_types if curr.get(k) is not None}

    result = {
        "location": loc,
        "current": {
            "time": curr.get("time"),
            "aqi_us": us_aqi,
            "aqi_european": european_aqi,
            "category": category,
            "health_tip": health_tip,
            "pm2_5": curr.get("pm2_5"),
            "pm10": curr.get("pm10"),
            "carbon_monoxide": curr.get("carbon_monoxide"),
            "nitrogen_dioxide": curr.get("nitrogen_dioxide"),
            "sulphur_dioxide": curr.get("sulphur_dioxide"),
            "ozone": curr.get("ozone"),
            "dust": curr.get("dust"),
            "uv_index": curr.get("uv_index"),
            "pollen": pollen_data if pollen_data else None,
        },
        "units": curr_units,
        "source": "Open-Meteo.com",
        "attribution": ATTRIBUTION_STATEMENT,
    }

    air_quality_cache[cache_key] = result
    return result


async def get_weather_advice(location_query: str) -> Dict[str, Any]:
    """Analyze current conditions and forecast to generate actionable lifestyle advice and comfort score."""
    current_data = await get_current_weather(location_query, temperature_unit="celsius")
    curr = current_data["current"]
    temp = curr.get("temperature", 20.0)
    apparent_temp = curr.get("apparent_temperature", temp)
    precip = curr.get("precipitation", 0.0)
    wind_speed = curr.get("wind_speed", 10.0)
    wind_gusts = curr.get("wind_gusts", wind_speed)
    humidity = curr.get("relative_humidity", 50)
    w_code = curr.get("weather_code", 0)

    # Retrieve UV index from Air Quality or current
    uv = 0.0
    try:
        aq = await get_air_quality(location_query)
        uv = aq["current"].get("uv_index") or 0.0
    except Exception:
        uv = 3.0 if curr.get("is_day") and w_code in (0, 1) else 0.0

    # 1. Umbrella advice
    umbrella_needed = precip > 0.0 or w_code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 97, 99)
    umbrella_reason = (
        "Active rain or showers detected; carry an umbrella."
        if umbrella_needed
        else "No precipitation detected. Umbrella not needed."
    )

    # 2. Jacket advice
    if apparent_temp >= 24.0:
        jacket = "none"
        jacket_reason = f"Warm temperatures ({round(apparent_temp, 1)}°C feels like). Light clothing recommended."
    elif apparent_temp >= 17.0:
        jacket = "light"
        jacket_reason = f"Mild weather ({round(apparent_temp, 1)}°C feels like). A light jacket or sweater is suitable."
    elif apparent_temp >= 8.0:
        jacket = "warm"
        jacket_reason = f"Cool conditions ({round(apparent_temp, 1)}°C feels like). A warm jacket or fleece is recommended."
    else:
        jacket = "heavy"
        jacket_reason = f"Cold temperatures ({round(apparent_temp, 1)}°C feels like). Heavy winter coat, gloves, and warm layers required."

    # 3. Sunscreen advice
    sunscreen_needed = uv >= 3.0
    sunscreen_reason = (
        f"UV index is {round(uv, 1)} (moderate to high). Apply SPF 30+ sunscreen and wear sunglasses if spending extended time outside."
        if sunscreen_needed
        else f"UV index is low ({round(uv, 1)}). Sunscreen is not urgently required."
    )

    # 4. Heat risk
    if temp >= 38.0:
        heat_risk = "extreme"
        heat_reason = f"Extreme heat alert ({round(temp, 1)}°C). High risk of heat exhaustion and stroke. Stay indoors in air conditioning and hydrate."
    elif temp >= 30.0:
        heat_risk = "caution"
        heat_reason = f"Warm/hot weather ({round(temp, 1)}°C). Drink plenty of water and avoid strenuous outdoor exercise in peak afternoon."
    else:
        heat_risk = "none"
        heat_reason = "Temperatures are within comfortable thermal limits."

    # 5. Wind warning
    wind_warning = wind_gusts >= 50.0
    wind_reason = (
        f"High wind gusts reaching {round(wind_gusts, 1)} km/h. Exercise caution driving and secure lightweight outdoor furniture."
        if wind_warning
        else f"Wind is calm to moderate ({round(wind_speed, 1)} km/h)."
    )

    # 6. Comfort score (0 to 10)
    # Starts at 10, penalizes for temperature deviation from 21°C, high humidity, rain, high wind
    score = 10.0
    temp_penalty = abs(apparent_temp - 21.0) * 0.25
    score -= min(temp_penalty, 4.0)

    if humidity > 70:
        score -= min((humidity - 70) * 0.05, 1.5)
    elif humidity < 30:
        score -= 0.5

    if precip > 0:
        score -= min(1.0 + precip * 0.5, 3.0)

    if wind_speed > 30:
        score -= min((wind_speed - 30) * 0.1, 2.0)

    comfort_score = max(0, min(10, int(round(score))))

    summary_narrative = (
        f"In {current_data['location']['name']}, conditions are {curr['weather_description'].lower()} "
        f"at {round(temp, 1)}°C ({round(apparent_temp, 1)}°C feels like). "
        f"{'Take an umbrella.' if umbrella_needed else 'No umbrella needed.'} "
        f"Wear {jacket} jacket. Overall comfort rating: {comfort_score}/10."
    )

    return {
        "location": current_data["location"],
        "comfort_score": comfort_score,
        "summary": summary_narrative,
        "advice": {
            "umbrella": {"needed": umbrella_needed, "reason": umbrella_reason},
            "jacket": {"type": jacket, "reason": jacket_reason},
            "sunscreen": {"needed": sunscreen_needed, "reason": sunscreen_reason, "uv_index": uv},
            "heat_risk": {"level": heat_risk, "reason": heat_reason},
            "wind_warning": {"warning": wind_warning, "reason": wind_reason, "gusts_kmh": wind_gusts},
        },
        "source": "Open-Meteo.com",
        "attribution": ATTRIBUTION_STATEMENT,
    }
