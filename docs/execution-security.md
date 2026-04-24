# Execution Layer — Security Configuration

This document explains how the CIS execution plane prevents container escapes,
limits system calls, and isolates task containers from the host.

---

## Architecture overview

```
Control Plane (FastAPI)
        │  schedule task (Redis/Celery)
        ▼
    Worker (Celery)
        │  docker run --rm ...
        ▼
  Sandbox Container (cis-runner image)
  ├── uid=1000:1000 (non-root)
  ├── network_mode=none
  ├── read_only filesystem + /tmp tmpfs
  ├── capability drop ALL
  ├── seccomp allowlist
  └── AppArmor MAC profile
```

The control plane **never executes scripts**.  It only enqueues a `task_id`.
The worker reads the task from PostgreSQL, spins up an ephemeral container, and
writes results back.  The container is destroyed immediately after completion.

---

## 1. Non-root user

Every container runs as `uid=1000 gid=1000` (`runner` user, no login shell).

* Dockerfile creates the user with `useradd -u 1000 -g runner -s /sbin/nologin -M runner`.
* `docker run --user 1000:1000` is enforced at the API level in `runner.py`; even
  if the image's default `USER` were overridden it would still be forced here.
* The UID is not mapped to any host account, so even if the container filesystem
  is accessible to the host the UID is unprivileged.

---

## 2. CPU and memory limits

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `mem_limit` | 256 MiB | Prevents a single task from consuming all host memory |
| `memswap_limit` | 256 MiB (= `mem_limit`) | Disables swap; prevents slow swap-based exhaustion attacks |
| `nano_cpus` | 500 000 000 (0.5 CPU) | Prevents CPU starvation of other containers / host processes |
| `pids_limit` | 100 | Prevents fork-bomb exhaustion of the host PID namespace |

Values are configurable via `MAX_MEMORY` and `MAX_CPUS` in `.env`.

---

## 3. Execution timeout (two-layer)

A two-layer timeout ensures no runaway container lives forever:

| Layer | Mechanism | Timeout | Exit code |
|-------|-----------|---------|-----------|
| **Inner (soft)** | `timeout $EXEC_TIMEOUT` inside the container's entrypoint | `TASK_TIMEOUT - 20 s` | 124 (POSIX) |
| **Outer (hard)** | `container.wait(timeout=TASK_TIMEOUT)` in the worker; `container.kill()` on exception | `TASK_TIMEOUT` (default 300 s) | −1 |

The inner timeout fires first and lets the process exit cleanly.  If the
container is still running when the outer timeout expires (e.g., a process that
ignores SIGTERM), Docker sends SIGKILL.  Both cases are recorded as
`TaskStatus.timeout` in the database (exit code 124 is explicitly recognised).

---

## 4. Log collection

Stdout and stderr are collected via `container.logs()` after the container exits,
capped at 10 MiB each to prevent log-flooding attacks.  Logs are stored in
PostgreSQL (`tasks.stdout` / `tasks.stderr`) and are only accessible to the task
owner or an admin via the authenticated API.

---

## 5. Preventing container escapes

Container escapes exploit one or more of: privileged capabilities, exposed
kernel surfaces, writable host paths, or weak namespace isolation.  CIS removes
every known vector:

### 5.1 Capability drop

```
--cap-drop ALL
```

All 40+ Linux capabilities are removed.  Without `CAP_SYS_ADMIN` a process
cannot: mount filesystems, change namespaces, load kernel modules, or manipulate
network interfaces.  Without `CAP_NET_RAW` it cannot craft raw packets.

### 5.2 No privileged mode

`privileged: false` is the Docker default; CIS never sets `privileged: true`.
Privileged mode gives the container `CAP_SYS_ADMIN` and full device access —
the primary container-escape primitive.

### 5.3 Read-only root filesystem

```
--read-only
```

The container's root filesystem is mounted read-only.  An attacker cannot
write malicious binaries or modify system files.  The only writable path is
`/tmp` (a tmpfs, see §5.5).

### 5.4 No network access

```
--network none
```

The container has no network interfaces (not even loopback).  This prevents:
- Exfiltration of secrets
- C2 callbacks
- Lateral movement to internal services
- Accessing the Docker daemon API (which would be a full host takeover)

### 5.5 Restricted /tmp (noexec, nosuid, nodev)

```
--tmpfs /tmp:size=64m,noexec,nosuid,nodev
```

| Flag | Effect |
|------|--------|
| `noexec` | Prevents execution of binaries written to /tmp (binary drop attacks) |
| `nosuid` | Ignores setuid/setgid bits on files in /tmp |
| `nodev` | Prevents creation of device files (e.g., `/dev/mem`) that could access host memory |

---

## 6. Limiting system calls (seccomp)

The seccomp profile at `execution/seccomp/profile.json` uses an **allowlist**
strategy: the default action is `SCMP_ACT_ERRNO` (return `EPERM`), and only
~100 syscalls required by Python and Ansible are explicitly permitted.

Key syscalls that are **explicitly blocked**:

