#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-triptailor-local}"
RELEASE="${RELEASE:-triptailor}"
BACKEND_REPLICAS="${BACKEND_REPLICAS:-3}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:30080}"
REQUESTS="${REQUESTS:-30}"

required_commands=(curl kubectl sort)

for command in "${required_commands[@]}"; do
	if ! command -v "${command}" >/dev/null 2>&1; then
		echo "Missing required command: ${command}" >&2
		exit 1
	fi
done

echo "Deploying ${BACKEND_REPLICAS} backend replicas..."
NAMESPACE="${NAMESPACE}" RELEASE="${RELEASE}" BACKEND_REPLICAS="${BACKEND_REPLICAS}" FORCE_BUILD_IMAGES=1 "${ROOT_DIR}/start.sh"

echo
echo "Backend pods:"
kubectl -n "${NAMESPACE}" get pods -l app.kubernetes.io/component=backend -o wide

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

echo
echo "Calling ${GATEWAY_URL}/api/debug/instance ${REQUESTS} times..."
for i in $(seq 1 "${REQUESTS}"); do
	response="$(curl -fsS "${GATEWAY_URL}/api/debug/instance")"
	instance="$(printf '%s\n' "${response}" | sed -n 's/.*"instance"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"

	if [[ -z "${instance}" ]]; then
		echo "Could not parse backend instance from response: ${response}" >&2
		exit 1
	fi

	printf '%02d  %s\n' "${i}" "${instance}"
	printf '%s\n' "${instance}" >>"${tmp_file}"
done

echo
echo "Distinct backend instances observed:"
sort -u "${tmp_file}"

distinct_count="$(sort -u "${tmp_file}" | wc -l | tr -d ' ')"
if [[ "${distinct_count}" -lt 2 ]]; then
	echo
	echo "Only one backend instance was observed. Re-run the script or increase REQUESTS to sample more requests." >&2
	exit 1
fi

echo
echo "Observed ${distinct_count} backend instances through the gateway."
