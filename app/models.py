"""Pydantic v2 data models and request/response contracts for all endpoints."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Standard Error Models
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """Detailed error object returned on all failed requests."""
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class StandardErrorResponse(BaseModel):
    """Consistent envelope for error responses across the API."""
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Time & Timezones Models
# ---------------------------------------------------------------------------

class TimeRequest(BaseModel):
    """Request model for retrieving current or evaluated local time in a timezone or city."""
    timezone: str = Field(..., description="IANA timezone name (e.g. 'America/New_York') or city name (e.g. 'Tokyo')")
    at: Optional[datetime] = Field(None, description="Optional ISO datetime to evaluate instead of current system time")
    date_format: Optional[str] = Field(None, description="Optional strftime formatting string")


class TimeResponse(BaseModel):
    """Detailed timezone and local time metadata."""
    timezone: str
    datetime: str
    utc_offset: str
    utc_offset_seconds: int
    is_dst: bool
    timezone_abbreviation: str
    day_of_week: str
    day_of_year: int
    week_number: int
    iso_year: int
    unix_timestamp: int


class WorldClockRequest(BaseModel):
    """Request model for checking current time across multiple cities or timezones."""
    locations: List[str] = Field(..., min_length=1, max_length=10, description="List of 1 to 10 cities or timezone identifiers")
    date_format: Optional[str] = Field(None, description="Optional strftime formatting string")


class WorldClockResponse(BaseModel):
    """World clock response sorted by UTC offset ascending."""
    count: int
    locations: List[TimeResponse]


class TimezoneConvertRequest(BaseModel):
    """Request model for converting a datetime across two timezones."""
    datetime_str: str = Field(..., description="Source date and time in ISO format (e.g. '2026-03-08T02:30:00')")
    from_zone: str = Field(..., description="Originating IANA timezone or city")
    to_zone: str = Field(..., description="Target IANA timezone or city")


class TimezoneConvertResponse(BaseModel):
    """Result of converting a wall-clock time between timezones, with DST warnings."""
    source_timezone: str
    source_datetime: str
    target_timezone: str
    target_datetime: str
    utc_difference_hours: float
    dst_active_source: bool
    dst_active_target: bool
    warning: Optional[str] = None


class TimezoneSearchResponse(BaseModel):
    """Matching IANA timezones response."""
    query: str
    count: int
    results: List[str]


# ---------------------------------------------------------------------------
# Date Calculator Models
# ---------------------------------------------------------------------------

class DateCalcRequest(BaseModel):
    """Request model for calendar date mathematics and inspections."""
    operation: Literal["difference", "add", "subtract", "weekday", "week_number", "days_until"] = Field(
        ..., description="Date calculation operation"
    )
    start_date: date = Field(..., description="Primary date in YYYY-MM-DD format")
    end_date: Optional[date] = Field(None, description="Secondary date for difference or target for days_until")
    days: int = Field(0, description="Calendar days to add or subtract")
    weeks: int = Field(0, description="Weeks to add or subtract")
    months: int = Field(0, description="Calendar months to add or subtract")
    years: int = Field(0, description="Calendar years to add or subtract")
    business_days: int = Field(0, description="Business days (skipping Sat & Sun) to add or subtract")


# ---------------------------------------------------------------------------
# Weather Models
# ---------------------------------------------------------------------------

class CurrentWeatherRequest(BaseModel):
    """Request model for current weather observation."""
    location: str = Field(..., description="City name (e.g. 'Paris') or 'latitude, longitude' coordinates")
    temperature_unit: Literal["celsius", "fahrenheit"] = Field("celsius", description="Temperature unit")
    wind_speed_unit: Literal["kmh", "ms", "mph", "kn"] = Field("kmh", description="Wind speed unit")
    precipitation_unit: Literal["mm", "inch"] = Field("mm", description="Precipitation unit")


class CurrentWeatherResponse(BaseModel):
    """Current weather metrics and metadata."""
    location: Dict[str, Any]
    current: Dict[str, Any]
    units: Dict[str, str]
    source: str
    attribution: str


class ForecastRequest(BaseModel):
    """Request model for weather forecasting."""
    location: str = Field(..., description="City name or 'latitude, longitude'")
    forecast_days: int = Field(7, ge=1, le=16, description="Days of forecast (1-16)")
    forecast_hours: Optional[int] = Field(None, ge=1, le=168, description="Optional hours of forecast for hourly data")
    include_hourly: bool = Field(False, description="Whether to include detailed hourly forecast array")
    include_astronomy: bool = Field(False, description="Whether to compute sun and moon phases")
    temperature_unit: Literal["celsius", "fahrenheit"] = Field("celsius")
    wind_speed_unit: Literal["kmh", "ms", "mph", "kn"] = Field("kmh")
    precipitation_unit: Literal["mm", "inch"] = Field("mm")


class ForecastResponse(BaseModel):
    """Forecast response with daily metrics and narrative summary."""
    location: Dict[str, Any]
    summary: str
    daily: List[Dict[str, Any]]
    daily_units: Dict[str, str]
    hourly: Optional[List[Dict[str, Any]]] = None
    hourly_units: Optional[Dict[str, str]] = None
    source: str
    attribution: str


class AirQualityRequest(BaseModel):
    """Request model for air quality inspection."""
    location: str = Field(..., description="City name or 'latitude, longitude'")


class AirQualityResponse(BaseModel):
    """Air quality metrics, pollutant concentrations, and health advice."""
    location: Dict[str, Any]
    current: Dict[str, Any]
    units: Dict[str, str]
    source: str
    attribution: str


class WeatherAdviceRequest(BaseModel):
    """Request model for lifestyle weather advice."""
    location: str = Field(..., description="City name or 'latitude, longitude'")


class WeatherAdviceResponse(BaseModel):
    """Lifestyle recommendations: umbrella, jacket, sunscreen, wind, heat, and comfort score."""
    location: Dict[str, Any]
    comfort_score: int = Field(..., ge=0, le=10, description="Overall outdoor comfort score from 0 (poor) to 10 (ideal)")
    summary: str
    advice: Dict[str, Any]
    source: str
    attribution: str


# ---------------------------------------------------------------------------
# Calculator & Finance Models
# ---------------------------------------------------------------------------

class CalcRequest(BaseModel):
    """Request model for safe AST mathematical evaluation."""
    expression: str = Field(..., description="Mathematical expression (e.g. '2^10 + sqrt(144) * sin(pi/2)')")


class CalcResponse(BaseModel):
    """Evaluated mathematical result."""
    expression: str
    result: Union[int, float]
    formatted: str


class FinanceCalcRequest(BaseModel):
    """Request model for financial and commercial calculations."""
    operation: Literal[
        "percentage", "discount", "tax", "tip_split", "simple_interest", "compound_interest", "emi"
    ] = Field(..., description="Financial calculation operation")
    amount: Optional[float] = Field(None, description="General amount for tax calculations")
    percent: Optional[float] = Field(None, description="General percentage")
    value: Optional[float] = Field(None, description="Value for percentage calculations")
    total: Optional[float] = Field(None, description="Total for share calculations")
    old_value: Optional[float] = Field(None, description="Original value for percentage increase/decrease")
    new_value: Optional[float] = Field(None, description="New value for percentage increase/decrease")
    original_price: Optional[float] = Field(None, description="Original price before discount")
    discount_percent: Optional[float] = Field(None, description="Discount percentage")
    tax_percent: Optional[float] = Field(None, description="Sales tax, GST, or VAT percentage")
    tax_included: bool = Field(False, description="True if amount already contains tax")
    bill_amount: Optional[float] = Field(None, description="Base bill amount before tip")
    tip_percent: Optional[float] = Field(None, description="Tip percentage (e.g. 15, 18, 20)")
    num_people: int = Field(1, ge=1, description="Number of people splitting the bill")
    principal: Optional[float] = Field(None, description="Principal loan or investment amount")
    rate_annual_percent: Optional[float] = Field(None, description="Annual interest rate in percent")
    time_years: Optional[float] = Field(None, description="Duration in years")
    compounding_frequency: int = Field(12, description="Compounding times per year (1=annual, 12=monthly, 365=daily)")
    tenure_months: Optional[int] = Field(None, description="Loan tenure in months for EMI")


# ---------------------------------------------------------------------------
# Unit Converter Models
# ---------------------------------------------------------------------------

class ConvertRequest(BaseModel):
    """Request model for converting physical measurement units."""
    value: float = Field(..., description="Numeric magnitude to convert")
    from_unit: str = Field(..., description="Source unit (e.g. 'celsius', 'mph', 'miles', 'lbs', 'GB')")
    to_unit: str = Field(..., description="Target unit (e.g. 'fahrenheit', 'km/h', 'km', 'kg', 'MiB')")


class ConvertResponse(BaseModel):
    """Result of unit conversion with canonical names and explanation."""
    from_value: float
    from_unit: str
    to_value: float
    to_unit: str
    canonical_from: str
    canonical_to: str
    explanation: str


class UnitCategoriesResponse(BaseModel):
    """Catalog of supported physical measurement categories."""
    categories: Dict[str, Any]


# ---------------------------------------------------------------------------
# Currency Models
# ---------------------------------------------------------------------------

class CurrencyConvertRequest(BaseModel):
    """Request model for currency exchange."""
    amount: float = Field(1.0, ge=0, description="Monetary amount to convert")
    from_currency: str = Field("USD", description="Base 3-letter currency code (e.g. 'USD', 'EUR')")
    to_currencies: List[str] = Field(
        default_factory=lambda: ["EUR"],
        min_length=1,
        max_length=10,
        description="List of 1 to 10 target currency codes",
    )
    date: Optional[str] = Field(None, description="Optional historical date in YYYY-MM-DD format")


class CurrencyConvertResponse(BaseModel):
    """Currency conversion results across requested targets."""
    amount: float
    base_currency: str
    base_currency_name: str
    date: str
    rates: Dict[str, float]
    conversions: Dict[str, Dict[str, Any]]


class CurrencyListResponse(BaseModel):
    """List of all currencies supported by the exchange provider."""
    count: int
    currencies: Dict[str, str]


class CurrencyTrendRequest(BaseModel):
    """Request model for currency time-series analysis."""
    from_currency: str = Field("USD", description="Base 3-letter currency code")
    to_currency: str = Field("EUR", description="Target 3-letter currency code")
    days: Literal[7, 30] = Field(30, description="Trend window in days (7 or 30)")


class CurrencyTrendResponse(BaseModel):
    """Historical rate trend, min/max/average, and directional analysis."""
    from_currency: str
    to_currency: str
    days: int
    start_date: str
    end_date: str
    min_rate: float
    max_rate: float
    average_rate: float
    first_rate: float
    latest_rate: float
    change_percent: float
    trend_direction: Literal["up", "down", "flat"]
    rates_count: int
    daily_rates: Dict[str, float]


# ---------------------------------------------------------------------------
# Health & Status Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Service status, Open-Meteo budget consumption, and cache metrics."""
    status: str
    service: str
    version: str
    uptime_seconds: float
    open_meteo_budget: Dict[str, Any]
    cache_stats: Dict[str, Any]
    attribution_notice: str
