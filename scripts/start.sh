#!/usr/bin/env sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

BUILD_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --build|-b) BUILD_FLAG="--build" ;;
  esac
done

ENV_ARGS=""
if [ -f ".env" ]; then
  ENV_ARGS="--env-file .env"
fi

if [ -z "${NAPCAT_UID:-}" ]; then
  export NAPCAT_UID="$(id -u 2>/dev/null || echo 1000)"
fi

if [ -z "${NAPCAT_GID:-}" ]; then
  export NAPCAT_GID="$(id -g 2>/dev/null || echo 1000)"
fi

docker compose $ENV_ARGS up -d $BUILD_FLAG

printf "\nAstrBot WebUI: http://localhost:6185\n"
printf "NapCat WebUI:  http://localhost:6099/webui\n"
printf "Logs:\n"
printf "  docker compose logs -f astrbot\n"
printf "  docker compose logs -f napcat\n"
