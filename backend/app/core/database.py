from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


def _get_environment_info() -> str:
    """Get human-readable environment information"""
    if "127.0.0.1" in settings.SUPABASE_URL or "localhost" in settings.SUPABASE_URL:
        return "LOCAL"
    elif "supabase.co" in settings.SUPABASE_URL:
        return "CLOUD"
    else:
        return "UNKNOWN"


# Initialize Supabase client
logger.info(f"Initializing Supabase client for {_get_environment_info()} environment")
logger.info(f"Supabase URL: {settings.SUPABASE_URL}")
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

async def init_db():
    """Initialize database connection"""
    try:
        # Test connection by fetching a simple query
        response = supabase.table('profiles').select('id').limit(1).execute()
        logger.info(f"Supabase connection established successfully ({_get_environment_info()} environment)")
    except Exception as e:
        logger.error(f"Supabase connection failed ({_get_environment_info()} environment): {e}")
        raise

def get_supabase() -> Client:
    """Get Supabase client instance"""
    return supabase