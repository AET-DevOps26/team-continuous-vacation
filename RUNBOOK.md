# TripTailor Runbook

This runbook is a detailed guide for evaluating, running, and explaining the
TripTailor application. It is written for a tutor who wants to understand the
full system, verify it locally, inspect the implementation, and troubleshoot the
most common problems.

## Start Here: Access and Setup

Use this section first. It shows where the running application is hosted, which
URLs expose which services, and how to start the same system locally.

### Recommended Hosted Access: AET Cluster

For tutor evaluation, use the AET Kubernetes deployment first. It has a stable
HTTPS hostname, while the Azure VM deployment can receive a new public IP after
some redeployments.

| Service or UI | Hosted URL | Notes |
| --- | --- | --- |
| Main application | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/` | Stable public entrypoint for the deployed TripTailor app. |
| Backend API through ingress | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/` | Public API prefix used by the frontend. |
| Backend health | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/health` | Quick backend reachability check. |
| Backend OpenAPI | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/openapi.yaml` | Public backend API contract. |
| Demo login endpoint | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/auth/demo` | Creates a demo traveler session. |
| Trips endpoint | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/trips` | Requires a bearer token from login/demo login. |
| Prometheus | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus` | Prometheus UI and metrics target inspection. |
| Prometheus targets | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus/targets` | Shows scrape status for runtime services. |
| Prometheus alerts | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus/alerts` | Shows alert rule state. |
| Grafana | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/grafana/` | Dashboards and trace exploration. |
| Grafana health | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/grafana/api/health` | Verifies Grafana through the ingress. |

Suggested hosted evaluation flow:

1. Open `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/`.
2. Use demo login.
3. Create a short future trip.
4. Open the generated itinerary.
5. Regenerate one activity, for example with "Make this indoor".
6. Open Prometheus or Grafana from the monitoring links in the UI, or use the
   direct URLs above.

### Azure VM Access

The Azure VM deployment is also supported, but its public IP can change. Resolve
the current IP first, then use the gateway on port `3000`.

Find the Azure VM public IP:

```bash
az login
az account set --subscription "<subscription-id>"

AZURE_VM_PUBLIC_IP="$(
  az network public-ip show \
    --resource-group triptailor-rg \
    --name triptailor-pip \
    --query ipAddress \
    --output tsv
)"

echo "${AZURE_VM_PUBLIC_IP}"
```

Azure VM URLs:

| Service or UI | Azure URL |
| --- | --- |
| Main application | `http://<AZURE_VM_PUBLIC_IP>:3000/` |
| Backend API through gateway | `http://<AZURE_VM_PUBLIC_IP>:3000/api/` |
| Backend health | `http://<AZURE_VM_PUBLIC_IP>:3000/api/health` |
| Backend OpenAPI | `http://<AZURE_VM_PUBLIC_IP>:3000/api/openapi.yaml` |
| Demo login endpoint | `http://<AZURE_VM_PUBLIC_IP>:3000/api/auth/demo` |
| Trips endpoint | `http://<AZURE_VM_PUBLIC_IP>:3000/api/trips` |
| Prometheus | `http://<AZURE_VM_PUBLIC_IP>:3000/prometheus/` |
| Prometheus targets | `http://<AZURE_VM_PUBLIC_IP>:3000/prometheus/targets` |
| Grafana | `http://<AZURE_VM_PUBLIC_IP>:3000/grafana/` |
| Grafana health | `http://<AZURE_VM_PUBLIC_IP>:3000/grafana/api/health` |

Internal Azure VM services are not public as standalone URLs. To inspect them,
SSH into the VM and use Docker Compose:

```bash
ssh tripadmin@<AZURE_VM_PUBLIC_IP>
cd /opt/triptailor

docker compose ps
docker compose exec gateway wget -qO- http://backend:8080/health
docker compose exec gateway wget -qO- http://persistence-service:8081/health
docker compose exec gateway wget -qO- http://genai-service:8000/health
curl -fsS http://localhost:8090/health
curl -fsS http://localhost:3200/ready
```

### Local Setup With Docker Compose

Docker Compose is the fastest way to run the complete system locally.

Prerequisites:

| Tool | Purpose |
| --- | --- |
| Docker with Docker Compose | Runs the full local stack. |
| curl | Health checks and smoke tests. |
| Optional `jq` | Easier manual API testing. |

Optional local provider configuration:

```bash
cp genai-service/.env.example genai-service/.env
cp travel-context-service/.env.example travel-context-service/.env
```

Set real secrets in those `.env` files if you want real Azure OpenAI or SerpApi
event lookup. Without `SERPAPI_API_KEY`, event lookup is skipped; weather and
geocoding still work. Do not commit `.env` files.

Start locally:

```bash
docker compose up --detach --build
```

Run the smoke test:

```bash
bash scripts/docker-compose-smoke.sh
```

Local URLs:

| Service or UI | Local URL |
| --- | --- |
| Main application | `http://localhost:3000/` |
| Backend health through gateway | `http://localhost:3000/api/health` |
| Grafana through gateway | `http://localhost:3000/grafana/` |
| Grafana direct | `http://localhost:3001` |
| Prometheus through gateway | `http://localhost:3000/prometheus/` |
| Prometheus direct | `http://localhost:9090` |
| Travel context health | `http://localhost:8090/health` |
| Tempo readiness | `http://localhost:3200/ready` |
| PostgreSQL from host | `localhost:5433`, database `triptailor`, user `tripuser`, password `trippassword` |

Stop locally:

```bash
docker compose down
```

Reset all local runtime data:

```bash
docker compose down --volumes
```

### Local Setup With Kubernetes

Use this when evaluating the Helm chart, Kubernetes services, load balancing, or
autoscaling demos.

Prerequisites:

| Tool | Purpose |
| --- | --- |
| Docker | Builds local service images. |
| kubectl | Talks to the local Kubernetes cluster. |
| Helm | Installs the chart. If missing, `start.sh` downloads a temporary Helm binary. |

Start local Kubernetes deployment:

```bash
./start.sh
```

The script builds missing images, installs or upgrades the Helm release, waits
for deployments, and prints:

```text
http://localhost:30080
```

Useful Kubernetes checks:

```bash
kubectl -n triptailor-local get pods,svc,ingress
kubectl -n triptailor-local rollout status deploy/backend
kubectl -n triptailor-local logs deploy/backend
```

Run demo scripts:

```bash
./scripts/demo-load-balancing.sh
./scripts/demo-autoscaling.sh
./scripts/demo-tracing.sh
```

## Table of Contents

