COMPOSE = docker compose -f docker-compose.yml
ARGS = $(filter-out $@,$(MAKECMDGOALS))

help:
	@echo "run               -- Run telegram bot"
	@echo "test              -- Run tests"
	@echo "shell             -- Open shell inside the container"
	@echo "check-imports     -- Check imports with isort"
	@echo "check-style       -- Check code-style"
	@echo "build             -- Rebuild the docker container"

run:
	$(COMPOSE) run --rm elram elram run-bot

shell:
	$(COMPOSE) run --rm elram /bin/bash

test:
	$(COMPOSE) run --rm elram pytest $(ARGS)

check-imports:
	$(COMPOSE) run --rm elram isort **/*.py

check-style:
	$(COMPOSE) run --rm elram black **/*.py

build:
	$(COMPOSE) build

stop:
	$(COMPOSE) down --remove-orphans

.PHONY: help run shell test check-imports check-style build stop
