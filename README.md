# Continuous Vacation (Dynamic Travel Itinerary Builder)

## Problem Statement

Planning a trip is often overwhelming, requiring travelers to juggle multiple websites, blogs, and notes to build a coherent daily schedule. While standard AI tools can suggest itineraries, they usually provide static, overwhelming walls of text. If a traveler needs to change one detail—like swapping an outdoor activity due to rain—they have to start over, which often messes up the rest of the timeline. This application solves this by providing a dynamic, visual itinerary where individual time blocks can be independently adjusted, saved, and managed with ease.

### What is the main functionality?

- **Instant Access:** Users can immediately dive into the app and start planning using a seamless demo profile, skipping lengthy registration processes entirely.
- **Custom Trip Creation:** Users input a destination, travel dates, and a preferred "vibe" (e.g., Foodie, Historic, Relaxing). The system generates a highly customized, day-by-day itinerary.
- **Visual Schedule Display:** Instead of a chat interface, the itinerary is presented as an easy-to-read, structured schedule divided into specific Days and time blocks (Morning, Afternoon, Evening).
- **Micro-Regeneration (Spot Editing):** Users can tweak a single activity block (e.g., typing "Swap this for an indoor activity") without regenerating or breaking the rest of their trip schedule.
- **Trip Dashboard & Auto-Save:** All generated itineraries and micro-edits are automatically saved. Users are greeted with a clean dashboard where they can view, resume, or delete their planned trips to keep their workspace organized.
- **Graceful Error Handling:** If the AI encounters a hiccup while generating a plan, the app safely catches the issue and provides a friendly prompt to try again, ensuring the app never freezes or crashes.

### Who are the intended users?

- Casual travelers and weekend backpackers who want to quickly draft a structured travel schedule without spending hours researching.
- Travelers who need on-the-fly flexibility to adjust specific parts of their plans due to weather, changing interests, or time constraints.

### How will you integrate GenAI meaningfully?

- The AI acts as an intelligent, behind-the-scenes travel agent rather than a conversational chatbot.
- Instead of generating free-flowing text, the AI is strictly constrained to output structured scheduling data. It takes the user's destination, dates, and vibe, and returns precise daily activities complete with titles, descriptions, and durations.
- The AI is also used for targeted problem-solving. When a user wants to change a specific block, the AI understands the context of that single activity and offers a suitable replacement based on the user's instructions, leaving the rest of the itinerary perfectly intact.

### Describe some scenarios of how your app will function

**Scenario 1: The Initial Generation (Full System Flow)**
The user opens the app and enters "Munich, 3 days in mid may, sporty vibe." The application processes this request through the AI engine. After a few seconds, the user is presented with a beautifully formatted 3-day schedule, neatly divided into morning, afternoon, and evening blocks with specific activities. This trip is automatically saved to their personal dashboard so they can close the app and return to it later.

**Scenario 2: The Rainy Day Swap (Micro-Regeneration)**
While reviewing their saved trip, the user looks at Day 2, Afternoon: "Walking tour of the English Garden." Realizing the forecast calls for rain, they click an "Edit" button on that specific activity block and type "Make this indoor." The AI processes this targeted request and suggests "Visit the Deutsches Museum." The schedule instantly updates that single card on the screen, keeping the morning and evening plans exactly as they were.

## Local Configuration

The travel context service uses SerpApi for Google Events. Create `travel-context-service/.env` from `travel-context-service/.env.example` and set `SERPAPI_API_KEY`; without it, event lookup is skipped and trip context responses contain no events.

## Service Map

TripTailor runs as five application services plus Postgres:

| Service | Path | Responsibility |
| --- | --- | --- |
| Frontend | `frontend/` | React, Vite, and Refine UI for authentication, trip creation, trip listing, and itinerary editing. |
| Backend API | `backend/` | Public Spring Boot backend-for-frontend. Owns auth, JWT validation, trip orchestration, and calls to internal services. |
| Persistence Service | `persistence-service/` | Internal Spring Boot database access layer for travelers, trips, days, activities, and tags. |
| GenAI Service | `genai-service/` | Internal FastAPI service that prompts the configured LLM and validates structured itinerary output. |
| Travel Context Service | `travel-context-service/` | Internal FastAPI enrichment service for geocoding, events, places, weather, ranking, and cache-backed provider calls. |
| Database | Docker Compose / Helm | PostgreSQL backing the persistence service. |

In Docker Compose and Kubernetes, the gateway exposes the frontend and routes `/api/*` to the backend. Persistence, GenAI, travel-context, and Postgres are internal implementation services.

## Local Commands

Run commands from the module directory unless noted.

| Area | Validate | Coverage |
| --- | --- | --- |
| Frontend | `npm run lint && npm run test && npm run build` | `npm run test:coverage` |
| Backend API | `./gradlew build` | `./gradlew test jacocoTestReport` |
| Persistence Service | `./gradlew build` | `./gradlew test jacocoTestReport` |
| GenAI Service | `pytest --verbose` | `pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html` |
| Travel Context Service | `pytest --verbose` | `pytest --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html` |
| Full local stack | `docker compose up --build` | Not applicable; use module coverage commands. |

Python services expect dependencies from `requirements.txt` and `requirements-dev.txt` to be installed in the active virtual environment.

## Source Of Truth And Generated Files

- OpenAPI contracts live in `api-specification/`. The current persistence contract file is intentionally named `persistance.yaml` for compatibility with existing build scripts.
- `backend/src/main/resources/openapi.yaml` and `persistence-service/src/main/resources/openapi.yaml` are generated by Gradle resource processing from `api-specification/`.
- `frontend/src/lib/api-types.ts` is generated from `api-specification/frontend.yaml` with `npm run generate-api-types`.
- Build output, coverage reports, virtual environments, copied OpenAPI resources, and generated frontend API types are ignored and should not be edited by hand.
