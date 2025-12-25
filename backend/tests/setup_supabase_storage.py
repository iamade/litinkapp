#!/usr/bin/env python3
"""
Setup script for Supabase Storage bucket for video files
Run this script to create the necessary storage bucket and policies
"""

import os
import sys
from supabase.client import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_supabase_storage():
    """Setup Supabase Storage bucket for video files"""
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        sys.exit(1)
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Get bucket name from config
        bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "books")
        
        print(f"🔧 Setting up Supabase Storage bucket: {bucket_name}")
        
        # Check if bucket exists
        try:
            buckets = supabase.storage.list_buckets()
            bucket_exists = any(bucket['name'] == bucket_name for bucket in buckets)
            
            if bucket_exists:
                print(f"✅ Bucket '{bucket_name}' already exists")
            else:
                # Create bucket
                print(f"📦 Creating bucket '{bucket_name}'...")
                supabase.storage.create_bucket(
                    name=bucket_name,
                    public=True,  # Make bucket public for video access
                    file_size_limit=52428800,  # 50MB limit
                    allowed_mime_types=['video/mp4', 'video/webm', 'video/avi', 'image/png', 'image/jpeg', 'application/pdf']
                )
                print(f"✅ Bucket '{bucket_name}' created successfully")
        
        except Exception as e:
            print(f"❌ Error checking/creating bucket: {e}")
            return False
        
        # Create storage policies (if using RLS)
        print("🔐 Setting up storage policies...")
        
        # Policy for public read access to videos
        try:
            # This would require SQL execution - for now, we'll use public bucket
            print("ℹ️  Using public bucket for video access")
            print("ℹ️  For production, consider setting up Row Level Security (RLS) policies")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not set up storage policies: {e}")
            print("ℹ️  Videos will still be accessible via public URLs")
        
        print("\n🎉 Supabase Storage setup completed!")
        print(f"📁 Videos will be stored in bucket: {bucket_name}")
        print(f"🌐 Public URLs will be available for video playback")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up Supabase Storage: {e}")
        return False

def test_upload():
    """Test uploading a small file to verify setup"""
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "books")
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Create a test file
        test_content = b"Test video file content"
        test_filename = "test_video.mp4"
        
        print(f"🧪 Testing upload to bucket '{bucket_name}'...")
        
        # Upload test file
        supabase.storage.from_(bucket_name).upload(
            path=f"videos/{test_filename}",
            file=test_content,
            file_options={"content-type": "video/mp4"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(f"videos/{test_filename}")
        
        print(f"✅ Test upload successful!")
        print(f"🔗 Test file URL: {public_url}")
        
        # Clean up test file
        supabase.storage.from_(bucket_name).remove([f"videos/{test_filename}"])
        print("🧹 Test file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Test upload failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Supabase Storage Setup for Litink App")
    print("=" * 50)
    
    # Setup storage
    if setup_supabase_storage():
        print("\n" + "=" * 50)
        
        # Test upload
        test_response = input("\n🧪 Would you like to test the upload functionality? (y/n): ")
        if test_response.lower() in ['y', 'yes']:
            test_upload()
        
        print("\n✅ Setup completed successfully!")
        print("\n📝 Next steps:")
        print("1. Make sure your .env file has the correct Supabase credentials")
        print("2. Videos will now be uploaded to Supabase Storage instead of local files")
        print("3. Frontend can access videos via public URLs")
        
    else:
        print("\n❌ Setup failed. Please check your Supabase credentials and try again.")
        sys.exit(1) 