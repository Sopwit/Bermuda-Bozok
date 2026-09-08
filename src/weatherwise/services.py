"""
Business logic for weather access, ML predictions, planning, and user-facing recommendations.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import joblib
import numpy as np
import requests
from fastapi import HTTPException

from weatherwise.config import get_settings

__all__ = [
    "activity_recommendation",
    "assess_confidence",
    "build_activity_windows",
    "build_headline",
    "build_outfit_plan",
    "build_reason",
    "close_async_client",
    "dependencies_status",
    "fetch_air_quality_data",
    "fetch_all_weather_data_async",
    "fetch_daily_forecast",
    "fetch_forecast_data",
    "fetch_weather_data",
    "find_best_time_window",
    "format_coordinate_location",
    "generate_llm_advice",
    "generate_llm_advice_async",
    "geocode_city",
    "geocode_city_async",
    "get_async_client",
    "model_assets_available",
    "predict_ml_decisions",
    "search_city_suggestions",
    "search_city_suggestions_async",
    "summarize_advice",
]

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

_ASYNC_CLIENT: httpx.AsyncClient | None = None


def get_async_client() -> httpx.AsyncClient:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is None or _ASYNC_CLIENT.is_closed:
        settings = get_settings()
        limits = httpx.Limits(max_keepalive_connections=30, max_connections=100)
        _ASYNC_CLIENT = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            limits=limits,
            http2=True,
        )
    return _ASYNC_CLIENT


async def close_async_client() -> None:
    global _ASYNC_CLIENT
    if _ASYNC_CLIENT is not None and not _ASYNC_CLIENT.is_closed:
        await _ASYNC_CLIENT.aclose()
        _ASYNC_CLIENT = None


@lru_cache(maxsize=1)
def load_model_assets() -> dict[str, Any]:
    model_umbrella = joblib.load(MODELS_DIR / "model_umbrella.joblib")
    model_clothing = joblib.load(MODELS_DIR / "model_clothing.joblib")
    label_encoder_clothing = joblib.load(MODELS_DIR / "label_encoder_clothing.joblib")
    model_features = joblib.load(MODELS_DIR / "model_features.joblib")

    feature_idx = {name: i for i, name in enumerate(model_features)}

    booster_umb = getattr(model_umbrella, "get_booster", lambda: None)()
    booster_cloth = getattr(model_clothing, "get_booster", lambda: None)()

    return {
        "model_umbrella": model_umbrella,
        "model_clothing": model_clothing,
        "label_encoder_clothing": label_encoder_clothing,
        "model_features": model_features,
        "feature_idx": feature_idx,
        "num_features": len(model_features),
        "clothing_classes": list(label_encoder_clothing.classes_),
        "booster_umb": booster_umb,
        "booster_cloth": booster_cloth,
    }


def model_assets_available() -> bool:
    required_files = [
        MODELS_DIR / "model_umbrella.joblib",
        MODELS_DIR / "model_clothing.joblib",
        MODELS_DIR / "label_encoder_clothing.joblib",
        MODELS_DIR / "model_features.joblib",
    ]
    return all(path.exists() for path in required_files)


def format_coordinate_location(latitude: float | None, longitude: float | None) -> str:
    if latitude is None or longitude is None:
        return "Unknown location"
    return f"{latitude:.4f}, {longitude:.4f}"


def dependencies_status() -> dict[str, str]:
    settings = get_settings()
    return {
        "open_meteo": "configured (no key required)",
        "huggingface": "configured" if settings.hf_api_key else "missing",
    }


def get_season(month: int | None = None) -> str:
    if month is None:
        month = datetime.now().month
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def map_wmo_code(wmo_code: int) -> str:
    if wmo_code == 0:
        return "clear"
    if wmo_code in (1, 2, 3, 45, 48):
        return "clouds"
    if wmo_code in (51, 53, 55, 56, 57):
        return "drizzle"
    if wmo_code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if wmo_code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if wmo_code in (95, 96, 99):
        return "thunderstorm"
    return "clouds"


# ── Network helpers ─────────────────────────────────────────────────────────


async def _async_get_json(url: str, *, params: dict) -> dict:
    client = get_async_client()
    try:
        response = await client.get(url, params=params)
    except httpx.RequestError as exc:
        logger.exception("External weather request failed: %s", url)
        raise HTTPException(
            status_code=502,
            detail="Weather service is currently unavailable.",
        ) from exc

    if response.status_code == 404:
        city_name = params.get("name") or "the requested location"
        raise HTTPException(
            status_code=404,
            detail=f"'{city_name}' is not a valid city. Please check the spelling.",
        )

    if response.status_code != 200:
        logger.error("Weather service returned %s: %s", response.status_code, response.text)
        raise HTTPException(
            status_code=502,
            detail="Weather service is currently unavailable.",
        )

    return response.json()


def _get_json(url: str, *, params: dict) -> dict:
    settings = get_settings()
    try:
        response = requests.get(
            url,
            params=params,
            timeout=settings.request_timeout_seconds,
        )
    except requests.RequestException as exc:
        logger.exception("External weather request failed.")
        raise HTTPException(
            status_code=502,
            detail="Weather service is currently unavailable.",
        ) from exc

    if response.status_code == 404:
        city_name = params.get("name") or "the requested location"
        raise HTTPException(
            status_code=404,
            detail=f"'{city_name}' is not a valid city. Please check the spelling.",
        )

    if response.status_code != 200:
        logger.error("Weather service returned %s: %s", response.status_code, response.text)
        raise HTTPException(
            status_code=502,
            detail="Weather service is currently unavailable.",
        )

    return response.json()


# ── Geocoding ───────────────────────────────────────────────────────────────


@lru_cache(maxsize=512)
def geocode_city(city: str) -> dict:
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_data = _get_json(
        geo_url,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
    )

    if not geo_data.get("results"):
        raise HTTPException(
            status_code=404,
            detail=f"'{city}' is not a valid city. Please check the spelling.",
        )

    return geo_data["results"][0]


async def geocode_city_async(city: str) -> dict:
    cleaned = city.strip()
    try:
        return geocode_city(cleaned)
    except HTTPException:
        raise
    except Exception:
        pass

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_data = await _async_get_json(
        geo_url,
        params={"name": cleaned, "count": 1, "language": "en", "format": "json"},
    )

    if not geo_data.get("results"):
        raise HTTPException(
            status_code=404,
            detail=f"'{cleaned}' is not a valid city. Please check the spelling.",
        )

    return geo_data["results"][0]


def _format_city_result(item: dict) -> dict:
    name = item.get("name", "")
    country = item.get("country")
    admin1 = item.get("admin1")
    admin2 = item.get("admin2")
    latitude = float(item["latitude"])
    longitude = float(item["longitude"])

    parts = [name]
    if admin1 and admin1.lower() != name.lower():
        parts.append(admin1)
    if country:
        parts.append(country)

    return {
        "name": name,
        "country": country,
        "admin1": admin1,
        "admin2": admin2,
        "latitude": latitude,
        "longitude": longitude,
        "display_name": ", ".join(parts),
    }


def search_city_suggestions(query: str, limit: int = 8) -> list[dict]:
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_data = _get_json(
        geo_url,
        params={
            "name": cleaned,
            "count": limit,
            "language": "en",
            "format": "json",
        },
    )

    results = geo_data.get("results", [])
    if not results:
        return []

    seen: set[tuple[str, str | None, str | None]] = set()
    suggestions: list[dict] = []

    for item in results:
        key = (
            item.get("name", "").strip().lower(),
            (item.get("admin1") or "").strip().lower() or None,
            (item.get("country") or "").strip().lower() or None,
        )
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(_format_city_result(item))

    return suggestions[:limit]


async def search_city_suggestions_async(query: str, limit: int = 8) -> list[dict]:
    cleaned = query.strip()
    if len(cleaned) < 2:
        return []

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_data = await _async_get_json(
        geo_url,
        params={
            "name": cleaned,
            "count": limit,
            "language": "en",
            "format": "json",
        },
    )

    results = geo_data.get("results", [])
    if not results:
        return []

    seen: set[tuple[str, str | None, str | None]] = set()
    suggestions: list[dict] = []

    for item in results:
        key = (
            item.get("name", "").strip().lower(),
            (item.get("admin1") or "").strip().lower() or None,
            (item.get("country") or "").strip().lower() or None,
        )
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(_format_city_result(item))

    return suggestions[:limit]


# ── Weather Payloads & Parsers ──────────────────────────────────────────────


def _build_forecast_params(lat: float, lon: float) -> dict[str, Any]:
    return {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
            "wind_direction_10m,cloud_cover,visibility,uv_index"
        ),
        "hourly": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
            "wind_direction_10m,cloud_cover,visibility,uv_index"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max,uv_index_max,"
            "sunshine_duration,wind_gusts_10m_max,sunrise,sunset"
        ),
        "timezone": "auto",
        "forecast_days": 7,
    }


def _build_aq_params(lat: float, lon: float) -> dict[str, Any]:
    return {
        "latitude": lat,
        "longitude": lon,
        "current": "european_aqi,pm2_5,pm10",
        "timezone": "auto",
    }


def _parse_live_weather(w_data: dict, air_quality: dict) -> dict:
    current = w_data["current"]
    daily = w_data.get("daily", {})

    sunrise_local = None
    sunset_local = None

    if daily.get("sunrise") and len(daily["sunrise"]) > 0:
        sunrise_local = daily["sunrise"][0][-5:]
    if daily.get("sunset") and len(daily["sunset"]) > 0:
        sunset_local = daily["sunset"][0][-5:]

    return {
        "temperature_c": float(current["temperature_2m"]),
        "feels_like_c": float(current["apparent_temperature"]),
        "precipitation_mm": float(current["precipitation"]),
        "wind_speed_kmh": float(current["wind_speed_10m"]),
        "wind_gust_kmh": float(current.get("wind_gusts_10m")) if current.get("wind_gusts_10m") is not None else None,
        "humidity_pct": int(current["relative_humidity_2m"]),
        "wind_direction_deg": (
            float(current["wind_direction_10m"]) if current.get("wind_direction_10m") is not None else None
        ),
        "cloud_cover_pct": int(current["cloud_cover"]) if current.get("cloud_cover") is not None else None,
        "visibility_km": (
            round(float(current["visibility"]) / 1000, 1) if current.get("visibility") is not None else None
        ),
        "uv_index": float(current.get("uv_index")) if current.get("uv_index") is not None else None,
        "european_aqi": air_quality.get("european_aqi"),
        "pm2_5_ugm3": air_quality.get("pm2_5_ugm3"),
        "pm10_ugm3": air_quality.get("pm10_ugm3"),
        "sunrise_local": sunrise_local,
        "sunset_local": sunset_local,
        "weather_condition": map_wmo_code(current["weather_code"]),
        "season": get_season(),
    }


def _parse_hourly_forecast(f_data: dict) -> list[dict]:
    hourly = f_data["hourly"]
    times = hourly["time"]
    n = len(times)
    entries: list[dict] = []

    for i in range(n):
        timestamp = datetime.fromisoformat(times[i])
        entries.append(
            {
                "time_label": timestamp.strftime("%H:%M"),
                "temperature_c": float(hourly["temperature_2m"][i]),
                "feels_like_c": float(hourly["apparent_temperature"][i]),
                "precipitation_mm": float(hourly["precipitation"][i]),
                "wind_speed_kmh": float(hourly["wind_speed_10m"][i]),
                "wind_gust_kmh": float(hourly["wind_gusts_10m"][i]) if hourly.get("wind_gusts_10m") else None,
                "humidity_pct": int(hourly["relative_humidity_2m"][i]),
                "wind_direction_deg": (
                    float(hourly["wind_direction_10m"][i]) if hourly.get("wind_direction_10m") else None
                ),
                "cloud_cover_pct": int(hourly["cloud_cover"][i]) if hourly.get("cloud_cover") else None,
                "visibility_km": round(float(hourly["visibility"][i]) / 1000, 1) if hourly.get("visibility") else None,
                "uv_index": float(hourly["uv_index"][i]) if hourly.get("uv_index") else None,
                "european_aqi": None,
                "pm2_5_ugm3": None,
                "pm10_ugm3": None,
                "sunrise_local": None,
                "sunset_local": None,
                "weather_condition": map_wmo_code(hourly["weather_code"][i]),
                "season": get_season(timestamp.month),
            }
        )

    current_time_str = f_data.get("current", {}).get("time")
    if current_time_str:
        current_dt = datetime.fromisoformat(current_time_str)
        cutoff = current_dt.replace(minute=0, second=0, microsecond=0)
    else:
        now = datetime.now()
        cutoff = now.replace(minute=0, second=0, microsecond=0)

    upcoming = [
        entry
        for entry, raw_time in zip(entries, times)
        if datetime.fromisoformat(raw_time) >= cutoff
    ]

    if len(upcoming) >= 24:
        return upcoming[:24]

    return entries[:24]


def _parse_daily_forecast(d_data: dict) -> list[dict]:
    daily = d_data["daily"]
    items: list[dict] = []

    for i in range(len(daily["time"])):
        prob_max = daily.get("precipitation_probability_max")
        prob_val = int(prob_max[i]) if prob_max and prob_max[i] is not None else None

        uv_max = daily.get("uv_index_max")
        uv_val = float(uv_max[i]) if uv_max and uv_max[i] is not None else None

        sun_dur = daily.get("sunshine_duration")
        sun_val = round(float(sun_dur[i]) / 3600, 1) if sun_dur and sun_dur[i] is not None else None

        gust_max = daily.get("wind_gusts_10m_max")
        gust_val = float(gust_max[i]) if gust_max and gust_max[i] is not None else None

        sunrise_val = daily["sunrise"][i][-5:] if daily.get("sunrise") and daily["sunrise"][i] else None
        sunset_val = daily["sunset"][i][-5:] if daily.get("sunset") and daily["sunset"][i] else None

        items.append(
            {
                "date": daily["time"][i],
                "label": "Today" if i == 0 else datetime.fromisoformat(daily["time"][i]).strftime("%a"),
                "weather_condition": map_wmo_code(daily["weather_code"][i]),
                "temperature_high_c": float(daily["temperature_2m_max"][i]),
                "temperature_low_c": float(daily["temperature_2m_min"][i]),
                "precipitation_total_mm": float(daily["precipitation_sum"][i]),
                "precipitation_probability_max_pct": prob_val,
                "uv_index_max": uv_val,
                "sunshine_duration_hours": sun_val,
                "wind_gust_max_kmh": gust_val,
                "sunrise_local": sunrise_val,
                "sunset_local": sunset_val,
            }
        )

    return items


def _parse_air_quality(aq_data: dict) -> dict:
    current = aq_data.get("current", {})
    return {
        "european_aqi": int(current["european_aqi"]) if current.get("european_aqi") is not None else None,
        "pm2_5_ugm3": float(current["pm2_5"]) if current.get("pm2_5") is not None else None,
        "pm10_ugm3": float(current["pm10"]) if current.get("pm10") is not None else None,
    }


# ── High-Performance Parallel Fetchers ──────────────────────────────────────


async def fetch_all_weather_data_async(lat: float, lon: float) -> tuple[dict, list[dict], list[dict]]:
    """
    Fetches full forecast (current + hourly + daily) and air quality in parallel via HTTP/2 keep-alive.
    Reduces 4 sequential round trips to 1 single parallel round trip.
    """
    forecast_url = "https://api.open-meteo.com/v1/forecast"
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

    forecast_params = _build_forecast_params(lat, lon)
    aq_params = _build_aq_params(lat, lon)

    try:
        res_forecast, res_aq = await asyncio.gather(
            _async_get_json(forecast_url, params=forecast_params),
            _async_get_json(aq_url, params=aq_params),
            return_exceptions=True,
        )
    except Exception as exc:
        logger.exception("Failed to fetch weather data in parallel")
        raise HTTPException(status_code=502, detail="Weather service is currently unavailable.") from exc

    if isinstance(res_forecast, Exception):
        if isinstance(res_forecast, HTTPException):
            raise res_forecast
        raise HTTPException(status_code=502, detail="Weather service is currently unavailable.") from res_forecast

    aq_data = res_aq if isinstance(res_aq, dict) else {}
    air_quality = _parse_air_quality(aq_data)

    live_weather = _parse_live_weather(res_forecast, air_quality)
    hourly_forecast = _parse_hourly_forecast(res_forecast)
    daily_forecast = _parse_daily_forecast(res_forecast)

    return live_weather, hourly_forecast, daily_forecast


def fetch_air_quality_data(lat: float, lon: float) -> dict:
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_data = _get_json(aq_url, params=_build_aq_params(lat, lon))
    return _parse_air_quality(aq_data)


def fetch_weather_data(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    weather_url = "https://api.open-meteo.com/v1/forecast"
    w_data = _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
                "wind_direction_10m,cloud_cover,visibility,uv_index"
            ),
            "daily": "sunrise,sunset",
            "timezone": "auto",
            "forecast_days": 1,
        },
    )
    air_quality = fetch_air_quality_data(lat, lon)
    return _parse_live_weather(w_data, air_quality)


def fetch_forecast_data(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict]:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    weather_url = "https://api.open-meteo.com/v1/forecast"
    f_data = _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "time",
            "hourly": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
                "wind_direction_10m,cloud_cover,visibility,uv_index"
            ),
            "timezone": "auto",
            "forecast_days": 2,
        },
    )
    return _parse_hourly_forecast(f_data)


def fetch_daily_forecast(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict]:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    weather_url = "https://api.open-meteo.com/v1/forecast"
    d_data = _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,uv_index_max,"
                "sunshine_duration,wind_gusts_10m_max,sunrise,sunset"
            ),
            "timezone": "auto",
            "forecast_days": 7,
        },
    )
    return _parse_daily_forecast(d_data)


# ── Sub-Millisecond ML Inference ────────────────────────────────────────────


def predict_ml_decisions(weather_dict: dict) -> tuple[bool, str, str]:
    """
    Sub-millisecond XGBoost inference using pre-compiled feature index array mapping.
    Avoids 20ms pandas DataFrame overhead per call.
    """
    assets = load_model_assets()
    feature_idx = assets["feature_idx"]
    num_features = assets["num_features"]

    arr = np.zeros((1, num_features), dtype=np.float32)

    # Numerical features mapping
    for k, v in weather_dict.items():
        if k in feature_idx and isinstance(v, (int, float)):
            arr[0, feature_idx[k]] = float(v)

    # Categorical dummy features mapping
    season = weather_dict.get("season")
    if season:
        col = f"season_{season}"
        if col in feature_idx:
            arr[0, feature_idx[col]] = 1.0

    cond = weather_dict.get("weather_condition")
    if cond:
        col = f"weather_condition_{cond}"
        if col in feature_idx:
            arr[0, feature_idx[col]] = 1.0
        elif cond == "clouds":
            col = "weather_condition_cloudy"
            if col in feature_idx:
                arr[0, feature_idx[col]] = 1.0

    booster_umb = assets["booster_umb"]
    booster_cloth = assets["booster_cloth"]

    if booster_umb is not None and booster_cloth is not None:
        prob_umb = booster_umb.inplace_predict(arr)[0]
        pred_umb = prob_umb > 0.5
        probs_cloth = booster_cloth.inplace_predict(arr)[0]
        pred_cloth_idx = int(np.argmax(probs_cloth))
        clothing_text = assets["clothing_classes"][pred_cloth_idx]
    else:
        pred_umb = assets["model_umbrella"].predict(arr)[0]
        pred_cloth_idx = assets["model_clothing"].predict(arr)[0]
        clothing_text = assets["label_encoder_clothing"].inverse_transform([pred_cloth_idx])[0]

    umbrella_needed = bool(pred_umb)

    if (
        weather_dict.get("precipitation_mm", 0) > 0
        or weather_dict.get("weather_condition") in {"rain", "drizzle", "thunderstorm"}
    ):
        umbrella_needed = True

    umbrella_text = "Yes" if umbrella_needed else "No"
    return umbrella_needed, umbrella_text, str(clothing_text)


# ── Decision & Copy Builders ────────────────────────────────────────────────


def build_headline(weather_dict: dict, clothing_text: str, umbrella_needed: bool, language: str) -> str:
    clean_clothing = clothing_text.replace("_", " ")

    if language == "tr":
        if umbrella_needed:
            return f"Yağış ihtimali var. {clean_clothing} giy ve şemsiye al."
        return f"Hava sakin görünüyor. {clean_clothing} yeterli olacaktır."

    if umbrella_needed:
        return f"Rain-ready weather. Wear {clean_clothing} and bring an umbrella."
    return f"Comfortable conditions. {clean_clothing} should be enough."


def build_reason(weather_dict: dict) -> str:
    reasons: list[str] = []

    precip = weather_dict.get("precipitation_mm", 0.0)
    cond = weather_dict.get("weather_condition", "")
    wind = weather_dict.get("wind_speed_kmh", 0.0)
    temp = weather_dict.get("temperature_c", 20.0)

    if precip > 0:
        reasons.append("rain is already present")
    elif cond in {"rain", "drizzle", "thunderstorm"}:
        reasons.append("wet conditions are expected")

    if wind >= 20:
        reasons.append("wind is strong")
    elif wind <= 10:
        reasons.append("wind is light")

    if temp <= 8:
        reasons.append("the air feels cold")
    elif temp >= 24:
        reasons.append("the air feels warm")
    else:
        reasons.append("the temperature is comfortable")

    return ", ".join(reasons[:3]).capitalize() + "."


def assess_confidence(weather_dict: dict) -> str:
    precip = weather_dict.get("precipitation_mm", 0.0)
    wind = weather_dict.get("wind_speed_kmh", 0.0)
    cond = weather_dict.get("weather_condition", "")

    if precip > 0 or wind > 25:
        return "high"
    if cond in {"mist", "fog", "haze"}:
        return "low"
    return "medium"


def activity_recommendation(activity: str, weather_dict: dict) -> dict:
    rain = weather_dict.get("precipitation_mm", 0.0)
    wind = weather_dict.get("wind_speed_kmh", 0.0)
    temp = weather_dict.get("temperature_c", 20.0)

    if activity == "walking":
        if rain > 0 or wind > 30:
            return {
                "activity": activity,
                "recommendation": "not_recommended",
                "reason": "rain or strong wind makes walking less comfortable",
            }
        if temp < 5:
            return {
                "activity": activity,
                "recommendation": "acceptable",
                "reason": "dry weather is fine but the temperature is cold",
            }
        return {
            "activity": activity,
            "recommendation": "recommended",
            "reason": "dry weather and comfortable wind make walking suitable",
        }

    if activity == "cycling":
        if rain > 0 or wind > 22:
            return {
                "activity": activity,
                "recommendation": "not_recommended",
                "reason": "cycling becomes risky with rain or rising wind",
            }
        return {
            "activity": activity,
            "recommendation": "recommended",
            "reason": "road and wind conditions are reasonable for cycling",
        }

    # outdoor_dining
    if rain > 0:
        return {
            "activity": activity,
            "recommendation": "not_recommended",
            "reason": "rain reduces outdoor comfort",
        }
    if wind > 25:
        return {
            "activity": activity,
            "recommendation": "acceptable",
            "reason": "dry weather is good but wind may reduce comfort",
        }
    return {
        "activity": activity,
        "recommendation": "recommended",
        "reason": "the weather looks calm enough for outdoor dining",
    }


def summarize_advice(
    clothing_text: str,
    umbrella_needed: bool,
    activity_result: dict,
    language: str,
) -> str:
    clean_clothing = clothing_text.replace("_", " ")
    activity_name = activity_result["activity"].replace("_", " ")
    activity_status = activity_result["recommendation"]

    if language == "tr":
        umbrella_part = "Yanına şemsiye al" if umbrella_needed else "Şemsiyeye ihtiyacın yok"
        if activity_status == "recommended":
            activity_part = f"{activity_name} için uygun görünüyor"
        elif activity_status == "acceptable":
            activity_part = f"{activity_name} mümkün ama şartlar orta seviyede"
        else:
            activity_part = f"{activity_name} için ertelemek daha iyi olabilir"

        return f"{clean_clothing} giy. {umbrella_part}, ve {activity_part}."

    umbrella_part = "Take an umbrella with you" if umbrella_needed else "You can leave the umbrella at home"

    if activity_status == "recommended":
        if activity_name == "walking":
            activity_part = "a short walk could be a nice option"
        elif activity_name == "cycling":
            activity_part = "it is a good time for a bike ride"
        else:
            activity_part = f"{activity_name} sounds like a good plan"
    elif activity_status == "acceptable":
        if activity_name == "walking":
            activity_part = "a short walk is still possible, but keep expectations modest"
        elif activity_name == "cycling":
            activity_part = "cycling is possible, but it may not feel ideal"
        else:
            activity_part = f"{activity_name} is possible, but conditions are only fair"
    else:
        if activity_name == "walking":
            activity_part = "it may be better to skip the walk for now"
        elif activity_name == "cycling":
            activity_part = "it is better to avoid cycling right now"
        else:
            activity_part = f"it may be better to postpone {activity_name} for now"

    return f"Wear {clean_clothing}. {umbrella_part}, and {activity_part}."


def build_outfit_plan(clothing_text: str, umbrella_needed: bool, weather_dict: dict) -> dict:
    clean = clothing_text.replace("_", " ").strip().lower()

    layers = [clean.capitalize()] if clean else ["Light layer"]
    accessories: list[str] = []
    footwear = "Regular sneakers"

    if umbrella_needed:
        accessories.append("Umbrella")

    temp = weather_dict.get("temperature_c", 20.0)
    if temp >= 22:
        accessories.append("Sun protection")
    elif temp <= 8:
        accessories.append("Warm layer")

    summary_parts = [f"Start with {layers[0].lower()}"]
    if accessories:
        summary_parts.append(f"and add {', '.join(a.lower() for a in accessories)}")
    summary = " ".join(summary_parts).strip() + f". Finish with {footwear.lower()}."

    return {
        "summary": summary,
        "layers": layers,
        "accessories": accessories or ["No extras needed"],
        "footwear": footwear,
    }


# ── LLM Integration ────────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    text = text.strip()
    return re.sub(r"\s+", " ", text)


def _strip_technical_details(text: str) -> str:
    cleaned = text
    cleaned = re.sub(
        r"\bwith a temperature of [-+]?\d+(\.\d+)? degrees celsius\b[,]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b[-+]?\d+(\.\d+)?\s*(°c|celsius|degrees celsius|degrees)\b[,]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(it's|it is)\s+a\s+(cloudy|rainy|sunny|windy|foggy|snowy|clear)\s+day\s*(with)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(today is|it looks like)\s+(cloudy|rainy|sunny|windy|foggy|snowy|clear)\s*[,.-]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(as|because|since)\s+the\s+(dry weather|light wind|strong wind|temperature|humidity)\s+[^.]*[.]?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"^[,.\-:\s]+", "", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)

    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]

    return cleaned.strip()


def _is_advice_consistent(
    advice: str,
    umbrella_needed: bool,
    clothing_text: str,
    activity_result: dict,
) -> bool:
    advice_lower = advice.lower()
    clean_clothing = clothing_text.replace("_", " ").lower()
    activity_name = activity_result["activity"].replace("_", " ").lower()
    activity_status = activity_result["recommendation"]

    clothing_tokens = [token for token in clean_clothing.split() if len(token) > 2]
    if clothing_tokens and not any(token in advice_lower for token in clothing_tokens):
        return False

    has_umbrella_word = "umbrella" in advice_lower
    says_need_umbrella = any(
        phrase in advice_lower
        for phrase in [
            "bring an umbrella",
            "take an umbrella",
            "carry an umbrella",
            "use an umbrella",
        ]
    )
    says_no_umbrella = any(
        phrase in advice_lower
        for phrase in [
            "do not need an umbrella",
            "don't need an umbrella",
            "no umbrella is needed",
            "umbrella is not needed",
        ]
    )

    if umbrella_needed:
        if has_umbrella_word and says_no_umbrella:
            return False
    else:
        if says_need_umbrella:
            return False

    if activity_status == "not_recommended":
        forbidden = [
            f"{activity_name} looks like a good option",
            f"{activity_name} is recommended",
            f"great time for {activity_name}",
            f"{activity_name} is ideal",
        ]
        if any(phrase in advice_lower for phrase in forbidden):
            return False

    return True


def _build_llm_prompts(
    weather_condition: str,
    temp: float,
    umbrella_text: str,
    clothing_text: str,
    reason: str,
    activity_result: dict,
) -> tuple[str, str]:
    clean_clothing = clothing_text.replace("_", " ")
    umbrella_status = "required" if umbrella_text == "Yes" else "not needed"
    activity_name = activity_result["activity"].replace("_", " ")
    activity_status = activity_result["recommendation"]

    system_prompt = (
        "You are a friendly lifestyle assistant in a weather app. "
        "Write exactly 2 short natural English sentences. "
        "Do not mention numbers, temperature, degrees, humidity, "
        "wind speed, precipitation, or weather condition names. "
        "Do not sound technical or robotic. "
        "Do not repeat the structured data shown elsewhere in the interface. "
        "Focus on helpful everyday guidance. "
        "Always mention what to wear in natural wording. "
        "If umbrella is required, clearly tell the user to bring one. "
        "If umbrella is not needed, clearly say they do not need one. "
        "Make the advice feel varied and human, not repetitive. "
        "Do not always praise the activity. "
        "If the activity status is not_recommended, advise against it naturally. "
        "If the activity status is acceptable, sound cautious. "
        "If the activity status is recommended, keep it light and natural."
    )

    user_prompt = (
        f"Clothing recommendation: {clean_clothing}\n"
        f"Umbrella: {umbrella_status}\n"
        f"Activity: {activity_name}\n"
        f"Activity status: {activity_status}\n"
        f"Reason summary: {reason}\n\n"
        "Write exactly 2 short natural English sentences. "
        "Give practical, human-friendly advice. "
        "Do not mention technical weather details. "
        "Do not use the same template wording every time."
    )

    return system_prompt, user_prompt


async def _call_hf_chat_async(headers: dict, system_prompt: str, user_prompt: str) -> str | None:
    url = "https://router.huggingface.co/v1/chat/completions"
    candidate_models = [
        "meta-llama/Llama-3.1-8B-Instruct:fastest",
        "Qwen/Qwen2.5-7B-Instruct:fastest",
    ]
    client = get_async_client()

    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 100,
            "temperature": 0.2,
        }
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=4.0)
            if response.status_code != 200:
                continue
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content:
                return content
        except Exception:
            logger.debug("HF router request failed for model %s", model_name)

    return None


async def generate_llm_advice_async(
    city: str,
    weather_condition: str,
    temp: float,
    umbrella_text: str,
    clothing_text: str,
    reason: str,
    activity_result: dict,
    language: str,
) -> str:
    settings = get_settings()
    fallback_msg = summarize_advice(
        clothing_text,
        umbrella_text == "Yes",
        activity_result,
        language,
    )

    if not settings.hf_api_key:
        return fallback_msg

    headers = {
        "Authorization": f"Bearer {settings.hf_api_key}",
        "Content-Type": "application/json",
    }

    system_prompt, user_prompt = _build_llm_prompts(
        weather_condition=weather_condition,
        temp=temp,
        umbrella_text=umbrella_text,
        clothing_text=clothing_text,
        reason=reason,
        activity_result=activity_result,
    )

    content = await _call_hf_chat_async(headers, system_prompt, user_prompt)
    if not content:
        return fallback_msg

    content = _normalize_text(content)
    content = content.strip('"').strip("'").strip()
    content = _strip_technical_details(content)

    if not content or not _is_advice_consistent(
        advice=content,
        umbrella_needed=(umbrella_text == "Yes"),
        clothing_text=clothing_text,
        activity_result=activity_result,
    ):
        return fallback_msg

    return content


def generate_llm_advice(
    city: str,
    weather_condition: str,
    temp: float,
    umbrella_text: str,
    clothing_text: str,
    reason: str,
    activity_result: dict,
    language: str,
) -> str:
    """Synchronous version with fallback."""
    settings = get_settings()
    fallback_msg = summarize_advice(
        clothing_text,
        umbrella_text == "Yes",
        activity_result,
        language,
    )

    if not settings.hf_api_key:
        return fallback_msg

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return fallback_msg
        return loop.run_until_complete(
            generate_llm_advice_async(
                city, weather_condition, temp, umbrella_text, clothing_text, reason, activity_result, language
            )
        )
    except Exception:
        return fallback_msg


# ── Planning and Time Windows ──────────────────────────────────────────────


def _hour_from_label(time_label: str) -> int:
    return int(time_label.split(":")[0])


def _window_recommendation(activity: str, entry: dict) -> str:
    rain = entry["precipitation_mm"]
    wind = entry["wind_speed_kmh"]
    temp = entry["temperature_c"]

    if activity == "walking":
        if rain > 2.0 or wind > 40:
            return "not_recommended"
        if rain > 0.5 or wind > 25 or temp < 2 or temp > 35:
            return "acceptable"
        return "recommended"

    if activity == "cycling":
        if rain > 1.0 or wind > 30:
            return "not_recommended"
        if rain > 0.3 or wind > 20 or temp < 5 or temp > 32:
            return "acceptable"
        return "recommended"

    # outdoor dining
    if rain > 0.5 or wind > 25:
        return "not_recommended"
    if rain > 0.1 or wind > 18 or temp < 10 or temp > 35:
        return "acceptable"
    return "recommended"


def _score_activity_entry(activity: str, entry: dict) -> float:
    hour = _hour_from_label(entry["time_label"])
    temp = entry["temperature_c"]
    rain = entry["precipitation_mm"]
    wind = entry["wind_speed_kmh"]
    feels = entry.get("feels_like_c", temp)

    score = 80.0
    score -= min(rain * 45, 38)
    score -= max(wind - 8, 0) * 1.6

    if activity == "walking":
        score -= abs(feels - 18) * 1.1
        if hour < 7 or hour > 22:
            score -= 14
        elif 8 <= hour <= 11:
            score += 8
        elif 17 <= hour <= 20:
            score += 10
        elif 12 <= hour <= 16:
            score += 4

        if wind > 24:
            score -= 10

    elif activity == "cycling":
        score -= abs(feels - 16) * 1.5
        score -= max(wind - 12, 0) * 2.2
        if hour < 6 or hour > 21:
            score -= 18
        elif 7 <= hour <= 10:
            score += 10
        elif 16 <= hour <= 19:
            score += 7
        elif 11 <= hour <= 15:
            score -= 3

        if wind > 18:
            score -= 12

    else:  # outdoor_dining
        score -= abs(feels - 21) * 1.0
        if hour < 10 or hour > 23:
            score -= 18
        elif 12 <= hour <= 15:
            score += 10
        elif 18 <= hour <= 21:
            score += 12
        elif 16 <= hour <= 17:
            score += 5

        if wind > 16:
            score -= 8

    rec = _window_recommendation(activity, entry)
    if rec == "not_recommended":
        score -= 10
    elif rec == "acceptable":
        score -= 4

    return max(0.0, min(100.0, score))


def _window_reason(activity: str, entry: dict, recommendation: str) -> str:
    rain = entry["precipitation_mm"]
    wind = entry["wind_speed_kmh"]
    temp = entry["temperature_c"]

    if recommendation == "not_recommended":
        if rain > 0:
            return "rain makes this window unreliable"
        if wind > 20:
            return "wind makes this window uncomfortable"
        return "conditions are weaker than ideal"

    if recommendation == "acceptable":
        if rain > 0:
            return "light rain risk keeps this window only moderately suitable"
        if wind > 14:
            return "some wind may reduce comfort"
        if temp < 8:
            return "cool air makes this window less comfortable"
        return "conditions are fair but not ideal"

    if activity == "walking":
        return "low rain risk and steady conditions make walking feel suitable"
    if activity == "cycling":
        return "road and wind conditions are reasonable for cycling"
    return "the weather looks calm enough for outdoor dining"


def _window_end(start_label: str) -> str:
    hour = int(start_label.split(":")[0])
    return f"{(hour + 3) % 24:02d}:00"


def find_best_time_window(activity: str, forecast_entries: list[dict]) -> dict:
    if not forecast_entries:
        return {
            "best_time_window": "12:00-15:00",
            "summary": f"Best time for {activity.replace('_', ' ')} is around 12:00.",
            "reason": "conditions are fair",
            "confidence": "medium",
            "score": 50,
            "recommendation": "acceptable",
        }

    scored_entries = [
        {
            **entry,
            "_score": _score_activity_entry(activity, entry),
            "_recommendation": _window_recommendation(activity, entry),
        }
        for entry in forecast_entries
    ]

    ranked = sorted(scored_entries, key=lambda entry: entry["_score"], reverse=True)
    best = ranked[0]
    time_label = best["time_label"]

    if best["_score"] >= 78:
        confidence = "high"
    elif best["_score"] >= 52:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "best_time_window": f"{time_label}-{_window_end(time_label)}",
        "summary": f"Best time for {activity.replace('_', ' ')} is around {time_label}.",
        "reason": _window_reason(activity, best, best["_recommendation"]),
        "confidence": confidence,
        "score": int(round(best["_score"])),
        "recommendation": best["_recommendation"],
    }


def build_activity_windows(forecast_entries: list[dict]) -> list[dict]:
    windows: list[dict] = []

    for activity in ("walking", "cycling", "outdoor_dining"):
        best = find_best_time_window(activity, forecast_entries)

        if best["recommendation"] == "not_recommended":
            label = activity.replace("_", " ").capitalize()
            summary = f"{label} is generally weak today; this is the least risky window."
        elif best["recommendation"] == "acceptable":
            label = activity.replace("_", " ").capitalize()
            summary = f"{label} is possible in this window, but conditions are mixed."
        else:
            summary = f"Best time for {activity.replace('_', ' ')} is around {best['best_time_window']}."

        windows.append(
            {
                "activity": activity,
                "best_time_window": best["best_time_window"],
                "summary": summary,
                "reason": best["reason"],
                "confidence": best["confidence"],
                "score": best["score"],
                "recommendation": best["recommendation"],
            }
        )

    return windows