| Syscall | Why blocked |
|---------|-------------|
| `mount` / `umount2` | Cannot re-mount host paths or escape via namespace manipulation |
| `unshare` / `setns` | Cannot create new namespaces or join existing ones |
| `pivot_root` / `chroot` | Cannot change the filesystem root (classic escape) |
| `ptrace` | Cannot trace host or sibling processes |
| `bpf` | Cannot load kernel BPF programs (kernel code execution) |
| `kexec_load` | Cannot replace the running kernel |
| `open_by_handle_at` | Cannot open files by inode handle (bypasses path-based checks) |
| `name_to_handle_at` | See above |
| `perf_event_open` | Cannot access hardware performance counters (side-channel attacks) |
| `process_vm_readv/writev` | Cannot read/write another process's memory |
| `add_key` / `keyctl` | Cannot access the kernel keyring |
| `setuid` / `setgid` / `capset` | Cannot re-gain privileges |
| `sethostname` / `setdomainname` / `reboot` | Cannot modify host identity |

The profile is mounted read-only into the worker container at
`/etc/seccomp/profile.json` and passed to each task container via:

```python
security_opt=["seccomp:/etc/seccomp/profile.json"]
```

---

## 7. AppArmor Mandatory Access Control

AppArmor provides a second kernel-enforced MAC layer on top of seccomp.  Where
seccomp restricts **which syscalls** may be made, AppArmor restricts **what
those syscalls may access** (file paths, network families, capabilities).

### 7.1 Profile location

```
execution/apparmor/cis-runner
```

### 7.2 Installing the profile on each Docker host

```bash
sudo cp execution/apparmor/cis-runner /etc/apparmor.d/cis-runner
sudo apparmor_parser -r /etc/apparmor.d/cis-runner
# Verify:
sudo aa-status | grep cis-runner
```

### 7.3 Enabling in CIS

Set in `.env`:

```
APPARMOR_PROFILE=cis-runner
```

The worker will then pass `security_opt: ["apparmor:cis-runner"]` to every
task container.  If `APPARMOR_PROFILE` is empty (the default) AppArmor is not
requested and Docker applies its built-in `docker-default` profile instead.

### 7.4 What the profile enforces

| Rule | Protection |
|------|-----------|
| `deny mount` / `deny umount` / `deny pivot_root` | Container cannot escape via namespace/mount tricks |
| `deny ptrace` | Cannot trace host or sibling processes even if seccomp is bypassed |
| `deny @{PROC}/** w` | Cannot write to `/proc` (e.g., `/proc/sysrq-trigger`) |
| `deny network raw` / `deny network packet` | No raw sockets even if `network_mode` is relaxed |
| Writable paths limited to `/tmp/**` | All other paths are read-only from AppArmor's perspective |
| `deny capability sys_admin` / `sys_ptrace` / `net_admin` | MAC-level capability deny reinforces the capability drop |
| `signal peer=cis-runner` | Signals only within the same profile; cannot signal host PIDs |

---

## 8. Preventing access to the host

The combination of all controls prevents all known host-access vectors:

| Attack vector | Mitigation |
|---------------|-----------|
| Mount host filesystem | `CAP_SYS_ADMIN` dropped + `mount` syscall blocked + AppArmor `deny mount` |
| Docker socket access | No network (`--network none`); socket not bind-mounted into task containers |
| /proc manipulation | AppArmor `deny @{PROC}/** w`; seccomp blocks `open_by_handle_at` |
| Kernel module loading | `CAP_SYS_MODULE` dropped; `init_module` / `delete_module` blocked by seccomp |
| Namespace escape | `unshare` / `setns` blocked by seccomp |
| Fork bomb | `pids_limit=100` |
| Memory exhaustion | `mem_limit=256m`, `memswap_limit=256m` |
| CPU starvation | `nano_cpus` capped at 0.5 |
| Binary drop & execute | `/tmp` mounted `noexec`; root fs `read-only` |
| Device file creation | `/tmp` mounted `nodev` |
| Privilege re-gain | `no-new-privileges`, `setuid`/`setgid` blocked by seccomp |
| Host process tracing | `ptrace` blocked by seccomp + AppArmor |
| Raw socket attacks | No network; `CAP_NET_RAW` dropped; AppArmor `deny network raw` |

---

## 9. Defence-in-depth summary

```
┌─────────────────────────────────────────────────────────┐
│  Docker daemon                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Task container                                   │  │
│  │                                                   │  │
│  │  uid=1000:1000  (non-root, no login shell)        │  │
│  │  ──────────────────────────────────────────────   │  │
│  │  Capability drop ALL                               │  │
│  │  ──────────────────────────────────────────────   │  │
│  │  seccomp allowlist (~100 syscalls, deny rest)      │  │
│  │  ──────────────────────────────────────────────   │  │
│  │  AppArmor cis-runner (file/net/cap MAC)           │  │
│  │  ──────────────────────────────────────────────   │  │
│  │  network=none  read-only FS  /tmp noexec/nodev    │  │
│  │  mem 256 MiB   CPU 0.5     pids 100              │  │
│  │  timeout 280 s (soft)  +  300 s Docker kill       │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

Any single layer bypass still leaves five further layers of defence.
