# Observability: Tracing

TripTailor uses OpenTelemetry tracing for backend service flows.

A trace backend receives spans from instrumented services, stores them, and lets
you inspect one complete request by trace ID. Without a backend, services may
create trace IDs, but there is no durable place to view the full waterfall across
`backend`, `persistence-service`, `genai-service`, and `travel-context-service`.

Tempo is used for local tracing because it accepts OTLP traces and integrates
directly with Grafana. The compose override includes a minimal Grafana only for
local trace viewing; it does not replace the team's Grafana/Prometheus work.

## Local Demo

Run from the repository root:

```bash
./scripts/demo-tracing.sh
```

The script starts Docker Compose with `docker-compose.tracing.yml`, sends a trip
generation request through the gateway, prints recent logs with trace IDs, and
shows where to inspect traces.

Open Grafana:

```text
http://localhost:3001
```

Use Explore with the `Tempo` datasource and search for recent traces involving:

- `backend`
- `persistence-service`
- `genai-service`
- `travel-context-service`

If no real LLM endpoint/API key is configured locally, trip generation can end
with a 5xx response. That is still useful for tracing verification because the
request reaches the traced backend, GenAI, and travel-context flow before the LLM
call fails.

## Kubernetes Integration

The app Helm chart exposes tracing values but does not deploy Tempo or Grafana:

```yaml
tracing:
  enabled: true
  otlpEndpoint: http://tempo:4318/v1/traces
  samplingProbability: "1.0"
```

The observability stack should provide the OTLP endpoint. This keeps tracing
compatible with a future shared Grafana/Tempo deployment.
