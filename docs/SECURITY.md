# CIS Security Design Document

## 1. Multi-Tenant Isolation

**Threat:** One user's script reading or modifying another user's data.

**Mitigations:**
- Every `Script` and `Task` carries a `submitted_by`/`user_id` FK. API endpoints check ownership before returning or mutating records.
- Each task runs in a separate, ephemeral Docker container destroyed after execution — no shared state between executions.
- `network_mode=none` prevents containers from communicating with each other.

---

## 2. Command Injection Prevention

**Threat:** Malicious script content escaping the intended execution scope.

**Mitigations:**
- `ScriptValidator` performs static analysis before a script is persisted: forbidden Ansible modules (`shell`, `raw`, `command`, `script`, `expect`) and dangerous shell patterns (`rm -rf /`, `mkfs`, `dd if=`, `curl|sh`, `eval`) are rejected.
- Script content is base64-encoded before injection into the container environment variable `SCRIPT_CONTENT`, preventing shell metacharacter escape at the invocation boundary.
- A human reviewer must approve every script before it can be executed.

---

## 3. Privilege Escalation Prevention

**Threat:** Container process gaining root or elevated privileges.

**Mitigations:**
- Container runs as `uid=1000:1000` (non-root).
- `--security-opt=no-new-privileges:true` — setuid/setgid binaries cannot gain extra permissions.
- `--cap-drop=ALL` — all Linux capabilities removed.
- Custom seccomp profile blocks `setuid`, `setgid`, `capset`, and related syscalls.

---

## 4. Container Escape Prevention

**Threat:** Container breaking out to the host filesystem or kernel.

**Mitigations:**
- `--read-only` root filesystem — container cannot write to host-mounted paths.
- `/tmp` is a small `noexec,nosuid` tmpfs — cannot drop and execute binaries.
- Seccomp profile blocks `mount`, `pivot_root`, `chroot`, `unshare`, `setns`, `kexec_*`, `bpf`, `ptrace`, `process_vm_*`.
- `--pids-limit=100` prevents fork bombs.

---

## 5. Execution Timeout

**Threat:** Infinite-loop script consuming resources indefinitely.

**Mitigation:** Container is forcibly killed after `TASK_TIMEOUT=300` seconds. Task status set to `timeout`.

---

## 6. Resource Limits

**Threat:** Resource exhaustion (CPU, memory) impacting host stability.

**Mitigations:**
- `--memory=256m --memswap=256m` — hard memory cap.
- `--cpus=0.5` (`nano_cpus=500000000`) — CPU quota.
- `--pids-limit=100` — process count cap.

---

## 7. Audit Logging

**Threat:** Undetected misuse or attack.

**Mitigation:** Every API operation writes a structured `AuditLog` record: `who`, `what`, `when`, `result`, `ip`, `user_agent`. Logs are append-only in PostgreSQL.

---

## 8. JWT Security

**Threat:** Token theft or replay.

**Mitigations:**
- Access tokens expire in 15 minutes.
- Refresh tokens are single-use (rotated on every `/auth/refresh`): old token immediately blacklisted in Redis.
- Logout blacklists the current access token.
- Token blacklist uses SHA-256 fingerprint stored in Redis with TTL = remaining token lifetime.
- `python-jose >= 3.4.0` used to avoid algorithm confusion vulnerability.

---

## 9. Script Validation

**Threat:** Bypass of safety checks via obfuscated or complex scripts.

**Mitigations:**
- Ansible: YAML parsed with `yaml.safe_load`, all task module names checked against allow/deny lists.
- Shell: regex patterns detect common dangerous constructs.
- Human review is the final gate — static analysis is defence-in-depth only.

---

## 10. Network Isolation

**Threat:** Container exfiltrating data or reaching internal services.

**Mitigations:**
- `network_mode=none` — no network interface in task container.
- Docker Compose `internal: true` network for backend services — not reachable from host.
- Only Nginx exposes ports 80/443 to the internet.
- Docker socket exposed only to the Celery worker, not the API.
