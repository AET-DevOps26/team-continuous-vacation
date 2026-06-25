# Monitoring

Prometheus scrapes request count, latency, and error rate from every runtime
service, plus custom GenAI and Travel Context metrics, and evaluates alert
rules. Grafana is provisioned with a service dashboard backed by Prometheus and
links into Tempo for OTLP traces.

## Single source of truth

This directory is the **only** place monitoring config lives. Both deployment
targets read these exact files:

| Target | How it reads them |
| --- | --- |
| `docker-compose.yml` | Bind-mounts `./monitoring/prometheus` (a repo-root symlink → this directory) into the `prometheus` container. |
| Helm chart | `templates/monitoring-prometheus.yaml` loads the files into a ConfigMap via `.Files.Get`. |

This works because **Kubernetes Service names match docker-compose service
names** (`backend`, `persistence-service`, `genai-service`,
`travel-context-service`), so the scrape targets in `prometheus/prometheus.yml`
resolve identically in both environments — no per-environment config.

> The canonical files must physically live inside the chart (`files/monitoring/`)
> because Helm refuses to read files outside the chart root. The repo-root
> `monitoring` symlink only exists so `docker-compose.yml` can reach them with a
> clean relative path.

```
monitoring/
├── README.md
├── grafana/
│   ├── dashboards/
│   │   └── triptailor-services.json
│   └── provisioning/
│       ├── dashboards/
│       └── datasources/
└── prometheus/
    ├── prometheus.yml      # scrape jobs (10s interval) + rule_files
    └── alert.rules.yml     # alert rules
```

## Metrics exposed

| Service | Endpoint | Source |
| --- | --- | --- |
| `backend` | `/actuator/prometheus` | Spring Boot Actuator + Micrometer |
| `persistence-service` | `/actuator/prometheus` | Spring Boot Actuator + Micrometer |
| `genai-service` | `/metrics` | `prometheus-fastapi-instrumentator` + custom metrics |
| `travel-context-service` | `/metrics` | `prometheus-fastapi-instrumentator` |

Request count / latency / error rate come from the standard metrics:

- **Spring**: `http_server_requests_seconds_count` (count),
  `http_server_requests_seconds_bucket` (latency, histogram enabled via
  `management.metrics.distribution.percentiles-histogram.http.server.requests=true`),
  `outcome="SERVER_ERROR"` tag (errors).
- **FastAPI**: `http_requests_total{status}` (count + errors),
  `http_request_duration_seconds` (latency).

> The backend's Spring Security config (`backend/.../config/SecurityConfig.kt`)
> explicitly permits `/actuator/prometheus`; without it scrapes return `401`.

### Custom GenAI metrics

Defined in `genai-service/app/observability/metrics.py`, exported on the same
`/metrics` endpoint:

- `genai_generations_total{kind,outcome}` — generations by kind (`schedule` /
  `alternative`) and `outcome` (`success` / `error`).
- `genai_llm_request_duration_seconds` — latency histogram of a single LLM call.
- `genai_llm_requested_tokens{provider,model}` — requested completion-token
  budget per LLM provider call.
- `genai_llm_requested_completion_tokens_total{provider,model}` — cumulative
  requested completion-token budget.
- `genai_llm_usage_tokens_total{provider,model,token_type}` — provider-reported
  token usage when available (`prompt`, `completion`, `total`).

### Custom Travel Context metrics

Defined in `travel-context-service/app/metrics.py`, exported on `/metrics`:

- `travel_context_provider_requests_total{provider,outcome}` — external
  provider calls by provider and success/error.
- `travel_context_provider_duration_seconds{provider}` — provider call latency.
- `travel_context_cache_requests_total{cache,result}` — geocode/events/weather
  cache hit and miss counts.
- `travel_context_events_returned` — event candidates returned per context.
- `travel_context_weather_days_returned` — weather days returned per context.

### Grafana dashboard

The `TripTailor Services` dashboard is provisioned from
`grafana/dashboards/triptailor-services.json`. It covers availability, request
rate, error rate, latency, JVM health, GenAI generation outcomes, LLM latency,
Travel Context provider/cache behavior, and links to Tempo Explore for traces.

## Alert rules

Thresholds are intentionally aggressive (university project, no real customer):

| Alert | Condition | For |
| --- | --- | --- |
| `ServiceDown` | `up == 0` | 10s |
| `RequestFailing` | any 5xx in the last 1m (Spring + FastAPI variants) | 0s |
| `HighRequestLatency` | p95 request latency > 1s (Spring) | 30s |

## Run & verify

**docker-compose**

```bash
docker compose up -d --build
# Generate traffic (login, create a trip), then open Prometheus:
#   http://localhost:9090/targets   -> all 5 jobs UP
#   http://localhost:9090/alerts    -> rules listed
docker compose stop backend         # ServiceDown -> FIRING within ~10s
```

**Kubernetes**

```bash
helm upgrade --install triptailor infrastructure/kubernetes/triptailor
kubectl port-forward svc/prometheus 9090:9090
kubectl port-forward svc/grafana 3001:3000
# Disable with: --set monitoring.enabled=false
```

## Editing config

Edit the files in this directory only. docker-compose picks up changes on
`prometheus` container restart; the Helm ConfigMap checksum annotation rolls the
Prometheus pod automatically on `helm upgrade`. Validate before committing:

```bash
docker run --rm --entrypoint promtool \
  -v "$PWD/monitoring/prometheus:/etc/prometheus:ro" prom/prometheus:v3.11.0 \
  check config /etc/prometheus/prometheus.yml
```
