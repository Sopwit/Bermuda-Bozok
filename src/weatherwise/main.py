"""
Main FastAPI application entry point.

Registers routes, exception handlers, middleware, and a TTL-based response
cache for the WeatherWise API.
"""

from __future__ import annotations

import logging

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from weatherwise.config import get_settings
from weatherwise.schemas import (
    ActivitiesResponse,
    ActivityRecommendationItem,
    AdviceResponse,
    CitySuggestionItem,
    CitySuggestionsResponse,
    DashboardResponse,
    ErrorResponse,
    HealthDependencies,
    HealthResponse,
    PlanningInput,
    PlanningResponse,
    RecommendationInput,
)
from weatherwise.services import (
    _format_coordinate_location,
    activity_recommendation,
    assess_confidence,
    build_activity_windows,
    build_headline,
    build_outfit_plan,
    build_reason,
    dependencies_status,
    fetch_daily_forecast,
    fetch_forecast_data,
    fetch_weather_data,
    find_best_time_window,
    generate_llm_advice,
    model_assets_available,
    predict_ml_decisions,
    search_city_suggestions,
)

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="WeatherWise API",
    description="WeatherWise transforms live weather into short, human-friendly recommendations and planning signals.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}

api_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_seconds)


def _cache_key(prefix: str, data: RecommendationInput) -> str:
    if data.latitude is not None and data.longitude is not None:
        location_part = f"coords:{data.latitude:.6f}:{data.longitude:.6f}"
    else:
        location_part = f"city:{(data.city or '').strip().lower()}"
    activity = data.activity or "walking"
    language = getattr(data, "language", "en")
    return f"{prefix}:{location_part}:{activity}:{language}"


def error_payload(status_code: int, detail: str) -> dict:
    mapping = {
        400: "BAD_REQUEST",
        404: "CITY_NOT_FOUND",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_ERROR",
        502: "UPSTREAM_SERVICE_ERROR",
    }
    return {
        "status": "error",
        "error_code": mapping.get(status_code, "UNKNOWN_ERROR"),
        "detail": detail,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.status_code, str(exc.detail)),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_payload(422, "Request body is invalid."),
    )


# ── System ──────────────────────────────────────────────────────────────


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["system"],
)
async def health_check() -> HealthResponse:
    deps = dependencies_status()
    return HealthResponse(
        status="ok",
        service="weatherwise-api",
        version=app.version,
        model_assets_loaded=model_assets_available(),
        dependencies=HealthDependencies(**deps),
    )


