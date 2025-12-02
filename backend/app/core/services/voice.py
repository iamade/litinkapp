import httpx
from typing import List, Dict, Any, Optional
import asyncio
from app.core.config import settings


class VoiceService:
    """Voice generation service using ElevenLabs API"""
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def generate_speech(
        self, 
        text: str, 
        character_voice: Dict[str, Any], 
        emotion: str = "neutral"
    ) -> Optional[str]:
        """Generate speech audio from text"""
        if not self.api_key:
            return await self._mock_generate_speech(text, character_voice, emotion)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{character_voice['voice_id']}",
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.api_key
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.75,
                            "similarity_boost": 0.75,
                            "style": self._get_emotion_style(emotion),
                            "use_speaker_boost": True
                        }
                    }
                )
                
                if response.status_code == 200:
                    # In a real implementation, you would save the audio file
                    # and return a URL to access it
                    audio_filename = f"audio_{hash(text)}.mp3"
                    # Save audio_content to file storage
                    return f"/audio/{audio_filename}"
                else:
                    print(f"ElevenLabs API error: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"Voice service error: {e}")
            return None
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices"""
        if not self.api_key:
            return self._get_mock_voices()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "id": voice["voice_id"],
                            "name": voice["name"],
                            "description": voice.get("description", ""),
                            "voice_id": voice["voice_id"],
                            "personality": voice.get("labels", {}).get("accent", "neutral")
                        }
                        for voice in data.get("voices", [])
                    ]
                else:
                    return self._get_mock_voices()
                    
        except Exception as e:
            print(f"Voice service error: {e}")
            return self._get_mock_voices()
    
    def _get_emotion_style(self, emotion: str) -> float:
        """Convert emotion to style value"""
        emotion_map = {
            "neutral": 0.5,
            "excited": 0.8,
            "sad": 0.2,
            "angry": 0.9,
            "calm": 0.3,
            "mysterious": 0.6
        }
        return emotion_map.get(emotion, 0.5)
    
    async def _mock_generate_speech(
        self, 
        text: str, 
        character_voice: Dict[str, Any], 
        emotion: str
    ) -> str:
        """Mock speech generation for development"""
        # Simulate processing time
        await asyncio.sleep(1)
        
        # Return a mock audio URL
        return f"/mock-audio/{hash(text)}.mp3"
    
    def _get_mock_voices(self) -> List[Dict[str, Any]]:
        """Return mock voice data"""
        return [
            {
                "id": "narrator",
                "name": "Narrator",
                "description": "Professional storytelling voice",
                "voice_id": "narrator_voice_id",
                "personality": "authoritative"
            },
            {
                "id": "character1",
                "name": "Hero",
                "description": "Young, adventurous character",
                "voice_id": "hero_voice_id",
                "personality": "enthusiastic"
            },
            {
                "id": "character2",
                "name": "Wise Mentor",
                "description": "Elderly, wise character",
                "voice_id": "mentor_voice_id",
                "personality": "calm"
            }
        ]