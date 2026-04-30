#!/bin/bash

# create docker network if not exists
NETWORK_NAME=$(grep '^NETWORK_NAME=' .env | cut -d'=' -f2)

if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    docker network create "${NETWORK_NAME}" || true
fi

docker compose --env-file .env -f docker-compose.base.yml -f docker-compose.api.yml up --build -d

source scripts/setup_orion_to_cratedb.sh