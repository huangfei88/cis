"""Container security configuration injected by the Celery worker into every task container."""


def get_container_security_config() -> dict:
    """Return Docker SDK kwargs that enforce the sandbox security policy.

    SECURITY rationale for each constraint:
    - network_mode=none:  Container cannot make outbound connections or receive traffic.
    - read_only=True:     Root filesystem is immutable; prevents persistence of malicious files.
    - cap_drop=ALL:       Removes all Linux capabilities (NET_ADMIN, SYS_ADMIN, etc.).
    - no-new-privileges:  Prevents setuid/setgid binaries from gaining extra privileges.
    - mem_limit/nano_cpus: Prevents resource exhaustion (DoS) against the host.
    - tmpfs /tmp:         Provides a small writable scratch space; noexec prevents binary drops.
    - pids_limit:         Prevents fork bombs from exhausting the host PID namespace.
    - user 1000:1000:     Non-root execution user.
    """
    return {
        "network_mode": "none",
        "read_only": True,
        "mem_limit": "256m",
        "memswap_limit": "256m",
        "nano_cpus": 500_000_000,           # 0.5 CPU
        "security_opt": ["no-new-privileges:true"],
        "cap_drop": ["ALL"],
        "tmpfs": {"/tmp": "size=64m,noexec,nosuid,nodev"},
        "pids_limit": 100,
        "user": "1000:1000",
    }
