# Time, Weather & Utilities Plugin

An asynchronous, production-ready FastAPI plugin providing an AI assistant with 7 real-time live capabilities across time, meteorology, safe mathematics, units, and finance:

1. **Live Time & World Clock:** High-precision IANA timezone resolution, daylight saving time (DST) status, UTC offsets, and multi-location world clock comparisons.
2. **Time Zones & Conversion:** Inter-timezone conversions with automatic detection and warnings for DST spring-forward gaps and autumn fold ambiguities.
3. **Date Calculator:** Calendar differences (years/months/days/hours), business days tracking (skipping weekends), leap-year metadata, countdowns, and safe month-end roll addition/subtraction.
4. **Current Weather & Forecasts:** Real-time observations and 1-to-16 day forecasts powered by Open-Meteo, with WMO code translation, 16-point compass headings, hourly data, and lunar phases.
5. **Air Quality & Lifestyle Advice:** AQI levels (US & European), PM2.5, PM10, UV index, pollen counts, and rule-based advice (umbrella, clothing layers, sunscreen, comfort rating 0-10).
6. **Safe Calculator & Commercial Finance:** Sandboxed AST mathematical expression evaluator (strictly NO `eval` or `exec`), plus commercial calculators for percentage, discounts, sales tax, tip splitting, compound interest, and loan EMI.
7. **Unit Converter & Currency Exchange:** Physical unit conversion via `pint` (supporting temperature offsets, byte storage MB vs MiB, speed, length, mass) and live foreign currency exchange using European Central Bank reference rates via Frankfurter API.

---

## Technical Architecture

```
                    +------------------------------------+
                    |        Client / AI Agent           |
                    +-----------------+------------------+
                                      | HTTP Requests
                                      v
                    +-----------------+------------------+
                    |      FastAPI ASGI Engine           |
                    | (Lifespan, Rate Limiter 60 req/min)|
                    +-----------------+------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
+------------------+         +------------------+         +------------------+
| Local Engines    |         | Open-Meteo API   |         | Frankfurter API  |
| - AST Calculator |         | - Geocoding      |         | - Latest Rates   |
| - Pint Units     |         | - Forecasts      |         | - Historical     |
| - ZoneInfo Clock |         | - Air Quality    |         | - Time Series    |
| - Date Math      |         | (Daily Budget    |         | (ECB Rates,      |
|                  |         |  Counter: 9.5k)  |         |  Cached 1-24h)   |
+------------------+         +------------------+         +------------------+
         |                            |                            |
         +----------------------------+----------------------------+
                                      v
                    +-----------------+------------------+
                    |    In-Memory TTLCache Engine       |
                    | (Geocode 24h, Weather 10m, etc.)   |
                    +------------------------------------+
```

---

## Upstream Compliance & Attribution

