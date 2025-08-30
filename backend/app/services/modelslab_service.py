import requests
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from app.core.config import settings
import json

class ModelsLabService:
    def __init__(self):
        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL
        self.headers = {
            "Content-Type": "application/json"
        }

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, ugly, deformed",
        model_id: str = "midjourney",  # or "realistic-vision-v5", "juggernaut-xl-v9"
        width: int = 1024,
        height: int = 576,  # 16:9 aspect ratio for video
        samples: int = 1,
        steps: int = 30,
        guidance_scale: float = 7.5,
        safety_checker: bool = False,
        enhance_prompt: bool = True,
        seed: Optional[int] = None,
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab Text to Image API"""
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": str(width),
            "height": str(height),
            "samples": str(samples),
            "num_inference_steps": str(steps),
            "safety_checker": "yes" if safety_checker else "no",
            "enhance_prompt": "yes" if enhance_prompt else "no",
            "guidance_scale": guidance_scale,
            "multi_lingual": "no",
            "panorama": "no",
            "self_attention": "no",
            "upscale": "no",
            "embeddings_model": "",
            "lora_model": "",
            "tomesd": "yes",
            "use_karras_sigmas": "yes",
            "vae": "",
            "lora_strength": "",
            "scheduler": "UniPCMultistepScheduler",
            "webhook": webhook,
            "track_id": track_id
        }

        if seed:
            payload["seed"] = str(seed)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/text2img",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Image API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB IMAGE ERROR]: {str(e)}")
            raise e

    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_time: int = 300,  # 5 minutes
        check_interval: int = 10   # 10 seconds
    ) -> Dict[str, Any]:
        """Wait for generation to complete and return the result"""
        
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
                                raise Exception(f"Generation failed: {result.get('message', 'Unknown error')}")
                            elif status in ['processing', 'queued']:
                                await asyncio.sleep(check_interval)
                                elapsed_time += check_interval
                                continue
                        else:
                            await asyncio.sleep(check_interval)
                            elapsed_time += check_interval
                            continue
                            
            except Exception as e:
                if elapsed_time >= max_wait_time - check_interval:
                    raise Exception(f"Generation timeout after {max_wait_time} seconds: {str(e)}")
                await asyncio.sleep(check_interval)
                elapsed_time += check_interval
                continue

        raise Exception(f"Generation timeout after {max_wait_time} seconds")

    def get_model_for_style(self, style: str) -> str:
        """Get appropriate ModelsLab model based on style"""
        model_map = {
            "realistic": "realistic-vision-v5",
            "cinematic": "midjourney",
            "animated": "dreamshaper-v8",
            "fantasy": "juggernaut-xl-v9",
            "comic": "absolute-reality-v1.6",
            "artistic": "epicrealism-v5"
        }
        return model_map.get(style.lower(), "midjourney")
    
    # Add these methods to the existing ModelsLabService class after line 120

    async def generate_image_to_video(
        self,
        image_url: str,
        duration: float = 3.0,
        motion_strength: float = 0.8,
        fps: int = 24,
        width: int = 1024,
        height: int = 576,
        model_id: str = "stable-video-diffusion",  # or "animatediff-v3"
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate video from image using ModelsLab Image-to-Video API"""
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "init_image": image_url,
            "duration": str(duration),
            "motion_strength": motion_strength,
            "fps": str(fps),
            "width": str(width),
            "height": str(height),
            "steps": "25",
            "guidance_scale": 7.5,
            "scheduler": "DPMSolverMultistepScheduler",
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/image2video",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Image-to-Video API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB VIDEO ERROR]: {str(e)}")
            raise e

    async def generate_text_to_video(
        self,
        prompt: str,
        duration: float = 3.0,
        fps: int = 24,
        width: int = 1024,
        height: int = 576,
        model_id: str = "animatediff-v3",
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate video from text prompt using ModelsLab Text-to-Video API"""
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "prompt": prompt,
            "duration": str(duration),
            "fps": str(fps),
            "width": str(width),
            "height": str(height),
            "steps": "25",
            "guidance_scale": 7.5,
            "scheduler": "DPMSolverMultistepScheduler",
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/text2video",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Text-to-Video API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB VIDEO ERROR]: {str(e)}")
            raise e

    def get_video_model_for_style(self, style: str) -> str:
        """Get appropriate ModelsLab video model based on style"""
        model_map = {
            "realistic": "stable-video-diffusion",
            "cinematic": "animatediff-v3",
            "animated": "animatediff-v3",
            "fantasy": "stable-video-diffusion",
            "comic": "animatediff-v3",
            "artistic": "stable-video-diffusion"
        }
        return model_map.get(style.lower(), "stable-video-diffusion")

    def calculate_video_duration_from_audio(self, audio_segments: List[Dict[str, Any]], scene_id: str) -> float:
        """Calculate video duration based on corresponding audio segments"""
        total_duration = 0.0
        
        for segment in audio_segments:
            if segment.get('scene') == scene_id or segment.get('scene_id') == scene_id:
                total_duration += segment.get('duration', 3.0)
        
        # Minimum 3 seconds, maximum 30 seconds per scene
        return max(3.0, min(total_duration, 30.0))
    
    # Add these methods to the existing ModelsLabService class after line 200

    async def detect_faces_in_video(
        self,
        video_url: str,
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Detect faces in video using ModelsLab Face Detection API"""
        
        payload = {
            "key": self.api_key,
            "init_video": video_url,
            "detect_faces": True,
            "extract_regions": True,
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/face-detection",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Face Detection API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB FACE DETECTION ERROR]: {str(e)}")
            raise e

    async def generate_lip_sync(
        self,
        video_url: str,
        audio_url: str,
        face_regions: Optional[List[Dict]] = None,
        model_id: str = "wav2lip-hd",  # or "deepfake-lipsync"
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate lip sync for video using ModelsLab Lip Sync API"""
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "init_video": video_url,
            "init_audio": audio_url,
            "face_enhance": True,
            "quality": "high",
            "smooth_transitions": True,
            "maintain_expressions": True,
            "webhook": webhook,
            "track_id": track_id
        }
        
        # Add face regions if provided
        if face_regions:
            payload["face_regions"] = face_regions

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/lip-sync",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Lip Sync API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB LIP SYNC ERROR]: {str(e)}")
            raise e

    async def face_swap_with_audio(
        self,
        target_video_url: str,
        source_face_url: str,
        audio_url: str,
        model_id: str = "face-swap-audio",
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Face swap with audio sync using ModelsLab Face Swap API"""
        
        payload = {
            "key": self.api_key,
            "model_id": model_id,
            "target_video": target_video_url,
            "source_face": source_face_url,
            "audio_sync": audio_url,
            "face_enhance": True,
            "quality": "high",
            "preserve_identity": True,
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/face-swap",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Face Swap API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB FACE SWAP ERROR]: {str(e)}")
            raise e

    def get_lipsync_model_for_quality(self, quality_tier: str) -> str:
        """Get appropriate ModelsLab lip sync model based on quality tier"""
        model_map = {
            "free": "wav2lip-basic",
            "premium": "wav2lip-hd", 
            "professional": "deepfake-lipsync"
        }
        return model_map.get(quality_tier.lower(), "wav2lip-hd")

    async def audio_to_viseme(
        self,
        audio_url: str,
        language: str = "en",
        webhook: Optional[str] = None,
        track_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert audio to viseme data for lip sync"""
        
        payload = {
            "key": self.api_key,
            "audio_url": audio_url,
            "language": language,
            "output_format": "viseme",
            "timing_precision": "high",
            "webhook": webhook,
            "track_id": track_id
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/audio-to-viseme",
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error_text = await response.text()
                        raise Exception(f"ModelsLab Audio-to-Viseme API error: {response.status} - {error_text}")
        except Exception as e:
            print(f"[MODELSLAB AUDIO TO VISEME ERROR]: {str(e)}")
            raise e