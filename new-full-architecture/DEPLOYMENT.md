# Deployment & Infrastructure - LitinkAI Platform

Complete deployment architecture, infrastructure diagrams, and operational procedures for the LitinkAI platform.

---

## Table of Contents

1. [Infrastructure Overview](#infrastructure-overview)
2. [Deployment Architecture](#deployment-architecture)
3. [Container Architecture](#container-architecture)
4. [Environment Configuration](#environment-configuration)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Scaling Strategy](#scaling-strategy)
7. [Monitoring & Observability](#monitoring--observability)
8. [Disaster Recovery](#disaster-recovery)
9. [Security Configuration](#security-configuration)
10. [Cost Optimization](#cost-optimization)

---

## Infrastructure Overview

### Technology Stack

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
        Mobile[Mobile App<br/>Future]
    end
    
    subgraph "CDN & Edge"
        Netlify[Netlify CDN<br/>Frontend Hosting]
        Cloudflare[Cloudflare<br/>DNS & DDoS]
    end
    
    subgraph "Application Layer"
        LB[Load Balancer<br/>Traefik]
        API1[API Container 1]
        API2[API Container 2]
        API3[API Container N]
    end
    
    subgraph "Worker Layer"
        Worker1[Celery Worker 1<br/>Image Tasks]
        Worker2[Celery Worker 2<br/>Video Tasks]
        Worker3[Celery Worker 3<br/>Audio Tasks]
        Worker4[Celery Worker N<br/>General Tasks]
        Flower[Flower<br/>Monitoring]
    end
    
    subgraph "Cache & Queue"
        Redis[(Redis<br/>Cache & Queue)]
    end
    
    subgraph "Database Layer"
        Supabase[(Supabase<br/>PostgreSQL)]
        Storage[Supabase<br/>Object Storage]
    end
    
    subgraph "External Services"
        OpenRouter[OpenRouter<br/>LLM Gateway]
        ModelsLab[ModelsLab<br/>Image/Video]
        ElevenLabs[ElevenLabs<br/>Audio]
        Stripe[Stripe<br/>Payments]
        Mailgun[Mailgun<br/>Email]
    end
    
    Browser --> Cloudflare
    Cloudflare --> Netlify
    Browser --> Cloudflare
    Cloudflare --> LB
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> Redis
    API2 --> Redis
    API3 --> Redis
    
    API1 --> Supabase
    API2 --> Supabase
    API3 --> Supabase
    
    Redis --> Worker1
    Redis --> Worker2
    Redis --> Worker3
    Redis --> Worker4
    
    Worker1 --> Storage
    Worker2 --> Storage
    Worker3 --> Storage
    
    API1 -.-> OpenRouter
    API2 -.-> ModelsLab
    API3 -.-> ElevenLabs
    API1 -.-> Stripe
    API2 -.-> Mailgun
    
    Worker1 -.-> ModelsLab
    Worker2 -.-> ModelsLab
    Worker3 -.-> ElevenLabs
```

### Infrastructure Components

| Component | Technology | Purpose | Scaling |
|-----------|-----------|---------|---------|
| **Frontend** | React + Vite | User interface | CDN distribution |
| **API Gateway** | FastAPI + Uvicorn | REST API endpoints | Horizontal (3-10 instances) |
| **Load Balancer** | Traefik | Request distribution | High availability pair |
| **Workers** | Celery + Python | Async task processing | Horizontal (5-50 workers) |
| **Cache/Queue** | Redis | Caching & messaging | Master-replica with Sentinel |
| **Database** | PostgreSQL (Supabase) | Primary data store | Managed service |
| **Object Storage** | Supabase Storage | Media files | Managed service |
| **Monitoring** | Flower + Sentry | Task & error tracking | Single instance |

---

## Deployment Architecture

### Production Environment Diagram

```mermaid
graph TB
    subgraph "Internet"
        Users[Users]
    end
    
    subgraph "Edge Layer - Cloudflare"
        DNS[DNS]
        CDN[CDN Cache]
        WAF[Web Application Firewall]
        DDoS[DDoS Protection]
    end
    
    subgraph "Frontend - Netlify"
        Static[Static Assets<br/>React Build]
    end
    
    subgraph "VPS/Cloud Server - DigitalOcean/AWS"
        subgraph "Docker Network"
            Traefik[Traefik<br/>:80, :443]
            
            subgraph "API Services"
                API_1[API Instance 1<br/>:8001]
                API_2[API Instance 2<br/>:8002]
                API_3[API Instance 3<br/>:8003]
            end
            
            subgraph "Worker Services"
                Worker_Image[Image Worker<br/>x3 instances]
                Worker_Video[Video Worker<br/>x3 instances]
                Worker_Audio[Audio Worker<br/>x2 instances]
                Worker_General[General Worker<br/>x2 instances]
            end
            
            Redis_Master[Redis Master<br/>:6379]
            Redis_Replica[Redis Replica<br/>:6380]
            
            Flower[Flower Dashboard<br/>:5555]
            Mailpit[Mailpit<br/>Dev Email<br/>:8025]
        end
    end
    
    subgraph "Managed Services"
        Supabase_DB[(Supabase PostgreSQL)]
        Supabase_Auth[Supabase Auth]
        Supabase_Storage[Supabase Storage]
        
        Stripe_API[Stripe API]
        Mailgun_API[Mailgun API]
        
        OpenRouter_API[OpenRouter API]
        ModelsLab_API[ModelsLab API]
        ElevenLabs_API[ElevenLabs API]
    end
    
    Users --> DNS
    DNS --> WAF
    WAF --> DDoS
    DDoS --> CDN
    
    CDN --> Static
    CDN --> Traefik
    
    Traefik --> API_1
    Traefik --> API_2
    Traefik --> API_3
    Traefik --> Flower
    
    API_1 --> Redis_Master
    API_2 --> Redis_Master
    API_3 --> Redis_Master
    
    Redis_Master -.->|Replication| Redis_Replica
    
    Redis_Master --> Worker_Image
    Redis_Master --> Worker_Video
    Redis_Master --> Worker_Audio
    Redis_Master --> Worker_General
    
    API_1 --> Supabase_DB
    API_1 --> Supabase_Auth
    Worker_Image --> Supabase_Storage
    Worker_Video --> Supabase_Storage
    Worker_Audio --> Supabase_Storage
    
    API_1 -.->|HTTPS| Stripe_API
    API_2 -.->|HTTPS| Mailgun_API
    API_1 -.->|HTTPS| OpenRouter_API
    Worker_Image -.->|HTTPS| ModelsLab_API
    Worker_Audio -.->|HTTPS| ElevenLabs_API
```

### Environment Tiers

#### Development
- Local Docker Compose
- Single instance of each service
- SQLite or local PostgreSQL
- Mock external services
- Hot reload enabled

#### Staging
- Mimics production setup
- Smaller instance sizes
- Test data only
- Full external service integration
- Automated testing

#### Production
- Multi-instance deployment
- High availability configuration
- Production databases
- CDN enabled
- Full monitoring

---

## Container Architecture

### Docker Compose Structure

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API Gateway (3 replicas)
  api:
    image: litinkai/api:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      - redis
    networks:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Workers - Image Generation
  worker-image:
    image: litinkai/worker:latest
    deploy:
      replicas: 3
    command: celery -A app.celery_app worker -Q image -c 4 -n image@%h
    environment:
      - WORKER_TYPE=image
      - MODELSLAB_API_KEY=${MODELSLAB_API_KEY}
    depends_on:
      - redis
    networks:
      - backend

  # Celery Workers - Video Generation
  worker-video:
    image: litinkai/worker:latest
    deploy:
      replicas: 3
    command: celery -A app.celery_app worker -Q video -c 2 -n video@%h
    environment:
      - WORKER_TYPE=video
    depends_on:
      - redis
    networks:
      - backend

  # Celery Workers - Audio Generation
  worker-audio:
    image: litinkai/worker:latest
    deploy:
      replicas: 2
    command: celery -A app.celery_app worker -Q audio -c 4 -n audio@%h
    environment:
      - WORKER_TYPE=audio
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    depends_on:
      - redis
    networks:
      - backend

  # Redis (with persistence)
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 4gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s

  # Flower (monitoring)
  flower:
    image: mher/flower:latest
    command: celery flower --broker=redis://redis:6379
    environment:
      - CELERY_BROKER_URL=redis://redis:6379
    ports:
      - "5555:5555"
    depends_on:
      - redis
    networks:
      - backend

  # Traefik (load balancer)
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik/acme.json:/acme.json
    networks:
      - backend

volumes:
  redis-data:

networks:
  backend:
    driver: bridge
```

### Container Images

#### API Image (Dockerfile)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Frontend Build (Netlify)

```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = "dist"
  
[build.environment]
  NODE_VERSION = "18"
  
[[redirects]]
  from = "/api/*"
  to = "https://api.litinkai.com/api/:splat"
  status = 200
  
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
  
[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-Content-Type-Options = "nosniff"
    X-XSS-Protection = "1; mode=block"
    Referrer-Policy = "strict-origin-when-cross-origin"
```

---

## Environment Configuration

### Environment Variables

#### API Service (.env.production)

```bash
# Application
ENVIRONMENT=production
APP_NAME=LitinkAI
API_VERSION=v1
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@host:5432/litinkai
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=xxxxx
SUPABASE_SERVICE_KEY=xxxxx

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# AI Services
OPENROUTER_API_KEY=sk-or-xxxxx
OPENAI_API_KEY=sk-xxxxx
DEEPSEEK_API_KEY=xxxxx
MODELSLAB_API_KEY=xxxxx
ELEVENLABS_API_KEY=xxxxx

# Payment
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx

# Email
MAILGUN_API_KEY=xxxxx
MAILGUN_DOMAIN=mg.litinkai.com
EMAIL_FROM=noreply@litinkai.com

# Security
JWT_SECRET_KEY=xxxxx-random-secret-xxxxx
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# CORS
ALLOWED_ORIGINS=https://litinkai.com,https://www.litinkai.com
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Monitoring
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

#### Frontend (.env.production)

```bash
VITE_API_BASE_URL=https://api.litinkai.com/api/v1
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=xxxxx
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
VITE_ENVIRONMENT=production
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v
      
      - name: Lint code
        run: |
          cd backend
          flake8 app/ --max-line-length=100

  build-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Build and push API image
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          push: true
          tags: litinkai/api:latest,litinkai/api:${{ github.sha }}
          cache-from: type=registry,ref=litinkai/api:latest
          cache-to: type=inline
      
      - name: Build and push Worker image
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          file: ./backend/Dockerfile.worker
          push: true
          tags: litinkai/worker:latest,litinkai/worker:${{ github.sha }}

  build-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build
        env:
          VITE_API_BASE_URL: ${{ secrets.VITE_API_BASE_URL }}
          VITE_SUPABASE_URL: ${{ secrets.VITE_SUPABASE_URL }}
      
      - name: Deploy to Netlify
        uses: netlify/actions/cli@master
        with:
          args: deploy --prod --dir=dist
        env:
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}

  deploy:
    needs: [build-backend, build-frontend]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_SERVER_HOST }}
          username: ${{ secrets.PROD_SERVER_USER }}
          key: ${{ secrets.PROD_SERVER_SSH_KEY }}
          script: |
            cd /opt/litinkai
            docker-compose pull
            docker-compose up -d --remove-orphans
            docker image prune -f
      
      - name: Health check
        run: |
          sleep 30
          curl -f https://api.litinkai.com/health || exit 1
      
      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment to production completed!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Deployment Process

```mermaid
graph LR
    A[Code Push] --> B[Run Tests]
    B --> C{Tests Pass?}
    C -->|No| D[Notify Failure]
    C -->|Yes| E[Build Docker Images]
    E --> F[Push to Registry]
    F --> G[Deploy to Staging]
    G --> H[Run Integration Tests]
    H --> I{Tests Pass?}
    I -->|No| J[Rollback]
    I -->|Yes| K[Deploy to Production]
    K --> L[Health Checks]
    L --> M{Healthy?}
    M -->|No| N[Rollback]
    M -->|Yes| O[Notify Success]
```

---

## Scaling Strategy

### Horizontal Scaling

#### API Instances

```bash
# Scale API to 5 instances
docker-compose up --scale api=5 -d

# Auto-scaling rules (Kubernetes HPA)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Worker Scaling Strategy

| Worker Type | Min | Max | Scale Trigger |
|-------------|-----|-----|---------------|
| Image | 3 | 10 | Queue depth > 50 |
| Video | 3 | 8 | Queue depth > 30 |
| Audio | 2 | 6 | Queue depth > 40 |
| General | 2 | 5 | Queue depth > 100 |

### Vertical Scaling

#### Resource Allocation

**API Containers:**
- CPU: 1-2 cores per instance
- Memory: 2-4GB per instance
- Storage: 10GB per instance

**Worker Containers:**
- Image Workers: 2-4 cores, 4-8GB RAM
- Video Workers: 4-8 cores, 8-16GB RAM
- Audio Workers: 2 cores, 2-4GB RAM

**Redis:**
- Memory: 4-8GB (based on queue size)
- CPU: 2 cores

---

## Monitoring & Observability

### Monitoring Stack

```mermaid
graph TB
    subgraph "Application Layer"
        API[API Instances]
        Workers[Celery Workers]
    end
    
    subgraph "Metrics Collection"
        Prometheus[Prometheus]
        StatsD[StatsD]
    end
    
    subgraph "Visualization"
        Grafana[Grafana Dashboards]
        Flower[Flower UI]
    end
    
    subgraph "Logging"
        Loki[Loki]
        CloudWatch[AWS CloudWatch]
    end
    
    subgraph "Alerting"
        AlertManager[Alert Manager]
        PagerDuty[PagerDuty]
        Slack[Slack]
    end
    
    subgraph "Error Tracking"
        Sentry[Sentry]
    end
    
    API --> Prometheus
    Workers --> Prometheus
    API --> StatsD
    Workers --> StatsD
    
    Prometheus --> Grafana
    Workers --> Flower
    
    API --> Loki
    Workers --> Loki
    API --> CloudWatch
    
    Prometheus --> AlertManager
    AlertManager --> PagerDuty
    AlertManager --> Slack
    
    API --> Sentry
    Workers --> Sentry
```

### Key Metrics

#### Application Metrics
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (errors/second)
- Active connections
- CPU and memory usage

#### Business Metrics
- User registrations (per day)
- Subscription conversions
- Video generations (per hour)
- AI API costs (per day)
- Storage usage (GB)

#### Worker Metrics
- Queue depth per queue
- Task success/failure rate
- Average task duration
- Worker utilization
- Retry counts

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
        
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
        for: 5m
        annotations:
          summary: "95th percentile response time > 2s"
      
      - alert: HighCPUUsage
        expr: container_cpu_usage > 80
        for: 10m
        annotations:
          summary: "CPU usage above 80%"

  - name: worker_alerts
    rules:
      - alert: HighQueueDepth
        expr: celery_queue_length > 100
        for: 15m
        annotations:
          summary: "Queue depth above 100 tasks"
      
      - alert: WorkerDown
        expr: up{job="celery-worker"} == 0
        for: 2m
        annotations:
          summary: "Celery worker is down"
```

---

## Disaster Recovery

### Backup Strategy

#### Database Backups
- **Frequency**: Every 6 hours (Supabase automated)
- **Retention**: 30 days
- **Type**: Full backup + point-in-time recovery
- **Location**: Multi-region storage

#### Storage Backups
- **Frequency**: Daily incremental
- **Retention**: 90 days
- **Type**: Object versioning enabled
- **Location**: Supabase replication

#### Configuration Backups
- **Frequency**: On every change
- **Retention**: Indefinite (Git)
- **Type**: Git repository
- **Location**: GitHub

### Recovery Procedures

#### Database Recovery

```bash
# Restore from specific point in time
supabase db restore --project-id=xxxxx --timestamp="2025-11-06T18:00:00Z"

# Verify restoration
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
```

#### Application Recovery

```bash
# Rollback to previous version
docker-compose down
git checkout <previous-commit>
docker-compose pull
docker-compose up -d

# Or rollback using specific image tag
docker-compose down
sed -i 's/latest/<previous-tag>/g' docker-compose.yml
docker-compose up -d
```

### Recovery Time Objectives

| Component | RTO | RPO | Strategy |
|-----------|-----|-----|----------|
| Database | 1 hour | 15 minutes | Automated backup restore |
| Application | 15 minutes | 0 (stateless) | Redeploy from images |
| Object Storage | 4 hours | 24 hours | Copy from backup bucket |
| Configuration | 5 minutes | 0 | Git checkout |

---

## Security Configuration

### SSL/TLS Configuration

```nginx
# Traefik TLS configuration
[entryPoints]
  [entryPoints.websecure]
    address = ":443"
    [entryPoints.websecure.http.tls]
      minVersion = "VersionTLS12"
      cipherSuites = [
        "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
        "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
      ]
```

### Firewall Rules

```bash
# UFW configuration
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### Secrets Management

```bash
# Using Docker secrets
echo "database_password" | docker secret create db_password -
echo "api_key" | docker secret create openrouter_key -

# Reference in compose file
services:
  api:
    secrets:
      - db_password
      - openrouter_key
```

---

## Cost Optimization

### Infrastructure Costs (Monthly)

| Service | Configuration | Cost |
|---------|--------------|------|
| DigitalOcean Droplet | 8GB RAM, 4 CPUs | $48 |
| Redis Cloud | 4GB | $45 |
| Supabase Pro | Database + Storage | $25 |
| Netlify Pro | CDN + Hosting | $19 |
| Cloudflare Pro | DNS + Security | $20 |
| **Total Infrastructure** | | **$157** |

### AI Service Costs (Variable)

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| OpenRouter | 50M tokens | $250-500 |
| ModelsLab | 5,000 images | $50-150 |
| ElevenLabs | 500K characters | $90 |
| **Total AI** | | **$390-740** |

### Cost Optimization Strategies

1. **Caching**: Reduce AI API calls by 30-40%
2. **Batch Processing**: Group similar requests
3. **Tier-based Models**: Use cheaper models for free tier
4. **Spot Instances**: Use for non-critical workers
5. **Auto-scaling**: Scale down during off-hours

---

## Quick Reference

### Deployment Commands

```bash
# Deploy to production
git push origin main  # Triggers CI/CD

# Manual deployment
ssh production-server
cd /opt/litinkai
git pull
docker-compose up -d --build

# View logs
docker-compose logs -f api
docker-compose logs -f worker-image

# Scale services
docker-compose up --scale api=5 -d
docker-compose up --scale worker-video=4 -d

# Health check
curl https://api.litinkai.com/health
```

### Troubleshooting

```bash
# Check service status
docker-compose ps

# Restart specific service
docker-compose restart api

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# View worker tasks
docker-compose exec flower celery -A app.celery_app inspect active

# Database connection test
docker-compose exec api python -c "from app.database import test_connection; test_connection()"
```

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/index.html)
- [Main Architecture README](README.md)

---

**Last Updated**: 2025-11-06  
**Version**: 1.0  
**Maintained By**: DevOps Team