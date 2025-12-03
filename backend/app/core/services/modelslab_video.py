# from typing import Any, Dict, List, Optional
# import aiohttp
# from app.core.config import settings
# import time
# import asyncio


# class ModelsLabVideoService:
#     def __init__(self):
#         self.api_key = settings.MODELSLAB_API_KEY
#         self.base_url = settings.MODELSLAB_BASE_URL
#         self.headers = {
#             "Content-Type": "application/json"
#         }

#     def get_video_model_for_style(self, style: str) -> str:
#         """Get appropriate ModelsLab video model based on style"""
#         model_map = {
#             "realistic": "stable-video-diffusion",
#             "cinematic": "animatediff-v3",
#             "animated": "animatediff-v3",
#             "fantasy": "stable-video-diffusion",
#             "comic": "animatediff-v3",
#             "artistic": "stable-video-diffusion"
#         }
#         return model_map.get(style.lower(), "stable-video-diffusion")
    
#     async def generate_image_to_video(
#         self,
#         image_url: str,
#         duration: float = 3.0,
#         motion_strength: float = 0.8,
#         fps: int = 24,
#         width: int = 512,    # ✅ FIXED: Must be ≤ 512
#         height: int = 288,   # ✅ FIXED: 16:9 ratio within limits
#         model_id: str = "stable-video-diffusion"
#     ) -> Dict[str, Any]:
#         """Generate video from image using ModelsLab"""
        
#         url = f"{self.base_url}/video/img2video"
        
#         payload = {
#             "key": self.api_key,
#             "model_id": model_id,
#             "init_image": image_url,
#             "duration": int(duration),
#             "motion_bucket_id": int(motion_strength * 255),  # Convert to 0-255 range
#             "fps": fps,
#             "width": width,
#             "height": height,
#             "webhook": None,
#             "track_id": None
#         }
        
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(url, json=payload) as response:
#                     result = await response.json()
                    
#                     print(f"[MODELSLAB VIDEO] API Response: {result}")
#                     return result
                    
#         except Exception as e:
#             print(f"[MODELSLAB VIDEO ERROR]: {str(e)}")
#             raise e
        
#     async def generate_text_to_video(
#         self,
#         prompt: str,
#         duration: float = 3.0,
#         fps: int = 24,
#         width: int = 512,
#         height: int = 288,
#         model_id: str = "animatediff-v3",
#         webhook: Optional[str] = None,
#         track_id: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Generate video from text prompt using ModelsLab Text-to-Video API"""
        
#         payload = {
#             "key": self.api_key,
#             "model_id": model_id,
#             "prompt": prompt,
#             "duration": str(duration),
#             "fps": str(fps),
#             "width": str(width),
#             "height": str(height),
#             "steps": "25",
#             "guidance_scale": 7.5,
#             "scheduler": "DPMSolverMultistepScheduler",
#             "webhook": webhook,
#             "track_id": track_id
#         }

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(
#                     f"{self.base_url}/video/text2video",
#                     json=payload,
#                     headers=self.headers
#                 ) as response:
#                     if response.status == 200:
#                         result = await response.json()
#                         return result
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"ModelsLab Text-to-Video API error: {response.status} - {error_text}")
#         except Exception as e:
#             print(f"[MODELSLAB VIDEO ERROR]: {str(e)}")
#             raise e
        
    
#     def calculate_video_duration_from_audio(
#         self,
#         audio_files: List[Dict],
#         scene_id: str
#     ) -> float:
#         """Calculate video duration based on audio files for a scene"""
        
#         total_duration = 0.0
#         scene_number = int(scene_id.split('_')[1]) if '_' in scene_id else 1
        
#         # Find audio files for this scene
#         for audio in audio_files:
#             audio_scene = audio.get('scene', 1)
#             if audio_scene == scene_number:
#                 total_duration += audio.get('duration', 3.0)
        
#         # Ensure minimum duration of 3 seconds, maximum of 10 seconds
#         return max(3.0, min(total_duration, 10.0))
    
#     # Add these methods to the existing ModelsLabService class after line 200

#     async def detect_faces_in_video(
#         self,
#         video_url: str,
#         webhook: Optional[str] = None,
#         track_id: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Detect faces in video using ModelsLab Face Detection API"""
        
#         payload = {
#             "key": self.api_key,
#             "init_video": video_url,
#             "detect_faces": True,
#             "extract_regions": True,
#             "webhook": webhook,
#             "track_id": track_id
#         }

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(
#                     f"{self.base_url}/face-detection",
#                     json=payload,
#                     headers=self.headers
#                 ) as response:
#                     if response.status == 200:
#                         result = await response.json()
#                         return result
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"ModelsLab Face Detection API error: {response.status} - {error_text}")
#         except Exception as e:
#             print(f"[MODELSLAB FACE DETECTION ERROR]: {str(e)}")
#             raise e

