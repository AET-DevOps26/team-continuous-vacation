# Integration tests

Cross-service tests that drive the real stack through the gateway. Unlike the per-service test
suites, nothing here stubs a service boundary: `backend`, `genai-service`,
`travel-context-service` and Postgres all run for real, and only third-party APIs (the LLM,
Nominatim, SerpAPI, Open-Meteo) are faked by the `mock-providers` container. What is under test
is the traffic between our own services -- the thing the unit suites mock out and therefore
cannot catch.

## Running locally

```bash
export COMPOSE_FILE=docker-compose.yml:docker-compose.ci.yml
docker compose up --build --detach --wait
bash scripts/docker-compose-smoke.sh   # readiness gate these tests assume
pip install -r integration-tests/requirements.txt
pytest integration-tests --verbose
docker compose down --volumes --remove-orphans
```

`COMPOSE_FILE` is compose's own variable, so every command above picks up the CI override
without repeating `-f` flags. Without it, `up` would start no mock and `down` would orphan the
`mock-providers` container.

## Layout

- `test_stack.py` -- the end-to-end flow.
- `../tests/mock-providers/server.py` -- the third-party fake, shared with the compose smoke test.

## Changing the stubs

The LLM stubs are matched on prompt text, so renaming a prompt in `schedule_prompts.py` will
silently fall through to the wrong branch of `route()`. The stub responses must also satisfy the
contract validators in `genai-service/app/services/schedule_service.py`:

- `_validate_schedule_contract`: one day per requested date with dates matching the request
  exactly, sequential `dayNumber`, 3-5 activities per day, each time block at most once per day,
  titles unique across the schedule, and `durationMinutes` within 30-360. `server.py` derives the
  days from the prompt's `startDate`/`endDate`, so any trip length works.
- `_validate_alternative_contract`: the replacement must keep the original `timeBlock` and reuse
  neither the replaced title nor any other title in the trip.
