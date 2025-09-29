.PHONY: up debug dev stop rebuild logs

# Run in development mode WITHOUT debugger
dev:
	DEBUG=false ENVIRONMENT=development docker-compose up

# Run in production mode
up:
    DEBUG=false ENVIRONMENT=production docker-compose up

# Run in development mode WITH debugger
debug:
    DEBUG=true ENVIRONMENT=development docker-compose up

# Stop containers
stop:
	docker-compose down

# Rebuild development without debugger
rebuild-dev:
	DEBUG=false ENVIRONMENT=development docker-compose up --build

# Rebuild production
rebuild:
    DEBUG=false ENVIRONMENT=production docker-compose up --build

# Rebuild development with debugger
rebuild-debug:
    DEBUG=true ENVIRONMENT=development docker-compose up --build

# Show logs
logs:
	docker-compose logs -f api