@app.get(
    "/cities/search",
    response_model=CitySuggestionsResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["cities"],
)
async def cities_search(q: str = Query(..., min_length=2)) -> CitySuggestionsResponse:
    try:
        cleaned = q.strip()
        results = search_city_suggestions(cleaned)
        return CitySuggestionsResponse(
            status="success",
            query=cleaned,
            results=[CitySuggestionItem(**item) for item in results],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /cities/search")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc


# ── Internal builders ───────────────────────────────────────────────────


def _build_dashboard(data: RecommendationInput) -> DashboardResponse:
    cache_key = _cache_key("dashboard", data)
    if cache_key in api_cache:
        return DashboardResponse(**api_cache[cache_key])

    location_label = data.city or _format_coordinate_location(data.latitude, data.longitude)
    live_weather = fetch_weather_data(data.city, latitude=data.latitude, longitude=data.longitude)
    hourly_forecast = fetch_forecast_data(data.city, latitude=data.latitude, longitude=data.longitude)
    daily_forecast = fetch_daily_forecast(data.city, latitude=data.latitude, longitude=data.longitude)

    umbrella_needed, umbrella_text, clothing_text = predict_ml_decisions(live_weather)
    activity_result = activity_recommendation(data.activity or "walking", live_weather)
    reason = build_reason(live_weather)

    ai_advice = generate_llm_advice(
        city=location_label,
        weather_condition=live_weather["weather_condition"],
        temp=live_weather["temperature_c"],
        umbrella_text=umbrella_text,
        clothing_text=clothing_text,
        reason=reason,
        activity_result=activity_result,
        language=data.language,
    )

    outfit_plan = build_outfit_plan(clothing_text, umbrella_needed, live_weather)

    activities = [
        {
            "name": item["activity"],
            "recommendation": item["recommendation"],
            "reason": item["reason"],
        }
        for item in [activity_recommendation(name, live_weather) for name in ("walking", "cycling", "outdoor_dining")]
    ]

    activity_windows = build_activity_windows(hourly_forecast)

    payload = {
        "status": "success",
        "location": location_label,
        "headline": build_headline(live_weather, clothing_text, umbrella_needed, data.language),
        "advice": ai_advice,
        "reason": reason,
        "confidence": assess_confidence(live_weather),
        "live_data": live_weather,
        "ml_decision": {
            "umbrella_needed": umbrella_needed,
            "clothing_category": clothing_text,
        },
        "outfit_plan": outfit_plan,
        "activity_advice": activity_result,
        "alert": None,
        "ai_advice": ai_advice,
        "activities": activities,
        "activity_windows": activity_windows,
        "hourly_forecast": hourly_forecast,
        "daily_forecast": daily_forecast,
    }
    api_cache[cache_key] = payload
    return DashboardResponse(**payload)


def _build_recommendation(data: RecommendationInput) -> AdviceResponse:
    cache_key = _cache_key("recommendation", data)
    if cache_key in api_cache:
        return AdviceResponse(**api_cache[cache_key])

    location_label = data.city or _format_coordinate_location(data.latitude, data.longitude)
    live_weather = fetch_weather_data(data.city, latitude=data.latitude, longitude=data.longitude)
    umbrella_needed, umbrella_text, clothing_text = predict_ml_decisions(live_weather)
    activity_result = activity_recommendation(data.activity or "walking", live_weather)
    reason = build_reason(live_weather)

    ai_advice = generate_llm_advice(
        city=location_label,
        weather_condition=live_weather["weather_condition"],
        temp=live_weather["temperature_c"],
        umbrella_text=umbrella_text,
        clothing_text=clothing_text,
        reason=reason,
        activity_result=activity_result,
        language=data.language,
    )

    payload = {
        "status": "success",
        "location": location_label,
        "headline": build_headline(live_weather, clothing_text, umbrella_needed, data.language),
        "advice": ai_advice,
        "reason": reason,
        "confidence": assess_confidence(live_weather),
        "live_data": live_weather,
        "ml_decision": {
            "umbrella_needed": umbrella_needed,
            "clothing_category": clothing_text,
        },
        "activity_advice": activity_result,
        "ai_advice": ai_advice,
    }
    api_cache[cache_key] = payload
    return AdviceResponse(**payload)


# ── Endpoints ───────────────────────────────────────────────────────────


@app.post(
    "/weather/dashboard",
    response_model=DashboardResponse,
    responses=_ERROR_RESPONSES,
    tags=["dashboard"],
)
async def weather_dashboard(data: RecommendationInput) -> DashboardResponse:
    try:
        return _build_dashboard(data)
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /weather/dashboard")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc


@app.post(
    "/weather/recommendation",
    response_model=AdviceResponse,
    responses=_ERROR_RESPONSES,
    tags=["recommendations"],
)
async def weather_recommendation(data: RecommendationInput) -> AdviceResponse:
    try:
        return _build_recommendation(data)
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /weather/recommendation")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc


@app.post(
    "/get-advice",
    response_model=AdviceResponse,
    deprecated=True,
    responses=_ERROR_RESPONSES,
    tags=["legacy"],
)
async def get_weather_advice(data: RecommendationInput) -> AdviceResponse:
    return await weather_recommendation(data)


@app.post(
    "/planning/day",
    response_model=PlanningResponse,
    responses=_ERROR_RESPONSES,
    tags=["planning"],
)
async def planning_day(data: PlanningInput) -> PlanningResponse:
    try:
        location_label = data.city or _format_coordinate_location(data.latitude, data.longitude)
        forecast = fetch_forecast_data(data.city, latitude=data.latitude, longitude=data.longitude)
        best = find_best_time_window(data.activity, forecast)
        return PlanningResponse(
            status="success",
            location=location_label,
            activity=data.activity,
            best_time_window=best["best_time_window"],
            summary=best["summary"],
            reason=best["reason"],
            confidence=best["confidence"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /planning/day")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc


@app.post(
    "/recommendations/activities",
    response_model=ActivitiesResponse,
    responses=_ERROR_RESPONSES,
    tags=["recommendations"],
)
async def recommendations_activities(data: RecommendationInput) -> ActivitiesResponse:
    try:
        location_label = data.city or _format_coordinate_location(data.latitude, data.longitude)
        live_weather = fetch_weather_data(data.city, latitude=data.latitude, longitude=data.longitude)
        results = [
            ActivityRecommendationItem(
                name=activity_result["activity"],
                recommendation=activity_result["recommendation"],
                reason=activity_result["reason"],
            )
            for activity_result in [
                activity_recommendation(name, live_weather)
                for name in ("walking", "cycling", "outdoor_dining")
            ]
        ]
        headline = "Best current outdoor options for quick daily decisions."
        return ActivitiesResponse(
            status="success",
            location=location_label,
            headline=headline,
            activities=results,
            live_data=live_weather,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /recommendations/activities")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc
