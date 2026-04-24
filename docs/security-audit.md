# CIS — Security Audit & Threat Model

> Audit date: 2026-04-24  
> Scope: full stack (FastAPI backend, Celery worker, execution sandbox,
> nginx reverse-proxy, PostgreSQL, Redis, MinIO, Docker-compose deployment)

---

## 1. Architecture recap

```
Internet
  │  HTTPS only (TLS 1.2/1.3)
  ▼
[nginx]  (rate-limit, headers, TLS termination)
  │
  ├─[frontend SPA]
  │
  └─[FastAPI backend]  ←── JWT auth, RBAC, audit log
        │  Celery task (Redis queue)
        ▼
      [Celery worker]
        │  docker run --rm …
        ▼
      [Sandbox container]  (uid=1000, --network none, --read-only, cap-drop ALL,
                            seccomp allowlist, AppArmor MAC, mem/CPU limits)
```

The control plane **never executes scripts**.  Only the worker spawns containers.

---

## 2. Threat Model

### 2.1 Assets

| Asset | Sensitivity |
|-------|------------|
| Script content | High — can run code on infra |
| User credentials (bcrypt hash + JWT) | High |
| Task stdout/stderr | Medium — may contain secrets from target hosts |
| Audit logs | High — forensic evidence |
| Docker socket (worker) | Critical — full host takeover if leaked |

### 2.2 Threat actors

| Actor | Capability | Entry point |
|-------|-----------|-------------|
| Unauthenticated external attacker | Web-facing API | `/api/v1/auth/*` |
| Authenticated low-privilege user | All authenticated API | Scripts, Tasks |
| Compromised reviewer/admin | Privileged API | Script approval, Role management |
| Malicious script content | Executed inside sandbox | Worker → container |
| Insider / compromised host | SSH/container access | Docker socket, DB |

---

## 3. Attack Paths & Risk Levels

### 3.1 Remote Code Execution (RCE)

| # | Attack Path | Risk | Mitigation |
|---|------------|------|-----------|
| R1 | Submit script with forbidden module → bypass validator → approved → executed | **HIGH** | Multi-layer: static validator + human review gate (script must be `approved`) + Docker sandbox (network=none, read-only, seccomp) |
| R2 | Submit shell script with obfuscated pattern bypassing regex validator | **MEDIUM** | Regex is defence-in-depth; sandbox makes code execution impact-limited (no network, no persistence) |
| R3 | YAML billion-laughs / entity expansion in playbook content | **LOW** | `yaml.safe_load` used — entity expansion disabled |
| R4 | Large script content causes memory exhaustion during validation | **MEDIUM** | **Fixed:** `ScriptCreate.content` capped at 64 KiB in schema |

### 3.2 Privilege Escalation

| # | Attack Path | Risk | Mitigation |
|---|------------|------|-----------|
| P1 | Container escape via `CAP_SYS_ADMIN` | **CRITICAL** | `--cap-drop ALL` + seccomp blocks `mount`/`unshare`/`setns`/`kexec_load` + AppArmor `deny mount` |
| P2 | setuid binary inside container re-gains root | **HIGH** | `no-new-privileges:true`; seccomp blocks `setuid`/`setgid`/`capset` |
| P3 | JWT role claim manipulation | **LOW** | JWT role claim is informational only; `get_current_user` always re-reads `user.role` from DB |
| P4 | Admin promotes attacker-controlled account to admin with no audit trail | **MEDIUM** | **Fixed:** `admin.user.role_update` audit log records actor, target, old/new role |
| P5 | Container writes to /tmp, drops SUID binary, executes it | **HIGH** | `/tmp` mounted `noexec,nosuid,nodev` |

### 3.3 Lateral Movement

| # | Attack Path | Risk | Mitigation |
|---|------------|------|-----------|
| L1 | Compromised worker uses Docker socket to spawn privileged container → host escape | **CRITICAL** | Docker socket scoped only to worker; worker on isolated `internal` network; consider rootless Docker or Docker-in-Docker with restricted daemon in production |
| L2 | Malicious container connects to internal PostgreSQL/Redis via container network | **HIGH** | Task containers run with `--network none` — zero network interfaces |
| L3 | Task reads `/proc` to find host process memory | **MEDIUM** | seccomp blocks `process_vm_readv/writev`; AppArmor `deny @{PROC}/** w`; read-only `/proc` access limited to `status`/`maps`/`cpuinfo`/`meminfo` |
| L4 | Attacker reads another user's task stdout (may contain secrets) | **MEDIUM** | `GET /tasks/{id}` checks `task.user_id == current_user.id` or admin role |

### 3.4 API Abuse

| # | Attack Path | Risk | Mitigation |
|---|------------|------|-----------|
| A1 | Brute-force login | **HIGH** | nginx rate-limit: 5 req/min on `/api/v1/auth/`; constant-time password comparison; uniform 401 for unknown user vs wrong password |
| A2 | IP spoofing via `X-Forwarded-For` to bypass audit log attribution | **MEDIUM** | **Fixed:** `get_client_ip` now uses `X-Real-IP` (set by nginx to `$remote_addr`) instead of trusting the client-controlled XFF header |
| A3 | Enumerate non-approved scripts of other users via `GET /scripts/{id}` | **MEDIUM** | **Fixed:** non-approved scripts now return 404 to users who are neither the submitter nor an admin/reviewer |
| A4 | Unbounded `per_page` causes full-table scans and OOM | **MEDIUM** | **Fixed:** all list endpoints cap `per_page` at 100 |
| A5 | Huge `parameters` JSON stored in DB and passed into container env | **MEDIUM** | **Fixed:** `TaskCreate.parameters` validated against 4 KiB limit |
| A6 | Replay of revoked JWT | **MEDIUM** | Token blacklist in Redis with TTL matching token expiry; refresh token rotation on each use |
| A7 | Register endpoint not rate-limited | **LOW** | Covered by nginx `auth` zone (5 req/min applies to all `/api/v1/auth/` paths) |

### 3.5 DDoS

| # | Attack Path | Risk | Mitigation |
|---|------------|------|-----------|
| D1 | Large HTTP body floods memory | **HIGH** | **Fixed:** `client_max_body_size 2m` in nginx; schema-level content cap at 64 KiB |
| D2 | Slow-loris / slow-read — open many connections and send headers slowly | **MEDIUM** | **Fixed:** `proxy_connect_timeout 5s`, `proxy_send_timeout 30s`, `proxy_read_timeout 60s` |
| D3 | Task flood — submit thousands of tasks to exhaust worker pool | **MEDIUM** | Celery concurrency capped at 4; each container has CPU cap (0.5 core), `pids_limit=100`; task queue depth bounded by Redis memory |
| D4 | Fork bomb inside sandbox | **HIGH** | `pids_limit=100` per container |
| D5 | Memory exhaustion inside sandbox | **HIGH** | `mem_limit=256m`, `memswap_limit=256m` (swap disabled) |
| D6 | CPU starvation | **HIGH** | `nano_cpus=500_000_000` (0.5 CPU per container) |
| D7 | bcrypt DoS via extremely long password | **MEDIUM** | **Fixed:** password capped at 128 characters in `RegisterRequest` |
| D8 | Connection flood per IP | **MEDIUM** | `limit_conn conn_per_ip 30` in nginx |

---

## 4. Defensive Measures Summary

### 4.1 Already in place (pre-audit)

| Layer | Controls |
|-------|---------|
| Transport | TLS 1.2/1.3 only; HSTS; nginx rate limiting |
| Authentication | bcrypt (cost 12); JWT access (15 min) + refresh (7 days) with blacklist; refresh rotation |
| Authorisation | RBAC (admin / reviewer / user); `require_role` dependency; ownership checks |
| Script pipeline | Human review gate; static validator (forbidden modules + shell patterns) |
| Sandbox | uid=1000; `--network none`; `--read-only`; `--cap-drop ALL`; `no-new-privileges`; seccomp allowlist; AppArmor MAC; `mem_limit=256m`; `pids_limit=100`; two-layer timeout |
| Audit | Every mutating action logged with IP, user, resource, status code |
| Secrets | No plaintext secrets in code; all via env/`.env`; default `SECRET_KEY` rejected via `change-me-in-production` comment |

### 4.2 Fixed by this audit

| Finding | File(s) changed | Description |
|---------|----------------|-------------|
| IP spoofing in audit logs | `backend/app/core/deps.py` | Use `X-Real-IP` (nginx `$remote_addr`) instead of first `X-Forwarded-For` element |
| bcrypt DoS via long password | `backend/app/schemas/auth.py` | Max password length 128; max username length 64 |
| Script DB storage exhaustion | `backend/app/schemas/script.py` | Script content capped at 64 KiB; title at 255 chars |
| Unbounded task parameters | `backend/app/schemas/task.py` | Parameters JSON capped at 4 KiB |
| Unbounded pagination | `backend/app/api/scripts.py`, `tasks.py`, `admin.py` | All list endpoints cap `per_page` at 100 |
| Non-approved script data leakage | `backend/app/api/scripts.py` | `GET /scripts/{id}` returns 404 for non-approved scripts to unprivileged users |
| Missing audit log on role change | `backend/app/api/admin.py` | `PUT /admin/users/{id}/role` now emits `admin.user.role_update` audit entry with old/new role |
| DDoS via large HTTP body | `nginx/nginx.conf` | `client_max_body_size 2m` added |
| Slow-loris / slow-read | `nginx/nginx.conf` | `proxy_connect_timeout`, `proxy_send_timeout`, `proxy_read_timeout` added |

---

## 5. Improvement Recommendations (non-code)

### 5.1 Docker socket hardening (HIGH priority)

The worker requires the Docker socket to spawn containers.  This is the
highest-risk component: a compromised worker effectively has root on the host.

**Recommended mitigations (choose one or more):**
- Run Docker in **rootless mode** — the daemon and all containers run as a
  non-root user; the Docker socket does not grant host root.
- Use a **dedicated Docker daemon** for the worker with a separate
  `/var/run/docker-worker.sock`, protected by a socket-proxy (e.g.
  `tecnativa/docker-socket-proxy`) that allows only `POST /containers/create`
  and `DELETE /containers/{id}` — no image management, no swarm, no volumes.
- In Kubernetes, replace Docker-in-Docker with **Tekton Pipelines** or
  **Argo Workflows** where each task step is a native K8s Pod; the Docker
  socket is never exposed.

### 5.2 Secret management (MEDIUM priority)

- Rotate `SECRET_KEY` and all service passwords regularly.
- In production, use a secrets manager (HashiCorp Vault, AWS Secrets Manager)
  rather than `.env` files on disk.
- Enable PostgreSQL TDE (or encrypt task `stdout`/`stderr` at the application
  layer) — task output can contain sensitive hostnames, keys, or config.

### 5.3 Network segmentation (MEDIUM priority)

- The `worker` service sits on the `internal` network but also creates
  containers that inherit Docker's default bridge.  Ensure the default bridge
  is not routable to the `internal` network.
- Consider dedicating a separate Docker network for sandbox containers with
  `--internal: true` so even if `--network none` is accidentally omitted they
  cannot reach the backend.

### 5.4 Supply-chain security (MEDIUM priority)

- Pin all base images to digest (e.g.
  `python:3.11-slim@sha256:<digest>`).
- Run `trivy image cis-runner:latest` in CI to block images with critical CVEs.
- Enable Docker Content Trust (`DOCKER_CONTENT_TRUST=1`) for signed image
  verification.

### 5.5 Application-level brute-force counter (LOW priority)

nginx rate limiting (5 req/min on `/api/v1/auth/`) is the primary control.
For defence-in-depth at the application layer, consider tracking failed login
attempts per username in Redis and introducing a temporary account lockout
after N consecutive failures (e.g. 10 attempts → 15-minute cooldown).

---

## 6. Residual Risks (accepted with rationale)

| Risk | Rationale |
|------|-----------|
| Worker Docker socket → host root | Accepted for MVP; rootless Docker recommended before production |
| Task stdout/stderr stored in plaintext DB | Accepted; access requires authentication + authorisation; encrypt at rest in production |
| No MFA for admin accounts | Accepted for MVP; recommend TOTP for admin/reviewer roles in production |
