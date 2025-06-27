import httpx
import asyncio
import os
from typing import List, Dict, Any, Optional
from app.core.config import settings
import traceback


class ElevenLabsService:
    """Enhanced ElevenLabs service for advanced audio features"""
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.audio_dir = "uploads/audio"
        
        # Ensure audio directory exists
        os.makedirs(self.audio_dir, exist_ok=True)
    
    async def generate_enhanced_speech(
        self, 
        text: str, 
        voice_id: str,
        emotion: str = "neutral",
        speed: float = 1.0,
        stability: float = 0.75,
        similarity_boost: float = 0.75
    ) -> Optional[str]:
        """Generate enhanced speech with emotion and speed control, upload to Supabase, and return public URL"""
        if not self.api_key:
            return await self._mock_generate_speech(text, voice_id, emotion)
        
        try:
            # Validate input parameters
            if not text or not text.strip():
                print("Warning: Empty text provided to generate_enhanced_speech")
                return None
            
            if not voice_id:
                print("Warning: No voice_id provided to generate_enhanced_speech")
                return None
            
            # Truncate text if too long (ElevenLabs has limits)
            if len(text) > 2500:
                text = text[:2500] + "..."
                print(f"Warning: Text truncated to {len(text)} characters")
            
            request_data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                    "style": self._get_emotion_style(emotion),
                    "use_speaker_boost": True,
                    "speaking_rate": speed
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
                    # Save audio file
                    audio_filename = f"speech_{hash(text)}_{voice_id}.mp3"
                    audio_path = os.path.join(self.audio_dir, audio_filename)
                    
                    with open(audio_path, "wb") as f:
                        f.write(response.content)
                    
                    # Upload to Supabase and return public URL
                    if hasattr(self, 'supabase_service') and self.supabase_service:
                        public_url = await self.supabase_service.upload_file(audio_path)
                        return public_url
                    else:
                        print("[AUDIO UPLOAD ERROR] No supabase_service available to upload audio file.")
                        return None
                else:
                    print(f"ElevenLabs API error: {response.status_code}")
                    print(f"Response content: {response.text}")
                    # Fall back to mock generation
                    print("Falling back to mock speech generation")
                    return await self._mock_generate_speech(text, voice_id, emotion)
                    
        except Exception as e:
            print(f"❌ ElevenLabs generate_enhanced_speech error: {e}")
            print(traceback.format_exc())
            # Fall back to mock generation
            print("Falling back to mock speech generation due to exception")
            return await self._mock_generate_speech(text, voice_id, emotion)
    
    async def generate_character_voice(
        self,
        text: str,
        character_profile: Dict[str, Any],
        scene_context: str = ""
    ) -> Optional[str]:
        """Generate character-specific voice with personality"""
        if not self.api_key:
            return await self._mock_generate_character_voice(text, character_profile)
        
        try:
            # Get character voice settings
            voice_settings = self._get_character_voice_settings(character_profile)
            
            # Enhance text with character personality
            enhanced_text = await self._enhance_text_for_character(text, character_profile, scene_context)
            
            # Generate speech
            return await self.generate_enhanced_speech(
                text=enhanced_text,
                voice_id=voice_settings["voice_id"],
                emotion=voice_settings["emotion"],
                speed=voice_settings["speed"],
                stability=voice_settings["stability"],
                similarity_boost=voice_settings["similarity_boost"]
            )
            
        except Exception as e:
            print(f"Error generating character voice: {e}")
            return None
    
    async def generate_sound_effects(
        self, 
        effect_type: str, 
        duration: int = 3,
        intensity: float = 0.5
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
            
            # Return placeholder path - in real implementation, generate actual audio
            return f"/uploads/audio/{audio_filename}"
            
        except Exception as e:
            print(f"Error generating sound effects: {e}")
            return None
    
    async def mix_audio_tracks(
        self, 
        main_audio_path: Optional[str], 
        background_audio_path: Optional[str] = None,
        sound_effects: List[str] = []
    ) -> Optional[str]:
        """Mix multiple audio tracks together, upload to Supabase, and return public URL"""
        try:
            # Handle case where main_audio_path is None
            if not main_audio_path:
                print("Warning: main_audio_path is None, cannot mix audio tracks")
                return None
            
            # In a real implementation, you would use audio processing libraries
            # like pydub or ffmpeg to mix the audio tracks
            
            # For now, return the main audio path
            # This is a placeholder for actual audio mixing functionality
            
            if background_audio_path or sound_effects:
                # Create mixed audio filename
                mixed_filename = f"mixed_{hash(main_audio_path)}.mp3"
                mixed_path = os.path.join(self.audio_dir, mixed_filename)
                
                # Placeholder: in real implementation, mix the audio files
                # For now, just copy the main audio
                import shutil
                main_full_path = os.path.join(os.getcwd(), main_audio_path.lstrip('/'))
                if os.path.exists(main_full_path):
                    shutil.copy2(main_full_path, mixed_path)
                    # Upload to Supabase and return public URL
                    if hasattr(self, 'supabase_service') and self.supabase_service:
                        public_url = await self.supabase_service.upload_file(mixed_path)
                        return public_url
                    else:
                        print("[AUDIO UPLOAD ERROR] No supabase_service available to upload mixed audio file.")
                        return None
            
            return main_audio_path
            
        except Exception as e:
            print(f"Error mixing audio tracks: {e}")
            return main_audio_path
    

    async def create_audio_narration(self, text: str, narrator_style: str = "narration", background_music: Optional[str] = None) -> dict:
        try:
            # Use narrator_style to get voice settings
            voice_settings = self._get_narrator_voice_settings(narrator_style)
            
            # Generate main narration
            narration_audio = await self.generate_enhanced_speech(
                text=text,
                voice_id=voice_settings["voice_id"],
                emotion=voice_settings["emotion"],
                speed=voice_settings["speed"]
            )
            
            if not narration_audio:
                return None
            
            # Mix with background music if provided
            if background_music:
                mixed_audio = await self.mix_audio_tracks(
                    main_audio_path=narration_audio,
                    background_audio_path=background_music
                )
                return mixed_audio
            
            return narration_audio
            
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
    
    def _get_character_voice_settings(self, character_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get voice settings based on character profile"""
        personality = character_profile.get("personality", "neutral")
        age = character_profile.get("age", "adult")
        gender = character_profile.get("gender", "neutral")
        
        # Map character traits to voice settings
        voice_mapping = {
            "brave": {"emotion": "confident", "speed": 1.1, "stability": 0.8},
            "wise": {"emotion": "wise", "speed": 0.9, "stability": 0.9},
            "young": {"emotion": "excited", "speed": 1.2, "stability": 0.7},
            "mysterious": {"emotion": "mysterious", "speed": 0.8, "stability": 0.8},
            "friendly": {"emotion": "friendly", "speed": 1.0, "stability": 0.75}
        }
        
        settings = voice_mapping.get(personality, {
            "emotion": "neutral",
            "speed": 1.0,
            "stability": 0.75
        })
        
        # Add voice ID based on character profile
        settings["voice_id"] = self._get_voice_id_for_character(character_profile)
        settings["similarity_boost"] = 0.75
        
        return settings
    
    def _get_voice_id_for_character(self, character_profile: Dict[str, Any]) -> str:
        """Get appropriate voice ID for character"""
        # Use a real ElevenLabs voice ID
        # For now, use a common default voice ID
        return "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    
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
    
    async def _enhance_text_for_character(
        self, 
        text: str, 
        character_profile: Dict[str, Any], 
        scene_context: str
    ) -> str:
        """Enhance text to match character personality"""
        # In a real implementation, you might use AI to enhance the text
        # For now, return the original text
        return text
    
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
    
    async def _mock_generate_character_voice(self, text: str, character_profile: Dict[str, Any]) -> str:
        """Mock character voice generation for development"""
        await asyncio.sleep(1)
        character_name = character_profile.get("name", "character")
        audio_filename = f"mock_{character_name}_{hash(text)}.mp3"
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
                "voice_id": "character_young",
                "name": "Young Character",
                "description": "Energetic and friendly voice for young characters",
                "category": "character",
                "personality": "friendly"
            },
            {
                "voice_id": "character_wise",
                "name": "Wise Character",
                "description": "Deep and thoughtful voice for wise characters",
                "category": "character",
                "personality": "wise"
            },
            {
                "voice_id": "character_mysterious",
                "name": "Mysterious Character",
                "description": "Enigmatic and intriguing voice for mysterious characters",
                "category": "character",
                "personality": "mysterious"
            }
        ] 