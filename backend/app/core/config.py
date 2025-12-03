from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, ClassVar, Dict, Literal
import os


class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    model_config = SettingsConfigDict(
        env_file="../../.envs/.env.local", env_ignore_empty=True, extra="ignore"
    )

    # Basic settings
    API_V1_STR: str = ""
    PROJECT_NAME: str = ""
    PROJECT_DESCRIPTION: str = ""
    SITE_NAME: str = ""
    VERSION: str = ""
    # ENVIRONMENT: str = "development"
    DEBUG: bool = True

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
        "https://litinkapp.netlify.app",
    ]

    @property
    def get_allowed_hosts(self) -> List[str]:
        """Get allowed hosts from environment or use defaults"""
        env_hosts = os.getenv("ALLOWED_HOSTS")
        if env_hosts:
            return [host.strip() for host in env_hosts.split(",")]
        return self.ALLOWED_HOSTS

    # Frontend URL for redirects
    FRONTEND_URL: str = (
        "http://localhost:5173"
        if ENVIRONMENT == "development"
        else "https://www.litinkai.com"
    )

    # Postgres Configuration
    DATABASE_URL: str = ""

    # Redis

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}"

    # Rabbitmq
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

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
    MAIL_FROM: str = ""
    MAIL_FROM_NAME: str = ""
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    MAILPIT_UI_PORT: int = 8025

    # Mailgun Configuration (Production)
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None
    MAILGUN_SENDER_EMAIL: str = "noreply@litinkai.com"
    MAILGUN_SENDER_NAME: str = "Litink"
    MAILGUN_SENDER_EMAIL: str = "noreply@litink.com"

    # Legacy / FastAPI-Mail support
    MAIL_FROM: str = "noreply@litink.com"
    MAIL_FROM_NAME: str = "Litink"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025

    FRONTEND_URL: str = "http://localhost:3000"

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
        "enterprise": 1000,
    }

    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # MinIO / S3 Storage Configuration
    USE_MINIO: bool = True  # Use MinIO in development, S3 in production
    MINIO_ENDPOINT: str = "http://minio:9000"  # MinIO server endpoint
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "litink-books"
    MINIO_SECURE: bool = False  # Use HTTP in development

    # S3 Configuration (for production)
    S3_ENDPOINT: Optional[str] = None  # AWS S3 or S3-compatible endpoint
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "litink-books-prod"
    S3_REGION: str = "us-east-1"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Book processing limits
    MAX_CHUNKS_PER_BOOK: int = 50  # Back to original limit
    MIN_CHUNK_SIZE: int = 1000  # Minimum chunk size in characters
    MAX_CHUNK_SIZE: int = 15000  # Maximum chunk size in characters
    AI_TIMEOUT_SECONDS: int = 30  # Timeout for AI API calls
    MAX_CHAPTERS_PER_BOOK: int = 50  # Increased to support books with up to 50 chapters

    # Kling AI API key
    # KLINGAI_API_KEY: str = os.getenv("KLINGAI_API_KEY", "")
    KLINGAI_ACCESS_KEY_ID: str = os.getenv("KLINGAI_ACCESS_KEY_ID", "")
    KLINGAI_ACCESS_KEY_SECRET: str = os.getenv("KLINGAI_ACCESS_KEY_SECRET", "")

    # ModelsLab
    MODELSLAB_API_KEY: str = os.getenv("MODELSLAB_API_KEY", "")
    # MODELSLAB_V6_BASE_URL: str = "https://modelslab.com/api/v6"
    MODELSLAB_BASE_URL: str = "https://modelslab.com/api/v7"  # Updated to v7

    # OTP_EXPIRATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5
    LOGIN_ATTEMPTS: int = 3
    LOCKOUT_DURATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5
    ACTIVATION_TOKEN_EXPIRATION_MINUTES: int = 2 if ENVIRONMENT == "development" else 5

    API_BASE_URL: str = ""
    SUPPORT_EMAIL: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRATION_MINUTES: int = (
        30 if ENVIRONMENT == "development" else 15
    )
    JWT_REFRESH_TOKEN_EXPIRATION_DAYS: int = 1
    COOKIE_SECURE: bool = False if ENVIRONMENT == "development" else True
    COOKIE_ACCESS_NAME: str = "access_token"
    COOKIE_REFRESH_NAME: str = "refresh_token"
    COOKIE_LOGGED_IN_NAME: str = "logged_in"

    COOKIE_HTTP_ONLY: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    COOKIE_PATH: str = "/"
    SIGNING_KEY: str = ""
    PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES: int = (
        3 if ENVIRONMENT == "development" else 5
    )

    #  # Security
    # SECRET_KEY: str = "your-secret-key-change-in-production"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # ALGORITHM: str = "HS256"

    # class Config:
    #     env_file = ".env"
    #     case_sensitive = True
    #     extra = "ignore"


settings = Settings()
