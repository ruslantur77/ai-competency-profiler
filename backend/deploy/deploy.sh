#!/bin/sh
set -eEuo pipefail
cd "$(dirname "$0")"
set -x

PROJECT_NAME="competency_system"
TIMEOUT=120
INTERVAL=5
DEPLOY_LOG="deploy.log"

: > "$DEPLOY_LOG"

NEW_TAG=$1
if [ -z "$NEW_TAG" ]; then
    echo "Usage: $0 <image_tag>"
    exit 1
fi

# current slot

ACTIVE=$(cat ./nginx/active 2>/dev/null || echo "blue" > ./nginx/active && cat ./nginx/active)

if [ "$ACTIVE" = "blue" ]; then
    STANDBY="green"
    STANDBY_API_PORT=1001
    STANDBY_AIRFLOW_PORT=2001
else
    STANDBY="blue"
    STANDBY_API_PORT=1000
    STANDBY_AIRFLOW_PORT=2000
fi

echo "Active slot  : $ACTIVE"
echo "Standby slot : $STANDBY"
echo "New tag      : $NEW_TAG"

STANDBY_DIR="./$STANDBY"

# update tag

touch "$STANDBY_DIR/tag"
grep -q '^IMAGE_TAG=' "$STANDBY_DIR/tag" \
  && sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$NEW_TAG/" "$STANDBY_DIR/tag" \
  || echo "IMAGE_TAG=$NEW_TAG" >> "$STANDBY_DIR/tag"

# starting standby

echo "Starting standby slot ($STANDBY)..."
IMAGE_TAG="$NEW_TAG" ENV_FILE=$(realpath ../.env) docker compose -p "${PROJECT_NAME}_${STANDBY}" -f "$STANDBY_DIR/docker-compose.yml" --env-file $(realpath ../.env)\
    up -d --pull always --force-recreate --quiet-pull 2>&1 | tee -a "$DEPLOY_LOG"

# healthcheck standby

echo "Waiting for $STANDBY to be healthy (timeout: ${TIMEOUT}s)..."
elapsed=0
HEALTHY=0

while [ $elapsed -lt $TIMEOUT ]; do
    ALL_OK=1

    for c in $(docker compose ps -q); do
        status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $c)

        if [ "$status" != "healthy" ] && [ "$status" != "running" ]; then
            echo "  container $c not ready: $status"
            ALL_OK=0
        fi
    done

    if [ $ALL_OK -eq 1 ]; then
        echo "All containers are ready"
        HEALTHY=1
        break
    fi

    echo "  ${elapsed}s — waiting for containers..."
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

# rollback

if [ $HEALTHY -ne 1 ]; then
    echo "Standby unhealthy — rolling back" | tee -a "$DEPLOY_LOG"
    docker compose -p "${PROJECT_NAME}_${STANDBY}" -f "$STANDBY_DIR/docker-compose.yml" \
        down 2>&1 | tee -a "$DEPLOY_LOG" || true
    exit 1
fi

# nginx switch

echo "Switching nginx to $STANDBY..."

cat > "./nginx/upstream.conf" <<EOF
upstream app_active {
    server 127.0.0.1:${STANDBY_API_PORT};
}
upstream airflow_active {
    server 127.0.0.1:${STANDBY_AIRFLOW_PORT};
}
EOF

docker compose -f ./shared/docker-compose.yml exec nginx nginx -t 2>&1 | tee -a "$DEPLOY_LOG"
docker compose -f ./shared/docker-compose.yml exec nginx nginx -s reload 2>&1 | tee -a "$DEPLOY_LOG"

echo "$STANDBY" > "./nginx/active"
echo "Traffic switched to $STANDBY"

# stopping old
OLD_TAG=$(
  [ -f "./$ACTIVE/tag" ] && \
  grep '^IMAGE_TAG=' "./$ACTIVE/tag" 2>/dev/null | cut -d= -f2
)

echo "Draining old slot ($ACTIVE) for 15s..."
sleep 15

IMAGE_TAG="$OLD_TAG" ENV_FILE=$(realpath ../.env) docker compose -p "${PROJECT_NAME}_${ACTIVE}" -f "./$ACTIVE/docker-compose.yml" --env-file $(realpath ../.env)\
    down 2>&1 | tee -a "$DEPLOY_LOG" || true

echo "Stopped old slot: $ACTIVE"

# remove old images


if [ -n "$OLD_TAG" ] && [ "$OLD_TAG" != "$NEW_TAG" ]; then
    docker rmi "ghcr.io/ruslantur77/api:${OLD_TAG}" 2>&1 | tee -a "$DEPLOY_LOG" || true
    docker rmi "ghcr.io/ruslantur77/worker:${OLD_TAG}" 2>&1 | tee -a "$DEPLOY_LOG" || true
    docker rmi "ghcr.io/ruslantur77/airflow:${OLD_TAG}" 2>&1 | tee -a "$DEPLOY_LOG" || true
fi

echo "Deploy complete. Active slot: $STANDBY"
exit 0