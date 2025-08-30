import requests
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from app.core.config import settings
import json

class ModelsLabAudioService:
    def __init__(self):
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Voice mappings for different character types
        self.narrator_voices = [
            "en-US-JennyNeural",  # Professional female narrator
            "en-US-GuyNeural",    # Professional male narrator
        ]
        
        self.character_voices = {
            "male_young": "en-US-ChristopherNeural",
            "male_adult": "en-US-EricNeural", 
            "male_old": "en-US-GuyNeural",
            "female_young": "en-US-AriaNeural",
            "female_adult": "en-US-JennyNeural",
            "female_old": "en-US-NancyNeural",
        }

    async def generate_tts_audio(
        self,
        text: str,
        voice_id: str = "en-US-JennyNeural",
        audio_format: str = "mp3",
        speed: float = 1.0,
        pitch: float = 1.0,
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate TTS audio using ModelsLab API"""
        
        payload = {
            "key": self.api_key,
            "text": text,
            "voice": voice_id,
            "audio_format": audio_format,
            "speed": speed,
            "pitch": pitch,
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/tts",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab TTS API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB TTS ERROR]: {str(e)}")
            raise e

    async def generate_sound_effect(
        self,
        description: str,
        duration: float = 5.0,
        audio_format: str = "mp3",
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate sound effects using ModelsLab API"""
        
        payload = {
            "key": self.api_key,
            "prompt": f"Generate sound effect: {description}",
            "duration": duration,
            "audio_format": audio_format,
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/audio-generation", 
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Audio Generation API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB SOUND EFFECT ERROR]: {str(e)}")
            raise e

    def assign_character_voice(self, character_name: str, character_description: str = "") -> str:
        """Assign appropriate voice to character based on description"""
        character_lower = character_name.lower()
        desc_lower = character_description.lower()
        
        # Simple character voice mapping logic
        if any(word in character_lower for word in ["boy", "young", "child"]):
            return self.character_voices.get("male_young") if "male" in desc_lower else self.character_voices.get("female_young")
        elif any(word in character_lower for word in ["old", "elder", "grandfather", "grandmother"]):
            return self.character_voices.get("male_old") if "male" in desc_lower else self.character_voices.get("female_old")
        elif any(word in character_lower for word in ["man", "father", "king", "wizard", "male"]):
            return self.character_voices.get("male_adult")
        elif any(word in character_lower for word in ["woman", "mother", "queen", "witch", "female"]):
            return self.character_voices.get("female_adult")
        else:
            # Default assignment
            return self.character_voices.get("male_adult")

    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_time: int = 120,  # 2 minutes for audio
        check_interval: int = 5    # 5 seconds
    ) -> Dict[str, Any]:
        """Wait for audio generation to complete"""
        
        elapsed_time = 0
        while elapsed_time < max_wait_time:
            try:
                # Check status payload
                status_payload = {
                    "key": self.api_key,
                    "request_id": request_id
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/fetch",
                        json=status_payload,
                        headers=self.headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            status = result.get('status')
                            if status == 'success':
                                return result
                            elif status == 'failed':
                                raise Exception(f"Audio generation failed: {result.get('message', 'Unknown error')}")
                            elif status in ['processing', 'queued']:
                                await asyncio.sleep(check_interval)
                                elapsed_time += check_interval
                                continue
                        else:
                            # If status check fails, wait and retry
                            await asyncio.sleep(check_interval)
                            elapsed_time += check_interval
                            continue
                            
            except Exception as e:
                if elapsed_time >= max_wait_time - check_interval:
                    raise Exception(f"Audio generation timeout after {max_wait_time} seconds: {str(e)}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                continue

        raise Exception(f"Audio generation timeout after {max_wait_time} seconds")