#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-triptailor-local}"
RELEASE="${RELEASE:-triptailor}"
FORCE_BUILD_IMAGES="${FORCE_BUILD_IMAGES:-0}"
MOCK_CPU="${MOCK_CPU:-1}"
SIMULATED_LOAD_DELAY="${SIMULATED_LOAD_DELAY:-10}"
HPA_MIN_REPLICAS="${HPA_MIN_REPLICAS:-1}"
HPA_MAX_REPLICAS="${HPA_MAX_REPLICAS:-3}"
HPA_TARGET_CPU="${HPA_TARGET_CPU:-20}"
BACKEND_CPU_REQUEST="${BACKEND_CPU_REQUEST:-50m}"
REAL_LOAD_SECONDS="${REAL_LOAD_SECONDS:-90}"
SCALE_TIMEOUT_SECONDS="${SCALE_TIMEOUT_SECONDS:-180}"

required_commands=(kubectl)

for command in "${required_commands[@]}"; do
	if ! command -v "${command}" >/dev/null 2>&1; then
		echo "Missing required command: ${command}" >&2
		exit 1
	fi
done

if [[ "${HPA_MAX_REPLICAS}" -lt 2 ]]; then
	echo "HPA_MAX_REPLICAS must be at least 2 for the autoscaling demo." >&2
	exit 1
fi

wait_for_backend_replicas() {
	local expected="$1"
	local timeout_seconds="$2"
	local deadline=$((SECONDS + timeout_seconds))

	while [[ "${SECONDS}" -lt "${deadline}" ]]; do
		local ready_replicas
		ready_replicas="$(kubectl -n "${NAMESPACE}" get deploy/backend -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true)"
		ready_replicas="${ready_replicas:-0}"

		if [[ "${ready_replicas}" -ge "${expected}" ]]; then
			return 0
		fi

		sleep 5
	done

	return 1
}

wait_for_backend_replicas_exactly() {
	local expected="$1"
	local timeout_seconds="$2"
	local deadline=$((SECONDS + timeout_seconds))

	while [[ "${SECONDS}" -lt "${deadline}" ]]; do
		local ready_replicas
		ready_replicas="$(kubectl -n "${NAMESPACE}" get deploy/backend -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true)"
		ready_replicas="${ready_replicas:-0}"

		if [[ "${ready_replicas}" -eq "${expected}" ]]; then
			return 0
		fi

		sleep 5
	done

	return 1
}

show_autoscaling_state() {
	echo
	echo "HPA:"
	kubectl -n "${NAMESPACE}" get hpa backend
	echo
	echo "Backend deployment:"
	kubectl -n "${NAMESPACE}" get deploy backend
	echo
	echo "Backend pods:"
	kubectl -n "${NAMESPACE}" get pods -l app.kubernetes.io/component=backend -o wide
}

echo "Deploying backend autoscaling demo..."
NAMESPACE="${NAMESPACE}" \
	RELEASE="${RELEASE}" \
	FORCE_BUILD_IMAGES="${FORCE_BUILD_IMAGES}" \
	BACKEND_AUTOSCALING_ENABLED=true \
	BACKEND_AUTOSCALING_MIN_REPLICAS="${HPA_MIN_REPLICAS}" \
	BACKEND_AUTOSCALING_MAX_REPLICAS="${HPA_MAX_REPLICAS}" \
	BACKEND_AUTOSCALING_TARGET_CPU="${HPA_TARGET_CPU}" \
	BACKEND_CPU_REQUEST="${BACKEND_CPU_REQUEST}" \
	"${ROOT_DIR}/start.sh"

kubectl -n "${NAMESPACE}" rollout status deploy/backend --timeout=180s
kubectl -n "${NAMESPACE}" get hpa backend >/dev/null

show_autoscaling_state

if [[ "${MOCK_CPU}" == "1" ]]; then
	echo
	echo "MOCK_CPU=1: simulating a CPU pressure signal without burning laptop CPU."
	echo "Normalizing backend to 1 replica before the simulated scale-out."
	kubectl -n "${NAMESPACE}" scale deploy/backend --replicas=1

	if ! wait_for_backend_replicas_exactly 1 "${SCALE_TIMEOUT_SECONDS}"; then
		echo "Backend did not settle at 1 ready replica within ${SCALE_TIMEOUT_SECONDS}s." >&2
		show_autoscaling_state >&2
		exit 1
	fi

	show_autoscaling_state
	echo
	echo "After ${SIMULATED_LOAD_DELAY}s, the script will raise the HPA minimum to 2 replicas."
	sleep "${SIMULATED_LOAD_DELAY}"

	kubectl -n "${NAMESPACE}" patch hpa backend --type merge -p '{"spec":{"minReplicas":2}}'

	if ! wait_for_backend_replicas 2 "${SCALE_TIMEOUT_SECONDS}"; then
		echo "Backend did not reach 2 ready replicas within ${SCALE_TIMEOUT_SECONDS}s." >&2
		show_autoscaling_state >&2
		exit 1
	fi

	show_autoscaling_state
	echo
	echo "Simulated autoscaling succeeded: the HPA raised backend capacity to at least 2 ready replicas."
	exit 0
fi

echo
echo "MOCK_CPU=0: running a real CPU-based HPA demo."
if ! kubectl get apiservice v1beta1.metrics.k8s.io >/dev/null 2>&1; then
	echo "The Kubernetes metrics API is not available. Install metrics-server or run the default MOCK_CPU=1 demo." >&2
	exit 1
fi

backend_pod="$(kubectl -n "${NAMESPACE}" get pods -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')"
if [[ -z "${backend_pod}" ]]; then
	echo "Could not find a backend pod for the real CPU demo." >&2
	exit 1
fi

echo "Starting bounded CPU work in ${backend_pod} for ${REAL_LOAD_SECONDS}s..."
kubectl -n "${NAMESPACE}" exec "${backend_pod}" -- sh -c "timeout ${REAL_LOAD_SECONDS} sh -c 'while true; do :; done'" >/dev/null 2>&1 &
load_pid="$!"

if ! wait_for_backend_replicas 2 "${SCALE_TIMEOUT_SECONDS}"; then
	kill "${load_pid}" >/dev/null 2>&1 || true
	echo "Backend did not scale to 2 ready replicas within ${SCALE_TIMEOUT_SECONDS}s." >&2
	show_autoscaling_state >&2
	exit 1
fi

wait "${load_pid}" >/dev/null 2>&1 || true
show_autoscaling_state
echo
echo "Real autoscaling succeeded: backend reached at least 2 ready replicas."
