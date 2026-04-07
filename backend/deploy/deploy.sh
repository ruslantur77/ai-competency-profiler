#!/bin/sh
set -eEuo pipefail
cd "$(dirname "$0")"
set -x

PROJECT_NAME="competency_system"
TIMEOUT=120
INTERVAL=5
DEPLOY_LOG="deploy.log"

ENV_FILE="$(realpath ../.env)"
DOCKER_SOCKET="/var/run/docker.sock"

: > "$DEPLOY_LOG"

# --- args ---
NEW_TAG="${1:-}"
if [ -z "$NEW_TAG" ]; then
    echo "Usage: $0 <image_tag>"
    exit 1
fi

# --- helpers ---
wait_for_stack() {
    stack_project="$1"
    stack_compose="$2"
    stack_env="$3"
    stack_tag="${4:-placeholder}"
    label="$5"

    echo "Waiting for $label to be healthy (timeout: ${TIMEOUT}s)..."
    elapsed=0

    while [ "$elapsed" -lt "$TIMEOUT" ]; do
        ALL_OK=1

        for c in $(
            IMAGE_TAG="$stack_tag" \
            ENV_FILE="$stack_env" \
            DOCKER_SOCKET="$DOCKER_SOCKET" \
            docker compose \
                -p "$stack_project" \
                -f "$stack_compose" \
                --env-file "$stack_env" \
                ps -q
        ); do
            name=$(docker inspect --format='{{.Name}}' "$c" | tr -d '/')
            health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c")
            state=$(docker inspect --format='{{.State.Status}}' "$c")

            case "$name" in
                *migrate*|*airflow-init*)
                    exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$c")
                    if [ "$state" != "exited" ] || [ "$exit_code" != "0" ]; then
                        echo "  $name not done: state=$state exit_code=$exit_code"
                        ALL_OK=0
                    fi
                    ;;
                *)
                    if [ "$health" = "none" ]; then
                        if [ "$state" != "running" ]; then
                            echo "  $name not ready: state=$state"
                            ALL_OK=0
                        fi
                    else
                        if [ "$health" != "healthy" ]; then
                            echo "  $name not ready: health=$health"
                            ALL_OK=0
                        fi
                    fi
                    ;;
            esac
        done

        if [ "$ALL_OK" -eq 1 ]; then
            echo "All containers in $label are ready"
            return 0
        fi

        echo "  ${elapsed}s — waiting for $label..."
        sleep "$INTERVAL"
        elapsed=$((elapsed + INTERVAL))
    done

    echo "$label did not become healthy in time" | tee -a "$DEPLOY_LOG"
    return 1
}

# --- shared stack ---
echo "Starting shared stack..."
IMAGE_TAG="placeholder" \
ENV_FILE="$ENV_FILE" \
DOCKER_SOCKET="$DOCKER_SOCKET" \
docker compose \
    -p "${PROJECT_NAME}_shared" \
    -f ./shared/docker-compose.yml \
    --env-file "$ENV_FILE" \
    up -d --quiet-pull \
    2>&1 | tee -a "$DEPLOY_LOG"

wait_for_stack \
    "${PROJECT_NAME}_shared" \
    "./shared/docker-compose.yml" \
    "$ENV_FILE" \
    "placeholder" \
    "shared" || {
        echo "Shared stack failed — aborting" | tee -a "$DEPLOY_LOG"
        exit 1
    }

# --- slots ---
ACTIVE_FILE="./nginx/active"
if [ ! -f "$ACTIVE_FILE" ]; then
    echo "blue" > "$ACTIVE_FILE"
fi
ACTIVE=$(cat "$ACTIVE_FILE")

if [ "$ACTIVE" = "blue" ]; then
    STANDBY="green"
else
    STANDBY="blue"
fi

echo "Active slot  : $ACTIVE"
echo "Standby slot : $STANDBY"
echo "New tag      : $NEW_TAG"

