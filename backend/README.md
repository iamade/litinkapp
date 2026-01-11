try to implmenet passkeys and sso in future

# Litink Backend API

FastAPI backend for the Litink AI-powered interactive book platform.

## Features

- **Authentication & Authorization**: JWT-based auth with role-based access
- **AI Integration**: OpenAI for content generation, ElevenLabs for voice, Tavus for video
- **Blockchain**: Algorand integration for NFT badges and collectibles
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for performance optimization
- **Background Tasks**: Celery for async processing
- **File Processing**: Support for PDF, DOCX, and TXT uploads

## Quick Start

### Local Development (Recommended)

**New developers: Follow these steps for first-time setup:**

```bash
cd backend

# Step 1: Start Supabase local instance
make supabase-start

# Step 2: Update .env.local with LOCAL Supabase keys
./scripts/update-env-keys.sh

# Step 3: Start application services
make dev
```

**For subsequent starts:**
```bash
cd backend
make all-up  # Starts both Supabase and application
```

This starts:
- Supabase local (Database, Auth, Storage, Studio)
- All application services (API, Redis, Celery, etc.)
- Email testing with Inbucket

**For detailed setup:** See [LOCAL_DEVELOPMENT_GUIDE.md](LOCAL_DEVELOPMENT_GUIDE.md)

**Having issues?** See [SUPABASE_TROUBLESHOOTING.md](SUPABASE_TROUBLESHOOTING.md)

### Production/Cloud Database

To connect to the production database (not recommended for development):

1. Copy environment file:
   ```bash
   cp .envs/.env.example .envs/.env.production
   ```
2. Update with production credentials
3. Start services:
   ```bash
   docker-compose -f local.yml up -d
   ```

The API will be available at `http://localhost:8000`

### Manual Setup

1. Install Python 3.11+
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up PostgreSQL and Redis
5. Copy and configure `.env` file
6. Run migrations:
   ```bash
   alembic upgrade head
   ```
7. Start the server:
   ```bash
  make up 
   ```

## API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Environment Variables

### Required
- `SECRET_KEY`: JWT secret key
- `DATABASE_URL`: PostgreSQL connection string

### AI Services (Optional - will use mock data if not provided)
- `OPENAI_API_KEY`: OpenAI API key for content generation
- `ELEVENLABS_API_KEY`: ElevenLabs API key for voice generation
- `TAVUS_API_KEY`: Tavus API key for video generation

### Blockchain (Optional)
- `ALGORAND_TOKEN`: Algorand API token
- `CREATOR_MNEMONIC`: Algorand account mnemonic for NFT creation

### Infrastructure
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### Books
- `GET /api/v1/books/` - Get published books
- `POST /api/v1/books/` - Create book (authors only)
- `GET /api/v1/books/{id}` - Get book details
- `POST /api/v1/books/upload` - Upload book file

### AI Services
- `POST /api/v1/ai/generate-quiz` - Generate AI quiz
- `POST /api/v1/ai/generate-voice` - Generate voice audio
- `POST /api/v1/ai/generate-video-scene` - Generate video scene

### Merge Operations
- `POST /api/v1/merge/manual` - Start a manual merge operation
- `POST /api/v1/merge/preview` - Generate a merge preview
- `GET /api/v1/merge/status/{merge_id}` - Check merge operation status
- `GET /api/v1/merge/{merge_id}/download` - Download completed merge result
- `POST /api/v1/merge/upload` - Upload files for merge operations

### User Progress
- `GET /api/v1/users/me/progress` - Get reading progress
- `POST /api/v1/users/me/progress/{book_id}` - Update progress

### Badges & NFTs
- `GET /api/v1/badges/` - Get available badges
- `GET /api/v1/badges/me` - Get user badges
- `GET /api/v1/nfts/me` - Get user NFT collectibles

## Architecture

### Core Components
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation and serialization
- **JWT**: Secure authentication
- **Celery**: Background task processing

### AI Services
- **OpenAI GPT-3.5**: Content generation and analysis
- **ElevenLabs**: Voice synthesis for characters
- **Tavus**: AI video generation for scenes

### Blockchain
- **Algorand**: NFT creation for badges and collectibles
- **py-algorand-sdk**: Python SDK for Algor and integration

### Database Schema
- Users with role-based access (author/explorer)
- Books with chapters and AI-generated content
- Progress tracking and analytics
- Quiz system with attempts and scoring
- Badge and NFT collectible systems

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
isort app/
flake8 app/
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Background Tasks
Monitor Celery tasks with Flower:
```bash
celery -A app.tasks.celery_app flower
```
Access at `http://localhost:5555`

## Production Deployment

1. Set `ENVIRONMENT=production` in `.env`
2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```
3. Set up proper database and Redis instances
4. Configure reverse proxy (nginx)
5. Set up SSL certificates
6. Monitor with logging and metrics

## Security

- JWT tokens for authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation with Pydantic
- SQL injection prevention with SQLAlchemy
- Rate limiting (can be added with slowapi)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run code formatting and tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

make dev     # Should show: 🔄 Starting in DEVELOPMENT mode WITHOUT debugger...
make debug   # Should show: 🐛 Starting in DEVELOPMENT mode WITH debugger...
make up      # Should show: 🚀 Starting in PRODUCTION mode...
make rebuild-dev


<!-- Step 4: Start VS Code Debugger
Go to Run and Debug panel (Ctrl+Shift+D)
Select "Docker: Attach to FastAPI"
Click the green play button
Wait for "Attached to Python" message
Step 5: Trigger the Code
Go to your frontend
Upload a book to trigger the breakpoints
VS Code should stop at your breakpoints
4. Debug the 'id' Error Specifically
Set breakpoints at these critical points: -->

## Quick Start Workflow

make supabase-start - Start database (once)
Update .envs/.env.local with the keys from output
make dev - Start your application
make down - Stop app when done
make supabase-stop - Stop database when completely done
Use make help to see all available commands!

ALL test users (superadmin, admin, creator, user, premium accounts)
**First Time Setup:**
1. `make supabase-start` - Start local Supabase (database, auth, storage)
2. `./scripts/update-env-keys.sh` - Automatically update .env.local with local keys
3. Create superadmin user in Supabase Studio (http://127.0.0.1:54323)
   - Email: support@litinkai.com
   - Set a secure password
4. `make dev` - Start your application

**Daily Development:**
1. `make all-up` - Start everything (Supabase + app)
2. Make your changes and develop
3. `make down` - Stop app when done
4. `make supabase-stop` - Stop database when completely done

**Common Commands:**
- `make help` - See all available commands
- `make logs` - View API logs
- `make supabase-status` - Check Supabase status
- `make supabase-reset` - Reset database (⚠️ deletes all data!)

## Important Notes

### Local vs Remote Supabase
Your `.env.local` should use **LOCAL** Supabase keys for development:
- ✅ `SUPABASE_URL=http://127.0.0.1:54321`
- ✅ `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- ✅ Local API keys from `supabase status` or `./scripts/update-env-keys.sh`

❌ **Do NOT use remote/cloud Supabase keys** (vtuqaubejlzqjmieelyr.supabase.co) in local development

### Stripe Integration
Stripe payment processing is fully integrated. Ensure you have:
- `STRIPE_SECRET_KEY` in your `.env.local`
- `STRIPE_PUBLISHABLE_KEY` for frontend
- `STRIPE_WEBHOOK_SECRET` for webhook handling

### make makemigrations name="add_character_ids_to_scripts"