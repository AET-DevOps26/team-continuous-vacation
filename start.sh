#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="${ROOT_DIR}/infrastructure/kubernetes/triptailor"
LOCAL_VALUES="${CHART_DIR}/values-local.yaml"
NAMESPACE="${NAMESPACE:-triptailor-local}"
RELEASE="${RELEASE:-triptailor}"

HELM_VERSION="${HELM_VERSION:-v3.15.4}"
HELM_BIN="${HELM_BIN:-}"
required_commands=(docker kubectl)

for command in "${required_commands[@]}"; do
	if ! command -v "${command}" >/dev/null 2>&1; then
		echo "Missing required command: ${command}" >&2
		exit 1
	fi
done

if [[ -z "${HELM_BIN}" ]]; then
	if command -v helm >/dev/null 2>&1; then
		HELM_BIN="helm"
	else
		case "$(uname -s)" in
			Darwin) helm_os="darwin" ;;
			Linux) helm_os="linux" ;;
			*)
				echo "Unsupported OS for automatic Helm download: $(uname -s)" >&2
				exit 1
				;;
		esac

		case "$(uname -m)" in
			x86_64 | amd64) helm_arch="amd64" ;;
			arm64 | aarch64) helm_arch="arm64" ;;
			*)
				echo "Unsupported CPU architecture for automatic Helm download: $(uname -m)" >&2
				exit 1
				;;
		esac

		if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
			echo "Helm is not installed, and curl/tar are required to download it automatically." >&2
			exit 1
		fi

		helm_dir="/tmp/triptailor-helm-${HELM_VERSION}-${helm_os}-${helm_arch}"
		HELM_BIN="${helm_dir}/${helm_os}-${helm_arch}/helm"

		if [[ ! -x "${HELM_BIN}" ]]; then
			echo "Helm not found. Downloading ${HELM_VERSION} to ${helm_dir}"
			mkdir -p "${helm_dir}"
			curl -fsSL "https://get.helm.sh/helm-${HELM_VERSION}-${helm_os}-${helm_arch}.tar.gz" \
				-o "${helm_dir}/helm.tar.gz"
			tar -xzf "${helm_dir}/helm.tar.gz" -C "${helm_dir}"
			chmod +x "${HELM_BIN}"
		fi
	fi
fi

if ! kubectl config current-context >/dev/null 2>&1; then
	echo "kubectl has no current context. Enable Docker Desktop Kubernetes or select a local cluster." >&2
	exit 1
fi

build_image_if_missing() {
	local image="$1"
	local context="$2"
	shift 2

	if docker image inspect "${image}" >/dev/null 2>&1; then
		echo "Image exists: ${image}"
		return
	fi

	echo "Building missing image: ${image}"
	docker build -t "${image}" "$@" "${context}"
}

build_image_if_missing "triptailor/backend:latest" "${ROOT_DIR}/backend" \
	--build-context "api-spec=${ROOT_DIR}/api-specification"
build_image_if_missing "triptailor/persistence-service:latest" "${ROOT_DIR}/persistence-service" \
	--build-context "api-spec=${ROOT_DIR}/api-specification"
build_image_if_missing "triptailor/genai-service:latest" "${ROOT_DIR}/genai-service"
build_image_if_missing "triptailor/frontend:latest" "${ROOT_DIR}/frontend" \
	--build-context "api-spec=${ROOT_DIR}/api-specification"

"${HELM_BIN}" upgrade --install "${RELEASE}" "${CHART_DIR}" \
	--namespace "${NAMESPACE}" \
	--create-namespace \
	-f "${LOCAL_VALUES}"

kubectl -n "${NAMESPACE}" rollout status deploy/db --timeout=180s
kubectl -n "${NAMESPACE}" rollout status deploy/persistence-service --timeout=180s
kubectl -n "${NAMESPACE}" rollout status deploy/genai-service --timeout=180s
kubectl -n "${NAMESPACE}" rollout status deploy/backend --timeout=180s
kubectl -n "${NAMESPACE}" rollout status deploy/frontend --timeout=180s

echo
echo "TripTailor is running at http://localhost:30080"
