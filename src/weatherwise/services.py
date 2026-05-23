"""
Business logic for weather access, ML predictions, planning, and user-facing recommendations.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
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
    "dependencies_status",
    "fetch_air_quality_data",
    "fetch_daily_forecast",
    "fetch_forecast_data",
    "fetch_weather_data",
    "find_best_time_window",
    "generate_llm_advice",
    "geocode_city",
    "format_coordinate_location",
    "model_assets_available",
    "predict_ml_decisions",
    "search_city_suggestions",
    "summarize_advice",
]

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


@lru_cache(maxsize=1)
def load_model_assets() -> dict:
    return {
        "model_umbrella": joblib.load(MODELS_DIR / "model_umbrella.joblib"),
        "model_clothing": joblib.load(MODELS_DIR / "model_clothing.joblib"),
        "label_encoder_clothing": joblib.load(MODELS_DIR / "label_encoder_clothing.joblib"),
        "model_features": joblib.load(MODELS_DIR / "model_features.joblib"),
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


def _fetch_weather_payload(lat: float, lon: float) -> dict:
    weather_url = "https://api.open-meteo.com/v1/forecast"
    return _get_json(
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


def _fetch_hourly_payload(lat: float, lon: float) -> dict:
    weather_url = "https://api.open-meteo.com/v1/forecast"
    return _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,"
                "wind_direction_10m,cloud_cover,visibility,uv_index"
            ),
            "timezone": "auto",
            "forecast_days": 2,
        },
    )


def _fetch_daily_payload(lat: float, lon: float) -> dict:
    weather_url = "https://api.open-meteo.com/v1/forecast"
    return _get_json(
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


def dependencies_status() -> dict:
    settings = get_settings()
    return {
        "open_meteo": "configured (no key required)",
        "huggingface": "configured" if settings.hf_api_key else "missing",
    }


def get_season() -> str:
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    if month in [3, 4, 5]:
        return "spring"
    if month in [6, 7, 8]:
        return "summer"
    return "autumn"


def map_wmo_code(wmo_code: int) -> str:
    if wmo_code == 0:
        return "clear"
    if wmo_code in [1, 2, 3, 45, 48]:
        return "clouds"
    if wmo_code in [51, 53, 55, 56, 57]:
        return "drizzle"
    if wmo_code in [61, 63, 65, 66, 67, 80, 81, 82]:
        return "rain"
    if wmo_code in [71, 73, 75, 77, 85, 86]:
        return "snow"
    if wmo_code in [95, 96, 99]:
        return "thunderstorm"
    return "clouds"


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


def _geocode_city_uncached(city: str) -> dict:
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


@lru_cache(maxsize=256)
def geocode_city(city: str) -> dict:
    return _geocode_city_uncached(city)


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

def fetch_air_quality_data(lat: float, lon: float) -> dict:
    aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aq_data = _get_json(
        aq_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "european_aqi,pm2_5,pm10",
            "timezone": "auto",
        },
    )

    current = aq_data.get("current", {})

    return {
        "european_aqi": int(current["european_aqi"]) if current.get("european_aqi") is not None else None,
        "pm2_5_ugm3": float(current["pm2_5"]) if current.get("pm2_5") is not None else None,
        "pm10_ugm3": float(current["pm10"]) if current.get("pm10") is not None else None,
    }

def fetch_weather_data(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
        w_data = _fetch_weather_payload(latitude, longitude)
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
        w_data = _fetch_weather_payload(lat, lon)
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    current = w_data["current"]
    daily = w_data.get("daily", {})

    sunrise_local = None
    sunset_local = None

    if daily.get("sunrise"):
        sunrise_local = daily["sunrise"][0][-5:]
    if daily.get("sunset"):
        sunset_local = daily["sunset"][0][-5:]

    air_quality = fetch_air_quality_data(lat, lon)

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
        "european_aqi": air_quality["european_aqi"],
        "pm2_5_ugm3": air_quality["pm2_5_ugm3"],
        "pm10_ugm3": air_quality["pm10_ugm3"],
        "sunrise_local": sunrise_local,
        "sunset_local": sunset_local,
        "weather_condition": map_wmo_code(current["weather_code"]),
        "season": get_season(),
    }

def fetch_forecast_data(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict]:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
        f_data = _fetch_hourly_payload(lat, lon)
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
        f_data = _fetch_hourly_payload(lat, lon)
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    hourly = f_data["hourly"]
    entries: list[dict] = []

    for i in range(len(hourly["time"])):
        timestamp = datetime.fromisoformat(hourly["time"][i])
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
                "season": get_season(),
            }
        )

    now = datetime.now()
    cutoff = now.replace(minute=0, second=0, microsecond=0)
    upcoming = [
        entry
        for entry, raw_time in zip(entries, hourly["time"])
        if datetime.fromisoformat(raw_time) >= cutoff
    ]

    if len(upcoming) >= 24:
        return upcoming[:24]

    return entries[:24]


def fetch_daily_forecast(
    city: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> list[dict]:
    if latitude is not None and longitude is not None:
        lat, lon = latitude, longitude
        d_data = _fetch_daily_payload(lat, lon)
    elif city:
        geo = geocode_city(city)
        lat, lon = geo["latitude"], geo["longitude"]
        d_data = _fetch_daily_payload(lat, lon)
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided.")

    daily = d_data["daily"]
    items: list[dict] = []

    for i in range(len(daily["time"])):
        items.append(
            {
                "date": daily["time"][i],
                "label": "Today" if i == 0 else datetime.fromisoformat(daily["time"][i]).strftime("%a"),
                "weather_condition": map_wmo_code(daily["weather_code"][i]),
                "temperature_high_c": float(daily["temperature_2m_max"][i]),
                "temperature_low_c": float(daily["temperature_2m_min"][i]),
                "precipitation_total_mm": float(daily["precipitation_sum"][i]),
                "precipitation_probability_max_pct": (
                    int(daily["precipitation_probability_max"][i])
                    if daily.get("precipitation_probability_max") else None
                ),
                "uv_index_max": float(daily["uv_index_max"][i]) if daily.get("uv_index_max") else None,
                "sunshine_duration_hours": (
                    round(float(daily["sunshine_duration"][i]) / 3600, 1)
                    if daily.get("sunshine_duration") else None
                ),
                "wind_gust_max_kmh": float(daily["wind_gusts_10m_max"][i]) if daily.get("wind_gusts_10m_max") else None,
                "sunrise_local": daily["sunrise"][i][-5:] if daily.get("sunrise") else None,
                "sunset_local": daily["sunset"][i][-5:] if daily.get("sunset") else None,
            }
        )

    return items


def predict_ml_decisions(weather_dict: dict) -> tuple[bool, str, str]:
    assets = load_model_assets()

    df_input = pd.DataFrame([weather_dict])
    df_input = pd.get_dummies(df_input)
    df_input = df_input.reindex(columns=assets["model_features"], fill_value=0)

    pred_umb = assets["model_umbrella"].predict(df_input)[0]
    pred_cloth_idx = assets["model_clothing"].predict(df_input)[0]

    clothing_text = assets["label_encoder_clothing"].inverse_transform([pred_cloth_idx])[0]

    umbrella_needed = bool(pred_umb)

    if (
        weather_dict["precipitation_mm"] > 0
        or weather_dict["weather_condition"] in {"rain", "drizzle", "thunderstorm"}
    ):
        umbrella_needed = True

    umbrella_text = "Yes" if umbrella_needed else "No"
    return umbrella_needed, umbrella_text, str(clothing_text)


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

    if weather_dict["precipitation_mm"] > 0:
        reasons.append("rain is already present")
    elif weather_dict["weather_condition"] in {"rain", "drizzle", "thunderstorm"}:
        reasons.append("wet conditions are expected")

    if weather_dict["wind_speed_kmh"] >= 20:
        reasons.append("wind is strong")
    elif weather_dict["wind_speed_kmh"] <= 10:
        reasons.append("wind is light")

    if weather_dict["temperature_c"] <= 8:
        reasons.append("the air feels cold")
    elif weather_dict["temperature_c"] >= 24:
        reasons.append("the air feels warm")
    else:
        reasons.append("the temperature is comfortable")

    return ", ".join(reasons[:3]).capitalize() + "."


def assess_confidence(weather_dict: dict) -> str:
    if weather_dict["precipitation_mm"] > 0 or weather_dict["wind_speed_kmh"] > 25:
        return "high"
    if weather_dict["weather_condition"] in {"mist", "fog", "haze"}:
        return "low"
    return "medium"


def activity_recommendation(activity: str, weather_dict: dict) -> dict:
    rain = weather_dict["precipitation_mm"]
    wind = weather_dict["wind_speed_kmh"]
    temp = weather_dict["temperature_c"]

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
        if umbrella_needed:
            umbrella_part = "Yanına şemsiye al"
        else:
            umbrella_part = "Şemsiyeye ihtiyacın yok"

        if activity_status == "recommended":
            activity_part = f"{activity_name} için uygun görünüyor"
        elif activity_status == "acceptable":
            activity_part = f"{activity_name} mümkün ama şartlar orta seviyede"
        else:
            activity_part = f"{activity_name} için ertelemek daha iyi olabilir"

        return f"{clean_clothing} giy. {umbrella_part}, ve {activity_part}."

    if umbrella_needed:
        umbrella_part = "Take an umbrella with you"
    else:
        umbrella_part = "You can leave the umbrella at home"

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

    if weather_dict["temperature_c"] >= 22:
        accessories.append("Sun protection")
    elif weather_dict["temperature_c"] <= 8:
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


def _normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


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


def _call_hf_chat(headers: dict, system_prompt: str, user_prompt: str) -> str | None:
    url = "https://router.huggingface.co/v1/chat/completions"

    candidate_models = [
        "meta-llama/Llama-3.1-8B-Instruct:fastest",
        "Qwen/Qwen2.5-7B-Instruct:fastest",
    ]

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
            response = requests.post(url, headers=headers, json=payload, timeout=25)

            if response.status_code != 200:
                logger.warning(
                    "HF router error for model %s -> %s: %s",
                    model_name,
                    response.status_code,
                    response.text,
                )
                continue

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            if content:
                logger.info("HF model succeeded: %s", model_name)
                return content

        except Exception:
            logger.exception("HF router request failed for model %s", model_name)

    return None


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

    content = _call_hf_chat(headers, system_prompt, user_prompt)

    if not content:
        return fallback_msg

    content = _normalize_text(content)
    content = content.strip('"').strip("'").strip()
    content = _strip_technical_details(content)

    if not content:
        return fallback_msg

    if not _is_advice_consistent(
        advice=content,
        umbrella_needed=(umbrella_text == "Yes"),
        clothing_text=clothing_text,
        activity_result=activity_result,
    ):
        logger.warning("LLM advice was inconsistent with structured outputs. Using fallback.")
        return fallback_msg

    return content

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


def find_best_time_window(activity: str, forecast_entries: list[dict]) -> dict:
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


def _window_end(start_label: str) -> str:
    hour = int(start_label.split(":")[0])
    return f"{(hour + 3) % 24:02d}:00"
