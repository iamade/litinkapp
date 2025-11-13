#!/bin/bash

# ============================================
# View Local Development Logs
# ============================================
# This script helps you view logs from different services

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Litinkai Local Development Logs${NC}"
echo ""
echo "Select which logs to view:"
echo ""
echo "1) All application services"
echo "2) API service only"
echo "3) Celery worker"
echo "4) Celery beat"
echo "5) Flower"
echo "6) Redis"
echo "7) RabbitMQ"
echo "8) Mailpit"
echo "9) Supabase logs"
echo ""

read -p "Enter your choice (1-9): " choice
echo ""

case $choice in
    1)
        echo -e "${GREEN}Viewing all application service logs...${NC}"
        docker-compose -f local.yml logs -f
        ;;
    2)
        echo -e "${GREEN}Viewing API service logs...${NC}"
        docker-compose -f local.yml logs -f api
        ;;
    3)
        echo -e "${GREEN}Viewing Celery worker logs...${NC}"
        docker-compose -f local.yml logs -f celeryworker
        ;;
    4)
        echo -e "${GREEN}Viewing Celery beat logs...${NC}"
        docker-compose -f local.yml logs -f celerybeat
        ;;
    5)
        echo -e "${GREEN}Viewing Flower logs...${NC}"
        docker-compose -f local.yml logs -f flower
        ;;
    6)
        echo -e "${GREEN}Viewing Redis logs...${NC}"
        docker-compose -f local.yml logs -f redis
        ;;
    7)
        echo -e "${GREEN}Viewing RabbitMQ logs...${NC}"
        docker-compose -f local.yml logs -f rabbitmq
        ;;
    8)
        echo -e "${GREEN}Viewing Mailpit logs...${NC}"
        docker-compose -f local.yml logs -f mailpit
        ;;
    9)
        echo -e "${GREEN}Viewing Supabase logs...${NC}"
        echo "Opening Supabase Studio for logs..."
        echo "Visit: http://127.0.0.1:54323"
        echo ""
        echo "Or view Supabase container logs directly:"
        docker logs -f supabase-db 2>/dev/null || echo "Supabase containers use project-specific names"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
