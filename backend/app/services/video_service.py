import httpx
from typing import List, Dict, Any, Optional
import asyncio
from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.elevenlabs_service import ElevenLabsService
import time
import os
import subprocess
import tempfile
import aiofiles
import aiohttp
from pathlib import Path
from supabase.client import create_client, Client
import base64
import jwt
import json
import re


class VideoService:
    """Video generation service using Tavus API with RAG and ElevenLabs integration"""
    
    def __init__(self, supabase_client=None):
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = "https://tavusapi.com/v2"
        self.kling_access_key_id = settings.KLINGAI_ACCESS_KEY_ID
        self.kling_access_key_secret = settings.KLINGAI_ACCESS_KEY_SECRET

        # Initialize Supabase client for storage
        if supabase_client:
            self.supabase = supabase_client
        else:
            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        self.supabase_service = self.supabase  # Alias for compatibility

        self.rag_service = RAGService(self.supabase)
        self.elevenlabs_service = ElevenLabsService(self.supabase)
    
    async def generate_video_from_chapter(
        self,
        chapter_id: str,
        video_style: str = "realistic",
        include_context: bool = True,
        include_audio_enhancement: bool = True,
        supabase_client = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video from a specific chapter"""
        try:
            # Use provided client or create new one
            if supabase_client:
                self.supabase = supabase_client
            
            # Get chapter and book information
            chapter_response = self.supabase.table("chapters").select(
                "*, books(title, cover_image_url, book_type, difficulty, user_id)"
            ).eq("id", chapter_id).single().execute()
            
            if not chapter_response.data:
                raise ValueError("Chapter not found")
            
            chapter_data = chapter_response.data
            book_data = chapter_data.get("books", {})
            
            # Get user_id from book data
            user_id = book_data.get("user_id")
            
            # Get book cover image URL for thumbnail
            cover_image_url = book_data.get("cover_image_url")
            if not cover_image_url:
                # Fallback to placeholder if no cover image
                cover_image_url = "https://via.placeholder.com/1280x720/000000/FFFFFF?text=Book+Cover"
            
            # Get chapter content and context
            chapter_content = chapter_data.get("content", "")
            chapter_title = chapter_data.get("title", "")
            book_title = book_data.get("title", "")
            book_type = book_data.get("book_type", "learning")
            
            if not chapter_content:
                raise ValueError("Chapter content is empty")
            
            # Generate script based on book type
            if book_type == "learning":
                script = await self._generate_learning_script(
                    chapter_content, chapter_title, book_title, video_style
                )
            else:
                script = await self._generate_entertainment_script(
                    chapter_content, chapter_title, book_title, video_style
                )
            
            if not script:
                raise ValueError("Failed to generate script")
            
            # Generate video with priority: Tavus API > FFmpeg > Mock
            video_result = None
            
            # Priority 1: Try Tavus API first (real AI video generation)
            if settings.TAVUS_API_KEY and settings.TAVUS_API_KEY != "your-tavus-api-key":
                print("Using Tavus API for real video generation...")
                video_result = await self._generate_real_video(script, video_style, user_id)
                if video_result:
                    print("✅ Tavus API video generation successful")
            
            # Priority 2: Try FFmpeg mock video if Tavus fails or not available
            if not video_result:
                print("Tavus API not available, trying FFmpeg mock video...")
                video_result = await self._mock_generate_scene(
                    f"Chapter: {chapter_title}", script
                )
                if video_result:
                    print("✅ FFmpeg mock video generation successful")
            
            # Priority 3: Fallback to basic mock response if everything fails
            if not video_result:
                print("All video generation methods failed, using basic fallback...")
                video_result = {
                    "id": f"fallback_video_{int(time.time())}",
                    "title": f"Chapter: {chapter_title}",
                    "description": "Video generation temporarily unavailable",
                    "video_url": None,
                    "thumbnail_url": cover_image_url,
                    "duration": 180,
                    "status": "error",
                    "mock": True,
                    "error": "Video generation services unavailable"
                }
            
            # Add book cover as thumbnail (if not already set)
            if video_result and not video_result.get("thumbnail_url"):
                video_result["thumbnail_url"] = cover_image_url
            
            return video_result
            
        except Exception as e:
            print(f"Error generating video from chapter: {e}")
            return None
    
    async def _generate_enhanced_audio(
        self, 
        script: str, 
        chapter_context: Dict[str, Any], 
        video_style: str,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Generate enhanced audio with narration, character voices, and sound effects"""
        try:
            if video_style in ["tutorial", "educational", "learning"]:
                # Generate tutorial-style narration
                narration_audio = await self.elevenlabs_service.create_audio_narration(
                    text=script,
                    narrator_style="professional",
                    user_id=user_id
                )
                
                return {
                    'type': 'tutorial_narration',
                    'audio_url': narration_audio,
                    'duration': 180  # Default 3 minutes
                }
            
            else:
                # Generate entertainment audio with character voices and sound effects
                return await self._generate_entertainment_audio(script, chapter_context, video_style, user_id)
                
        except Exception as e:
            print(f"Error generating enhanced audio: {e}")
            return None
    
    async def _generate_entertainment_audio(
        self, 
        script: str, 
        chapter_context: Dict[str, Any], 
        video_style: str,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Generate entertainment audio with character voices and sound effects"""
        try:
            # Extract character dialogue from script
            character_dialogues = self._extract_character_dialogues(script)
            
            # Generate character voices
            character_audios = []
            for dialogue in character_dialogues:
                character_profile = self._create_character_profile(dialogue['character'])
                audio_url = await self.elevenlabs_service.generate_character_voice(
                    text=dialogue['text'],
                    character_name=dialogue['character'],
                    character_traits=character_profile.get('personality', ''),
                    user_id=user_id
                )
                
                if audio_url:
                    character_audios.append({
                        'character': dialogue['character'],
                        'text': dialogue['text'],
                        'audio_url': audio_url
                    })
            
            # Generate background sound effects
            background_audio = await self.elevenlabs_service.generate_sound_effects(
                effect_type=self._get_background_effect_type(video_style),
                duration=180,  # 3 minutes
                intensity=0.3,
                user_id=user_id
            )
            
            # Handle case where no character dialogues were found
            if not character_audios:
                print("Warning: No character dialogues found in script, using fallback audio")
                # Create a fallback narration audio
                fallback_audio = await self.elevenlabs_service.create_audio_narration(
                    text=script[:500],  # Use first 500 characters as fallback
                    narrator_style="professional",
                    user_id=user_id
                )
                
                return {
                    'type': 'fallback_narration',
                    'audio_url': fallback_audio,
                    'character_audios': [],
                    'background_audio': background_audio,
                    'duration': 180
                }
            
            # Mix all audio tracks
            mixed_audio = await self.elevenlabs_service.mix_audio_tracks(
                audio_tracks=[{"url": audio['audio_url']} for audio in character_audios] + [{"url": background_audio}],
                user_id=user_id
            )
            
            return {
                'type': 'entertainment_audio',
                'audio_url': mixed_audio.get('audio_url') if isinstance(mixed_audio, dict) else mixed_audio,
                'character_audios': character_audios,
                'background_audio': background_audio,
                'duration': 180
            }
            
        except Exception as e:
            print(f"Error generating entertainment audio: {e}")
            return None
    
    def _extract_character_dialogues(self, script: str) -> List[Dict[str, str]]:
        """Extract character dialogues from screenplay script"""
        dialogues = []
        lines = script.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for character names in caps (screenplay format)
            if line.isupper() and len(line) > 2 and len(line) < 50:
                character = line
                # Look for dialogue in next lines
                dialogue_text = ""
                j = i + 1
                while j < len(lines) and (lines[j].strip().startswith('    ') or not lines[j].strip()):
                    if lines[j].strip():
                        dialogue_text += lines[j].strip() + " "
                    j += 1
                
                if dialogue_text.strip():
                    dialogues.append({
                        'character': character,
                        'text': dialogue_text.strip()
                    })
        
        return dialogues
    
    def _create_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Create character profile based on character name"""
        # Simple character profiling - in a real implementation, you might use AI
        character_name_lower = character_name.lower()
        
        if any(word in character_name_lower for word in ['narrator', 'narrator']):
            return {
                'name': character_name,
                'personality': 'professional',
                'age': 'adult',
                'gender': 'neutral'
            }
        elif any(word in character_name_lower for word in ['young', 'child', 'kid']):
            return {
                'name': character_name,
                'personality': 'friendly',
                'age': 'young',
                'gender': 'neutral'
            }
        elif any(word in character_name_lower for word in ['wise', 'elder', 'sage']):
            return {
                'name': character_name,
                'personality': 'wise',
                'age': 'elder',
                'gender': 'neutral'
            }
        elif any(word in character_name_lower for word in ['mysterious', 'shadow', 'dark']):
            return {
                'name': character_name,
                'personality': 'mysterious',
                'age': 'adult',
                'gender': 'neutral'
            }
        else:
            return {
                'name': character_name,
                'personality': 'neutral',
                'age': 'adult',
                'gender': 'neutral'
            }
    
    def _get_background_effect_type(self, video_style: str) -> str:
        """Get appropriate background sound effect type for video style"""
        effect_mapping = {
            "realistic": "ambient",
            "animated": "magical",
            "cartoon": "nature",
            "dramatic": "emotional",
            "adventure": "action"
        }
        return effect_mapping.get(video_style, "ambient")
    
    async def generate_story_scene(
        self,
        scene_description: str,
        dialogue: str,
        avatar_style: str = "realistic"
    ) -> Optional[Dict[str, Any]]:
        """Generate video scene for story"""
        if not self.api_key:
            return await self._mock_generate_scene(scene_description, dialogue)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/videos",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "script": dialogue,
                        "avatar_id": self._get_avatar_id(avatar_style),
                        "background": self._get_background_for_style(avatar_style),
                        "voice_settings": {
                            "voice_id": self._get_voice_id_for_style(avatar_style),
                            "stability": 0.75,
                            "similarity_boost": 0.75
                        },
                        "video_settings": {
                            "quality": "high",
                            "format": "mp4",
                            "duration": 180  # 3 minutes default
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    video_id = data.get("video_id")
                    
                    # Poll for completion
                    return await self._poll_video_status(video_id, scene_description)
                else:
                    print(f"Tavus API error: {response.status_code}")
                    return await self._mock_generate_scene(scene_description, dialogue)
                    
        except Exception as e:
            print(f"Video service error: {e}")
            return await self._mock_generate_scene(scene_description, dialogue)
    
    async def generate_tutorial_video(
        self,
        chapter_id: str,
        tutorial_style: str = "udemy",
        supabase_client = None
    ) -> Optional[Dict[str, Any]]:
        """Generate tutorial-style video for learning content"""
        return await self.generate_video_from_chapter(
            chapter_id=chapter_id,
            video_style="realistic",  # Tutorials typically use realistic avatars
            include_context=True,
            include_audio_enhancement=True,
            supabase_client=supabase_client
        )
    

    async def generate_entertainment_video(
        self,
        chapter_id: str,
        animation_style: str = "animated",
        script_style: str = "cinematic_movie",
        supabase_client = None,
        user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Generate entertainment-style video for story content using RAG, OpenAI, ElevenLabs, KlingAI, and FFmpeg. User can choose script_style ('cinematic_movie' or 'cinematic_narration')."""
        logs = []
        try:
            # 1. Get chapter context using RAG
            chapter_context = await self.rag_service.get_chapter_with_context(
                chapter_id=chapter_id,
                include_adjacent=True,
                use_vector_search=True
            )
            
            # 2. Generate script using RAG with character extraction
            script_result = await self.rag_service.generate_video_script(chapter_context, animation_style, script_style=script_style)
            script = script_result.get("script", "")
            characters = script_result.get("characters", [])
            character_details = script_result.get("character_details", "")
            
            # Debug script generation
            logs.append(f"[SCRIPT DEBUG] Script result type: {type(script_result)}")
            logs.append(f"[SCRIPT DEBUG] Script type: {type(script)}")
            logs.append(f"[SCRIPT DEBUG] Script length: {len(script) if script else 0}")
            logs.append(f"[SCRIPT DEBUG] Script preview: {script[:200] if script else 'None'}...")
            logs.append(f"[CHARACTERS] Extracted characters: {characters}")
            logs.append(f"[CHARACTER_DETAILS] {character_details}")
            
            # 3. Parse script dynamically for ElevenLabs and KlingAI
            parsed_content = self._parse_script_for_services(script, script_style)
            elevenlabs_content = parsed_content["elevenlabs_content"]
            klingai_content = parsed_content["klingai_content"]
            elevenlabs_content_type = parsed_content["elevenlabs_content_type"]
            klingai_content_type = parsed_content["klingai_content_type"]
            
            # Fallback if parsing failed or content is empty
            if not elevenlabs_content or elevenlabs_content.strip() == "":
                logs.append("[FALLBACK] ElevenLabs content empty, using fallback")
                elevenlabs_content = "Narrator: This is a cinematic narration of the story content."
                elevenlabs_content_type = "fallback_narration"
            
            if not klingai_content or klingai_content.strip() == "":
                logs.append("[FALLBACK] KlingAI content empty, using fallback")
                klingai_content = "A cinematic scene with visual elements, camera movements, and dramatic lighting."
                klingai_content_type = "fallback_scene"
            
            logs.append(f"[PARSED CONTENT] ElevenLabs ({elevenlabs_content_type}): {elevenlabs_content[:200]}...")
            logs.append(f"[PARSED CONTENT] KlingAI ({klingai_content_type}): {klingai_content[:200]}...")
            
            # 4. Generate enhanced audio with ElevenLabs (parsed dialogue/narration)
            enhanced_audio = await self._generate_enhanced_audio(elevenlabs_content, chapter_context, animation_style, user_id)
            if not enhanced_audio or "error" in enhanced_audio:
                logs.append(f"[AUDIO ERROR] {enhanced_audio}")
                return {"error": f"Audio generation failed: {enhanced_audio}", "logs": logs}
            
            mixed_audio_url = enhanced_audio.get("mixed_audio_url", "")
            logs.append(f"[AUDIO SUCCESS] Enhanced audio URL: {mixed_audio_url}")
            
            # 5. Generate video with KlingAI (parsed scene descriptions)
            logs.append(f"[KLINGAI DEBUG] About to generate video with content type: {klingai_content_type}")
            logs.append(f"[KLINGAI DEBUG] KlingAI content length: {len(klingai_content)}")
            logs.append(f"[KLINGAI DEBUG] Full KlingAI content:")
            logs.append(f"[KLINGAI CONTENT] {klingai_content}")
            logs.append(f"[KLINGAI DEBUG] Animation style: {animation_style}")
            logs.append(f"[KLINGAI DEBUG] Target duration: 180s")
            
            kling_result = await self._generate_kling_video(klingai_content, animation_style, target_duration=180)  # 3 minutes
            if "video_url" not in kling_result:
                logs.append(f"[KLINGAI ERROR] KlingAI generation failed: {kling_result}")
                raise Exception(f"Kling AI video generation failed: {kling_result.get('error')}")
            
            video_url = kling_result["video_url"]
            logs.append(f"[VIDEO SUCCESS] KlingAI video URL: {video_url}")
            
            # 6. Save KlingAI video metadata to Supabase DB
            try:
                kling_metadata = {
                    "chapter_id": chapter_id,
                    "video_url": video_url,
                    "script": script,
                    "character_details": character_details,
                    "scene_prompt": klingai_content,
                    "created_at": int(time.time()),
                    "source": "klingai"
                }
                if 'book' in chapter_context and 'id' in chapter_context['book']:
                    kling_metadata["book_id"] = chapter_context['book']['id']
                if user_id:
                    kling_metadata["user_id"] = user_id
                logs.append(f"[DB INSERT] Saving KlingAI video metadata: {kling_metadata}")
                db_result_kling = self.supabase_service.table("videos").insert(kling_metadata).execute()
                logs.append(f"[DB INSERT RESULT] {db_result_kling}")
            except Exception as db_exc:
                logs.append(f"[DB INSERT ERROR - KlingAI] {db_exc}")
            
            # Validate URLs before downloading
            def is_valid_url(url):
                return isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))
            
            # Ensure ElevenLabs audio is in Supabase Storage
            if is_valid_url(mixed_audio_url) and "supabase.co" not in mixed_audio_url:
                # Download and upload to Supabase
                import tempfile, httpx, os
                fd, temp_audio_path = tempfile.mkstemp(suffix=".mp3"); os.close(fd)
                try:
                    with httpx.Client() as client:
                        r = client.get(mixed_audio_url)
                        if r.status_code == 200:
                            with open(temp_audio_path, 'wb') as f:
                                f.write(r.content)
                            # Upload to Supabase (append user_id if available)
                            supabase_audio_url = await self._serve_video_from_supabase(temp_audio_path, f"audio_{int(time.time())}.mp3", user_id=user_id)
                            logs.append(f"[AUDIO UPLOAD] Uploaded ElevenLabs audio to Supabase: {supabase_audio_url}")
                            mixed_audio_url = supabase_audio_url
                        else:
                            logs.append(f"[AUDIO DOWNLOAD ERROR] {mixed_audio_url} status {r.status_code}")
                except Exception as e:
                    logs.append(f"[AUDIO DOWNLOAD ERROR] {e}")
            
            # Download video and audio files
            import tempfile, os, subprocess, httpx
            async def download_file(url, suffix):
                # Ensure URL has proper protocol
                if not url.startswith(('http://', 'https://')):
                    if url.startswith('//'):
                        url = 'https:' + url
                    else:
                        url = 'https://' + url
                
                logs.append(f"[DOWNLOAD] Attempting to download: {url}")
                
                fd, path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        r = await client.get(url)
                        r.raise_for_status()  # Raise exception for bad status codes
                        with open(path, 'wb') as f:
                            f.write(r.content)
                        logs.append(f"[DOWNLOAD SUCCESS] Downloaded to: {path}")
                        return path
                except Exception as e:
                    logs.append(f"[DOWNLOAD ERROR] Failed to download {url}: {e}")
                    # Clean up the temp file if it was created
                    if os.path.exists(path):
                        os.remove(path)
                    raise
            
            try:
                video_path = await download_file(video_url, ".mp4")
                audio_path = await download_file(mixed_audio_url, ".mp3")
            except Exception as download_error:
                logs.append(f"[DOWNLOAD FAILED] {download_error}")
                return {"error": f"Failed to download files: {download_error}", "logs": logs}
            
            # Check file existence
            if not os.path.exists(video_path):
                logs.append(f"[ERROR] Video file not found at {video_path}")
                return {"error": "Video file not found", "logs": logs}
            if not os.path.exists(audio_path):
                logs.append(f"[ERROR] Audio file not found at {audio_path}")
                return {"error": "Audio file not found", "logs": logs}
            
            # 7. Merge audio and video with FFmpeg
            merged_path = tempfile.mktemp(suffix="_merged.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                merged_path
            ]
            logs.append(f"[FFMPEG CMD] {' '.join(ffmpeg_cmd)}")
            proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            logs.append(f"[FFMPEG OUT] {proc.stdout}")
            logs.append(f"[FFMPEG ERR] {proc.stderr}")
            if not os.path.exists(merged_path):
                logs.append(f"[ERROR] Merged video not found at {merged_path}")
                return {"error": "Merged video not found", "logs": logs}
            
            # 8. Upload merged video to storage and return URL (append user_id if available)
            merged_video_url = await self._serve_video_from_supabase(merged_path, f"merged_video_{int(time.time())}.mp4", user_id=user_id)
            logs.append(f"[UPLOAD] Merged video public URL: {merged_video_url}")
            
            # 9. Save merged video metadata to Supabase DB
            try:
                merged_metadata = {
                    "chapter_id": chapter_id,
                    "video_url": merged_video_url,
                    "script": script,
                    "character_details": character_details,
                    "scene_prompt": klingai_content,
                    "created_at": int(time.time()),
                    "source": "merged",
                    "klingai_video_url": video_url
                }
                if 'book' in chapter_context and 'id' in chapter_context['book']:
                    merged_metadata["book_id"] = chapter_context['book']['id']
                if user_id:
                    merged_metadata["user_id"] = user_id
                logs.append(f"[DB INSERT] Saving merged video metadata: {merged_metadata}")
                db_result_merged = self.supabase_service.table("videos").insert(merged_metadata).execute()
                logs.append(f"[DB INSERT RESULT] {db_result_merged}")
            except Exception as db_exc:
                logs.append(f"[DB INSERT ERROR - Merged] {db_exc}")
            
            return {
                "merged_video_url": merged_video_url,
                "klingai_video_url": video_url,
                "logs": logs,
                "script": script,
                "characters": characters,
                "character_details": character_details,
                "scene_prompt": klingai_content,
                "elevenlabs_content": elevenlabs_content,
                "klingai_prompt": klingai_content,
                "video_url": merged_video_url,
                "enhanced_audio_url": mixed_audio_url,
                "service_inputs": {
                    "elevenlabs": {
                        "content": elevenlabs_content,
                        "content_type": elevenlabs_content_type,
                        "character_count": len(elevenlabs_content)
                    },
                    "klingai": {
                        "content": klingai_content,
                        "content_type": klingai_content_type,
                        "character_count": len(klingai_content)
                    }
                },
                "parsed_sections": parsed_content.get("parsed_sections", {})
            }
        except Exception as e:
            logs.append(f"[ERROR] {e}")
            print(f"Error generating entertainment video: {e}")
            return {"error": str(e), "logs": logs}

    
    async def get_available_avatars(self) -> List[Dict[str, Any]]:
        """Get available avatars"""
        if not self.api_key:
            return self._get_mock_avatars()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/avatars",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "avatar_id": avatar["avatar_id"],
                            "name": avatar.get("name", "Avatar"),
                            "style": avatar.get("style", "realistic"),
                            "voice_id": avatar.get("voice_id", "default")
                        }
                        for avatar in data.get("avatars", [])
                    ]
                else:
                    return self._get_mock_avatars()
                    
        except Exception as e:
            print(f"Video service error: {e}")
            return self._get_mock_avatars()
    
    async def _poll_video_status(self, video_id: str, scene_description: str) -> Dict[str, Any]:
        """Poll video generation status"""
        max_attempts = 60  # 10 minutes max
        attempt = 0
        
        while attempt < max_attempts:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/videos/{video_id}",
                        headers={"x-api-key": self.api_key}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"📊 Polling response: {data}")
                        
                        # Handle different response formats
                        status = data.get("status") or data.get("data", {}).get("status")
                        
                        if status == "ready" or status == "completed":
                            # Extract video URL from response
                            video_url = data.get("download_url") or data.get("video_url") or data.get("data", {}).get("download_url")
                            
                            return {
                                "id": video_id,
                                "title": scene_description,
                                "description": "AI-generated video content",
                                "video_url": video_url,
                                "thumbnail_url": data.get("thumbnail_url") or data.get("data", {}).get("thumbnail_url"),
                                "duration": data.get("duration", 180),
                                "status": "ready"
                            }
                        elif status == "failed" or status == "error":
                            print(f"❌ Video generation failed: {data}")
                            break
                        else:
                            print(f"⏳ Video status: {status} (attempt {attempt + 1}/{max_attempts})")
                
                # Wait 10 seconds before next poll
                await asyncio.sleep(10)
                attempt += 1
                
            except Exception as e:
                print(f"❌ Polling error: {e}")
                break
        
        # Return error or timeout result
        return {
            "id": video_id,
            "title": scene_description,
            "description": "Video generation failed or timed out",
            "video_url": None,
            "status": "error"
        }
    
    def _get_avatar_id(self, style: str) -> str:
        """Get avatar ID based on style"""
        avatar_map = {
            "realistic": "avatar_001",
            "animated": "avatar_002",
            "cartoon": "avatar_003",
            "tutorial": "avatar_004",
            "story": "avatar_005"
        }
        return avatar_map.get(style, "avatar_001")
    
    def _get_replica_id(self, style: str) -> str:
        """Get replica ID based on style - replace with your actual replica IDs from Tavus"""
        replica_map = {
            "realistic": "rb17cf590e15",  # Replace with your actual replica ID
            "animated": "rb17cf590e15",   # Replace with your actual replica ID
            "cartoon": "rb17cf590e15",    # Replace with your actual replica ID
            "tutorial": "rb17cf590e15",   # Replace with your actual replica ID
            "story": "rb17cf590e15"       # Replace with your actual replica ID
        }
        return replica_map.get(style, "rb17cf590e15")  # Default replica ID
    
    def _get_background_for_style(self, style: str) -> str:
        """Get appropriate background for video style"""
        background_map = {
            "realistic": "bg_001",
            "animated": "bg_002",
            "cartoon": "bg_003",
            "tutorial": "bg_004",
            "story": "bg_005"
        }
        return background_map.get(style, "bg_001")
    
    def _get_voice_id_for_style(self, style: str) -> str:
        """Get appropriate voice ID for video style"""
        voice_map = {
            "realistic": "voice_001",
            "animated": "voice_002",
            "cartoon": "voice_003",
            "tutorial": "voice_004",
            "story": "voice_005"
        }
        return voice_map.get(style, "voice_001")
    
    async def _mock_generate_scene(self, scene_description: str, dialogue: str) -> Dict[str, Any]:
        """Mock video generation for development using FFmpeg and Supabase Storage"""
        # Simulate processing time
        await asyncio.sleep(3)
        
        try:
            # Create a real video file using FFmpeg
            video_path = await self._create_mock_video(duration=180)
            
            if video_path:
                # Generate unique filename
                filename = f"mock_video_{int(time.time())}.mp4"
                
                # Upload to Supabase Storage and get public URL
                video_url = await self._serve_video_from_supabase(video_path, filename)
                
                if video_url:
                    return {
                        "id": f"mock_video_{int(time())}",
                        "title": scene_description,
                        "description": "AI-generated video content for development",
                        "video_url": video_url,
                        "thumbnail_url": "https://via.placeholder.com/1280x720/000000/FFFFFF?text=Video+Thumbnail",
                        "duration": 180,
                        "status": "ready",
                        "mock": True,
                        "local_path": video_path,
                        "supabase_url": video_url
                    }
            
            # Fallback if video creation fails
            print("Video creation failed, returning fallback response")
            return {
                "id": f"mock_video_{int(time())}",
                "title": scene_description,
                "description": "Video generation failed - development mode",
                "video_url": None,
                "thumbnail_url": "https://via.placeholder.com/1280x720/FF0000/FFFFFF?text=Video+Failed",
                "duration": 180,
                "status": "error",
                "mock": True,
                "error": "FFmpeg not available or video creation failed"
            }
            
        except Exception as e:
            print(f"Error in mock video generation: {e}")
            return {
                "id": f"mock_video_{int(time())}",
                "title": scene_description,
                "description": "Video generation error",
                "video_url": None,
                "thumbnail_url": "https://via.placeholder.com/1280x720/FF0000/FFFFFF?text=Error",
                "duration": 180,
                "status": "error",
                "mock": True,
                "error": str(e)
            }
    
    def _get_mock_avatars(self) -> List[Dict[str, Any]]:
        """Return mock avatar data"""
        return [
            {
                "avatar_id": "avatar_001",
                "name": "Narrator",
                "style": "realistic",
                "voice_id": "voice_001"
            },
            {
                "avatar_id": "avatar_002",
                "name": "Character",
                "style": "animated",
                "voice_id": "voice_002"
            },
            {
                "avatar_id": "avatar_003",
                "name": "Mentor",
                "style": "realistic",
                "voice_id": "voice_003"
            },
            {
                "avatar_id": "avatar_004",
                "name": "Instructor",
                "style": "realistic",
                "voice_id": "voice_004"
            }
        ]

    async def _download_file(self, url: str, file_path: str) -> bool:
        """Download a file from URL to local path"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(await response.read())
                        return True
                    else:
                        print(f"Failed to download {url}: {response.status}")
                        return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    async def _merge_video_audio(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """Merge video and audio using FFmpeg"""
        try:
            # Check if FFmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("FFmpeg not found, using fallback method")
                return False
            
            # Merge video and audio
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # Copy video stream without re-encoding
                '-c:a', 'aac',   # Use AAC for audio
                '-shortest',     # End when shortest stream ends
                '-y',            # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully merged video and audio to {output_path}")
                return True
            else:
                print(f"FFmpeg merge failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error merging video and audio: {e}")
            return False

    async def _create_mock_video(self, duration: int = 180) -> str:
        """Create a mock video using FFmpeg for development"""
        try:
            # Check if FFmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("FFmpeg not found, cannot create mock video")
                return None
            
            # Create output directory
            output_dir = Path(settings.UPLOAD_DIR) / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / f"mock_video_{int(time.time())}.mp4"
            
            # Create a simple video with text overlay
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'color=c=black:size=1280x720:duration={duration}',
                '-f', 'lavfi',
                '-i', f'sine=frequency=440:duration={duration}',
                '-vf', 'drawtext=text=\'AI Generated Video\':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Created mock video: {output_path}")
                return str(output_path)
            else:
                print(f"Failed to create mock video: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error creating mock video: {e}")
            return None

    async def _serve_video_file(self, file_path: str) -> str:
        """Serve video file and return accessible URL"""
        try:
            # For development, return a local file path
            # In production, you'd upload to cloud storage and return a CDN URL
            if os.path.exists(file_path):
                # Convert to relative URL for serving
                relative_path = os.path.relpath(file_path, settings.UPLOAD_DIR)
                return f"/uploads/{relative_path}"
            else:
                print(f"Video file not found: {file_path}")
                return None
        except Exception as e:
            print(f"Error serving video file: {e}")
            return None

    async def _merge_real_video_audio(self, tavus_video_url: str, elevenlabs_audio_url: str, scene_description: str) -> Dict[str, Any]:
        """Merge real Tavus video with ElevenLabs audio and upload to Supabase"""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_temp:
                video_path = video_temp.name
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_temp:
                audio_path = audio_temp.name
            
            # Download video and audio files
            video_downloaded = await self._download_file(tavus_video_url, video_path)
            audio_downloaded = await self._download_file(elevenlabs_audio_url, audio_path)
            
            if not video_downloaded or not audio_downloaded:
                print("Failed to download video or audio files")
                return None
            
            # Create output directory and path
            output_dir = Path(settings.UPLOAD_DIR) / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"merged_video_{int(time.time())}.mp4"
            
            # Merge video and audio
            merge_success = await self._merge_video_audio(video_path, audio_path, str(output_path))
            
            # Clean up temporary files
            try:
                os.unlink(video_path)
                os.unlink(audio_path)
            except:
                pass
            
            if merge_success:
                # Generate unique filename for Supabase
                filename = f"merged_video_{int(time.time())}.mp4"
                
                # Upload to Supabase Storage and get public URL
                video_url = await self._serve_video_from_supabase(str(output_path), filename)
                
                if video_url:
                    return {
                        "id": f"merged_video_{int(time())}",
                        "title": scene_description,
                        "description": "AI-generated video with synchronized audio",
                        "video_url": video_url,
                        "thumbnail_url": "https://via.placeholder.com/1280x720/000000/FFFFFF?text=AI+Video",
                        "duration": 180,
                        "status": "ready",
                        "mock": False,
                        "local_path": str(output_path),
                        "supabase_url": video_url
                    }
            
            print("Video merging failed")
            return None
            
        except Exception as e:
            print(f"Error merging real video and audio: {e}")
            return None

    async def _upload_to_supabase_storage(self, file_path: str, filename: str, folder: str = "videos") -> Optional[str]:
        """Upload file to Supabase Storage and return public URL"""
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create storage path
            storage_path = f"{folder}/{filename}"
            
            # Upload to Supabase Storage
            self.supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "video/mp4"}
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
            
            print(f"Uploaded video to Supabase: {public_url}")
            return public_url
            
        except Exception as e:
            print(f"Error uploading to Supabase Storage: {e}")
            return None

    async def _serve_video_from_supabase(self, file_path: str, filename: str, user_id: str = None) -> str:
        """Upload video to Supabase Storage and return public URL"""
        try:
            # Read the file
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create storage path with user organization
            if user_id:
                storage_path = f"users/{user_id}/videos/{filename}"
            else:
                storage_path = f"videos/{filename}"
            
            # Upload to Supabase Storage
            self.supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "video/mp4"}
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).get_public_url(storage_path)
            print(f"[VIDEO UPLOAD] Video uploaded to: {public_url}")
            
            return public_url
            
        except Exception as e:
            print(f"Error uploading video to Supabase: {e}")
            raise

    async def _generate_learning_script(
        self, 
        chapter_content: str, 
        chapter_title: str, 
        book_title: str, 
        video_style: str
    ) -> str:
        """Generate a learning-focused video script using RAGService for richer AI content"""
        try:
            # Use RAGService to get chapter context and generate script
            chapter_context = {
                'chapter': {'title': chapter_title, 'content': chapter_content},
                'book': {'title': book_title, 'book_type': 'learning'},
                'total_context': chapter_content
            }
            if self.rag_service:
                return await self.rag_service.generate_video_script(chapter_context, video_style)
            else:
                # Fallback to basic template if RAGService is not available
                script = f"""
Welcome to {book_title}. In this chapter, we'll explore {chapter_title}.

{chapter_content[:1000]}...

This concludes our discussion of {chapter_title}. Remember to review the key concepts we've covered today.
                """.strip()
                return script
        except Exception as e:
            print(f"Error generating learning script: {e}")
            return chapter_content[:500] + "..."

    async def _generate_entertainment_script(
        self, 
        chapter_content: str, 
        rag_context: Dict[str, Any], 
        script_style: str
    ) -> Dict[str, Any]:
        """Generate entertainment script using OpenAI"""
        try:
            # Use RAG context to enhance script generation
            context_text = rag_context.get("total_context", chapter_content)
            
            if script_style == "screenplay":
                prompt = f"""
Generate a screenplay-style script for a video adaptation of this chapter content.
Focus on dialogue and character interactions.

Chapter Content:
{chapter_content}

Context:
{context_text[:2000]}

Generate a screenplay with:
1. Character names in CAPS
2. Dialogue in quotes
3. Scene descriptions
4. Character details

Return as JSON with: script, character_details, scene_prompt
"""
            else:  # narration
                prompt = f"""
Generate a narration-style script for a video adaptation of this chapter content.
Focus on storytelling and descriptive narration.

Chapter Content:
{chapter_content}

Context:
{context_text[:2000]}

Generate a narration script with:
1. Engaging storytelling
2. Descriptive language
3. Character descriptions
4. Scene descriptions

Return as JSON with: script, character_details, scene_prompt
"""
            
            # Use OpenAI to generate script
            response = await self.rag_service.ai_service.client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {"role": "system", "content": "You are an expert script writer for video adaptations."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Error generating entertainment script: {e}")
            return {
                "script": chapter_content[:500],
                "character_details": "Main character",
                "scene_prompt": "A scene from the story"
            }

    async def _merge_audio_video(
        self, 
        video_url: str, 
        audio_url: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Download and merge audio/video files"""
        try:
            import tempfile
            import subprocess
            import httpx
            
            # Download video and audio files
            async def download_file(url: str, suffix: str) -> str:
                # Ensure URL has proper protocol
                if not url.startswith(('http://', 'https://')):
                    if url.startswith('//'):
                        url = 'https:' + url
                    else:
                        url = 'https://' + url
                
                logs.append(f"[DOWNLOAD] Attempting to download: {url}")
                
                fd, path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        r = await client.get(url)
                        r.raise_for_status()  # Raise exception for bad status codes
                        with open(path, 'wb') as f:
                            f.write(r.content)
                        logs.append(f"[DOWNLOAD SUCCESS] Downloaded to: {path}")
                        return path
                except Exception as e:
                    logs.append(f"[DOWNLOAD ERROR] Failed to download {url}: {e}")
                    # Clean up the temp file if it was created
                    if os.path.exists(path):
                        os.remove(path)
                    raise
            
            try:
                video_path = await download_file(video_url, ".mp4")
                audio_path = await download_file(audio_url, ".mp3")
            except Exception as download_error:
                logs.append(f"[DOWNLOAD FAILED] {download_error}")
                return {"error": f"Failed to download files: {download_error}", "logs": logs}
            
            # Check file existence
            if not os.path.exists(video_path):
                return {"error": "Video file not found"}
            if not os.path.exists(audio_path):
                return {"error": "Audio file not found"}
            
            # Merge with FFmpeg
            merged_path = tempfile.mktemp(suffix="_merged.mp4")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                merged_path
            ]
            
            proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if not os.path.exists(merged_path):
                return {"error": "Merged video not found"}
            
            # Upload merged video to Supabase
            merged_video_url = await self._serve_video_from_supabase(
                merged_path, 
                f"merged_video_{int(time.time())}.mp4",
                user_id
            )
            
            # Clean up temporary files
            os.remove(video_path)
            os.remove(audio_path)
            os.remove(merged_path)
            
            return {"merged_video_url": merged_video_url}
            
        except Exception as e:
            print(f"Error merging audio/video: {e}")
            return {"error": str(e)}

    async def _generate_real_video(self, script: str, video_style: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Generate real video using Tavus API + ElevenLabs audio"""
        try:
            print(f"Generating real video with Tavus API + ElevenLabs using style: {video_style}")
            
            # Step 1: Generate video with Tavus API
            tavus_video = await self._generate_tavus_video(script, video_style)
            if not tavus_video or not tavus_video.get("video_url"):
                print("❌ Tavus video generation failed or no video URL returned.")
                return tavus_video  # Return the failed tavus_video object

            # Step 2: Generate audio with ElevenLabs ONLY if Tavus video was successful
            elevenlabs_audio = await self._generate_elevenlabs_audio(script, video_style, user_id)
            if not elevenlabs_audio:
                print("⚠️  ElevenLabs audio unavailable, returning Tavus video only.")
                return tavus_video  # Return the successful tavus_video (with its URL)

            # Step 3: Merge video and audio (we know tavus_video.get("video_url") is not None here)
            print("Merging Tavus video with ElevenLabs audio...")
            merged_video = await self._merge_real_video_audio(
                tavus_video["video_url"],
                elevenlabs_audio["audio_url"],
                f"AI-generated content in {video_style} style"
            )
            if merged_video:
                print("✅ Successfully merged Tavus video with ElevenLabs audio")
                return merged_video
            else:
                print("Video merging failed, returning Tavus video only")
                return tavus_video
                
        except Exception as e:
            print(f"Error generating real video with Tavus + ElevenLabs: {e}")
            return None

    async def _generate_tavus_video(self, script: str, video_style: str) -> Optional[Dict[str, Any]]:
        """Generate video using Tavus API"""
        try:
            print(f"🎬 Generating Tavus video with style: {video_style}")
            
            # Get replica ID based on style (these should be your actual replica IDs from Tavus)
            replica_id = self._get_replica_id(video_style)
            
            # Prepare Tavus API request
            headers = {
                "x-api-key": settings.TAVUS_API_KEY,
                "Content-Type": "application/json"
            }
            
            # Create video generation request with correct payload structure
            payload = {
                "replica_id": replica_id,  # Required field
                "script": script,
                "video_name": f"AI Generated Video - {video_style}"  # Optional field
            }
            
            print(f"📤 Sending request to Tavus API...")
            print(f"📋 Payload: {payload}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Create a new video
                response = await client.post(
                    f"{self.base_url}/videos",
                    headers=headers,
                    json=payload
                )
                
                print(f"📊 Create Video Response Status: {response.status_code}")
                print(f"📄 Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200 or response.status_code == 201:
                    data = response.json()
                    print(f"✅ Video creation initiated: {data}")
                    
                    video_id = data.get("video_id") or data.get("id")
                    if video_id:
                        # Poll for completion
                        return await self._poll_video_status(video_id, f"AI Generated Video - {video_style}")
                    else:
                        print("❌ No video ID in response")
                        return None
                        
                elif response.status_code == 400:
                    print(f"❌ Bad Request: {response.text}")
                    # Try to get available replicas and use the first one
                    return await self._try_with_available_replicas(client, headers, script, video_style)
                    
                elif response.status_code == 404:
                    print("⚠️  /videos endpoint not found, trying alternative approach...")
                    return await self._try_alternative_video_creation(client, headers, script, video_style)
                    
                else:
                    print(f"❌ Video creation failed: {response.status_code}")
                    print(f"📄 Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error generating Tavus video: {e}")
            return None

    async def _generate_elevenlabs_audio(self, script: str, video_style: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        try:
            # Map video_style to narrator_style
            narrator_style = self._map_video_style_to_narrator_style(video_style)
            audio_url = await self.elevenlabs_service.create_audio_narration(
                text=script, 
                narrator_style=narrator_style,
                user_id=user_id
            )
            if not audio_url:
                print("❌ ElevenLabs audio generation failed or returned None")
                return None
            return {"audio_url": audio_url}
        except Exception as e:
            print(f"❌ Error in _generate_elevenlabs_audio: {e}")
            return None

    def _map_video_style_to_narrator_style(self, video_style: str) -> str:
        """Map video style to narrator style for ElevenLabs"""
        style_map = {
            "realistic": "professional",
            "animated": "engaging",
            "cartoon": "friendly",
            "tutorial": "instructor",
            "story": "narration"
        }
        return style_map.get(video_style, "narration")

    async def _try_alternative_video_creation(self, client, headers, script, video_style):
        """Try alternative methods to create videos with Tavus API"""
        try:
            print("🔄 Trying alternative video creation methods...")
            
            # Method 1: Try to get available videos and use existing ones
            response = await client.get(f"{self.base_url}/videos", headers=headers)
            
            if response.status_code == 200:
                videos_data = response.json()
                print(f"📦 Found {len(videos_data.get('data', []))} existing videos")
                
                # Use the first available video as a template
                if videos_data.get('data'):
                    first_video = videos_data['data'][0]
                    video_id = first_video.get('video_id')
                    
                    if video_id:
                        print(f"✅ Using existing video as template: {video_id}")
                        return await self._poll_video_status(video_id, f"AI Generated Video - {video_style}")
            
            # Method 2: Try different endpoints
            alternative_endpoints = [
                "/scenes",
                "/generate", 
                "/projects",
                "/templates"
            ]
            
            for endpoint in alternative_endpoints:
                try:
                    print(f"🔍 Trying endpoint: {endpoint}")
                    
                    payload = {
                        "script": script[:1000],  # Limit script length
                        "style": video_style,
                        "name": f"AI Video - {video_style}"
                    }
                    
                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    )
                    
                    print(f"📊 {endpoint} Status: {response.status_code}")
                    
                    if response.status_code in [200, 201, 202]:
                        data = response.json()
                        print(f"✅ Success with {endpoint}: {data}")
                        
                        video_id = data.get("id") or data.get("video_id") or data.get("scene_id")
                        if video_id:
                            return await self._poll_video_status(video_id, f"AI Generated Video - {video_style}")
                            
                except Exception as e:
                    print(f"❌ Error with {endpoint}: {e}")
                    continue
            
            print("❌ All alternative methods failed")
            return None
            
        except Exception as e:
            print(f"❌ Error in alternative video creation: {e}")
            return None

    async def _try_with_available_replicas(self, client, headers, script, video_style):
        """Try to get available replicas and use the first one"""
        try:
            print("🔄 Trying to get available replicas...")
            
            # Try to get available replicas
            response = await client.get(f"{self.base_url}/replicas", headers=headers)
            
            if response.status_code == 200:
                replicas_data = response.json()
                print(f"📦 Found {len(replicas_data.get('data', []))} available replicas")
                
                # Use the first available replica
                if replicas_data.get('data'):
                    first_replica = replicas_data['data'][0]
                    replica_id = first_replica.get('replica_id') or first_replica.get('id')
                    
                    if replica_id:
                        print(f"✅ Using available replica: {replica_id}")
                        
                        # Try video creation with this replica
                        payload = {
                            "replica_id": replica_id,
                            "script": script,
                            "video_name": f"AI Generated Video - {video_style}"
                        }
                        
                        response = await client.post(
                            f"{self.base_url}/videos",
                            headers=headers,
                            json=payload
                        )
                        
                        if response.status_code in [200, 201]:
                            data = response.json()
                            video_id = data.get("video_id") or data.get("id")
                            if video_id:
                                return await self._poll_video_status(video_id, f"AI Generated Video - {video_style}")
            
            # If no replicas found, try with a default replica ID
            print("⚠️  No replicas found, trying with default replica ID...")
            default_payload = {
                "replica_id": "rb17cf590e15",  # Default replica ID from your account
                "script": script,
                "video_name": f"AI Generated Video - {video_style}"
            }
            
            response = await client.post(
                f"{self.base_url}/videos",
                headers=headers,
                json=default_payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                video_id = data.get("video_id") or data.get("id")
                if video_id:
                    return await self._poll_video_status(video_id, f"AI Generated Video - {video_style}")
            
            print("❌ Failed to create video with any replica")
            return None
            
        except Exception as e:
            print(f"❌ Error trying with available replicas: {e}")
            return None

    async def _generate_kling_video(self, script: str, video_style: str = "realistic", target_duration: int = 30) -> dict:
        """Generate a video using Kling AI API and return the video URL and metadata."""
        # Calculate proper duration based on content length
        # Rough estimate: 1 second per 10-15 words for natural pacing
        word_count = len(script.split())
        calculated_duration = max(10, min(60, word_count // 12))  # 10-60 seconds range
        
        # Use the calculated duration or target duration, whichever is more appropriate
        final_duration = max(calculated_duration, target_duration)
        
        print(f"[KlingAI DEBUG] Content word count: {word_count}")
        print(f"[KlingAI DEBUG] Calculated duration: {calculated_duration}s")
        print(f"[KlingAI DEBUG] Target duration: {target_duration}s")
        print(f"[KlingAI DEBUG] Final duration: {final_duration}s")
        
        # Generate JWT for Bearer authentication as per Kling AI docs
        headers_jwt = {
            "alg": "HS256",
            "typ": "JWT"
        }
        payload_jwt = {
            "iss": self.kling_access_key_id,
            "exp": int(time.time()) + 1800,  # 30 minutes from now
            "nbf": int(time.time()) - 5       # valid 5 seconds ago
        }
        token = jwt.encode(payload_jwt, self.kling_access_key_secret, algorithm="HS256", headers=headers_jwt)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        print(f"[KlingAI DEBUG] Using Authorization header: Bearer <JWT>")
        
        # If duration is longer than 10 seconds, we need to split into multiple segments
        if final_duration > 10:
            return await self._generate_long_kling_video(script, video_style, final_duration, headers)
        else:
            # For shorter videos, use single KlingAI call
            kling_duration = "10" if final_duration > 5 else "5"
            return await self._generate_single_kling_video(script, video_style, kling_duration, headers, final_duration)

    async def _generate_single_kling_video(self, script: str, video_style: str, kling_duration: str, headers: dict, target_duration: int) -> dict:
        """Generate a single KlingAI video segment"""
        payload = {
            "model_name": "kling-v1",
            "prompt": f"A {video_style} video of: {script}",
            "aspect_ratio": "16:9",
            "duration": kling_duration
        }
        
        print(f"[KlingAI DEBUG] Single video request - duration: {kling_duration}s")
        print(f"[KlingAI DEBUG] Full payload being sent to API:")
        print(f"[KlingAI PAYLOAD] {payload}")
        print(f"[KlingAI DEBUG] Original script length: {len(script)}")
        print(f"[KlingAI DEBUG] Original script preview: {script[:200]}...")
        
        base_url = "https://api-singapore.klingai.com"
        create_url = f"{base_url}/v1/videos/text2video"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    create_url, json=payload, headers=headers, timeout=60
                )
                response.raise_for_status()
                data = response.json()

                task_id = data.get("data", {}).get("task_id")
                if not task_id:
                    raise Exception("No task_id returned from Kling AI")
                
                print(f"[KlingAI DEBUG] Task created with ID: {task_id}")

                # Poll for completion
                poll_url = f"{create_url}/{task_id}"
                for i in range(60):  # Poll for up to 10 minutes
                    await asyncio.sleep(10)
                    print(f"[KlingAI DEBUG] Polling status for task {task_id} (attempt {i+1})")
                    poll_resp = await client.get(poll_url, headers=headers, timeout=30)
                    poll_resp.raise_for_status()
                    poll_data = poll_resp.json()

                    task_status = poll_data.get("data", {}).get("task_status")
                    print(f"[KlingAI DEBUG] Task status: {task_status}")
                    
                    if task_status == "succeed":
                        videos = poll_data.get("data", {}).get("task_result", {}).get("videos", [])
                        if videos and videos[0].get("url"):
                            video_url = videos[0]["url"]
                            print(f"[KlingAI SUCCESS] Video generated: {video_url}")
                            return {
                                "video_url": video_url, 
                                "task_id": task_id, 
                                "meta": poll_data.get("data"),
                                "actual_duration": kling_duration,
                                "target_duration": target_duration,
                                "is_segment": False
                            }
                        else:
                            raise Exception(f"Kling AI task succeeded but no video URL found. Response: {poll_data}")
                    
                    elif task_status == "failed":
                        error_msg = poll_data.get("data", {}).get("task_status_msg", "Unknown error")
                        print(f"[KlingAI ERROR] Task failed with message: {error_msg}")
                        print(f"[KlingAI ERROR] Full error response: {poll_data}")
                        raise Exception(f"Kling AI video generation failed: {error_msg}")

                raise Exception("Kling AI video generation timed out.")
            except Exception as e:
                print(f"[KlingAI ERROR] {e}")
                return {"error": str(e)}

    async def _generate_long_kling_video(self, script: str, video_style: str, target_duration: int, headers: dict) -> dict:
        """Generate a longer video by combining multiple KlingAI segments"""
        print(f"[KlingAI DEBUG] Generating long video: {target_duration}s")
        print(f"[KlingAI DEBUG] Original script length: {len(script)}")
        print(f"[KlingAI DEBUG] Original script preview: {script[:200]}...")
        
        # Split the script into segments for multiple 10-second videos
        segments = self._split_script_for_segments(script, target_duration)
        print(f"[KlingAI DEBUG] Split into {len(segments)} segments")
        
        # Generate each segment
        segment_videos = []
        for i, segment in enumerate(segments):
            print(f"[KlingAI DEBUG] Generating segment {i+1}/{len(segments)}")
            print(f"[KlingAI DEBUG] Segment {i+1} content: {segment}")
            print(f"[KlingAI DEBUG] Segment {i+1} length: {len(segment)}")
            
            result = await self._generate_single_kling_video(
                segment, video_style, "10", headers, 10
            )
            
            if "error" in result:
                print(f"[KlingAI ERROR] Segment {i+1} failed: {result}")
                return result
            
            result["segment_index"] = i
            segment_videos.append(result)
        
        # For now, return the first segment as the main video
        # In a full implementation, you would merge all segments using FFmpeg
        main_video = segment_videos[0]
        main_video["all_segments"] = segment_videos
        main_video["target_duration"] = target_duration
        main_video["is_segment"] = True
        main_video["total_segments"] = len(segments)
        
        print(f"[KlingAI DEBUG] Generated {len(segments)} segments for {target_duration}s video")
        return main_video

    def _split_script_for_segments(self, script: str, target_duration: int) -> List[str]:
        """Split script into segments for multiple video generation"""
        # Simple splitting by sentences for now
        # In a more sophisticated implementation, you might use NLP to split by scenes
        sentences = script.split('. ')
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment + sentence) < 200:  # Rough character limit per segment
                current_segment += sentence + ". "
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + ". "
        
        if current_segment:
            segments.append(current_segment.strip())
        
        # Ensure we have at least one segment
        if not segments:
            segments = [script]
        
        return segments

    def _format_dialogues_for_elevenlabs(self, character_dialogues: List[Dict[str, str]]) -> str:
        """Format character dialogues for ElevenLabs audio generation"""
        if not character_dialogues:
            return ""
        
        formatted_dialogues = []
        for dialogue in character_dialogues:
            formatted_dialogues.append(f"{dialogue['character']}: {dialogue['text']}")
        
        return "\n".join(formatted_dialogues)
    
    def _extract_narration_text(self, script: str) -> str:
        """Extract narration text from script, removing scene descriptions"""
        lines = script.split('\n')
        narration_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip scene descriptions (usually in caps or with specific formatting)
            if (line.isupper() and len(line) > 2 and len(line) < 50) or \
               line.startswith('(') and line.endswith(')') or \
               line.startswith('[') and line.endswith(']') or \
               line.startswith('INT.') or line.startswith('EXT.') or \
               line.startswith('FADE') or line.startswith('CUT'):
                continue
            
            # Include dialogue and narration text
            if line and not line.startswith('    '):  # Not indented dialogue
                narration_lines.append(line)
        
        return "\n".join(narration_lines)

    def _parse_script_for_services(self, script: str, script_style: str) -> Dict[str, Any]:
        """Dynamically parse the generated script to separate content for ElevenLabs and KlingAI"""
        try:
            # Debug: Check script type and content
            print(f"[SCRIPT PARSER DEBUG] Script type: {type(script)}")
            print(f"[SCRIPT PARSER DEBUG] Script content: {script[:200] if script else 'None'}")
            
            # Ensure script is a string
            if not isinstance(script, str):
                print(f"[SCRIPT PARSER ERROR] Script is not a string, converting: {type(script)}")
                script = str(script) if script is not None else ""
            
            if not script or script.strip() == "":
                print("[SCRIPT PARSER WARNING] Empty script, using fallback")
                return {
                    "elevenlabs_content": "Narrator: This is a fallback narration for the video content.",
                    "klingai_content": "A cinematic scene with visual elements and camera movements.",
                    "elevenlabs_content_type": "fallback_narration",
                    "klingai_content_type": "fallback_scene"
                }
            
            if script_style == "cinematic_movie":
                return self._parse_screenplay_script(script)
            else:  # cinematic_narration
                return self._parse_narration_script(script)
        except Exception as e:
            print(f"Error parsing script: {e}")
            print(f"Script content that caused error: {script}")
            import traceback
            traceback.print_exc()
            # Fallback: use entire script for both services
            return {
                "elevenlabs_content": str(script) if script else "Narrator: This is a fallback narration.",
                "klingai_content": str(script) if script else "A cinematic scene with visual elements.",
                "elevenlabs_content_type": "fallback_full_script",
                "klingai_content_type": "fallback_full_script"
            }

    def _parse_screenplay_script(self, script: str) -> Dict[str, Any]:
        """Parse screenplay format script to separate dialogue from scene descriptions"""
        # Initialize content sections
        scene_descriptions = []
        narrator_dialogue = []
        character_dialogue = []
        
        # Split script into lines
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Scene headings (INT./EXT. locations)
            if re.match(r'^(INT\.|EXT\.)', line, re.IGNORECASE):
                scene_descriptions.append(line)
                continue
                
            # Camera directions and scene descriptions
            if any(keyword in line.upper() for keyword in [
                'CAMERA', 'WE SEE', 'THE CAMERA', 'ZOOMS', 'PANS', 'SHOWS', 
                'CUT TO', 'FADE', 'DISSOLVE', 'TRANSITION'
            ]):
                scene_descriptions.append(line)
                continue
                
            # Character names in CAPS (dialogue)
            if re.match(r'^[A-Z][A-Z\s]+$', line) and len(line) < 50:
                # This is a character name, next line should be dialogue
                continue
                
            # Narrator dialogue (V.O. or voice-over)
            if 'NARRATOR' in line.upper() or '(V.O.)' in line.upper() or 'VOICE-OVER' in line.upper():
                # Extract the dialogue part
                dialogue_match = re.search(r'["\']([^"\']+)["\']', line)
                if dialogue_match:
                    narrator_dialogue.append(dialogue_match.group(1))
                else:
                    # If no quotes, take everything after NARRATOR
                    parts = re.split(r'NARRATOR\s*\(?V\.O\.\)?\s*:', line, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        narrator_dialogue.append(parts[1].strip())
                continue
                
            # Character dialogue in quotes
            if '"' in line or "'" in line:
                dialogue_match = re.search(r'["\']([^"\']+)["\']', line)
                if dialogue_match:
                    character_dialogue.append(dialogue_match.group(1))
                continue
                
            # Action descriptions (not dialogue, not scene headings)
            if not re.match(r'^[A-Z][A-Z\s]+$', line) and len(line) > 10:
                scene_descriptions.append(line)
                continue
        
        # Combine content for each service
        elevenlabs_content = self._format_dialogues_for_elevenlabs([
            {"character": "NARRATOR", "dialogue": dialogue} 
            for dialogue in narrator_dialogue
        ] + [
            {"character": "CHARACTER", "dialogue": dialogue} 
            for dialogue in character_dialogue
        ])
        
        klingai_content = "\n".join(scene_descriptions)
        
        return {
            "elevenlabs_content": elevenlabs_content,
            "klingai_content": klingai_content,
            "elevenlabs_content_type": "character_and_narrator_dialogue",
            "klingai_content_type": "scene_descriptions_and_camera_directions",
            "parsed_sections": {
                "scene_descriptions": scene_descriptions,
                "narrator_dialogue": narrator_dialogue,
                "character_dialogue": character_dialogue
            }
        }

    def _parse_narration_script(self, script: str) -> Dict[str, Any]:
        """Parse narration format script to separate narrative text from scene descriptions"""
        # For narration scripts, most content goes to ElevenLabs
        # Scene descriptions (camera directions) go to KlingAI
        
        scene_descriptions = []
        narration_text = []
        
        lines = script.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Camera directions and visual descriptions
            if any(keyword in line.upper() for keyword in [
                'CAMERA', 'WE SEE', 'THE CAMERA', 'ZOOMS', 'PANS', 'SHOWS', 
                'VISUAL', 'SCENE', 'SETTING', 'BACKGROUND'
            ]):
                scene_descriptions.append(line)
            else:
                # Everything else is narration
                narration_text.append(line)
        
        elevenlabs_content = "\n".join(narration_text)
        klingai_content = "\n".join(scene_descriptions) if scene_descriptions else "A cinematic scene based on the narration"
        
        return {
            "elevenlabs_content": elevenlabs_content,
            "klingai_content": klingai_content,
            "elevenlabs_content_type": "narration_text",
            "klingai_content_type": "scene_descriptions",
            "parsed_sections": {
                "narration_text": narration_text,
                "scene_descriptions": scene_descriptions
            }
        }