from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

async def init_db():
    """Initialize database connection"""
    try:
        # Test connection by fetching a simple query
        response = supabase.table('profiles').select('id').limit(1).execute()
        logger.info("Supabase connection established successfully")
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        raise

def get_supabase() -> Client:
    """Get Supabase client instance"""
    return supabase