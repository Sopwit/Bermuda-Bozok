"""
Request and response schemas for the WeatherWise API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


SUPPORTED_ACTIVITIES = ("walking", "cycling", "outdoor_dining")

class CitySuggestionItem(BaseModel):
    name: str
    country: str | None = None
    admin1: str | None = None
    latitude: float
    longitude: float
    display_name: str


class CitySuggestionsResponse(BaseModel):
    status: str
    query: str
    results: list[CitySuggestionItem]


class CityInput(BaseModel):
    city: str = Field(..., min_length=2, max_length=100, description="City name to query.")

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("City name must contain at least 2 characters.")
        return cleaned


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


class LiveWeatherData(BaseModel):
    temperature_c: float
    feels_like_c: float
    precipitation_mm: float
    wind_speed_kmh: float
    humidity_pct: int
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