| Section | Description |
| --- | --- |
| [Start Here: Access and Setup](#start-here-access-and-setup) | Hosted URLs and local setup paths. |
| [1. Executive Summary](#1-executive-summary) | Short product and architecture overview. |
| [2. Repository Map](#2-repository-map) | Important files and directories. |
| [3. Application Capabilities](#3-application-capabilities) | User-facing workflows and system behavior. |
| [4. Local Quick Start With Docker Compose](#4-local-quick-start-with-docker-compose) | Local prerequisites, environment files, startup, smoke tests, and reset commands. |
| [5. Manual API Demo](#5-manual-api-demo) | cURL-based demo flow through the gateway. |
| [6. Runtime Request Flows](#6-runtime-request-flows) | Auth, trip generation, and activity regeneration sequences. |
| [7. Public and Internal APIs](#7-public-and-internal-apis) | Backend, persistence, GenAI, and travel-context endpoint maps. |
| [8. Data Model](#8-data-model) | Database tables and domain objects. |
| [9. GenAI Behavior](#9-genai-behavior) | LLM provider setup, prompts, validation, and failure behavior. |
| [10. Travel Context Behavior](#10-travel-context-behavior) | Geocoding, events, weather, and caching. |
| [11. Frontend Behavior](#11-frontend-behavior) | Frontend routing, API provider, and auth storage. |
| [12. Backend Service Details](#12-backend-service-details) | Security, JWTs, metrics, and tracing. |
| [13. Persistence Service Details](#13-persistence-service-details) | Database service configuration and ownership. |
| [14. Observability](#14-observability) | Metrics, dashboards, traces, alerts, and validation. |
| [15. Validation and Tests](#15-validation-and-tests) | Commands for frontend, Kotlin services, Python services, and full stack checks. |
| [16. CI/CD](#16-cicd) | GitHub Actions workflows for CI, images, AET, and Azure VM deployment. |
| [17. Kubernetes Runbook](#17-kubernetes-runbook) | Local Kubernetes, Helm, demos, and stable AET hosted URLs. |
| [18. Azure VM Runbook](#18-azure-vm-runbook) | Azure VM discovery, service URLs, Terraform, and Ansible. |
| [19. Troubleshooting](#19-troubleshooting) | Common failures and diagnostic commands. |
| [20. Common Evaluation Script](#20-common-evaluation-script) | Concise tutor demo checklist. |
| [21. What to Inspect in the Code](#21-what-to-inspect-in-the-code) | Recommended code-reading order. |
| [22. Known Limitations and Design Tradeoffs](#22-known-limitations-and-design-tradeoffs) | Current constraints and tradeoffs. |
| [23. File Generation Rules](#23-file-generation-rules) | Generated files and their sources. |
| [24. Cleanup Checklist](#24-cleanup-checklist) | Final checks before hand-in or demo. |

## 1. Executive Summary

TripTailor is a dynamic travel itinerary builder. A traveler creates a trip by
entering a destination, start date, end date, and travel vibe. The application
generates a structured day-by-day itinerary with activity cards instead of a
chat transcript. After generation, the traveler can regenerate one activity at a
time, for example "make this indoor", without replacing the whole itinerary.

The system is built as a small microservice application:

| Component | Path | Technology | Role |
| --- | --- | --- | --- |
| Gateway | `infrastructure/gateway/nginx.conf` | NGINX | Single browser entrypoint. Routes `/` to frontend, `/api/*` to backend, `/grafana/` to Grafana, and `/prometheus/` to Prometheus. |
| Frontend | `frontend/` | React 19, Vite, Refine, shadcn-style UI | User interface for login/demo session, trip list, trip creation, trip details, activity regeneration, and deletion. |
| Backend API | `backend/` | Kotlin, Spring Boot | Public backend-for-frontend. Owns authentication, JWT validation, API validation, orchestration, metrics, and traces. |
| Persistence Service | `persistence-service/` | Kotlin, Spring Boot, JDBC | Internal database API. Owns all SQL and PostgreSQL access. |
| GenAI Service | `genai-service/` | Python, FastAPI | Internal AI service. Builds prompts, calls Azure/OpenAI-compatible LLM, validates structured output, assigns IDs. |
| Travel Context Service | `travel-context-service/` | Python, FastAPI | Internal enrichment service. Fetches geocoding, weather, and optional events. Caches provider responses. |
| Database | Docker Compose / Helm | PostgreSQL 17 | Stores travelers, trips, days, activities, and activity tags. |
| Monitoring | `monitoring/` symlink to chart files | Prometheus, Grafana, Tempo | Metrics, dashboards, alerts, and distributed traces. |

The browser never calls the internal services directly. It calls the gateway at
`http://localhost:3000`, and all application API traffic goes through
`/api/*`, which the gateway forwards to the backend service.

## 2. Repository Map

Important root-level files and directories:

| Path | Purpose |
| --- | --- |
| `README.md` | Main project overview and architecture summary. |
| `RUNBOOK.md` | This evaluator-facing runbook. |
| `docker-compose.yml` | Full local stack: gateway, frontend, backend, persistence, GenAI, travel context, Postgres, Prometheus, Tempo, Grafana. |
| `start.sh` | Local Kubernetes helper that builds missing images and installs the Helm chart. |
| `scripts/docker-compose-smoke.sh` | Smoke test for the Docker Compose stack. |
| `scripts/demo-load-balancing.sh` | Demonstrates Kubernetes service-level load balancing for backend replicas. |
| `scripts/demo-autoscaling.sh` | Demonstrates backend HPA behavior. |
| `scripts/demo-tracing.sh` | Demonstrates distributed tracing. |
| `api-specification/` | OpenAPI contracts for frontend, persistence, GenAI, and travel-context boundaries. |
| `diagrams/` | PlantUML architecture, use-case, flow, and object model diagrams. |
| `infrastructure/kubernetes/triptailor/` | Helm chart for Kubernetes deployment. |
| `infrastructure/terraform/` | Azure VM provisioning. |
| `infrastructure/ansible/` | Azure VM application deployment using Docker Compose. |
| `.github/workflows/ci.yaml` | CI quality gate and Docker Compose verification. |
| `.github/workflows/images.yaml` | Container image publishing and AET Kubernetes deployment. |
| `.github/workflows/azure-vm-deploy.yaml` | Azure VM provisioning and deployment workflow. |

## 3. Application Capabilities

The user-facing product supports these workflows:

| Workflow | User action | System behavior |
| --- | --- | --- |
| Demo access | User opens the app and starts without registration. | Frontend calls `POST /auth/demo`; backend creates a demo traveler through persistence and returns a JWT. |
| Registration | User enters email and password. | Backend hashes password with BCrypt, creates traveler, and returns a JWT. |
| Login | User enters email and password. | Backend fetches auth record from persistence, verifies BCrypt password, and returns a JWT. |
| Trip generation | User enters destination, dates, and vibe. | Backend validates dates, calls GenAI for a schedule, saves the trip through persistence, and returns the full trip. |
| Trip list | User opens dashboard. | Frontend calls `GET /trips`; backend returns summaries owned by the authenticated traveler. |
| Trip details | User opens a trip. | Frontend calls `GET /trips/{tripId}`; backend returns the full schedule. |
| Activity regeneration | User edits one activity with a text instruction. | Backend fetches the whole trip, asks GenAI for one replacement, persists only that activity, and returns it. |
| Activity deletion | User deletes one card. | Backend verifies ownership by fetching the trip, then persistence deletes the activity. |
| Trip deletion | User deletes a trip. | Persistence deletes the trip; SQL cascading deletes days, activities, and tags. |

The central design goal is structured itinerary data. The GenAI output is not
stored as plain text. It is validated into days and activities with fields such
as `timeBlock`, `durationMinutes`, `isIndoor`, and `tags`.

## 4. Local Quick Start With Docker Compose

### 4.1 Prerequisites

Install:

| Tool | Used for |
| --- | --- |
| Docker with Docker Compose | Running the complete local stack. |
| curl | Health checks and smoke tests. |
| Node.js 20 | Frontend development and tests. |
| Java 21 | Kotlin Spring Boot services. |
| Python 3.11 | FastAPI services and tests. |

Optional but useful:

| Tool | Used for |
| --- | --- |
| kubectl | Local or remote Kubernetes inspection. |
| Helm | Kubernetes deployment. `start.sh` can download Helm if missing. |
| Terraform | Azure VM provisioning. |
| Ansible | Azure VM deployment. |

### 4.2 Secrets and Environment Files

For local Docker Compose, the GenAI service loads `genai-service/.env.example`
and optionally `genai-service/.env`. The travel context service loads
`travel-context-service/.env.example` and optionally `travel-context-service/.env`.

Create local override files when real provider calls are required:

```bash
cp genai-service/.env.example genai-service/.env
cp travel-context-service/.env.example travel-context-service/.env
```

Important local variables:

| File | Variable | Meaning |
| --- | --- | --- |
| `genai-service/.env` | `LLM_PROVIDER` | `azure` or `local`. |
| `genai-service/.env` | `AZURE_LLM_API_KEY` | Required when `LLM_PROVIDER=azure`. |
| `genai-service/.env` | `AZURE_LLM_BASE_URL` | Azure OpenAI endpoint. |
| `genai-service/.env` | `MODEL_NAME` | Azure deployment name or OpenAI-compatible model name. |
| `genai-service/.env` | `LOCAL_LLM_BASE_URL` | Local OpenAI-compatible endpoint, for example Ollama. |
| `travel-context-service/.env` | `SERPAPI_API_KEY` | Optional. If absent, event lookup is skipped and weather/geocoding still work. |

Do not commit `.env` files with real secrets.

### 4.3 Start the Stack

From the repository root:

```bash
docker compose up --build
```

Or run in the background:

```bash
docker compose up --detach --build
```

Main local URLs:

| Service | URL |
| --- | --- |
| Application gateway | `http://localhost:3000` |
| Backend health through gateway | `http://localhost:3000/api/health` |
| Travel context health | `http://localhost:8090/health` |
| Prometheus direct | `http://localhost:9090` |
| Prometheus through gateway | `http://localhost:3000/prometheus/` |
| Grafana direct | `http://localhost:3001` |
| Grafana through gateway | `http://localhost:3000/grafana/` |
| Tempo readiness | `http://localhost:3200/ready` |
| PostgreSQL from host | `localhost:5433`, database `triptailor`, user `tripuser`, password `trippassword` |

Internal-only service names inside Compose:

| Service | Internal URL |
| --- | --- |
| Backend | `http://backend:8080` |
| Persistence | `http://persistence-service:8081` |
| GenAI | `http://genai-service:8000` |
| Travel context | `http://travel-context-service:8090` |
| Postgres | `db:5432` |

### 4.4 Smoke Test the Stack

In another terminal:

```bash
bash scripts/docker-compose-smoke.sh
```

The script checks:

| Check | Target |
| --- | --- |
| Frontend through gateway | `http://localhost:3000/` |
| Backend through gateway | `http://localhost:3000/api/health` |
| Persistence from Compose network | `http://persistence-service:8081/health` |
| GenAI from Compose network | `http://genai-service:8000/health` |
| Travel context from host | `http://localhost:8090/health` |
| Prometheus through gateway | `http://localhost:3000/prometheus/-/healthy` |
| Grafana through gateway | `http://localhost:3000/grafana/api/health` |
| Tempo | `http://localhost:3200/ready` |
| Container state | no service should be exited |

Useful smoke-test overrides:

```bash
GATEWAY_URL=http://localhost:3000 \
TEMPO_URL=http://localhost:3200 \
TRAVEL_CONTEXT_URL=http://localhost:8090 \
SMOKE_RETRIES=60 \
SMOKE_SLEEP_SECONDS=2 \
bash scripts/docker-compose-smoke.sh
```

### 4.5 Stop and Reset

Stop containers but keep database and Prometheus volumes:

```bash
docker compose down
```

Stop and delete volumes, including the local database:

```bash
docker compose down --volumes
```

Use the volume reset when demo data or schema state is confusing.

## 5. Manual API Demo

These commands exercise the backend through the gateway, the same way the
frontend does.

### 5.1 Create a Demo Session

```bash
TOKEN="$(
  curl -fsS -X POST http://localhost:3000/api/auth/demo \
    -H 'Content-Type: application/json' \
  | jq -r '.accessToken'
)"
```

If `jq` is not available, call the endpoint and copy the `accessToken` manually:

```bash
curl -fsS -X POST http://localhost:3000/api/auth/demo \
  -H 'Content-Type: application/json'
```

### 5.2 List Trips

```bash
curl -fsS http://localhost:3000/api/trips \
  -H "Authorization: Bearer ${TOKEN}"
```

### 5.3 Generate a Trip

Use dates today or later. The frontend enforces a maximum of 14 days; the backend
validates only that `endDate` is on or after `startDate`.

```bash
curl -fsS -X POST http://localhost:3000/api/trips \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{
    "destination": "Munich",
    "startDate": "2026-08-10",
    "endDate": "2026-08-12",
    "vibe": "Historic and cultural"
  }'
```

Save the returned `trip.id`, one `day.id`, and one `activity.id` to test
regeneration.

### 5.4 Regenerate One Activity

```bash
curl -fsS -X PATCH \
  "http://localhost:3000/api/trips/${TRIP_ID}/days/${DAY_ID}/activities/${ACTIVITY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d '{ "instruction": "Make this indoor and suitable for rainy weather" }'
```

### 5.5 Delete One Activity

```bash
curl -fsS -X DELETE \
  "http://localhost:3000/api/trips/${TRIP_ID}/days/${DAY_ID}/activities/${ACTIVITY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -i
```

Expected status: `204 No Content`.

## 6. Runtime Request Flows

### 6.1 Demo Authentication Flow

1. Browser loads frontend from gateway.
2. Frontend checks local storage for `access_token`.
3. If absent, the login page can create a demo session.
4. Frontend calls `POST /api/auth/demo`.
5. Gateway strips `/api/` and forwards to backend `POST /auth/demo`.
6. Backend calls persistence `POST /travelers` with `isDemo: true`.
7. Persistence inserts a row into `travelers`.
8. Backend signs an HS256 JWT with the traveler UUID as `sub`.
9. Frontend stores `access_token`, `traveler_id`, and `is_demo` in local storage.

### 6.2 Registered Login Flow

1. Frontend calls `POST /api/auth/login` with email and password.
2. Backend calls persistence `GET /travelers/auth-record?email=...`.
3. Persistence returns email, password hash, traveler ID, demo flag, and created timestamp.
4. Backend verifies the submitted password with BCrypt.
5. Backend returns a signed JWT.

Security detail: the auth-record endpoint is internal and must not be exposed
publicly, because it returns password hashes for backend verification.

### 6.3 Trip Generation Flow

1. Frontend validates the form with Zod:
   - destination required
   - start date required
   - end date required
   - vibe required
   - start date cannot be in the past
   - end date must be on or after start date
   - trip duration cannot exceed 14 days
2. Frontend calls `POST /api/trips`.
3. Backend authenticates the JWT and extracts traveler UUID from the token subject.
4. Backend validates that `endDate >= startDate`.
5. Backend starts an observation named `trip.generate`.
6. Backend calls GenAI `POST /schedules`.
7. GenAI asks its relevance classifier whether event context is useful.
8. GenAI calls travel context `POST /trip-context`.
9. Travel context geocodes the destination.
10. Travel context fetches weather for each requested day.
11. Travel context optionally fetches SerpApi Google Events if event context is relevant and `SERPAPI_API_KEY` is configured.
12. GenAI builds the schedule prompt with trip preferences, real events, and weather.
13. GenAI calls the configured LLM provider.
14. GenAI parses JSON, sanitizes activity tags, validates the schedule contract, and assigns UUIDs.
15. Backend creates a trip ID and calls persistence `POST /trips?travelerId=...`.
16. Persistence inserts `trips`, `days`, `activities`, and `activity_tags` in one transaction.
17. Backend returns the saved trip to the frontend.
18. Frontend navigates to the trip detail page.

### 6.4 Activity Regeneration Flow

1. User opens an activity card and enters an instruction.
2. Frontend calls `PATCH /api/trips/{tripId}/days/{dayId}/activities/{activityId}`.
3. Backend authenticates the JWT.
4. Backend fetches the full trip from persistence to verify ownership and get context.
5. Backend locates the target activity in the returned schedule.
6. Backend calls GenAI `POST /activities/alternative` with:
   - user instruction
   - activity being replaced
   - complete trip context
7. GenAI builds a replacement prompt.
8. GenAI calls the LLM.
9. GenAI validates that the replacement title is not the old title and does not duplicate any other trip activity.
10. GenAI assigns a new activity UUID and keeps the original day ID.
11. Backend calls persistence `PUT /trips/{tripId}/days/{dayId}/activities/{activityId}`.
12. Persistence verifies that the old activity belongs to the trip and day.
13. Persistence deletes old activity tags, deletes the old activity row, inserts the replacement activity, and inserts replacement tags.
14. Backend returns the replacement activity.
15. Frontend refetches the trip to display the updated schedule.

## 7. Public and Internal APIs

OpenAPI specifications live in `api-specification/`.

| Contract | File | Runtime owner |
| --- | --- | --- |
| Public frontend/backend API | `api-specification/frontend.yaml` | Backend API |
| Internal persistence API | `api-specification/persistance.yaml` | Persistence service |
| Internal GenAI API | `api-specification/gen-ai.yaml` | GenAI service |
| Internal travel context API | `api-specification/travel-context.yaml` | Travel context service |

Note: `persistance.yaml` is intentionally misspelled for compatibility with
existing build scripts.

### 7.1 Backend Public Endpoints

Through gateway, prefix these with `/api`. Directly inside the backend service,
use the path without `/api`.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | no | Backend health. |
| `GET` | `/openapi.yaml` | no | Generated/copy public OpenAPI document. |
| `GET` | `/actuator/health` | no | Spring actuator health. |
| `GET` | `/actuator/prometheus` | no | Prometheus scrape endpoint. |
| `POST` | `/auth/demo` | no | Create anonymous demo traveler and JWT. |
| `POST` | `/auth/register` | no | Register traveler and JWT. |
| `POST` | `/auth/login` | no | Login and JWT. |
| `GET` | `/trips` | yes | List authenticated traveler's trips. |
| `POST` | `/trips` | yes | Generate and save a trip. |
| `GET` | `/trips/{tripId}` | yes | Get a full trip. |
| `DELETE` | `/trips/{tripId}` | yes | Delete a trip. |
| `PATCH` | `/trips/{tripId}/days/{dayId}/activities/{activityId}` | yes | Regenerate one activity. |
| `DELETE` | `/trips/{tripId}/days/{dayId}/activities/{activityId}` | yes | Delete one activity. |
| `GET` | `/debug/instance` | no | Debug endpoint used to demonstrate load balancing. |

### 7.2 Persistence Endpoints

These are internal. They are reachable inside Compose/Kubernetes through
`persistence-service:8081`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health. |
| `GET` | `/actuator/prometheus` | Metrics. |
| `POST` | `/travelers` | Create demo or registered traveler. |
| `GET` | `/travelers?email=...` | Find non-sensitive traveler profile by email. |
| `GET` | `/travelers/auth-record?email=...` | Find login auth record, including password hash. |
| `GET` | `/travelers/{travelerId}` | Get traveler by UUID. |
| `GET` | `/trips?travelerId=...` | List trip summaries. |
| `POST` | `/trips?travelerId=...` | Save full trip. |
| `GET` | `/trips/{tripId}?travelerId=...` | Get full trip owned by traveler. |
| `DELETE` | `/trips/{tripId}?travelerId=...` | Delete trip owned by traveler. |
| `PUT` | `/trips/{tripId}/days/{dayId}/activities/{activityId}` | Replace one activity. |
| `DELETE` | `/trips/{tripId}/days/{dayId}/activities/{activityId}` | Delete one activity. |

### 7.3 GenAI Endpoints

These are internal. They are reachable inside Compose/Kubernetes through
`genai-service:8000`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health. |
| `GET` | `/metrics` | Metrics. |
| `POST` | `/schedules` | Generate complete schedule from preferences. |
| `POST` | `/activities/alternative` | Generate one replacement activity. |

### 7.4 Travel Context Endpoints

The service is internal in Kubernetes but also exposed on host port `8090` in
Docker Compose for debugging.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health. |
| `GET` | `/metrics` | Metrics. |
| `POST` | `/trip-context` | Build geocoding, weather, and optional event context. |

## 8. Data Model

The database schema is defined in
`persistence-service/src/main/resources/schema.sql`.

### 8.1 Tables

| Table | Main columns | Notes |
| --- | --- | --- |
| `travelers` | `id`, `email`, `password_hash`, `is_demo`, `created_at` | `email` is unique and nullable for demo users. |
| `trips` | `id`, `traveler_id`, `destination`, `start_date`, `end_date`, `vibe` | `traveler_id` references `travelers(id)` with cascade delete. |
| `days` | `id`, `trip_id`, `day_number`, `date` | `trip_id` references `trips(id)` with cascade delete. |
| `activities` | `id`, `day_id`, `time_block`, `title`, `description`, `duration_minutes`, `is_indoor` | `day_id` references `days(id)` with cascade delete. |
| `activity_tags` | `activity_id`, `tag` | Composite primary key on activity and tag. |

### 8.2 Domain Objects

The same core objects appear in Kotlin models, Python Pydantic models, and
OpenAPI schemas:

| Object | Meaning |
| --- | --- |
| `Traveler` | A registered or demo user. |
| `TripSummary` | Lightweight trip list row. |
| `Trip` | Destination, date range, vibe, and full schedule. |
| `Schedule` | Wrapper containing ordered days. |
| `Day` | One calendar day in the itinerary. |
| `Activity` | One scheduled item in a time block. |
| `TimeBlock` | `MORNING`, `NOON`, `AFTERNOON`, `EVENING`, `NIGHT`. |
| `ActivityTag` | `OUTDOOR`, `INDOOR`, `CULTURAL`, `SPORTY`, `RELAXING`, `ADVENTUROUS`, `FOOD`, `SHOPPING`, `ENTERTAINMENT`, `FAMILY_FRIENDLY`, `PARTY`. |

### 8.3 Persistence Behavior

Important repository behavior:

| Behavior | Implementation detail |
| --- | --- |
| Traveler creation | Registered travelers require email and password hash. Demo travelers only require `isDemo=true`. |
| Email normalization | Emails are lowercased before lookup and insert. |
| Trip save | Inserts trip, days, activities, and activity tags in one transaction. |
| Trip ownership | `getTrip` selects by both `tripId` and `travelerId`; this is how public backend requests enforce ownership. |
| Trip delete | Calls `getTrip` first for ownership and 404 behavior, then deletes from `trips`; child rows cascade. |
| Activity update | Verifies activity belongs to the specified trip/day, deletes the old activity, inserts replacement with the supplied new ID. |
| Activity delete | Verifies activity belongs to the specified trip/day, then deletes it. |

## 9. GenAI Behavior

### 9.1 Provider Configuration

The GenAI service supports:

| Provider | `LLM_PROVIDER` | Implementation |
| --- | --- | --- |
| Azure OpenAI | `azure` | Uses the official OpenAI Python SDK `AzureOpenAI`. Requires `AZURE_LLM_API_KEY`. |
| OpenAI-compatible local provider | `local` | Uses `httpx` against `${LOCAL_LLM_BASE_URL}/chat/completions`. Suitable for local compatible APIs. |

The default `.env.example` points to Azure and model/deployment
`gpt-5-nano`. Kubernetes `values.yaml` defaults to `LLM_PROVIDER=local` with an
invalid Azure URL unless real secrets/values are supplied.

### 9.2 Schedule Prompt Inputs

The schedule prompt includes:

| Input | Source |
| --- | --- |
| Destination, start date, end date, vibe | Frontend form through backend. |
| Expected dates | Computed from start/end date. |
| Real events | Travel context service, if the relevance classifier chooses event context and SerpApi is configured. |
| Weather outlook | Travel context service, forecast or historical estimate per day and time block. |
| Output schema | Hard-coded prompt instructions. |

### 9.3 Schedule Validation

The GenAI service rejects model output unless it satisfies these rules:

| Rule | Why it matters |
| --- | --- |
| Response must be parseable JSON. | Prevents storing free-form text. |
| Response must validate against Pydantic generated schedule models. | Ensures required fields and enum values are correct. |
| Exactly one day per requested date. | Prevents missing or extra days. |
| Day numbers must be sequential from 1. | Keeps UI ordering deterministic. |
| Day dates must match requested dates exactly. | Prevents model drift. |
| Each day must contain 3 to 5 activities. | Keeps itineraries useful but not overloaded. |
| A time block can appear only once per day. | Prevents duplicate morning/afternoon cards. |
| Activity titles must be unique across the trip. | Prevents repeated itinerary items. |
| Tags are sanitized and unsupported tags are dropped. | Keeps persisted enums valid. |

If validation fails, GenAI raises `ScheduleGenerationError` and the API returns
HTTP `502`.

### 9.4 Alternative Activity Validation

The alternative endpoint rejects output unless:

| Rule | Meaning |
| --- | --- |
| Response is one activity, not a full schedule. | Only one card changes. |
| Title differs from the replaced activity title. | Ensures the model did not return the same idea. |
| Title does not duplicate another existing activity. | Prevents duplicate cards in the trip. |
| Activity validates against the Pydantic schema. | Required fields and enum values are valid. |

The backend copies the original day ID onto the replacement before persisting.

### 9.5 Travel Context Failures

The GenAI `TravelContextClient` treats travel context as best effort. If the
travel context call fails or times out, GenAI logs a warning and continues with
`None` context. In that case the prompt contains empty event and weather context,
but schedule generation can still proceed if the LLM provider is working.

## 10. Travel Context Behavior

The travel context service enriches trip generation with real-world context.

### 10.1 Providers

| Provider | Purpose | Secret required |
| --- | --- | --- |
| Nominatim | Primary geocoding. | no |
| Photon | Fallback geocoding. | no |
| Open-Meteo forecast API | Weather for dates within the forecast horizon. | no |
| Open-Meteo archive API | Historical seasonal estimate for dates beyond the forecast horizon. | no |
| SerpApi Google Events | Event candidates. | yes, `SERPAPI_API_KEY` |

### 10.2 Weather Rules

Open-Meteo forecast covers an inclusive forecast window from today through
`today + WEATHER_FORECAST_MAX_DAYS`. The default is 15 days. Dates outside that
window are mapped to the same calendar date in the previous year and fetched
from the historical archive API. A single trip can have both forecast and
historical weather entries.

Weather is bucketed into application time blocks:

| Time block | Local hours |
| --- | --- |
| `MORNING` | 06:00-10:59 |
| `NOON` | 11:00-13:59 |
| `AFTERNOON` | 14:00-17:59 |
| `EVENING` | 18:00-21:59 |
| `NIGHT` | 22:00-05:59 |

The prompt instructs the model to prefer indoor or sheltered activities during
rain, drizzle, snow, thunderstorms, or high precipitation.

### 10.3 Caching

The service uses in-memory TTL caches for:

| Cache | Key idea | Default TTL |
| --- | --- | --- |
| Geocode | destination string | 21600 seconds |
| Events | location, country code, date filter | 21600 seconds |
| Weather | coordinates and date range | 21600 seconds |

The cache is per process. It is lost when the container restarts and is not
shared across replicas.

## 11. Frontend Behavior

### 11.1 Framework and Routing

The frontend uses React 19, Vite, Refine, React Router, React Hook Form, Zod,
and UI components under `frontend/src/components`.

Primary routes:

| Route | Component | Purpose |
| --- | --- | --- |
| `/login` | `frontend/src/pages/login/index.tsx` | Login, registration, and demo access. |
| `/trips` | `frontend/src/pages/trips/list.tsx` | Dashboard of saved trip summaries. |
| `/trips/create` | `frontend/src/pages/trips/create.tsx` | Trip generation form. |
| `/trips/:id` | `frontend/src/pages/trips/show.tsx` | Full itinerary with activity cards. |

The app resource definition is in `frontend/src/App.tsx`.

### 11.2 API Client

The Refine data provider is in `frontend/src/providers/data-provider.ts`.

| Data provider method | Backend endpoint |
| --- | --- |
| `getList("trips")` | `GET /trips` |
| `getOne("trips", id)` | `GET /trips/{tripId}` |
| `create("trips")` | `POST /trips` |
| `deleteOne("trips")` | `DELETE /trips/{tripId}` |
| `update("activities")` | `PATCH /trips/{tripId}/days/{dayId}/activities/{activityId}` |
| `deleteOne("activities")` | `DELETE /trips/{tripId}/days/{dayId}/activities/{activityId}` |

The API base URL is `VITE_API_URL` when set, otherwise `/api`. In Docker
Compose, the gateway handles `/api`.

OpenAPI TypeScript types are generated with:

```bash
cd frontend
npm run generate-api-types
```

The generated file `frontend/src/lib/api-types.ts` should not be edited by hand.

### 11.3 Authentication Storage

The auth provider stores:

| Local storage key | Meaning |
| --- | --- |
| `access_token` | Backend JWT. |
| `traveler_id` | Authenticated traveler UUID. |
| `is_demo` | Whether the traveler is a demo account. |

Logout removes all three keys.

## 12. Backend Service Details

The backend is the public security and orchestration boundary.

### 12.1 Security

Implemented in `backend/src/main/kotlin/com/vacation/app/config/SecurityConfig.kt`.

| Rule | Detail |
| --- | --- |
| Session policy | Stateless. |
| CSRF | Disabled because the API uses bearer tokens. |
| JWT algorithm | HS256. |
| JWT secret | `JWT_SECRET`, default `dev-only-change-this-secret-to-at-least-32-bytes`. Must be at least 32 bytes. |
| JWT issuer | `JWT_ISSUER`, default `triptailor-app-api`. |
| JWT TTL | `JWT_TTL_DAYS`, default `30`. |
| Public paths | `/`, `/openapi.yaml`, `/health`, `/actuator/health`, `/actuator/prometheus`, `/auth/**`, `/debug/instance`. |
| Protected paths | Everything else. |

### 12.2 Backend Metrics

The backend records:

| Metric | Meaning |
| --- | --- |
| Spring `http_server_requests_seconds_*` | Request count and latency. |
| `triptailor.trips.generated{outcome}` | Success/error counter for trip generation. |
| `triptailor.activity.regenerations{outcome}` | Success/error counter for activity regeneration. |

Tracing is enabled through Spring Boot OpenTelemetry when
`OTEL_TRACES_SAMPLER_ARG` is greater than zero and `TRACING_OTLP_ENDPOINT` points
to Tempo.

## 13. Persistence Service Details

The persistence service is intentionally simple. It exposes an internal REST API
and uses `NamedParameterJdbcTemplate` for SQL. It is the only application
service that should talk to PostgreSQL.

Important configuration:

| Variable | Default |
| --- | --- |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5433/triptailor` |
| `SPRING_DATASOURCE_USERNAME` | `tripuser` |
| `SPRING_DATASOURCE_PASSWORD` | `trippassword` |
| `server.port` | `8081` |

SQL schema initialization runs on startup with `spring.sql.init.mode=always`.

## 14. Observability

### 14.1 Metrics Endpoints

| Service | Metrics endpoint |
| --- | --- |
| Backend | `/actuator/prometheus` |
| Persistence service | `/actuator/prometheus` |
| GenAI service | `/metrics` |
| Travel context service | `/metrics` |

Prometheus scrape config and alert rules live in:

```text
infrastructure/kubernetes/triptailor/files/monitoring/prometheus/
```

The repo-root `monitoring` symlink points there so Docker Compose and Helm use
the same files.

### 14.2 Custom GenAI Metrics

Defined in `genai-service/app/observability/metrics.py`:

| Metric | Meaning |
| --- | --- |
| `genai_generations_total{kind,outcome}` | Schedule and alternative generation successes/errors. |
| `genai_llm_request_duration_seconds` | LLM call latency. |
| `genai_llm_requested_tokens{provider,model}` | Requested token budget observations. |
| `genai_llm_requested_completion_tokens_total{provider,model}` | Cumulative requested completion token budget. |
| `genai_llm_usage_tokens_total{provider,model,token_type}` | Provider-reported prompt, completion, and total token usage. |

### 14.3 Custom Travel Context Metrics

Defined in `travel-context-service/app/metrics.py`:

| Metric | Meaning |
| --- | --- |
| `travel_context_provider_requests_total{provider,outcome}` | External provider call outcomes. |
| `travel_context_provider_duration_seconds{provider}` | External provider latency. |
| `travel_context_cache_requests_total{cache,result}` | Cache hit and miss count. |
| `travel_context_events_returned` | Event candidates returned per context response. |
| `travel_context_weather_days_returned` | Weather days returned per context response. |

### 14.4 Dashboards and Traces

Grafana is provisioned with:

| Resource | Path |
| --- | --- |
| Dashboard | `infrastructure/observability/grafana/dashboards/triptailor-services.json` |
| Prometheus datasource | `infrastructure/observability/grafana/provisioning/datasources/prometheus.yaml` |
| Tempo datasource | `infrastructure/observability/grafana/provisioning/datasources/tempo.yaml` |

Local access:

| Tool | URL |
| --- | --- |
| Grafana through gateway | `http://localhost:3000/grafana/` |
| Grafana direct | `http://localhost:3001` |
| Prometheus through gateway | `http://localhost:3000/prometheus/` |
| Prometheus direct | `http://localhost:9090` |

Grafana anonymous admin login is enabled in Docker Compose for local/demo use.

### 14.5 Alert Rules

Alert rules are in:

```text
infrastructure/kubernetes/triptailor/files/monitoring/prometheus/alert.rules.yml
```

Configured alerts:

| Alert | Condition |
| --- | --- |
| `ServiceDown` | A scrape target is down. |
| `RequestFailing` | Any 5xx response in the recent window. |
| `HighRequestLatency` | Spring p95 request latency greater than 1 second. |

Validate Prometheus config:

```bash
docker run --rm --entrypoint promtool \
  -v "$PWD/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.11.0 \
  check config /etc/prometheus/prometheus.yml
```

## 15. Validation and Tests

### 15.1 Frontend

```bash
cd frontend
npm ci
npm run lint
npm run test
npm run test:coverage
npm run build
```

What this covers:

| Command | Coverage |
| --- | --- |
| `npm run lint` | ESLint, TypeScript/React hooks style. |
| `npm run test` | Vitest unit/component tests. |
| `npm run test:coverage` | Frontend coverage output. |
| `npm run build` | Generates API types, TypeScript compilation, Vite/Refine production build. |

### 15.2 Backend API

```bash
cd backend
./gradlew build
```

The Gradle build includes:

| Check | Detail |
| --- | --- |
| Kotlin compile | Java 21 toolchain. |
| Tests | JUnit 5. |
| Detekt | Static analysis with existing baseline. |
| JaCoCo | Coverage report and 80 percent line coverage gate. |
| OpenAPI copy | Copies `api-specification/frontend.yaml` into backend resources as `openapi.yaml`. |

Run tests only:

```bash
cd backend
./gradlew test
```

### 15.3 Persistence Service

```bash
cd persistence-service
./gradlew build
```

This includes compile, tests, Detekt, JaCoCo, and the 80 percent coverage gate.
It copies `api-specification/persistance.yaml` into resources as `openapi.yaml`.

### 15.4 GenAI Service

```bash
cd genai-service
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
flake8 app tests --count --show-source --statistics
mypy app
pytest --verbose --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
```

### 15.5 Travel Context Service

```bash
cd travel-context-service
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
flake8 app tests --count --show-source --statistics
mypy app
pytest --verbose --cov=app --cov-report=term-missing --cov-report=xml --cov-report=html --cov-fail-under=80
```

### 15.6 Full Stack Validation

```bash
docker compose config --quiet
docker compose build
docker compose up --detach --wait --wait-timeout 240
bash scripts/docker-compose-smoke.sh
```

## 16. CI/CD

### 16.1 Pull Request and Main CI

Workflow: `.github/workflows/ci.yaml`

Runs on:

| Event | Branch |
| --- | --- |
| push | `main` |
| pull request | `main` |

Jobs:

| Job | Main checks |
| --- | --- |
| `build-frontend` | Node 20, `npm ci`, lint, tests, coverage, build. |
| `build-backend` | Java 21, `./gradlew build`, coverage artifact. |
| `build-persistence-service` | Java 21, `./gradlew build`, coverage artifact. |
| `build-genai` | Python 3.11, flake8, mypy, pytest coverage with 80 percent gate. |
| `build-travel-context` | Python 3.11, flake8, mypy, pytest coverage with 80 percent gate. |
| `coverage-report` | Downloads all coverage artifacts and verifies 80 percent line coverage per service. |
| `verify-docker-compose` | Validates Compose config, builds images, starts stack, runs smoke test. |

Coverage summary generation is implemented in `scripts/coverage-report.mjs`.

### 16.2 Image Publishing and AET Kubernetes Deployment

Workflow: `.github/workflows/images.yaml`

It builds and publishes five images to GitHub Container Registry:

| Image |
| --- |
| `ghcr.io/aet-devops26/team-continuous-vacation/backend:<sha>` |
| `ghcr.io/aet-devops26/team-continuous-vacation/persistence-service:<sha>` |
| `ghcr.io/aet-devops26/team-continuous-vacation/genai-service:<sha>` |
| `ghcr.io/aet-devops26/team-continuous-vacation/travel-context-service:<sha>` |
| `ghcr.io/aet-devops26/team-continuous-vacation/frontend:<sha>` |

Deployment uses the Helm chart in `infrastructure/kubernetes/triptailor/` and
the namespace `team-continuous-vacation`.

Required secrets:

| Secret | Purpose |
| --- | --- |
| `AET_KUBECONFIG` | Kubernetes access. |
| `AZURE_LLM_API_KEY` | GenAI Azure provider. |
| `SERPAPI_API_KEY` | Event lookup in travel context. |

Optional secrets:

| Secret | Purpose |
| --- | --- |
| `POSTGRES_PASSWORD` | Overrides default database password. |
| `JWT_SECRET` | Overrides default JWT signing secret. |
| `GHCR_USERNAME` and `GHCR_PAT` | Pull private GHCR images. |

### 16.3 Azure VM Deployment

Workflow: `.github/workflows/azure-vm-deploy.yaml`

It:

1. Authenticates to Azure with OIDC.
2. Runs Terraform format, init, validate, plan, and apply/destroy.
3. Captures VM public IP.
4. Installs Ansible.
5. SSHes into the VM.
6. Runs the Ansible playbook to deploy Docker Compose.

The Azure VM path is documented in `infrastructure/README.md`.

## 17. Kubernetes Runbook

### 17.1 Local Kubernetes With Docker Desktop

From the repository root:

```bash
./start.sh
```

What `start.sh` does:

1. Checks `docker` and `kubectl`.
2. Finds Helm or downloads Helm `v3.15.4` to `/tmp`.
3. Verifies a current Kubernetes context exists.
4. Builds local images if missing:
   - `triptailor/backend:latest`
   - `triptailor/persistence-service:latest`
   - `triptailor/genai-service:latest`
   - `triptailor/travel-context-service:latest`
   - `triptailor/frontend:latest`
5. Installs or upgrades Helm release `triptailor` in namespace `triptailor-local`.
6. Applies `values-local.yaml`.
7. Waits for deployments to roll out.
8. Prints `http://localhost:30080`.

Useful overrides:

| Variable | Meaning |
| --- | --- |
| `NAMESPACE` | Kubernetes namespace, default `triptailor-local`. |
| `RELEASE` | Helm release, default `triptailor`. |
| `FORCE_BUILD_IMAGES=1` | Rebuild images even if local tags already exist. |
| `BACKEND_REPLICAS` | Override backend replica count. |
| `BACKEND_AUTOSCALING_ENABLED` | Enable/disable backend HPA. |
| `BACKEND_AUTOSCALING_MIN_REPLICAS` | HPA minimum replicas. |
| `BACKEND_AUTOSCALING_MAX_REPLICAS` | HPA maximum replicas. |
| `BACKEND_AUTOSCALING_TARGET_CPU` | HPA CPU target. |
| `BACKEND_CPU_REQUEST` | Backend CPU request. |

### 17.2 Manual Helm Commands

Build images:

```bash
docker build -t triptailor/backend:latest --build-context api-spec=api-specification backend
docker build -t triptailor/persistence-service:latest --build-context api-spec=api-specification persistence-service
docker build -t triptailor/genai-service:latest genai-service
docker build -t triptailor/travel-context-service:latest travel-context-service
docker build -t triptailor/frontend:latest --build-context api-spec=api-specification frontend
```

Install chart:

```bash
helm upgrade --install triptailor ./infrastructure/kubernetes/triptailor \
  --namespace triptailor-local \
  --create-namespace \
  -f infrastructure/kubernetes/triptailor/values-local.yaml
```

Check rollout:

```bash
kubectl -n triptailor-local rollout status deploy/db
kubectl -n triptailor-local rollout status deploy/persistence-service
kubectl -n triptailor-local rollout status deploy/travel-context-service
kubectl -n triptailor-local rollout status deploy/genai-service
kubectl -n triptailor-local rollout status deploy/backend
kubectl -n triptailor-local rollout status deploy/frontend
```

Open:

```text
http://localhost:30080
```

Uninstall:

```bash
helm uninstall triptailor -n triptailor-local
kubectl delete namespace triptailor-local
```

### 17.3 Kubernetes Services

The Helm chart uses service names that match Docker Compose:

| Service | Port |
| --- | --- |
| `db` | `5432` |
| `persistence-service` | `8081` |
| `travel-context-service` | `8090` |
| `genai-service` | `8000` |
| `backend` | `8080` |
| `frontend` | `3000` |
| `prometheus` | `9090` |
| `grafana` | `3000` |
| `tempo` | `3200`, `4317`, `4318` |

#### 17.3.1 Network policies

The Helm chart enables `networkPolicy.enabled` by default. A release-scoped
default-deny policy is combined with explicit policies for every workload:
gateway ingress to public services, backend-to-persistence and backend-to-GenAI,
GenAI-to-travel-context, persistence-to-Postgres, Prometheus scraping, Tempo
tracing, Grafana data sources, DNS, and external HTTPS provider calls.

The defaults expect an ingress-nginx controller in the `ingress-nginx` namespace.
Override `networkPolicy.ingressController.namespaceLabels` and `podLabels` when
the cluster uses different controller labels. Check the installed labels before
enabling ingress:

```bash
kubectl get pods --all-namespaces --show-labels | grep -i ingress
helm template triptailor infrastructure/kubernetes/triptailor -f my-values.yaml
```

NetworkPolicies require a CNI plugin that enforces them. They introduce no new
application secrets. Set `networkPolicy.enabled=false` only for troubleshooting
on clusters without NetworkPolicy support.

### 17.4 Local Kubernetes Monitoring Access

If services are not exposed publicly, use port-forward:

```bash
kubectl -n triptailor-local port-forward svc/prometheus 9090:9090
kubectl -n triptailor-local port-forward svc/grafana 3001:3000
```

Then open:

```text
http://localhost:9090
http://localhost:3001
```

### 17.5 Load Balancing Demo

```bash
./scripts/demo-load-balancing.sh
```

The script deploys the chart with three backend replicas and repeatedly calls:

```text
http://localhost:30080/api/debug/instance
```

The response includes the backend hostname. Multiple hostnames prove that the
Kubernetes `backend` service is distributing requests across ready pods.

### 17.6 Autoscaling Demo

```bash
./scripts/demo-autoscaling.sh
```

By default, the script demonstrates HPA-controlled scaling by raising the HPA
minimum replica count to 2. To use real CPU metrics, the cluster needs
metrics-server:

```bash
MOCK_CPU=0 ./scripts/demo-autoscaling.sh
```

### 17.7 AET Cluster Hosted URLs

For tutor evaluation, prefer the AET Kubernetes deployment because it has a
stable HTTPS hostname. The Azure VM deployment can receive a new public IP after
some redeployments, while the AET cluster URL stays stable.

| Service or UI | Hosted URL | Notes |
| --- | --- | --- |
| Main application | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/` | Stable public entrypoint for the deployed TripTailor app. |
| Backend API through ingress | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/` | Public API prefix used by the frontend. |
| Backend health | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/health` | Quick backend reachability check. |
| Backend OpenAPI | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/openapi.yaml` | Public backend API contract. |
| Demo login endpoint | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/auth/demo` | Creates a demo traveler session. |
| Trips endpoint | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/api/trips` | Requires a bearer token from login/demo login. |
| Prometheus | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus` | Prometheus UI and metrics target inspection. |
| Prometheus targets | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus/targets` | Shows scrape status for runtime services. |
| Prometheus alerts | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/prometheus/alerts` | Shows alert rule state. |
| Grafana | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/grafana/` | Dashboards and trace exploration. |
| Grafana health | `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/grafana/api/health` | Verifies Grafana through the ingress. |

After a demo login in the application, the UI also exposes monitoring links for
Prometheus and Grafana.

## 18. Azure VM Runbook

The Azure VM deployment path uses Terraform for infrastructure and Ansible for
application deployment. For tutor evaluation, the AET cluster URL in section
17.7 is usually the better hosted target because it is stable:
`https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/`. The Azure VM is
still documented here because it is part of the deployment setup, but its public
IP can change across redeployments.

### 18.1 Find the Azure Deployment and Services

TripTailor does not deploy each runtime component as a separate Azure App
Service. Terraform creates Azure infrastructure for one Linux VM, and Ansible
deploys the application onto that VM with Docker Compose. In Azure, look for the
VM and networking resources first; on the VM, use Docker Compose to find the
individual application services.

Azure resources created by Terraform:

| Azure resource | Terraform name | Purpose |
| --- | --- | --- |
| Resource group | `triptailor-rg` by default | Container for all VM resources. |
| Linux virtual machine | `triptailor-vm` | Runs Docker and the TripTailor Compose stack. |
| Public IP | `triptailor-pip` | Static public IP used to reach the VM. |
| Network security group | `triptailor-nsg` | Opens SSH and the public gateway port. |
| Network interface | `triptailor-nic` | Connects the VM to the virtual network. |
| Virtual network | `triptailor-vnet` | Private Azure network. |
| Subnet | `triptailor-subnet` | VM subnet inside the virtual network. |
| Managed OS disk | attached to `triptailor-vm` | Ubuntu 24.04 system disk. |

#### Option A: Find It in the Azure Portal

1. Open the Azure Portal.
2. Select the correct subscription.
3. Open **Resource groups**.
4. Search for `triptailor-rg` or the value configured as
   `AZURE_RESOURCE_GROUP`.
5. Open the resource group and inspect:
   - `triptailor-vm` for VM status and public IP.
   - `triptailor-pip` for the static public IP address.
   - `triptailor-nsg` for inbound rules.
   - `triptailor-nic` for private IP and network association.

#### Option B: Find It With Azure CLI

Login and select the subscription:

```bash
az login
az account list --output table
az account set --subscription "<subscription-id>"
```

Find likely TripTailor resource groups:

```bash
az group list \
  --query "[?contains(name, 'triptailor')].{name:name, location:location}" \
  --output table
```

List all resources in the default resource group:

```bash
az resource list \
  --resource-group triptailor-rg \
  --output table
```

Find the VM and its public IP:

```bash
az vm list \
  --resource-group triptailor-rg \
  --show-details \
  --output table

az network public-ip list \
  --resource-group triptailor-rg \
  --query "[].{name:name, ip:ipAddress, allocation:publicIPAllocationMethod}" \
  --output table
```

Check which ports Azure allows from the internet:

```bash
az network nsg rule list \
  --resource-group triptailor-rg \
  --nsg-name triptailor-nsg \
  --query "[].{name:name, access:access, protocol:protocol, port:destinationPortRange, priority:priority}" \
  --output table
```

The Terraform default NSG opens:

| Port | Purpose |
| --- | --- |
| `22` | SSH into the VM. |
| `80` | Reserved HTTP ingress rule. |
| `443` | Reserved HTTPS ingress rule. |
| `3000` | TripTailor gateway. This is the main public application port. |

#### Option C: Read Terraform Outputs

If Terraform state is available locally:

```bash
cd infrastructure/terraform
terraform output
terraform output -raw vm_public_ip
terraform output -raw ssh_command
```

Expected outputs:

| Output | Meaning |
| --- | --- |
| `vm_public_ip` | Public IP of `triptailor-vm`. |
| `vm_admin_username` | SSH username, default `tripadmin`. |
| `ssh_command` | Convenience command for connecting to the VM. |

#### Find the Application Services on the VM

SSH into the VM:

```bash
ssh tripadmin@<VM_PUBLIC_IP>
```

The Ansible playbook deploys the repository to:

```text
/opt/triptailor
```

List the running application services:

```bash
cd /opt/triptailor
docker compose ps
```

Expected Compose services:

| Compose service | Container name | Role |
| --- | --- | --- |
| `gateway` | `triptailor-gateway` | Public NGINX gateway on VM port `3000`. |
| `frontend` | `triptailor-frontend` | Internal React static frontend server. |
| `backend` | `triptailor-backend` | Internal public API service behind gateway `/api/*`. |
| `persistence-service` | `triptailor-persistence` | Internal database API. |
| `genai-service` | `triptailor-genai` | Internal LLM schedule service. |
| `travel-context-service` | `triptailor-travel-context` | Travel context API; host port `8090` in Compose, but not opened by the default Azure NSG. |
| `db` | `triptailor-db` | PostgreSQL. |
| `prometheus` | `triptailor-prometheus` | Metrics and alerts. |
| `grafana` | `triptailor-grafana` | Dashboards and trace exploration. |
| `tempo` | `triptailor-tempo` | Distributed trace backend. |

Check logs for one service:

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 genai-service
docker compose logs --tail=100 travel-context-service
```

Run the same smoke test used locally from inside the VM:

```bash
cd /opt/triptailor
bash scripts/docker-compose-smoke.sh
```

#### Azure Hosted Service URLs

With the default Azure deployment, the public host is the static public IP of
`triptailor-pip`. In the tables below, replace `<AZURE_VM_PUBLIC_IP>` with that
IP address.

Find the deployed Azure IP with the CLI:

```bash
az login
az account set --subscription "<subscription-id>"

AZURE_VM_PUBLIC_IP="$(
  az network public-ip show \
    --resource-group triptailor-rg \
    --name triptailor-pip \
    --query ipAddress \
    --output tsv
)"

echo "${AZURE_VM_PUBLIC_IP}"
```

The same IP is visible in the Azure Portal under:

```text
Resource groups -> triptailor-rg -> triptailor-pip -> IP address
```

Public URLs exposed through the Azure VM gateway:

| Service or UI | Azure URL | What to use it for |
| --- | --- | --- |
| Application gateway | `http://<AZURE_VM_PUBLIC_IP>:3000` | Main public entrypoint. NGINX serves the frontend and routes API/monitoring subpaths. |
| Frontend | `http://<AZURE_VM_PUBLIC_IP>:3000/` | React TripTailor application: demo login, trip list, trip creation, trip detail, activity edits. |
| Backend API through gateway | `http://<AZURE_VM_PUBLIC_IP>:3000/api/` | Public API prefix used by the frontend. |
| Backend health | `http://<AZURE_VM_PUBLIC_IP>:3000/api/health` | Fast check that the backend is reachable through the gateway. |
| Backend OpenAPI | `http://<AZURE_VM_PUBLIC_IP>:3000/api/openapi.yaml` | Public API contract served by the backend. |
| Auth API | `http://<AZURE_VM_PUBLIC_IP>:3000/api/auth/demo`, `/api/auth/login`, `/api/auth/register` | Demo session, login, and registration endpoints. |
| Trips API | `http://<AZURE_VM_PUBLIC_IP>:3000/api/trips` | Authenticated trip list and trip generation endpoint. |
| Grafana | `http://<AZURE_VM_PUBLIC_IP>:3000/grafana/` | Dashboard UI for metrics and traces. |
| Grafana health | `http://<AZURE_VM_PUBLIC_IP>:3000/grafana/api/health` | Verifies Grafana through the gateway. |
| Prometheus | `http://<AZURE_VM_PUBLIC_IP>:3000/prometheus/` | Prometheus UI through the gateway. |
| Prometheus targets | `http://<AZURE_VM_PUBLIC_IP>:3000/prometheus/targets` | Shows scrape status for backend, persistence, GenAI, and travel-context services. |
| Prometheus alerts | `http://<AZURE_VM_PUBLIC_IP>:3000/prometheus/alerts` | Shows alert rule state. |

Example:

```bash
curl -i "http://${AZURE_VM_PUBLIC_IP}:3000/api/health"
open "http://${AZURE_VM_PUBLIC_IP}:3000/grafana/"
open "http://${AZURE_VM_PUBLIC_IP}:3000/prometheus/targets"
```

Services that exist on Azure but are intentionally not public as standalone
URLs:

| Service | Public Azure URL | How to reach it |
| --- | --- | --- |
| Backend container | No direct public `:8080` URL in the default deployment. | Use gateway URLs under `http://<AZURE_VM_PUBLIC_IP>:3000/api/*`, or SSH into the VM and call `http://backend:8080` from the Compose network. |
| Persistence service | No public URL. | SSH into the VM and call it from the Compose network, for example `docker compose exec gateway wget -qO- http://persistence-service:8081/health`. |
| GenAI service | No public URL. | SSH into the VM and call it from the Compose network, for example `docker compose exec gateway wget -qO- http://genai-service:8000/health`. |
| Travel context service | Not public through the default NSG. | SSH into the VM and use `curl http://localhost:8090/health`, or call `http://travel-context-service:8090/health` from the Compose network. |
| Tempo | No public UI. | SSH into the VM and check `curl http://localhost:3200/ready`; traces are viewed in Grafana. |
| PostgreSQL | No public database URL. | SSH into the VM and use Docker/psql locally; the container uses `db:5432` inside the Compose network. |

Useful checks after SSH:

```bash
ssh tripadmin@<AZURE_VM_PUBLIC_IP>
cd /opt/triptailor

docker compose ps
docker compose exec gateway wget -qO- http://backend:8080/health
docker compose exec gateway wget -qO- http://persistence-service:8081/health
docker compose exec gateway wget -qO- http://genai-service:8000/health
curl -fsS http://localhost:8090/health
curl -fsS http://localhost:3200/ready
```

The Docker Compose file also publishes some direct host ports on the VM, such as
`3001` for Grafana, `9090` for Prometheus, `8090` for travel context, and `5433`
for PostgreSQL. Those ports are not reachable from the public internet unless
the Azure NSG is changed. For normal evaluation, use the gateway URLs on port
`3000` or SSH into the VM and access direct ports locally from there.

### 18.2 Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Set:

| Variable | Meaning |
| --- | --- |
| `subscription_id` | Azure subscription ID. |
| `ssh_public_key_path` | Path to public SSH key. |
| `resource_group_name` | Resource group name. |
| `location` | Azure region. |
| `vm_size` | VM SKU. |
| `admin_username` | VM SSH username. |

Run:

```bash
terraform init
terraform apply
```

The output `vm_public_ip` is used by Ansible.

Important note: `main.tf` uses a shared Azure remote state backend. For local
experiments in a different subscription, the backend block may need to be
temporarily commented out and `terraform init -reconfigure` run. Do not commit
that change.

### 18.3 Ansible

```bash
cd infrastructure/ansible
cp inventory.ini.example inventory.ini
cp vars.yml.example vars.yml
```

Set:

| File | Variable |
| --- | --- |
| `inventory.ini` | VM public IP and SSH details. |
| `vars.yml` | Azure LLM API key, Azure LLM base URL, optional SerpApi key, optional database/JWT secrets. |

Deploy:

```bash
ansible-playbook -i inventory.ini playbook.yml -e @vars.yml
```

The app is available through the gateway:

```text
http://<VM_IP>:3000
```

## 19. Troubleshooting

### 19.1 Service Health Commands

Docker Compose:

```bash
docker compose ps
docker compose logs backend
docker compose logs persistence-service
docker compose logs genai-service
docker compose logs travel-context-service
docker compose logs gateway
```

Kubernetes:

```bash
kubectl -n triptailor-local get pods,svc,ingress
kubectl -n triptailor-local describe pod <pod-name>
kubectl -n triptailor-local logs deploy/backend
kubectl -n triptailor-local logs deploy/genai-service
```

### 19.2 Frontend Does Not Load

Check:

1. Gateway is running: `docker compose ps gateway`.
2. Frontend is running: `docker compose ps frontend`.
3. Gateway config routes `/` to `frontend:3000`.
4. Browser URL is `http://localhost:3000`, not the internal frontend container.
5. Frontend build succeeded during `docker compose build frontend`.

Useful command:

```bash
curl -i http://localhost:3000/
```

### 19.3 API Returns 401

Likely causes:

| Cause | Fix |
| --- | --- |
| Missing bearer token | Create demo/login session again. |
| Frontend local storage has stale token | Logout or clear `access_token`, `traveler_id`, and `is_demo`. |
| JWT secret changed after token issuance | Create a new session. |
| Calling backend directly without `/api` and without token | Use gateway and include `Authorization: Bearer <token>`. |

Check public backend health:

```bash
curl -i http://localhost:3000/api/health
```

### 19.4 Trip Generation Returns 500 or 502

Likely causes:

| Symptom | Cause | Fix |
| --- | --- | --- |
| GenAI service unhealthy | Missing required environment variable or provider startup failure. | Check `docker compose logs genai-service`. |
| `AZURE_LLM_API_KEY is required` | `LLM_PROVIDER=azure` without real key. | Set key in `genai-service/.env` or switch to `LLM_PROVIDER=local`. |
| LLM HTTP error | Bad base URL, deployment name, API version, or key. | Check GenAI logs for provider status code and response. |
| `Generated schedule did not match the expected format` | LLM returned invalid JSON or violated schedule contract. | Retry, lower temperature, inspect raw response in debug logs. |
| Travel context lookup failed | Geocoder/weather/event provider timeout. | GenAI should continue without context; if not, inspect travel-context logs. |

### 19.5 Event Lookup Returns No Events

This is expected when `SERPAPI_API_KEY` is empty. The code logs:

```text
SerpApi event lookup skipped because SERPAPI_API_KEY is not configured
```

Set `SERPAPI_API_KEY` in `travel-context-service/.env` or in Helm secrets for
events. Weather and geocoding do not require this key.

### 19.6 Weather Missing

Check:

| Check | Command or file |
| --- | --- |
| Weather enabled | `WEATHER_ENABLED=true` in travel context config. |
| Open-Meteo reachable | `docker compose logs travel-context-service`. |
| Travel context health | `curl http://localhost:8090/health`. |
| Direct context request | `POST http://localhost:8090/trip-context`. |

Weather failures are intentionally best effort in the travel context service.
If Open-Meteo fails, the service logs a warning and returns an empty weather
list instead of failing the full context response.

### 19.7 Database Problems

Connect from host:

```bash
psql postgresql://tripuser:trippassword@localhost:5433/triptailor
```

Useful SQL:

```sql
select id, email, is_demo, created_at from travelers order by created_at desc;
select id, traveler_id, destination, start_date, end_date, vibe from trips order by start_date desc;
select count(*) from days;
select count(*) from activities;
select count(*) from activity_tags;
```

Reset local database:

```bash
docker compose down --volumes
docker compose up --build
```

### 19.8 Prometheus Target Down

Open:

```text
http://localhost:9090/targets
```

Check:

| Target | Expected endpoint |
| --- | --- |
| `backend` | `backend:8080/actuator/prometheus` |
| `persistence-service` | `persistence-service:8081/actuator/prometheus` |
| `genai-service` | `genai-service:8000/metrics` |
| `travel-context-service` | `travel-context-service:8090/metrics` |

If backend metrics return 401, confirm `/actuator/prometheus` is still permitted
in `SecurityConfig.kt`.

### 19.9 Grafana Subpath Problems

Grafana is configured to serve from `/grafana/` in Docker Compose:

| Variable | Value |
| --- | --- |
| `GF_SERVER_ROOT_URL` | `%(protocol)s://%(domain)s:3000/grafana/` |
| `GF_SERVER_SERVE_FROM_SUB_PATH` | `true` |

Use the trailing slash:

```text
http://localhost:3000/grafana/
```

### 19.10 Kubernetes Pod CrashLoopBackOff

Common causes:

| Pod | Likely cause |
| --- | --- |
| `genai-service` | Missing/invalid LLM configuration. |
| `persistence-service` | Cannot connect to Postgres or database secret mismatch. |
| `backend` | Persistence or GenAI unavailable, invalid JWT secret too short. |
| `frontend` | Image build issue or nginx config issue. |
| `prometheus` | Invalid Prometheus config or rules. |

Commands:

```bash
kubectl -n triptailor-local describe pod <pod>
kubectl -n triptailor-local logs <pod> --previous
kubectl -n triptailor-local get events --sort-by=.lastTimestamp
```

## 20. Common Evaluation Script

A concise demo path for a tutor:

1. Start the stack:

   ```bash
   docker compose up --detach --build
   ```

2. Run smoke test:

   ```bash
   bash scripts/docker-compose-smoke.sh
   ```

3. Open the app:

   ```text
   http://localhost:3000
   ```

4. Create a demo session.
5. Create a new trip with a short future date range, for example 2 or 3 days.
6. Open the generated itinerary.
7. Regenerate one activity with an instruction such as:

   ```text
   Make this indoor and suitable for rainy weather
   ```

8. Delete one activity.
9. Open Grafana:

   ```text
   http://localhost:3000/grafana/
   ```

10. Open Prometheus targets:

   ```text
   http://localhost:9090/targets
   ```

11. Stop the stack:

   ```bash
   docker compose down
   ```

## 21. What to Inspect in the Code

Recommended code-reading order:

| Topic | Files |
| --- | --- |
| Product and architecture overview | `README.md`, `diagrams/*.puml` |
| Gateway routing | `infrastructure/gateway/nginx.conf` |
| Frontend routes | `frontend/src/App.tsx` |
| Frontend data provider | `frontend/src/providers/data-provider.ts` |
| Frontend auth | `frontend/src/providers/auth-provider.ts` |
| Trip creation UI | `frontend/src/pages/trips/create.tsx` |
| Trip detail and regeneration UI | `frontend/src/pages/trips/show.tsx` |
| Backend auth | `backend/src/main/kotlin/com/vacation/app/controller/AuthController.kt`, `backend/src/main/kotlin/com/vacation/app/service/AuthService.kt`, `backend/src/main/kotlin/com/vacation/app/service/TokenService.kt` |
| Backend security | `backend/src/main/kotlin/com/vacation/app/config/SecurityConfig.kt` |
| Backend trip orchestration | `backend/src/main/kotlin/com/vacation/app/controller/TripController.kt`, `backend/src/main/kotlin/com/vacation/app/service/TripService.kt` |
| Backend service clients | `backend/src/main/kotlin/com/vacation/app/client/HttpPersistenceClient.kt`, `backend/src/main/kotlin/com/vacation/app/client/HttpGenAiClient.kt` |
| Persistence controllers | `persistence-service/src/main/kotlin/com/vacation/persistence/controller/*.kt` |
| Persistence SQL/repository | `persistence-service/src/main/resources/schema.sql`, `persistence-service/src/main/kotlin/com/vacation/persistence/repository/TripTailorRepository.kt` |
| GenAI routes and service | `genai-service/app/api/routes/schedules.py`, `genai-service/app/services/schedule_service.py` |
| GenAI prompts | `genai-service/app/services/prompts/schedule_prompts.py` |
| LLM provider integration | `genai-service/app/services/llm/*.py` |
| Travel context service | `travel-context-service/app/services/context_service.py` |
| Weather provider | `travel-context-service/app/services/providers/open_meteo_provider.py` |
| Events provider | `travel-context-service/app/services/providers/serpapi_events_provider.py` |
| Compose stack | `docker-compose.yml` |
| Helm chart | `infrastructure/kubernetes/triptailor/` |
| CI | `.github/workflows/ci.yaml` |

## 22. Known Limitations and Design Tradeoffs

| Area | Current behavior | Tradeoff |
| --- | --- | --- |
| Demo users | Demo travelers are stored in the same database as registered users. | Easy demo flow, but no automatic cleanup job is currently visible in the implementation. |
| Trip date limit | GenAI and travel-context APIs enforce an inclusive maximum of 7 days. | Keeps generation cost and itinerary size bounded. |
| LLM reliability | Invalid model output becomes a 502. | Preserves data integrity, but users may need to retry. |
| Activity replacement | Persistence deletes old activity and inserts replacement with a new ID. | Simple model, but references to old activity IDs become invalid. |
| Travel context cache | In-memory per process. | Simple and fast, but not shared across replicas and lost on restart. |
| Event lookup | Requires SerpApi key. | App still works without events, but generated plans lose real event enrichment. |
| Auth | HS256 shared secret JWT. | Simple for project deployment; production would use stronger secret management and rotation. |
| Gateway | NGINX routes public frontend/API/monitoring. | Internal services remain private in Kubernetes; Compose exposes travel context and monitoring for debugging. |

## 23. File Generation Rules

Do not edit generated outputs by hand:

| Generated file | Source |
| --- | --- |
| `backend/src/main/resources/openapi.yaml` | Copied from `api-specification/frontend.yaml` during Gradle resource processing. |
| `persistence-service/src/main/resources/openapi.yaml` | Copied from `api-specification/persistance.yaml` during Gradle resource processing. |
| `frontend/src/lib/api-types.ts` | Generated from `api-specification/frontend.yaml` by `npm run generate-api-types`. |

When API contracts change, update the relevant OpenAPI file first, then
regenerate/build the affected services.

## 24. Cleanup Checklist

Before handing in or demonstrating:

1. No real secrets committed.
2. `docker compose config --quiet` passes.
3. `bash scripts/docker-compose-smoke.sh` passes after stack startup.
4. `npm run lint`, `npm run test`, and `npm run build` pass in `frontend/`.
5. `./gradlew build` passes in `backend/`.
6. `./gradlew build` passes in `persistence-service/`.
7. `flake8`, `mypy`, and `pytest --cov-fail-under=80` pass in both Python services.
8. Prometheus targets are up.
9. Grafana dashboard loads.
10. A short trip can be generated and one activity can be regenerated.
