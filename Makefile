.PHONY: help tunnel-dev tunnel-staging start-vps-dev start-vps-staging start-dev start-staging vps-dev vps-staging dev staging frontend logs logs-api logs-worker ps ps-backend stop-backend down docker-down down-backend restart-dev restart-staging recreate-backend migrate current-migration history

help:
	@echo "LitInkAI local/VPS tunnel commands"
	@echo "==================================="
	@echo ""
	@echo "Tunnel commands (keep terminal open):"
	@echo "  make tunnel-dev       - Open SSH tunnel to VPS dev services"
	@echo "  make tunnel-staging   - Open SSH tunnel to VPS staging services"
	@echo ""
	@echo "VPS tunnel start commands (run in second terminal):"
	@echo "  make start-vps-dev     - Start local backend against VPS dev tunnel"
	@echo "  make start-vps-staging - Start local backend against VPS staging tunnel"
	@echo "  make vps-dev          - Alias for start-vps-dev"
	@echo "  make vps-staging      - Alias for start-vps-staging"
	@echo ""
	@echo "Normal local commands:"
	@echo "  make dev              - Run the existing backend Makefile dev target"
	@echo "  make staging          - Not mapped to VPS tunnel; use make vps-staging explicitly"
	@echo "  make frontend         - Start local Vite frontend on localhost:5173"
	@echo ""
	@echo "Backend Docker helpers:"
	@echo "  make logs             - Follow all backend service logs"
	@echo "  make logs-api         - Follow API logs"
	@echo "  make logs-worker      - Follow Celery worker logs"
	@echo "  make ps               - Show backend compose services"
	@echo "  make stop-backend     - Stop backend containers without deleting volumes"
	@echo "  make down             - Docker compose down without deleting volumes"
	@echo "  make docker-down      - Alias for down"
	@echo "  make recreate-backend - Rebuild/recreate API + Celery services only"
	@echo ""
	@echo "Alembic helpers:"
	@echo "  make migrate          - Run alembic upgrade head inside API container"
	@echo "  make current-migration - Show current Alembic revision"
	@echo "  make history          - Show Alembic history"
	@echo ""
	@echo "Recommended VPS tunnel dev flow:"
	@echo "  Terminal 1: make tunnel-dev"
	@echo "  Terminal 2: make start-vps-dev"
	@echo "  For staging: make tunnel-staging, then make start-vps-staging"
	@echo "  Terminal 3: make frontend"

# Tunnel commands intentionally block while active. Leave the terminal open.
tunnel-dev:
	bash scripts/tunnel-dev.sh

tunnel-staging:
	bash scripts/tunnel-staging.sh

start-vps-dev:
	bash scripts/start-vps-dev.sh

start-vps-staging:
	bash scripts/start-vps-staging.sh

# Backward-compatible explicit names. Prefer vps-dev/vps-staging for tunnel mode.
start-dev: start-vps-dev

start-staging: start-vps-staging

vps-dev: start-vps-dev

vps-staging: start-vps-staging

# Preserve the pre-existing local backend Makefile flow; do not overwrite local env with VPS tunnel env.
dev:
	cd backend && $(MAKE) dev

staging:
	@echo "Use 'make vps-staging' for VPS tunnel staging. No default staging alias is provided to avoid accidental env overwrite."
	@exit 1

frontend:
	cd frontend && npm run dev

restart-dev: start-dev

restart-staging: start-staging

logs:
	cd backend && docker compose -f local.yml logs -f

logs-api:
	cd backend && docker compose -f local.yml logs -f api

logs-worker:
	cd backend && docker compose -f local.yml logs -f celeryworker

ps:
	cd backend && docker compose -f local.yml ps

ps-backend: ps

stop-backend:
	cd backend && docker compose -f local.yml stop api celeryworker celerybeat

# Safe down: removes containers/networks, but does not delete volumes. Never uses -v.
down:
	cd backend && docker compose -f local.yml down

docker-down: down

down-backend: down

# Safe recreate: does not run down -v and does not delete database/Redis/MinIO volumes.
recreate-backend:
	cd backend && docker compose -f local.yml up --build -d --force-recreate api celeryworker celerybeat

migrate:
	cd backend && docker compose -f local.yml exec api alembic upgrade head

current-migration:
	cd backend && docker compose -f local.yml exec api alembic current

history:
	cd backend && docker compose -f local.yml exec api alembic history
