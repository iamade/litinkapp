# Supabase Storage Setup for Video Files

## Overview

This app now uses **Supabase Storage** instead of local file storage for video files. This provides:

- ✅ **Cloud storage** - Videos stored in the cloud, not on your PC
- ✅ **Public URLs** - Direct access to videos from anywhere
- ✅ **Scalability** - No local storage limitations
- ✅ **Reliability** - Videos persist even if server restarts
- ✅ **CDN** - Fast global delivery via Supabase CDN

## Setup Instructions

### 1. Environment Variables

Make sure your `.env` file has these Supabase credentials:

```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_BUCKET_NAME=books  # or any bucket name you prefer
```

### 2. Run Setup Script

```bash
cd backend
python setup_supabase_storage.py
```

This script will:

- Create the storage bucket if it doesn't exist
- Set up public access for video files
- Test the upload functionality
- Configure file size limits (50MB) and allowed file types

### 3. Manual Setup (Alternative)

If you prefer to set up manually in Supabase Dashboard:

1. Go to your Supabase project dashboard
2. Navigate to **Storage** → **Buckets**
3. Create a new bucket named `books` (or your preferred name)
4. Set bucket to **Public**
5. Configure file size limit to 50MB
6. Add allowed MIME types:
   - `video/mp4`
   - `video/webm`
   - `video/avi`
   - `image/png`
   - `image/jpeg`
   - `application/pdf`

## How It Works

### Before (Local Storage)

```
Video generated → Saved to backend/uploads/videos/ → Served via FastAPI static files
```

### After (Supabase Storage)

```
Video generated → Uploaded to Supabase Storage → Public URL returned → Frontend plays directly
```

### File Structure in Supabase

```
books/ (bucket)
├── videos/
│   ├── mock_video_1234567890.mp4
│   ├── merged_video_1234567891.mp4
│   └── chapter_video_1234567892.mp4
├── covers/
│   └── book_covers.png
└── pdfs/
    └── uploaded_books.pdf
```

## Benefits

### For Development

- No need to manage local file storage
- Videos accessible from any device
- No file cleanup required
- Easy testing across different environments

### For Production

- Scalable cloud storage
- Global CDN delivery
- Automatic backups
- No server storage costs
- Better user experience

## API Changes

The video service now returns URLs like:

```json
{
  "video_url": "https://your-project.supabase.co/storage/v1/object/public/books/videos/mock_video_1234567890.mp4",
  "supabase_url": "https://your-project.supabase.co/storage/v1/object/public/books/videos/mock_video_1234567890.mp4"
}
```

Instead of local paths like:

```json
{
  "video_url": "/uploads/videos/mock_video_1234567890.mp4"
}
```

## Frontend Integration

The frontend `<video>` element will work seamlessly with Supabase URLs:

```tsx
<video src={videoData.video_url} controls className="w-full h-auto" />
```

## Troubleshooting

### Common Issues

1. **"Bucket not found" error**

   - Run the setup script: `python setup_supabase_storage.py`
   - Check bucket name in `.env` file

2. **"Permission denied" error**

   - Ensure bucket is set to **Public**
   - Check service role key permissions

3. **"File too large" error**

   - Increase file size limit in bucket settings
   - Default limit is 50MB

4. **Upload fails**
   - Check internet connection
   - Verify Supabase credentials
   - Check file format is allowed

### Fallback Behavior

If Supabase upload fails, the system falls back to local storage:

- Videos saved locally as before
- Served via FastAPI static files
- Logs error for debugging

## Security Considerations

### Public Access

- Videos are publicly accessible via URLs
- Anyone with the URL can view/download
- Consider implementing authentication for sensitive content

### Row Level Security (RLS)

For production, consider implementing RLS policies:

```sql
-- Example: Only authenticated users can upload
CREATE POLICY "Users can upload videos" ON storage.objects
FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Example: Only book owners can delete their videos
CREATE POLICY "Book owners can delete videos" ON storage.objects
FOR DELETE USING (
  auth.uid() IN (
    SELECT user_id FROM books WHERE id = (
      SELECT book_id FROM chapters WHERE id = (
        SELECT chapter_id FROM videos WHERE storage_path = storage.objects.name
      )
    )
  )
);
```

## Cost Considerations

- **Supabase Storage**: $0.021 per GB/month
- **Bandwidth**: $0.09 per GB
- **Free tier**: 1GB storage, 2GB bandwidth/month

For typical video files (10-50MB each), costs are minimal for most use cases.