# --- update image tag for standby ---
TAG_FILE="./$STANDBY/tag"
touch "$TAG_FILE"
if grep -q '^IMAGE_TAG=' "$TAG_FILE"; then
    sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=$NEW_TAG/" "$TAG_FILE"
else
    echo "IMAGE_TAG=$NEW_TAG" >> "$TAG_FILE"
fi

# --- start standby ---
echo "Starting standby slot ($STANDBY)..."
IMAGE_TAG="$NEW_TAG" \
ENV_FILE="$ENV_FILE" \
DOCKER_SOCKET="$DOCKER_SOCKET" \
docker compose \
    -p "${PROJECT_NAME}_${STANDBY}" \
    -f "./$STANDBY/docker-compose.yml" \
    --env-file "$ENV_FILE" \
    up -d --pull always --force-recreate --quiet-pull \
    2>&1 | tee -a "$DEPLOY_LOG"

# --- wait for standby healthy ---
wait_for_stack \
    "${PROJECT_NAME}_${STANDBY}" \
    "./$STANDBY/docker-compose.yml" \
    "$ENV_FILE" \
    "$NEW_TAG" \
    "$STANDBY" || {
        echo "Standby unhealthy — rolling back" | tee -a "$DEPLOY_LOG"
        IMAGE_TAG="$NEW_TAG" \
        ENV_FILE="$ENV_FILE" \
        DOCKER_SOCKET="$DOCKER_SOCKET" \
        docker compose \
            -p "${PROJECT_NAME}_${STANDBY}" \
            -f "./$STANDBY/docker-compose.yml" \
            down 2>&1 | tee -a "$DEPLOY_LOG" || true
        exit 1
    }

# --- switch nginx to standby ---
echo "Switching nginx to $STANDBY..."
NGINX_CONF="./nginx/nginx.conf"

sed -i "s/${ACTIVE}_api/${STANDBY}_api/g" "$NGINX_CONF"
sed -i "s/${ACTIVE}_airflow-webserver/${STANDBY}_airflow-webserver/g" "$NGINX_CONF"

docker compose \
    -p "${PROJECT_NAME}_shared" \
    -f ./shared/docker-compose.yml \
    --env-file "$ENV_FILE" \
    exec nginx nginx -t \
    2>&1 | tee -a "$DEPLOY_LOG"

docker compose \
    -p "${PROJECT_NAME}_shared" \
    -f ./shared/docker-compose.yml \
    --env-file "$ENV_FILE" \
    exec nginx nginx -s reload \
    2>&1 | tee -a "$DEPLOY_LOG"

echo "$STANDBY" > "$ACTIVE_FILE"
echo "Traffic switched to $STANDBY"

# --- drain and stop old slot ---
OLD_TAG=""
if [ -f "./$ACTIVE/tag" ]; then
    OLD_TAG=$(grep '^IMAGE_TAG=' "./$ACTIVE/tag" 2>/dev/null | cut -d= -f2 || true)
fi

echo "Draining old slot ($ACTIVE) for 15s..."
sleep 15

IMAGE_TAG="${OLD_TAG:-placeholder}" \
ENV_FILE="$ENV_FILE" \
DOCKER_SOCKET="$DOCKER_SOCKET" \
docker compose \
    -p "${PROJECT_NAME}_${ACTIVE}" \
    -f "./$ACTIVE/docker-compose.yml" \
    --env-file "$ENV_FILE" \
    down 2>&1 | tee -a "$DEPLOY_LOG" || true

echo "Stopped old slot: $ACTIVE"

# --- remove old images ---
if [ -n "$OLD_TAG" ] && [ "$OLD_TAG" != "$NEW_TAG" ]; then
    for img in api worker airflow; do
        docker rmi "ghcr.io/ruslantur77/${img}:${OLD_TAG}" \
            2>&1 | tee -a "$DEPLOY_LOG" || true
    done
fi

echo "Deploy complete. Active slot: $STANDBY"
exit 0