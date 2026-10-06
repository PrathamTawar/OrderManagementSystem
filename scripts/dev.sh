#!/bin/sh
set -eu

export DOCKER_UID="$(id -u)"
export DOCKER_GID="$(id -g)"

exec docker compose -f compose.dev.yaml "$@"