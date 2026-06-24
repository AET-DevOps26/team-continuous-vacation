# Travel Context Service

FastAPI enrichment service that supplies real-world context to itinerary generation. It combines geocoding, event lookup, weather lookup, ranking helpers, and short-lived in-memory caches.

## Responsibilities

- Geocode destinations with Nominatim and Photon fallback.
- Retrieve Google Events through SerpApi when event context is requested.
- Retrieve per-day and per-time-block weather from Open-Meteo.
- Rank and normalize external provider candidates.
- Return best-effort context to GenAI without failing the whole trip flow for optional provider outages.

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8090
python -m pytest --verbose
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html
```

Coverage HTML is written to `htmlcov/index.html`; XML is written to `coverage.xml` for CI artifacts.

## Configuration

Create `.env` from `.env.example` for local provider configuration. `SERPAPI_API_KEY` enables event lookup; without it, event results are skipped. Open-Meteo weather is keyless and controlled by the `WEATHER_*` settings.
