#!/bin/bash
# Entrypoint for sandboxed execution container.
# Receives SCRIPT_TYPE (ansible|shell) and SCRIPT_CONTENT (base64-encoded).
# SECURITY: runs as uid=1000, no network, read-only fs except /tmp.

set -euo pipefail

WORK_DIR="/tmp/runner_$$"
mkdir -p "$WORK_DIR"

if [ -z "${SCRIPT_CONTENT:-}" ]; then
    echo "ERROR: SCRIPT_CONTENT is not set" >&2
    exit 1
fi

if [ "${SCRIPT_TYPE:-}" = "ansible" ]; then
    echo "$SCRIPT_CONTENT" | base64 -d > "$WORK_DIR/playbook.yml"
    ansible-playbook \
        -i "localhost," \
        -c local \
        --timeout 280 \
        "$WORK_DIR/playbook.yml"
elif [ "${SCRIPT_TYPE:-}" = "shell" ]; then
    echo "$SCRIPT_CONTENT" | base64 -d > "$WORK_DIR/script.sh"
    chmod +x "$WORK_DIR/script.sh"
    bash "$WORK_DIR/script.sh"
else
    echo "ERROR: Unknown SCRIPT_TYPE: '${SCRIPT_TYPE:-}'" >&2
    exit 1
fi
