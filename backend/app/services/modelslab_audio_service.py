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
            "madison",            # Female narrator from docs
            "leo",               # Male narrator from docs
        ]
        
        self.character_voices = {
            "male_young": "dan",
            "male_adult": "leo", 
            "male_old": "zac",
            "female_young": "mia",
            "female_adult": "tara",
            "female_old": "leah",
        }

    async def generate_tts_audio(
    self,
    text: str,
    voice_id: str = "madison",
    audio_format: str = "mp3",
    speed: float = 1.0,
    pitch: float = 1.0,
    webhook: Optional[str] = None,
    track_id: Optional[str] = None
) -> Dict[str, Any]:
        """Generate TTS audio using ModelsLab API"""
        
        # ✅ CORRECTED: Fixed parameter names to match API docs exactly
        payload = {
            "key": self.api_key,
            "prompt": text,  # ✅ Correct: Use 'prompt' for text
            "voice_id": voice_id,  # ✅ Keep as voice_id - this is correct per docs
            "language": "american english",  # ✅ Use full language name
            "output_format": audio_format,
            "speed": int(speed),  # ✅ Convert to integer as per docs
            "emotion": False,  # ✅ This is correct and valid!
            "temp": False   # ✅ Add temp parameter
        }
        
        if webhook:
            payload["webhook"] = webhook
        if track_id:
            payload["track_id"] = track_id

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/voice/text_to_speech",
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()
                    print(f"[MODELSLAB TTS] API Response: {result}")
                    
                    if response.status == 200:
                        # ✅ Handle both sync and async responses
                        if result.get('status') == 'success':
                            # Synchronous response - audio ready immediately
                            return result
                        elif result.get('status') == 'processing':
                            # Asynchronous response - need to fetch later
                            request_id = result.get('id')
                            if request_id:
                                # Wait for completion
                                final_result = await self.wait_for_completion(request_id)
                                return final_result
                            else:
                                raise Exception("No request ID provided for async processing")
                        else:
                            raise Exception(f"API returned error: {result.get('message', 'Unknown error')}")
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab TTS API error: {response.status} - {error_text}")
                    
        except Exception as e:
            print(f"[MODELSLAB TTS ERROR]: {str(e)}")
            raise e

    async def generate_sound_effect(
    self,
    description: str,
    duration: float = 10.0,  # ✅ Changed default to 10 (API default)
    audio_format: str = "wav",  # ✅ Changed default to wav (API default)
    bitrate: str = "128k",  # ✅ Added bitrate parameter
    temp: bool = False,  # ✅ Added temp parameter
    webhook: Optional[str] = None,
    track_id: Optional[str] = None
) -> Dict[str, Any]:
        """Generate sound effects using ModelsLab SFX API"""
        
        # ✅ CORRECTED: Use proper SFX API payload format
        payload = {
            "key": self.api_key,
            "prompt": description,  # Direct description, no prefix needed
            "duration": int(duration),  # Must be integer, 3-15 seconds range
            "output_format": audio_format,  # wav, mp3, flac
            "bitrate": bitrate,  # 128k, 192k, 320k
            "temp": temp  # TRUE or FALSE
        }
        
        if webhook:
            payload["webhook"] = webhook
        if track_id:
            payload["track_id"] = track_id

        try:
            async with aiohttp.ClientSession() as session:
                # ✅ CORRECTED: Use the proper SFX endpoint from docs
                async with session.post(
                    f"{self.base_url}/voice/sfx",  # Correct SFX endpoint
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()
                    print(f"[MODELSLAB SFX] API Response: {result}")
                    
                    if response.status == 200 and result.get('status') == 'success':
                        return result
                    else:
                        print(f"[MODELSLAB SFX ERROR] {response.status}: {result}")
                        raise Exception(f"ModelsLab SFX API error: {result.get('message', 'Unknown error')}")
                        
        except Exception as e:
            print(f"[MODELSLAB SFX ERROR]: {str(e)}")
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
    max_wait_time: int = 300,
    check_interval: int = 10
) -> Dict[str, Any]:
        """Wait for async generation to complete"""
        
        elapsed_time = 0
        while elapsed_time < max_wait_time:
            try:
                payload = {
                    "key": self.api_key,
                    "request_id": str(request_id)
                }
                
                async with aiohttp.ClientSession() as session:
                    # ✅ Use the fetch endpoint from ModelsLab response
                    async with session.post(
                        f"{self.base_url}/voice/fetch/{request_id}",
                        json=payload,
                        headers=self.headers
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            if result.get('status') == 'success':
                                print(f"[MODELSLAB] Audio generation completed: {result.get('output', [])}")
                                return result
                            elif result.get('status') == 'failed':
                                raise Exception(f"Generation failed: {result.get('message', 'Unknown error')}")
                            elif result.get('status') in ['processing', 'queued']:
                                print(f"[MODELSLAB] Still processing... waiting {check_interval}s")
                                await asyncio.sleep(check_interval)
                                elapsed_time += check_interval
                                continue
                            else:
                                # Unknown status, wait and retry
                                await asyncio.sleep(check_interval)
                                elapsed_time += check_interval
                                continue
                        else:
                            await asyncio.sleep(check_interval)
                            elapsed_time += check_interval
                            continue
                            
            except Exception as e:
                print(f"[MODELSLAB] Fetch error: {str(e)}")
                if elapsed_time >= max_wait_time - check_interval:
                    raise Exception(f"Generation timeout after {max_wait_time} seconds: {str(e)}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval

        raise Exception(f"Generation timeout after {max_wait_time} seconds")