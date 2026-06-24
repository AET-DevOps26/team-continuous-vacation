# Repository Guidelines

## Project Structure & Module Organization

- `backend/`: Kotlin Spring Boot service. Application code lives in `src/main/kotlin/com/vacation/app`, resources in `src/main/resources`, and tests in `src/test/kotlin`.
- `frontend/`: React 19 + Vite + Refine app. Pages are in `src/pages`, reusable UI in `src/components`, providers in `src/providers`, and helpers in `src/lib`.
- `api-specification/`: OpenAPI YAML files for frontend, persistence, and GenAI boundaries.
- `diagrams/`: PlantUML architecture and flow diagrams.
- `docker-compose.yml`: Local multi-service setup for Postgres, backend, and frontend.

## Build, Test, and Development Commands

Run commands from the relevant module unless noted.

- `cd frontend && npm run dev`: start the Refine/Vite development server.
- `cd frontend && npm run lint`: run ESLint checks for TypeScript and React hooks.
- `cd frontend && npm run build`: run TypeScript compilation and production build.
- `cd backend && ./gradlew build`: compile, test, and package the Spring Boot service.
- `cd backend && ./gradlew test`: run backend tests only.
- `docker compose up --build`: build and run Postgres, backend, and frontend together.

## Monitoring & Observability

Stage 1 is Prometheus-only (Grafana + tracing/logs are Stage 2). All monitoring
config has a **single source of truth** in
`infrastructure/kubernetes/triptailor/files/monitoring/` (see its `README.md`),
consumed by both `docker-compose.yml` (via the repo-root `monitoring` symlink) and
the Helm chart (via `templates/monitoring-prometheus.yaml` + `.Files.Get`). Service
names match across both environments, so `prometheus/prometheus.yml` needs no
per-environment variants.

- All four runtime services expose metrics: Spring services at
  `/actuator/prometheus` (Micrometer), FastAPI services at `/metrics`
  (`prometheus-fastapi-instrumentator`). New backend `/actuator/*` paths that
  should be scraped must be permitted in `backend/.../config/SecurityConfig.kt`.
- Custom GenAI metrics live in `genai-service/app/observability/metrics.py`.
- Edit alert rules in `files/monitoring/prometheus/alert.rules.yml`; validate with
  `promtool check rules` before committing.
- Toggle the K8s stack with the `monitoring.enabled` value (default `true`).

## Coding Style & Naming Conventions

Use Kotlin idioms in the backend with packages under `com.vacation.app`. Keep class names in `PascalCase`, functions and properties in `camelCase`, and test classes ending in `Tests`.

Frontend code uses TypeScript and React function components. Name components in `PascalCase`, hooks as `useSomething`, and page folders by route, for example `src/pages/vacations/list.tsx`. Follow the existing two-space frontend indentation and tab indentation used by Gradle/Kotlin templates. Use ESLint as the frontend style authority.

## Testing Guidelines

Backend tests use JUnit 5 through Gradle; place tests under `backend/src/test/kotlin` and prefer focused Spring tests for controller/service behavior. The frontend currently has lint and build validation but no dedicated test runner configured. Run `npm run lint`, `npm run build`, and `./gradlew build` before PRs that touch both modules.

## Commit & Pull Request Guidelines

Git history uses short summaries and issue references, for example `#6: Add basic openAPI specification...` and `fix: update analysis object model...`. Keep commits focused and include the issue number when available.

Pull requests should include a clear description, linked issue, test results, and screenshots for visible UI changes. Note any API contract changes and update `api-specification/` or `diagrams/` when behavior crosses module boundaries.

## Security & Configuration Tips

Do not commit secrets. Local Docker credentials in `docker-compose.yml` are development defaults only. Keep environment-specific configuration in ignored local files or deployment settings.
