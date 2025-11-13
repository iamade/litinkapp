.PHONY: up debug dev down rebuild logs supabase-start supabase-stop supabase-status supabase-reset all-up all-down help

# ============================================
# Supabase Management Commands
# ============================================

# Start Supabase services only
supabase-start:
	@cd scripts && ./start-supabase.sh

# Stop Supabase services only
supabase-stop:
	@cd scripts && ./stop-supabase.sh

# Check Supabase status
supabase-status:
	@cd supabase && supabase status

# Reset Supabase database (WARNING: Deletes all data!)
supabase-reset:
	@cd scripts && ./reset-local-db.sh

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

# ============================================
# Combined Commands
# ============================================

# Start both Supabase and application services
all-up:
	@echo "Starting Supabase..."
	@make supabase-start
	@echo ""
	@echo "Starting application services..."
	@make dev

# Stop both application and Supabase services
all-down:
	@echo "Stopping application services..."
	@make down
	@echo ""
	@echo "Stopping Supabase..."
	@make supabase-stop

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
	@echo "Supabase Commands:"
	@echo "  make supabase-start    - Start Supabase services only"
	@echo "  make supabase-stop     - Stop Supabase services only"
	@echo "  make supabase-status   - Check Supabase status"
	@echo "  make supabase-reset    - Reset Supabase database (deletes data!)"
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
	@echo "  1. make supabase-start - Start database (once)"
	@echo "  2. make dev            - Start your application"
	@echo "  3. make down           - Stop app when done"
	@echo "  4. make supabase-stop  - Stop database when completely done"
	@echo ""