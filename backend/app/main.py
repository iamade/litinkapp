from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import api_router
from app.core.auth import get_current_user
from app.services.redis_service import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    await redis_client.connect()
    yield
    # Shutdown
    await redis_client.disconnect()


app = FastAPI(
    title="Litink API",
    description="AI-powered interactive book platform backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware - Updated for production with comprehensive origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # "http://localhost:3000",
        # "http://localhost:5173", 
        # "https://localhost:5173",
        "https://www.litinkai.com",
        "https://litinkai.com",
        "https://litink.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Uploads directory for generated content (fallback for local files)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Litink API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if redis_client.is_connected else "disconnected"
    }


if __name__ == "__main__":
    if os.getenv("ENVIRONMENT") == "development":
        import debugpy
        debugpy.listen(("0.0.0.0", 5678))
        print("🐛 Debug server listening on port 5678...")
        print("Waiting for debugger to attach...")
        # debugpy.wait_for_client()  # Uncomment to wait for debugger
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )