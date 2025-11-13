# Local Development Setup Checklist

Use this checklist to verify your local development environment is properly configured.

## ✅ Pre-Setup Checklist

- [ ] Docker Desktop installed and running
- [ ] Supabase CLI installed (`supabase --version`)
- [ ] Git repository cloned
- [ ] In the `backend` directory

## ✅ Configuration Checklist

### Environment Files

- [ ] `.envs/.env.local` exists
- [ ] `.envs/.env.local` has valid API keys (or placeholder keys for testing)
- [ ] `SUPABASE_URL` set to `http://127.0.0.1:54321`
- [ ] `DATABASE_URL` set to local postgres connection

### Supabase Configuration

- [ ] `supabase/config.toml` exists
- [ ] `supabase/seed.sql` exists
- [ ] `supabase/migrations/` contains 18 migration files
- [ ] Storage bucket configured in `config.toml`

### Scripts

- [ ] `scripts/start-local-dev.sh` exists and is executable
- [ ] `scripts/stop-local-dev.sh` exists and is executable
- [ ] `scripts/reset-local-db.sh` exists and is executable
- [ ] `scripts/view-local-logs.sh` exists and is executable

### Documentation

- [ ] `LOCAL_SETUP_COMPLETE.md` exists
- [ ] `QUICK_START_LOCAL.md` exists
- [ ] `LOCAL_DEVELOPMENT_GUIDE.md` exists
- [ ] `SETUP_SUMMARY.md` exists
- [ ] `scripts/README.md` exists

## ✅ First Start Checklist

### Starting Services

```bash
cd backend
./scripts/start-local-dev.sh
```

- [ ] Script runs without errors
- [ ] Supabase services start successfully
- [ ] Application services start successfully
- [ ] No port conflict errors

### Verify Supabase

Run: `cd supabase && supabase status && cd ..`

- [ ] API URL shows: `http://127.0.0.1:54321`
- [ ] DB URL shows: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- [ ] Studio URL shows: `http://127.0.0.1:54323`
- [ ] Inbucket URL shows: `http://127.0.0.1:54324`
- [ ] All services show as "Started"

### Verify Application Services

Run: `docker-compose -f local.yml ps`

- [ ] `api` service is "Up"
- [ ] `redis` service is "Up"
- [ ] `rabbitmq` service is "Up"
- [ ] `celeryworker` service is "Up"
- [ ] `celerybeat` service is "Up"
- [ ] `flower` service is "Up"
- [ ] `mailpit` service is "Up"

### Test URLs

Visit these URLs in your browser:

- [ ] http://127.0.0.1:54323 (Supabase Studio) - Opens successfully
- [ ] http://localhost:8000/docs (API Docs) - Shows FastAPI documentation
- [ ] http://127.0.0.1:54324 (Inbucket) - Shows email interface
- [ ] http://localhost:15672 (RabbitMQ) - Login with guest/guest works
- [ ] http://localhost:5555 (Flower) - Shows Celery dashboard

### Test API Health

Run: `curl http://localhost:8000/health`

- [ ] Returns `{"status":"healthy"}` or similar success message

### Verify Database

Open Supabase Studio (http://127.0.0.1:54323) and check:

- [ ] Database is accessible
- [ ] Table Editor shows existing tables
- [ ] SQL Editor works
- [ ] Authentication → Users shows 5 test users

### Test Users Exist

In Supabase Studio → Authentication → Users:

- [ ] superadmin@litinkai.local
- [ ] admin@litinkai.local
- [ ] creator@litinkai.local
- [ ] user@litinkai.local
- [ ] premium@litinkai.local

### Test Storage

In Supabase Studio → Storage:

- [ ] `books` bucket exists
- [ ] Bucket is accessible

## ✅ Development Workflow Checklist

### Making Code Changes

- [ ] Edit Python file in `backend/app/`
- [ ] API auto-reloads with changes
- [ ] No manual restart needed

### Viewing Logs

Run: `./scripts/view-local-logs.sh`

- [ ] Script shows menu of log options
- [ ] Can select and view logs
- [ ] Logs are readable and updating

### Creating Migration

```bash
cd supabase
supabase migration new test_migration
```

- [ ] Migration file created in `supabase/migrations/`
- [ ] File has timestamp and name

### Resetting Database

Run: `./scripts/reset-local-db.sh`

- [ ] Script asks for confirmation
- [ ] Accepts "yes" to proceed
- [ ] Database resets successfully
- [ ] Migrations re-applied
- [ ] Seed data reloaded
- [ ] Test users exist again

### Stopping Services

Run: `./scripts/stop-local-dev.sh`

- [ ] Application services stop
- [ ] Supabase services stop
- [ ] No errors during shutdown

## ✅ Integration Testing Checklist

### Test User Login

From your frontend application:

- [ ] Can login with `creator@litinkai.local` / `password123`
- [ ] User data loads correctly
- [ ] Dashboard shows user information
- [ ] Can logout successfully

### Test File Upload

- [ ] Can upload a test book/file
- [ ] File appears in Supabase Storage
- [ ] Database record created
- [ ] File accessible via URL

### Test Email Flow

- [ ] Trigger password reset or registration
- [ ] Email appears in Inbucket (http://127.0.0.1:54324)
- [ ] Email content is correct
- [ ] Links in email work

### Test Background Tasks

- [ ] Trigger a Celery task (e.g., book processing)
- [ ] Task appears in Flower (http://localhost:5555)
- [ ] Task completes successfully
- [ ] Can see task logs

## ✅ Troubleshooting Checklist

If something doesn't work:

### General Issues

- [ ] Docker is running
- [ ] No other services using required ports
- [ ] Ran from `backend` directory
- [ ] Scripts are executable (`chmod +x scripts/*.sh`)

### Supabase Issues

- [ ] Supabase CLI is installed
- [ ] Ran `supabase stop` then `supabase start`
- [ ] Checked `supabase status` for errors
- [ ] Reviewed Supabase logs

### Application Issues

- [ ] Checked `.envs/.env.local` is correct
- [ ] Ran `docker-compose -f local.yml down` then `up -d`
- [ ] Reviewed application logs
- [ ] No port conflicts (8000, 5555, 15672)

### Database Issues

- [ ] Ran `./scripts/reset-local-db.sh`
- [ ] Checked migrations have no errors
- [ ] Verified `seed.sql` syntax is correct
- [ ] Can access DB via Supabase Studio

## ✅ Production Readiness Checklist

Before pushing to production:

- [ ] All features tested locally
- [ ] All tests pass
- [ ] Database migrations work correctly
- [ ] No hardcoded local URLs in code
- [ ] Environment switching works correctly
- [ ] Migrations pushed to cloud: `supabase db push`

## 🎉 All Done!

If all items are checked, your local development environment is fully functional!

## 📚 Next Steps

- Read [QUICK_START_LOCAL.md](QUICK_START_LOCAL.md) for daily workflow
- Review [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md) for detailed info
- Check [scripts/README.md](scripts/README.md) for script details

---

**Need help?** Check the troubleshooting sections in the documentation or ask your team.
