# Observability: Tracing

TripTailor uses OpenTelemetry tracing for backend service flows.

A trace backend receives spans from instrumented services, stores them, and lets
you inspect one complete request by trace ID. Without a backend, services may
create trace IDs, but there is no durable place to view the full waterfall across
`backend`, `persistence-service`, `genai-service`, and `travel-context-service`.

Tempo is used for local tracing because it accepts OTLP traces and integrates
directly with Grafana. The root `docker-compose.yml` includes Tempo and Grafana
(with both Tempo and Prometheus datasources plus the provisioned `TripTailor
Services` dashboard); the Tempo runtime config now lives in the monitoring
single source of truth at
`infrastructure/kubernetes/triptailor/files/monitoring/tempo/tempo.yaml`
(reachable from the repo root via the `monitoring/` symlink).

## Local Demo

Run from the repository root:

```bash
./scripts/demo-tracing.sh
```

The script starts Docker Compose (the full stack now lives in the root
`docker-compose.yml`), sends a trip generation request through the gateway,
prints recent logs with trace IDs, and shows where to inspect traces.

Open Grafana directly at `http://localhost:3001`, or through the gateway at
`http://localhost:3000/grafana/`. Prometheus is exposed the same way at
`http://localhost:3000/prometheus/` (or `http://localhost:9090`).

Open Dashboards -> TripTailor -> `TripTailor Services` for metrics. Use Explore
with the `Tempo` datasource and search for recent traces involving:

- `backend`
- `persistence-service`
- `genai-service`
- `travel-context-service`

If no real LLM endpoint/API key is configured locally, trip generation can end
with a 5xx response. That is still useful for tracing verification because the
request reaches the traced backend, GenAI, and travel-context flow before the LLM
call fails.

## Kubernetes Integration

The app Helm chart deploys the full suite — Prometheus, Grafana, and Tempo — and
enables tracing by default:

```yaml
tracing:
  enabled: true
  otlpEndpoint: http://tempo:4318/v1/traces
  samplingProbability: "1.0"

monitoring:
  enabled: true
  tempo:
    enabled: true
    persistence:
      enabled: true
      size: 5Gi
```

Tempo runs as an in-cluster Deployment/Service named `tempo` (see
`templates/monitoring-tempo.yaml`), so the OTLP endpoint above resolves without
an external observability stack. Set `tracing.enabled: false` to opt out, or
`monitoring.tempo.enabled: false` / `monitoring.enabled: false` to drop Tempo or
the whole monitoring stack.
