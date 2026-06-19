#!/bin/bash
set -e

# Runs as root only long enough to fix the /output bind-mount ownership,
# then exec's Python which drops to UID 1000 via os.setuid() at startup.
mkdir -p /output
chown 1000:100 /output    # agent:users

echo "[agent-runner] handing off to agent.py (will drop to UID 1000)"
exec python -u /app/agent.py
