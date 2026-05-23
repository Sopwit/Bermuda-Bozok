from fastapi import HTTPException
from fastapi.testclient import TestClient

from weatherwise import main


client = TestClient(main.app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "weatherwise-api"
    assert payload["dependencies"]["open_meteo"] == "configured (no key required)"
    assert payload["dependencies"]["huggingface"] in {"configured", "missing"}
    assert "model_assets_loaded" in payload


def test_weather_recommendation_success(monkeypatch):
    def fake_fetch(*args, **kwargs):
        return {
            "temperature_c": 18.0,
            "feels_like_c": 17.5,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.6,
            "humidity_pct": 52,
            "weather_condition": "clouds",
            "season": "spring",
        }

    def fake_predict(weather_dict):
        return True, "Yes", "light_jacket"

    def fake_advice(**kwargs):
        return "Take an umbrella and wear a light jacket."

    main.api_cache.clear()
    monkeypatch.setattr(main, "fetch_weather_data", fake_fetch)
    monkeypatch.setattr(main, "predict_ml_decisions", fake_predict)
    monkeypatch.setattr(main, "generate_llm_advice", fake_advice)

    response = client.post("/weather/recommendation", json={"city": "Ankara", "activity": "walking"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["location"] == "Ankara"
    assert payload["headline"]
    assert payload["advice"] == "Take an umbrella and wear a light jacket."
    assert payload["reason"]
    assert payload["confidence"] in {"low", "medium", "high"}
    assert payload["ml_decision"]["umbrella_needed"] is True
    assert payload["activity_advice"]["activity"] == "walking"


def test_planning_day_success(monkeypatch):
    def fake_forecast(*args, **kwargs):
        return [
            {
                "time_label": "09:00",
                "temperature_c": 8.0,
                "feels_like_c": 7.0,
                "precipitation_mm": 1.0,
                "wind_speed_kmh": 18.0,
                "humidity_pct": 60,
                "weather_condition": "rain",
                "season": "spring",
            },
            {
                "time_label": "15:00",
                "temperature_c": 18.0,
                "feels_like_c": 18.0,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 8.0,
                "humidity_pct": 42,
                "weather_condition": "clouds",
                "season": "spring",
            },
        ]

    monkeypatch.setattr(main, "fetch_forecast_data", fake_forecast)

    response = client.post("/planning/day", json={"city": "Ankara", "activity": "walking"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["activity"] == "walking"
    assert payload["best_time_window"] == "15:00-18:00"


def test_activities_success(monkeypatch):
    def fake_fetch(*args, **kwargs):
        return {
            "temperature_c": 18.0,
            "feels_like_c": 17.5,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.6,
            "humidity_pct": 52,
            "weather_condition": "clouds",
            "season": "spring",
        }

    monkeypatch.setattr(main, "fetch_weather_data", fake_fetch)

    response = client.post("/recommendations/activities", json={"city": "Ankara"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert len(payload["activities"]) == 3


def test_weather_dashboard_supports_coordinates(monkeypatch):
    def fake_fetch_weather(*args, **kwargs):
        return {
            "temperature_c": 18.0,
            "feels_like_c": 17.5,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.6,
            "humidity_pct": 52,
            "weather_condition": "clouds",
            "season": "spring",
        }

    def fake_forecast(*args, **kwargs):
        return [
            {
                "time_label": "09:00",
                "temperature_c": 8.0,
                "feels_like_c": 7.0,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 8.0,
                "humidity_pct": 60,
                "weather_condition": "clouds",
                "season": "spring",
            },
            {
                "time_label": "15:00",
                "temperature_c": 18.0,
                "feels_like_c": 18.0,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 8.0,
                "humidity_pct": 42,
                "weather_condition": "clouds",
                "season": "spring",
            },
        ]

    def fake_daily(*args, **kwargs):
        return [
            {
                "date": "2026-05-23",
                "label": "Today",
                "weather_condition": "clouds",
                "temperature_high_c": 19.0,
                "temperature_low_c": 12.0,
                "precipitation_total_mm": 0.0,
            }
        ]

    def fake_predict(weather_dict):
        return False, "No", "light_jacket"

    def fake_advice(**kwargs):
        return "Wear a light jacket."

    main.api_cache.clear()
    monkeypatch.setattr(main, "fetch_weather_data", fake_fetch_weather)
    monkeypatch.setattr(main, "fetch_forecast_data", fake_forecast)
    monkeypatch.setattr(main, "fetch_daily_forecast", fake_daily)
    monkeypatch.setattr(main, "predict_ml_decisions", fake_predict)
    monkeypatch.setattr(main, "generate_llm_advice", fake_advice)

    response = client.post(
        "/weather/dashboard",
        json={
            "city": "Current Location",
            "latitude": 39.92,
            "longitude": 32.85,
            "activity": "walking",
            "language": "en",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["location"] == "Current Location"
    assert payload["headline"]
    assert len(payload["activity_windows"]) == 3
    assert len(payload["daily_forecast"]) == 1


def test_weather_recommendation_propagates_http_errors(monkeypatch):
    def fake_fetch(*args, **kwargs):
        raise HTTPException(status_code=404, detail="City not found.")

    main.api_cache.clear()
    monkeypatch.setattr(main, "fetch_weather_data", fake_fetch)

    response = client.post("/weather/recommendation", json={"city": "InvalidCity"})

    assert response.status_code == 404
    assert response.json()["error_code"] == "CITY_NOT_FOUND"
