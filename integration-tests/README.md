# Integration tests

Cross-service tests that drive the real stack through the gateway. Unlike the per-service test
suites, nothing here stubs a service boundary: `backend`, `genai-service`,
`travel-context-service` and Postgres all run for real, and only third-party APIs (the LLM,
Nominatim, SerpAPI, Open-Meteo) are faked by a WireMock container. What is under test is the
traffic between our own services -- the thing the unit suites mock out and therefore cannot catch.

## Running locally

```bash
docker compose -f docker-compose.yml -f docker-compose.ci.yml up --build --detach --wait
# Readiness gate these tests assume. COMPOSE_FILES must match the -f flags above.
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.ci.yml" bash scripts/docker-compose-smoke.sh
pip install -r integration-tests/requirements.txt
pytest integration-tests --verbose
docker compose -f docker-compose.yml -f docker-compose.ci.yml down --volumes --remove-orphans
```

Both `-f` flags are required on *every* compose command. Omitting the override on `down` leaves
the WireMock container orphaned.

## Layout

- `test_stack.py` -- the end-to-end flow.
- `wiremock/mappings/*.json` -- third-party stubs, mounted into the WireMock container.

## Debugging a stub mismatch

WireMock runs with `--verbose`, so unmatched requests are logged with the closest stub and a
diff:

```bash
docker compose -f docker-compose.yml -f docker-compose.ci.yml logs mock-externals
```

`GET http://localhost:8080/__admin/requests` lists everything received, but the port is only
reachable from inside the compose network (`docker compose exec gateway wget -qO- ...`).

## Changing the stubs

The LLM stubs are matched on prompt text, so renaming a prompt in `schedule_prompts.py` will
silently fall through to no match. The schedule stub's response must also satisfy
`_validate_schedule_contract` in `genai-service/app/services/schedule_service.py`: one day per
requested date with dates matching `TRIP_START`/`TRIP_END` exactly, sequential `dayNumber`,
3-5 activities per day, each time block at most once per day, titles unique across the schedule,
and `durationMinutes` within 30-360.
