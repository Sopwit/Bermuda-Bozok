"""
Main FastAPI application entry point.
"""
from __future__ import annotations

import logging

from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import get_settings
from schemas import (
    ActivitiesResponse,
    ActivityRecommendationItem,
    AdviceResponse,
    ErrorResponse,
    HealthDependencies,
    HealthResponse,
    MLDecision,
    PlanningInput,
    PlanningResponse,
    RecommendationInput,
    CitySuggestionItem,
    CitySuggestionsResponse,
)
from services import (
    activity_recommendation,
    assess_confidence,
    build_headline,
    build_reason,
    dependencies_status,
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
api_cache = TTLCache(maxsize=1000, ttl=settings.cache_ttl_seconds)


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
async def cities_search(q: str) -> CitySuggestionsResponse:
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


def _build_recommendation(data: RecommendationInput) -> AdviceResponse:
    cache_key = f"recommendation:{data.city.strip().lower()}:{data.activity}:{data.language}"
    if cache_key in api_cache:
        return AdviceResponse(**api_cache[cache_key])

    live_weather = fetch_weather_data(data.city)
    umbrella_needed, umbrella_text, clothing_text = predict_ml_decisions(live_weather)
    activity_result = activity_recommendation(data.activity or "walking", live_weather)
    reason = build_reason(live_weather)
    ai_advice = generate_llm_advice(
        city=data.city,
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
        "location": data.city,
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


@app.post(
    "/weather/recommendation",
    response_model=AdviceResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
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
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["legacy"],
)
async def get_weather_advice(data: RecommendationInput) -> AdviceResponse:
    return await weather_recommendation(data)


@app.post(
    "/planning/day",
    response_model=PlanningResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["planning"],
)
async def planning_day(data: PlanningInput) -> PlanningResponse:
    try:
        forecast = fetch_forecast_data(data.city)
        best = find_best_time_window(data.activity, forecast)
        return PlanningResponse(
            status="success",
            location=data.city,
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
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    tags=["recommendations"],
)
async def recommendations_activities(data: RecommendationInput) -> ActivitiesResponse:
    try:
        live_weather = fetch_weather_data(data.city)
        results = [
            ActivityRecommendationItem(
                name=activity_result["activity"],
                recommendation=activity_result["recommendation"],
                reason=activity_result["reason"],
            )
            for activity_result in [activity_recommendation(name, live_weather) for name in ("walking", "cycling", "outdoor_dining")]
        ]
        headline = "Best current outdoor options for quick daily decisions."
        return ActivitiesResponse(
            status="success",
            location=data.city,
            headline=headline,
            activities=results,
            live_data=live_weather,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logging.exception("Unhandled error in /recommendations/activities")
        raise HTTPException(status_code=500, detail="Internal server error.") from exc