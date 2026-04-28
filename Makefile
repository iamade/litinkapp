.PHONY: help tunnel-staging tunnel-dev vps-staging vps-dev start-vps-staging start-vps-dev frontend down stop logs

help:
	@echo "LitInkAI staging helper targets"
	@echo "  make tunnel-staging   - Open SSH tunnel to VPS staging Postgres/Redis/MinIO"
	@echo "  make tunnel-dev       - Open SSH tunnel to VPS dev Postgres/Redis/MinIO"
	@echo "  make vps-staging      - Start local backend against VPS staging tunnel"
	@echo "  make vps-dev          - Start local backend against VPS dev tunnel"
	@echo "  make frontend         - Start frontend dev server"
	@echo "  make down             - Stop local Docker services for tunnel mode"
	@echo "  make logs             - Follow backend API logs"

tunnel-staging:
	bash scripts/tunnel-staging.sh

tunnel-dev:
	bash scripts/tunnel-dev.sh

vps-staging: start-vps-staging

vps-dev: start-vps-dev

start-vps-staging:
	bash scripts/start-staging.sh

start-vps-dev:
	bash scripts/start-dev.sh

frontend:
	cd frontend && npm run dev

down: stop

stop:
	cd backend && docker compose -f local.yml down

logs:
	cd backend && docker compose -f local.yml logs -f api
