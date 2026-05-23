"""
Request and response schemas for the WeatherWise API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SUPPORTED_ACTIVITIES = ("walking", "cycling", "outdoor_dining")

__all__ = [
    "ActivitiesResponse",
    "ActivityAdvice",
    "ActivityRecommendationItem",
    "ActivityWindow",
    "AdviceResponse",
    "CityInput",
    "CitySuggestionItem",
    "CitySuggestionsResponse",
    "DailyForecastItem",
    "DashboardResponse",
    "ErrorResponse",
    "ForecastEntry",
    "HealthDependencies",
    "HealthResponse",
    "LiveWeatherData",
    "MLDecision",
    "OutfitPlan",
    "PlanningInput",
    "PlanningResponse",
    "RecommendationInput",
    "WeatherAlert",
]


class CityInput(BaseModel):
    city: str | None = Field(default=None, max_length=100, description="City name to query.")
    latitude: float | None = Field(default=None, description="Latitude for coordinate-based lookup.")
    longitude: float | None = Field(default=None, description="Longitude for coordinate-based lookup.")

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("City name must contain at least 2 characters.")
        return cleaned

    @model_validator(mode="after")
    def validate_location(self) -> CityInput:
        has_city = bool(self.city)
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None

        if has_latitude != has_longitude:
            raise ValueError("Latitude and longitude must be provided together.")

        if not has_city and not (has_latitude and has_longitude):
            raise ValueError("Either city or latitude/longitude must be provided.")

        if self.city is not None:
            self.city = self.city.strip() or None
            if self.city is not None and len(self.city) < 2:
                raise ValueError("City name must contain at least 2 characters.")

        return self


class RecommendationInput(CityInput):
    activity: Literal["walking", "cycling", "outdoor_dining"] | None = Field(
        default="walking",
        description="Primary activity to evaluate for the user.",
    )
    language: Literal["en", "tr"] = Field(
        default="en",
        description="Language for user-facing recommendation copy.",
    )


class PlanningInput(CityInput):
    activity: Literal["walking", "cycling", "outdoor_dining"] = Field(
        default="walking",
        description="Activity to evaluate for the best time window.",
    )


class CitySuggestionItem(BaseModel):
    name: str
    country: str | None = None
    admin1: str | None = None
    admin2: str | None = None
    latitude: float
    longitude: float
    display_name: str


class CitySuggestionsResponse(BaseModel):
    status: str
    query: str
    results: list[CitySuggestionItem]


class LiveWeatherData(BaseModel):
    temperature_c: float
    feels_like_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    wind_gust_kmh: float | None = None
    humidity_pct: int
    wind_direction_deg: float | None = None
    cloud_cover_pct: int | None = None
    visibility_km: float | None = None
    uv_index: float | None = None
    european_aqi: int | None = None
    pm2_5_ugm3: float | None = None
    pm10_ugm3: float | None = None
    sunrise_local: str | None = None
    sunset_local: str | None = None
    weather_condition: str
    season: str


class MLDecision(BaseModel):
    umbrella_needed: bool
    clothing_category: str


class ActivityAdvice(BaseModel):
    activity: str
    recommendation: str
    reason: str


class AdviceResponse(BaseModel):
    status: str
    location: str
    headline: str
    advice: str
    reason: str
    confidence: Literal["low", "medium", "high"]
    live_data: LiveWeatherData
    ml_decision: MLDecision
    activity_advice: ActivityAdvice
    ai_advice: str


class PlanningResponse(BaseModel):
    status: str
    location: str
    activity: str
    best_time_window: str
    summary: str
    reason: str
    confidence: Literal["low", "medium", "high"]


class ActivityRecommendationItem(BaseModel):
    name: str
    recommendation: str
    reason: str


class ActivitiesResponse(BaseModel):
    status: str
    location: str
    headline: str
    activities: list[ActivityRecommendationItem]
    live_data: LiveWeatherData


class OutfitPlan(BaseModel):
    summary: str
    layers: list[str]
    accessories: list[str]
    footwear: str


class WeatherAlert(BaseModel):
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str


class ActivityWindow(BaseModel):
    activity: Literal["walking", "cycling", "outdoor_dining"]
    best_time_window: str
    summary: str
    reason: str
    confidence: Literal["low", "medium", "high"]
    score: int
    recommendation: Literal["recommended", "acceptable", "not_recommended"]


class ForecastEntry(LiveWeatherData):
    time_label: str


class DailyForecastItem(BaseModel):
    date: str
    label: str
    weather_condition: str
    temperature_high_c: float
    temperature_low_c: float
    precipitation_total_mm: float
    precipitation_probability_max_pct: int | None = None
    uv_index_max: float | None = None
    sunshine_duration_hours: float | None = None
    wind_gust_max_kmh: float | None = None
    sunrise_local: str | None = None
    sunset_local: str | None = None


class DashboardResponse(BaseModel):
    status: str
    location: str
    headline: str
    advice: str
    reason: str
    confidence: Literal["low", "medium", "high"]
    live_data: LiveWeatherData
    ml_decision: MLDecision
    outfit_plan: OutfitPlan
    activity_advice: ActivityAdvice
    alert: WeatherAlert | None = None
    ai_advice: str
    activities: list[ActivityRecommendationItem]
    activity_windows: list[ActivityWindow]
    hourly_forecast: list[ForecastEntry]
    daily_forecast: list[DailyForecastItem]


class HealthDependencies(BaseModel):
    open_meteo: str
    huggingface: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    model_assets_loaded: bool
    dependencies: HealthDependencies


class ErrorResponse(BaseModel):
    status: str
    error_code: str
    detail: str
