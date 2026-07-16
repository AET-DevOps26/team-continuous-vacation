#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:3000}"
TEMPO_URL="${TEMPO_URL:-http://localhost:3200}"
TRAVEL_CONTEXT_URL="${TRAVEL_CONTEXT_URL:-http://localhost:8090}"
SMOKE_RETRIES="${SMOKE_RETRIES:-60}"
SMOKE_SLEEP_SECONDS="${SMOKE_SLEEP_SECONDS:-2}"
# Deliberately unquoted at the call sites so it word-splits into separate flags. Callers that
# layer on an override (see docker-compose.ci.yml) must pass it here too, or the exited-service
# check below silently ignores the extra services.
COMPOSE_FILES="${COMPOSE_FILES:-}"

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
		if docker compose ${COMPOSE_FILES} exec -T gateway wget -qO- "${url}" >/dev/null 2>&1; then
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
wait_for_internal_http "genai service" "http://genai-service:8000/health"
wait_for_http "travel context service" "${TRAVEL_CONTEXT_URL}/health"
wait_for_http "Prometheus through gateway" "${GATEWAY_URL}/prometheus/-/healthy"
wait_for_http "Grafana through gateway" "${GATEWAY_URL}/grafana/api/health"
wait_for_http "Tempo" "${TEMPO_URL}/ready"

exited_services="$(docker compose ${COMPOSE_FILES} ps --status exited --services)"
if [[ -n "${exited_services}" ]]; then
	echo "Compose services exited unexpectedly:" >&2
	echo "${exited_services}" >&2
	exit 1
fi

docker compose ${COMPOSE_FILES} ps
