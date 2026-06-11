from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Literal

import httpx

from app.models.schemas import Coordinates, WeatherBlock, WeatherDaily

logger = logging.getLogger(__name__)

WeatherSource = Literal["forecast", "historical"]
TimeBlockName = Literal["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]

# WMO weather interpretation codes -> (human text, severity rank). A higher
# severity wins when several different conditions occur within one time block,
# so a thunderstorm hour is never hidden behind a "partly cloudy" average.
WMO_CODES: dict[int, tuple[str, int]] = {
    0: ("Clear sky", 0),
    1: ("Mainly clear", 1),
    2: ("Partly cloudy", 2),
    3: ("Overcast", 3),
    45: ("Fog", 5),
    48: ("Rime fog", 5),
    51: ("Light drizzle", 6),
    53: ("Moderate drizzle", 7),
    55: ("Dense drizzle", 8),
    56: ("Light freezing drizzle", 8),
    57: ("Dense freezing drizzle", 9),
    61: ("Slight rain", 10),
    63: ("Moderate rain", 12),
    65: ("Heavy rain", 14),
    66: ("Light freezing rain", 13),
    67: ("Heavy freezing rain", 15),
    71: ("Slight snow", 10),
    73: ("Moderate snow", 12),
    75: ("Heavy snow", 14),
    77: ("Snow grains", 9),
    80: ("Slight rain showers", 11),
    81: ("Moderate rain showers", 13),
    82: ("Violent rain showers", 16),
    85: ("Slight snow showers", 11),
    86: ("Heavy snow showers", 14),
    95: ("Thunderstorm", 20),
    96: ("Thunderstorm with hail", 22),
    99: ("Thunderstorm with heavy hail", 24),
}

# Local-time hour buckets that line up with the scheduler's activity time blocks.
BLOCK_HOURS: dict[TimeBlockName, set[int]] = {
    "MORNING": {6, 7, 8, 9, 10},
    "NOON": {11, 12, 13},
    "AFTERNOON": {14, 15, 16, 17},
    "EVENING": {18, 19, 20, 21},
    "NIGHT": {0, 1, 2, 3, 4, 5, 22, 23},
}
BLOCK_ORDER: list[TimeBlockName] = ["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]


class OpenMeteoWeatherProvider:
    """Fetches per-day, per-time-block weather from the free Open-Meteo APIs.

    Dates inside the forecast horizon use the live forecast endpoint; dates
    beyond it fall back to the same calendar dates from the previous year via
    the historical archive endpoint. A single trip can mix both.
    """

    def __init__(
        self,
        forecast_base_url: str,
        archive_base_url: str,
        forecast_max_days: int,
    ):
        self.forecast_base_url = forecast_base_url
        self.archive_base_url = archive_base_url
        self.forecast_max_days = forecast_max_days

    async def get_weather(
        self,
        coordinates: Coordinates,
        start_date: date,
        end_date: date,
        today: date,
    ) -> list[WeatherDaily]:
        trip_dates = _inclusive_dates(start_date, end_date)
        forecast_horizon = today + timedelta(days=self.forecast_max_days)
        forecast_dates = [d for d in trip_dates if today <= d <= forecast_horizon]
        historical_dates = [d for d in trip_dates if d not in forecast_dates]

        result: dict[date, WeatherDaily] = {}

        # The forecast and historical segments are fetched independently so that a
        # failure in one (e.g. a date just past the provider's allowed window) still
        # lets the other segment's days through instead of losing all weather.
        if forecast_dates:
            try:
                by_date = await self._fetch_buckets(
                    self.forecast_base_url,
                    coordinates,
                    forecast_dates[0],
                    forecast_dates[-1],
                    include_probability=True,
                )
                for trip_date in forecast_dates:
                    records = by_date.get(trip_date)
                    if records:
                        result[trip_date] = _build_daily(trip_date, "forecast", None, records)
            except Exception as error:
                logger.warning(
                    "Open-Meteo forecast segment failed start=%s end=%s error=%s",
                    forecast_dates[0],
                    forecast_dates[-1],
                    error,
                )

        if historical_dates:
            reference_map = {d: _prior_year(d) for d in historical_dates}
            references = sorted(reference_map.values())
            try:
                by_date = await self._fetch_buckets(
                    self.archive_base_url,
                    coordinates,
                    references[0],
                    references[-1],
                    include_probability=False,
                )
                for trip_date in historical_dates:
                    reference_date = reference_map[trip_date]
                    records = by_date.get(reference_date)
                    if records:
                        result[trip_date] = _build_daily(
                            trip_date, "historical", reference_date, records
                        )
            except Exception as error:
                logger.warning(
                    "Open-Meteo historical segment failed start=%s end=%s error=%s",
                    references[0],
                    references[-1],
                    error,
                )

        return [result[d] for d in trip_dates if d in result]

    async def _fetch_buckets(
        self,
        base_url: str,
        coordinates: Coordinates,
        range_start: date,
        range_end: date,
        include_probability: bool,
    ) -> dict[date, list[dict[str, Any]]]:
        hourly_vars = ["temperature_2m", "precipitation", "weather_code"]
        if include_probability:
            hourly_vars.append("precipitation_probability")

        params: dict[str, Any] = {
            "latitude": coordinates.lat,
            "longitude": coordinates.lon,
            "start_date": range_start.isoformat(),
            "end_date": range_end.isoformat(),
            "hourly": ",".join(hourly_vars),
            "timezone": "auto",
        }
        logger.info(
            "Fetching Open-Meteo weather base_url=%s start=%s end=%s probability=%s",
            base_url,
            range_start,
            range_end,
            include_probability,
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(base_url, params=params)
            logger.info(
                "Open-Meteo response status=%s response_bytes=%s",
                response.status_code,
                len(response.content),
            )
            if response.status_code >= 400:
                logger.warning(
                    "Open-Meteo error status=%s body=%r",
                    response.status_code,
                    response.text[:1000],
                )
            response.raise_for_status()
            payload = response.json()

        return _bucket_hourly(payload.get("hourly") or {})


def _inclusive_dates(start_date: date, end_date: date) -> list[date]:
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _prior_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        # Feb 29 in a non-leap reference year -> clamp to Feb 28.
        return value.replace(year=value.year - 1, day=28)


def _bucket_hourly(hourly: dict[str, Any]) -> dict[date, list[dict[str, Any]]]:
    times = hourly.get("time") or []
    temperatures = hourly.get("temperature_2m") or []
    precipitations = hourly.get("precipitation") or []
    codes = hourly.get("weather_code") or []
    probabilities = hourly.get("precipitation_probability") or []

    buckets: dict[date, list[dict[str, Any]]] = {}
    for index, timestamp in enumerate(times):
        day = date.fromisoformat(timestamp[:10])
        hour = int(timestamp[11:13])
        buckets.setdefault(day, []).append(
            {
                "hour": hour,
                "temperature": _at(temperatures, index),
                "precipitation": _at(precipitations, index) or 0.0,
                "code": _at(codes, index),
                "probability": _at(probabilities, index),
            }
        )
    return buckets


def _at(values: list[Any], index: int) -> Any:
    return values[index] if index < len(values) else None


def _build_daily(
    trip_date: date,
    source: WeatherSource,
    reference_date: date | None,
    records: list[dict[str, Any]],
) -> WeatherDaily:
    blocks = []
    for block_name in BLOCK_ORDER:
        block_records = [r for r in records if r["hour"] in BLOCK_HOURS[block_name]]
        block = _build_block(block_name, block_records)
        if block is not None:
            blocks.append(block)

    temps = [r["temperature"] for r in records if r["temperature"] is not None]
    probs = [r["probability"] for r in records if r["probability"] is not None]
    temp_min = round(min(temps), 1) if temps else None
    temp_max = round(max(temps), 1) if temps else None
    prob_max = int(max(probs)) if probs else None

    worst_text, _ = _worst_condition(records)
    summary_parts = [worst_text]
    if temp_min is not None and temp_max is not None:
        summary_parts.append(f"{temp_min:.0f}-{temp_max:.0f}°C")
    if source == "historical" and reference_date is not None:
        summary_parts.append(f"typical for the season (based on {reference_date.isoformat()})")
    summary = ", ".join(summary_parts)

    return WeatherDaily(
        date=trip_date,
        source=source,
        referenceDate=reference_date,
        summary=summary,
        tempMinC=temp_min,
        tempMaxC=temp_max,
        precipitationProbabilityMax=prob_max,
        blocks=blocks,
    )


def _build_block(block_name: TimeBlockName, records: list[dict[str, Any]]) -> WeatherBlock | None:
    if not records:
        return None
    condition, _ = _worst_condition(records)
    temps = [r["temperature"] for r in records if r["temperature"] is not None]
    temperature = round(sum(temps) / len(temps), 1) if temps else None
    precipitation = round(sum(r["precipitation"] for r in records), 1)
    return WeatherBlock(
        timeBlock=block_name,
        condition=condition,
        temperatureC=temperature,
        precipitationMm=precipitation,
    )


def _worst_condition(records: list[dict[str, Any]]) -> tuple[str, int]:
    worst_text = "Unknown"
    worst_severity = -1
    for record in records:
        text, severity = _wmo(record["code"])
        if severity > worst_severity:
            worst_severity = severity
            worst_text = text
    return worst_text, worst_severity


def _wmo(code: Any) -> tuple[str, int]:
    if code is None:
        return ("Unknown", 0)
    return WMO_CODES.get(int(code), ("Unknown", 0))
