"""
Shared fixtures and test data for WeatherWise API tests.
"""

import pytest
from fastapi.testclient import TestClient

from weatherwise import main


@pytest.fixture
def client():
    main.api_cache.clear()
    return TestClient(main.app)


@pytest.fixture
def sample_weather():
    return {
        "temperature_c": 18.0,
        "feels_like_c": 17.5,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 12.6,
        "humidity_pct": 52,
        "weather_condition": "clouds",
        "season": "spring",
    }


@pytest.fixture
def sample_forecast():
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


@pytest.fixture
def sample_daily_forecast():
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


@pytest.fixture
def sample_ml_result():
    return True, "Yes", "light_jacket"


@pytest.fixture
def sample_ml_result_no_umbrella():
    return False, "No", "light_jacket"


@pytest.fixture
def sample_advice():
    return "Take an umbrella and wear a light jacket."
