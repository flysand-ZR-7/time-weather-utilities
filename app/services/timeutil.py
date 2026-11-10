"""Time, timezone conversion, world clock, and date calculation utilities."""

import calendar
import difflib
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, available_timezones

# Common city and alias mapping to standard IANA timezone keys
COMMON_CITY_TIMEZONES: Dict[str, str] = {
    "london": "Europe/London",
    "manchester": "Europe/London",
    "edinburgh": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "rome": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "amsterdam": "Europe/Amsterdam",
    "brussels": "Europe/Brussels",
    "vienna": "Europe/Vienna",
    "zurich": "Europe/Zurich",
    "geneva": "Europe/Zurich",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "athens": "Europe/Athens",
    "istanbul": "Europe/Istanbul",
    "moscow": "Europe/Moscow",
    "dubai": "Asia/Dubai",
    "abu dhabi": "Asia/Dubai",
    "doha": "Asia/Qatar",
    "riyadh": "Asia/Riyadh",
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "nairobi": "Africa/Nairobi",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "new delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "chennai": "Asia/Kolkata",
    "hyderabad": "Asia/Kolkata",
    "karachi": "Asia/Karachi",
    "dhaka": "Asia/Dhaka",
    "bangkok": "Asia/Bangkok",
    "singapore": "Asia/Singapore",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "jakarta": "Asia/Jakarta",
    "tokyo": "Asia/Tokyo",
    "osaka": "Asia/Tokyo",
    "kyoto": "Asia/Tokyo",
    "seoul": "Asia/Seoul",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "taipei": "Asia/Taipei",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "auckland": "Pacific/Auckland",
    "wellington": "Pacific/Auckland",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "boston": "America/New_York",
    "washington": "America/New_York",
    "miami": "America/New_York",
    "atlanta": "America/New_York",
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "chicago": "America/Chicago",
    "houston": "America/Chicago",
    "dallas": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "vancouver": "America/Vancouver",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "santiago": "America/Santiago",
    "honolulu": "Pacific/Honolulu",
    "utc": "UTC",
    "gmt": "Etc/GMT",
}


def get_all_timezones() -> List[str]:
    """Return sorted list of all available IANA timezones."""
    return sorted(list(available_timezones()))


def search_timezones(query: str, limit: int = 10) -> List[str]:
    """Search available timezones by city name or IANA pattern."""
    q = query.strip().lower()
    if not q:
        return get_all_timezones()[:limit]

    matches: List[str] = []

    # 1. Direct city alias match
    if q in COMMON_CITY_TIMEZONES:
        matches.append(COMMON_CITY_TIMEZONES[q])

    # 2. Substring matching in available IANA zones
    all_zones = get_all_timezones()
    for tz in all_zones:
        if q in tz.lower():
            if tz not in matches:
                matches.append(tz)

    # 3. Fuzzy matching if few/no substring matches
    if len(matches) < limit:
        fuzzy = difflib.get_close_matches(query, all_zones, n=limit, cutoff=0.4)
        for f in fuzzy:
            if f not in matches:
                matches.append(f)

    return matches[:limit]


def resolve_timezone(name_or_city: str) -> str:
    """Resolve an input string (city name or IANA identifier) into a valid IANA timezone string.
    
    Raises:
        ValueError if the timezone cannot be resolved, including close suggestions.
    """
    raw = name_or_city.strip()
    clean = raw.lower()

    # 1. Check direct city alias
    if clean in COMMON_CITY_TIMEZONES:
        return COMMON_CITY_TIMEZONES[clean]

    # 2. Try direct ZoneInfo instantiation
    try:
        ZoneInfo(raw)
        return raw
    except Exception:
        pass

    # 3. Case-insensitive lookup across all available IANA timezones
    all_zones = get_all_timezones()
    zone_lookup = {z.lower(): z for z in all_zones}
    if clean in zone_lookup:
        return zone_lookup[clean]

    # If no exact match or alias exists, raise with fuzzy suggestions
    suggestions = difflib.get_close_matches(raw, all_zones, n=3, cutoff=0.3)
    suggestion_msg = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    raise ValueError(f"Timezone or city '{name_or_city}' could not be resolved.{suggestion_msg}")


