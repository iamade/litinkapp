import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
)

# Check Mrs. Dursley's record
character_id = "a08f1f97-056e-484f-b1f1-33c7beb182b2"
result = supabase.table("characters").select("id, name, image_url, image_generation_prompt, image_metadata, updated_at").eq("id", character_id).execute()

print("Mrs. Dursley's current data in database:")
print(result.data)
