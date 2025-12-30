# MinIO Setup Guide for Litinkapp

## Why MinIO?

MinIO provides S3-compatible object storage that:
- ✅ **Memory-efficient**: Streams files instead of loading into RAM
- ✅ **Production-ready**: Same API as AWS S3
- ✅ **Local development**: No cloud costs during development
- ✅ **Scalable**: Easy to switch to AWS S3/Supabase for production

## Quick Setup

### 1. Start MinIO with Docker

Add to your `local.yml`: #i have local.yml not docker-compose.yml

```yaml
services:
  minio:
    image: minio/minio:latest
    container_name: minio
    ports:
      - "9000:9000"      # API port
      - "9001:9001"      # Console port
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    networks:
      - litinkapp_network

volumes:
  minio_data:
```

### 2. Start MinIO

```bash
docker compose -f local.yml up -d minio
```

### 3. Access MinIO Console

- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

### 4. Create Bucket

In the MinIO console:
1. Go to "Buckets"
2. Click "Create Bucket"
3. Name it `litinkapp`
4. Set access policy to "Public" (or configure as needed)

### 5. Environment Variables

Your `.env` file should have:

```bash
# Storage Configuration
USE_MINIO=true
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=litinkapp
MINIO_PUBLIC_URL=http://localhost:9000
```

## Production Setup

### Option 1: Supabase Storage

```bash
USE_MINIO=false
USE_SUPABASE_STORAGE=true
SUPABASE_STORAGE_ENDPOINT=https://your-project.supabase.co/storage/v1/s3
SUPABASE_BUCKET_NAME=books
AWS_ACCESS_KEY_ID=your-supabase-s3-key
AWS_SECRET_ACCESS_KEY=your-supabase-s3-secret
```

### Option 2: AWS S3

```bash
USE_MINIO=false
USE_SUPABASE_STORAGE=false
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
AWS_BUCKET_NAME=litinkapp-production
```

## Memory Benefits

### Before (LocalStorageService)
```python
# Loads entire file into memory
file_content = await file.read()  # 100MB file = 100MB RAM
await storage.upload(file_content, path)
```

### After (S3StorageService)
```python
# Streams file in chunks
await storage.upload_stream(file.file, path)  # ~10MB RAM max
```

## Usage in Code

The storage service automatically uses the right backend:

```python
from app.core.services.storage import storage_service

# Upload (works with MinIO, Supabase, or AWS)
url = await storage_service.upload(file_bytes, "path/to/file.pdf")

# Upload large files (streaming)
url = await storage_service.upload_stream(file_stream, "path/to/large-video.mp4")

# Download
content = await storage_service.download("path/to/file.pdf")

# Delete
await storage_service.delete("path/to/file.pdf")

# List files
files = storage_service.list("users/123/covers")

# Batch delete
await storage_service.remove_batch(["file1.pdf", "file2.pdf"])
```

## Testing

```bash
# Test MinIO connection
docker exec -it minio mc alias set local http://localhost:9000 minioadmin minioadmin

# List buckets
docker exec -it minio mc ls local

# Upload test file
docker exec -it minio mc cp /tmp/test.txt local/litinkapp/test.txt
```

## Troubleshooting

### MinIO not accessible
```bash
# Check if MinIO is running
docker ps | grep minio

# Check logs
docker logs minio

# Restart MinIO
docker-compose restart minio
```

### Bucket not found
```bash
# Create bucket via CLI
docker exec -it minio mc mb local/litinkapp
```

### Connection refused
- Make sure `MINIO_ENDPOINT` uses `http://minio:9000` (container name) not `localhost` when running in Docker
- For local testing outside Docker, use `http://localhost:9000`

## Migration from Supabase Storage

All storage operations have been refactored to use the new `S3StorageService`. Simply:

1. Start MinIO
2. Set `USE_MINIO=true` in `.env`
3. Restart your backend

Files will now be stored in MinIO instead of Supabase Storage, saving memory and cloud costs during development!
