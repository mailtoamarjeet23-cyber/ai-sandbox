#!/bin/bash
set -e

# Runs as root only long enough to fix the /output bind-mount ownership,
# then drops to UID 1000 (agent) for all actual work.
# read_only:true in Compose makes the overlay FS read-only; bind mounts and
# tmpfs are still writable so /output and /tmp remain accessible.

mkdir -p /output
chown agent:users /output

echo "[agent-runner] dropping privileges → UID=$(id -u agent) (agent)"
exec su-exec agent python -u /app/agent.py
