import requests
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from app.core.config import settings
import json

class ModelsLabImageService:
    def __init__(self):
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL
        self.headers = {
            "Content-Type": "application/json"
        }

    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 288,
        samples: int = 1,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        safety_checker: bool = True,  # ✅ FIXED: Add safety_checker parameter
        enhance_prompt: str = "yes",
        seed: Optional[int] = None,
        model_id: str = "realistic-vision-v51",
        scheduler: str = "DPMSolverMultistepScheduler",
        use_karras_sigmas: str = "yes"
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab API with proper safety_checker parameter"""
        
        url = f"{self.base_url}/realtime/text2img"
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "samples": samples,
            "num_inference_steps": num_inference_steps,
            "safety_checker": safety_checker,  # ✅ FIXED: Always include as boolean
            "enhance_prompt": enhance_prompt,
            "guidance_scale": guidance_scale,
            "scheduler": scheduler,
            "use_karras_sigmas": use_karras_sigmas,
            "webhook": None,
            "track_id": None
        }
        
        # Add seed if provided
        if seed is not None:
            payload["seed"] = seed
        
        try:
            print(f"[MODELSLAB IMAGE] Making API call with safety_checker={safety_checker}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    print(f"[MODELSLAB IMAGE] API Response: {result}")
                    
                    if result.get("status") == "error":
                        raise Exception(f"ModelsLab API error: {result.get('message', 'Unknown error')}")
                    
                    return result
                    
        except Exception as e:
            print(f"[MODELSLAB IMAGE ERROR]: {str(e)}")
            raise e
    async def generate_character_image(
        self,
        character_name: str,
        character_description: str,
        style: str = "realistic",
        width: int = 512,    # ✅ Video-compatible width  
        height: int = 288 
    ) -> Dict[str, Any]:
        """Generate character reference image"""
        
        # Create character-specific prompt
        style_prompts = {
            "realistic": "photorealistic, detailed face, high quality, professional portrait",
            "animated": "animated character, cartoon style, expressive features",
            "cinematic": "cinematic lighting, dramatic, film quality, detailed",
            "fantasy": "fantasy character, magical, ethereal, detailed fantasy art",
            "comic": "comic book style, bold lines, superhero aesthetic"
        }
        
        base_prompt = f"Character portrait of {character_name}, {character_description}"
        style_modifier = style_prompts.get(style, style_prompts["realistic"])
        
        prompt = f"{base_prompt}, {style_modifier}, centered composition, clear background"
        negative_prompt = "blurry, low quality, distorted, multiple people, crowd, text, watermark"
        
        return await self.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,  # Portrait aspect ratio for characters
            safety_checker=True,  # ✅ FIXED: Explicitly set safety_checker
            enhance_prompt="yes"
        )
        
    async def generate_scene_image(
    self,
    scene_description: str,
    style: str = "realistic",
    width: int = 512,    # ✅ Changed default to 512 for video compatibility
    height: int = 288    # ✅ Changed default to 288 for 16:9 ratio
) -> Dict[str, Any]:
        """Generate scene image with video-compatible dimensions"""
        
        style_prompts = {
            "realistic": "photorealistic scene, detailed environment, high quality, cinematic composition",
            "animated": "animated scene, cartoon style, vibrant colors, stylized environment",
            "cinematic": "cinematic scene, dramatic lighting, film quality, movie scene",
            "fantasy": "fantasy scene, magical atmosphere, detailed fantasy environment",
            "comic": "comic book scene, bold colors, dynamic composition, graphic novel style"
        }
        
        style_modifier = style_prompts.get(style, style_prompts["realistic"])
        
        prompt = f"Scene: {scene_description}, {style_modifier}, wide shot, detailed background"
        negative_prompt = "blurry, low quality, distorted, text, watermark, people close-up, nsfw"
        
        return await self._make_image_request(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,      # ✅ Now uses video-compatible width (512)
            height=height,    # ✅ Now uses video-compatible height (288)
            image_type="scene"
        )
        
    async def generate_lip_sync(
        self,
        video_url: str,
        audio_url: str,
        face_regions: Optional[List[Dict]] = None,
        model_id: str = "wav2lip"
    ) -> Dict[str, Any]:
        """Generate lip sync using ModelsLab"""
        
        url = f"{self.base_url}/video/lipsync"
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "init_video": video_url,
            "init_audio": audio_url,
            "webhook": None,
            "track_id": None
        }
        
        if face_regions:
            payload["face_regions"] = face_regions
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    return result
        except Exception as e:
            print(f"[MODELSLAB LIPSYNC ERROR]: {str(e)}")
            raise e
    
    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_time: int = 300,
        check_interval: int = 10
    ) -> Dict[str, Any]:
        """Wait for async request completion"""
        
        url = f"{self.base_url}/fetch"
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < max_wait_time:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json={"key": self.api_key, "request_id": request_id}) as response:
                        result = await response.json()
                        
                        if result.get("status") == "success":
                            return result
                        elif result.get("status") == "failed":
                            raise Exception(f"Request failed: {result.get('message', 'Unknown error')}")
                        
                        # Still processing, wait and try again
                        print(f"[MODELSLAB] Still processing request {request_id}...")
                        await asyncio.sleep(check_interval)
                        
            except Exception as e:
                if "failed" in str(e).lower():
                    raise e
                print(f"[MODELSLAB] Error checking status: {e}")
                await asyncio.sleep(check_interval)
        
        raise Exception(f"Request timed out after {max_wait_time} seconds")
    
    def get_lipsync_model_for_quality(self, quality_tier: str) -> str:
        """Get lip sync model based on quality tier"""
        model_mapping = {
            "basic": "wav2lip",
            "premium": "wav2lip++",
            "professional": "sadtalker"
        }
        return model_mapping.get(quality_tier, "wav2lip")

    
    async def generate_character_reference_image(
        self,
        character_name: str,
        character_description: str,
        style: str = "realistic"
    ) -> Dict[str, Any]:
        """Generate character reference image with proper safety_checker"""
        
        # Create character-specific prompt
        style_prompts = {
            "realistic": "photorealistic portrait, detailed face, high quality, professional headshot",
            "animated": "animated character portrait, cartoon style, expressive features",
            "cinematic": "cinematic character portrait, dramatic lighting, film quality",
            "fantasy": "fantasy character portrait, magical, ethereal, detailed fantasy art",
            "comic": "comic book character portrait, bold lines, superhero style"
        }
        
        base_prompt = f"Character portrait of {character_name}: {character_description}"
        style_modifier = style_prompts.get(style, style_prompts["realistic"])
        
        prompt = f"{base_prompt}, {style_modifier}, centered composition, plain background"
        negative_prompt = "blurry, low quality, distorted, multiple people, crowd, text, watermark, nsfw"
        
        return await self._make_image_request(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=512,
            height=768,  # Portrait aspect ratio
            image_type="character"
        )
        
    async def _make_image_request(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 288,
        samples: int = 1,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        model_id: str = "realistic-vision-v51",
        image_type: str = "general"
    ) -> Dict[str, Any]:
        """Make image generation request with proper safety_checker parameter"""
        
        url = f"{self.base_url}/realtime/text2img"
        
         # ✅ Debug logging
        print(f"[IMAGE REQUEST DEBUG] Making request with dimensions: {width}x{height}")
        print(f"[IMAGE REQUEST DEBUG] Image type: {image_type}")
        print(f"[IMAGE REQUEST DEBUG] Prompt length: {len(prompt)}")
        
        
        # ✅ FIXED: Always include safety_checker as boolean
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "samples": samples,
            "num_inference_steps": num_inference_steps,
            "safety_checker": True,  # ✅ FIXED: Boolean
            "enhance_prompt": True,  # ✅ FIXED: Changed from "yes" to True
            "guidance_scale": guidance_scale,
            "scheduler": "DPMSolverMultistepScheduler",
            "use_karras_sigmas": True,  # ✅ FIXED: Changed from "yes" to True
            "webhook": None,
            "track_id": None
        }
        
        try:
            print(f"[MODELSLAB IMAGE] Generating {image_type} image...")
            print(f"[MODELSLAB IMAGE] Payload - safety_checker: {payload['safety_checker']} (type: {type(payload['safety_checker'])})")
            print(f"[MODELSLAB IMAGE] Payload - enhance_prompt: {payload['enhance_prompt']} (type: {type(payload['enhance_prompt'])})")
            print(f"[MODELSLAB IMAGE] Payload - use_karras_sigmas: {payload['use_karras_sigmas']} (type: {type(payload['use_karras_sigmas'])})")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {response_text}")
                    
                    result = await response.json()
                    
                    print(f"[MODELSLAB IMAGE] API Response status: {result.get('status')}")
                    
                    if result.get("status") == "error":
                        error_msg = result.get('message', 'Unknown error')
                        print(f"[MODELSLAB IMAGE ERROR]: {error_msg}")
                        raise Exception(f"API returned error: {error_msg}")
                    
                    return result
                    
        except asyncio.TimeoutError:
            raise Exception("Request timed out after 60 seconds")
        except Exception as e:
            print(f"[MODELSLAB IMAGE ERROR]: {str(e)}")
            raise e

    def get_image_model_for_style(self, style: str) -> str:
        """Get appropriate image model for style"""
        model_mapping = {
            "realistic": "realistic-vision-v51",
            "cinematic": "realistic-vision-v51", 
            "animated": "anything-v5",
            "fantasy": "dreamshaper-v8",
            "comic": "comic-diffusion",
            "artistic": "stable-diffusion-v1-5"
        }
        return model_mapping.get(style, "realistic-vision-v51")

    async def upscale_image(
        self,
        image_url: str,
        scale: int = 2
    ) -> Dict[str, Any]:
        """Upscale image using ModelsLab upscaler"""
        
        url = f"{self.base_url}/realtime/upscale"
        
        payload = {
            "key": self.api_key,
            "init_image": image_url,
            "scale": scale,
            "webhook": None,
            "track_id": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    result = await response.json()
                    
                    if result.get("status") == "error":
                        raise Exception(f"Upscale API error: {result.get('message', 'Unknown error')}")
                    
                    return result
                    
        except Exception as e:
            print(f"[MODELSLAB UPSCALE ERROR]: {str(e)}")
            raise e