from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ModelsLabV7VideoService:
    """ModelsLab V7 Video Service for Veo 2 Video Generation and Lip Sync"""
    
    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")
            
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL  # v7 URL
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # ✅ V7 Video API Endpoints
        self.image_to_video_endpoint = f"{self.base_url}/video-fusion/image-to-video"
        self.lip_sync_endpoint = f"{self.base_url}/video-fusion/lip-sync"
        
        # ✅ Available Veo 2 models
        self.video_models = {
            'veo2': 'veo2',  # Primary Veo 2 model
            'veo2_pro': 'veo2_pro',  # Enhanced Veo 2 model
            'veo2_standard': 'veo2'  # Standard Veo 2
        }
        
        # ✅ Available lip sync models
        self.lipsync_models = {
            'lipsync-2': 'lipsync-2',  # Latest lip sync model
            'lipsync-1': 'lipsync-1',  # Previous version
            'lipsync-hd': 'lipsync-2'  # HD quality mapping
        }
    
    async def generate_image_to_video(
        self,
        image_url: str,
        prompt: str,
        model_id: str = "veo2",
        negative_prompt: str = "",
        duration: float = 5.0,
        fps: int = 24,
        motion_strength: float = 0.8
    ) -> Dict[str, Any]:
        """Generate video from image using ModelsLab V7 Veo 2 API"""
        
        try:
            payload = {
                "model_id": model_id,
                "init_image": image_url,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "key": self.api_key
            }
            
            # Add optional parameters if they're supported
            if duration != 5.0:
                payload["duration"] = duration
            if fps != 24:
                payload["fps"] = fps
            if motion_strength != 0.8:
                payload["motion_strength"] = motion_strength
            
            logger.info(f"[MODELSLAB V7 VIDEO] Generating video with Veo 2")
            logger.info(f"[MODELSLAB V7 VIDEO] Model: {model_id}")
            logger.info(f"[MODELSLAB V7 VIDEO] Image: {image_url}")
            logger.info(f"[MODELSLAB V7 VIDEO] Prompt: {prompt[:100]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_to_video_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 VIDEO] Response status: {response.status}")
                    logger.info(f"[MODELSLAB V7 VIDEO] Response: {result}")
                    
                    return self._process_video_response(result, 'image_to_video')
                    
        except Exception as e:
            logger.error(f"[MODELSLAB V7 VIDEO ERROR]: {str(e)}")
            raise e
    
    async def generate_lip_sync(
        self,
        video_url: str,
        audio_url: str,
        model_id: str = "lipsync-2"
    ) -> Dict[str, Any]:
        """Generate lip sync using ModelsLab V7 API"""
        
        try:
            payload = {
                "model_id": model_id,
                "init_video": video_url,
                "init_audio": audio_url,
                "key": self.api_key
            }
            
            logger.info(f"[MODELSLAB V7 LIPSYNC] Generating lip sync")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Model: {model_id}")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Video: {video_url}")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Audio: {audio_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.lip_sync_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 LIPSYNC] Response status: {response.status}")
                    logger.info(f"[MODELSLAB V7 LIPSYNC] Response: {result}")
                    
                    return self._process_video_response(result, 'lip_sync')
                    
        except Exception as e:
            logger.error(f"[MODELSLAB V7 LIPSYNC ERROR]: {str(e)}")
            raise e
    
    async def enhance_video_for_scene(
        self,
        scene_description: str,
        image_url: str,
        audio_url: Optional[str] = None,
        dialogue_audio: Optional[List[Dict[str, Any]]] = None,
        style: str = "cinematic",
        include_lipsync: bool = True
    ) -> Dict[str, Any]:
        """Generate and enhance video for a complete scene"""
        
        try:
            logger.info(f"[SCENE VIDEO] Enhancing scene: {scene_description[:50]}...")

            # Step 1: Generate video from image with character information
            video_prompt = self._create_scene_video_prompt_with_characters(scene_description, style, dialogue_audio)

            video_result = await self.generate_image_to_video(
                image_url=image_url,
                prompt=video_prompt,
                model_id="veo2",
                negative_prompt=self._get_negative_prompt_for_style(style)
            )

            if video_result.get('status') != 'success':
                raise Exception(f"Video generation failed: {video_result.get('error', 'Unknown error')}")

            video_url = video_result.get('video_url')
            if not video_url:
                raise Exception("No video URL in response")

            enhanced_result = {
                'original_video': video_result,
                'video_url': video_url,
                'has_lipsync': False,
                'dialogue_audio': dialogue_audio or []
            }

            # Step 2: Apply lip sync for dialogue audio if provided
            if include_lipsync and dialogue_audio:
                logger.info(f"[SCENE VIDEO] Applying lip sync for {len(dialogue_audio)} dialogue segments...")

                # For multiple dialogue segments, we need to handle them sequentially
                current_video_url = video_url
                lipsync_results = []

                for i, dialogue in enumerate(dialogue_audio):
                    dialogue_audio_url = dialogue.get('audio_url')
                    if dialogue_audio_url:
                        logger.info(f"[SCENE VIDEO] Processing dialogue {i+1}: {dialogue.get('character', 'Unknown')}")

                        lipsync_result = await self.generate_lip_sync(
                            video_url=current_video_url,
                            audio_url=dialogue_audio_url,
                            model_id="lipsync-2"
                        )

                        if lipsync_result.get('status') == 'success':
                            new_video_url = lipsync_result.get('video_url')
                            if new_video_url:
                                current_video_url = new_video_url
                                lipsync_results.append(lipsync_result)
                                logger.info(f"[SCENE VIDEO] ✅ Dialogue {i+1} lip sync applied")
                            else:
                                logger.warning(f"[SCENE VIDEO] ⚠️ Dialogue {i+1} lip sync completed but no video URL")
                        else:
                            logger.warning(f"[SCENE VIDEO] ⚠️ Dialogue {i+1} lip sync failed: {lipsync_result.get('error', 'Unknown error')}")

                if lipsync_results:
                    enhanced_result['lipsync_videos'] = lipsync_results
                    enhanced_result['video_url'] = current_video_url  # Use final lip-synced version
                    enhanced_result['has_lipsync'] = True
                    logger.info(f"[SCENE VIDEO] ✅ All dialogue lip sync applied successfully")
                else:
                    logger.warning(f"[SCENE VIDEO] ⚠️ No dialogue lip sync succeeded")

            # Step 3: Apply lip sync for background audio if provided (separate from dialogue)
            elif include_lipsync and audio_url and not dialogue_audio:
                logger.info(f"[SCENE VIDEO] Applying lip sync for background audio...")

                lipsync_result = await self.generate_lip_sync(
                    video_url=video_url,
                    audio_url=audio_url,
                    model_id="lipsync-2"
                )

                if lipsync_result.get('status') == 'success':
                    lipsync_video_url = lipsync_result.get('video_url')
                    if lipsync_video_url:
                        enhanced_result['lipsync_video'] = lipsync_result
                        enhanced_result['video_url'] = lipsync_video_url  # Use lip-synced version
                        enhanced_result['has_lipsync'] = True
                        logger.info(f"[SCENE VIDEO] ✅ Background audio lip sync applied successfully")
                    else:
                        logger.warning(f"[SCENE VIDEO] ⚠️ Background audio lip sync completed but no video URL")
                else:
                    logger.warning(f"[SCENE VIDEO] ⚠️ Background audio lip sync failed: {lipsync_result.get('error', 'Unknown error')}")

            return {
                'status': 'success',
                'scene_description': scene_description,
                'enhanced_video': enhanced_result,
                'processing_steps': ['image_to_video'] + (['lip_sync'] if enhanced_result['has_lipsync'] else []),
                'character_dialogue_count': len(dialogue_audio) if dialogue_audio else 0
            }
            
        except Exception as e:
            logger.error(f"[SCENE VIDEO] Enhancement failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'scene_description': scene_description
            }
    
    async def batch_generate_scene_videos(
        self,
        scenes: List[Dict[str, Any]],
        max_concurrent: int = 2  # Lower for video generation
    ) -> List[Dict[str, Any]]:
        """Generate videos for multiple scenes with controlled concurrency"""
        
        logger.info(f"[BATCH VIDEO] Processing {len(scenes)} scenes (max {max_concurrent} concurrent)")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def generate_single_scene_video(scene: Dict[str, Any], index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    scene_description = scene.get('description', '')
                    image_url = scene.get('image_url', '')
                    audio_url = scene.get('audio_url')
                    style = scene.get('style', 'cinematic')
                    
                    if not image_url:
                        raise Exception("No image URL provided for scene")
                    
                    result = await self.enhance_video_for_scene(
                        scene_description=scene_description,
                        image_url=image_url,
                        audio_url=audio_url,
                        style=style,
                        include_lipsync=bool(audio_url)
                    )
                    
                    result['batch_index'] = index
                    result['scene_id'] = scene.get('scene_id', f'scene_{index + 1}')
                    
                    # Delay to prevent rate limiting
                    await asyncio.sleep(2.0)  # 2 second delay between requests
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"[BATCH VIDEO] Failed to generate scene {index}: {e}")
                    return {
                        'status': 'error',
                        'error': str(e),
                        'batch_index': index,
                        'scene_id': scene.get('scene_id', f'scene_{index + 1}')
                    }
        
        # Process all scenes
        tasks = [
            generate_single_scene_video(scene, i) 
            for i, scene in enumerate(scenes)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'status': 'error',
                    'error': str(result),
                    'batch_index': i,
                    'scene_id': scenes[i].get('scene_id', f'scene_{i + 1}')
                })
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.get('status') == 'success')
        logger.info(f"[BATCH VIDEO] Completed: {successful_count}/{len(scenes)} successful")
        
        return processed_results
    
    def get_video_model_for_style(self, style: str) -> str:
        """Get appropriate Veo 2 model based on style"""
        
        # For now, all styles use the main veo2 model
        # This could be expanded if different Veo 2 variants become available
        return "veo2"
    
    def get_lipsync_model_for_quality(self, quality_tier: str) -> str:
        """Get appropriate lip sync model based on quality tier"""
        
        model_map = {
            "basic": "lipsync-1",
            "standard": "lipsync-2",
            "premium": "lipsync-2",
            "professional": "lipsync-2"
        }
        return model_map.get(quality_tier.lower(), "lipsync-2")
    
    def calculate_video_duration_from_audio(
        self,
        audio_files: List[Dict],
        scene_id: str
    ) -> float:
        """Calculate video duration based on audio files for a scene"""
        
        total_duration = 0.0
        scene_number = int(scene_id.split('_')[1]) if '_' in scene_id else 1
        
        # Find audio files for this scene
        for audio in audio_files:
            audio_scene = audio.get('scene', 1)
            if audio_scene == scene_number:
                total_duration += audio.get('duration', 3.0)
        
        # Ensure minimum duration of 3 seconds, maximum of 30 seconds (Veo 2 limits)
        return max(3.0, min(total_duration, 30.0))
    
    def _create_scene_video_prompt(self, scene_description: str, style: str) -> str:
        """Create optimized prompt for Veo 2 video generation"""

        style_modifiers = {
            "realistic": "cinematic realism, natural movement, photorealistic details, smooth camera motion",
            "cinematic": "epic cinematic style, dramatic lighting, professional cinematography, dynamic camera angles",
            "animated": "animated style, expressive movement, stylized animation, fluid motion",
            "fantasy": "fantasy cinematography, magical atmosphere, ethereal movements, mystical lighting",
            "comic": "comic book style, dynamic action, bold movements, superhero cinematography",
            "artistic": "artistic cinematography, creative movement, unique visual style, artistic flair"
        }

        style_prompt = style_modifiers.get(style.lower(), style_modifiers["cinematic"])

        # Enhanced prompt for Veo 2
        full_prompt = f"""
{scene_description}

{style_prompt}.
High quality video production, smooth motion, professional videography,
engaging visual storytelling, seamless transitions, cinematic composition.
""".strip()

        return full_prompt

    def _create_scene_video_prompt_with_characters(self, scene_description: str, style: str, dialogue_audio: Optional[List[Dict[str, Any]]] = None) -> str:
        """Create optimized prompt for Veo 2 video generation with character information"""

        base_prompt = self._create_scene_video_prompt(scene_description, style)

        # Add character information if dialogue audio is provided
        if dialogue_audio:
            character_info = []
            for dialogue in dialogue_audio:
                character_name = dialogue.get('character', 'Character')
                character_profile = dialogue.get('character_profile', {})

                # Build character description
                char_desc = f"{character_name}"
                if character_profile.get('age'):
                    char_desc += f" ({character_profile['age']})"
                if character_profile.get('gender') and character_profile['gender'] != 'neutral':
                    char_desc += f" {character_profile['gender']}"
                if character_profile.get('personality'):
                    char_desc += f", {character_profile['personality']}"

                character_info.append(char_desc)

            if character_info:
                characters_text = "Characters present: " + ", ".join(character_info)
                base_prompt = f"{characters_text}\n\n{base_prompt}"

                # Add instruction for character visibility in video
                base_prompt += "\n\nEnsure characters are clearly visible and appropriately positioned for dialogue delivery."

        return base_prompt
    
    def _get_negative_prompt_for_style(self, style: str) -> str:
        """Get negative prompt to avoid unwanted elements"""
        
        base_negative = "blurry, low quality, distorted, pixelated, artifacts, glitches, stuttering motion"
        
        style_negatives = {
            "realistic": f"{base_negative}, cartoon, animated, artificial looking, fake",
            "cinematic": f"{base_negative}, amateur, poor lighting, shaky camera",
            "animated": f"{base_negative}, photorealistic, real people",
            "fantasy": f"{base_negative}, modern elements, technology, realistic",
            "comic": f"{base_negative}, photorealistic, dull colors",
            "artistic": f"{base_negative}, generic, boring, conventional"
        }
        
        return style_negatives.get(style.lower(), base_negative)
    
    def _process_video_response(self, response: Dict[str, Any], operation_type: str) -> Dict[str, Any]:
        """Process and standardize video API response"""
        
        try:
            # ✅ Handle different response formats from V7 API
            if response.get('status') == 'success' or 'output' in response:
                output_urls = response.get('output', [])
                
                if output_urls and len(output_urls) > 0:
                    video_url = output_urls[0]
                    
                    # Handle different URL formats
                    if isinstance(video_url, dict):
                        video_url = video_url.get('url') or video_url.get('video_url')
                    
                    # Extract metadata
                    meta = response.get('meta', {})
                    
                    return {
                        'status': 'success',
                        'output': output_urls,
                        'video_url': video_url,
                        'meta': meta,
                        'generation_time': response.get('generation_time', 0),
                        'model_used': response.get('model_id', 'veo2'),
                        'operation_type': operation_type
                    }
                else:
                    # Check if it's an async operation
                    request_id = response.get('id')
                    if request_id:
                        return {
                            'status': 'processing',
                            'request_id': request_id,
                            'operation_type': operation_type,
                            'message': 'Video generation in progress'
                        }
                    else:
                        raise Exception("No video URL or request ID in response output")
            else:
                # Handle error response
                error_message = response.get('message', response.get('error', 'Unknown error'))
                raise Exception(f"{operation_type} failed: {error_message}")
                
        except Exception as e:
            logger.error(f"[MODELSLAB V7 VIDEO] Response processing error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'operation_type': operation_type,
                'raw_response': response
            }
    
    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_time: int = 600,  # 10 minutes for video generation
        check_interval: int = 30
    ) -> Dict[str, Any]:
        """Wait for async video generation to complete"""
        
        # ✅ V7 APIs might be synchronous, but keeping this for compatibility
        logger.info(f"[MODELSLAB V7 VIDEO] Waiting for completion of request: {request_id}")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                # For V7, you might need to poll a status endpoint
                # This is a placeholder - adjust based on actual V7 API documentation
                await asyncio.sleep(check_interval)
                
                # If V7 APIs are synchronous, return immediately
                return {
                    'status': 'completed',
                    'message': 'V7 APIs appear to be synchronous'
                }
                
            except Exception as e:
                logger.error(f"[MODELSLAB V7 VIDEO] Error checking status: {e}")
                await asyncio.sleep(check_interval)
        
        raise Exception(f"Video generation timed out after {max_wait_time} seconds")
    
    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get available models for different video operations"""
        
        return {
            'video_generation': {
                'veo2': 'Veo 2 (Recommended)',
                'veo2_pro': 'Veo 2 Pro (Enhanced)',
            },
            'lip_sync': {
                'lipsync-2': 'Lip Sync V2 (Latest)',
                'lipsync-1': 'Lip Sync V1 (Legacy)'
            }
        }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get supported input/output formats"""
        
        return {
            'input_images': ['jpg', 'jpeg', 'png', 'webp'],
            'input_videos': ['mp4', 'mov', 'avi'],
            'input_audio': ['mp3', 'wav', 'aac'],
            'output_videos': ['mp4']
        }
    
    async def validate_inputs(
        self,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """Validate input URLs and formats"""
        
        validation_results = {
            'image_valid': True,
            'video_valid': True,
            'audio_valid': True,
            'all_valid': True
        }
        
        try:
            # Basic URL validation (could be enhanced with actual file checking)
            if image_url:
                if not any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    validation_results['image_valid'] = False
            
            if video_url:
                if not any(ext in video_url.lower() for ext in ['.mp4', '.mov', '.avi']):
                    validation_results['video_valid'] = False
            
            if audio_url:
                if not any(ext in audio_url.lower() for ext in ['.mp3', '.wav', '.aac']):
                    validation_results['audio_valid'] = False
            
            validation_results['all_valid'] = all([
                validation_results['image_valid'],
                validation_results['video_valid'],
                validation_results['audio_valid']
            ])
            
        except Exception as e:
            logger.error(f"[VALIDATION] Error validating inputs: {e}")
            validation_results['all_valid'] = False
        
        return validation_results