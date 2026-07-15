# Security Scanner — Remediation Notes

This branch (`fix/security-scanner-findings`) addresses the actionable findings from the
`devops26 check-packages` scan (Trivy, KICS, zizmor, Hadolint, Dockle, gitleaks, npm audit).
Below are the **accepted residuals** — findings deliberately not changed, with the reason.

## Kubernetes (KICS)

- **Root filesystem not read-only** (`a9c2f49d`): not enabled. The JVM, nginx and uvicorn
  images write to `/tmp` (and nginx to its cache/run dirs). Enabling `readOnlyRootFilesystem`
  safely requires per-service writable `emptyDir` mounts that cannot be validated without a
  live cluster; deferred to avoid CrashLoop risk. All containers already drop `ALL`
  capabilities, run non-root, and set `allowPrivilegeEscalation: false`.
- **Pod/Container without LimitRange / ResourceQuota** (`4a20ebac`, `48a5beba`): not added.
  A namespace `ResourceQuota` can block scheduling on the constrained AET/student cluster.
  Explicit per-container `requests`+`limits` are now set instead.
- **Using unrecommended namespace "default"** (`611ab018`): false positive for a Helm chart —
  the release namespace is supplied at install time (`helm ... -n team-continuous-vacation`),
  not hardcoded in templates.
- **Kubernetes native secret management** (`b9c83569`) / **Secrets as env vars** (`3d658f8b`):
  accepted. An external secret store (Vault / External Secrets Operator) is out of scope for
  this project; secrets are injected from CI via `--set-file`.
- **Postgres volume not read-only** (`b7652612`): postgres must write its data directory.

## Terraform (KICS)

- **DDoS protection plan disabled** (`b4cc2c52`): a standard Azure DDoS plan is a paid add-on;
  not justified for a single demo VM.
- **NIC with public IP** (`c1573577`) / **SSH exposed to the internet** (`3e3c175e`): the VM is
  reached over its public IP by the GitHub Actions runner (dynamic egress IPs) for Ansible
  deployment, so the SSH NSG rule cannot be narrowed to a fixed CIDR without breaking CD.

## Container images (Trivy)

- **Debian `python:3.11-slim` OS CVEs with `Fixed Version: none`** (curl, perl-base, ncurses,
  util-linux, …): cannot be resolved by `apt-get upgrade`. `apt-get upgrade` is applied to pick
  up the CVEs that *do* have fixes; the remainder would require a base-image change (distroless /
  Chainguard / alpine), tracked as a follow-up.

## Dockerfiles (Hadolint)

- **DL3022 `COPY --from` should reference a FROM alias**: false positive. `api-spec` is a Docker
  buildx *named build context* (`--build-context api-spec=./api-specification`), not a build
  stage.

## Frontend (npm audit)

- The scanner's Trivy findings are all fixed via `overrides`. `npm audit` (a different advisory
  DB) additionally flags `tmp` (transitively via `@refinedev/cli` → `jscodeshift`); the only
  `npm audit fix` is a breaking downgrade of `@refinedev/cli`, deferred. `undici`/`vite` dev-only
  advisories are picked up by the same override/refresh pass.
