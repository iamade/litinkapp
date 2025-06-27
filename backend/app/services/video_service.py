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


class VideoService:
    """Video generation service using Tavus API with RAG and ElevenLabs integration"""
    
    def __init__(self, supabase_client=None):
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = "https://tavusapi.com/v2"
        self.rag_service = RAGService(supabase_client) if supabase_client else None
        self.elevenlabs_service = ElevenLabsService()
        
        # Initialize Supabase client for storage
        if supabase_client:
            self.supabase = supabase_client
        else:
            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
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
                "*, books(title, cover_image_url, book_type, difficulty)"
            ).eq("id", chapter_id).single().execute()
            
            if not chapter_response.data:
                raise ValueError("Chapter not found")
            
            chapter_data = chapter_response.data
            book_data = chapter_data.get("books", {})
            
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
                video_result = await self._generate_real_video(script, video_style)
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
        video_style: str
    ) -> Optional[Dict[str, Any]]:
        """Generate enhanced audio with ElevenLabs for video content"""
        try:
            book = chapter_context['book']
            chapter = chapter_context['chapter']
            
            if book['book_type'] == 'learning':
                # Generate tutorial narration
                narration_audio = await self.elevenlabs_service.create_audio_narration(
                    script=script,
                    narrator_style="professional"
                )
                
                return {
                    'type': 'tutorial_narration',
                    'audio_url': narration_audio,
                    'duration': 180  # Default 3 minutes
                }
            
            else:
                # Generate entertainment audio with character voices and sound effects
                return await self._generate_entertainment_audio(script, chapter_context, video_style)
                
        except Exception as e:
            print(f"Error generating enhanced audio: {e}")
            return None
    
    async def _generate_entertainment_audio(
        self, 
        script: str, 
        chapter_context: Dict[str, Any], 
        video_style: str
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
                    character_profile=character_profile,
                    scene_context=chapter_context['chapter']['title']
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
                intensity=0.3
            )
            
            # Handle case where no character dialogues were found
            if not character_audios:
                print("Warning: No character dialogues found in script, using fallback audio")
                # Create a fallback narration audio
                fallback_audio = await self.elevenlabs_service.create_audio_narration(
                    script=script[:500],  # Use first 500 characters as fallback
                    narrator_style="professional"
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
                main_audio_path=character_audios[0]['audio_url'],
                background_audio_path=background_audio,
                sound_effects=[audio['audio_url'] for audio in character_audios[1:]]
            )
            
            return {
                'type': 'entertainment_audio',
                'audio_url': mixed_audio,
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
        supabase_client = None
    ) -> Optional[Dict[str, Any]]:
        """Generate entertainment-style video for story content using RAG and OpenAI"""
        try:
            # 1. Get chapter context using RAG
            chapter_context = await self.rag_service.get_chapter_with_context(
                chapter_id=chapter_id,
                include_adjacent=True,
                use_vector_search=True
            )

            # 2. Generate script using OpenAI (not PlotDrive)
            script = await self.rag_service.generate_video_script(
                chapter_context=chapter_context,
                video_style=animation_style
            )

            # 3. Continue with video/audio generation as before...
            return await self._generate_real_video(script, animation_style)
        except Exception as e:
            print(f"Error in generate_entertainment_video: {e}")
            return None

    
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
        max_attempts = 30  # 5 minutes max
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
                        "id": f"mock_video_{int(time.time())}",
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
                "id": f"mock_video_{int(time.time())}",
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
                "id": f"mock_video_{int(time.time())}",
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
                        "id": f"merged_video_{int(time.time())}",
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

    async def _serve_video_from_supabase(self, file_path: str, filename: str) -> str:
        """Upload video to Supabase and return public URL"""
        try:
            # Upload to Supabase Storage
            public_url = await self._upload_to_supabase_storage(file_path, filename)
            
            if public_url:
                return public_url
            else:
                # Fallback to local serving if Supabase upload fails
                print("Supabase upload failed, falling back to local serving")
                return await self._serve_video_file(file_path)
                
        except Exception as e:
            print(f"Error serving video from Supabase: {e}")
            # Fallback to local serving
            return await self._serve_video_file(file_path)

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
        chapter_title: str, 
        book_title: str, 
        video_style: str
    ) -> str:
        """Generate an entertainment-focused video script using RAGService for richer AI content"""
        try:
            # Use RAGService to get chapter context and generate script
            chapter_context = {
                'chapter': {'title': chapter_title, 'content': chapter_content},
                'book': {'title': book_title, 'book_type': 'entertainment'},
                'total_context': chapter_content
            }
            if self.rag_service:
                return await self.rag_service.generate_video_script(chapter_context, video_style)
            else:
                # Fallback to basic template if RAGService is not available
                script = f"""
Join us for an exciting journey through {book_title}, as we dive into {chapter_title}.

{chapter_content[:1000]}...

What an incredible adventure! Stay tuned for more from {book_title}.
                """.strip()
                return script
        except Exception as e:
            print(f"Error generating entertainment script: {e}")
            return chapter_content[:500] + "..."

    async def _generate_real_video(self, script: str, video_style: str) -> Optional[Dict[str, Any]]:
        """Generate real video using Tavus API + ElevenLabs audio"""
        try:
            print(f"Generating real video with Tavus API + ElevenLabs using style: {video_style}")
            
            # Step 1: Generate video with Tavus API
            tavus_video = await self._generate_tavus_video(script, video_style)
            if not tavus_video:
                print("❌ Tavus video generation failed")
                return None
            
            # Step 2: Generate audio with ElevenLabs
            elevenlabs_audio = await self._generate_elevenlabs_audio(script, video_style)
            if not elevenlabs_audio:
                print("⚠️  ElevenLabs audio unavailable, returning Tavus video only")
                return tavus_video
            
            # Step 3: Merge video and audio
            if tavus_video.get("video_url"):
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
            else:
                print("⚠️  Tavus video URL not available, skipping audio merge.")
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

    async def _generate_elevenlabs_audio(self, script: str, video_style: str) -> Optional[Dict[str, Any]]:
        try:
            # Map video_style to narrator_style
            narrator_style = self._map_video_style_to_narrator_style(video_style)
            audio = await self.elevenlabs_service.create_audio_narration(text=script, narrator_style=narrator_style)
            if not audio:
                print("❌ ElevenLabs audio generation failed or returned None")
                return None
            return audio
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