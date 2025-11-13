# Quick Start - Local Development

Get up and running with local development in 5 minutes!

## Prerequisites

- Docker Desktop (running)
- Supabase CLI installed

```bash
# Install Supabase CLI
brew install supabase/tap/supabase  # macOS
```

## Steps

### 1. Start Services

```bash
cd backend
./scripts/start-local-dev.sh
```

Wait 1-2 minutes for all services to start.

### 2. Open Dashboards

- **Supabase Studio**: http://127.0.0.1:54323
- **API**: http://localhost:8000/docs
- **Email Testing**: http://127.0.0.1:54324

### 3. Test Login

Use these test accounts (password: `password123`):

- `superadmin@litinkai.local`
- `creator@litinkai.local`
- `user@litinkai.local`

### 4. Start Coding!

The API will hot-reload when you make changes to Python files.

## Common Commands

```bash
# View logs
./scripts/view-local-logs.sh

# Reset database
./scripts/reset-local-db.sh

# Stop everything
./scripts/stop-local-dev.sh
```

## Need Help?

See [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md) for detailed documentation.

## Troubleshooting

**Port conflicts?**
```bash
# Stop everything and restart
./scripts/stop-local-dev.sh
./scripts/start-local-dev.sh
```

**Database issues?**
```bash
# Reset database
./scripts/reset-local-db.sh
```

**Can't connect?**
- Make sure Docker is running
- Check all services started: `docker-compose -f local.yml ps`
- Check Supabase: `cd supabase && supabase status && cd ..`

## What's Running?

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | Main application |
| Supabase Studio | http://127.0.0.1:54323 | Database UI |
| Inbucket | http://127.0.0.1:54324 | Email testing |
| RabbitMQ | http://localhost:15672 | Message queue |
| Flower | http://localhost:5555 | Celery monitoring |

---

**You're ready to code!** 🚀
