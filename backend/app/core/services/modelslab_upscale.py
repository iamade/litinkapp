"""
ModelsLab V6 Image Upscaling Service

Uses the ModelsLab V6 API for super resolution / image upscaling.
Supported models:
- RealESRGAN_x4plus: 4x upscaling model
- RealESRGAN_x4plus_anime_6B: 4x Anime upscaling model
- RealESRGAN_x2plus: 2x upscaling model
- realesr-general-x4v3: 4x upscaling general model
- ultra_resolution: 4K+ upscaling general model
"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


# Available upscaling models
UPSCALE_MODELS = {
    "4x": "RealESRGAN_x4plus",
    "4x_anime": "RealESRGAN_x4plus_anime_6B",
    "2x": "RealESRGAN_x2plus",
    "4x_general": "realesr-general-x4v3",
    "ultra": "ultra_resolution",
}


class ModelsLabUpscaleService:
    """ModelsLab V6 Image Upscaling Service for super resolution"""

    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")

        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_V6_BASE_URL
        self.upscale_endpoint = f"{self.base_url}/image_editing/super_resolution"

        self.headers = {
            "Content-Type": "application/json",
        }

    async def upscale_image(
        self,
        image_url: str,
        model_id: str = "realesr-general-x4v3",
        scale: int = 4,
        face_enhance: bool = False,
        wait_for_completion: bool = True,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """
        Upscale an image using ModelsLab V6 super resolution API.

        Args:
            image_url: URL of the image to upscale
            model_id: Upscaling model to use (default: realesr-general-x4v3)
                - RealESRGAN_x4plus: 4x upscaling
                - RealESRGAN_x4plus_anime_6B: 4x Anime upscaling
                - RealESRGAN_x2plus: 2x upscaling
                - realesr-general-x4v3: 4x general upscaling
                - ultra_resolution: 4K+ upscaling
            scale: Upscale factor (2, 3, or 4)
            face_enhance: Whether to enhance faces in the image
            wait_for_completion: Wait for async processing to complete
            max_wait_time: Maximum time to wait in seconds

        Returns:
            Dict with status, output URL, and metadata
        """
        try:
            payload = {
                "key": self.api_key,
                "init_image": image_url,
                "model_id": model_id,
                "scale": scale,
                "face_enhance": face_enhance,
            }

            logger.info(
                f"[UPSCALE] Starting upscale with model: {model_id}, scale: {scale}x"
            )
            logger.info(f"[UPSCALE] Input image: {image_url[:80]}...")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.upscale_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=180),
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()
                    logger.info(f"[UPSCALE] Initial response: {result}")

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
                            completed_result = await self._wait_for_completion(
                                session, fetch_url, request_id, max_wait_time
                            )
                            return completed_result
                        else:
                            raise Exception("No fetch URL provided for async upscaling")

                    # Handle immediate success
                    return self._process_response(result)

        except asyncio.TimeoutError as e:
            error_msg = "Request timeout waiting for ModelsLab upscale API"
            logger.error(f"[UPSCALE TIMEOUT]: {error_msg}")
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            logger.error(f"[UPSCALE ERROR]: {error_msg}")
            raise Exception(f"Image upscaling failed: {error_msg}") from e

    async def _wait_for_completion(
        self,
        session: aiohttp.ClientSession,
        fetch_url: str,
        request_id: str,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """Wait for async upscaling to complete"""

        logger.info(f"[UPSCALE] Waiting for completion: {request_id}")

        start_time = asyncio.get_event_loop().time()
        check_interval = 5  # Check every 5 seconds

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
                        logger.info(f"[UPSCALE] Fetch response: {result}")

                        if result.get("status") == "success" and result.get("output"):
                            logger.info(
                                f"[UPSCALE] ✅ Upscaling completed: {request_id}"
                            )
                            return self._process_response(result)
                        elif result.get("status") == "processing":
                            logger.info(f"[UPSCALE] ⏳ Still processing: {request_id}")
                            await asyncio.sleep(check_interval)
                            continue
                        else:
                            error_msg = result.get(
                                "message", "Unknown error during upscaling"
                            )
                            raise Exception(f"Upscaling failed: {error_msg}")
                    else:
                        logger.warning(
                            f"[UPSCALE] Fetch failed with status: {response.status}"
                        )
                        await asyncio.sleep(check_interval)
                        continue

            except Exception as e:
                logger.warning(f"[UPSCALE] Error during fetch: {e}")
                await asyncio.sleep(check_interval)
                continue

        raise Exception(f"Upscaling timed out after {max_wait_time} seconds")

    def _process_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and standardize upscale API response"""

        if response.get("status") == "success" and response.get("output"):
            output_urls = response.get("output", [])

            if output_urls and len(output_urls) > 0:
                upscaled_url = output_urls[0]

                return {
                    "status": "success",
                    "upscaled_url": upscaled_url,
                    "output": output_urls,
                    "proxy_links": response.get("proxy_links", []),
                    "generation_time": response.get("generationTime", 0),
                    "meta": response.get("meta", {}),
                }
            else:
                raise Exception("No output URLs in successful response")

        elif response.get("status") == "error":
            raise Exception(response.get("message", "Upscaling failed"))

        else:
            raise Exception(f"Unexpected response status: {response.get('status')}")

    async def upscale_4x(
        self, image_url: str, face_enhance: bool = False
    ) -> Dict[str, Any]:
        """Convenience method for 4x upscaling with general model"""
        return await self.upscale_image(
            image_url=image_url,
            model_id="realesr-general-x4v3",
            scale=4,
            face_enhance=face_enhance,
        )

    async def upscale_2x(
        self, image_url: str, face_enhance: bool = False
    ) -> Dict[str, Any]:
        """Convenience method for 2x upscaling"""
        return await self.upscale_image(
            image_url=image_url,
            model_id="RealESRGAN_x2plus",
            scale=2,
            face_enhance=face_enhance,
        )

    async def upscale_ultra(
        self, image_url: str, face_enhance: bool = False
    ) -> Dict[str, Any]:
        """Convenience method for 4K+ ultra resolution upscaling"""
        return await self.upscale_image(
            image_url=image_url,
            model_id="ultra_resolution",
            scale=4,
            face_enhance=face_enhance,
        )

    async def upscale_anime(self, image_url: str) -> Dict[str, Any]:
        """Convenience method for anime-style image upscaling"""
        return await self.upscale_image(
            image_url=image_url,
            model_id="RealESRGAN_x4plus_anime_6B",
            scale=4,
            face_enhance=False,
        )

    async def upscale_with_tier(
        self,
        image_url: str,
        user_tier: str,
        face_enhance: bool = False,
        wait_for_completion: bool = True,
        max_wait_time: int = 300,
    ) -> Dict[str, Any]:
        """
        Upscale image using tier-appropriate model with automatic fallback.

        Args:
            image_url: URL of the image to upscale
            user_tier: User subscription tier (free, basic, standard, premium, professional, enterprise)
            face_enhance: Whether to enhance faces
            wait_for_completion: Wait for async processing
            max_wait_time: Maximum wait time in seconds

        Returns:
            Dict with status, upscaled_url, model_used, etc.
        """
        from app.core.model_config import get_model_config

        config = get_model_config("upscale", user_tier)
        if not config:
            logger.warning(
                f"[UPSCALE] No config for tier {user_tier}, using FREE defaults"
            )
            config = get_model_config("upscale", "free")

        # Determine scale from model
        scale = 4  # Default
        if config.primary == "RealESRGAN_x2plus":
            scale = 2

        # Try primary model first
        models_to_try = [config.primary]
        if config.fallback:
            models_to_try.append(config.fallback)
        if config.fallback2:
            models_to_try.append(config.fallback2)

        last_error = None
        for model_id in models_to_try:
            try:
                logger.info(f"[UPSCALE] Trying model: {model_id} for tier: {user_tier}")

                # Update scale if switching to 2x model
                current_scale = 2 if model_id == "RealESRGAN_x2plus" else scale

                result = await self.upscale_image(
                    image_url=image_url,
                    model_id=model_id,
                    scale=current_scale,
                    face_enhance=face_enhance,
                    wait_for_completion=wait_for_completion,
                    max_wait_time=max_wait_time,
                )

                # Add model info to result
                result["model_used"] = model_id
                result["tier"] = user_tier
                result["scale"] = current_scale

                logger.info(f"[UPSCALE] ✅ Success with model: {model_id}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[UPSCALE] Model {model_id} failed: {str(e)}, trying fallback..."
                )
                continue

        # All models failed
        raise Exception(f"All upscale models failed. Last error: {last_error}")
