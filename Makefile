RESET  := \033[0m
BOLD   := \033[1m
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m

DOCKER_COMPOSE := $(shell \
  if docker-compose version >/dev/null 2>&1; then \
    echo "docker-compose"; \
  elif docker compose version >/dev/null 2>&1; then \
    echo "docker compose"; \
  fi)

.DEFAULT_GOAL := help

.PHONY: dev dev42 \
        up down restart build rebuild \
        logs logs-backend logs-frontend logs-nginx logs-vault \
        status health urls diagnose \
        shell-backend shell-frontend \
        migrate \
        clean prune \
        help

dev: ## Full setup and launch (standard environment)
	@printf "$(BLUE)$(BOLD)» Launching Transcendence (standard)...$(RESET)\n"
	@bash setup-docker.sh

dev42: ## Full setup and launch (42 school / rootless Docker)
	@printf "$(BLUE)$(BOLD)» Launching Transcendence (42 school)...$(RESET)\n"
	@bash setup-docker-42.sh

up: ## Start containers (no rebuild)
	@printf "$(GREEN)» Starting containers...$(RESET)\n"
	@$(DOCKER_COMPOSE) up -d

down: ## Stop and remove containers
	@printf "$(YELLOW)» Stopping containers...$(RESET)\n"
	@$(DOCKER_COMPOSE) down --remove-orphans

restart: ## Restart all containers
	@printf "$(YELLOW)» Restarting all containers...$(RESET)\n"
	@$(DOCKER_COMPOSE) restart

build: ## Build images without starting
	@printf "$(BLUE)» Building images...$(RESET)\n"
	@$(DOCKER_COMPOSE) build

rebuild: ## Force rebuild and restart all services
	@printf "$(BLUE)» Rebuilding and restarting all services...$(RESET)\n"
	@$(DOCKER_COMPOSE) up -d --build

logs: ## Tail logs from all services
	@$(DOCKER_COMPOSE) logs -f || true

logs-backend: ## Tail backend logs
	@$(DOCKER_COMPOSE) logs -f backend || true

logs-frontend: ## Tail frontend logs
	@$(DOCKER_COMPOSE) logs -f frontend || true

logs-nginx: ## Tail nginx / WAF logs
	@$(DOCKER_COMPOSE) logs -f nginx || true

logs-vault: ## Tail vault logs
	@$(DOCKER_COMPOSE) logs -f vault || true

status: ## Show container status
	@printf "$(CYAN)$(BOLD)» Container status:$(RESET)\n\n"
	@$(DOCKER_COMPOSE) ps

health: ## Show health state for each service
	@printf "$(CYAN)$(BOLD)» Service health:$(RESET)\n\n"
	@for svc in backend frontend nginx vault; do \
		state=$$($(DOCKER_COMPOSE) ps $$svc 2>/dev/null | grep -oE "healthy|unhealthy|running|exited" | tail -1); \
		if [ "$$state" = "healthy" ]; then \
			printf "  $(GREEN)✓  %-14s healthy$(RESET)\n" "$$svc"; \
		elif [ "$$state" = "running" ]; then \
			printf "  $(YELLOW)~  %-14s running (no healthcheck yet)$(RESET)\n" "$$svc"; \
		elif [ -z "$$state" ]; then \
			printf "  $(RED)✗  %-14s not running$(RESET)\n" "$$svc"; \
		else \
			printf "  $(RED)✗  %-14s $$state$(RESET)\n" "$$svc"; \
		fi; \
	done
	@printf "\n"

urls: ## Print service URLs and test credentials
	@printf "\n$(CYAN)$(BOLD)» Service URLs:$(RESET)\n\n"
	@printf "  $(GREEN)Frontend     $(RESET)http://localhost:4200\n"
	@printf "  $(GREEN)Backend API  $(RESET)http://localhost:8000\n"
	@printf "  $(GREEN)Django Admin $(RESET)http://localhost:8000/admin/\n"
	@printf "  $(GREEN)Nginx HTTPS  $(RESET)https://localhost:8443\n"
	@printf "  $(GREEN)Nginx HTTP   $(RESET)http://localhost:8080\n"
	@printf "  $(GREEN)Vault UI     $(RESET)http://localhost:8200\n"
	@printf "\n  $(BOLD)Test credentials:$(RESET)\n"
	@printf "  admin / admin123  ·  testuser / test123  ·  player1-5 / password123\n\n"

diagnose: ## Run the rootless Docker diagnostic script
	@bash diagnose-docker.sh

shell-backend: ## Open an interactive shell inside the backend container
	@$(DOCKER_COMPOSE) exec backend sh

shell-frontend: ## Open an interactive shell inside the frontend container
	@$(DOCKER_COMPOSE) exec frontend sh

migrate: ## Run Django database migrations
	@printf "$(BLUE)» Running Django migrations...$(RESET)\n"
	@$(DOCKER_COMPOSE) exec -T backend python manage.py migrate

clean: ## Stop containers and delete volumes
	@printf "$(RED)» Removing containers and volumes...$(RESET)\n"
	@$(DOCKER_COMPOSE) down -v --remove-orphans

prune: ## Remove all unused Docker resources (images, containers, networks)
	@printf "$(RED)» Pruning unused Docker resources...$(RESET)\n"
	@docker system prune -f

help: ## Show this help
	@printf "\n$(BOLD)Transcendence — Developer Commands$(RESET)\n\n"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_][a-zA-Z0-9_-]*:.*##/ { printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\n"
