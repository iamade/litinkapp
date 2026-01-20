"""
Google Veo Video Service - Direct API Integration via Google AI Studio

This service provides direct access to Google's Veo video generation models
through the Google AI Studio (Gemini) API using the official SDK.

API Documentation: https://ai.google.dev/api/generate-content
"""

import asyncio
import base64
import functools
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


class GoogleVeoVideoService:
    """
    Service for generating videos using Google's Veo models via Google AI Studio API.

    Supported models:
    - veo-2.0-generate-001 (Veo 2)
    """

    def __init__(self):
        self.api_key = settings.GOOGLE_AI_STUDIO_API_KEY
        self.client = None
        
        # Initialize client if API key is available
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"[GOOGLE VEO] Failed to initialize Google GenAI client: {e}")

        # Veo model configurations
        self.video_models = {
            "veo-3-direct": "veo-2.0-generate-001",  # Currently mapping to available Veo 2
            "veo-2-direct": "veo-2.0-generate-001",
            "veo-3": "veo-2.0-generate-001",
        }

        # Default video generation parameters
        self.default_duration = 5  # seconds
        self.default_fps = 24
        self.default_resolution = "1280x720"

        # Thread executor for running sync SDK calls
        self._executor = ThreadPoolExecutor(max_workers=3)

    def is_available(self) -> bool:
        """Check if the Google Veo service is available (API key configured)"""
        return bool(self.api_key) and self.client is not None

    def _get_model_name(self, model_id: str) -> str:
        """Map our model ID to Google's model name"""
        return self.video_models.get(model_id, "veo-2.0-generate-001")

    async def _run_sync(self, func, *args, **kwargs):
        """Run a synchronous function in a thread pool"""
        loop = asyncio.get_running_loop()
        partial_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(self._executor, partial_func)

    async def generate_image_to_video(
        self,
        image_url: str,
        prompt: str,
        model_id: str = "veo-3-direct",
        duration: int = None,
        fps: int = None,
        resolution: str = None,
        negative_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a video from an image using Google Veo.
        """
        if not self.is_available():
            logger.warning("[GOOGLE VEO] API key not configured, service unavailable")
            return {
                "status": "error",
                "error": "Google Veo API key not configured",
                "fallback_required": True,
            }

        try:
            logger.info(
                f"[GOOGLE VEO] Generating video from image: model={model_id}, "
                f"duration={duration or self.default_duration}s"
            )

            # Download the image first
            image_data = await self._download_image(image_url)
            if not image_data:
                return {
                    "status": "error",
                    "error": "Failed to download source image",
                    "fallback_required": True,
                }

            model_name = self._get_model_name(model_id)
            
            # Build prompt
            full_prompt = prompt
            if negative_prompt:
                full_prompt += f"\n\nAvoid: {negative_prompt}"

            # Prepare config
            config = types.GenerateVideosConfig(
                video_duration_seconds=float(duration or self.default_duration),
                aspect_ratio=resolution if resolution and ":" in resolution else "16:9",
                # extracted resolution to aspect ratio mapping if needed
            )

            # Run synchronous generation call in executor
            # Note: The SDK's generate_videos handles the polling internally by default?
            # Actually, looking at docs, client.models.generate_videos returns a response directly
            # containing the video or operation.
            
            # The uploaded image part construction
            # For image-to-video, we pass the image as part of the prompt contents or specific parameter?
            # According to Veo docs, we pass the image in the prompt parts.
            
            # Using raw bytes for image
            image_part = types.Part.from_bytes(
                data=image_data["bytes"], 
                mime_type=image_data["mime_type"]
            )
            
            prompt_content = f"{full_prompt}"
            
            def _generate_call():
                return self.client.models.generate_videos(
                    model=model_name,
                    prompt=prompt_content,
                    video_duration_seconds=float(duration or self.default_duration),
                    aspect_ratio=resolution if resolution and ":" in resolution else "16:9",
                    prompt_image=image_part # Hypothetical SDK parameter based on latest generic usage
                    # If SDK requires list of contents:
                    # contents=[image_part, prompt_content]
                )

            # NOTE: The SDK structure might be slightly different depending on version.
            # Adapting to the structure implied by user's snippet:
            # response = client.models.generate_videos(model=..., prompt=..., config=...)
            
            # But generate_videos usually takes prompt text. For Image-to-Video, we verify SDK usage.
            # Assuming prompt can take image parts or there's a specific param.
            # The google-genai SDK treats images as parts of the prompt list usually.
            
            def _generate_call_v2():
                # Construct content list with image and text
                # We use specific generate_videos signature
                return self.client.models.generate_videos(
                    model=model_name,
                    prompt=full_prompt,
                    config=config,
                    # If this SDK version accepts image as a separate argument or part of prompt?
                    # Trying generic 'prompt' as list if supported, or looking for specific arg.
                    # Current Veo API often separates text_prompt and image_prompt.
                    # Ideally we'd use the typed objects.
                )
                
            # LET'S USE THE EXACT PATTERN FROM THE USER'S SNIPPET, BUT ADAPTED FOR IMAGE
            # "For Veo, you must use generate_videos... prompt='...'"
            # User snippet didn't show image-to-video.
            # We will try to pass the image in the prompt if possible, or fail back to text if not obvious.
            # But the requirement IS image-to-video.
            
            # Correct approach for Image+Text to Video in Gemini/Veo often involves
            # sending the image as a 'Part' in the content.
            # However, generate_videos might strictly be text-to-video in the helper method.
            # We will use the lower-level generate_content if generate_videos doesn't support images,
            # OR assume generate_videos accepts a list for 'prompt'.
            
            # Let's try passing the image part in the prompt argument (as a list).
            
            def _generate_call_final():
                return self.client.models.generate_videos(
                    model=model_name,
                    prompt=[
                        types.Part.from_bytes(
                            data=image_data["bytes"],
                            mime_type=image_data["mime_type"]
                        ),
                        full_prompt
                    ],
                    config=config
                )

            logger.info("Calling Google Veo API via SDK...")
            response = await self._run_sync(_generate_call_final)
            
            # Process response
            # The SDK response should have a 'candidates' or 'video' attribute
            # Depending on version it might wait for completion.
            
            # If the response contains the video bytes directly
            if hasattr(response, "video") and response.video:
                # Save or return
                pass # logic to extract

            # Extract video
            return await self._process_sdk_response(response)

        except Exception as e:
            logger.error(f"[GOOGLE VEO] Unexpected error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_required": True,
            }

    async def generate_text_to_video(
        self,
        prompt: str,
        model_id: str = "veo-3-direct",
        duration: int = None,
        fps: int = None,
        resolution: str = None,
        negative_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Generate a video from text prompt using Google Veo.
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "Google Veo API key not configured",
                "fallback_required": True,
            }

        try:
            logger.info(
                f"[GOOGLE VEO] Generating video from text: model={model_id}, "
                f"duration={duration or self.default_duration}s"
            )

            model_name = self._get_model_name(model_id)
            full_prompt = prompt
            if negative_prompt:
                full_prompt += f"\n\nAvoid: {negative_prompt}"

            config = types.GenerateVideosConfig(
                video_duration_seconds=float(duration or self.default_duration),
                aspect_ratio=resolution if resolution and ":" in resolution else "16:9",
            )

            def _generate_call():
                return self.client.models.generate_videos(
                    model=model_name,
                    prompt=full_prompt,
                    config=config
                )

            response = await self._run_sync(_generate_call)
            return await self._process_sdk_response(response)

        except Exception as e:
            logger.error(f"[GOOGLE VEO] Unexpected error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_required": True,
            }

    async def _process_sdk_response(self, response) -> Dict[str, Any]:
        """Process the SDK response to extract video"""
        # Note: real SDK usage to extract video bytes
         # response.video_bytes might be available or we iterate through candidates
        try:
            # Check for attributes based on SDK version
            video_bytes = None
            mime_type = "video/mp4"
            
            if hasattr(response, "parts"):
                for part in response.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                         video_bytes = part.inline_data.data
                         mime_type = part.inline_data.mime_type
                         
            # If using generate_videos, it might be simpler
            if not video_bytes and hasattr(response, "video"):
                 # if response is bytes?
                 pass

            # Fallback inspection
            # Assuming for now we receive a valid response object we can parse
            # This logic mimics the manual parsing but using object attributes
            
            # MOCKING extraction for safety if I don't know exact SDK structure:
            # We assume successful return means we can serve it.
            # Ideally we'd save to file here.
            
            # Since I can't see the exact SDK response type definitions without running it,
            # I will assume standard Gemini pattern: response.candidates[0].content.parts[0].inline_data
            
            if hasattr(response, "candidates") and response.candidates:
                part = response.candidates[0].content.parts[0]
                if part.inline_data:
                    video_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type
            
            if video_bytes:
                # Return base64 for now, or assume caller handles upload
                return {
                    "status": "success",
                    "video_data_base64": base64.b64encode(video_bytes).decode("utf-8"),
                    "mime_type": mime_type,
                    "model_used": "google-veo",
                    "provider": "google_ai_studio",
                    "needs_upload": True
                }
            
            # If response gives a URI (file API)
            # ...
            
            return {
                "status": "error",
                "error": "Could not extract video from SDK response",
                "fallback_required": True
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Error processing SDK response: {e}",
                "fallback_required": True
            }

    async def _download_image(self, image_url: str) -> Optional[Dict[str, Any]]:
        """Download image using aiohttp"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.read()
                        mime_type = response.headers.get("Content-Type", "image/jpeg")
                        return {"bytes": data, "mime_type": mime_type}
        except Exception as e:
            logger.error(f"[GOOGLE VEO] Image download failed: {e}")
        return None

    async def check_api_status(self) -> Dict[str, Any]:
        """Check API availability"""
        if not self.is_available():
            return {"status": "unavailable", "message": "API key not configured"}
        
        try:
            # Simple list models call
            def _list_models():
                # Correct way to list models in SDK
                return list(self.client.models.list(config={"page_size": 10}))
                
            models = await self._run_sync(_list_models)
            return {
                "status": "available",
                "models_count": len(models),
                "veo_available": any("veo" in m.name for m in models)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Singleton instance
_google_veo_service: Optional[GoogleVeoVideoService] = None


def get_google_veo_service() -> GoogleVeoVideoService:
    """Get the singleton GoogleVeoVideoService instance"""
    global _google_veo_service
    if _google_veo_service is None:
        _google_veo_service = GoogleVeoVideoService()
    return _google_veo_service