> [!IMPORTANT]
> **Open-Meteo Non-Commercial Compliance:**
> This service queries Open-Meteo.com under its free, non-commercial tier (under 10,000 calls/day). 
> For commercial deployments, a commercial license from Open-Meteo is required.
> 
> **Attribution:**
> Weather data by [Open-Meteo.com](https://open-meteo.com) (non-commercial free tier).

### Upstream Daily Budget Protection
To prevent unintentional quota abuse or IP blocks:
- **Daily Budget Counter:** Thread-safe daily counter tracked against UTC midnight.
- **Warning Threshold (8,000 calls):** Logs operational warnings when daily usage reaches 8,000 calls.
- **Hard Protection Threshold (9,500 calls):** Rejects further outbound weather requests with HTTP `503 Service Unavailable` and code `UPSTREAM_BUDGET_EXCEEDED` before hitting the 10,000 threshold.
- **Aggressive Caching:** Geocoding is cached for 24 hours; current weather for 10 minutes; forecasts and air quality for 30 minutes, keyed by rounded coordinates (~1.1 km precision) and query parameters.

---

## Project Structure

```
time-weather-utilities/
├── app/
│   ├── __init__.py
│   ├── config.py              # Pydantic BaseSettings loading from .env
│   ├── cache.py               # In-memory TTLCache definitions and metrics
│   ├── ratelimit.py           # Sliding-window IP rate limiter middleware
│   ├── upstream.py            # Shared httpx.AsyncClient & Open-Meteo daily budget counter
│   ├── models.py              # Pydantic v2 request/response contracts
│   ├── main.py                # FastAPI app setup, exception handlers, /health
│   ├── services/
│   │   ├── wmo.py             # WMO interpretation table & 16-point compass
│   │   ├── timeutil.py        # ZoneInfo, DST fold/gap detection, date calculations
│   │   ├── geocode.py         # Open-Meteo geocoding search & coordinate parser
│   │   ├── weather.py         # Weather, forecast summary, moon phase, lifestyle advice
│   │   ├── calc.py            # AST-safe evaluator & finance mathematics
│   │   ├── units.py           # Pint unit conversion & category catalog
│   │   └── currency.py        # Frankfurter currency exchange & 30-day trends
│   └── routers/
│       ├── time.py            # /time, /time/world, /timezone/convert, /date/calc
│       ├── weather.py         # /weather/current, /forecast, /air-quality, /advice
│       ├── calc.py            # /calc, /calc/finance
│       ├── units.py           # /convert, /convert/units
│       └── currency.py        # /currency, /currency/list, /currency/trend
├── tools_manifest.json        # OpenAI/Anthropic function calling tool definitions
├── tests/
│   ├── conftest.py            # Test fixtures and cache resets
│   ├── test_time.py           # Time, world clock, conversion, date calc tests
│   ├── test_weather.py        # Current weather & advice tests
│   ├── test_forecast.py       # Multi-day forecast & astronomy tests
│   ├── test_air_quality.py    # Air quality AQI & health tip tests
│   ├── test_calc.py           # AST calculator safety & finance tests
│   ├── test_units.py          # Unit conversion & offset temperature tests
│   ├── test_currency.py       # Currency exchange & trend tests
│   └── test_system.py         # Health check, rate limit, and budget tests
├── requirements.txt
├── .env.example
├── pytest.ini
└── README.md
```

---

## Quickstart

### 1. Requirements & Installation

Requires Python 3.11+.

```bash
# Clone or navigate to the repository
cd time-weather-utilities

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# or: .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Default settings in `.env`:
```env
HOST=0.0.0.0
PORT=8000
RATE_LIMIT_PER_MINUTE=60
OPEN_METEO_WARN_LIMIT=8000
OPEN_METEO_BLOCK_LIMIT=9500
FRANKFURTER_BASE_URL=https://api.frankfurter.dev/v1
```

### 3. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

---

## API Documentation & Examples

### 1. Live Time & World Clock

#### `POST /time`
Get current local time, UTC offset, and DST details:
```bash
curl -s -X POST "http://localhost:8000/time" \
  -H "Content-Type: application/json" \
  -d '{"timezone": "America/New_York"}'
```
Response:
```json
{
  "timezone": "America/New_York",
  "datetime": "2026-10-24T15:45:30.123456-04:00",
  "utc_offset": "-04:00",
  "utc_offset_seconds": -14400,
  "is_dst": true,
  "timezone_abbreviation": "EDT",
  "day_of_week": "Saturday",
  "day_of_year": 297,
  "week_number": 43,
  "iso_year": 2026,
  "unix_timestamp": 1792871130
}
```

#### `POST /time/world`
Compare local times across multiple locations (sorted by UTC offset):
```bash
curl -s -X POST "http://localhost:8000/time/world" \
  -H "Content-Type: application/json" \
  -d '{"locations": ["San Francisco", "London", "Tokyo", "Sydney"]}'
```

#### `POST /timezone/convert`
Convert time across zones with DST autumn fold and spring forward gap detection:
```bash
curl -s -X POST "http://localhost:8000/timezone/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "datetime_str": "2026-03-08T02:30:00",
    "from_zone": "America/New_York",
    "to_zone": "Asia/Tokyo"
  }'
```

#### `POST /date/calc`
Perform business-day arithmetic, countdowns, and date differences:
```bash
# Calculate business days between dates
curl -s -X POST "http://localhost:8000/date/calc" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "difference",
    "start_date": "2026-11-01",
    "end_date": "2026-11-30"
  }'

# Safe month-end rollover (e.g. Jan 31 + 1 month = Feb 28/29)
curl -s -X POST "http://localhost:8000/date/calc" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "add",
    "start_date": "2026-01-31",
    "months": 1
  }'
```

---

### 2. Weather & Forecasts

#### `POST /weather/current`
Get live weather conditions with WMO interpretation and compass directions:
```bash
curl -s -X POST "http://localhost:8000/weather/current" \
  -H "Content-Type: application/json" \
  -d '{"location": "Tokyo", "temperature_unit": "celsius"}'
```
Response:
```json
{
  "location": {
    "name": "Tokyo",
    "latitude": 35.6895,
    "longitude": 139.6917,
    "country": "Japan"
  },
  "current": {
    "temperature": 19.4,
    "apparent_temperature": 18.2,
    "relative_humidity": 60,
    "weather_code": 1,
    "weather_description": "Mainly clear",
    "wind_speed": 12.5,
    "wind_direction_compass": "NE",
    "pressure_msl": 1016.4
  },
  "units": {
    "temperature": "°C",
    "wind_speed": "km/h",
    "pressure": "hPa"
  },
  "source": "Open-Meteo.com",
  "attribution": "Weather data by Open-Meteo.com (non-commercial free tier). For commercial use, a paid license is required."
}
```

#### `POST /weather/forecast`
Get up to 16 days of daily forecasts, plain-language summary, and lunar phases:
```bash
curl -s -X POST "http://localhost:8000/weather/forecast" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Paris",
    "forecast_days": 7,
    "include_astronomy": true
  }'
```

#### `POST /weather/air-quality`
Get AQI, PM2.5, PM10, UV index, and health tips:
```bash
curl -s -X POST "http://localhost:8000/weather/air-quality" \
  -H "Content-Type: application/json" \
  -d '{"location": "London"}'
