# LitInkAI

AI-powered book processing and trailer generation platform.

**Stack:** FastAPI + React + PostgreSQL + Redis + Celery + MinIO

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/iamade/litinkapp.git
cd litinkapp

# Start all services
docker-compose up -d

# Services will be available at:
# - Frontend:      http://localhost:5173
# - Backend API:   http://localhost:8000
# - API Docs:      http://localhost:8000/docs
# - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
```

---

## Docker Services

| Service       | Port  | Description                      |
|---------------|-------|----------------------------------|
| postgres      | 5432  | PostgreSQL 16 database           |
| redis         | 6379  | Redis for Celery broker          |
| minio         | 9000/9001 | S3-compatible object storage |
| backend       | 8000  | FastAPI backend                  |
| frontend      | 5173  | React/Vite frontend              |
| celery-worker | -     | Celery task worker               |
| celery-beat   | -     | Celery task scheduler            |

---

## Development Commands

### Frontend (Local)

```bash
cd frontend
npm install
npm run dev      # Development server on :5173
npm run build    # Production build
npm run lint     # ESLint
```

### Backend (Docker)

```bash
# Backend runs in Docker by default
# For local development:
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database

```bash
# PostgreSQL runs in Docker
# Connection string (inside containers):
# postgresql://litink:litink_dev_2026@postgres:5432/litinkapp
```

---

## Celery + Redis Setup

Celery handles async tasks (audio generation, video processing, book processing, etc.):

```bash
# Celery worker (in Docker)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Celery beat scheduler (in Docker)
celery -A app.tasks.celery_app beat --loglevel=info
```

**Required environment variables:**
```env
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379/0
```

---

## Branch Workflow (4-Stage)

```
feat/* → dev_branch → staging → main
```

| Branch        | Purpose                                    |
|---------------|-------------------------------------------|
| `feat/*`      | Feature branches (create from dev_branch)  |
| `dev_branch`  | Development integration                    |
| `staging`     | QA testing (requires PR)                   |
| `main`        | Production (requires Ade + CQO approval)   |

**Rules:**
- Never commit directly to `main` or `dev_branch`
- Create feature branches from `dev_branch`
- Merge to `staging` for QA testing
- Merge `staging` → `main` requires BOTH Ade AND CQO approval

---

## Environment Variables

Copy `.env.example` to `.env.local`:

```bash
cd backend/.envs
cp .env.example .env.local
# Edit with your API keys
```

**Required keys:**
- `OPENAI_API_KEY` — OpenAI API key
- `JWT_SECRET_KEY` — JWT signing secret
- `SIGNING_KEY` — Token signing key
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string

---

## Project Structure

```
litinkapp/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/                # Config, security, DB
│   │   ├── books/               # Book models & routes
│   │   ├── audiobooks/          # Audiobook generation service
│   │   ├── scripts/             # Script generation
│   │   ├── videos/              # Video generation
│   │   ├── trailers/            # Trailer generation
│   │   └── tasks/               # Celery async tasks
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── lib/                 # Utilities, API client
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

---

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

---

## Conventional Commits

Use prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`

Examples:
```
feat(KAN-149): add trailer scene selection service
fix(KAN-143): prevent cross-script data bleeding in StoryboardContext
docs: update README with dev setup instructions
```

---

## Questions?

Reach out in **#project-litinkai** Discord channel.