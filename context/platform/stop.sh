#!/bin/bash

# create docker network if not exists
NETWORK_NAME=$(grep '^NETWORK_NAME=' .env | cut -d'=' -f2)

# Print a message if the network does not exist
if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    echo "Network ${NETWORK_NAME} does not exist. Maybe the this script cannot down the platform correctly."
fi

docker compose --env-file .env -f docker-compose.base.yml -f docker-compose.api.yml down

echo "Script finished."