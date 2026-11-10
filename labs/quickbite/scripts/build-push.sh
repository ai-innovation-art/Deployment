#!/usr/bin/env bash
# Builds every QuickBite image and (optionally) pushes it to Docker Hub.
#   ./scripts/build-push.sh          -> build only
#   ./scripts/build-push.sh --push   -> build + push (run `docker login` first)
# You only need this ONCE. Afterwards every cluster pulls from Docker Hub.
set -euo pipefail
cd "$(dirname "$0")/.."

REG=${REGISTRY:-kumawatsunil}
PUSH=${1:-}

build() {  # build <image-name> <context> [extra docker args...]
  local img=$1 ctx=$2; shift 2
  echo ">> $REG/$img"
  docker build -q -t "$REG/$img" "$@" "$ctx" >/dev/null
  [ "$PUSH" = "--push" ] && docker push -q "$REG/$img"
  return 0
}

build quickbite-web:1.0          services/web
build quickbite-orders-api:1.0   services/orders-api   --build-arg APP_VERSION=1.0
build quickbite-notifier:1.0     services/notifier
build quickbite-daily-report:1.0 services/daily-report

# menu-api has three versions: these drive the rollout / rollback chapter
build quickbite-menu-api:1.0        services/menu-api --build-arg APP_VERSION=1.0
build quickbite-menu-api:1.1        services/menu-api --build-arg APP_VERSION=1.1
build quickbite-menu-api:1.2-broken services/menu-api --build-arg APP_VERSION=1.2-broken --build-arg BROKEN=true

echo
docker images "$REG/quickbite-*" --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'
[ "$PUSH" = "--push" ] && echo "pushed to https://hub.docker.com/u/$REG" || echo "built locally (add --push to publish)"