```

#### `POST /weather/advice`
Get actionable lifestyle guidance:
```bash
curl -s -X POST "http://localhost:8000/weather/advice" \
  -H "Content-Type: application/json" \
  -d '{"location": "Berlin"}'
```
Response:
```json
{
  "location": {"name": "Berlin", "country": "Germany"},
  "comfort_score": 8,
  "summary": "In Berlin, conditions are mainly clear at 18.5°C (17.2°C feels like). No umbrella needed. Wear light jacket. Overall comfort rating: 8/10.",
  "advice": {
    "umbrella": {"needed": false, "reason": "No precipitation detected."},
    "jacket": {"type": "light", "reason": "Mild weather (17.2°C feels like). A light jacket is suitable."},
    "sunscreen": {"needed": true, "reason": "UV index is 4.0 (moderate). Apply SPF 30+."},
    "heat_risk": {"level": "none", "reason": "Temperatures are within comfortable thermal limits."},
    "wind_warning": {"warning": false, "reason": "Wind is calm to moderate (14.0 km/h)."}
  }
}
```

---

### 3. Safe Math & Finance Calculator

#### `POST /calc`
Sandboxed mathematical evaluation (powers `^`, trigonometry, logarithms, factorials):
```bash
curl -s -X POST "http://localhost:8000/calc" \
  -H "Content-Type: application/json" \
  -d '{"expression": "2^10 + sqrt(144) * sin(pi / 2)"}'
```
Response:
```json
{
  "expression": "2^10 + sqrt(144) * sin(pi / 2)",
  "result": 1036,
  "formatted": "1036"
}
```

#### `POST /calc/finance`
Commercial math operations:
```bash
# Discount calculation with sales tax
curl -s -X POST "http://localhost:8000/calc/finance" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "discount",
    "original_price": 120,
    "discount_percent": 25,
    "tax_percent": 8.5
  }'

# Loan EMI calculation
curl -s -X POST "http://localhost:8000/calc/finance" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "emi",
    "principal": 50000,
    "rate_annual_percent": 7.5,
    "tenure_months": 60
  }'
```

---

### 4. Unit Conversion

#### `POST /convert`
Convert between measurement units:
```bash
# Temperature offset conversion
curl -s -X POST "http://localhost:8000/convert" \
  -H "Content-Type: application/json" \
  -d '{"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}'

# Digital byte conversion (MB vs MiB)
curl -s -X POST "http://localhost:8000/convert" \
  -H "Content-Type: application/json" \
  -d '{"value": 1, "from_unit": "MB", "to_unit": "MiB"}'
```

---

### 5. Currency Exchange

#### `POST /currency`
Convert an amount to up to 10 currencies using ECB reference rates:
```bash
curl -s -X POST "http://localhost:8000/currency" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 250,
    "from_currency": "USD",
    "to_currencies": ["EUR", "GBP", "JPY"]
  }'
```

#### `POST /currency/trend`
Analyze 7 or 30-day historical currency movements:
```bash
curl -s -X POST "http://localhost:8000/currency/trend" \
  -H "Content-Type: application/json" \
  -d '{"from_currency": "USD", "to_currency": "EUR", "days": 30}'
```

---

### 6. Health & Resource Inspection

#### `GET /health`
Inspect server uptime, Open-Meteo call budget, and cache hit metrics:
```bash
curl -s "http://localhost:8000/health"
```
Response:
```json
{
  "status": "healthy",
  "service": "time-weather-utilities",
  "version": "1.0.0",
  "uptime_seconds": 1245.8,
  "open_meteo_budget": {
    "utc_date": "2026-10-24",
    "calls_used": 142,
    "warn_limit": 8000,
    "block_limit": 9500,
    "remaining_calls": 9358
  },
  "cache_stats": {
    "geocoding": {"current_size": 18, "max_size": 2000, "ttl_seconds": 86400},
    "weather": {"current_size": 25, "max_size": 2000, "ttl_seconds": 600}
  },
  "attribution_notice": "Weather data by Open-Meteo.com (non-commercial free tier). For commercial use, a paid license is required."
}
```

---

## Function Calling Tool Manifest

The plugin provides a ready-to-use function calling tool manifest in [`tools_manifest.json`](tools_manifest.json). This manifest defines JSON schemas for all 13 AI assistant tool calls compatible with OpenAI and Anthropic tool calling formats.

---

## Testing

The project includes an end-to-end automated test suite using `pytest`, `pytest-asyncio`, and `respx` to mock external HTTP endpoints.

```bash
# Run the entire test suite
pytest -v
```

All 52 tests verify:
- IANA timezone evaluation, formatting, and city aliases
- DST autumn fold ambiguity and spring forward gap warnings
- Date difference, business day steps, and month-end rolling math
- Open-Meteo geocoding, coordinates parsing, and current conditions
- Forecast generation, hourly data arrays, and moon phases
- Air quality categorization and pollen exposure alerts
- AST calculator sandboxing, domain error handling, and exponent guards
- Commercial finance computations (EMI, taxes, tip splits, interest)
- Temperature offset and byte storage conversions
- ECB currency exchange and 30-day trend analytics
- Sliding-window rate limiting (60 req/min) and Open-Meteo budget blocking (HTTP 503)
