import httpx
from typing import List, Dict, Any, Optional
import asyncio
from app.core.config import settings


class VideoService:
    """Video generation service using Tavus API"""
    
    def __init__(self):
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = "https://api.tavus.io/v2"
    
    async def generate_story_scene(
        self,
        scene_description: str,
        dialogue: str,
        avatar_style: str = "realistic"
    ) -> Optional[Dict[str, Any]]:
        """Generate video scene for story"""
        if not self.api_key:
            return await self._mock_generate_scene(scene_description, dialogue)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/videos",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "script": dialogue,
                        "avatar_id": self._get_avatar_id(avatar_style),
                        "background": "fantasy",
                        "voice_settings": {
                            "voice_id": "default",
                            "stability": 0.75,
                            "similarity_boost": 0.75
                        },
                        "video_settings": {
                            "quality": "high",
                            "format": "mp4"
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    video_id = data.get("video_id")
                    
                    # Poll for completion
                    return await self._poll_video_status(video_id, scene_description)
                else:
                    print(f"Tavus API error: {response.status_code}")
                    return await self._mock_generate_scene(scene_description, dialogue)
                    
        except Exception as e:
            print(f"Video service error: {e}")
            return await self._mock_generate_scene(scene_description, dialogue)
    
    async def get_available_avatars(self) -> List[Dict[str, Any]]:
        """Get available avatars"""
        if not self.api_key:
            return self._get_mock_avatars()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/avatars",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "avatar_id": avatar["avatar_id"],
                            "name": avatar.get("name", "Avatar"),
                            "style": avatar.get("style", "realistic"),
                            "voice_id": avatar.get("voice_id", "default")
                        }
                        for avatar in data.get("avatars", [])
                    ]
                else:
                    return self._get_mock_avatars()
                    
        except Exception as e:
            print(f"Video service error: {e}")
            return self._get_mock_avatars()
    
    async def _poll_video_status(self, video_id: str, scene_description: str) -> Dict[str, Any]:
        """Poll video generation status"""
        max_attempts = 30  # 5 minutes max
        attempt = 0
        
        while attempt < max_attempts:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/videos/{video_id}",
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("status") == "completed":
                            return {
                                "id": video_id,
                                "title": scene_description,
                                "description": "AI-generated story scene",
                                "video_url": data.get("download_url"),
                                "thumbnail_url": data.get("thumbnail_url"),
                                "duration": data.get("duration", 30),
                                "status": "ready"
                            }
                        elif data.get("status") == "failed":
                            break
                
                # Wait 10 seconds before next poll
                await asyncio.sleep(10)
                attempt += 1
                
            except Exception as e:
                print(f"Polling error: {e}")
                break
        
        # Return error or timeout result
        return {
            "id": video_id,
            "title": scene_description,
            "description": "Video generation failed or timed out",
            "status": "error"
        }
    
    def _get_avatar_id(self, style: str) -> str:
        """Get avatar ID based on style"""
        avatar_map = {
            "realistic": "realistic_avatar_id",
            "animated": "animated_avatar_id",
            "cartoon": "cartoon_avatar_id"
        }
        return avatar_map.get(style, "realistic_avatar_id")
    
    async def _mock_generate_scene(self, scene_description: str, dialogue: str) -> Dict[str, Any]:
        """Mock video generation for development"""
        # Simulate processing time
        await asyncio.sleep(3)
        
        return {
            "id": f"scene_{hash(scene_description)}",
            "title": scene_description,
            "description": "AI-generated story scene (Demo)",
            "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "thumbnail_url": "https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=400",
            "duration": 30,
            "status": "ready"
        }
    
    def _get_mock_avatars(self) -> List[Dict[str, Any]]:
        """Return mock avatar data"""
        return [
            {
                "avatar_id": "narrator_avatar",
                "name": "Narrator",
                "style": "realistic",
                "voice_id": "professional"
            },
            {
                "avatar_id": "character_avatar",
                "name": "Character",
                "style": "animated",
                "voice_id": "young"
            },
            {
                "avatar_id": "mentor_avatar",
                "name": "Mentor",
                "style": "realistic",
                "voice_id": "wise"
            }
        ]