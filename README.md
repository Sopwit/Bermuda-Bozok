# Bermuda_Bozok_WeatherWise

WeatherWise is a FastAPI service that converts weather signals into short, human-friendly decisions for daily life. Instead of behaving like a raw weather dashboard, it focuses on product outputs such as whether to take an umbrella, what to wear, which outdoor activity is suitable, and the best time window for that activity.

## Product Scope

- Live weather data from OpenWeatherMap
- ML-based clothing and umbrella recommendations
- Gemini-powered short recommendation copy
- Planning support for daily activity timing
- Postman collection ready for technical checkpoint and jury demo

## Project Structure

- `main.py`: FastAPI routes and error handling
- `services.py`: weather access, ML inference, planning, and AI recommendation logic
- `schemas.py`: request and response models
- `config.py`: environment-based runtime settings
- `tests/`: API tests
- `postman/`: Postman workspace files for demo and review
- `model_metadata.json`: model artifact generation metadata

## Setup

Recommended runtime: `Python 3.12`

1. Create a virtual environment with `python3.12 -m venv .venv312`.
2. Activate it with `source .venv312/bin/activate`.
3. Install dependencies with `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in your API keys.
5. Start the API with `uvicorn main:app --reload --port 8000`.

## Environment Variables

- `OWM_API_KEY`: OpenWeatherMap API key
- `GEMINI_API_KEY`: Gemini API key
- `WEATHERWISE_CACHE_TTL_SECONDS`: cache duration in seconds, default `1800`
- `WEATHERWISE_REQUEST_TIMEOUT_SECONDS`: outbound weather request timeout, default `10`

## API Endpoints

### `GET /health`

Returns service health, dependency readiness, and model artifact status.

### `POST /weather/recommendation`

Generates a short product-ready weather recommendation.

Example request:

```json
{
  "city": "Ankara",
  "activity": "walking",
  "language": "en"
}
```

### `POST /planning/day`

Returns the best near-term time window for an activity using forecast data.

### `POST /recommendations/activities`

Returns quick suitability signals for walking, cycling, and outdoor dining.

### `POST /get-advice`

Legacy compatibility route that mirrors `/weather/recommendation`.

## Postman Demo Flow

The Postman collection is organized for jury-friendly review:

1. `Health Check`
2. `Generate Smart Recommendation`
3. `Plan Best Time Window`
4. `Review Outdoor Activities`
5. `Invalid City Validation`

Use the `Local` environment and run the backend on port `8000`.

## Hackathon Delivery Notes

### What to submit to GitHub

- Backend source files
- `postman/` and `.postman/` folders
- `requirements.txt`
- `README.md`
- `model_metadata.json`
- Model artifacts used by the API

### What not to submit

- `.env`
- `.venv/` or `.venv312/`
- local cache folders

### Recommended jury demo order

1. Start backend on port `8000`
2. Show `GET /health`
3. Show `POST /weather/recommendation`
4. Show `POST /planning/day`
5. Show `POST /recommendations/activities`
6. Show invalid city error handling

### Short demo script

- `Health Check`: “First, we verify that the service is running and all model assets are loaded.”
- `Generate Smart Recommendation`: “This is the core product value. We transform weather into a short decision, not just raw data.”
- `Plan Best Time Window`: “We also help users decide when an activity is best.”
- `Review Outdoor Activities`: “The API compares multiple outdoor options for quick daily decision-making.”
- `Invalid City Validation`: “The API fails gracefully with standardized error responses, which makes frontend integration safer.”

### Postman Cloud

For demo reliability, the primary review path should remain the desktop `Local` workspace connected to this repository.

If you also want the collection to appear in the Postman web workspace, use `Publish local version to Postman Cloud` from the Postman desktop app after finalizing the collection. Do not publish secret API keys or `.env` contents.

## Test

Run:

```bash
.venv312/bin/python -m pytest
```

## Run on error

### Backend

python -m venv venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000


### Frontend

cd frontend

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

npm install

npm run dev
