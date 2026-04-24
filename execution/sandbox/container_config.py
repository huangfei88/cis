"""Container security configuration injected by the Celery worker into every task container."""


def get_container_security_config(
    seccomp_profile_path: str = "/etc/seccomp/profile.json",
    apparmor_profile: str = "",
    mem_limit: str = "256m",
    nano_cpus: int = 500_000_000,
) -> dict:
    """Return Docker SDK kwargs that enforce the sandbox security policy.

    SECURITY rationale for each constraint:
    - network_mode=none:      Container cannot make outbound connections or receive traffic.
    - read_only=True:         Root filesystem is immutable; prevents persistence of malicious files.
    - cap_drop=ALL:           Removes all Linux capabilities (NET_ADMIN, SYS_ADMIN, etc.).
    - no-new-privileges:      Prevents setuid/setgid binaries from gaining extra privileges.
    - seccomp profile:        Kernel-level allowlist of ~100 syscalls; all others return EPERM.
                              See ../seccomp/profile.json.  Explicitly blocks mount, unshare,
                              setns, ptrace, bpf, kexec_load, open_by_handle_at, and other
                              container-escape primitives.
    - apparmor profile:       MAC policy (when loaded on host) restricts file-system paths,
                              capabilities, and network operations at the kernel level.
                              See ../apparmor/cis-runner.
    - mem_limit/memswap_limit: Prevents memory exhaustion; swap disabled (memswap == mem_limit).
    - nano_cpus:              Prevents CPU starvation of other containers/host.
    - tmpfs /tmp:             Small writable scratch space; noexec/nosuid/nodev prevent binary
                              drops and device-file creation inside the container.
    - pids_limit:             Prevents fork bombs from exhausting the host PID namespace.
    - user 1000:1000:         Non-root execution user; UID not mapped to any host account.
    """
    security_opt = [
        "no-new-privileges:true",
        f"seccomp:{seccomp_profile_path}",
    ]
    if apparmor_profile:
        security_opt.append(f"apparmor:{apparmor_profile}")

    return {
        "network_mode": "none",
        "read_only": True,
        "mem_limit": mem_limit,
        "memswap_limit": mem_limit,   # swap disabled: memswap_limit == mem_limit
        "nano_cpus": nano_cpus,       # 0.5 CPU with default
        "security_opt": security_opt,
        "cap_drop": ["ALL"],
        "tmpfs": {"/tmp": "size=64m,noexec,nosuid,nodev"},
        "pids_limit": 100,
        "user": "1000:1000",
    }
