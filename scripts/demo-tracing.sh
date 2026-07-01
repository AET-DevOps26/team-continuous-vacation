#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:3000}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
REQUEST_BODY='{"destination":"Munich","startDate":"2026-07-15","endDate":"2026-07-16","vibe":"Culture"}'

required_commands=(curl docker python3)

for command in "${required_commands[@]}"; do
	if ! command -v "${command}" >/dev/null 2>&1; then
		echo "Missing required command: ${command}" >&2
		exit 1
	fi
done

compose() {
	docker compose "$@"
}

echo "Starting TripTailor with Tempo and Grafana tracing..."
compose up --build -d

echo
echo "Waiting for gateway at ${GATEWAY_URL}..."
gateway_ready=0
for _ in $(seq 1 60); do
	if curl -fsS "${GATEWAY_URL}/api/health" >/dev/null 2>&1; then
		gateway_ready=1
		break
	fi
	sleep 2
done

if [[ "${gateway_ready}" != "1" ]]; then
	echo "Gateway did not become ready. Recent logs:" >&2
	compose logs --tail=80 gateway backend persistence-service genai-service travel-context-service >&2
	exit 1
fi

echo "Creating demo session..."
auth_response="$(curl -fsS -X POST "${GATEWAY_URL}/api/auth/demo")"
access_token="$(AUTH_RESPONSE="${auth_response}" python3 - <<'PY'
import json
import os

print(json.loads(os.environ["AUTH_RESPONSE"])["accessToken"])
PY
)"

tmp_response="$(mktemp)"
cleanup() {
	rm -f "${tmp_response}"
}
trap cleanup EXIT

echo
echo "Generating a trip to create an end-to-end trace..."
http_status="$(
	curl -sS -o "${tmp_response}" -w "%{http_code}" \
		-X POST "${GATEWAY_URL}/api/trips" \
		-H "Authorization: Bearer ${access_token}" \
		-H "Content-Type: application/json" \
		-d "${REQUEST_BODY}"
)"

echo "Trip generation HTTP status: ${http_status}"
if [[ "${http_status}" -ge 500 ]]; then
	echo "The request reached the traced service flow but ended with ${http_status}."
	echo "That is expected if no real LLM endpoint/API key is configured locally."
else
	echo "Trip generation response:"
	cat "${tmp_response}"
	echo
fi

echo
echo "Recent correlated service logs:"
compose logs --tail=60 backend persistence-service genai-service travel-context-service \
	| grep -E "trace_id=|traceId|span_id=|spanId" || true

echo
echo "Open Grafana at ${GRAFANA_URL}"
echo "Open Dashboards -> TripTailor -> TripTailor Services for metrics."
echo "Use Explore -> Tempo and search recent traces for services:"
echo "  backend, persistence-service, genai-service, travel-context-service"
echo
echo "Tempo is also available at http://localhost:3200"
