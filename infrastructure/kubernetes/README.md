# Kubernetes and Helm

This directory contains a simple Helm chart for deploying TripTailor to Kubernetes.

The chart mirrors the working `docker-compose.yml` topology:

- `db`: PostgreSQL 17 with a persistent volume
- `persistence-service`: Spring Boot service on port 8081
- `travel-context-service`: FastAPI enrichment service on port 8090
- `genai-service`: FastAPI service on port 8000
- `backend`: Spring Boot app API on port 8080
- `frontend`: nginx-served React app on port 3000

The service names intentionally match Docker Compose. Public traffic enters through one gateway-style edge:

```text
Browser
  -> Gateway / Ingress
      /      -> frontend
      /api/* -> backend
  -> backend
      -> persistence-service
      -> genai-service
  -> persistence-service
      -> db
```

`persistence-service`, `genai-service`, and `db` stay private inside the cluster. The LLM service is intentionally not exposed through the gateway because the backend owns authentication, validation, trip context, persistence, and error handling.

Kubernetes load balancing is provided by `Service` objects. For example, if `backend.replicaCount` is `3`, the `backend` Service keeps one stable address and distributes traffic across the ready backend pods. This is load balancing only, not autoscaling. Autoscaling would require a separate HorizontalPodAutoscaler and metrics support.

For local Kubernetes, `values-local.yaml` exposes the frontend via NodePort. The frontend nginx container proxies `/api` to the `backend` Service, so the same service-level load balancing is exercised locally.

## Local Test with Docker Desktop Kubernetes

From the repository root, the simplest local start command is:

```bash
./start.sh
```

The script builds any missing local images, installs or upgrades the Helm release, waits for all deployments, and exposes the frontend at `http://localhost:30080`. If Helm is not installed, the script downloads a temporary Helm binary into `/tmp`.

Build the local images:

```bash
docker build -t triptailor/backend:latest --build-context api-spec=api-specification backend
docker build -t triptailor/persistence-service:latest --build-context api-spec=api-specification persistence-service
docker build -t triptailor/genai-service:latest genai-service
docker build -t triptailor/travel-context-service:latest travel-context-service
docker build -t triptailor/frontend:latest --build-context api-spec=api-specification frontend
```

Install the chart:

```bash
helm upgrade --install triptailor ./infrastructure/kubernetes/triptailor \
  --namespace triptailor-local \
  --create-namespace \
  -f infrastructure/kubernetes/triptailor/values-local.yaml
```

Wait for the rollout:

```bash
kubectl -n triptailor-local rollout status deploy/db
kubectl -n triptailor-local rollout status deploy/persistence-service
kubectl -n triptailor-local rollout status deploy/travel-context-service
kubectl -n triptailor-local rollout status deploy/genai-service
kubectl -n triptailor-local rollout status deploy/backend
kubectl -n triptailor-local rollout status deploy/frontend
```

Open the frontend at `http://localhost:30080`.

## Demonstrate Backend Load Balancing

Run:

```bash
./scripts/demo-load-balancing.sh
```

The script deploys the local chart with three backend replicas, waits for rollout, lists the backend pods, and repeatedly calls:

```bash
http://localhost:30080/api/debug/instance
```

The response includes the backend pod/container hostname. Seeing more than one distinct hostname proves requests are being distributed through the `backend` Kubernetes Service.

## Demonstrate Backend Autoscaling

Run:

```bash
./scripts/demo-autoscaling.sh
```

The default demo enables the backend `HorizontalPodAutoscaler`, waits briefly,
and then simulates a CPU pressure signal by raising the HPA minimum replica count
to `2`. This avoids creating heavy CPU load on a laptop while still showing the
HPA-controlled backend deployment scaling out.

To run a real CPU-based HPA demo instead, the cluster needs metrics-server:

```bash
MOCK_CPU=0 ./scripts/demo-autoscaling.sh
```

Uninstall:

```bash
helm uninstall triptailor -n triptailor-local
kubectl delete namespace triptailor-local
```

## AET Cluster Deployment

GitHub Actions publishes images and deploys them to the AET namespace. The workflow is `.github/workflows/images.yaml`.

It publishes the five images to GitHub Container Registry as:

- `ghcr.io/aet-devops26/team-continuous-vacation/backend:<git-sha>`
- `ghcr.io/aet-devops26/team-continuous-vacation/persistence-service:<git-sha>`
- `ghcr.io/aet-devops26/team-continuous-vacation/genai-service:<git-sha>`
- `ghcr.io/aet-devops26/team-continuous-vacation/travel-context-service:<git-sha>`
- `ghcr.io/aet-devops26/team-continuous-vacation/frontend:<git-sha>`

Use the Git commit SHA as the Helm image tag. Avoid `latest` for reproducible cluster deployments. The workflow uses the short commit SHA for both publishing and deployment.

Required GitHub repository secrets:

- `AET_KUBECONFIG`: kubeconfig YAML for the AET cluster
- `AZURE_LLM_API_KEY`: Azure OpenAI API key for `genai-service`
- `SERPAPI_API_KEY`: SerpApi key for Google Events lookup in `travel-context-service`

The per-day weather enrichment in `travel-context-service` uses the free, keyless
Open-Meteo forecast and historical-archive APIs, so it needs no secret. It is
configured via the `travelContextService.config` values (`OPEN_METEO_*`,
`WEATHER_ENABLED`, `WEATHER_FORECAST_MAX_DAYS`).

Optional GitHub repository secrets:

- `POSTGRES_PASSWORD`: PostgreSQL password for the chart Secret. Defaults to `trippassword`.
- `JWT_SECRET`: backend JWT signing secret, at least 32 bytes. Defaults to `dev-only-change-this-secret-to-at-least-32-bytes`.

If GHCR packages are private, also add:

- `GHCR_USERNAME`: GitHub username that can read the packages
- `GHCR_PAT`: GitHub token with `read:packages`

If the packages are public, `GHCR_USERNAME` and `GHCR_PAT` are not needed.

The workflow deploys to the namespace `team-continuous-vacation` and enables an Ingress for `https://team-continuous-vacation.stud.k8s.aet.cit.tum.de/`.

On `main`, the workflow publishes images and deploys automatically. It can also be run manually with `workflow_dispatch`.

## Manual AET Deployment

Create an untracked values file from the example:

```bash
cp infrastructure/kubernetes/triptailor/values-aet.example.yaml infrastructure/kubernetes/triptailor/values-aet.yaml
```

Set:

- image repositories and tags that the AET cluster can pull
- `postgres.auth.password`
- `backend.secrets.JWT_SECRET`
- `genaiService.secrets.AZURE_LLM_API_KEY`
- `travelContextService.image.repository` and `travelContextService.image.tag`
- `travelContextService.secrets.SERPAPI_API_KEY`
- optional `global.imagePullSecrets`
- optional `ingress` settings if the cluster provides an ingress controller and hostname

Deploy:

```bash
helm upgrade --install triptailor ./infrastructure/kubernetes/triptailor \
  --namespace team-continuous-vacation \
  -f infrastructure/kubernetes/triptailor/values-aet.yaml
```

Check:

```bash
kubectl -n team-continuous-vacation get pods,svc,ingress
kubectl -n team-continuous-vacation rollout status deploy/travel-context-service
kubectl -n team-continuous-vacation rollout status deploy/backend
kubectl -n team-continuous-vacation rollout status deploy/frontend
```

Without ingress, use a temporary port-forward:

```bash
kubectl -n team-continuous-vacation port-forward svc/frontend 3000:3000
```
