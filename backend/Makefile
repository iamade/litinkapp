.PHONY: up debug dev stop rebuild logs

# Run in development mode WITHOUT debugger
dev:
	DEBUG=false ENVIRONMENT=development docker compose -f local.yml up --build -d

# Run in production mode
up:
    DEBUG=false ENVIRONMENT=production docker compose -f local.yml up --build -d

# Run in development mode WITH debugger
debug:
	DEBUG=true ENVIRONMENT=development docker compose -f local.yml up --build -d

# Stop containers
down:
	docker compose -f local.yml down

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
	docker-compose logs -f api

litinkai-config:
	docker compose -f local.yml config

inspect-network:
	docker network inspect litinkai_local_nw