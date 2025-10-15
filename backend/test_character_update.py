"""
Test script to verify character image_url update works
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

# Test character ID from your example
character_id = "2abb3425-1b0b-4e2d-bc19-0e00e205805e"

print(f"Testing update for character: {character_id}")

# First, read the current character data
print("\n1. Reading current character data...")
result = supabase.table("characters").select("*").eq("id", character_id).execute()
print(f"Current character data: {result.data}")

# Try to update with a test image URL
print("\n2. Attempting to update image_url...")
test_image_url = "https://test.com/test-image.png"
update_data = {
    "image_url": test_image_url,
    "image_generation_prompt": "Test prompt",
    "image_metadata": {"test": "metadata"}
}

try:
    update_result = supabase.table("characters").update(update_data).eq("id", character_id).execute()
    print(f"Update result: {update_result}")
    print(f"Updated successfully: {update_result.data}")
except Exception as e:
    print(f"Update failed with error: {e}")
    print(f"Error type: {type(e).__name__}")

# Read again to verify
print("\n3. Reading character data after update...")
verify_result = supabase.table("characters").select("*").eq("id", character_id).execute()
print(f"Character data after update: {verify_result.data}")

if verify_result.data and verify_result.data[0].get("image_url") == test_image_url:
    print("\n✅ SUCCESS: image_url was updated correctly!")
else:
    print("\n❌ FAILED: image_url was NOT updated")
    print(f"Expected: {test_image_url}")
    print(f"Got: {verify_result.data[0].get('image_url') if verify_result.data else 'No data'}")
