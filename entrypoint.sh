#!/bin/sh

set -eu

python - <<'PY'
import os
import socket
import time

services = [
    (
        os.environ.get("POSTGRES_HOST", "db"),
        int(os.environ.get("POSTGRES_PORT", "5432")),
    ),
    (
        os.environ.get("REDIS_HOST", "redis"),
        int(os.environ.get("REDIS_PORT", "6379")),
    ),
]

for host, port in services:
    for _ in range(60):
        try:
            with socket.create_connection((host, port), timeout=2):
                break
        except OSError:
            time.sleep(1)
    else:
        raise RuntimeError(f"{host}:{port} is unavailable")
PY

exec "$@"