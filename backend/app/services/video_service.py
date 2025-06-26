import httpx
from typing import List, Dict, Any, Optional
import asyncio
from app.core.config import settings
from app.services.rag_service import RAGService
from app.services.elevenlabs_service import ElevenLabsService


class VideoService:
    """Video generation service using Tavus API with RAG and ElevenLabs integration"""
    
    def __init__(self, supabase_client=None):
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = "https://api.tavus.io/v2"
        self.rag_service = RAGService(supabase_client) if supabase_client else None
        self.elevenlabs_service = ElevenLabsService()
    
    async def generate_video_from_chapter(
        self,
        chapter_id: str,
        video_style: str = "realistic",
        include_context: bool = True,
        include_audio_enhancement: bool = True,
        supabase_client = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using RAG-retrieved chapter content with ElevenLabs audio enhancement"""
        if not self.rag_service and supabase_client:
            self.rag_service = RAGService(supabase_client)
        
        if not self.rag_service:
            raise ValueError("RAG service not initialized. Please provide supabase_client.")
        
        try:
            # 1. Retrieve chapter content with context using RAG
            chapter_context = await self.rag_service.get_chapter_with_context(
                chapter_id, 
                include_adjacent=include_context
            )
            
            if not chapter_context:
                raise ValueError(f"Could not retrieve context for chapter {chapter_id}")
            
            # 2. Generate optimized script based on book type and context
            script = await self.rag_service.generate_video_script(
                chapter_context, 
                video_style
            )
            
            # 3. Get video metadata
            metadata = await self.rag_service.get_video_metadata(
                chapter_context, 
                video_style
            )
            
            # 4. Generate enhanced audio if requested
            enhanced_audio = None
            if include_audio_enhancement:
                enhanced_audio = await self._generate_enhanced_audio(
                    script, 
                    chapter_context, 
                    video_style
                )
            
            # 5. Generate video with Tavus
            video_result = await self.generate_story_scene(
                scene_description=metadata['title'],
                dialogue=script,
                avatar_style=video_style
            )
            
            if video_result:
                # Add RAG context and audio enhancement to video result
                video_result.update({
                    'chapter_id': chapter_id,
                    'book_id': chapter_context['book']['id'],
                    'book_type': chapter_context['book']['book_type'],
                    'script': script,
                    'metadata': metadata,
                    'enhanced_audio': enhanced_audio
                })
            
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
                    'duration': metadata.get('estimated_duration', 180)
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
            
            # Mix all audio tracks
            mixed_audio = await self.elevenlabs_service.mix_audio_tracks(
                main_audio_path=character_audios[0]['audio_url'] if character_audios else None,
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
        """Generate entertainment-style video for story content"""
        return await self.generate_video_from_chapter(
            chapter_id=chapter_id,
            video_style=animation_style,
            include_context=True,
            include_audio_enhancement=True,
            supabase_client=supabase_client
        )
    
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
                        headers={"Authorization": f"Bearer {self.api_key}"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("status") == "completed":
                            return {
                                "id": video_id,
                                "title": scene_description,
                                "description": "AI-generated video content",
                                "video_url": data.get("download_url"),
                                "thumbnail_url": data.get("thumbnail_url"),
                                "duration": data.get("duration", 180),
                                "status": "ready"
                            }
                        elif data.get("status") == "failed":
                            break
                
                # Wait 10 seconds before next poll
                await asyncio.sleep(10)
                attempt += 1
                
            except Exception as e:
                print(f"Polling error: {e}")
                break
        
        # Return error or timeout result
        return {
            "id": video_id,
            "title": scene_description,
            "description": "Video generation failed or timed out",
            "status": "error"
        }
    
    def _get_avatar_id(self, style: str) -> str:
        """Get avatar ID based on style"""
        avatar_map = {
            "realistic": "realistic_avatar_id",
            "animated": "animated_avatar_id",
            "cartoon": "cartoon_avatar_id",
            "tutorial": "instructor_avatar_id",
            "story": "narrator_avatar_id"
        }
        return avatar_map.get(style, "realistic_avatar_id")
    
    def _get_background_for_style(self, style: str) -> str:
        """Get appropriate background for video style"""
        background_map = {
            "realistic": "professional",
            "animated": "fantasy",
            "cartoon": "colorful",
            "tutorial": "classroom",
            "story": "mystical"
        }
        return background_map.get(style, "professional")
    
    def _get_voice_id_for_style(self, style: str) -> str:
        """Get appropriate voice ID for video style"""
        voice_map = {
            "realistic": "professional",
            "animated": "young",
            "cartoon": "friendly",
            "tutorial": "instructor",
            "story": "narrator"
        }
        return voice_map.get(style, "professional")
    
    async def _mock_generate_scene(self, scene_description: str, dialogue: str) -> Dict[str, Any]:
        """Mock video generation for development"""
        # Simulate processing time
        await asyncio.sleep(3)
        
        return {
            "id": f"scene_{hash(scene_description)}",
            "title": scene_description,
            "description": "AI-generated video content (Demo)",
            "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "thumbnail_url": "https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=400",
            "duration": 180,
            "status": "ready"
        }
    
    def _get_mock_avatars(self) -> List[Dict[str, Any]]:
        """Return mock avatar data"""
        return [
            {
                "avatar_id": "narrator_avatar",
                "name": "Narrator",
                "style": "realistic",
                "voice_id": "professional"
            },
            {
                "avatar_id": "character_avatar",
                "name": "Character",
                "style": "animated",
                "voice_id": "young"
            },
            {
                "avatar_id": "mentor_avatar",
                "name": "Mentor",
                "style": "realistic",
                "voice_id": "wise"
            },
            {
                "avatar_id": "instructor_avatar",
                "name": "Instructor",
                "style": "realistic",
                "voice_id": "professional"
            }
        ]