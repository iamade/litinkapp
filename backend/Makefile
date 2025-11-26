
# ============================================
# Application Service Commands
# ============================================

# Run in development mode WITHOUT debugger
dev:
	DEBUG=false ENVIRONMENT=development docker compose -f local.yml up --build -d
# 	@cd scripts && ./start-local-dev.sh

# Run in production mode
up:
	DEBUG=false ENVIRONMENT=production docker compose -f local.yml up --build -d

# Run in development mode WITH debugger
debug:
	DEBUG=true ENVIRONMENT=development docker compose -f local.yml up --build -d

# Stop application containers only
down:
	docker-compose -f local.yml down
# 	@cd scripts && ./stop-local-dev.sh

# Rebuild development without debugger
rebuild-dev:
	DEBUG=false ENVIRONMENT=development docker compose -f local.yml up --build -d --remove-orphans

# Rebuild production
rebuild:
	DEBUG=false ENVIRONMENT=production docker compose -f local.yml up --build -d --remove-orphans

# Rebuild development with debugger
rebuild-debug:
	DEBUG=true ENVIRONMENT=development docker compose -f local.yml up --build -d --remove-orphans

# Show logs
logs:
	docker-compose -f local.yml logs -f api

# Show all service logs
logs-all:
	docker-compose -f local.yml logs -f

# Show Postgres db
psql:
	docker-compose -f local.yml exec postgres psql -U adesegun -d litinkai

makemigrations:
	docker compose -f local.yml  exec -it api alembic revision --autogenerate -m "$(name)"

migrate:
	docker compose -f local.yml exec -it api alembic upgrade head

history:
	docker compose -f local.yml exec -it api alembic history

current-migration:
	docker compose -f local.yml exec -it api alembic current

downgrade:
	docker compose -f local.yml exec -it api alembic downgrade $(version)



# ============================================
# Utility Commands
# ============================================

# Show Docker Compose configuration
config:
	docker compose -f local.yml config

# Inspect Docker network
inspect-network:
	docker network inspect litinkai_local_nw

# Create Docker network if it doesn't exist
create-network:
	docker network create litinkai_local_nw || true

# Help command
help:
	@echo "Litinkai Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Application Commands:"
	@echo "  make dev               - Start app in development mode (requires Supabase running)"
	@echo "  make up                - Start app in production mode"
	@echo "  make debug             - Start app with debugger enabled"
	@echo "  make down              - Stop application services"
	@echo "  make rebuild-dev       - Rebuild and start app in dev mode"
	@echo "  make logs              - Show API logs"
	@echo "  make logs-all          - Show all service logs"
	@echo ""
	@echo "Combined Commands:"
	@echo "  make all-up            - Start both Supabase and app services"
	@echo "  make all-down          - Stop both app and Supabase services"
	@echo ""
	@echo "Recommended Workflow:"
	@echo "  2. make dev            - Start your application"
	@echo "  3. make down           - Stop app when done"
	@echo ""