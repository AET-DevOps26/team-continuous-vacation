# GenAI Service

AI-powered itinerary generation service for TripTailor.

## Features

- Generate personalized travel itineraries using LLM
- RESTful API built with FastAPI
- Docker support for easy deployment

## Project Structure

```
genai-service/
├── app/
│   └── main.py                   # FastAPI application
├── Dockerfile
├── requirements.txt
└── .env.example
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

### Docker

Build and run with Docker:
```bash
docker build -t genai-service .
docker run -p 8000:8000 --env-file .env genai-service
```

