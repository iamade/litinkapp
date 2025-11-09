import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
from sqlalchemy import text
from backend.app.tasks.celery_app import celery_app
from backend.app.core.logging import get_logger
from backend.app.core.database import get_supabase

logger = get_logger()

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "healthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    DOWN = "down"
    
class HealthCheck:
    def __init__(self):
        self._services: Dict[str, ServiceStatus] = {}
        self._check_functions: Dict[str, Callable[[], Awaitable[bool]]] = {}
        self._last_check: Dict[str,datetime] = {}
        self._timeouts: Dict[str,float] = {}
        self._retry_delays: Dict[str, float] = {}
        self._max_retries: Dict[str,int] = {}
        self._lock = asyncio.Lock()
        self._dependencies: Dict[str,set[str]] = {}
        
        self._cache_duration: timedelta = timedelta(seconds=25)
        self._cache_status: Optional[Dict[str,Any]] = None
        self._last_check_time: Optional[datetime] = None
    
    async def validate_dependencies(self, service_name: str, depends_on: list[str]) -> None:
        if not depends_on:
            return
        
        for dep in depends_on:
            if dep not in self._services:
                raise ValueError(
                    f"Dependency '{dep}' not registered for service' {service_name}'"
                )
        
    async def add_service(
        self,service_name: str, check_function: Callable[[], Awaitable[bool]], timeout: float=5.0,
        retry_delay: float = 1.0, max_retries: int = 3, depends_on: list[str] | None = None
    )-> None:
        self._services[service_name] = ServiceStatus.STARTING
        self._check_functions[service_name] = check_function
        self._timeouts[service_name] = timeout
        self._retry_delays[service_name] = retry_delay
        self._max_retries[service_name] = max_retries
        self._last_check[service_name] = datetime.now(timezone.utc)
        
        if depends_on:
            await self.validate_dependencies(service_name, depends_on)
            self._dependencies[service_name] = set(depends_on)
            logger.info(
                f"Service '{service_name}' registered with dependencies: {depends_on}"
            )
    
    async def check_redis(self)-> bool:
        try:
            redis_client = celery_app.backend.client
            redis_client.ping()
            self._last_check["redis"] = datetime.now(timezone.utc)
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
        
    """Health check for Supabase database and API"""
    async def check_supabase(self) -> bool:
        try:
            
            supabase = get_supabase()
            
            # Test database connection via Supabase API
            response = supabase.table('profiles').select('id').limit(1).execute()
            
            self._last_check["supabase"] = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False