# Bermuda_Bozok_WeatherWise

WeatherWise is a FastAPI service that converts weather signals into short, human-friendly decisions for daily life. Instead of behaving like a raw weather dashboard, it focuses on product outputs such as whether to take an umbrella, what to wear, which outdoor activity is suitable, and the best time window for that activity.

## Product Scope

- Live weather data from Open-Meteo
- ML-based clothing and umbrella recommendations
- Hugging Face-powered short recommendation copy
- Planning support for daily activity timing
- Postman collection ready for technical checkpoint and jury demo

## Project Structure

```
src/
└── weatherwise/            # Application package
    ├── main.py             # FastAPI routes and error handling
    ├── services.py         # Weather access, ML inference, planning, AI recommendation
    ├── schemas.py          # Request and response models
    ├── config.py           # Environment-based runtime settings
    └── train.py            # ML model training script
models/                     # Trained model artifacts (.joblib)
data/                       # CSV datasets for training
tests/                      # API tests
frontend/                   # Frontend application (React + TypeScript)
postman/                    # Postman workspace files for demo and review
```

## Setup

Recommended runtime: `Python 3.11+` (tested on 3.14)

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install the package with dependencies:
   ```bash
   pip install -e .
   ```
3. (Optional) Install dev/test dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
4. Copy `.env.example` to `.env` and set `HF_API_KEY` if you want LLM-backed copy.
5. Start the API:
   ```bash
   uvicorn weatherwise.main:app --reload --port 8000
   ```

## Environment Variables

- `HF_API_KEY`: Hugging Face Inference Router API key
- `WEATHERWISE_CACHE_TTL_SECONDS`: cache duration in seconds, default `600`
- `WEATHERWISE_REQUEST_TIMEOUT_SECONDS`: outbound weather request timeout, default `5`

Weather lookups use Open-Meteo and do not require a key.

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

- `src/` - Application source code
- `tests/` - Test suite
- `models/` - Trained model artifacts
- `data/` - Training datasets
- `frontend/` - Frontend application
- `postman/` and `.postman/` folders
- `requirements.txt`
- `pyproject.toml`
- `README.md`

### What not to submit

- `.env`
- `.venv/` or `venv/` or `.venv312/`
- `node_modules/`
- `__pycache__/`, `.pytest_cache/`, `.egg-info/`
- `dist/`, `build/`
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
python3 -m pytest
```

## Run on error

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -e ".[dev]"
uvicorn weatherwise.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
