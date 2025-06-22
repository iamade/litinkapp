from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic settings
    PROJECT_NAME: str = "Litink API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://localhost:5173"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres.rsatunfeautnsltfvxse:litink123@aws-0-ca-central-1.pooler.supabase.com:5432/litink"
    
    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None
    TAVUS_API_KEY: Optional[str] = None
    
    # Blockchain
    ALGORAND_TOKEN: Optional[str] = None
    ALGORAND_SERVER: str = "https://testnet-api.algonode.cloud"
    ALGORAND_INDEXER: str = "https://testnet-idx.algonode.cloud"
    CREATOR_MNEMONIC: Optional[str] = None
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()