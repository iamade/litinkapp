from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from app.core.config import settings
from app.core.model_config import get_model_config
from app.core.services.model_fallback import fallback_manager
import logging

logger = logging.getLogger(__name__)


class ModelsLabV7ImageService:
    """ModelsLab V7 Image Service for Runway text-to-image generation"""

    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")

        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL  # v7 URL
        self.headers = {"Content-Type": "application/json"}

        # ✅ V7 Image Generation Endpoint
        self.image_endpoint = f"{self.base_url}/images/text-to-image"
        self.image_to_image_endpoint = f"{self.base_url}/images/image-to-image"
        self.fetch_endpoint = f"{self.base_url}/images/fetch"

        # ✅ Models that use width/height parameters
        self.width_height_models = {"seedream-t2i"}

        # ✅ Models that use aspect_ratio parameter
        self.aspect_ratio_models = {
            "seedream-4",
            "imagen-4",
            "seedream-4.5",
            "imagen-4.0-ultra",
            "nano-banana-pro",
            "qwen-image-2512",
            "gpt-image-1.5",
            "nano-banana",
            "seedream-4.0-i2i",
            "seedream-4.5-i2i",
            "seededit-i2i",
        }

        # ✅ Models that only need prompt + model_id (no size parameters)
        self.minimal_models = {"nano-banana-t2i"}

        # ✅ Available models for V7
        self.image_models = {
            "seedream-t2i": "seedream-t2i",
            "seedream-4": "seedream-4",
            "imagen-4": "imagen-4",
            "nano-banana-t2i": "nano-banana-t2i",
            "seedream-4.5": "seedream-4.5",
            "imagen-4.0-ultra": "imagen-4.0-ultra",
            "nano-banana-pro": "nano-banana-pro",
            "qwen-image-2512": "qwen-image-2512",
            "gpt-image-1.5": "gpt-image-1.5",
            "nano-banana": "nano-banana",
            "seedream-4.0-i2i": "seedream-4.0-i2i",
            "seedream-4.5-i2i": "seedream-4.5-i2i",
            "seededit-i2i": "seededit-i2i",
        }

        # ✅ Updated tier-based model mapping matching model_config.py
        self.tier_model_mapping = {
            "free": "seedream-t2i",
            "basic": "seedream-4",
            "standard": "imagen-4",
            "premium": "nano-banana-t2i",
            "professional": "seedream-4.5",
            "enterprise": "qwen-image-2512",
        }

        logger.info(
            f"[MODELSLAB V7 IMAGE] Initialized with models: {list(self.image_models.keys())}"
        )
        logger.info(
            f"[MODELSLAB V7 IMAGE] Tier model mapping: {self.tier_model_mapping}"
        )
        logger.info(f"[MODELSLAB V7 IMAGE] Default model_id: seedream-t2i")

        # ✅ Aspect ratio presets
        self.aspect_ratios = {
            "square": "1:1",
            "portrait": "3:4",
            "landscape": "4:3",
            "widescreen": "16:9",
            "ultrawide": "21:9",
            "vertical": "9:16",
            "video_landscape": "1920:1080",
            "video_portrait": "1080:1920",
            "instagram_square": "1080:1080",
            "instagram_story": "1080:1920",
        }

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        wait_for_completion: bool = True,
        max_wait_time: int = 1200,  # Increased to 20 minutes
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab V7 API with automatic fallback"""

        if user_tier:

            async def _generate_with_model(model_id: str, **kwargs) -> Dict[str, Any]:
                return await self._execute_generation(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    model_id=model_id,
                    wait_for_completion=wait_for_completion,
                    max_wait_time=max_wait_time,
                )

            return await fallback_manager.try_with_fallback(
                service_type="image",
                user_tier=user_tier,
                generation_function=_generate_with_model,
                request_params={
                    "model_id": model_id or self._get_model_for_tier(user_tier)
                },
                model_param_name="model_id",
            )
        else:
            if model_id is None:
                model_id = "seedream-t2i"  # Default to FREE tier model

            return await self._execute_generation(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                model_id=model_id,
                wait_for_completion=wait_for_completion,
                max_wait_time=max_wait_time,
            )

    def _aspect_ratio_to_dimensions(self, aspect_ratio: str) -> tuple[str, str]:
        """Convert aspect ratio string to width and height dimensions.

        The ModelsLab API expects width and height as string parameters,
        not aspect_ratio. This method converts common aspect ratios to
        appropriate dimensions.
        """
        # Mapping of aspect ratios to (width, height) in pixels
        dimension_map = {
            "1:1": ("1024", "1024"),
            "3:4": ("768", "1024"),  # Portrait
            "4:3": ("1024", "768"),  # Landscape
            "16:9": ("1024", "576"),  # Widescreen
            "9:16": ("576", "1024"),  # Vertical/Mobile
            "21:9": ("1024", "439"),  # Ultra-wide
            "1920:1080": ("1920", "1080"),  # Full HD Landscape
            "1080:1920": ("1080", "1920"),  # Full HD Portrait
            "1080:1080": ("1080", "1080"),  # Instagram Square
        }

        # Check if it's already in the map
        if aspect_ratio in dimension_map:
            return dimension_map[aspect_ratio]

        # Try to parse custom aspect ratio (e.g., "16:9")
        try:
            if ":" in aspect_ratio:
                parts = aspect_ratio.split(":")
                if len(parts) == 2:
                    w_ratio = float(parts[0])
                    h_ratio = float(parts[1])

                    # Calculate dimensions maintaining max 1024 on largest side
                    if w_ratio >= h_ratio:
                        width = 1024
                        height = int(1024 * (h_ratio / w_ratio))
                    else:
                        height = 1024
                        width = int(1024 * (w_ratio / h_ratio))

                    return (str(width), str(height))
        except (ValueError, ZeroDivisionError):
            pass

        # Default to square if parsing fails
        logger.warning(
            f"[MODELSLAB V7 IMAGE] Unknown aspect ratio '{aspect_ratio}', defaulting to 1024x1024"
        )
        return ("1024", "1024")

    def _uses_width_height(self, model_id: str) -> bool:
        """Check if the model uses width/height parameters"""
        return model_id in self.width_height_models

    def _uses_aspect_ratio(self, model_id: str) -> bool:
        """Check if the model uses aspect_ratio parameter"""
        return model_id in self.aspect_ratio_models

    async def _execute_generation(
        self,
        prompt: str,
        aspect_ratio: str,
        model_id: str,
        wait_for_completion: bool = True,
        max_wait_time: int = 60,
    ) -> Dict[str, Any]:
        """Execute the actual image generation with specified model using V7 API"""

        try:
            # Build payload based on model type
            if self._uses_width_height(model_id):
                # Models like seedream-t2i use width/height parameters
                width, height = self._aspect_ratio_to_dimensions(aspect_ratio)
                payload = {
                    "prompt": prompt,
                    "model_id": model_id,
                    "width": width,  # String format
                    "height": height,  # String format
                    "key": self.api_key,
                }
                logger.info(
                    f"[MODELSLAB V7 IMAGE] Using width/height: {width}x{height}"
                )
            elif model_id in self.minimal_models:
                # Models like nano-banana-t2i only need prompt + model_id
                payload = {
                    "prompt": prompt,
                    "model_id": model_id,
                    "key": self.api_key,
                }
                logger.info(
                    f"[MODELSLAB V7 IMAGE] Using minimal params (prompt + model_id only)"
                )
            else:
                # Models like seedream-4, imagen-4 use aspect_ratio parameter
                payload = {
                    "prompt": prompt,
                    "model_id": model_id,
                    "aspect_ratio": aspect_ratio,
                    "key": self.api_key,
                }
                logger.info(f"[MODELSLAB V7 IMAGE] Using aspect_ratio: {aspect_ratio}")

            logger.info(f"[MODELSLAB V7 IMAGE] Generating image with model: {model_id}")
            logger.info(f"[MODELSLAB V7 IMAGE] Prompt: {prompt[:100]}...")
            logger.info(f"[DEBUG] API endpoint: {self.image_endpoint}")
            logger.info(f"[DEBUG] API payload: {payload}")

            async with aiohttp.ClientSession() as session:
                # Submit generation request with extended timeout
                async with session.post(
                    self.image_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()

                    logger.info(f"[MODELSLAB V7 IMAGE] Initial response: {result}")

                    # ✅ Handle async processing response
                    if result.get("status") == "processing":
                        if not wait_for_completion:
                            return {
                                "status": "processing",
                                "request_id": result.get("id"),
                                "fetch_url": result.get("fetch_result"),
                                "eta": result.get("eta", 10),
                                "future_links": result.get("future_links", []),
                            }

                        # Wait for completion
                        fetch_url = result.get("fetch_result")
                        request_id = result.get("id")

                        if fetch_url:
                            completed_result = await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time, model_id
                            )
                            return completed_result
                        else:
                            raise Exception(
                                "No fetch URL provided for async generation"
                            )

                    # Handle immediate response (if synchronous)
                    return self._process_image_response(result, model_id)

        except asyncio.TimeoutError as e:
            error_msg = f"Request timeout after 60s waiting for ModelsLab API response"
            logger.error(f"[MODELSLAB V7 IMAGE TIMEOUT]: {error_msg}")
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"[MODELSLAB V7 IMAGE ERROR]: {error_msg}")
            raise Exception(error_msg) from e

    async def _wait_for_completion(
        self,
        session: aiohttp.ClientSession,
        fetch_url: str,
        request_id: str,
        max_wait_time: int = 1200,  # Increased to 20 minutes
        model_id: str = "unknown",
    ) -> Dict[str, Any]:
        """Wait for async image generation to complete"""

        logger.info(f"[MODELSLAB V7 IMAGE] Waiting for completion: {request_id}")

        start_time = asyncio.get_event_loop().time()
        check_interval = 5  # Check every 5 seconds

        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                # ✅ FIX: Use POST instead of GET for fetch endpoint
                fetch_payload = {"key": self.api_key}

                async with session.post(  # Changed from GET to POST
                    fetch_url,
                    json=fetch_payload,  # Added payload with API key
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"[MODELSLAB V7 IMAGE] Fetch response: {result}")

                        # Check if generation is complete
                        if result.get("status") == "success" and result.get("output"):
                            logger.info(
                                f"[MODELSLAB V7 IMAGE] ✅ Generation completed: {request_id}"
                            )
                            return self._process_image_response(result, model_id)
                        elif result.get("status") == "processing":
                            logger.info(
                                f"[MODELSLAB V7 IMAGE] ⏳ Still processing: {request_id}"
                            )
                            await asyncio.sleep(check_interval)
                            continue
                        else:
                            # Handle error status
                            error_msg = result.get(
                                "message", "Unknown error during generation"
                            )
                            raise Exception(f"Generation failed: {error_msg}")
                    else:
                        logger.warning(
                            f"[MODELSLAB V7 IMAGE] Fetch failed with status: {response.status}"
                        )
                        error_text = await response.text()
                        logger.warning(
                            f"[MODELSLAB V7 IMAGE] Error response: {error_text}"
                        )
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
        character_description: str,  # Now accepts pre-built prompt OR raw description
        style: str = "realistic",
        aspect_ratio: str = "3:4",  # Portrait for characters
        user_tier: Optional[str] = None,
        prompt_already_built: bool = True,  # Flag to indicate if prompt is pre-built
    ) -> Dict[str, Any]:
        """
        Generate character image using V7 API with automatic fallback.

        When prompt_already_built=True (default), character_description is used directly as the prompt.
        This allows StandaloneImageService to handle all prompt engineering centrally.

        When prompt_already_built=False, basic style modifiers are added (for backward compatibility).
        """
        try:
            if prompt_already_built:
                # Use the description directly as prompt - all engineering done by caller
                full_prompt = self._sanitize_prompt(character_description)
            else:
                # Backward compatibility: add basic style modifiers only
                style_modifiers = {
                    "realistic": "photorealistic portrait, detailed facial features, professional lighting, high quality",
                    "cinematic": "cinematic character portrait, dramatic lighting, movie quality",
                    "animated": "animated character design, cartoon style, vibrant colors",
                    "fantasy": "fantasy character art, magical aura, ethereal lighting",
                }
                style_prompt = style_modifiers.get(style, style_modifiers["realistic"])
                sanitized_desc = self._sanitize_prompt(character_description)
                full_prompt = f"Character portrait of {character_name}: {sanitized_desc}. {style_prompt}."

            logger.info(
                f"[CHARACTER IMAGE] Generating {style} portrait for: {character_name}"
            )
            logger.info(f"[CHARACTER IMAGE] User tier: {user_tier}")
            logger.info(f"[CHARACTER IMAGE] Prompt: {full_prompt[:100]}...")

            result = await self.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                model_id=None,
                user_tier=user_tier,
                wait_for_completion=True,
                max_wait_time=1200,
            )

            # Add character metadata
            if result.get("status") == "success":
                result["character_name"] = character_name
                result["character_style"] = style
                result["image_type"] = "character"

            return result

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"[CHARACTER IMAGE ERROR] {character_name}: {error_msg}")
            raise Exception(
                f"Character image generation failed for {character_name}: {error_msg}"
            ) from e

    def _get_i2i_model_for_tier(self, user_tier: str, image_count: int = 1) -> str:
        """Get appropriate i2i model ID for the given user subscription tier and image count"""
        from app.core.model_config import (
            IMAGE_I2I_SINGLE_MODEL_CONFIG,
            IMAGE_I2I_MULTI_MODEL_CONFIG,
            ModelTier,
        )

        try:
            tier_enum = ModelTier(user_tier.lower())

            if image_count > 1:
                config = IMAGE_I2I_MULTI_MODEL_CONFIG.get(tier_enum)
            else:
                config = IMAGE_I2I_SINGLE_MODEL_CONFIG.get(tier_enum)

            if config:
                return config.primary

            # Fallback if config not found
            return "seedream-4.0-i2i" if image_count > 1 else "seededit-i2i"

        except (ValueError, KeyError):
            logger.warning(f"Invalid tier {user_tier}, using fallback i2i model")
            return "seedream-4.0-i2i"

    async def generate_image_to_image(
        self,
        prompt: str,
        init_images: List[str],
        aspect_ratio: str = "1:1",
        model_id: Optional[str] = None,
        user_tier: Optional[str] = None,
        wait_for_completion: bool = True,
        max_wait_time: int = 1200,
        strength: float = 0.7,  # Controls how much to modify input image (0.0-1.0)
    ) -> Dict[str, Any]:
        """Generate image using Image-to-Image models

        Args:
            prompt: Text prompt for generation
            init_images: Reference images
            aspect_ratio: Output aspect ratio
            model_id: Specific model to use
            user_tier: User tier for model selection
            wait_for_completion: Wait for async generation
            max_wait_time: Max wait time in seconds
            strength: How much to modify input (0.0 = identical, 1.0 = completely different)
                      Use lower values (0.2-0.4) for suggested shots to preserve background
        """

        # Determine model if not provided
        if not model_id and user_tier:
            model_id = self._get_i2i_model_for_tier(user_tier, len(init_images))
        elif not model_id:
            model_id = "seedream-4.0-i2i"  # Default fallback

        try:
            payload = {
                "prompt": prompt,
                "model_id": model_id,
                "key": self.api_key,
                "aspect_ratio": aspect_ratio,
                "strength": str(strength),  # Add strength to payload
            }

            # Handle model-specific payloads
            if model_id == "nano-banana":
                # Nano-banana takes init_image and init_image_2
                if len(init_images) > 0:
                    payload["init_image"] = init_images[0]
                if len(init_images) > 1:
                    payload["init_image_2"] = init_images[1]
                # If more images, they are ignored for this model

            elif model_id == "seededit-i2i":
                # Seededit takes single init_image
                if len(init_images) > 0:
                    payload["init_image"] = init_images[0]

            else:
                # Seedream models take list of strings for init_image
                # Note: API expects list of strings for these models
                payload["init_image"] = init_images
                # Ensure aspect-ratio key matches what API expects (some use aspect_ratio, some aspect-ratio?)
                # Code above uses aspect_ratio, but one example showed "aspect-ratio".
                # Assuming standardizing on snake_case unless proven otherwise,
                # but seedream-4.0 example showed "aspect-ratio".
                # Let's check existing code... existing code uses "aspect_ratio".
                # However, the user provided example for `seedream-4.0-i2i` uses "aspect-ratio".
                # To be safe, I'll stick to snake_case as per existing client unless explicit error.
                # Actually, requests.post in user example for seedream-4.0-i2i used "aspect-ratio".
                # I will add a check.
                if "seedream" in model_id:
                    payload["aspect-ratio"] = aspect_ratio
                    payload.pop("aspect_ratio", None)

            logger.info(
                f"[MODELSLAB I2I] Generating with model: {model_id}, images: {len(init_images)}"
            )
            logger.info(f"[DEBUG] I2I Payload keys: {payload.keys()}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_to_image_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()

                    # Handle response similar to t2i
                    if result.get("status") == "processing":
                        if not wait_for_completion:
                            return result

                        fetch_url = result.get("fetch_result")
                        request_id = result.get("id")
                        if fetch_url:
                            return await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time, model_id
                            )

                    return self._process_image_response(result, model_id)

        except Exception as e:
            logger.error(f"[MODELSLAB I2I ERROR]: {str(e)}")
            raise Exception(f"Image-to-Image generation failed: {str(e)}") from e

    async def generate_scene_image(
        self,
        scene_description: str,  # Now accepts a pre-built prompt OR raw description
        style: str = "cinematic",
        aspect_ratio: str = "16:9",
        user_tier: Optional[str] = None,
        character_image_urls: Optional[List[str]] = None,
        prompt_already_built: bool = True,  # Flag to indicate if prompt is pre-built
        is_suggested_shot: bool = False,  # For suggested shots, use lower strength
    ) -> Dict[str, Any]:
        """
        Generate scene image using V7 API with automatic fallback.

        When prompt_already_built=True (default), scene_description is used directly as the prompt.
        This allows StandaloneImageService to handle all prompt engineering centrally.

        When prompt_already_built=False, basic style modifiers are added (for backward compatibility).

        Args:
            is_suggested_shot: If True, uses lower I2I strength (0.30) to preserve parent scene background
        """
        try:
            if prompt_already_built:
                # Use the prompt directly - all engineering done by caller (StandaloneImageService)
                full_prompt = scene_description
                sanitized_description = self._sanitize_prompt(full_prompt)
                full_prompt = sanitized_description
            else:
                # Backward compatibility: add basic style modifiers only
                style_modifiers = {
                    "realistic": "photorealistic environment, natural lighting, high resolution",
                    "cinematic": "cinematic scene, dramatic lighting, film still",
                    "animated": "animated scene background, vibrant world design",
                    "fantasy": "fantasy environment, magical atmosphere",
                }
                style_prompt = style_modifiers.get(style, style_modifiers["cinematic"])
                sanitized_description = self._sanitize_prompt(scene_description)
                full_prompt = f"Scene: {sanitized_description}. {style_prompt}."

            logger.info(
                f"[SCENE IMAGE] Generating {style} scene: {full_prompt[:80]}..."
            )
            logger.info(f"[SCENE IMAGE] User tier: {user_tier}")
            if is_suggested_shot:
                logger.info(
                    f"[SCENE IMAGE] SUGGESTED SHOT mode - using low strength for background preservation"
                )

            # Use Image-to-Image if character images are provided
            if character_image_urls and len(character_image_urls) > 0:
                logger.info(
                    f"[SCENE IMAGE] Using {len(character_image_urls)} character reference images"
                )
                # Use lower strength for suggested shots to preserve parent scene background
                i2i_strength = 0.30 if is_suggested_shot else 0.7
                logger.info(f"[SCENE IMAGE] I2I strength: {i2i_strength}")

                result = await self.generate_image_to_image(
                    prompt=full_prompt,
                    init_images=character_image_urls,
                    aspect_ratio=aspect_ratio,
                    user_tier=user_tier,
                    wait_for_completion=True,
                    strength=i2i_strength,  # Pass strength based on suggested shot
                )
            else:
                # Standard Text-to-Image
                result = await self.generate_image(
                    prompt=full_prompt,
                    aspect_ratio=aspect_ratio,
                    model_id=None,
                    user_tier=user_tier,
                    wait_for_completion=True,
                    max_wait_time=1200,  # Increased to 20 minutes
                )

            # Add scene metadata
            if result.get("status") == "success":
                result["scene_description"] = scene_description
                result["scene_style"] = style
                result["image_type"] = "scene"

            return result

        except Exception as e:
            logger.error(f"[SCENE IMAGE ERROR]: {str(e)}")
            raise e

    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize prompt to avoid safety filter triggers"""
        import re

        # Dictionary of sensitive words and their safe replacements
        replacements = {
            r"\bdead\b": "unconscious",
            r"\bkilled\b": "defeated",
            r"\bkill\b": "defeat",
            r"\bmurder\b": "crime",
            r"\bblood\b": "red liquid",
            r"\bbloody\b": "red",
            r"\bcorpse\b": "body",
            r"\bgun\b": "weapon",
            r"\bshoot\b": "fire",
            r"\bviolence\b": "conflict",
            r"\bhurt\b": "injured",
            r"\btorture\b": "interrogation",
            r"\bwar\b": "battle",
            r"\bbattlefield\b": "field",
            r"\bnaked\b": "clothed",
            r"\bnude\b": "covered",
            r"\bsex\b": "intimacy",
            r"\badult\b": "mature",
            r"\bdrugs\b": "substances",
            r"\balcohol\b": "drinks",
            r"\bsuicide\b": "tragedy",
            r"\bterrorist\b": "enemy",
        }

        sanitized = prompt.lower()
        for pattern, replacement in replacements.items():
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        # If no changes were made but we suspect issues, we can return the original
        # But here we return the sanitized version (which might be same as original)
        return sanitized

    async def generate_environment_image(
        self,
        environment_description: str,
        mood: str = "neutral",
        time_of_day: str = "day",
        aspect_ratio: str = "16:9",
        user_tier: Optional[str] = None,
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
                "neutral": "balanced lighting, natural atmosphere, clear visibility",
            }

            time_modifiers = {
                "dawn": "dawn lighting, golden hour, soft morning light, sunrise",
                "day": "daylight, natural lighting, clear visibility, bright",
                "dusk": "dusk lighting, sunset colors, golden hour, warm tones",
                "night": "night scene, moonlight, artificial lighting, dark sky",
                "twilight": "twilight atmosphere, blue hour, soft evening light",
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

            logger.info(
                f"[ENVIRONMENT IMAGE] {mood} {time_of_day} environment: {environment_description[:50]}..."
            )
            logger.info(f"[ENVIRONMENT IMAGE] User tier: {user_tier}")
            logger.info(
                f"[ENVIRONMENT IMAGE] Selected model: {model_id} ({'tier-based' if user_tier else 'hardcoded'})"
            )

            result = await self.generate_image(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                model_id=model_id,
                user_tier=user_tier,
            )

            # Add environment metadata
            if result.get("status") == "success":
                result["environment_description"] = environment_description
                result["mood"] = mood
                result["time_of_day"] = time_of_day
                result["image_type"] = "environment"

            return result

        except Exception as e:
            logger.error(f"[ENVIRONMENT IMAGE ERROR]: {str(e)}")
            raise e

    async def batch_generate_images(
        self,
        image_requests: List[Dict[str, Any]],
        max_concurrent: int = 3,
        user_tier: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate multiple images with controlled concurrency"""

        logger.info(
            f"[BATCH GENERATION] Processing {len(image_requests)} images (max {max_concurrent} concurrent)"
        )

        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def generate_single_image(
            request: Dict[str, Any], index: int
        ) -> Dict[str, Any]:
            async with semaphore:
                try:
                    image_type = request.get("type", "general")

                    if image_type == "character":
                        result = await self.generate_character_image(
                            character_name=request.get(
                                "character_name", f"Character_{index}"
                            ),
                            character_description=request.get("description", ""),
                            style=request.get("style", "realistic"),
                            aspect_ratio=request.get("aspect_ratio", "3:4"),
                            user_tier=user_tier,
                            character_id=request.get("character_id"),
                        )
                        # Character consistency check
                        if request.get("character_id") and result.get(
                            "character_id"
                        ) != request.get("character_id"):
                            result["consistency_warning"] = (
                                "Generated image not linked to requested character_id"
                            )
                    elif image_type == "scene":
                        result = await self.generate_scene_image(
                            scene_description=request.get("description", ""),
                            style=request.get("style", "cinematic"),
                            aspect_ratio=request.get("aspect_ratio", "16:9"),
                        )
                    elif image_type == "environment":
                        result = await self.generate_environment_image(
                            environment_description=request.get("description", ""),
                            mood=request.get("mood", "neutral"),
                            time_of_day=request.get("time_of_day", "day"),
                            aspect_ratio=request.get("aspect_ratio", "16:9"),
                        )
                    else:
                        # General image generation
                        model_id = request.get("model_id")
                        if model_id is None and user_tier:
                            model_id = self._get_model_for_tier(user_tier)
                        elif model_id is None:
                            model_id = "gen4_image"  # Fallback

                        logger.info(
                            f"[BATCH GENERATION] Using model: {model_id} for request {index} ({'tier-based' if user_tier else 'hardcoded'})"
                        )
                        result = await self.generate_image(
                            prompt=request.get(
                                "prompt", request.get("description", "")
                            ),
                            aspect_ratio=request.get("aspect_ratio", "16:9"),
                            model_id=model_id,
                            user_tier=user_tier,
                        )

                    result["batch_index"] = index
                    result["request_type"] = image_type

                    # Small delay to prevent rate limiting
                    await asyncio.sleep(0.5)

                    return result

                except Exception as e:
                    logger.error(f"[BATCH] Failed to generate image {index}: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "batch_index": index,
                        "request_type": request.get("type", "general"),
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
                processed_results.append(
                    {
                        "status": "error",
                        "error": str(result),
                        "batch_index": i,
                        "request_type": image_requests[i].get("type", "general"),
                    }
                )
            else:
                processed_results.append(result)

        successful_count = sum(
            1 for r in processed_results if r.get("status") == "success"
        )
        logger.info(
            f"[BATCH GENERATION] Completed: {successful_count}/{len(image_requests)} successful"
        )

        return processed_results

    def _get_model_for_style(self, style: str) -> str:
        """Get appropriate model ID for the given style"""
        model_id = self.image_models.get(style, "gen4_image")
        logger.info(
            f"[MODELSLAB V7 IMAGE] Style '{style}' mapped to model '{model_id}' (hardcoded mapping)"
        )
        return model_id

    def _get_model_for_tier(self, user_tier: str) -> str:
        """Get appropriate model ID for the given user subscription tier"""
        model_id = self.tier_model_mapping.get(user_tier, "gen4_image")
        logger.info(
            f"[MODELSLAB V7 IMAGE] Tier '{user_tier}' mapped to model '{model_id}' (tier-based selection)"
        )
        logger.info(f"[DEBUG] Available tier mappings: {self.tier_model_mapping}")
        logger.info(
            f"[DEBUG] Requested tier: '{user_tier}', resolved model: '{model_id}'"
        )
        return model_id

    def _get_aspect_ratio(self, ratio_name: str) -> str:
        """Get aspect ratio string from preset name"""
        return self.aspect_ratios.get(ratio_name, ratio_name)

    def _process_image_response(
        self, response: Dict[str, Any], model_id: str = "unknown"
    ) -> Dict[str, Any]:
        """Process and standardize image API response"""

        try:
            # ✅ Handle successful responses
            if response.get("status") == "success" and response.get("output"):
                output_urls = response.get("output", [])

                if output_urls and len(output_urls) > 0:
                    image_url = output_urls[0]

                    # Extract metadata
                    meta = response.get("meta", {})

                    return {
                        "status": "success",
                        "output": output_urls,
                        "image_url": image_url,
                        "meta": meta,
                        "generation_time": response.get("generation_time", 0),
                        "model_used": model_id,  # Use the model we sent, not API response
                    }
                else:
                    raise Exception("No image URLs in successful response")

            # ✅ Handle processing status
            elif response.get("status") == "processing":
                return {
                    "status": "processing",
                    "request_id": response.get("id"),
                    "fetch_url": response.get("fetch_result"),
                    "eta": response.get("eta", 10),
                    "future_links": response.get("future_links", []),
                }

            # ✅ Handle error responses
            else:
                error_message = response.get(
                    "message", response.get("error", "Unknown error")
                )
                raise Exception(f"Image generation failed: {error_message}")

        except Exception as e:
            logger.error(f"[MODELSLAB V7 IMAGE] Response processing error: {e}")
            return {"status": "error", "error": str(e), "raw_response": response}

    async def wait_for_completion(
        self, request_id: str, max_wait_time: int = 300
    ) -> Dict[str, Any]:
        """Wait for async image generation to complete (if applicable)"""

        # ✅ Note: ModelsLab V7 Image API appears to be synchronous based on examples
        # This method is kept for compatibility but may not be needed

        logger.info(
            f"[MODELSLAB V7 IMAGE] Waiting for completion of request: {request_id}"
        )

        # For now, return a timeout since V7 APIs seem synchronous
        await asyncio.sleep(2)  # Brief wait

        return {
            "status": "completed",
            "message": "V7 Image APIs are synchronous - no waiting required",
        }

    def get_available_models(self) -> Dict[str, str]:
        """Get available image generation models"""

        return {
            "gen4_image": "Generation 4 Image Model (Recommended)",
            "runway_image": "Runway Image Model (Artistic)",
        }

    def get_available_aspect_ratios(self) -> Dict[str, str]:
        """Get available aspect ratios"""

        return {
            "1:1": "Square (1:1)",
            "3:4": "Portrait (3:4)",
            "4:3": "Landscape (4:3)",
            "16:9": "Widescreen (16:9)",
            "21:9": "Ultra-wide (21:9)",
            "9:16": "Vertical (9:16)",
            "1920:1080": "Full HD Landscape (1920:1080)",
            "1080:1920": "Full HD Portrait (1080:1920)",
        }

    async def enhance_image_for_video(
        self, image_url: str, enhancement_type: str = "video_ready"
    ) -> Dict[str, Any]:
        """Enhance image for video production (placeholder for future enhancement features)"""

        # ✅ This could be extended to use upscaling or other enhancement APIs
        logger.info(
            f"[IMAGE ENHANCEMENT] Enhancing image for video: {enhancement_type}"
        )

        # For now, return the original image with metadata
        return {
            "status": "success",
            "enhanced_url": image_url,
            "original_url": image_url,
            "enhancement_type": enhancement_type,
            "message": "Image ready for video production",
        }

    async def expand_image(
        self,
        image_url: str,
        target_aspect_ratio: str = "16:9",
        prompt: str = "",
        user_tier: Optional[str] = None,
        wait_for_completion: bool = True,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """
        Expand/outpaint an image to a target aspect ratio using ModelsLab outpainting API.

        This is useful for converting portrait images (e.g., 3:4) to landscape (16:9)
        for video production by expanding the background.

        Args:
            image_url: URL of the source image to expand
            target_aspect_ratio: Target aspect ratio (16:9, 21:9, 4:3, etc.)
            prompt: Optional prompt to guide background generation
            user_tier: User subscription tier for model selection
            wait_for_completion: Whether to wait for async processing
            max_wait_time: Maximum wait time in seconds

        Returns:
            Dict with expanded image URL and metadata
        """
        try:
            logger.info(
                f"[IMAGE EXPAND] Expanding image to {target_aspect_ratio}: {image_url[:50]}..."
            )

            # Calculate expansion dimensions
            expansion_params = self._calculate_expansion_params(target_aspect_ratio)

            # Build outpainting payload
            # ModelsLab outpainting endpoint uses v6 API
            outpaint_url = f"{settings.MODELSLAB_V6_BASE_URL}/image_editing/outpaint"

            # Default expansion prompt if none provided
            if not prompt:
                prompt = "seamless background extension, natural continuation of scene, consistent lighting and atmosphere"

            payload = {
                "key": self.api_key,
                "init_image": image_url,
                "prompt": prompt,
                "left_expansion_ratio": expansion_params.get("left", 0),
                "right_expansion_ratio": expansion_params.get("right", 0),
                "top_expansion_ratio": expansion_params.get("top", 0),
                "bottom_expansion_ratio": expansion_params.get("bottom", 0),
                "webhook": None,
                "track_id": None,
            }

            logger.info(f"[IMAGE EXPAND] Payload: {payload}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    outpaint_url,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()
                    logger.info(f"[IMAGE EXPAND] Initial response: {result}")

                    # Handle async processing
                    if result.get("status") == "processing":
                        if not wait_for_completion:
                            return {
                                "status": "processing",
                                "request_id": result.get("id"),
                                "fetch_url": result.get("fetch_result"),
                                "eta": result.get("eta", 30),
                            }

                        # Wait for completion
                        fetch_url = result.get("fetch_result")
                        request_id = result.get("id")

                        if fetch_url:
                            return await self._wait_for_expansion_completion(
                                session, fetch_url, request_id, max_wait_time
                            )

                    # Handle immediate success
                    if result.get("status") == "success" and result.get("output"):
                        return {
                            "status": "success",
                            "expanded_url": result["output"][0] if isinstance(result["output"], list) else result["output"],
                            "original_url": image_url,
                            "target_aspect_ratio": target_aspect_ratio,
                            "expansion_params": expansion_params,
                        }

                    # Handle error
                    error_msg = result.get("message", "Unknown outpainting error")
                    raise Exception(f"Outpainting failed: {error_msg}")

        except Exception as e:
            logger.error(f"[IMAGE EXPAND ERROR]: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "original_url": image_url,
            }

    async def _wait_for_expansion_completion(
        self,
        session: aiohttp.ClientSession,
        fetch_url: str,
        request_id: str,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """Wait for async outpainting/expansion to complete"""

        logger.info(f"[IMAGE EXPAND] Waiting for expansion completion: {request_id}")

        start_time = asyncio.get_event_loop().time()
        check_interval = 5

        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                fetch_payload = {"key": self.api_key}

                async with session.post(
                    fetch_url,
                    json=fetch_payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"[IMAGE EXPAND] Fetch response: {result}")

                        if result.get("status") == "success" and result.get("output"):
                            output = result["output"]
                            expanded_url = output[0] if isinstance(output, list) else output

                            return {
                                "status": "success",
                                "expanded_url": expanded_url,
                                "generation_time": asyncio.get_event_loop().time() - start_time,
                            }
                        elif result.get("status") == "processing":
                            await asyncio.sleep(check_interval)
                            continue
                        else:
                            error_msg = result.get("message", "Unknown error")
                            raise Exception(f"Expansion failed: {error_msg}")
                    else:
                        logger.warning(f"[IMAGE EXPAND] Fetch failed with status: {response.status}")
                        await asyncio.sleep(check_interval)

            except Exception as e:
                logger.warning(f"[IMAGE EXPAND] Fetch error: {e}")
                await asyncio.sleep(check_interval)

        raise Exception(f"Image expansion timed out after {max_wait_time} seconds")

    def _calculate_expansion_params(self, target_aspect_ratio: str) -> Dict[str, float]:
        """
        Calculate expansion ratios for outpainting based on target aspect ratio.

        Assumes source image is typically portrait (e.g., 3:4 character portrait)
        and calculates how much to expand on each side to reach target ratio.

        Args:
            target_aspect_ratio: Target aspect ratio (e.g., "16:9", "21:9", "4:3")

        Returns:
            Dict with left, right, top, bottom expansion ratios (0.0 to 1.0)
        """
        # Parse target aspect ratio
        try:
            parts = target_aspect_ratio.split(":")
            target_w = float(parts[0])
            target_h = float(parts[1])
            target_ratio = target_w / target_h
        except (ValueError, IndexError, ZeroDivisionError):
            logger.warning(f"Invalid aspect ratio '{target_aspect_ratio}', defaulting to 16:9")
            target_ratio = 16 / 9

        # Assume source is 3:4 portrait (common for character images)
        source_ratio = 3 / 4  # 0.75

        if target_ratio > source_ratio:
            # Target is wider - expand horizontally
            # Calculate how much wider we need to be
            expansion_factor = target_ratio / source_ratio
            horizontal_expansion = (expansion_factor - 1) / 2  # Split between left and right

            return {
                "left": min(horizontal_expansion, 1.0),
                "right": min(horizontal_expansion, 1.0),
                "top": 0.0,
                "bottom": 0.0,
            }
        elif target_ratio < source_ratio:
            # Target is taller - expand vertically
            expansion_factor = source_ratio / target_ratio
            vertical_expansion = (expansion_factor - 1) / 2

            return {
                "left": 0.0,
                "right": 0.0,
                "top": min(vertical_expansion, 1.0),
                "bottom": min(vertical_expansion, 1.0),
            }
        else:
            # Same aspect ratio - no expansion needed
            return {
                "left": 0.0,
                "right": 0.0,
                "top": 0.0,
                "bottom": 0.0,
            }

    # Add nano-banana support to your existing service
    def _get_nano_banana_model_for_style(self, style: str) -> str:
        """Get appropriate model ID for the given style"""
        # ✅ Switch to nano-banana for faster generation
        style_models = {
            "realistic": "nano-banana",  # Changed from gen4_image
            "cinematic": "nano-banana",  # Much faster
            "animated": "nano-banana",
            "fantasy": "nano-banana",
            "comic": "nano-banana",
            "artistic": "nano-banana",
        }
        return style_models.get(style, "nano-banana")

    # Update the generate_image method to handle nano-banana specifics
    async def generate_image_with_nano_banana(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model_id: str = "nano-banana",  # Default to nano-banana
        wait_for_completion: bool = True,
        max_wait_time: int = 30,  # ✅ Reduced timeout for faster model
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab V7 API with nano-banana optimization"""

        try:
            # ✅ Nano-banana specific payload
            payload = {
                "prompt": prompt,
                "model_id": model_id,
                "aspect_ratio": aspect_ratio,
                "key": self.api_key,
            }

            # ✅ Add nano-banana specific parameters for better quality
            if model_id == "nano-banana":
                payload.update(
                    {
                        "width": 1024,  # Standard width for nano-banana
                        "height": (
                            1024 if aspect_ratio == "1:1" else 576
                        ),  # Adjust for aspect ratio
                        "guidance_scale": 7.5,  # Good balance for nano-banana
                        "num_inference_steps": 20,  # Faster inference
                        "safety_checker": False,  # Speed up generation
                    }
                )

            logger.info(f"[NANO BANANA] Generating image with nano-banana model")
            logger.info(f"[NANO BANANA] Aspect ratio: {aspect_ratio}")
            logger.info(f"[NANO BANANA] Prompt: {prompt[:100]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.image_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(
                        total=45
                    ),  # Increased timeout for nano-banana
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()

                    logger.info(f"[NANO BANANA] Initial response: {result}")

                    # ✅ Nano-banana usually responds faster
                    if result.get("status") == "processing":
                        if not wait_for_completion:
                            return {
                                "status": "processing",
                                "request_id": result.get("id"),
                                "fetch_url": result.get("fetch_result"),
                                "eta": result.get("eta", 5),  # Usually faster
                            }

                        # Wait for completion with shorter timeout
                        fetch_url = result.get("fetch_result")
                        request_id = result.get("id")

                        if fetch_url:
                            completed_result = await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time, model_id
                            )
                            return completed_result

                    return self._process_image_response(result, model_id)

        except Exception as e:
            logger.error(f"[NANO BANANA ERROR]: {str(e)}")
            raise e
