# Backend API

Spring Boot backend-for-frontend for TripTailor. It exposes the public app API, issues and validates JWT bearer tokens, orchestrates trip generation, persists travelers and trips in PostgreSQL, and calls the internal GenAI service.

## Responsibilities

- Register, login, and demo traveler sessions.
- Validate JWTs for protected trip endpoints.
- Generate trips by requesting a schedule from `genai-service` and persisting it to PostgreSQL.
- Fetch, delete, and micro-regenerate trip activities.
- Serve interactive OpenAPI documentation at `/` and the copied API spec at `/openapi.yaml`.

## Commands

```bash
./gradlew build
./gradlew test
./gradlew test jacocoTestReport
```

The JaCoCo HTML report is written to `build/reports/jacoco/test/html/index.html`; XML is written to `build/reports/jacoco/test/jacocoTestReport.xml` for CI artifacts.

## Configuration

Important environment-backed properties are defined in `src/main/resources/application.properties`:

- `SPRING_DATASOURCE_URL`: PostgreSQL JDBC URL.
- `SPRING_DATASOURCE_USERNAME` / `SPRING_DATASOURCE_PASSWORD`: database credentials.
- `GENAI_BASE_URL`: internal GenAI service URL.
- `JWT_SECRET`: HS256 signing secret, at least 32 bytes.

The OpenAPI resource is copied from `../api-specification/frontend.yaml` during Gradle resource processing.
