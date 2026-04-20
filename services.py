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

from config import get_settings


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_model_assets() -> dict:
    # Load all required machine learning assets into memory once
    return {
        "model_umbrella": joblib.load(BASE_DIR / "model_umbrella.joblib"),
        "model_clothing": joblib.load(BASE_DIR / "model_clothing.joblib"),
        "label_encoder_clothing": joblib.load(BASE_DIR / "label_encoder_clothing.joblib"),
        "model_features": joblib.load(BASE_DIR / "model_features.joblib"),
    }


def model_assets_available() -> bool:
    # Check if all necessary ML joblib files exist in the directory
    required_files = [
        BASE_DIR / "model_umbrella.joblib",
        BASE_DIR / "model_clothing.joblib",
        BASE_DIR / "label_encoder_clothing.joblib",
        BASE_DIR / "model_features.joblib",
    ]
    return all(path.exists() for path in required_files)


def dependencies_status() -> dict:
    # Check the configuration status of external services
    settings = get_settings()
    return {
        "open_meteo": "configured (no key required)",
        "huggingface": "configured" if settings.hf_api_key else "missing",
    }


def get_season() -> str:
    # Determine the current season based on the month
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    if month in [3, 4, 5]:
        return "spring"
    if month in [6, 7, 8]:
        return "summer"
    return "autumn"


def map_wmo_code(wmo_code: int) -> str:
    # Map Open-Meteo numerical weather codes to labels recognized by the ML model
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
    # Execute safe external HTTP GET requests
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
        city = params.get("name", "unknown")
        raise HTTPException(
            status_code=404,
            detail=f"'{city}' is not a valid city. Please check the spelling.",
        )

    if response.status_code != 200:
        logger.error("Weather service returned %s: %s", response.status_code, response.text)
        raise HTTPException(
            status_code=502,
            detail="Weather service is currently unavailable.",
        )

    return response.json()

def _format_city_result(item: dict) -> dict:
    name = item.get("name", "")
    country = item.get("country")
    admin1 = item.get("admin1")
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


def fetch_weather_data(city: str) -> dict:
    # Step 1: Geocoding (convert city name to latitude/longitude)
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

    lat = geo_data["results"][0]["latitude"]
    lon = geo_data["results"][0]["longitude"]

    # Step 2: Fetch current weather using coordinates
    weather_url = "https://api.open-meteo.com/v1/forecast"
    w_data = _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m"
            ),
        },
    )

    current = w_data["current"]

    return {
        "temperature_c": float(current["temperature_2m"]),
        "feels_like_c": float(current["apparent_temperature"]),
        "precipitation_mm": float(current["precipitation"]),
        "wind_speed_kmh": float(current["wind_speed_10m"]),
        "humidity_pct": int(current["relative_humidity_2m"]),
        "weather_condition": map_wmo_code(current["weather_code"]),
        "season": get_season(),
    }


def fetch_forecast_data(city: str) -> list[dict]:
    # Step 1: Geocoding
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

    lat = geo_data["results"][0]["latitude"]
    lon = geo_data["results"][0]["longitude"]

    # Step 2: Fetch 24-hour forecast data
    weather_url = "https://api.open-meteo.com/v1/forecast"
    f_data = _get_json(
        weather_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,wind_speed_10m"
            ),
            "forecast_hours": 24,
        },
    )

    hourly = f_data["hourly"]
    entries: list[dict] = []

    for i in range(len(hourly["time"])):
        time_str = hourly["time"][i][-5:]
        entries.append(
            {
                "time_label": time_str,
                "temperature_c": float(hourly["temperature_2m"][i]),
                "feels_like_c": float(hourly["apparent_temperature"][i]),
                "precipitation_mm": float(hourly["precipitation"][i]),
                "wind_speed_kmh": float(hourly["wind_speed_10m"][i]),
                "humidity_pct": int(hourly["relative_humidity_2m"][i]),
                "weather_condition": map_wmo_code(hourly["weather_code"][i]),
                "season": get_season(),
            }
        )

    return entries


