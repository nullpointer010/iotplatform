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

.PHONY: help up down logs ps restart bootstrap clean check-env test seed

help: ## List targets
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check-env:
	@if [ ! -f $(ENV_FILE) ]; then \
	  echo "ERROR: $(ENV_FILE) not found. Run: cp platform/.env.example $(ENV_FILE)"; \
	  exit 1; \
	fi

up: check-env ## Build and start the dev stack in the background
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || docker network create $(NETWORK_NAME)
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

clean: check-env ## DESTRUCTIVE: stop stack and drop all volumes (requires CONFIRM=1)
	@if [ "$(CONFIRM)" != "1" ]; then \
	  echo "Refusing to drop volumes. Re-run with: make clean CONFIRM=1"; \
	  exit 1; \
	fi
	$(DC) down -v
