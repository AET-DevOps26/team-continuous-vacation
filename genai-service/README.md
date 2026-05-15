# GenAI Service

AI-powered itinerary generation service for TripTailor.

## Features

- Generate personalized travel itineraries using LLM
- RESTful API built with FastAPI (OpenAPI 3.0.3 compliant)
- Docker support for easy deployment
- Type-safe Pydantic models generated from OpenAPI specification

## Project Structure

```
genai-service/
├── app/
│   ├── api/routes/
│   │   └── schedules.py          # OpenAPI spec-compliant routes
│   ├── config/
│   │   └── settings.py           # Environment configuration
│   ├── models/
│   │   └── schemas.py            # OpenAPI spec-generated models
│   ├── services/
│   │   ├── schedule_service.py   # Core AI schedule logic
│   └── main.py                   # FastAPI application
├── tests/
│   └── test_api.py               # API endpoint tests
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## API Endpoints

The service implements the OpenAPI specification defined in `/api-specification/gen-ai.yaml`.

### Generate Schedule
```http
POST /schedules
Content-Type: application/json

{
  "destination": "Munich",
  "startDate": "2026-05-15",
  "endDate": "2026-05-18",
  "vibe": "Sporty and active"
}
```

### Suggest Alternative Activity
```http
POST /activities/alternative
Content-Type: application/json

{
  "instruction": "Make this an indoor activity",
  "activity": { ... },
  "tripContext": { ... }
}
```

### Health Check
```http
GET /health
```

## Setup

### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing and linting
```

3. Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the service:
```bash
uvicorn app.main:app --reload --port 8000
```

5. Run tests:
```bash
pytest
```

6. Run linter:
```bash
flake8 app
```

### Docker

Build and run with Docker:
```bash
docker build -t genai-service .
docker run -p 8000:8000 --env-file .env genai-service
```

## Models

All models are generated from the OpenAPI specification and located in `app/models/schemas.py`:

- **GenerationPreferences**: Input for schedule generation
- **Schedule**: Multi-day schedule with activities
- **Day**: Single day with activities
- **Activity**: Individual activity with time block and tags
- **AlternativeActivityRequest**: Request for activity replacement
- **TripContext**: Full trip context for AI model
- **TimeBlock**: Enum (MORNING, NOON, AFTERNOON, EVENING, NIGHT)
- **ActivityTag**: Enum (OUTDOOR, INDOOR, CULTURAL, SPORTY, etc.)

## TODO

- [ ] Implement LLM integration (OpenAI, Anthropic, etc.)
- [ ] Add proper error handling and logging
- [ ] Implement caching mechanism
- [ ] Add rate limiting
- [ ] Add authentication/authorization
- [ ] Implement prompt engineering for better results
- [ ] Add metrics and monitoring
