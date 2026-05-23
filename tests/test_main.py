"""
Tests for WeatherWise API endpoints and error handling.
"""

from fastapi import HTTPException

from weatherwise import main


class TestHealthCheck:
    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["service"] == "weatherwise-api"
        assert payload["dependencies"]["open_meteo"] == "configured (no key required)"
        assert payload["dependencies"]["huggingface"] in {"configured", "missing"}
        assert "model_assets_loaded" in payload


class TestWeatherRecommendation:
    def test_successful_recommendation(self, client, monkeypatch, sample_weather, sample_ml_result, sample_advice):
        def fake_fetch(*args, **kwargs):
            return sample_weather

        def fake_predict(weather_dict):
            return sample_ml_result

        def fake_advice(**kwargs):
            return sample_advice

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
        assert payload["advice"] == sample_advice
        assert payload["reason"]
        assert payload["confidence"] in {"low", "medium", "high"}
        assert payload["ml_decision"]["umbrella_needed"] is True
        assert payload["activity_advice"]["activity"] == "walking"

    def test_propagates_http_errors(self, client, monkeypatch):
        def fake_fetch(*args, **kwargs):
            raise HTTPException(status_code=404, detail="City not found.")

        main.api_cache.clear()
        monkeypatch.setattr(main, "fetch_weather_data", fake_fetch)

        response = client.post("/weather/recommendation", json={"city": "InvalidCity"})

        assert response.status_code == 404
        assert response.json()["error_code"] == "CITY_NOT_FOUND"


class TestPlanningDay:
    def test_successful_planning(self, client, monkeypatch, sample_forecast):
        def fake_forecast(*args, **kwargs):
            return sample_forecast

        monkeypatch.setattr(main, "fetch_forecast_data", fake_forecast)

        response = client.post("/planning/day", json={"city": "Ankara", "activity": "walking"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["activity"] == "walking"
        assert payload["best_time_window"] == "15:00-18:00"


class TestActivities:
    def test_returns_three_activities(self, client, monkeypatch, sample_weather):
        def fake_fetch(*args, **kwargs):
            return sample_weather

        monkeypatch.setattr(main, "fetch_weather_data", fake_fetch)

        response = client.post("/recommendations/activities", json={"city": "Ankara"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert len(payload["activities"]) == 3


class TestDashboard:
    def test_supports_coordinate_lookup(self, client, monkeypatch, sample_weather, sample_forecast, sample_daily_forecast, sample_ml_result_no_umbrella):
        def fake_fetch_weather(*args, **kwargs):
            return sample_weather

        def fake_forecast(*args, **kwargs):
            return sample_forecast

        def fake_daily(*args, **kwargs):
            return sample_daily_forecast

        def fake_predict(weather_dict):
            return sample_ml_result_no_umbrella

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
