from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, ClassVar, Dict, Literal
import os


class Settings(BaseSettings):
    ENVIRONMENT: Literal["development","staging","production"] = "development"
    
    model_config = SettingsConfigDict(
        env_file="../../.envs/.env.local",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    # Basic settings
    API_V1_STR: str = ""
    PROJECT_NAME: str = ""
    PROJECT_DESCRIPTION: str = ""
    SITE_NAME: str = ""
    VERSION: str = ""
    # ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    
    # CORS PRODUCTION
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5173", 
        "https://localhost:5173",
        "https://litinkai.com",
        "https://www.litinkai.com",
        "https://www.litink.com",
        "https://litink.com",
        "https://teal-crostata-10b809.netlify.app",
        "https://litinkapp.netlify.app"
    ]
    
    @property
    def get_allowed_hosts(self) -> List[str]:
        """Get allowed hosts from environment or use defaults"""
        env_hosts = os.getenv("ALLOWED_HOSTS")
        if env_hosts:
            return [host.strip() for host in env_hosts.split(",")]
        return self.ALLOWED_HOSTS
    
    # Frontend URL for redirects
    FRONTEND_URL: str = "http://localhost:5173" if ENVIRONMENT == "development" else "https://www.litinkai.com"
    
    # Supabase Configuration (Primary Database)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str =""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_BUCKET_NAME: str = "books"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    TAVUS_API_KEY: Optional[str] = None
    PLOTDRIVE_API_KEY: Optional[str] = None

    # ✅ NEW: DeepSeek Configuration
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"  # Non-thinking mode
    DEEPSEEK_REASONER_MODEL: str = "deepseek-reasoner"  # Thinking mode

    # ✅ NEW: OpenRouter Configuration
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    
    # Blockchain
    ALGORAND_TOKEN: Optional[str] = None
    ALGORAND_SERVER: str = "https://testnet-api.algonode.cloud"
    ALGORAND_INDEXER: str = "https://testnet-idx.algonode.cloud"
    CREATOR_MNEMONIC: Optional[str] = None
    
    # Email Configuration
    MAIL_SERVICE: str = "mailpit"  # mailpit for dev, mailgun for production

    # Mailpit Configuration (Development)
    MAILPIT_SMTP_HOST: str = "localhost"
    MAILPIT_SMTP_PORT: int = 1025
    MAILPIT_WEB_UI_PORT: int = 8025

    # Mailgun Configuration (Production)
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None
    MAILGUN_SENDER_EMAIL: str = "noreply@litinkai.com"
    MAILGUN_SENDER_NAME: str = "Litink"

    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None

    # Stripe Price IDs for subscription tiers
    STRIPE_FREE_PRICE_ID: Optional[str] = None
    STRIPE_BASIC_PRICE_ID: Optional[str] = None
    STRIPE_STANDARD_PRICE_ID: Optional[str] = None
    STRIPE_PREMIUM_PRICE_ID: Optional[str] = None
    STRIPE_PROFESSIONAL_PRICE_ID: Optional[str] = None
    STRIPE_PRO_PRICE_ID: Optional[str] = None  # Keep for backward compatibility

    # Rate Limiting per Tier (requests per minute)
    RATE_LIMITS: ClassVar[Dict[str, int]] = {
        "free": 10,
        "basic": 30,
        "standard": 60,
        "premium": 120,
        "professional": 300,
        "enterprise": 1000
    }
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Book processing limits
    MAX_CHUNKS_PER_BOOK: int = 50  # Back to original limit
    MIN_CHUNK_SIZE: int = 1000     # Minimum chunk size in characters
    MAX_CHUNK_SIZE: int = 15000    # Maximum chunk size in characters
    AI_TIMEOUT_SECONDS: int = 30   # Timeout for AI API calls
    MAX_CHAPTERS_PER_BOOK: int = 50  # Increased to support books with up to 50 chapters
    
    # Kling AI API key
    # KLINGAI_API_KEY: str = os.getenv("KLINGAI_API_KEY", "")
    KLINGAI_ACCESS_KEY_ID: str = os.getenv("KLINGAI_ACCESS_KEY_ID", "")
    KLINGAI_ACCESS_KEY_SECRET: str = os.getenv("KLINGAI_ACCESS_KEY_SECRET", "")
    
     # ModelsLab
    MODELSLAB_API_KEY: str = os.getenv("MODELSLAB_API_KEY", "")
    # MODELSLAB_V6_BASE_URL: str = "https://modelslab.com/api/v6"
    MODELSLAB_BASE_URL: str = "https://modelslab.com/api/v7"  # Updated to v7
    
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()