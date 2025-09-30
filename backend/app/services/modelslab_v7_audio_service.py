from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
import random
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ModelsLabV7AudioService:
    """ModelsLab V7 Audio Service for TTS, Sound Effects, and Music Generation"""
    
    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")
            
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL  # v7 URL
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # ✅ V7 API Endpoints
        self.tts_endpoint = f"{self.base_url}/voice/text-to-speech"
        self.sound_effects_endpoint = f"{self.base_url}/voice/sound-generation"
        self.music_endpoint = f"{self.base_url}/voice/music-gen"
        
        # ✅ Voice mapping for narrators (ElevenLabs voices)
        self.narrator_voices = {
            'professional': 'ErXwobaYiN019PkySvjV',     # Professional narrator
            'storyteller': 'M7baJQBjzMsrxxZ796H6',      # Male storyteller
            'friendly': 'pNInz6obpgDQGcFmaJgB',        # Female friendly narrator
        }

        # ✅ Voice mapping for characters (ElevenLabs voices for dialogue)
        self.character_voices = {
            'conversational_male': '29vD33N1CtxCmqQRPOHJ',    # Conversational male
            'conversational_female': '21m00Tcm4TlvDq8ikWAM',  # Conversational female
            'expressive_male': 'IKne3meq5aSn9XLyUdCD',       # Expressive male
            'expressive_female': 'AZnzlk1XvdvUeBnXmlld',     # Expressive female
            'warm_male': 'pNInz6obpgDQGcFmaJgB',            # Warm male
            'warm_female': 'EXAVITQu4vr4xnSDxMaL',          # Warm female
        }
        
        # ✅ Available TTS models
        self.tts_models = {
            'multilingual': 'eleven_multilingual_v2',
            'english': 'eleven_english_v1',
            'turbo': 'eleven_turbo_v2'
        }
        
        # ✅ Sound effects model
        self.sound_effects_model = "eleven_sound_effect"
        
        # ✅ Music generation model
        self.music_model = "music_v1"
    
    async def generate_tts_audio(
        self,
        text: str,
        voice_id: str = "M7baJQBjzMsrxxZ796H6",
        model_id: str = "eleven_multilingual_v2",
        speed: float = 1.0,
        stability: float = 0.5,
        similarity_boost: float = 0.5
    ) -> Dict[str, Any]:
        """Generate text-to-speech audio using ModelsLab V7 ElevenLabs API"""
        
        try:
            payload = {
                "model_id": model_id,
                "prompt": text,
                "voice_id": voice_id,
                "key": self.api_key
            }
            
            # Optional parameters for voice tuning
            if speed != 1.0:
                payload["speed"] = speed
            if stability != 0.5:
                payload["stability"] = stability
            if similarity_boost != 0.5:
                payload["similarity_boost"] = similarity_boost
            
            logger.info(f"[MODELSLAB V7 TTS] Generating audio for text: {text[:50]}...")
            logger.info(f"[MODELSLAB V7 TTS] Using voice: {voice_id}, model: {model_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.tts_endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 TTS] Response status: {response.status}")
                    logger.info(f"[MODELSLAB V7 TTS] Response: {result}")
                    
                    if response.status == 200:
                        return self._process_tts_response(result)
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab V7 TTS API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"[MODELSLAB V7 TTS ERROR]: {str(e)}")
            raise e
    
    async def generate_sound_effect(
        self,
        description: str,
        duration: float = 10.0,
        model_id: str = "eleven_sound_effect"
    ) -> Dict[str, Any]:
        """Generate sound effects using ModelsLab V7 API"""
        
        try:
            # ✅ Limit duration to API constraints (usually max 30 seconds)
            duration = min(duration, 30.0)
            duration = max(duration, 1.0)  # Minimum 1 second
            
            payload = {
                "prompt": description,
                "time in seconds": str(int(duration)),
                "model_id": model_id,
                "key": self.api_key
            }
            
            logger.info(f"[MODELSLAB V7 SFX] Generating sound effect: {description[:50]}...")
            logger.info(f"[MODELSLAB V7 SFX] Duration: {duration}s, Model: {model_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.sound_effects_endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 SFX] Response status: {response.status}")
                    logger.info(f"[MODELSLAB V7 SFX] Response: {result}")
                    
                    if response.status == 200:
                        return self._process_audio_response(result, 'sound_effect')
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab V7 Sound Effects API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"[MODELSLAB V7 SFX ERROR]: {str(e)}")
            raise e
    
    async def generate_background_music(
        self,
        description: str,
        model_id: str = "music_v1",
        duration: float = 30.0
    ) -> Dict[str, Any]:
        """Generate background music using ModelsLab V7 API"""
        
        try:
            payload = {
                "prompt": description,
                "model_id": model_id,
                "key": self.api_key
            }
            
            # ✅ Add duration if supported (check API docs)
            if duration:
                payload["duration"] = duration
            
            logger.info(f"[MODELSLAB V7 MUSIC] Generating music: {description[:50]}...")
            logger.info(f"[MODELSLAB V7 MUSIC] Model: {model_id}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.music_endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 MUSIC] Response status: {response.status}")
                    logger.info(f"[MODELSLAB V7 MUSIC] Response: {result}")
                    
                    if response.status == 200:
                        return self._process_audio_response(result, 'music')
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab V7 Music API error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"[MODELSLAB V7 MUSIC ERROR]: {str(e)}")
            raise e
    
    
    def _process_tts_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process TTS API response and extract relevant information"""
        
        try:
            # ✅ Handle different response formats
            if response.get('status') == 'success' or 'output' in response:
                output_urls = response.get('output', [])
                
                if output_urls and len(output_urls) > 0:
                    audio_url = output_urls[0]
                    
                    # Extract metadata
                    meta = response.get('meta', {})
                    duration = response.get('audio_time', 0) or meta.get('duration', 0)
                    
                    return {
                        'status': 'success',
                        'output': output_urls,
                        'audio_url': audio_url,
                        'audio_time': duration,
                        'meta': meta,
                        'generation_time': response.get('generation_time', 0)
                    }
                else:
                    raise Exception("No audio URL in response output")
            else:
                # Handle error response
                error_message = response.get('message', response.get('error', 'Unknown error'))
                raise Exception(f"TTS generation failed: {error_message}")
                
        except Exception as e:
            logger.error(f"[MODELSLAB V7 TTS] Response processing error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'raw_response': response
            }
    
    def _process_audio_response(self, response: Dict[str, Any], audio_type: str) -> Dict[str, Any]:
        """Process sound effects or music API response"""
        
        try:
            # ✅ Handle different response formats  
            if response.get('status') == 'success' or 'output' in response:
                output_urls = response.get('output', [])
                
                if output_urls and len(output_urls) > 0:
                    audio_url = output_urls[0]
                    
                    # Extract metadata
                    meta = response.get('meta', {})
                    duration = response.get('audio_time', 0) or meta.get('duration', 0)
                    
                    return {
                        'status': 'success',
                        'output': output_urls,
                        'audio_url': audio_url,
                        'audio_time': duration,
                        'meta': meta,
                        'audio_type': audio_type,
                        'generation_time': response.get('generation_time', 0)
                    }
                else:
                    raise Exception(f"No audio URL in {audio_type} response output")
            else:
                # Handle error response
                error_message = response.get('message', response.get('error', 'Unknown error'))
                raise Exception(f"{audio_type} generation failed: {error_message}")
                
        except Exception as e:
            logger.error(f"[MODELSLAB V7 {audio_type.upper()}] Response processing error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'audio_type': audio_type,
                'raw_response': response
            }
    
    async def wait_for_completion(self, request_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Wait for async audio generation to complete (if applicable)"""
        
        # ✅ Note: ModelsLab V7 APIs appear to be synchronous based on examples
        # This method is kept for compatibility but may not be needed
        
        logger.info(f"[MODELSLAB V7] Waiting for completion of request: {request_id}")
        
        # For now, return a timeout since V7 APIs seem synchronous
        await asyncio.sleep(2)  # Brief wait
        
        return {
            'status': 'completed',
            'message': 'V7 APIs are synchronous - no waiting required'
        }
    
    def get_available_voices(self) -> Dict[str, str]:
        """Get available narrator voice IDs and their descriptions"""

        return {
            'ErXwobaYiN019PkySvjV': 'Professional Narrator',
            'M7baJQBjzMsrxxZ796H6': 'Male Storyteller',
            'pNInz6obpgDQGcFmaJgB': 'Friendly Female Narrator'
        }

    def get_available_character_voices(self) -> Dict[str, str]:
        """Get available character voice IDs and their descriptions"""

        return {
            '29vD33N1CtxCmqQRPOHJ': 'Conversational Male',
            '21m00Tcm4TlvDq8ikWAM': 'Conversational Female',
            'IKne3meq5aSn9XLyUdCD': 'Expressive Male',
            'AZnzlk1XvdvUeBnXmlld': 'Expressive Female',
            'pNInz6obpgDQGcFmaJgB': 'Warm Male',
            'EXAVITQu4vr4xnSDxMaL': 'Warm Female'
        }
    
    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get available models for different audio types"""
        
        return {
            'tts': {
                'eleven_multilingual_v2': 'Multilingual TTS Model (Recommended)',
                'eleven_english_v1': 'English-only TTS Model',
                'eleven_turbo_v2': 'Fast TTS Model'
            },
            'sound_effects': {
                'eleven_sound_effect': 'ElevenLabs Sound Effects Model'
            },
            'music': {
                'music_v1': 'Music Generation Model V1'
            }
        }
    
    async def batch_generate_tts(
        self,
        texts: List[Dict[str, str]],
        default_voice: str = "29vD33N1CtxCmqQRPOHJ",  # Default to conversational male for character dialogue
        use_character_voices: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate multiple TTS audio files in batch"""
        
        results = []
        
        # Cycle through character voices for variety if using character voices
        character_voice_list = list(self.character_voices.values()) if use_character_voices else [default_voice]

        for i, text_item in enumerate(texts):
            try:
                text = text_item.get('text', '')
                # Use different voices for different characters to add variety
                voice_id = text_item.get('voice_id', character_voice_list[i % len(character_voice_list)])
                character = text_item.get('character', f'Speaker_{i+1}')

                logger.info(f"[BATCH TTS] Processing {i+1}/{len(texts)}: {character} (voice: {voice_id})")

                result = await self.generate_tts_audio(
                    text=text,
                    voice_id=voice_id
                )

                result['character'] = character
                result['sequence'] = i + 1
                result['voice_used'] = voice_id
                results.append(result)

                # ✅ Small delay to prevent rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"[BATCH TTS] Failed for item {i+1}: {e}")
                results.append({
                    'status': 'error',
                    'error': str(e),
                    'character': text_item.get('character', f'Speaker_{i+1}'),
                    'sequence': i + 1
                })
        
        return results
    
    async def enhance_audio_for_scene(
        self,
        scene_description: str,
        dialogue_audio_urls: List[str] = None,
        include_ambient: bool = True,
        include_music: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive audio enhancement for a scene"""
        
        try:
            logger.info(f"[SCENE AUDIO] Enhancing audio for scene: {scene_description[:50]}...")
            
            enhanced_audio = {
                'dialogue': dialogue_audio_urls or [],
                'sound_effects': [],
                'background_music': [],
                'ambient_sounds': []
            }
            
            # ✅ Generate ambient sound effects
            if include_ambient:
                ambient_prompt = f"Ambient sound effects for: {scene_description}. Create atmospheric background audio suitable for the scene."
                
                ambient_result = await self.generate_sound_effect(
                    description=ambient_prompt,
                    duration=15.0
                )
                
                if ambient_result.get('status') == 'success':
                    enhanced_audio['ambient_sounds'].append(ambient_result)
            
            # ✅ Generate background music
            if include_music:
                music_prompt = f"Background music for: {scene_description}. Create atmospheric music that matches the mood and setting."
                
                music_result = await self.generate_background_music(
                    description=music_prompt,
                    duration=30.0
                )
                
                if music_result.get('status') == 'success':
                    enhanced_audio['background_music'].append(music_result)
            
            return {
                'status': 'success',
                'scene_description': scene_description,
                'enhanced_audio': enhanced_audio,
                'total_elements': (
                    len(enhanced_audio['dialogue']) +
                    len(enhanced_audio['sound_effects']) + 
                    len(enhanced_audio['background_music']) +
                    len(enhanced_audio['ambient_sounds'])
                )
            }
            
        except Exception as e:
            logger.error(f"[SCENE AUDIO] Enhancement failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'scene_description': scene_description
            }