def predict_ml_decisions(weather_dict: dict) -> tuple[bool, str, str]:
    assets = load_model_assets()

    df_input = pd.DataFrame([weather_dict])
    df_input = pd.get_dummies(df_input)
    df_input = df_input.reindex(columns=assets["model_features"], fill_value=0)

    pred_umb = assets["model_umbrella"].predict(df_input)[0]
    pred_cloth_idx = assets["model_clothing"].predict(df_input)[0]

    clothing_text = assets["label_encoder_clothing"].inverse_transform([pred_cloth_idx])[0]

    umbrella_needed = bool(pred_umb)

    # Safety override for obvious wet conditions
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
            return f"Rain is likely. Wear {clean_clothing} and bring an umbrella."
        return f"The weather looks calm. {clean_clothing} should be enough."

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
    city: str,
    weather_dict: dict,
    clothing_text: str,
    umbrella_needed: bool,
    activity_result: dict,
    language: str,
) -> str:
    clean_clothing = clothing_text.replace("_", " ")
    activity_name = activity_result["activity"].replace("_", " ")
    activity_status = activity_result["recommendation"]

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

def _normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text
def _strip_technical_details(text: str) -> str:
    """
    Remove technical weather details from LLM advice while keeping the advice natural.
    """
    cleaned = text

    # Remove temperature phrases like:
    # "with a temperature of 7.4 degrees Celsius"
    cleaned = re.sub(
        r"\bwith a temperature of [-+]?\d+(\.\d+)? degrees celsius\b[,]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Remove shorter temperature phrases like:
    # "it is 7 degrees", "7.4°C", "7 degrees Celsius"
    cleaned = re.sub(
        r"\b[-+]?\d+(\.\d+)?\s*(°c|celsius|degrees celsius|degrees)\b[,]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Remove leading weather-summary phrases
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

    # Remove technical reason fragments
    cleaned = re.sub(
        r"\b(as|because|since)\s+the\s+(dry weather|light wind|strong wind|temperature|humidity)\s+[^.]*[.]?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    # Cleanup spacing and punctuation
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
    cleaned = re.sub(r"^[,.\-:\s]+", "", cleaned)
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)

    # Ensure first letter is uppercase
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

    # Clothing: allow partial overlap instead of exact full phrase only
    clothing_tokens = [token for token in clean_clothing.split() if len(token) > 2]
    if clothing_tokens and not any(token in advice_lower for token in clothing_tokens):
        return False

    # Umbrella consistency
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

    # Activity consistency
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
        "Do not mention numbers, temperature, degrees, humidity, wind speed, precipitation, or weather condition names. "
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
    """
    Try two model alternatives through Hugging Face router.
    Returns the first successful content, otherwise None.
    """
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
        city,
        {
            "weather_condition": weather_condition,
            "temperature_c": temp,
        },
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

def find_best_time_window(activity: str, forecast_entries: list[dict]) -> dict:
    def score(entry: dict) -> float:
        base = 100.0
        base -= entry["precipitation_mm"] * 20
        base -= max(entry["wind_speed_kmh"] - 10, 0) * 1.5
        base -= abs(entry["temperature_c"] - 18) * 1.2

        if activity == "cycling":
            base -= max(entry["wind_speed_kmh"] - 15, 0) * 2

        return base

    ranked = sorted(forecast_entries, key=score, reverse=True)
    best = ranked[0]
    time_label = best["time_label"]

    summary = f"Best time for {activity.replace('_', ' ')} is around {time_label}."

    return {
        "best_time_window": f"{time_label}-{_window_end(time_label)}",
        "summary": summary,
        "reason": build_reason(best),
        "confidence": assess_confidence(best),
    }


def _window_end(start_label: str) -> str:
    hour = int(start_label.split(":")[0])
    return f"{(hour + 3) % 24:02d}:00"