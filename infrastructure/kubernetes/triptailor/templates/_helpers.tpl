{{/*
Common labels.
*/}}
{{- define "triptailor.labels" -}}
app.kubernetes.io/name: {{ include "triptailor.name" . }}
helm.sh/chart: {{ include "triptailor.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "triptailor.selectorLabels" -}}
app.kubernetes.io/name: {{ include "triptailor.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "triptailor.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "triptailor.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "triptailor.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "triptailor.imagePullSecrets" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{/*
Pod-level security context. Callers pass a dict with the numeric "uid" the image
runs as (and optionally "gid"/"fsGroup"). Resolves KICS "Container Running As Root",
"Container Running With Low UID" and "Seccomp Profile Is Not Configured".
Usage: {{ include "triptailor.podSecurityContext" (dict "uid" 1000) }}
*/}}
{{- define "triptailor.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .uid }}
runAsGroup: {{ .gid | default .uid }}
fsGroup: {{ .fsGroup | default (.gid | default .uid) }}
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/*
Container-level hardening security context. Resolves KICS "Privilege Escalation
Allowed", "NET_RAW Capabilities Not Being Dropped", "No Drop Capabilities for
Containers" and "Container Capabilities Unrestricted".
*/}}
{{- define "triptailor.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
{{- end }}
