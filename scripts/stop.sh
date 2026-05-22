#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

ENV_ARGS=""
if [ -f ".env" ]; then
  ENV_ARGS="--env-file .env"
fi

docker compose $ENV_ARGS down
