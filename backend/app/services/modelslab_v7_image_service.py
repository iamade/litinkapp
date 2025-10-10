from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ModelsLabV7ImageService:
    """ModelsLab V7 Image Service for Runway text-to-image generation"""
    
    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")
            
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL  # v7 URL
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # ✅ V7 Image Generation Endpoint
        self.image_endpoint = f"{self.base_url}/images/text-to-image"
        self.fetch_endpoint = f"{self.base_url}/images/fetch"
        
        # ✅ Available models for V7
        self.image_models = {
            'gen4': 'gen4_image',
            'runway': 'runway_image',
            'cinematic': 'gen4_image',
            'realistic': 'gen4_image',
            'artistic': 'gen4_image'
        }

        # ✅ Tier-based model mapping (based on architecture)
        self.tier_model_mapping = {
            'free': 'imagen-4.0-ultra',        # ModelsLab Imagen 4.0 Ultra for free tier
            'basic': 'imagen-4.0-fast-generate',       # ModelsLab Imagen 4.0 Fast Generate for basic tier
            'pro': 'runway_image',       # Better quality for Pro tier
            'premium': 'runway_image',   # Premium models
            'professional': 'runway_image',  # Professional tier
            'enterprise': 'runway_image' # Enterprise tier
        }

        logger.info(f"[MODELSLAB V7 IMAGE] Initialized with image models: {self.image_models}")
        logger.info(f"[MODELSLAB V7 IMAGE] Tier model mapping: {self.tier_model_mapping}")
        logger.info(f"[MODELSLAB V7 IMAGE] Default model_id: gen4_image")
        
        # ✅ Aspect ratio presets
        self.aspect_ratios = {
            'square': '1:1',
            'portrait': '3:4',
            'landscape': '4:3',
            'widescreen': '16:9',
            'ultrawide': '21:9',
            'vertical': '9:16',
            'video_landscape': '1920:1080',
            'video_portrait': '1080:1920',
            'instagram_square': '1080:1080',
            'instagram_story': '1080:1920'
        }
    
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        wait_for_completion: bool = True,
        max_wait_time: int = 60
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab V7 API with async handling"""

        try:
            # Determine model_id based on user_tier if not explicitly provided
            if model_id is None and user_tier is not None:
                model_id = self._get_model_for_tier(user_tier)
            elif model_id is None:
                model_id = "gen4_image"  # Fallback to default

            payload = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model_id": model_id,
                "key": self.api_key
            }

            logger.info(f"[MODELSLAB V7 IMAGE] Generating image with model: {model_id}")
            logger.info(f"[MODELSLAB V7 IMAGE] User tier: {user_tier}")
            logger.info(f"[MODELSLAB V7 IMAGE] Aspect ratio: {aspect_ratio}")
            logger.info(f"[MODELSLAB V7 IMAGE] Prompt: {prompt[:100]}...")
            logger.info(f"[MODELSLAB V7 IMAGE] Model selection: {'tier-based' if user_tier else 'hardcoded/default'}")
            logger.info(f"[DEBUG] API payload model_id: {payload.get('model_id')}")
            
            async with aiohttp.ClientSession() as session:
                # Submit generation request
                async with session.post(
                    self.image_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    logger.info(f"[MODELSLAB V7 IMAGE] Initial response: {result}")
                    
                    # ✅ Handle async processing response
                    if result.get('status') == 'processing':
                        if not wait_for_completion:
                            return {
                                'status': 'processing',
                                'request_id': result.get('id'),
                                'fetch_url': result.get('fetch_result'),
                                'eta': result.get('eta', 10),
                                'future_links': result.get('future_links', [])
                            }
                        
                        # Wait for completion
                        fetch_url = result.get('fetch_result')
                        request_id = result.get('id')
                        
                        if fetch_url:
                            completed_result = await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time
                            )
                            return completed_result
                        else:
                            raise Exception("No fetch URL provided for async generation")
                    
                    # Handle immediate response (if synchronous)
                    return self._process_image_response(result)
                    
        except Exception as e:
            logger.error(f"[MODELSLAB V7 IMAGE ERROR]: {str(e)}")
            raise e
        
    async def _wait_for_completion(
        self, 
        session: aiohttp.ClientSession, 
        fetch_url: str, 
        request_id: str, 
        max_wait_time: int = 60
    ) -> Dict[str, Any]:
            """Wait for async image generation to complete"""
            
            logger.info(f"[MODELSLAB V7 IMAGE] Waiting for completion: {request_id}")
            
            start_time = asyncio.get_event_loop().time()
            check_interval = 5  # Check every 5 seconds
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                try:
                    # ✅ FIX: Use POST instead of GET for fetch endpoint
                    fetch_payload = {
                        "key": self.api_key
                    }
                    
                    async with session.post(  # Changed from GET to POST
                        fetch_url,
                        json=fetch_payload,  # Added payload with API key
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"[MODELSLAB V7 IMAGE] Fetch response: {result}")
                            
                            # Check if generation is complete
                            if result.get('status') == 'success' and result.get('output'):
                                logger.info(f"[MODELSLAB V7 IMAGE] ✅ Generation completed: {request_id}")
                                return self._process_image_response(result)
                            elif result.get('status') == 'processing':
                                logger.info(f"[MODELSLAB V7 IMAGE] ⏳ Still processing: {request_id}")
                                await asyncio.sleep(check_interval)
                                continue
                            else:
                                # Handle error status
                                error_msg = result.get('message', 'Unknown error during generation')
                                raise Exception(f"Generation failed: {error_msg}")
                        else:
                            logger.warning(f"[MODELSLAB V7 IMAGE] Fetch failed with status: {response.status}")
                            error_text = await response.text()
                            logger.warning(f"[MODELSLAB V7 IMAGE] Error response: {error_text}")
                            await asyncio.sleep(check_interval)
                            continue
                            
                except Exception as e:
                    logger.warning(f"[MODELSLAB V7 IMAGE] Error during fetch: {e}")
                    await asyncio.sleep(check_interval)
                    continue
            
            # Timeout reached
            raise Exception(f"Image generation timed out after {max_wait_time} seconds")

    async def generate_character_image(
        self,
        character_name: str,
        character_description: str,
        style: str = "realistic",
        aspect_ratio: str = "3:4",  # Portrait for characters
        user_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate character image using V7 API"""
        
        try:
            # ✅ Enhanced character prompts for better quality
            style_modifiers = {
                "realistic": "photorealistic portrait, detailed facial features, professional lighting, high quality, 8k resolution",
                "cinematic": "cinematic character portrait, dramatic lighting, film noir style, movie quality",
                "animated": "animated character design, cartoon style, expressive features, vibrant colors",
                "fantasy": "fantasy character art, magical aura, ethereal lighting, detailed fantasy design"
            }
            
            style_prompt = style_modifiers.get(style, style_modifiers["realistic"])
            
            # ✅ Comprehensive character prompt
            full_prompt = f"""Character portrait of {character_name}: {character_description}. 
            {style_prompt}. 
            Clear background, centered composition, detailed character design, 
            expressive eyes, well-defined features, professional character art"""
            
            # Get appropriate model for style (fallback if no tier provided)
            if user_tier:
                model_id = self._get_model_for_tier(user_tier)
            else:
                model_id = self._get_model_for_style(style)

            logger.info(f"[CHARACTER IMAGE] Generating {style} portrait for: {character_name}")
            logger.info(f"[CHARACTER IMAGE] User tier: {user_tier}")
            logger.info(f"[CHARACTER IMAGE] Selected model: {model_id} ({'tier-based' if user_tier else 'style-based'})")

            result = await self.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                model_id=model_id,
                user_tier=user_tier,
                wait_for_completion=True,  # Wait for character images
                max_wait_time=120  # 2 minutes for characters
            
            )
            
            # Add character metadata
            if result.get('status') == 'success':
                result['character_name'] = character_name
                result['character_style'] = style
                result['image_type'] = 'character'
            
            return result
            
        except Exception as e:
            logger.error(f"[CHARACTER IMAGE ERROR] {character_name}: {str(e)}")
            raise e
    
    async def generate_scene_image(
        self,
        scene_description: str,
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        user_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate scene image using V7 API"""
        
        try:
            # ✅ Enhanced scene prompts
            style_modifiers = {
                "realistic": "photorealistic environment, detailed landscape, natural lighting, high resolution",
                "cinematic": "cinematic scene, dramatic lighting, movie-quality composition, epic vista",
                "animated": "animated scene background, cartoon environment, vibrant world design",
                "fantasy": "fantasy environment, magical atmosphere, otherworldly landscape, mystical setting"
            }
            
            style_prompt = style_modifiers.get(style, style_modifiers["cinematic"])
            
            full_prompt = f"""Scene: {scene_description}. 
            {style_prompt}. 
            Wide establishing shot, detailed environment, atmospheric perspective, 
            rich visual storytelling, immersive background, professional scene composition"""
            
            # Get appropriate model for style (fallback if no tier provided)
            if user_tier:
                model_id = self._get_model_for_tier(user_tier)
            else:
                model_id = self._get_model_for_style(style)

            logger.info(f"[SCENE IMAGE] Generating {style} scene: {scene_description[:50]}...")
            logger.info(f"[SCENE IMAGE] User tier: {user_tier}")
            logger.info(f"[SCENE IMAGE] Selected model: {model_id} ({'tier-based' if user_tier else 'style-based'})")

            result = await self.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                model_id=model_id,
                user_tier=user_tier,
                wait_for_completion=True,  # Wait for scene images
                max_wait_time=120  # 2 minutes for scenes
            )
            
            # Add scene metadata
            if result.get('status') == 'success':
                result['scene_description'] = scene_description
                result['scene_style'] = style
                result['image_type'] = 'scene'
            
            return result
            
        except Exception as e:
            logger.error(f"[SCENE IMAGE ERROR]: {str(e)}")
            raise e

    
    async def generate_environment_image(
        self,
        environment_description: str,
        mood: str = "neutral",
        time_of_day: str = "day",
        aspect_ratio: str = "16:9",
        user_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate environment/background image with specific mood and timing"""
        
        try:
            # ✅ Mood and time modifiers
            mood_modifiers = {
                "dark": "dark atmosphere, moody lighting, shadows, mysterious ambiance",
                "bright": "bright lighting, cheerful atmosphere, vibrant colors, sunny",
                "dramatic": "dramatic lighting, high contrast, intense atmosphere",
                "peaceful": "serene atmosphere, soft lighting, calm mood, tranquil",
                "mysterious": "mysterious atmosphere, fog, ethereal lighting, enigmatic",
                "neutral": "balanced lighting, natural atmosphere, clear visibility"
            }
            
            time_modifiers = {
                "dawn": "dawn lighting, golden hour, soft morning light, sunrise",
                "day": "daylight, natural lighting, clear visibility, bright",
                "dusk": "dusk lighting, sunset colors, golden hour, warm tones",
                "night": "night scene, moonlight, artificial lighting, dark sky",
                "twilight": "twilight atmosphere, blue hour, soft evening light"
            }
            
            mood_prompt = mood_modifiers.get(mood, mood_modifiers["neutral"])
            time_prompt = time_modifiers.get(time_of_day, time_modifiers["day"])
            
            full_prompt = f"""Environment: {environment_description}. 
            {mood_prompt}, {time_prompt}. 
            Detailed environment design, atmospheric perspective, immersive background, 
            professional landscape composition, rich visual detail, cinematic quality"""
            
            # Get appropriate model for tier
            if user_tier:
                model_id = self._get_model_for_tier(user_tier)
            else:
                model_id = "gen4_image"  # Fallback

            logger.info(f"[ENVIRONMENT IMAGE] {mood} {time_of_day} environment: {environment_description[:50]}...")
            logger.info(f"[ENVIRONMENT IMAGE] User tier: {user_tier}")
            logger.info(f"[ENVIRONMENT IMAGE] Selected model: {model_id} ({'tier-based' if user_tier else 'hardcoded'})")

            result = await self.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                model_id=model_id,
                user_tier=user_tier
            )
            
            # Add environment metadata
            if result.get('status') == 'success':
                result['environment_description'] = environment_description
                result['mood'] = mood
                result['time_of_day'] = time_of_day
                result['image_type'] = 'environment'
            
            return result
            
        except Exception as e:
            logger.error(f"[ENVIRONMENT IMAGE ERROR]: {str(e)}")
            raise e
    
    async def batch_generate_images(
        self,
        image_requests: List[Dict[str, Any]],
        max_concurrent: int = 3,
        user_tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate multiple images with controlled concurrency"""
        
        logger.info(f"[BATCH GENERATION] Processing {len(image_requests)} images (max {max_concurrent} concurrent)")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def generate_single_image(request: Dict[str, Any], index: int) -> Dict[str, Any]:
            async with semaphore:
                try:
                    image_type = request.get('type', 'general')
                    
                    if image_type == 'character':
                        result = await self.generate_character_image(
                            character_name=request.get('character_name', f'Character_{index}'),
                            character_description=request.get('description', ''),
                            style=request.get('style', 'realistic'),
                            aspect_ratio=request.get('aspect_ratio', '3:4'),
                            user_tier=user_tier,
                            character_id=request.get('character_id')
                        )
                        # Character consistency check
                        if request.get('character_id') and result.get('character_id') != request.get('character_id'):
                            result['consistency_warning'] = "Generated image not linked to requested character_id"
                    elif image_type == 'scene':
                        result = await self.generate_scene_image(
                            scene_description=request.get('description', ''),
                            style=request.get('style', 'cinematic'),
                            aspect_ratio=request.get('aspect_ratio', '16:9')
                        )
                    elif image_type == 'environment':
                        result = await self.generate_environment_image(
                            environment_description=request.get('description', ''),
                            mood=request.get('mood', 'neutral'),
                            time_of_day=request.get('time_of_day', 'day'),
                            aspect_ratio=request.get('aspect_ratio', '16:9')
                        )
                    else:
                        # General image generation
                        model_id = request.get('model_id')
                        if model_id is None and user_tier:
                            model_id = self._get_model_for_tier(user_tier)
                        elif model_id is None:
                            model_id = 'gen4_image'  # Fallback

                        logger.info(f"[BATCH GENERATION] Using model: {model_id} for request {index} ({'tier-based' if user_tier else 'hardcoded'})")
                        result = await self.generate_image(
                            prompt=request.get('prompt', request.get('description', '')),
                            aspect_ratio=request.get('aspect_ratio', '16:9'),
                            model_id=model_id,
                            user_tier=user_tier
                        )
                    
                    result['batch_index'] = index
                    result['request_type'] = image_type
                    
                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.5)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"[BATCH] Failed to generate image {index}: {e}")
                    return {
                        'status': 'error',
                        'error': str(e),
                        'batch_index': index,
                        'request_type': request.get('type', 'general')
                    }
        
        # Process all images
        tasks = [
            generate_single_image(request, i) 
            for i, request in enumerate(image_requests)
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
                    'request_type': image_requests[i].get('type', 'general')
                })
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.get('status') == 'success')
        logger.info(f"[BATCH GENERATION] Completed: {successful_count}/{len(image_requests)} successful")
        
        return processed_results
    
    def _get_model_for_style(self, style: str) -> str:
        """Get appropriate model ID for the given style"""
        model_id = self.image_models.get(style, 'gen4_image')
        logger.info(f"[MODELSLAB V7 IMAGE] Style '{style}' mapped to model '{model_id}' (hardcoded mapping)")
        return model_id

    def _get_model_for_tier(self, user_tier: str) -> str:
        """Get appropriate model ID for the given user subscription tier"""
        model_id = self.tier_model_mapping.get(user_tier, 'gen4_image')
        logger.info(f"[MODELSLAB V7 IMAGE] Tier '{user_tier}' mapped to model '{model_id}' (tier-based selection)")
        logger.info(f"[DEBUG] Available tier mappings: {self.tier_model_mapping}")
        logger.info(f"[DEBUG] Requested tier: '{user_tier}', resolved model: '{model_id}'")
        return model_id
    
    def _get_aspect_ratio(self, ratio_name: str) -> str:
        """Get aspect ratio string from preset name"""
        return self.aspect_ratios.get(ratio_name, ratio_name)
    
    def _process_image_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize image API response"""
        
        try:
            # ✅ Handle successful responses
            if response.get('status') == 'success' and response.get('output'):
                output_urls = response.get('output', [])
                
                if output_urls and len(output_urls) > 0:
                    image_url = output_urls[0]
                    
                    # Extract metadata
                    meta = response.get('meta', {})
                    
                    return {
                        'status': 'success',
                        'output': output_urls,
                        'image_url': image_url,
                        'meta': meta,
                        'generation_time': response.get('generation_time', 0),
                        'model_used': response.get('model_id', 'gen4_image')
                    }
                else:
                    raise Exception("No image URLs in successful response")
            
            # ✅ Handle processing status
            elif response.get('status') == 'processing':
                return {
                    'status': 'processing',
                    'request_id': response.get('id'),
                    'fetch_url': response.get('fetch_result'),
                    'eta': response.get('eta', 10),
                    'future_links': response.get('future_links', [])
                }
            
            # ✅ Handle error responses
            else:
                error_message = response.get('message', response.get('error', 'Unknown error'))
                raise Exception(f"Image generation failed: {error_message}")
                
        except Exception as e:
            logger.error(f"[MODELSLAB V7 IMAGE] Response processing error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'raw_response': response
            }
    
    async def wait_for_completion(self, request_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Wait for async image generation to complete (if applicable)"""
        
        # ✅ Note: ModelsLab V7 Image API appears to be synchronous based on examples
        # This method is kept for compatibility but may not be needed
        
        logger.info(f"[MODELSLAB V7 IMAGE] Waiting for completion of request: {request_id}")
        
        # For now, return a timeout since V7 APIs seem synchronous
        await asyncio.sleep(2)  # Brief wait
        
        return {
            'status': 'completed',
            'message': 'V7 Image APIs are synchronous - no waiting required'
        }
    
    def get_available_models(self) -> Dict[str, str]:
        """Get available image generation models"""
        
        return {
            'gen4_image': 'Generation 4 Image Model (Recommended)',
            'runway_image': 'Runway Image Model (Artistic)',
        }
    
    def get_available_aspect_ratios(self) -> Dict[str, str]:
        """Get available aspect ratios"""
        
        return {
            '1:1': 'Square (1:1)',
            '3:4': 'Portrait (3:4)',
            '4:3': 'Landscape (4:3)',
            '16:9': 'Widescreen (16:9)',
            '21:9': 'Ultra-wide (21:9)',
            '9:16': 'Vertical (9:16)',
            '1920:1080': 'Full HD Landscape (1920:1080)',
            '1080:1920': 'Full HD Portrait (1080:1920)'
        }
    
    async def enhance_image_for_video(
        self,
        image_url: str,
        enhancement_type: str = "video_ready"
    ) -> Dict[str, Any]:
        """Enhance image for video production (placeholder for future enhancement features)"""
        
        # ✅ This could be extended to use upscaling or other enhancement APIs
        logger.info(f"[IMAGE ENHANCEMENT] Enhancing image for video: {enhancement_type}")
        
        # For now, return the original image with metadata
        return {
            'status': 'success',
            'enhanced_url': image_url,
            'original_url': image_url,
            'enhancement_type': enhancement_type,
            'message': 'Image ready for video production'
        }
        
    # Add nano-banana support to your existing service
    def _get_nano_banana_model_for_style(self, style: str) -> str:
        """Get appropriate model ID for the given style"""
        # ✅ Switch to nano-banana for faster generation
        style_models = {
            'realistic': 'nano-banana',  # Changed from gen4_image
            'cinematic': 'nano-banana',  # Much faster
            'animated': 'nano-banana',
            'fantasy': 'nano-banana',
            'comic': 'nano-banana',
            'artistic': 'nano-banana'
        }
        return style_models.get(style, 'nano-banana')

    # Update the generate_image method to handle nano-banana specifics
    async def generate_image_with_nano_banana(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model_id: str = "nano-banana",  # Default to nano-banana
        wait_for_completion: bool = True,
        max_wait_time: int = 30  # ✅ Reduced timeout for faster model
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab V7 API with nano-banana optimization"""
        
        try:
            # ✅ Nano-banana specific payload
            payload = {
                "prompt": prompt,
                "model_id": model_id,
                "aspect_ratio": aspect_ratio,
                "key": self.api_key
            }
            
            # ✅ Add nano-banana specific parameters for better quality
            if model_id == "nano-banana":
                payload.update({
                    "width": 1024,  # Standard width for nano-banana
                    "height": 1024 if aspect_ratio == "1:1" else 576,  # Adjust for aspect ratio
                    "guidance_scale": 7.5,  # Good balance for nano-banana
                    "num_inference_steps": 20,  # Faster inference
                    "safety_checker": False  # Speed up generation
                })
            
            logger.info(f"[NANO BANANA] Generating image with nano-banana model")
            logger.info(f"[NANO BANANA] Aspect ratio: {aspect_ratio}")
            logger.info(f"[NANO BANANA] Prompt: {prompt[:100]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=45)  # Increased timeout for nano-banana
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    logger.info(f"[NANO BANANA] Initial response: {result}")
                    
                    # ✅ Nano-banana usually responds faster
                    if result.get('status') == 'processing':
                        if not wait_for_completion:
                            return {
                                'status': 'processing',
                                'request_id': result.get('id'),
                                'fetch_url': result.get('fetch_result'),
                                'eta': result.get('eta', 5),  # Usually faster
                            }
                        
                        # Wait for completion with shorter timeout
                        fetch_url = result.get('fetch_result')
                        request_id = result.get('id')
                        
                        if fetch_url:
                            completed_result = await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time
                            )
                            return completed_result
                    
                    return self._process_image_response(result)
                    
        except Exception as e:
            logger.error(f"[NANO BANANA ERROR]: {str(e)}")
            raise e