#     async def generate_lip_sync(
#         self,
#         video_url: str,
#         audio_url: str,
#         face_regions: Optional[List[Dict]] = None,
#         model_id: str = "wav2lip-hd",  # or "deepfake-lipsync"
#         webhook: Optional[str] = None,
#         track_id: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Generate lip sync for video using ModelsLab Lip Sync API"""
        
#         payload = {
#             "key": self.api_key,
#             "model_id": model_id,
#             "init_video": video_url,
#             "init_audio": audio_url,
#             "face_enhance": True,
#             "quality": "high",
#             "smooth_transitions": True,
#             "maintain_expressions": True,
#             "webhook": webhook,
#             "track_id": track_id
#         }
        
#         # Add face regions if provided
#         if face_regions:
#             payload["face_regions"] = face_regions

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(
#                     f"{self.base_url}/lip-sync",
#                     json=payload,
#                     headers=self.headers
#                 ) as response:
#                     if response.status == 200:
#                         result = await response.json()
#                         return result
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"ModelsLab Lip Sync API error: {response.status} - {error_text}")
#         except Exception as e:
#             print(f"[MODELSLAB LIP SYNC ERROR]: {str(e)}")
#             raise e

#     async def face_swap_with_audio(
#         self,
#         target_video_url: str,
#         source_face_url: str,
#         audio_url: str,
#         model_id: str = "face-swap-audio",
#         webhook: Optional[str] = None,
#         track_id: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Face swap with audio sync using ModelsLab Face Swap API"""
        
#         payload = {
#             "key": self.api_key,
#             "model_id": model_id,
#             "target_video": target_video_url,
#             "source_face": source_face_url,
#             "audio_sync": audio_url,
#             "face_enhance": True,
#             "quality": "high",
#             "preserve_identity": True,
#             "webhook": webhook,
#             "track_id": track_id
#         }

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(
#                     f"{self.base_url}/face-swap",
#                     json=payload,
#                     headers=self.headers
#                 ) as response:
#                     if response.status == 200:
#                         result = await response.json()
#                         return result
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"ModelsLab Face Swap API error: {response.status} - {error_text}")
#         except Exception as e:
#             print(f"[MODELSLAB FACE SWAP ERROR]: {str(e)}")
#             raise e

#     def get_lipsync_model_for_quality(self, quality_tier: str) -> str:
#         """Get appropriate ModelsLab lip sync model based on quality tier"""
#         model_map = {
#             "free": "wav2lip-basic",
#             "premium": "wav2lip-hd", 
#             "professional": "deepfake-lipsync"
#         }
#         return model_map.get(quality_tier.lower(), "wav2lip-hd")

#     async def audio_to_viseme(
#         self,
#         audio_url: str,
#         language: str = "en",
#         webhook: Optional[str] = None,
#         track_id: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """Convert audio to viseme data for lip sync"""
        
#         payload = {
#             "key": self.api_key,
#             "audio_url": audio_url,
#             "language": language,
#             "output_format": "viseme",
#             "timing_precision": "high",
#             "webhook": webhook,
#             "track_id": track_id
#         }

#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.post(
#                     f"{self.base_url}/audio-to-viseme",
#                     json=payload,
#                     headers=self.headers
#                 ) as response:
#                     if response.status == 200:
#                         result = await response.json()
#                         return result
#                     else:
#                         error_text = await response.text()
#                         raise Exception(f"ModelsLab Audio-to-Viseme API error: {response.status} - {error_text}")
#         except Exception as e:
#             print(f"[MODELSLAB AUDIO TO VISEME ERROR]: {str(e)}")
#             raise e
        
       
#     async def wait_for_completion(
#         self,
#         request_id: str,
#         max_wait_time: int = 300,
#         check_interval: int = 10
#     ) -> Dict[str, Any]:
#         """Wait for async video generation to complete"""
        
#         # ✅ FIX: Use correct URL format with request_id in path
#         url = f"{self.base_url}/video/fetch/{request_id}"
        
#         start_time = time.time()
        
#         while time.time() - start_time < max_wait_time:
#             try:
#                 async with aiohttp.ClientSession() as session:
#                     # ✅ FIXED: Send POST request with just API key in body
#                     payload = {
#                         "key": self.api_key
#                     }
                    
#                     async with session.post(url, json=payload) as response:
#                         result = await response.json()
                        
#                         print(f"[MODELSLAB VIDEO] Fetch response: {result}")
                        
#                         if result.get('status') == 'success':
#                             return result
#                         elif result.get('status') == 'error':
#                             raise Exception(f"Video generation failed: {result.get('message', 'Unknown error')}")
                        
#                         # Still processing, wait and retry
#                         print(f"[MODELSLAB VIDEO] Still processing request {request_id}...")
#                         await asyncio.sleep(check_interval)
                        
#             except Exception as e:
#                 print(f"[MODELSLAB VIDEO] Error checking status: {e}")
#                 await asyncio.sleep(check_interval)
        
#         raise Exception(f"Video generation timed out after {max_wait_time} seconds")