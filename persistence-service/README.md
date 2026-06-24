# Persistence Service

Internal Spring Boot service that owns PostgreSQL access for travelers, authentication records, trips, days, activities, and activity tags. It is consumed by the backend API and is not intended to be exposed directly to browsers.

## Responsibilities

- Create demo and registered traveler records.
- Return auth records with password hashes only to the backend API.
- Persist and retrieve complete trip schedules.
- Update or delete individual activities by trip, day, and activity ID.
- Serve interactive OpenAPI documentation at `/` and the copied API spec at `/openapi.yaml`.

## Commands

```bash
./gradlew build
./gradlew test
./gradlew test jacocoTestReport
```

The JaCoCo HTML report is written to `build/reports/jacoco/test/html/index.html`; XML is written to `build/reports/jacoco/test/jacocoTestReport.xml` for CI artifacts.

## Configuration

The service reads datasource settings from `src/main/resources/application.properties`:

- `SPRING_DATASOURCE_URL`
- `SPRING_DATASOURCE_USERNAME`
- `SPRING_DATASOURCE_PASSWORD`

Tests use H2 in PostgreSQL compatibility mode. The OpenAPI resource is copied from `../api-specification/persistance.yaml` during Gradle resource processing; the filename is kept for compatibility with existing scripts.
