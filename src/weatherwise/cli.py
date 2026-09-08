"""
WeatherWise Command-Line Interface (CLI).

Provides terminal commands for querying weather recommendations,
starting the FastAPI server, running model training, and checking system health.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from weatherwise import __version__
from weatherwise.config import get_settings
from weatherwise.services import (
    activity_recommendation,
    assess_confidence,
    build_headline,
    build_reason,
    dependencies_status,
    fetch_weather_data,
    format_coordinate_location,
    model_assets_available,
    predict_ml_decisions,
)


def _cmd_query(args: argparse.Namespace) -> int:
    """Query weather advice and ML recommendations for a city or coordinates."""
    city = args.city
    lat = args.latitude
    lon = args.longitude
    activity = args.activity or "walking"
    lang = args.lang or "en"
    output_json = args.json

    if not city and (lat is None or lon is None):
        print("Error: Either a city name or latitude and longitude must be provided.", file=sys.stderr)
        return 1

    try:
        live = fetch_weather_data(city=city, latitude=lat, longitude=lon)
        umbrella_needed, umbrella_text, clothing_text = predict_ml_decisions(live)
        act_res = activity_recommendation(activity, live)
        headline = build_headline(live, clothing_text, umbrella_needed, lang)
        reason = build_reason(live)
        confidence = assess_confidence(live)
        loc_label = city or format_coordinate_location(lat, lon)

        if output_json:
            result = {
                "location": loc_label,
                "headline": headline,
                "reason": reason,
                "confidence": confidence,
                "weather": live,
                "ml_decision": {
                    "umbrella_needed": umbrella_needed,
                    "clothing_category": clothing_text,
                    "umbrella_text": umbrella_text,
                },
                "activity_advice": act_res,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0

        feels_like = live.get("feels_like_c", live.get("temperature_c"))
        humidity = live.get("humidity_pct", "N/A")
        wind = live.get("wind_speed_kmh", "N/A")
        cond = live.get("weather_condition", "unknown").replace("_", " ").title()

        # Formatted human-friendly CLI output
        print("\n==================================================")
        print(f"WeatherWise CLI -- {loc_label}")
        print("==================================================")
        print(f"Headline:   {headline}")
        print(f"Temp:       {live['temperature_c']}C (Feels like: {feels_like}C)")
        print(f"Condition:  {cond}")
        print(f"Humidity:   {humidity}% | Wind: {wind} km/h")
        print(f"Umbrella:   {'YES (Take an umbrella!)' if umbrella_needed else 'NO (Not needed)'}")
        print(f"Clothing:   {clothing_text.replace('_', ' ').title()}")
        print(f"Activity:   [{activity.title()}] {act_res['recommendation']} -- {act_res['reason']}")
        print(f"Reason:     {reason}")
        print(f"Confidence: {confidence.upper()}")
        print("==================================================\n")
        return 0
    except Exception as exc:
        print(f"Error querying weather for '{city or f'{lat},{lon}'}': {exc}", file=sys.stderr)
        return 1


def _cmd_serve(args: argparse.Namespace) -> int:
    """Launch the FastAPI uvicorn server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: 'uvicorn' is not installed. Please install it with 'pip install uvicorn'.", file=sys.stderr)
        return 1

    host = args.host or "127.0.0.1"
    port = args.port or 8000
    reload = args.reload

    print(f"Starting WeatherWise API server on http://{host}:{port} (reload={reload})...")
    uvicorn.run("weatherwise.main:app", host=host, port=port, reload=reload)
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    """Train the XGBoost umbrella and clothing models."""
    from weatherwise.train import main as train_main

    print("Running WeatherWise XGBoost model training...")
    try:
        train_main()
        print("Model training completed successfully.")
        return 0
    except Exception as exc:
        print(f"Training failed: {exc}", file=sys.stderr)
        return 1


def _cmd_health(args: argparse.Namespace) -> int:
    """Check WeatherWise system health, dependencies, and model status."""
    deps = dependencies_status()
    models_ready = model_assets_available()
    settings = get_settings()

    if args.json:
        data = {
            "version": __version__,
            "models_loaded": models_ready,
            "dependencies": deps,
            "settings": {
                "cache_ttl_seconds": settings.cache_ttl_seconds,
                "request_timeout_seconds": settings.request_timeout_seconds,
                "has_hf_api_key": bool(settings.hf_api_key),
            },
        }
        print(json.dumps(data, indent=2))
        return 0

    print("\n=== WeatherWise Health & System Status ===")
    print(f"Version:            {__version__}")
    print(f"ML Models Loaded:   {'READY' if models_ready else 'NOT LOADED'}")
    print(f"Open-Meteo:         {deps.get('open_meteo', 'N/A')}")
    print(f"Hugging Face:       {'CONFIGURED' if settings.hf_api_key else 'FALLBACK (Deterministic engine)'}")
    print(f"Cache TTL:          {settings.cache_ttl_seconds}s")
    print(f"Request Timeout:    {settings.request_timeout_seconds}s")
    print("==========================================\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the WeatherWise CLI."""
    parser = argparse.ArgumentParser(
        prog="weatherwise",
        description="WeatherWise CLI — AI-powered weather recommendations and assistant.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: query / ask
    query_parser = subparsers.add_parser(
        "query",
        aliases=["ask", "get"],
        help="Get weather recommendations and planning advice for a city.",
    )
    query_parser.add_argument("city", nargs="?", default=None, help="City name (e.g. Istanbul, London, Tokyo)")
    query_parser.add_argument("--lat", "--latitude", dest="latitude", type=float, default=None, help="Latitude")
    query_parser.add_argument("--lon", "--longitude", dest="longitude", type=float, default=None, help="Longitude")
    query_parser.add_argument(
        "-a", "--activity", default="walking", help="Target activity (walking, cycling, outdoor_dining)"
    )
    query_parser.add_argument("-l", "--lang", default="en", help="Response language (en, tr)")
    query_parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted text")
    query_parser.set_defaults(func=_cmd_query)

    # Subcommand: serve
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI backend server.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    serve_parser.add_argument("-p", "--port", type=int, default=8000, help="Port number (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    serve_parser.set_defaults(func=_cmd_serve)

    # Subcommand: train
    train_parser = subparsers.add_parser("train", help="Train and save the XGBoost ML models.")
    train_parser.set_defaults(func=_cmd_train)

    # Subcommand: health
    health_parser = subparsers.add_parser("health", help="Check system status and model readiness.")
    health_parser.add_argument("--json", action="store_true", help="Output health status as JSON")
    health_parser.set_defaults(func=_cmd_health)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main entry point."""
    parser = build_parser()

    raw_args = list(argv if argv is not None else sys.argv[1:])
    subcommands = {"query", "ask", "get", "serve", "train", "health", "-v", "--version", "-h", "--help"}

    if raw_args and raw_args[0] not in subcommands and not raw_args[0].startswith("-"):
        raw_args = ["query"] + raw_args

    if not raw_args:
        parser.print_help()
        return 0

    args = parser.parse_args(raw_args)
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
