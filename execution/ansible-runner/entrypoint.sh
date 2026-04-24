#!/bin/bash
# Entrypoint for sandboxed execution container.
# Receives SCRIPT_TYPE (ansible|shell), SCRIPT_CONTENT (base64-encoded), and
# EXEC_TIMEOUT (seconds, default 280).
# SECURITY: runs as uid=1000, no network, read-only fs except /tmp.

set -euo pipefail

WORK_DIR="/tmp/runner_$$"
mkdir -p "$WORK_DIR"

# Soft timeout — must be shorter than the Docker-level hard-kill timeout so
# the process has a chance to exit cleanly.  Exit code 124 is returned by
# `timeout` when it sends SIGTERM and the child does not exit in time.
EXEC_TIMEOUT="${EXEC_TIMEOUT:-280}"

if [ -z "${SCRIPT_CONTENT:-}" ]; then
    echo "ERROR: SCRIPT_CONTENT is not set" >&2
    exit 1
fi

if [ "${SCRIPT_TYPE:-}" = "ansible" ]; then
    echo "$SCRIPT_CONTENT" | base64 -d > "$WORK_DIR/playbook.yml"
    # --timeout is ansible-playbook's per-host SSH timeout; keep it 10 s less
    # than EXEC_TIMEOUT so the outer `timeout` always fires last.
    exec timeout "$EXEC_TIMEOUT" ansible-playbook \
        -i "localhost," \
        -c local \
        --timeout $((EXEC_TIMEOUT - 10)) \
        "$WORK_DIR/playbook.yml"
elif [ "${SCRIPT_TYPE:-}" = "shell" ]; then
    echo "$SCRIPT_CONTENT" | base64 -d > "$WORK_DIR/script.sh"
    chmod +x "$WORK_DIR/script.sh"
    exec timeout "$EXEC_TIMEOUT" bash "$WORK_DIR/script.sh"
else
    echo "ERROR: Unknown SCRIPT_TYPE: '${SCRIPT_TYPE:-}'" >&2
    exit 1
fi
