# Production Deployment Guide

## Frontend Configuration

The frontend is already configured to use the correct backend URL in production. The `src/lib/api.ts` file automatically switches between:

- Development: `http://localhost:8000/api/v1`
- Production: `https://litinkapp.onrender.com/api/v1`

## Backend Configuration

### Environment Variables for Render Deployment

Set these environment variables in your Render dashboard:

```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-change-this-in-production

# CORS Configuration (comma-separated list)
ALLOWED_HOSTS=https://litinkai.com,https://www.litinkai.com,https://litink.com,https://www.litink.com

# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_BUCKET_NAME=books

# Redis Configuration
REDIS_URL=your-redis-url

# AI Services
OPENAI_API_KEY=your-openai-api-key
ELEVENLABS_API_KEY=your-elevenlabs-api-key
TAVUS_API_KEY=your-tavus-api-key
PLOTDRIVE_API_KEY=your-plotdrive-api-key

# KlingAI Configuration
KLINGAI_ACCESS_KEY_ID=your-klingai-access-key-id
KLINGAI_ACCESS_KEY_SECRET=your-klingai-access-key-secret

# Blockchain Configuration
ALGORAND_TOKEN=your-algorand-token
ALGORAND_SERVER=https://testnet-api.algonode.cloud
ALGORAND_INDEXER=https://testnet-idx.algonode.cloud
CREATOR_MNEMONIC=your-creator-mnemonic

# Celery Configuration
CELERY_BROKER_URL=your-redis-url/0
CELERY_RESULT_BACKEND=your-redis-url/0
```

### CORS Configuration

The backend is now configured to accept requests from:

- `https://litinkai.com`
- `https://www.litinkai.com`
- `https://litink.com`
- `https://www.litink.com`
- Local development URLs (localhost)

You can override this by setting the `ALLOWED_HOSTS` environment variable with a comma-separated list of domains.

## Deployment Steps

### 1. Frontend (Netlify)

- The frontend will automatically use the production backend URL
- The `netlify.toml` file is configured to redirect API calls to the Render backend
- Deploy to Netlify with the domain `litinkai.com`

### 2. Backend (Render)

- Deploy the backend to Render
- Set all required environment variables in the Render dashboard
- Ensure the service is accessible at `https://litinkapp.onrender.com`

### 3. Testing

- Test API connectivity from the frontend to backend
- Verify CORS is working correctly
- Test authentication flows
- Test file uploads and AI services

## Troubleshooting

### CORS Issues

If you encounter CORS errors:

1. Check that your frontend domain is in the `ALLOWED_HOSTS` list
2. Verify the `ALLOWED_HOSTS` environment variable is set correctly in Render
3. Ensure the backend is accessible and responding

### API Connection Issues

1. Verify the backend URL is correct in the frontend
2. Check that the backend is running and healthy
3. Test the health endpoint: `https://litinkapp.onrender.com/health`

### Environment Variables

1. Ensure all required environment variables are set in Render
2. Check that sensitive keys are properly configured
3. Verify Redis and Supabase connections