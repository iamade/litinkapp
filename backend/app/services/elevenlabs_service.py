import httpx
import asyncio
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings
import traceback
import time


class ElevenLabsService:
    """Enhanced ElevenLabs service for advanced audio features"""
    
    def __init__(self, supabase_client=None):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.audio_dir = "uploads/audio"
        self.supabase_client = supabase_client
        self.supabase_bucket_name = settings.SUPABASE_BUCKET_NAME
        
        # Ensure audio directory exists
        os.makedirs(self.audio_dir, exist_ok=True)
    
    async def generate_enhanced_speech(
        self, 
        text: str, 
        voice_id: str = "21m00Tcm4TlvDq8ikWAM", 
        user_id: str = None,
        emotion: str = "neutral",
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Generate enhanced speech with ElevenLabs API"""
        try:
            # Generate audio with emotion and speed settings
            audio_data = await self._generate_speech_with_settings(text, voice_id, emotion, speed)
            
            if not audio_data:
                return {"audio_url": None, "error": "Failed to generate audio"}
            
            # Save audio to local file
            timestamp = int(time.time())
            audio_filename = f"speech_{timestamp}.mp3"
            audio_path = os.path.join(self.audio_dir, audio_filename)
            
            with open(audio_path, "wb") as f:
                f.write(audio_data)
            
            # Upload to Supabase Storage with user organization
            if user_id:
                storage_path = f"users/{user_id}/audio/{audio_filename}"
            else:
                storage_path = f"audio/{audio_filename}"
            
            with open(audio_path, "rb") as f:
                self.supabase_client.storage.from_(self.supabase_bucket_name).upload(
                    path=storage_path,
                    file=f.read(),
                    file_options={"content-type": "audio/mpeg"}
                )
            
            # Get public URL
            public_url = self.supabase_client.storage.from_(self.supabase_bucket_name).get_public_url(storage_path)
            
            # Clean up local file
            os.remove(audio_path)
            
            return {"audio_url": public_url, "local_path": audio_path}
            
        except Exception as e:
            print(f"Error in generate_enhanced_speech: {e}")
            return {"audio_url": None, "error": str(e)}
    

    async def generate_audio_narration(
        self, 
        text: str, 
        background_music: str = "ambient",
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        user_id: str = None
    ) -> Optional[str]:
        """Generate complete audio narration with background music"""
        try:
            # Generate main narration
            narration_result = await self.generate_enhanced_speech(text, voice_id, user_id)
            
            if not narration_result or not narration_result.get("audio_url"):
                return None
            
            # For now, return the narration without background music
            # In a full implementation, you would mix with background music
            return narration_result["audio_url"]
            
        except Exception as e:
            print(f"Error generating audio narration: {e}")
            return None

    async def generate_sound_effect(
        self, 
        effect_type: str, 
        duration: float = 2.0, 
        intensity: str = "medium",
        user_id: str = None
    ) -> Optional[str]:
        """Generate sound effects and upload to Supabase Storage"""
        try:
            # For now, use a placeholder sound effect
            # In a real implementation, you would generate actual sound effects
            placeholder_text = f"Sound effect: {effect_type} at {intensity} intensity for {duration} seconds"
            
            # Generate a simple audio representation
            result = await self.generate_enhanced_speech(placeholder_text, "21m00Tcm4TlvDq8ikWAM", user_id)
            
            if result and result.get("audio_url"):
                return result["audio_url"]
            else:
                # Fallback to a public CDN sound effect
                return f"https://example.com/sound-effects/{effect_type}_{intensity}.mp3"
                
        except Exception as e:
            print(f"Error generating sound effect: {e}")
            return None

    async def generate_sound_effects(
        self, 
        effect_type: str, 
        duration: int = 3,
        intensity: float = 0.5,
        user_id: str = None
    ) -> Optional[str]:
        """Generate sound effects using ElevenLabs (if available) or return placeholder"""
        try:
            # For now, return placeholder sound effects
            # In a real implementation, you might use ElevenLabs' sound generation features
            # or integrate with other sound effect services
            
            effect_mapping = {
                "ambient": "ambient_background",
                "action": "action_sequence",
                "emotional": "emotional_moment",
                "transition": "scene_transition",
                "magical": "magical_effect",
                "nature": "nature_sounds"
            }
            
            effect_name = effect_mapping.get(effect_type, "generic")
            audio_filename = f"sfx_{effect_name}_{duration}s.mp3"
            
            # Generate a simple audio representation
            placeholder_text = f"Sound effect: {effect_type} at {intensity} intensity for {duration} seconds"
            result = await self.generate_enhanced_speech(placeholder_text, "21m00Tcm4TlvDq8ikWAM", user_id)
            
            if result and result.get("audio_url"):
                return result["audio_url"]
            else:
                # Return placeholder path - in real implementation, generate actual audio
                return f"/uploads/audio/{audio_filename}"
            
        except Exception as e:
            print(f"Error generating sound effects: {e}")
            return None
    
    async def mix_audio_tracks(self, audio_tracks: List[Dict[str, Any]], user_id: str = None) -> Dict[str, Any]:
        """Mix multiple audio tracks together"""
        try:
            if not audio_tracks:
                return {"audio_url": None, "error": "No audio tracks provided"}
            
            # Download and mix audio files
            mixed_audio_path = await self._download_and_mix_audio(audio_tracks)
            
            if not mixed_audio_path or not os.path.exists(mixed_audio_path):
                return {"audio_url": None, "error": "Failed to create mixed audio"}
            
            # Upload to Supabase Storage with user organization
            timestamp = int(time.time())
            mixed_filename = f"mixed_audio_{timestamp}.mp3"
            
            if user_id:
                storage_path = f"users/{user_id}/audio/{mixed_filename}"
            else:
                storage_path = f"audio/{mixed_filename}"
            
            with open(mixed_audio_path, "rb") as f:
                self.supabase_client.storage.from_(self.supabase_bucket_name).upload(
                    path=storage_path,
                    file=f.read(),
                    file_options={"content-type": "audio/mpeg"}
                )
            
            # Get public URL
            public_url = self.supabase_client.storage.from_(self.supabase_bucket_name).get_public_url(storage_path)
            
            # Clean up local file
            os.remove(mixed_audio_path)
            
            return {"audio_url": public_url, "local_path": mixed_audio_path}
            
        except Exception as e:
            print(f"Error in mix_audio_tracks: {e}")
            return {"audio_url": None, "error": str(e)}
    

    async def create_audio_narration(self, text: str, narrator_style: str = "narration", background_music: Optional[str] = None, user_id: str = None) -> dict:
        try:
            # Use narrator_style to get voice settings
            voice_settings = self._get_narrator_voice_settings(narrator_style)
            
            # Generate main narration
            narration_result = await self.generate_enhanced_speech(
                text=text,
                voice_id=voice_settings["voice_id"],
                user_id=user_id
            )
            
            if not narration_result or not narration_result.get("audio_url"):
                return None
            
            # Mix with background music if provided
            if background_music:
                mixed_audio = await self.mix_audio_tracks(
                    audio_tracks=[{"url": narration_result["audio_url"]}, {"url": background_music}],
                    user_id=user_id
                )
                return mixed_audio
            
            return narration_result["audio_url"]
            
        except Exception as e:
            print(f"❌ ElevenLabs create_audio_narration error: {e}")
            print(traceback.format_exc())
            return None

    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices with enhanced metadata"""
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
                            "voice_id": voice["voice_id"],
                            "name": voice["name"],
                            "description": voice.get("description", ""),
                            "category": voice.get("category", "general"),
                            "labels": voice.get("labels", {}),
                            "preview_url": voice.get("preview_url", ""),
                            "personality": self._extract_personality(voice.get("labels", {}))
                        }
                        for voice in data.get("voices", [])
                    ]
                else:
                    return self._get_mock_voices()
                    
        except Exception as e:
            print(f"Error fetching voices: {e}")
            return self._get_mock_voices()

    async def list_voices(self) -> List[Dict[str, Any]]:
        """Alias for get_available_voices for compatibility"""
        return await self.get_available_voices()
    
    def _get_emotion_style(self, emotion: str) -> float:
        """Map emotion to ElevenLabs style parameter (numeric value)"""
        emotion_styles = {
            "neutral": 0.5,
            "happy": 0.8,
            "sad": 0.2,
            "angry": 0.9,
            "excited": 0.8,
            "calm": 0.3,
            "mysterious": 0.6,
            "professional": 0.5,
            "friendly": 0.7,
            "wise": 0.4,
            "confident": 0.8,
            "intense": 0.9,
            "cheerful": 0.8,
            "melancholic": 0.2,
            "energetic": 0.8,
            "serene": 0.3
        }
        return emotion_styles.get(emotion, 0.5)
    
    
    
    def _get_narrator_voice_settings(self, narrator_style: str) -> Dict[str, Any]:
        """Get voice settings for narrator"""
        # Use a real ElevenLabs voice ID or fall back to mock
        # Real ElevenLabs voice IDs are long alphanumeric strings
        # For now, use a common default voice ID
        default_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
        style_mapping = {
            "professional": {"emotion": "professional", "speed": 1.0, "voice_id": default_voice_id},
            "storyteller": {"emotion": "mysterious", "speed": 0.9, "voice_id": default_voice_id},
            "friendly": {"emotion": "friendly", "speed": 1.1, "voice_id": default_voice_id},
            "dramatic": {"emotion": "intense", "speed": 0.8, "voice_id": default_voice_id}
        }
        
        return style_mapping.get(narrator_style, style_mapping["professional"])
    
    
    def _extract_personality(self, labels: Dict[str, str]) -> str:
        """Extract personality from voice labels"""
        personality_indicators = ["accent", "age", "gender", "personality"]
        for indicator in personality_indicators:
            if indicator in labels:
                return labels[indicator]
        return "neutral"
    
    async def _mock_generate_speech(self, text: str, voice_id: str, emotion: str) -> str:
        """Mock speech generation for development"""
        await asyncio.sleep(1)
        audio_filename = f"mock_speech_{hash(text)}.mp3"
        return f"/uploads/audio/{audio_filename}"
    
    
    def _get_mock_voices(self) -> List[Dict[str, Any]]:
        """Return mock voice data"""
        return [
            {
                "voice_id": "narrator_professional",
                "name": "Professional Narrator",
                "description": "Clear and authoritative voice for educational content",
                "category": "narrator",
                "personality": "professional"
            },
            {
                "voice_id": "narrator_storyteller",
                "name": "Storyteller Narrator",
                "description": "Warm and engaging voice for storytelling",
                "category": "narrator",
                "personality": "mysterious"
            },
            {
                "voice_id": "narrator_friendly",
                "name": "Friendly Narrator",
                "description": "Approachable and conversational voice",
                "category": "narrator",
                "personality": "friendly"
            }
        ]

    async def _generate_speech_with_settings(
        self, 
        text: str, 
        voice_id: str, 
        emotion: str = "neutral", 
        speed: float = 1.0
    ) -> Optional[bytes]:
        """Generate speech with emotion and speed settings"""
        if not self.api_key:
            return None
        
        try:
            # Map emotion to style parameter
            style = self._get_emotion_style(emotion)
            
            # Prepare request with emotion and speed settings
            request_data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75,
                    "style": style,
                    "use_speaker_boost": True,
                    "speaking_rate": speed
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.api_key
                    },
                    json=request_data
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"ElevenLabs API error: {response.status_code}")
                    print(f"Response content: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error in _generate_speech_with_settings: {e}")
            return None

    async def _generate_speech(self, text: str, voice_id: str) -> Optional[bytes]:
        """Generate speech using ElevenLabs API"""
        if not self.api_key:
            return None
        
        try:
            # Validate input parameters
            if not text or not text.strip():
                print("Warning: Empty text provided to _generate_speech")
                return None
            
            if not voice_id:
                print("Warning: No voice_id provided to _generate_speech")
                return None
            
            # Truncate text if too long (ElevenLabs has limits)
            if len(text) > 2500:
                text = text[:2500] + "..."
                print(f"Warning: Text truncated to {len(text)} characters")
            
            request_data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75,
                    "use_speaker_boost": True
                }
            }
            
            print(f"ElevenLabs request - voice_id: {voice_id}, text_length: {len(text)}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.api_key
                    },
                    json=request_data
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    print(f"ElevenLabs API error: {response.status_code}")
                    print(f"Response content: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"Error in _generate_speech: {e}")
            return None

    async def _download_and_mix_audio(self, audio_tracks: List[Dict[str, Any]]) -> Optional[str]:
        """Download and mix audio tracks"""
        try:
            # For now, return the first audio track as a simple implementation
            # In a real implementation, you would use audio processing libraries
            # like pydub or ffmpeg to mix the audio tracks
            
            if not audio_tracks:
                return None
            
            first_track = audio_tracks[0]
            audio_url = first_track.get("audio_url")
            
            if not audio_url:
                return None
            
            # Download the audio file
            async with httpx.AsyncClient() as client:
                response = await client.get(audio_url)
                if response.status_code == 200:
                    # Save to temporary file
                    timestamp = int(time.time())
                    mixed_filename = f"mixed_audio_{timestamp}.mp3"
                    mixed_path = os.path.join(self.audio_dir, mixed_filename)
                    
                    with open(mixed_path, "wb") as f:
                        f.write(response.content)
                    
                    return mixed_path
            
            return None
            
        except Exception as e:
            print(f"Error in _download_and_mix_audio: {e}")
            return None 