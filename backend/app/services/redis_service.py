import redis.asyncio as redis
from typing import Optional, Any
import json
from app.core.config import settings


class RedisService:
    """Redis service for caching and session management"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.is_connected = True
            print("Redis connected successfully")
        except Exception as e:
            print(f"Redis connection error: {e}")
            self.is_connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
    
    async def set(self, key: str, value: Any, expire: int = 3600):
        """Set value in Redis with expiration"""
        if not self.is_connected:
            return False
        
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            await self.redis_client.set(key, serialized_value, ex=expire)
            return True
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.is_connected:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value.decode('utf-8')
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.is_connected:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    async def cache_quiz_result(self, user_id: str, quiz_id: str, result: dict):
        """Cache quiz result"""
        key = f"quiz_result:{user_id}:{quiz_id}"
        await self.set(key, result, expire=86400)  # 24 hours
    
    async def get_cached_quiz_result(self, user_id: str, quiz_id: str) -> Optional[dict]:
        """Get cached quiz result"""
        key = f"quiz_result:{user_id}:{quiz_id}"
        return await self.get(key)
    
    async def cache_ai_content(self, content_hash: str, ai_content: dict):
        """Cache AI-generated content"""
        key = f"ai_content:{content_hash}"
        await self.set(key, ai_content, expire=604800)  # 7 days
    
    async def get_cached_ai_content(self, content_hash: str) -> Optional[dict]:
        """Get cached AI content"""
        key = f"ai_content:{content_hash}"
        return await self.get(key)


# Global Redis client instance
redis_client = RedisService()