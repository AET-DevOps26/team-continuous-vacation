#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:3000}"
TEMPO_URL="${TEMPO_URL:-http://localhost:3200}"
TRAVEL_CONTEXT_URL="${TRAVEL_CONTEXT_URL:-http://localhost:8090}"
SMOKE_RETRIES="${SMOKE_RETRIES:-60}"
SMOKE_SLEEP_SECONDS="${SMOKE_SLEEP_SECONDS:-2}"

wait_for_http() {
	local name="$1"
	local url="$2"

	for _ in $(seq 1 "${SMOKE_RETRIES}"); do
		if curl -fsS "${url}" >/dev/null 2>&1; then
			echo "${name} is healthy (${url})"
			return 0
		fi
		sleep "${SMOKE_SLEEP_SECONDS}"
	done

	echo "${name} did not become healthy at ${url}" >&2
	return 1
}

wait_for_internal_http() {
	local name="$1"
	local url="$2"

	for _ in $(seq 1 "${SMOKE_RETRIES}"); do
		if docker compose exec -T gateway wget -qO- "${url}" >/dev/null 2>&1; then
			echo "${name} is healthy (${url})"
			return 0
		fi
		sleep "${SMOKE_SLEEP_SECONDS}"
	done

	echo "${name} did not become healthy at ${url}" >&2
	return 1
}

wait_for_http "frontend through gateway" "${GATEWAY_URL}/"
wait_for_http "backend through gateway" "${GATEWAY_URL}/api/health"
wait_for_internal_http "persistence service" "http://persistence-service:8081/health"
wait_for_internal_http "genai service" "http://genai-service:8000/health"
wait_for_http "travel context service" "${TRAVEL_CONTEXT_URL}/health"
wait_for_http "Prometheus through gateway" "${GATEWAY_URL}/prometheus/-/healthy"
wait_for_http "Grafana through gateway" "${GATEWAY_URL}/grafana/api/health"
wait_for_http "Tempo" "${TEMPO_URL}/ready"

if docker compose ps --services | grep -qx "mock-providers"; then
	start_date="$(python3 -c 'from datetime import date,timedelta; print(date.today() + timedelta(days=1))')"
	end_date="$(python3 -c 'from datetime import date,timedelta; print(date.today() + timedelta(days=2))')"
	trip_payload="{\"destination\":\"Munich\",\"startDate\":\"${start_date}\",\"endDate\":\"${end_date}\",\"vibe\":\"cultural\"}"

	context_response="$(curl -fsS -H 'Content-Type: application/json' \
		--data "${trip_payload}" "${TRAVEL_CONTEXT_URL}/trip-context")"
	python3 -c 'import json,sys; value=json.load(sys.stdin); assert value["events"] and value["weather"]' \
		<<<"${context_response}"
	echo "Mocked travel-context provider flow returned events and weather"

	schedule_response="$(docker compose exec -T gateway wget -qO- \
		--header='Content-Type: application/json' --post-data="${trip_payload}" \
		http://genai-service:8000/schedules/generate)"
	python3 -c 'import json,sys; value=json.load(sys.stdin); assert len(value["days"]) == 2' \
		<<<"${schedule_response}"
	echo "Mocked GenAI -> travel-context -> provider flow generated a two-day schedule"
elif [[ "${REAL_PROVIDER_SMOKE:-false}" == "true" ]]; then
	start_date="$(python3 -c 'from datetime import date,timedelta; print(date.today() + timedelta(days=1))')"
	end_date="$(python3 -c 'from datetime import date,timedelta; print(date.today() + timedelta(days=2))')"
	trip_payload="{\"destination\":\"Munich\",\"startDate\":\"${start_date}\",\"endDate\":\"${end_date}\",\"vibe\":\"cultural\"}"
	schedule_response="$(docker compose exec -T gateway wget -qO- \
		--header='Content-Type: application/json' --post-data="${trip_payload}" \
		http://genai-service:8000/schedules/generate)"
	python3 -c 'import json,sys; value=json.load(sys.stdin); assert len(value["days"]) == 2' \
		<<<"${schedule_response}"
	echo "Controlled real-provider/LLM smoke generation succeeded (response not logged)"
fi

exited_services="$(docker compose ps --status exited --services)"
if [[ -n "${exited_services}" ]]; then
	echo "Compose services exited unexpectedly:" >&2
	echo "${exited_services}" >&2
	exit 1
fi

docker compose ps