def format_utc_offset(td: Optional[timedelta]) -> str:
    """Format a timedelta offset into '+HH:MM' or '-HH:MM' string."""
    if td is None:
        return "+00:00"
    total_seconds = int(td.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def get_live_time(
    timezone_name: str,
    at: Optional[datetime] = None,
    date_format: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve detailed time information for a resolved IANA timezone."""
    resolved_tz = resolve_timezone(timezone_name)
    zi = ZoneInfo(resolved_tz)

    if at is None:
        target_dt = datetime.now(zi)
    else:
        if at.tzinfo is None:
            target_dt = at.replace(tzinfo=zi)
        else:
            target_dt = at.astimezone(zi)

    utc_offset_td = target_dt.utcoffset()
    utc_offset_str = format_utc_offset(utc_offset_td)
    utc_offset_seconds = int(utc_offset_td.total_seconds()) if utc_offset_td else 0

    # DST check
    dst_td = target_dt.dst()
    is_dst = dst_td is not None and dst_td.total_seconds() != 0

    tz_abbr = target_dt.strftime("%Z")
    day_of_week = target_dt.strftime("%A")
    day_of_year = target_dt.timetuple().tm_yday
    iso_year, iso_week, _ = target_dt.isocalendar()

    formatted_time = target_dt.strftime(date_format) if date_format else target_dt.isoformat()

    return {
        "timezone": resolved_tz,
        "datetime": formatted_time,
        "utc_offset": utc_offset_str,
        "utc_offset_seconds": utc_offset_seconds,
        "is_dst": is_dst,
        "timezone_abbreviation": tz_abbr,
        "day_of_week": day_of_week,
        "day_of_year": day_of_year,
        "week_number": iso_week,
        "iso_year": iso_year,
        "unix_timestamp": int(target_dt.timestamp()),
    }


def convert_timezone_times(
    datetime_str: str,
    from_zone_input: str,
    to_zone_input: str,
) -> Dict[str, Any]:
    """Convert a datetime string from one timezone to another with DST fold/gap ambiguity detection."""
    from_tz = resolve_timezone(from_zone_input)
    to_tz = resolve_timezone(to_zone_input)

    from_zi = ZoneInfo(from_tz)
    to_zi = ZoneInfo(to_tz)

    # Parse ISO datetime
    try:
        dt_naive = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        if dt_naive.tzinfo is not None:
            # If already has tzinfo, convert from its tzinfo
            source_dt = dt_naive.astimezone(from_zi)
        else:
            source_dt = dt_naive.replace(tzinfo=from_zi)
    except Exception as exc:
        raise ValueError(f"Invalid datetime format: '{datetime_str}'. Expected ISO 8601 format (e.g., '2026-03-08T02:30:00').") from exc

    # Check for DST gap (spring forward: non-existent local time) and fold (fall back: repeated time)
    warning: Optional[str] = None
    naive_repr = source_dt.replace(tzinfo=None)

    dt_fold0 = naive_repr.replace(fold=0, tzinfo=from_zi)
    dt_fold1 = naive_repr.replace(fold=1, tzinfo=from_zi)

    if dt_fold0.utcoffset() != dt_fold1.utcoffset():
        warning = (
            "Ambiguous local time: this wall-clock time occurs twice during the autumn DST fallback. "
            "Evaluated using the earlier standard/daylight occurrence (fold=0)."
        )

    # Check spring-forward gap: converting to UTC and back produces a different wall clock time
    back_dt = source_dt.astimezone(timezone.utc).astimezone(from_zi)
    if (back_dt.hour, back_dt.minute) != (source_dt.hour, source_dt.minute):
        warning = (
            "Non-existent local time: this wall-clock time falls inside the spring-forward DST transition gap. "
            "Adjusted automatically by timezone rules."
        )

    target_dt = source_dt.astimezone(to_zi)

    # Calculate difference in UTC offset hours
    src_offset = source_dt.utcoffset().total_seconds() / 3600.0 if source_dt.utcoffset() else 0.0
    tgt_offset = target_dt.utcoffset().total_seconds() / 3600.0 if target_dt.utcoffset() else 0.0
    diff_hours = tgt_offset - src_offset

    dst_src = source_dt.dst() is not None and source_dt.dst().total_seconds() != 0
    dst_tgt = target_dt.dst() is not None and target_dt.dst().total_seconds() != 0

    return {
        "source_timezone": from_tz,
        "source_datetime": source_dt.isoformat(),
        "target_timezone": to_tz,
        "target_datetime": target_dt.isoformat(),
        "utc_difference_hours": round(diff_hours, 2),
        "dst_active_source": dst_src,
        "dst_active_target": dst_tgt,
        "warning": warning,
    }


def add_months(sourcedate: date, months: int) -> date:
    """Add or subtract months with correct month-end rollover/clamping (e.g. Jan 31 + 1 mo = Feb 28/29)."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def calculate_date_operation(
    operation: str,
    start_date: date,
    end_date: Optional[date] = None,
    days: int = 0,
    weeks: int = 0,
    months: int = 0,
    years: int = 0,
    business_days: int = 0,
) -> Dict[str, Any]:
    """Perform date mathematics and inspection."""
    op = operation.lower().strip()

    if op == "difference":
        if end_date is None:
            raise ValueError("end_date is required for 'difference' operation.")

        d1, d2 = start_date, end_date
        is_negative = d2 < d1
        if is_negative:
            d1, d2 = d2, d1

        total_days = (d2 - d1).days
        total_hours = total_days * 24

        # Count business days (Monday=0 to Friday=4)
        cur = d1
        biz_count = 0
        while cur < d2:
            if cur.weekday() < 5:
                biz_count += 1
            cur += timedelta(days=1)

        # Approximate calendar year/month breakdown
        curr_y = d1.year
        curr_m = d1.month
        months_diff = (d2.year - curr_y) * 12 + (d2.month - curr_m)
        if d2.day < d1.day:
            months_diff -= 1

        cal_years = months_diff // 12
        cal_months = months_diff % 12

        # Remainder days
        temp_date = add_months(d1, cal_years * 12 + cal_months)
        rem_days = (d2 - temp_date).days

        return {
            "operation": "difference",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_days": -total_days if is_negative else total_days,
            "total_hours": -total_hours if is_negative else total_hours,
            "business_days": -biz_count if is_negative else biz_count,
            "years": -cal_years if is_negative else cal_years,
            "months": -cal_months if is_negative else cal_months,
            "days": -rem_days if is_negative else rem_days,
        }

    elif op in ("add", "subtract"):
        factor = 1 if op == "add" else -1
        res_date = start_date

        # Add/subtract years and months
        total_months = factor * (years * 12 + months)
        if total_months != 0:
            res_date = add_months(res_date, total_months)

        # Add/subtract weeks and calendar days
        total_days_offset = factor * (weeks * 7 + days)
        if total_days_offset != 0:
            res_date += timedelta(days=total_days_offset)

        # Add/subtract business days
        if business_days > 0:
            count = 0
            step = 1 if factor == 1 else -1
            while count < business_days:
                res_date += timedelta(days=step)
                if res_date.weekday() < 5:
                    count += 1

        return {
            "operation": op,
            "start_date": str(start_date),
            "result_date": str(res_date),
            "day_of_week": res_date.strftime("%A"),
            "is_weekend": res_date.weekday() >= 5,
            "is_leap_year": calendar.isleap(res_date.year),
            "day_of_year": res_date.timetuple().tm_yday,
        }

    elif op == "weekday":
        day_idx = start_date.weekday()  # 0=Monday, 6=Sunday
        return {
            "operation": "weekday",
            "date": str(start_date),
            "day_name": start_date.strftime("%A"),
            "day_index": day_idx,
            "is_weekend": day_idx >= 5,
            "is_leap_year": calendar.isleap(start_date.year),
        }

    elif op == "week_number":
        iso_year, iso_week, iso_weekday = start_date.isocalendar()
        return {
            "operation": "week_number",
            "date": str(start_date),
            "iso_week": iso_week,
            "iso_year": iso_year,
            "day_of_year": start_date.timetuple().tm_yday,
        }

    elif op == "days_until":
        target = end_date or start_date
        reference = start_date if end_date is not None else date.today()

        delta = (target - reference).days
        is_past = delta < 0
        return {
            "operation": "days_until",
            "reference_date": str(reference),
            "target_date": str(target),
            "days_remaining": abs(delta),
            "is_past": is_past,
            "weeks_remaining": round(abs(delta) / 7.0, 1),
        }

    else:
        raise ValueError(
            f"Unsupported operation '{operation}'. Supported operations: 'difference', 'add', 'subtract', 'weekday', 'week_number', 'days_until'."
        )
