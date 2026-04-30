# CropDataSpace IoT Platform — dev stack control surface.
# Run `make help` for the list of targets.

SHELL := /usr/bin/env bash

ENV_FILE      := platform/.env
COMPOSE_BASE  := platform/compose/docker-compose.base.yml
COMPOSE_API   := platform/compose/docker-compose.api.yml
DC            := docker compose --env-file $(ENV_FILE) -f $(COMPOSE_BASE) -f $(COMPOSE_API)

# Read NETWORK_NAME from .env if present, else default.
NETWORK_NAME ?= $(shell [ -f $(ENV_FILE) ] && grep -E '^NETWORK_NAME=' $(ENV_FILE) | cut -d= -f2)
NETWORK_NAME := $(if $(NETWORK_NAME),$(NETWORK_NAME),iot-net)

.DEFAULT_GOAL := help

.PHONY: help up down logs ps restart bootstrap clean check-env test seed secrets-keycloak logs-keycloak logs-oauth2-proxy mqtt-password

help: ## List targets
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-env:
	@if [ ! -f $(ENV_FILE) ]; then \
	  echo "ERROR: $(ENV_FILE) not found. Run: cp platform/.env.example $(ENV_FILE)"; \
	  exit 1; \
	fi

up: check-env ## Build and start the dev stack in the background
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || docker network create $(NETWORK_NAME)
	@if [ ! -f platform/config/mosquitto/passwd ]; then $(MAKE) mqtt-password; fi
	$(DC) up -d --build

down: check-env ## Stop the dev stack (keep volumes)
	$(DC) down

logs: check-env ## Tail logs of all services
	$(DC) logs -f --tail=100

ps: check-env ## Show service status
	$(DC) ps

restart: down up ## Restart the dev stack

bootstrap: up ## First-run: ensure network, start stack, register Orion->QL subscription
	@bash platform/scripts/setup_orion_subscription.sh

test: check-env ## Run API integration tests against the running stack
	$(DC) exec -T iot-api pytest -v

seed: check-env ## Populate the platform with realistic seed data
	@python3 platform/scripts/add_test_data.py

secrets-keycloak: ## Print commands to generate the oauth2-proxy cookie secret
	@echo "# Generate a 32-byte cookie secret for oauth2-proxy and add to platform/.env:"
	@echo "openssl rand -base64 32 | tr -- '+/' '-_' | tr -d '='"
	@echo "# Then set OAUTH2_PROXY_COOKIE_SECRET=<output> in platform/.env"

logs-keycloak: check-env ## Tail Keycloak logs
	$(DC) logs -f --tail=200 keycloak

logs-oauth2-proxy: check-env ## Tail oauth2-proxy logs
	$(DC) logs -f --tail=200 oauth2-proxy

mqtt-password: check-env ## Generate Mosquitto password file from MQTT_BRIDGE_* in .env
	@set -a; . $(ENV_FILE); set +a; \
	  if [ -z "$$MQTT_BRIDGE_USERNAME" ] || [ -z "$$MQTT_BRIDGE_PASSWORD" ]; then \
	    echo "ERROR: MQTT_BRIDGE_USERNAME / MQTT_BRIDGE_PASSWORD missing from $(ENV_FILE)"; exit 1; \
	  fi; \
	  docker run --rm -v $$PWD/platform/config/mosquitto:/m eclipse-mosquitto:2.0 \
	    sh -c "mosquitto_passwd -b -c /m/passwd $$MQTT_BRIDGE_USERNAME $$MQTT_BRIDGE_PASSWORD && chmod 0644 /m/passwd" && \
	  echo "Wrote platform/config/mosquitto/passwd for user '$$MQTT_BRIDGE_USERNAME'"

clean: check-env ## DESTRUCTIVE: stop stack and drop all volumes (requires CONFIRM=1)
	@if [ "$(CONFIRM)" != "1" ]; then \
	  echo "Refusing to drop volumes. Re-run with: make clean CONFIRM=1"; \
	  exit 1; \
	fi
	$(DC) down -v
