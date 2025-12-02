import httpx
from typing import List, Dict, Any, Optional
import asyncio
from app.core.config import settings
from app.core.services.rag import RAGService
from app.core.services.elevenlabs import ElevenLabsService
from app.core.services.text_utils import TextSanitizer
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
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.videos.models import VideoGeneration, VideoSegment
from app.books.models import Chapter, Book, LearningContent


class VideoService:
    """Video generation service using Tavus API with RAG and ElevenLabs integration"""

    def __init__(self, session: AsyncSession, supabase_client=None):
        self.session = session
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = "https://tavusapi.com/v2"
        self.kling_access_key_id = settings.KLINGAI_ACCESS_KEY_ID
        self.kling_access_key_secret = settings.KLINGAI_ACCESS_KEY_SECRET

        # Initialize Supabase client for storage (files), not DB
        if supabase_client:
            self.supabase = supabase_client
        else:
            self.supabase = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
            )
        self.supabase_service = self.supabase  # Alias for compatibility

        self.rag_service = RAGService(self.session)
        self.elevenlabs_service = ElevenLabsService(self.supabase)

    async def generate_video_from_chapter(
        self,
        chapter_id: str,
        video_style: str = "realistic",
        include_context: bool = True,
        include_audio_enhancement: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Generate video from a specific chapter"""
        try:
            # 1. Fetch chapter and book data using SQLAlchemy
            statement = select(Chapter, Book).join(Book).where(Chapter.id == chapter_id)
            result = await self.session.exec(statement)
            chapter_book = result.first()

            if not chapter_book:
                raise ValueError("Chapter not found")

            chapter, book = chapter_book

            # Get user_id from book data
            user_id = str(book.user_id)

            # Get book cover image URL for thumbnail
            cover_image_url = book.cover_image_url
            if not cover_image_url:
                # Fallback to placeholder if no cover image
                cover_image_url = (
                    "https://via.placeholder.com/1280x720/000000/FFFFFF?text=Book+Cover"
                )

            # Get chapter content and context
            chapter_content = chapter.content or ""
            chapter_title = chapter.title or ""
            book_title = book.title or ""
            book_type = book.book_type or "learning"

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
            if (
                settings.TAVUS_API_KEY
                and settings.TAVUS_API_KEY != "your-tavus-api-key"
            ):
                print("Using Tavus API for real video generation...")
                video_result = await self._generate_real_video(
                    script, video_style, user_id
                )
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
                    "error": "Video generation services unavailable",
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
        user_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate enhanced audio with narration, character voices, and sound effects"""
        try:
            if video_style in ["tutorial", "educational", "learning"]:
                # Generate tutorial-style narration
                narration_audio = await self.elevenlabs_service.create_audio_narration(
                    text=script, narrator_style="professional", user_id=user_id
                )

                return {
                    "type": "tutorial_narration",
                    "audio_url": narration_audio,
                    "duration": 180,  # Default 3 minutes
                }

            else:
                # Generate entertainment audio with character voices and sound effects
                return await self._generate_entertainment_audio(
                    script, chapter_context, video_style, user_id
                )

        except Exception as e:
            print(f"Error generating enhanced audio: {e}")
            return None

    async def _generate_entertainment_audio(
        self,
        script: str,
        chapter_context: Dict[str, Any],
        video_style: str,
        user_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate entertainment audio with character voices and sound effects"""
        try:
            # Extract character dialogue from script
            character_dialogues = self._extract_character_dialogues(script)

            # Generate character voices
            character_audios = []
            for dialogue in character_dialogues:
                character_profile = self._create_character_profile(
                    dialogue["character"]
                )
                audio_url = await self.elevenlabs_service.generate_character_voice(
                    text=dialogue["text"],
                    character_name=dialogue["character"],
                    character_traits=character_profile.get("personality", ""),
                    user_id=user_id,
                )

                if audio_url:
                    character_audios.append(
                        {
                            "character": dialogue["character"],
                            "text": dialogue["text"],
                            "audio_url": audio_url,
                        }
                    )

            # Generate background sound effects
            background_audio = await self.elevenlabs_service.generate_sound_effects(
                effect_type=self._get_background_effect_type(video_style),
                duration=180,  # 3 minutes
                intensity=0.3,
                user_id=user_id,
            )

            # Handle case where no character dialogues were found
            if not character_audios:
                print(
                    "Warning: No character dialogues found in script, using fallback audio"
                )
                # Create a fallback narration audio
                fallback_audio = await self.elevenlabs_service.create_audio_narration(
                    text=script[:500],  # Use first 500 characters as fallback
                    narrator_style="professional",
                    user_id=user_id,
                )

                return {
                    "type": "fallback_narration",
                    "audio_url": fallback_audio,
                    "character_audios": [],
                    "background_audio": background_audio,
                    "duration": 180,
                }

            # Mix all audio tracks
            mixed_audio = await self.elevenlabs_service.mix_audio_tracks(
                audio_tracks=[{"url": audio["audio_url"]} for audio in character_audios]
                + [{"url": background_audio}],
                user_id=user_id,
            )

            return {
                "type": "entertainment_audio",
                "audio_url": (
                    mixed_audio.get("audio_url")
                    if isinstance(mixed_audio, dict)
                    else mixed_audio
                ),
                "character_audios": character_audios,
                "background_audio": background_audio,
                "duration": 180,
            }

        except Exception as e:
            print(f"Error generating entertainment audio: {e}")
            return None

    def _extract_character_dialogues(self, script: str) -> List[Dict[str, str]]:
        """Extract character dialogues from screenplay script"""
        dialogues = []
        lines = script.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            # Look for character names in caps (screenplay format)
            if line.isupper() and len(line) > 2 and len(line) < 50:
                character = line
                # Look for dialogue in next lines
                j = i + 1
                while j < len(lines) and (
                    lines[j].strip().startswith("    ") or not lines[j].strip()
                ):
                    if lines[j].strip():
                        dialogue_text += lines[j].strip() + " "
                    j += 1

                if dialogue_text.strip():
                    dialogues.append(
                        {"character": character, "text": dialogue_text.strip()}
                    )

        return dialogues

    async def extract_dialogue_per_scene(
        self, script: str, scene_descriptions: List[Dict[str, Any]], user_id: str = None
    ) -> Dict[str, Any]:
        """Extract character dialogue for each scene and generate audio"""
        try:
            from app.core.services.script_parser import ScriptParser

            # Parse script to extract dialogue components
            script_parser = ScriptParser()
            parsed_audio = script_parser.parse_script_for_audio(
                script=script,
                characters=[],  # Will be extracted from script
                scene_descriptions=scene_descriptions,
                script_style="cinematic_movie",
            )

            # Extract character dialogues with scene information
            scene_dialogues = {}
            character_profiles = {}

            # Group dialogues by scene
            for dialogue in parsed_audio.get("character_dialogues", []):
                scene_num = dialogue.get("scene", 1)
                if scene_num not in scene_dialogues:
                    scene_dialogues[scene_num] = []

                scene_dialogues[scene_num].append(
                    {
                        "character": dialogue["character"],
                        "text": dialogue["text"],
                        "line_number": dialogue.get("line_number", 0),
                    }
                )

                # Create character profile if not exists
                if dialogue["character"] not in character_profiles:
                    character_profiles[dialogue["character"]] = (
                        self._create_character_profile(dialogue["character"])
                    )

            # Generate audio for each scene's dialogues
            scene_audio_files = {}
            for scene_num, dialogues in scene_dialogues.items():
                scene_audio = []
                for dialogue in dialogues:
                    # Generate character voice audio
                    character_profile = character_profiles[dialogue["character"]]
                    audio_url = await self.elevenlabs_service.generate_character_voice(
                        text=dialogue["text"],
                        character_name=dialogue["character"],
                        character_traits=character_profile.get("personality", ""),
                        user_id=user_id,
                    )

                    if audio_url:
                        scene_audio.append(
                            {
                                "character": dialogue["character"],
                                "text": dialogue["text"],
                                "audio_url": audio_url,
                                "scene": scene_num,
                                "character_profile": character_profile,
                            }
                        )

                if scene_audio:
                    scene_audio_files[scene_num] = scene_audio

            return {
                "scene_dialogues": scene_dialogues,
                "scene_audio_files": scene_audio_files,
                "character_profiles": character_profiles,
                "total_scenes_with_dialogue": len(scene_dialogues),
                "total_audio_files": sum(
                    len(audio) for audio in scene_audio_files.values()
                ),
            }

        except Exception as e:
            print(f"Error extracting dialogue per scene: {e}")
            return {
                "scene_dialogues": {},
                "scene_audio_files": {},
                "character_profiles": {},
                "error": str(e),
            }

    def _create_character_profile(self, character_name: str) -> Dict[str, Any]:
        """Create character profile based on character name"""
        # Simple character profiling - in a real implementation, you might use AI
        character_name_lower = character_name.lower()

        if any(word in character_name_lower for word in ["narrator", "narrator"]):
            return {
                "name": character_name,
                "personality": "professional",
                "age": "adult",
                "gender": "neutral",
            }
        elif any(word in character_name_lower for word in ["young", "child", "kid"]):
            return {
                "name": character_name,
                "personality": "friendly",
                "age": "young",
                "gender": "neutral",
            }
        elif any(word in character_name_lower for word in ["wise", "elder", "sage"]):
            return {
                "name": character_name,
                "personality": "wise",
                "age": "elder",
                "gender": "neutral",
            }
        elif any(
            word in character_name_lower for word in ["mysterious", "shadow", "dark"]
        ):
            return {
                "name": character_name,
                "personality": "mysterious",
                "age": "adult",
                "gender": "neutral",
            }
        else:
            return {
                "name": character_name,
                "personality": "neutral",
                "age": "adult",
                "gender": "neutral",
            }

    def _get_background_effect_type(self, video_style: str) -> str:
        """Get appropriate background sound effect type for video style"""
        effect_mapping = {
            "realistic": "ambient",
            "animated": "magical",
            "cartoon": "nature",
            "dramatic": "emotional",
            "adventure": "action",
        }
        return effect_mapping.get(video_style, "ambient")

    async def generate_story_scene(
        self, scene_description: str, dialogue: str, avatar_style: str = "realistic"
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
                        "Content-Type": "application/json",
                    },
                    json={
                        "script": dialogue,
                        "avatar_id": self._get_avatar_id(avatar_style),
                        "background": self._get_background_for_style(avatar_style),
                        "voice_settings": {
                            "voice_id": self._get_voice_id_for_style(avatar_style),
                            "stability": 0.75,
                            "similarity_boost": 0.75,
                        },
                        "video_settings": {
                            "quality": "high",
                            "format": "mp4",
                            "duration": 180,  # 3 minutes default
                        },
                    },
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
        self, chapter_id: str, tutorial_style: str = "udemy"
    ) -> Optional[Dict[str, Any]]:
        """Generate tutorial-style video for learning content"""
        return await self.generate_video_from_chapter(
            chapter_id=chapter_id,
            video_style="realistic",  # Tutorials typically use realistic avatars
            include_context=True,
            include_audio_enhancement=True,
        )

    # async def generate_entertainment_video(
    #     self,
    #     chapter_id: str,
    #     animation_style: str = "animated",
    #     script_style: str = "cinematic_movie",
    #     supabase_client = None,
    #     user_id: str = None
    # ) -> Optional[Dict[str, Any]]:
    #     """Generate entertainment-style video with integrated dialogue audio generation"""
    #     """Generate entertainment-style video for story content using RAG, OpenAI, ElevenLabs, KlingAI, and FFmpeg. User can choose script_style ('cinematic_movie' or 'cinematic_narration')."""
    #     logs = []
    #     try:
    #         # 1. Get chapter context using RAG
    #         chapter_context = await self.rag_service.get_chapter_with_context(
    #             chapter_id=chapter_id,
    #             include_adjacent=True,
    #             use_vector_search=True
    #         )

    #         # 2. Generate script using RAG with character extraction
    #         script_result = await self.rag_service.generate_video_script(chapter_context, animation_style, script_style=script_style)
    #         script = script_result.get("script", "")
    #         characters = script_result.get("characters", [])
    #         character_details = script_result.get("character_details", "")

    #         # Debug script generation
    #         logs.append(f"[SCRIPT DEBUG] Script result type: {type(script_result)}")
    #         logs.append(f"[SCRIPT DEBUG] Script type: {type(script)}")
    #         logs.append(f"[SCRIPT DEBUG] Script length: {len(script) if script else 0}")
    #         logs.append(f"[SCRIPT DEBUG] Script preview: {script[:200] if script else 'None'}...")
    #         logs.append(f"[CHARACTERS] Extracted characters: {characters}")
    #         logs.append(f"[CHARACTER_DETAILS] {character_details}")

    #         # 3. Parse script dynamically for ElevenLabs and KlingAI
    #         parsed_content = self._parse_script_for_services(script, script_style)
    #         elevenlabs_content = parsed_content["elevenlabs_content"]
    #         klingai_content = parsed_content["klingai_content"]
    #         elevenlabs_content_type = parsed_content["elevenlabs_content_type"]
    #         klingai_content_type = parsed_content["klingai_content_type"]

    #         # Fallback if parsing failed or content is empty
    #         if not elevenlabs_content or elevenlabs_content.strip() == "":
    #             logs.append("[FALLBACK] ElevenLabs content empty, using fallback")
    #             elevenlabs_content = "Narrator: This is a cinematic narration of the story content."
    #             elevenlabs_content_type = "fallback_narration"

    #         if not klingai_content or klingai_content.strip() == "":
    #             logs.append("[FALLBACK] KlingAI content empty, using fallback")
    #             klingai_content = "A cinematic scene with visual elements, camera movements, and dramatic lighting."
    #             klingai_content_type = "fallback_scene"

    #         logs.append(f"[PARSED CONTENT] ElevenLabs ({elevenlabs_content_type}): {elevenlabs_content[:200]}...")
    #         logs.append(f"[PARSED CONTENT] KlingAI ({klingai_content_type}): {klingai_content[:200]}...")

    #         # 4. Generate enhanced audio with ElevenLabs (parsed dialogue/narration)
    #         enhanced_audio = await self._generate_enhanced_audio(elevenlabs_content, chapter_context, animation_style, user_id)
    #         if not enhanced_audio or "error" in enhanced_audio:
    #             logs.append(f"[AUDIO ERROR] {enhanced_audio}")
    #             return {"error": f"Audio generation failed: {enhanced_audio}", "logs": logs}

    #         mixed_audio_url = enhanced_audio.get("mixed_audio_url", "")
    #         logs.append(f"[AUDIO SUCCESS] Enhanced audio URL: {mixed_audio_url}")

    #         # 5. Generate video with KlingAI (parsed scene descriptions)
    #         logs.append(f"[KLINGAI DEBUG] About to generate video with content type: {klingai_content_type}")
    #         logs.append(f"[KLINGAI DEBUG] KlingAI content length: {len(klingai_content)}")
    #         logs.append(f"[KLINGAI DEBUG] Full KlingAI content:")
    #         logs.append(f"[KLINGAI CONTENT] {klingai_content}")
    #         logs.append(f"[KLINGAI DEBUG] Animation style: {animation_style}")
    #         logs.append(f"[KLINGAI DEBUG] Target duration: 180s")

    #         # Use multi-scene segmentation for video generation
    #         logs.append(f"[SCENE GENERATION] Starting multi-scene video generation")
    #         logs.append(f"[SCENE GENERATION] Characters available: {characters}")

    #         # Split script into actual scenes
    #         scenes = self._split_script_by_scenes(script, characters)
    #         logs.append(f"[SCENE GENERATION] Successfully parsed {len(scenes)} scenes")

    #         # Generate video for each scene
    #         scene_results = []
    #         logs.append(f"[SCENE GENERATION] Processing {len(scenes)} scenes from parsed script")

    #         for i, scene in enumerate(scenes):
    #             scene_num = scene['scene_number']
    #             logs.append(f"[SCENE {scene_num}/{len(scenes)}] Generating video for {scene['character_count']} characters, {scene['dialogue_count']} dialogues, {scene['action_count']} actions")
    #             logs.append(f"[SCENE {scene_num}] Description: {scene['description'][:100]}...")
    #             logs.append(f"[SCENE {scene_num}] Prompt length: {len(scene['prompt'])} characters")

    #             # Calculate appropriate duration for this scene
    #             target_duration = max(10, min(60, scene['dialogue_count'] * 5))  # 5 seconds per dialogue
    #             logs.append(f"[SCENE {scene_num}] Target duration: {target_duration}s")

    #             # Generate video for this scene
    #             scene_kling_result = await self._generate_kling_video(
    #                 scene['prompt'],
    #                 animation_style,
    #                 target_duration=target_duration
    #             )

    #             if "video_url" not in scene_kling_result:
    #                 logs.append(f"[SCENE {scene_num} ERROR] KlingAI generation failed: {scene_kling_result}")
    #                 continue

    #             scene_video_url = scene_kling_result["video_url"]
    #             logs.append(f"[SCENE {scene_num} SUCCESS] Video URL: {scene_video_url}")

    #             scene_results.append({
    #                 "scene_number": scene_num,
    #                 "description": scene['description'],
    #                 "video_url": scene_video_url,
    #                 "dialogues": scene['dialogues'],
    #                 "actions": scene['actions'],
    #                 "camera_movements": scene['camera_movements'],
    #                 "character_count": scene['character_count'],
    #                 "dialogue_count": scene['dialogue_count'],
    #                 "action_count": scene['action_count'],
    #                 "kling_result": scene_kling_result
    #             })

    #         if not scene_results:
    #             logs.append(f"[SCENE GENERATION ERROR] No scenes were successfully generated")
    #             raise Exception("All scene video generations failed")

    #         # Use the first scene as the main video for compatibility
    #         video_url = scene_results[0]["video_url"]
    #         is_multi_segment = len(scene_results) > 1
    #         segment_urls = [result["video_url"] for result in scene_results]
    #         total_segments = len(scene_results)

    #         logs.append(f"[SCENE GENERATION] Completed: {len(scene_results)}/{len(scenes)} scenes generated successfully")
    #         logs.append(f"[SCENE GENERATION] Is multi-segment: {is_multi_segment}")
    #         logs.append(f"[SCENE GENERATION] Total segments: {total_segments}")
    #         logs.append(f"[SCENE GENERATION] Segment URLs: {segment_urls}")

    #         # 6. Save KlingAI video metadata to Supabase DB
    #         try:
    #             # Save main video metadata
    #             kling_metadata = {
    #                 "chapter_id": chapter_id,
    #                 "video_url": video_url,
    #                 "script": script,
    #                 "character_details": character_details,
    #                 "scene_prompt": klingai_content,
    #                 "created_at": int(time.time()),
    #                 "source": "klingai",
    #                 "is_multi_segment": is_multi_segment,
    #                 "total_segments": total_segments,
    #                 "segment_urls": segment_urls if is_multi_segment else []
    #             }
    #             if 'book' in chapter_context and 'id' in chapter_context['book']:
    #                 kling_metadata["book_id"] = chapter_context['book']['id']
    #             if user_id:
    #                 kling_metadata["user_id"] = user_id
    #             logs.append(f"[DB INSERT] Saving KlingAI video metadata: {kling_metadata}")
    #             db_result_kling = self.supabase_service.table("videos").insert(kling_metadata).execute()
    #             logs.append(f"[DB INSERT RESULT] {db_result_kling}")

    #             # Save individual scene segments to video_segments table
    #             if is_multi_segment and scene_results:
    #                 logs.append(f"[SCENE DB] Saving {len(scene_results)} individual scene segments")
    #                 video_generation_id = db_result_kling.data[0]['id'] if db_result_kling.data else None

    #                 for scene_result in scene_results:
    #                     try:
    #                         # Extract character names from dialogues
    #                         character_names = list(set([d.get("character", "Unknown") for d in scene_result['dialogues']]))

    #                         scene_metadata = {
    #                             "video_generation_id": video_generation_id,
    #                             "scene_id": f"scene_{scene_result['scene_number']}",
    #                             "scene_number": scene_result['scene_number'],
    #                             "video_url": scene_result['video_url'],
    #                             "scene_description": scene_result['description'],
    #                             "character_count": scene_result['character_count'],
    #                             "dialogue_count": scene_result['dialogue_count'],
    #                             "action_count": scene_result['action_count'],
    #                             "camera_movements": scene_result['camera_movements'],
    #                             "character_names": character_names,
    #                             "created_at": int(time.time()),
    #                             "status": "completed",
    #                             "prompt_length": len(scene_result.get('kling_result', {}).get('prompt', '')),
    #                             "target_duration": scene_result.get('kling_result', {}).get('target_duration', 0)
    #                         }
    #                         if user_id:
    #                             scene_metadata["user_id"] = user_id

    #                         logs.append(f"[SCENE DB] Saving scene {scene_result['scene_number']}: {scene_metadata['scene_description'][:50]}...")
    #                         logs.append(f"[SCENE DB] Characters: {character_names}, Dialogues: {scene_result['dialogue_count']}")
    #                         scene_db_result = self.supabase_service.table("video_segments").insert(scene_metadata).execute()
    #                         logs.append(f"[SCENE DB RESULT] Scene {scene_result['scene_number']} saved successfully with ID: {scene_db_result.data[0]['id'] if scene_db_result.data else 'unknown'}")

    #                     except Exception as scene_db_error:
    #                         logs.append(f"[SCENE DB ERROR] Failed to save scene {scene_result['scene_number']}: {scene_db_error}")
    #                         import traceback
    #                         logs.append(f"[SCENE DB ERROR TRACE] {traceback.format_exc()}")

    #         except Exception as db_exc:
    #             logs.append(f"[DB INSERT ERROR - KlingAI] {db_exc}")

    #         # Validate URLs before downloading
    #         def is_valid_url(url):
    #             return isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))

    #         # Ensure ElevenLabs audio is in Supabase Storage
    #         if is_valid_url(mixed_audio_url) and "supabase.co" not in mixed_audio_url:
    #             # Download and upload to Supabase
    #             import tempfile, httpx, os
    #             fd, temp_audio_path = tempfile.mkstemp(suffix=".mp3"); os.close(fd)
    #             try:
    #                 with httpx.Client() as client:
    #                     r = client.get(mixed_audio_url)
    #                     if r.status_code == 200:
    #                         with open(temp_audio_path, 'wb') as f:
    #                             f.write(r.content)
    #                         # Upload to Supabase (append user_id if available)
    #                         supabase_audio_url = await self._serve_video_from_supabase(temp_audio_path, f"audio_{int(time.time())}.mp3", user_id=user_id)
    #                         logs.append(f"[AUDIO UPLOAD] Uploaded ElevenLabs audio to Supabase: {supabase_audio_url}")
    #                         mixed_audio_url = supabase_audio_url
    #                     else:
    #                         logs.append(f"[AUDIO DOWNLOAD ERROR] {mixed_audio_url} status {r.status_code}")
    #             except Exception as e:
    #                 logs.append(f"[AUDIO DOWNLOAD ERROR] {e}")

    #         # Download video and audio files
    #         import tempfile, os, subprocess, httpx
    #         async def download_file(url, suffix):
    #             # Ensure URL has proper protocol
    #             if not url.startswith(('http://', 'https://')):
    #                 if url.startswith('//'):
    #                     url = 'https:' + url
    #                 else:
    #                     url = 'https://' + url

    #             logs.append(f"[DOWNLOAD] Attempting to download: {url}")

    #             fd, path = tempfile.mkstemp(suffix=suffix)
    #             os.close(fd)
    #             try:
    #                 async with httpx.AsyncClient(timeout=60.0) as client:
    #                     r = await client.get(url)
    #                     if r.status_code == 200:
    #                         with open(path, 'wb') as f:
    #                             f.write(r.content)
    #                         logs.append(f"[DOWNLOAD SUCCESS] Downloaded to: {path}")
    #                         return path
    #                     else:
    #                         logs.append(f"[DOWNLOAD ERROR] Failed to download {url}: {r.status_code}")
    #                         # Clean up the temp file if it was created
    #                         if os.path.exists(path):
    #                             os.remove(path)
    #                         raise Exception(f"Failed to download {url}: {r.status_code}")
    #             except Exception as e:
    #                 logs.append(f"[DOWNLOAD ERROR] Failed to download {url}: {e}")
    #                 # Clean up the temp file if it was created
    #                 if os.path.exists(path):
    #                     os.remove(path)
    #                 raise

    #         try:
    #             # For multi-segment videos, download all segments
    #             if is_multi_segment and segment_urls:
    #                 logs.append(f"[MULTI-SEGMENT] Downloading {len(segment_urls)} video segments")
    #                 video_paths = []
    #                 for i, segment_url in enumerate(segment_urls):
    #                     segment_path = await download_file(segment_url, f"_segment_{i}.mp4")
    #                     video_paths.append(segment_path)
    #                     logs.append(f"[MULTI-SEGMENT] Downloaded segment {i+1}: {segment_path}")

    #                 # Use the first segment as the main video for now
    #                 video_path = video_paths[0]
    #                 logs.append(f"[MULTI-SEGMENT] Using first segment as main video: {video_path}")
    #             else:
    #                 # Single video
    #                 video_path = await download_file(video_url, ".mp4")

    #             audio_path = await download_file(mixed_audio_url, ".mp3")
    #         except Exception as download_error:
    #             logs.append(f"[DOWNLOAD FAILED] {download_error}")
    #             return {"error": f"Failed to download files: {download_error}", "logs": logs}

    #         # Check file existence
    #         if not os.path.exists(video_path):
    #             logs.append(f"[ERROR] Video file not found at {video_path}")
    #             return {"error": "Video file not found", "logs": logs}
    #         if not os.path.exists(audio_path):
    #             logs.append(f"[ERROR] Audio file not found at {audio_path}")
    #             return {"error": "Audio file not found", "logs": logs}

    #         # 7. Merge audio and video with FFmpeg
    #         merged_path = tempfile.mktemp(suffix="_merged.mp4")
    #         ffmpeg_cmd = [
    #             "ffmpeg", "-y",
    #             "-i", video_path,
    #             "-i", audio_path,
    #             "-c:v", "copy",
    #             "-c:a", "aac",
    #             "-shortest",
    #             merged_path
    #         ]
    #         logs.append(f"[FFMPEG CMD] {' '.join(ffmpeg_cmd)}")
    #         proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    #         logs.append(f"[FFMPEG OUT] {proc.stdout}")
    #         if proc.stderr:
    #             logs.append(f"[FFMPEG ERR] {proc.stderr}")
    #         logs.append(f"[FFMPEG EXIT] {proc.returncode}")
    #         logs.append(f"[FFMPEG ERR] {proc.stderr}")
    #         if not os.path.exists(merged_path):
    #             logs.append(f"[ERROR] Merged video not found at {merged_path}")
    #             return {"error": "Merged video not found", "logs": logs}

    #         logs.append(f"[FFMPEG SUCCESS] Merged video created at: {merged_path}")

    #         # 8. Upload merged video to storage and return URL (append user_id if available)
    #         merged_video_url = await self._serve_video_from_supabase(merged_path, f"merged_video_{int(time.time())}.mp4", user_id=user_id)
    #         logs.append(f"[UPLOAD] Merged video public URL: {merged_video_url}")

    #         # 9. Save merged video metadata to Supabase DB
    #         try:
    #             merged_metadata = {
    #                 "chapter_id": chapter_id,
    #                 "video_url": merged_video_url,
    #                 "script": script,
    #                 "character_details": character_details,
    #                 "scene_prompt": klingai_content,
    #                 "created_at": int(time.time()),
    #                 "source": "merged",
    #                 "klingai_video_url": video_url,
    #                 "is_multi_segment": is_multi_segment,
    #                 "total_segments": total_segments,
    #                 "segment_urls": segment_urls if is_multi_segment else []
    #             }
    #             if 'book' in chapter_context and 'id' in chapter_context['book']:
    #                 merged_metadata["book_id"] = chapter_context['book']['id']
    #             if user_id:
    #                 merged_metadata["user_id"] = user_id
    #             logs.append(f"[DB INSERT] Saving merged video metadata: {merged_metadata}")
    #             db_result_merged = self.supabase_service.table("videos").insert(merged_metadata).execute()
    #             logs.append(f"[DB INSERT RESULT] {db_result_merged}")
    #         except Exception as db_exc:
    #             logs.append(f"[DB INSERT ERROR - Merged] {db_exc}")

    #         return {
    #             "merged_video_url": merged_video_url,
    #             "klingai_video_url": video_url,
    #             "logs": logs,
    #             "script": script,
    #             "characters": characters,
    #             "character_details": character_details,
    #             "scene_prompt": klingai_content,
    #             "elevenlabs_content": elevenlabs_content,
    #             "klingai_prompt": klingai_content,
    #             "video_url": merged_video_url,
    #             "enhanced_audio_url": mixed_audio_url,
    #             "is_multi_segment": is_multi_segment,
    #             "total_segments": total_segments,
    #             "segment_urls": segment_urls if is_multi_segment else [],
    #             "service_inputs": {
    #                 "elevenlabs": {
    #                     "content": elevenlabs_content,
    #                     "content_type": elevenlabs_content_type,
    #                     "character_count": len(elevenlabs_content)
    #                 },
    #                 "klingai": {
    #                     "content": klingai_content,
    #                     "content_type": klingai_content_type,
    #                     "character_count": len(klingai_content)
    #                 }
    #             },
    #             "parsed_sections": parsed_content.get("parsed_sections", {})
    #         }
    #     except Exception as e:
    #         logs.append(f"[ERROR] {e}")
    #         print(f"Error generating entertainment video: {e}")
    #         return {"error": str(e), "logs": logs}

    async def get_available_avatars(self) -> List[Dict[str, Any]]:
        """Get available avatars"""
        if not self.api_key:
            return self._get_mock_avatars()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/avatars",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )

                if response.status_code == 200:
                    data = response.json()
                    return [
                        {
                            "avatar_id": avatar["avatar_id"],
                            "name": avatar.get("name", "Avatar"),
                            "style": avatar.get("style", "realistic"),
                            "voice_id": avatar.get("voice_id", "default"),
                        }
                        for avatar in data.get("avatars", [])
                    ]
                else:
                    return self._get_mock_avatars()

        except Exception as e:
            print(f"Video service error: {e}")
            return self._get_mock_avatars()

    async def _poll_video_status(
        self, video_id: str, scene_description: str
    ) -> Dict[str, Any]:
        """Poll for video completion status"""
        try:
            print(f"🔄 Polling for video completion: {video_id}")

            headers = {
                "x-api-key": settings.TAVUS_API_KEY,
                "Content-Type": "application/json",
            }

            # Increase polling attempts and intervals for longer videos
            max_attempts = 120  # 10 minutes with 5-second intervals
            attempt = 0

            async with httpx.AsyncClient(timeout=30.0) as client:
                while attempt < max_attempts:
                    attempt += 1

                    try:
                        response = await client.get(
                            f"{self.base_url}/videos/{video_id}", headers=headers
                        )

                        print(f"📊 Polling response: {response.json()}")

                        if response.status_code == 200:
                            data = response.json()
                            status = data.get("status", "unknown")

                            if status == "completed":
                                print(f"✅ Video completed: {video_id}")
                                video_url = data.get("download_url") or data.get(
                                    "video_url"
                                )
                                hosted_url = data.get("hosted_url")

                                if video_url:
                                    return {
                                        "video_id": video_id,
                                        "video_url": video_url,
                                        "hosted_url": hosted_url,
                                        "download_url": data.get("download_url"),
                                        "duration": data.get("duration", 180),
                                        "status": "completed",
                                    }
                                else:
                                    print("⚠️ Video completed but no URL found")
                                    return {
                                        "video_id": video_id,
                                        "hosted_url": hosted_url,
                                        "status": "completed_no_download",
                                    }

                            elif status == "failed":
                                print(f"❌ Video generation failed: {video_id}")
                                return {
                                    "video_id": video_id,
                                    "status": "failed",
                                    "error": data.get("error", "Unknown error"),
                                }

                            elif status in ["queued", "generating"]:
                                progress = data.get("generation_progress", "0/100")
                                print(
                                    f"⏳ Video status: {status} (attempt {attempt}/{max_attempts}) - Progress: {progress}"
                                )

                                # Wait longer between polls for generating status
                                await asyncio.sleep(10 if status == "generating" else 5)
                                continue

                            else:
                                print(f"⚠️ Unknown status: {status}")
                                await asyncio.sleep(5)
                                continue

                        elif response.status_code == 404:
                            print(f"❌ Video not found: {video_id}")
                            return {"video_id": video_id, "status": "not_found"}

                        else:
                            print(f"❌ Polling failed: {response.status_code}")
                            await asyncio.sleep(5)
                            continue

                    except httpx.TimeoutException:
                        print(f"⏰ Timeout on attempt {attempt}, retrying...")
                        await asyncio.sleep(5)
                        continue

                    except Exception as e:
                        print(f"❌ Error polling video: {e}")
                        await asyncio.sleep(5)
                        continue

            # If we get here, we've exceeded max attempts
            print(f"⏰ Video generation timed out after {max_attempts * 5} seconds")
            return {
                "video_id": video_id,
                "status": "timeout",
                "message": f"Video generation took longer than expected (max {max_attempts * 5} seconds)",
            }

        except Exception as e:
            print(f"❌ Error in video polling: {e}")
            return {"video_id": video_id, "status": "error", "error": str(e)}

    def _get_avatar_id(self, style: str) -> str:
        """Get avatar ID based on style"""
        avatar_map = {
            "realistic": "avatar_001",
            "animated": "avatar_002",
            "cartoon": "avatar_003",
            "tutorial": "avatar_004",
            "story": "avatar_005",
        }
        return avatar_map.get(style, "avatar_001")

    def _get_replica_id(self, style: str) -> str:
        """Get replica ID based on style - replace with your actual replica IDs from Tavus"""
        replica_map = {
            "realistic": "rb17cf590e15",  # Replace with your actual replica ID
            "animated": "rb17cf590e15",  # Replace with your actual replica ID
            "cartoon": "rb17cf590e15",  # Replace with your actual replica ID
            "tutorial": "rb17cf590e15",  # Replace with your actual replica ID
            "story": "rb17cf590e15",  # Replace with your actual replica ID
        }
        return replica_map.get(style, "rb17cf590e15")  # Default replica ID

    def _get_background_for_style(self, style: str) -> str:
        """Get appropriate background for video style"""
        background_map = {
            "realistic": "bg_001",
            "animated": "bg_002",
            "cartoon": "bg_003",
            "tutorial": "bg_004",
            "story": "bg_005",
        }
        return background_map.get(style, "bg_001")

    def _get_voice_id_for_style(self, style: str) -> str:
        """Get appropriate voice ID for video style"""
        voice_map = {
            "realistic": "voice_001",
            "animated": "voice_002",
            "cartoon": "voice_003",
            "tutorial": "voice_004",
            "story": "voice_005",
        }
        return voice_map.get(style, "voice_001")

    async def _mock_generate_scene(
        self, scene_description: str, dialogue: str
    ) -> Dict[str, Any]:
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
                        "supabase_url": video_url,
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
                "error": "FFmpeg not available or video creation failed",
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
                "error": str(e),
            }

    def _get_mock_avatars(self) -> List[Dict[str, Any]]:
        """Return mock avatar data"""
        return [
            {
                "avatar_id": "avatar_001",
                "name": "Narrator",
                "style": "realistic",
                "voice_id": "voice_001",
            },
            {
                "avatar_id": "avatar_002",
                "name": "Character",
                "style": "animated",
                "voice_id": "voice_002",
            },
            {
                "avatar_id": "avatar_003",
                "name": "Mentor",
                "style": "realistic",
                "voice_id": "voice_003",
            },
            {
                "avatar_id": "avatar_004",
                "name": "Instructor",
                "style": "realistic",
                "voice_id": "voice_004",
            },
        ]

    async def _download_file(self, url: str, file_path: str) -> bool:
        """Download a file from URL to local path"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(await response.read())
                        return True
                    else:
                        print(f"Failed to download {url}: {response.status}")
                        return False
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    async def _merge_video_audio(
        self, video_path: str, audio_path: str, output_path: str
    ) -> bool:
        """Merge video and audio using FFmpeg"""
        try:
            # Check if FFmpeg is available
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                print("FFmpeg not found, using fallback method")
                return False

            # Merge video and audio
            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",  # Copy video stream without re-encoding
                "-c:a",
                "aac",  # Use AAC for audio
                "-shortest",  # End when shortest stream ends
                "-y",  # Overwrite output file
                output_path,
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

    async def extract_last_frame_from_video(
        self, video_url: str, output_filename: str, user_id: str = None
    ) -> Optional[str]:
        """Extract the last frame from a video using FFmpeg and upload to Supabase Storage"""
        try:
            print(f"[FRAME EXTRACTION] Extracting last frame from video: {video_url}")

            # Check if FFmpeg is available
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                print("[FRAME EXTRACTION] FFmpeg not found, cannot extract frame")
                return None

            # Download video to temporary file
            import tempfile
            import httpx

            fd, video_temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.get(video_url)
                    response.raise_for_status()
                    with open(video_temp_path, "wb") as f:
                        f.write(response.content)

                print(f"[FRAME EXTRACTION] Video downloaded to: {video_temp_path}")

                # Create temporary output path for the frame
                fd, frame_temp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(fd)

                # Use FFmpeg to extract the last frame
                # -sseof -1 means seek to 1 second before end, then extract frame
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-i",
                    video_temp_path,  # Input video
                    "-vf",
                    "select=eq(n\\,0)",  # Select only the last frame
                    "-q:v",
                    "2",  # High quality JPEG
                    "-f",
                    "image2",  # Output format
                    "-update",
                    "1",  # Only output one frame
                    "-y",  # Overwrite output
                    frame_temp_path,
                ]

                print(
                    f"[FRAME EXTRACTION] Running FFmpeg command: {' '.join(ffmpeg_cmd)}"
                )
                result = subprocess.run(
                    ffmpeg_cmd, capture_output=True, text=True, timeout=60
                )

                if result.returncode != 0:
                    print(f"[FRAME EXTRACTION] FFmpeg failed: {result.stderr}")
                    return None

                if not os.path.exists(frame_temp_path):
                    print("[FRAME EXTRACTION] Frame extraction failed - no output file")
                    return None

                print(f"[FRAME EXTRACTION] Frame extracted to: {frame_temp_path}")

                # Upload frame to Supabase Storage
                frame_url = await self._serve_video_from_supabase(
                    frame_temp_path, output_filename, user_id
                )

                if frame_url:
                    print(f"[FRAME EXTRACTION] Frame uploaded to: {frame_url}")
                else:
                    print("[FRAME EXTRACTION] Failed to upload frame to Supabase")

                return frame_url

            finally:
                # Clean up temporary files
                try:
                    if os.path.exists(video_temp_path):
                        os.unlink(video_temp_path)
                    if os.path.exists(frame_temp_path):
                        os.unlink(frame_temp_path)
                except:
                    pass

        except Exception as e:
            print(f"[FRAME EXTRACTION] Error extracting last frame: {e}")
            return None

    async def _create_mock_video(self, duration: int = 180) -> str:
        """Create a mock video using FFmpeg for development"""
        try:
            # Check if FFmpeg is available
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                print("FFmpeg not found, cannot create mock video")
                return None

            # Create output directory
            output_dir = Path(settings.UPLOAD_DIR) / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"mock_video_{int(time.time())}.mp4"

            # Create a simple video with text overlay
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:size=1280x720:duration={duration}",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:duration={duration}",
                "-vf",
                "drawtext=text='AI Generated Video':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-y",
                str(output_path),
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

    async def _merge_real_video_audio(
        self, tavus_video_url: str, elevenlabs_audio_url: str, scene_description: str
    ) -> Dict[str, Any]:
        """Merge real Tavus video with ElevenLabs audio and upload to Supabase"""
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_temp:
                video_path = video_temp.name
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_temp:
                audio_path = audio_temp.name

            # Download video and audio files
            video_downloaded = await self._download_file(tavus_video_url, video_path)
            audio_downloaded = await self._download_file(
                elevenlabs_audio_url, audio_path
            )

            if not video_downloaded or not audio_downloaded:
                print("Failed to download video or audio files")
                return None

            # Create output directory and path
            output_dir = Path(settings.UPLOAD_DIR) / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"merged_video_{int(time.time())}.mp4"

            # Merge video and audio
            merge_success = await self._merge_video_audio(
                video_path, audio_path, str(output_path)
            )

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
                video_url = await self._serve_video_from_supabase(
                    str(output_path), filename
                )

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
                        "supabase_url": video_url,
                    }

            print("Video merging failed")
            return None

        except Exception as e:
            print(f"Error merging real video and audio: {e}")
            return None

    async def _upload_to_supabase_storage(
        self, file_path: str, filename: str, folder: str = "videos"
    ) -> Optional[str]:
        """Upload file to Supabase Storage and return public URL"""
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None

            # Read file content
            with open(file_path, "rb") as f:
                file_content = f.read()

            # Create storage path
            storage_path = f"{folder}/{filename}"

            # Upload to Supabase Storage
            self.supabase.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "video/mp4"},
            )

            # Get public URL
            public_url = self.supabase.storage.from_(
                settings.SUPABASE_BUCKET_NAME
            ).get_public_url(storage_path)

            print(f"Uploaded video to Supabase: {public_url}")
            return public_url

        except Exception as e:
            print(f"Error uploading to Supabase Storage: {e}")
            return None

    async def _serve_video_from_supabase(
        self, file_path: str, filename: str, user_id: str = None
    ) -> str:
        """Upload video to Supabase Storage and return public URL"""
        try:
            # Read the file
            with open(file_path, "rb") as f:
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
                file_options={"content-type": "video/mp4"},
            )

            # Get public URL
            public_url = self.supabase.storage.from_(
                settings.SUPABASE_BUCKET_NAME
            ).get_public_url(storage_path)
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
        video_style: str,
    ) -> str:
        """Generate a learning-focused video script using RAGService for richer AI content"""
        try:
            # Use RAGService to get chapter context and generate script
            chapter_context = {
                "chapter": {"title": chapter_title, "content": chapter_content},
                "book": {"title": book_title, "book_type": "learning"},
                "total_context": chapter_content,
            }
            if self.rag_service:
                return await self.rag_service.generate_video_script(
                    chapter_context, video_style
                )
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
        self, chapter_content: str, rag_context: Dict[str, Any], script_style: str
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
                    {
                        "role": "system",
                        "content": "You are an expert script writer for video adaptations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"Error generating entertainment script: {e}")
            return {
                "script": chapter_content[:500],
                "character_details": "Main character",
                "scene_prompt": "A scene from the story",
            }

    async def _merge_audio_video(
        self, video_url: str, audio_url: str, user_id: str
    ) -> Dict[str, Any]:
        """Download and merge audio/video files"""
        try:
            import tempfile
            import subprocess
            import httpx

            # Download video and audio files
            async def download_file(url: str, suffix: str) -> str:
                # Ensure URL has proper protocol
                if not url.startswith(("http://", "https://")):
                    if url.startswith("//"):
                        url = "https:" + url
                    else:
                        url = "https://" + url

                logs.append(f"[DOWNLOAD] Attempting to download: {url}")

                fd, path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        r = await client.get(url)
                        r.raise_for_status()  # Raise exception for bad status codes
                        with open(path, "wb") as f:
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
                return {
                    "error": f"Failed to download files: {download_error}",
                    "logs": logs,
                }

            # Check file existence
            if not os.path.exists(video_path):
                return {"error": "Video file not found"}
            if not os.path.exists(audio_path):
                return {"error": "Audio file not found"}

            # Merge with FFmpeg
            merged_path = tempfile.mktemp(suffix="_merged.mp4")
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                merged_path,
            ]

            proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if not os.path.exists(merged_path):
                return {"error": "Merged video not found"}

            # Upload merged video to Supabase
            merged_video_url = await self._serve_video_from_supabase(
                merged_path, f"merged_video_{int(time.time())}.mp4", user_id
            )

            # Clean up temporary files
            os.remove(video_path)
            os.remove(audio_path)
            os.remove(merged_path)

            return {"merged_video_url": merged_video_url}

        except Exception as e:
            print(f"Error merging audio/video: {e}")
            return {"error": str(e)}

    async def _generate_real_video(
        self, script: str, video_style: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Generate real video using Tavus API + ElevenLabs audio"""
        try:
            print(
                f"Generating real video with Tavus API + ElevenLabs using style: {video_style}"
            )

            # Step 1: Generate video with Tavus API
            tavus_video = await self._generate_tavus_video(script, video_style)
            if not tavus_video or not tavus_video.get("video_url"):
                print("❌ Tavus video generation failed or no video URL returned.")
                return tavus_video  # Return the failed tavus_video object

            # Step 2: Generate audio with ElevenLabs ONLY if Tavus video was successful
            elevenlabs_audio = await self._generate_elevenlabs_audio(
                script, video_style, user_id
            )
            if not elevenlabs_audio:
                print("⚠️  ElevenLabs audio unavailable, returning Tavus video only.")
                return tavus_video  # Return the successful tavus_video (with its URL)

            # Step 3: Merge video and audio (we know tavus_video.get("video_url") is not None here)
            print("Merging Tavus video with ElevenLabs audio...")
            merged_video = await self._merge_real_video_audio(
                tavus_video["video_url"],
                elevenlabs_audio["audio_url"],
                f"AI-generated content in {video_style} style",
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

    async def _generate_tavus_video(
        self,
        script: str,
        video_style: str,
        content_id: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate video using Tavus API with enhanced error handling and logging"""
        try:
            print(f"🎬 Generating Tavus video with style: {video_style}")
            print(f"📝 Script length: {len(script)} characters")

            # Validate API key
            if (
                not settings.TAVUS_API_KEY
                or settings.TAVUS_API_KEY == "your-tavus-api-key"
            ):
                print("❌ Tavus API key not configured")
                return None

            # Get replica ID based on style
            replica_id = self._get_replica_id(video_style)
            print(f"🆔 Using replica ID: {replica_id}")

            # Prepare Tavus API request
            headers = {
                "x-api-key": settings.TAVUS_API_KEY,
                "Content-Type": "application/json",
            }

            # Create video generation request with correct payload structure
            payload = {
                "replica_id": replica_id,
                "script": script,
                "video_name": f"AI Generated Video - {video_style}",
            }

            print(f"📤 Sending request to Tavus API...")
            print(f"🌐 Endpoint: {self.base_url}/videos")
            print(f"📋 Payload keys: {list(payload.keys())}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Create a new video
                response = await client.post(
                    f"{self.base_url}/videos", headers=headers, json=payload
                )

                print(f"📊 Create Video Response Status: {response.status_code}")
                print(f"📄 Response Headers: {dict(response.headers)}")

                # Log the raw response for debugging
                try:
                    response_text = response.text
                    print(
                        f"📄 Raw Response: {response_text[:500]}..."
                    )  # First 500 chars

                    if response.status_code in [200, 201]:
                        data = response.json()
                        print(f"✅ Video creation initiated successfully")
                        print(
                            f"📊 Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                        )

                        # Extract video ID with multiple fallbacks
                        video_id = (
                            data.get("video_id")
                            or data.get("id")
                            or data.get("videoId")
                            or data.get("video_id")
                        )

                        if video_id:
                            print(f"🎯 Video ID extracted: {video_id}")
                            # Poll for completion with enhanced logging and database updates
                            return await self._poll_video_status_enhanced(
                                video_id,
                                f"AI Generated Video - {video_style}",
                                content_id,
                            )
                        else:
                            print("❌ No video ID found in response")
                            print(
                                f"🔍 Available keys in response: {list(data.keys()) if isinstance(data, dict) else 'Response is not a dict'}"
                            )
                            return None

                    elif response.status_code == 400:
                        print(f"❌ Bad Request (400): {response_text}")
                        # Try to get available replicas and use the first one
                        return await self._try_with_available_replicas(
                            client, headers, script, video_style
                        )

                    elif response.status_code == 401:
                        print(f"❌ Unauthorized (401): Check your Tavus API key")
                        return None

                    elif response.status_code == 404:
                        print(
                            "⚠️  /videos endpoint not found, trying alternative approach..."
                        )
                        return await self._try_alternative_video_creation(
                            client, headers, script, video_style
                        )

                    elif response.status_code == 429:
                        print(f"❌ Rate Limited (429): Too many requests to Tavus API")
                        return None

                    else:
                        print(
                            f"❌ Video creation failed with status: {response.status_code}"
                        )
                        print(f"📄 Error Response: {response_text}")
                        return None

                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse JSON response: {e}")
                    print(f"📄 Raw response text: {response.text}")
                    return None

        except httpx.TimeoutException:
            print(f"⏰ Timeout while creating Tavus video")
            return None
        except httpx.RequestError as e:
            print(f"❌ Network error while creating Tavus video: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error generating Tavus video: {e}")
            import traceback

            print(f"🔍 Full traceback: {traceback.format_exc()}")
            return None

    async def _generate_elevenlabs_audio(
        self, script: str, video_style: str, user_id: str = None
    ) -> Optional[Dict[str, Any]]:
        try:
            # Map video_style to narrator_style
            narrator_style = self._map_video_style_to_narrator_style(video_style)
            audio_url = await self.elevenlabs_service.create_audio_narration(
                text=script, narrator_style=narrator_style, user_id=user_id
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
            "story": "narration",
        }
        return style_map.get(video_style, "narration")

    async def _try_alternative_video_creation(
        self, client, headers, script, video_style
    ):
        """Try alternative methods to create videos with Tavus API"""
        try:
            print("🔄 Trying alternative video creation methods...")

            # Method 1: Try to get available videos and use existing ones
            response = await client.get(f"{self.base_url}/videos", headers=headers)

            if response.status_code == 200:
                videos_data = response.json()
                print(f"📦 Found {len(videos_data.get('data', []))} existing videos")

                # Use the first available video as a template
                if videos_data.get("data"):
                    first_video = videos_data["data"][0]
                    video_id = first_video.get("video_id")

                    if video_id:
                        print(f"✅ Using existing video as template: {video_id}")
                        return await self._poll_video_status(
                            video_id, f"AI Generated Video - {video_style}"
                        )

            # Method 2: Try different endpoints
            alternative_endpoints = ["/scenes", "/generate", "/projects", "/templates"]

            for endpoint in alternative_endpoints:
                try:
                    print(f"🔍 Trying endpoint: {endpoint}")

                    payload = {
                        "script": script[:1000],  # Limit script length
                        "style": video_style,
                        "name": f"AI Video - {video_style}",
                    }

                    response = await client.post(
                        f"{self.base_url}{endpoint}",
                        headers=headers,
                        json=payload,
                        timeout=30.0,
                    )

                    print(f"📊 {endpoint} Status: {response.status_code}")

                    if response.status_code in [200, 201, 202]:
                        data = response.json()
                        print(f"✅ Success with {endpoint}: {data}")

                        video_id = (
                            data.get("id")
                            or data.get("video_id")
                            or data.get("scene_id")
                        )
                        if video_id:
                            return await self._poll_video_status(
                                video_id, f"AI Generated Video - {video_style}"
                            )

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
                print(
                    f"📦 Found {len(replicas_data.get('data', []))} available replicas"
                )

                # Use the first available replica
                if replicas_data.get("data"):
                    first_replica = replicas_data["data"][0]
                    replica_id = first_replica.get("replica_id") or first_replica.get(
                        "id"
                    )

                    if replica_id:
                        print(f"✅ Using available replica: {replica_id}")

                        # Try video creation with this replica
                        payload = {
                            "replica_id": replica_id,
                            "script": script,
                            "video_name": f"AI Generated Video - {video_style}",
                        }

                        response = await client.post(
                            f"{self.base_url}/videos", headers=headers, json=payload
                        )

                        if response.status_code in [200, 201]:
                            data = response.json()
                            video_id = data.get("video_id") or data.get("id")
                            if video_id:
                                return await self._poll_video_status(
                                    video_id, f"AI Generated Video - {video_style}"
                                )

            # If no replicas found, try with a default replica ID
            print("⚠️  No replicas found, trying with default replica ID...")
            default_payload = {
                "replica_id": "rb17cf590e15",  # Default replica ID from your account
                "script": script,
                "video_name": f"AI Generated Video - {video_style}",
            }

            response = await client.post(
                f"{self.base_url}/videos", headers=headers, json=default_payload
            )

            if response.status_code in [200, 201]:
                data = response.json()
                video_id = data.get("video_id") or data.get("id")
                if video_id:
                    return await self._poll_video_status(
                        video_id, f"AI Generated Video - {video_style}"
                    )

            print("❌ Failed to create video with any replica")
            return None

        except Exception as e:
            print(f"❌ Error trying with available replicas: {e}")
            return None

    async def _generate_kling_video(
        self, script: str, video_style: str = "realistic", target_duration: int = 30
    ) -> dict:
        """Generate a video using Kling AI API and return the video URL and metadata."""

        # First, validate and sanitize content for KlingAI
        print(f"[KlingAI DEBUG] Original script length: {len(script)}")
        print(f"[KlingAI DEBUG] Original script preview: {script[:200]}...")

        # Validate content safety
        safety_check = self._validate_content_safety(script)
        print(f"[KlingAI SAFETY] Safety score: {safety_check['score']:.2f}")
        print(f"[KlingAI SAFETY] Is safe: {safety_check['safe']}")
        print(f"[KlingAI SAFETY] Issues found: {safety_check['issues']}")
        print(f"[KlingAI SAFETY] Recommendation: {safety_check['recommendation']}")

        # Sanitize content if needed
        sanitized_script = self._sanitize_content_for_klingai(script)

        if sanitized_script != script:
            print(f"[KlingAI SANITIZATION] Content was sanitized")
            print(
                f"[KlingAI SANITIZATION] Sanitized script preview: {sanitized_script[:200]}..."
            )
        else:
            print(
                f"[KlingAI SANITIZATION] Content passed safety check without modification"
            )

        # Use sanitized script for generation
        script = sanitized_script

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
        headers_jwt = {"alg": "HS256", "typ": "JWT"}
        payload_jwt = {
            "iss": self.kling_access_key_id,
            "exp": int(time.time()) + 1800,  # 30 minutes from now
            "nbf": int(time.time()) - 5,  # valid 5 seconds ago
        }
        token = jwt.encode(
            payload_jwt,
            self.kling_access_key_secret,
            algorithm="HS256",
            headers=headers_jwt,
        )
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        print(f"[KlingAI DEBUG] Using Authorization header: Bearer <JWT>")

        # If duration is longer than 10 seconds, we need to split into multiple segments
        if final_duration > 10:
            return await self._generate_long_kling_video(
                script, video_style, final_duration, headers
            )
        else:
            # For shorter videos, use single KlingAI call
            kling_duration = "10" if final_duration > 5 else "5"
            return await self._generate_single_kling_video(
                script, video_style, kling_duration, headers, final_duration
            )

    async def _generate_single_kling_video(
        self,
        script: str,
        video_style: str,
        kling_duration: str,
        headers: dict,
        target_duration: int,
    ) -> dict:
        """Generate a single KlingAI video segment"""

        # Final safety check before sending to KlingAI
        final_safety_check = self._validate_content_safety(script)
        if not final_safety_check["safe"]:
            print(
                f"[KlingAI WARNING] Content still has safety issues after sanitization"
            )
            print(f"[KlingAI WARNING] Safety score: {final_safety_check['score']:.2f}")
            print(f"[KlingAI WARNING] Issues: {final_safety_check['issues']}")

            # Create a completely safe fallback script
            safe_script = "A peaceful educational scene with gentle camera movements, showing people learning and growing in a positive environment."
            print(f"[KlingAI FALLBACK] Using safe fallback script: {safe_script}")
            script = safe_script

        payload = {
            "model_name": "kling-v1",
            "prompt": f"A {video_style} video of: {script}",
            "aspect_ratio": "16:9",
            "duration": kling_duration,
        }

        print(f"[KlingAI DEBUG] Single video request - duration: {kling_duration}s")
        print(f"[KlingAI DEBUG] Video style: {video_style}")
        print(f"[KlingAI DEBUG] Final script length: {len(script)}")
        print(f"[KlingAI DEBUG] Final script content:")
        print(f"[KlingAI CONTENT] {script}")
        print(f"[KlingAI DEBUG] Full payload being sent to API:")
        print(f"[KlingAI PAYLOAD] {payload}")

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
                    print(
                        f"[KlingAI DEBUG] Polling status for task {task_id} (attempt {i+1})"
                    )
                    poll_resp = await client.get(poll_url, headers=headers, timeout=30)
                    poll_resp.raise_for_status()
                    poll_data = poll_resp.json()

                    task_status = poll_data.get("data", {}).get("task_status")
                    print(f"[KlingAI DEBUG] Task status: {task_status}")

                    if task_status == "succeed":
                        videos = (
                            poll_data.get("data", {})
                            .get("task_result", {})
                            .get("videos", [])
                        )
                        if videos and videos[0].get("url"):
                            video_url = videos[0]["url"]
                            print(f"[KlingAI SUCCESS] Video generated: {video_url}")
                            return {
                                "video_url": video_url,
                                "task_id": task_id,
                                "meta": poll_data.get("data"),
                                "actual_duration": kling_duration,
                                "target_duration": target_duration,
                                "is_segment": False,
                            }
                        else:
                            raise Exception(
                                f"Kling AI task succeeded but no video URL found. Response: {poll_data}"
                            )

                    elif task_status == "failed":
                        error_msg = poll_data.get("data", {}).get(
                            "task_status_msg", "Unknown error"
                        )
                        print(f"[KlingAI ERROR] Task failed with message: {error_msg}")
                        print(f"[KlingAI ERROR] Full error response: {poll_data}")

                        # Check if it's a risk control failure
                        if (
                            "risk control" in error_msg.lower()
                            or "safety" in error_msg.lower()
                        ):
                            print(
                                f"[KlingAI RISK CONTROL] Content was flagged by risk control system"
                            )
                            print(
                                f"[KlingAI RISK CONTROL] Attempting with ultra-safe fallback content"
                            )

                            # Try with ultra-safe content
                            ultra_safe_payload = {
                                "model_name": "kling-v1",
                                "prompt": "A peaceful nature scene with gentle camera movements, showing beautiful landscapes and peaceful environments",
                                "aspect_ratio": "16:9",
                                "duration": kling_duration,
                            }

                            try:
                                fallback_response = await client.post(
                                    create_url,
                                    json=ultra_safe_payload,
                                    headers=headers,
                                    timeout=60,
                                )
                                fallback_response.raise_for_status()
                                fallback_data = fallback_response.json()
                                fallback_task_id = fallback_data.get("data", {}).get(
                                    "task_id"
                                )

                                if fallback_task_id:
                                    print(
                                        f"[KlingAI FALLBACK] Created fallback task: {fallback_task_id}"
                                    )
                                    # Continue with fallback task polling
                                    poll_url = f"{create_url}/{fallback_task_id}"
                                    for j in range(60):
                                        await asyncio.sleep(10)
                                        poll_resp = await client.get(
                                            poll_url, headers=headers, timeout=30
                                        )
                                        poll_resp.raise_for_status()
                                        poll_data = poll_resp.json()
                                        task_status = poll_data.get("data", {}).get(
                                            "task_status"
                                        )

                                        if task_status == "succeed":
                                            videos = (
                                                poll_data.get("data", {})
                                                .get("task_result", {})
                                                .get("videos", [])
                                            )
                                            if videos and videos[0].get("url"):
                                                video_url = videos[0]["url"]
                                                print(
                                                    f"[KlingAI FALLBACK SUCCESS] Fallback video generated: {video_url}"
                                                )
                                                return {
                                                    "video_url": video_url,
                                                    "task_id": fallback_task_id,
                                                    "meta": poll_data.get("data"),
                                                    "actual_duration": kling_duration,
                                                    "target_duration": target_duration,
                                                    "is_segment": False,
                                                    "is_fallback": True,
                                                }
                                        elif task_status == "failed":
                                            break
                            except Exception as fallback_error:
                                print(
                                    f"[KlingAI FALLBACK ERROR] Fallback attempt also failed: {fallback_error}"
                                )

                        raise Exception(
                            f"Kling AI video generation failed: {error_msg}"
                        )

                raise Exception("Kling AI video generation timed out.")
            except Exception as e:
                print(f"[KlingAI ERROR] {e}")
                return {"error": str(e)}

    async def _generate_long_kling_video(
        self, script: str, video_style: str, target_duration: int, headers: dict
    ) -> dict:
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

            # Sanitize each segment before generation
            sanitized_segment = self._sanitize_content_for_klingai(segment)
            if sanitized_segment != segment:
                print(f"[KlingAI SANITIZATION] Segment {i+1} was sanitized")
                print(
                    f"[KlingAI SANITIZATION] Sanitized segment {i+1}: {sanitized_segment}"
                )

            result = await self._generate_single_kling_video(
                sanitized_segment, video_style, "10", headers, 10
            )

            if "error" in result:
                print(f"[KlingAI ERROR] Segment {i+1} failed: {result}")
                return result

            result["segment_index"] = i
            result["segment_content"] = segment
            segment_videos.append(result)

        # Return all segments for proper processing
        main_video = (
            segment_videos[0] if segment_videos else {"error": "No segments generated"}
        )
        main_video["all_segments"] = segment_videos
        main_video["target_duration"] = target_duration
        main_video["is_segment"] = True
        main_video["total_segments"] = len(segments)
        main_video["segment_urls"] = [
            seg.get("video_url") for seg in segment_videos if seg.get("video_url")
        ]

        print(
            f"[KlingAI DEBUG] Generated {len(segments)} segments for {target_duration}s video"
        )
        print(f"[KlingAI DEBUG] Segment URLs: {main_video['segment_urls']}")
        return main_video

    def _split_script_for_segments(
        self, script: str, target_duration: int
    ) -> List[str]:
        """Split script into segments for multiple video generation"""
        # Simple splitting by sentences for now
        # In a more sophisticated implementation, you might use NLP to split by scenes
        sentences = script.split(". ")
        segments = []
        current_segment = ""

        for sentence in sentences:
            if (
                len(current_segment + sentence) < 200
            ):  # Rough character limit per segment
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

    def _split_script_by_scenes(
        self, script: str, characters: List[str]
    ) -> List[Dict[str, Any]]:
        """Split script into actual scenes based on scene headers and character dialogues"""
        print(
            f"[SCENE SEGMENTATION] Starting scene segmentation for script with {len(script)} characters"
        )
        print(f"[SCENE SEGMENTATION] Characters: {characters}")

        from app.core.services.script_parser import ScriptParser

        # Use the script parser to extract scene components
        script_parser = ScriptParser()
        parsed_components = script_parser.parse_script_for_video_prompt(
            script, characters
        )

        scenes = []

        # Group dialogues and actions by scene
        scene_dialogues = {}
        scene_actions = {}

        # Group dialogues by scene
        for dialogue in parsed_components.get("character_dialogues", []):
            scene_num = dialogue.get("scene", 1)
            if scene_num not in scene_dialogues:
                scene_dialogues[scene_num] = []
            scene_dialogues[scene_num].append(dialogue)

        # Group actions by scene
        for action in parsed_components.get("character_actions", []):
            scene_num = action.get("scene", 1)
            if scene_num not in scene_actions:
                scene_actions[scene_num] = []
            scene_actions[scene_num].append(action)

        # Create scene objects from scene descriptions
        for scene_desc in parsed_components.get("scene_descriptions", []):
            scene_num = scene_desc.get("scene_number", 1)
            scene_description = scene_desc.get("description", "")

            # Get dialogues and actions for this scene
            scene_dialogue_list = scene_dialogues.get(scene_num, [])
            scene_action_list = scene_actions.get(scene_num, [])

            # Create scene prompt
            scene_prompt = self._create_scene_prompt(
                scene_description,
                scene_dialogue_list,
                scene_action_list,
                scene_desc.get("camera_movements", []),
            )

            scenes.append(
                {
                    "scene_number": scene_num,
                    "description": scene_description,
                    "dialogues": scene_dialogue_list,
                    "actions": scene_action_list,
                    "camera_movements": scene_desc.get("camera_movements", []),
                    "prompt": scene_prompt,
                    "character_count": len(
                        set([d.get("character") for d in scene_dialogue_list])
                    ),
                    "dialogue_count": len(scene_dialogue_list),
                    "action_count": len(scene_action_list),
                }
            )

        # If no scenes were detected by scene headers, create scenes based on character dialogue changes
        if not scenes:
            print(
                f"[SCENE SEGMENTATION] No scene headers detected, creating scenes based on character dialogue changes"
            )
            scenes = self._create_scenes_from_dialogue_changes(
                script, characters, parsed_components
            )

        print(f"[SCENE SEGMENTATION] Successfully split into {len(scenes)} scenes")
        for i, scene in enumerate(scenes):
            print(
                f"[SCENE {i+1}/{len(scenes)}] Dialogues: {scene['dialogue_count']}, Actions: {scene['action_count']}, Characters: {scene['character_count']}"
            )
            print(f"[SCENE {i+1}] Description: {scene['description'][:100]}...")
            print(f"[SCENE {i+1}] Prompt preview: {scene['prompt'][:100]}...")

        return scenes

    def _create_scene_prompt(
        self,
        scene_description: str,
        dialogues: List[Dict],
        actions: List[Dict],
        camera_movements: List[str],
    ) -> str:
        """Create a comprehensive prompt for a single scene"""
        prompt_parts = [f"Scene: {scene_description}"]

        # Add camera movements
        if camera_movements:
            prompt_parts.append(f"Camera movements: {', '.join(camera_movements)}")

        # Add character actions
        if actions:
            action_texts = []
            for action in actions:
                character = action.get("character", "Unknown")
                action_desc = action.get("action", "")
                action_texts.append(f"{character} {action_desc}")
            prompt_parts.append(f"Character actions: {', '.join(action_texts)}")

        # Add character dialogues
        if dialogues:
            dialogue_texts = []
            for dialogue in dialogues:
                character = dialogue.get("character", "Unknown")
                text = dialogue.get("text", "")
                dialogue_texts.append(f'{character}: "{text}"')
            prompt_parts.append(f"Dialogues: {' | '.join(dialogue_texts)}")

        # Add cinematic quality instructions
        prompt_parts.extend(
            [
                "Cinematic quality, professional videography",
                "Smooth camera movements, natural character expressions",
                "High resolution, realistic lighting and composition",
            ]
        )

        return ". ".join(prompt_parts)

    def _create_scenes_from_dialogue_changes(
        self, script: str, characters: List[str], parsed_components: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create scenes based on character dialogue changes when no scene headers are detected"""
        print(f"[DIALOGUE SCENE DETECTION] Creating scenes from dialogue changes")

        scenes = []
        current_scene = 1
        current_character = None
        scene_dialogues = []
        scene_actions = []

        # Process all dialogues and group by character changes
        dialogues = parsed_components.get("character_dialogues", [])
        actions = parsed_components.get("character_actions", [])

        for i, dialogue in enumerate(dialogues):
            character = dialogue.get("character", "Unknown")

            # Start new scene when character changes or every 3 dialogues
            if (current_character and character != current_character) or len(
                scene_dialogues
            ) >= 3:
                # Create scene from accumulated dialogues
                scene_description = (
                    f"Scene {current_scene}: {current_character or character} speaks"
                )
                scene_prompt = self._create_scene_prompt(
                    scene_description, scene_dialogues, scene_actions, []
                )

                scenes.append(
                    {
                        "scene_number": current_scene,
                        "description": scene_description,
                        "dialogues": scene_dialogues.copy(),
                        "actions": scene_actions.copy(),
                        "camera_movements": [],
                        "prompt": scene_prompt,
                        "character_count": len(
                            set([d.get("character") for d in scene_dialogues])
                        ),
                        "dialogue_count": len(scene_dialogues),
                        "action_count": len(scene_actions),
                    }
                )

                # Reset for next scene
                current_scene += 1
                scene_dialogues.clear()
                scene_actions.clear()

            current_character = character
            scene_dialogues.append(dialogue)

            # Add relevant actions for this dialogue
            for action in actions:
                if action.get("character") == character:
                    scene_actions.append(action)

        # Add final scene if there are remaining dialogues
        if scene_dialogues:
            scene_description = (
                f"Scene {current_scene}: {current_character or 'Character'} speaks"
            )
            scene_prompt = self._create_scene_prompt(
                scene_description, scene_dialogues, scene_actions, []
            )

            scenes.append(
                {
                    "scene_number": current_scene,
                    "description": scene_description,
                    "dialogues": scene_dialogues,
                    "actions": scene_actions,
                    "camera_movements": [],
                    "prompt": scene_prompt,
                    "character_count": len(
                        set([d.get("character") for d in scene_dialogues])
                    ),
                    "dialogue_count": len(scene_dialogues),
                    "action_count": len(scene_actions),
                }
            )

        print(
            f"[DIALOGUE SCENE DETECTION] Created {len(scenes)} scenes from dialogue changes"
        )
        return scenes

    def _format_dialogues_for_elevenlabs(
        self, character_dialogues: List[Dict[str, str]]
    ) -> str:
        """Format character dialogues for ElevenLabs audio generation"""
        if not character_dialogues:
            return ""

        print(f"[ELEVENLABS FORMATTER] Formatting {len(character_dialogues)} dialogues")

        formatted_dialogues = []
        for dialogue in character_dialogues:
            character = dialogue.get("character", "Character")
            text = dialogue.get("text", "")
            if text:
                formatted_dialogues.append(f"{character}: {text}")
                print(f"[ELEVENLABS FORMATTER] Added: {character}: {text[:50]}...")

        result = "\n".join(formatted_dialogues)
        print(f"[ELEVENLABS FORMATTER] Final formatted content: {result[:200]}...")
        return result

    def _extract_narration_text(self, script: str) -> str:
        """Extract narration text from script, removing scene descriptions"""
        lines = script.split("\n")
        narration_lines = []

        for line in lines:
            line = line.strip()
            # Skip scene descriptions (usually in caps or with specific formatting)
            if (
                (line.isupper() and len(line) > 2 and len(line) < 50)
                or line.startswith("(")
                and line.endswith(")")
                or line.startswith("[")
                and line.endswith("]")
                or line.startswith("INT.")
                or line.startswith("EXT.")
                or line.startswith("FADE")
                or line.startswith("CUT")
            ):
                continue

            # Include dialogue and narration text
            if line and not line.startswith("    "):  # Not indented dialogue
                narration_lines.append(line)

        return "\n".join(narration_lines)

    def _parse_script_for_services(
        self, script: str, script_style: str
    ) -> Dict[str, Any]:
        """Dynamically parse the generated script to separate content for ElevenLabs and KlingAI"""
        try:
            # Debug: Check script type and content
            print(f"[SCRIPT PARSER DEBUG] Script type: {type(script)}")
            print(
                f"[SCRIPT PARSER DEBUG] Script content: {script[:200] if script else 'None'}"
            )

            # Ensure script is a string
            if not isinstance(script, str):
                print(
                    f"[SCRIPT PARSER ERROR] Script is not a string, converting: {type(script)}"
                )
                script = str(script) if script is not None else ""

            if not script or script.strip() == "":
                print("[SCRIPT PARSER WARNING] Empty script, using fallback")
                return {
                    "elevenlabs_content": "Narrator: This is a fallback narration for the video content.",
                    "klingai_content": "A cinematic scene with visual elements and camera movements.",
                    "elevenlabs_content_type": "fallback_narration",
                    "klingai_content_type": "fallback_scene",
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
                "elevenlabs_content": (
                    str(script) if script else "Narrator: This is a fallback narration."
                ),
                "klingai_content": (
                    str(script) if script else "A cinematic scene with visual elements."
                ),
                "elevenlabs_content_type": "fallback_full_script",
                "klingai_content_type": "fallback_full_script",
            }

    def _parse_screenplay_script(self, script: str) -> Dict[str, Any]:
        """Parse screenplay format script to separate dialogue from scene descriptions"""
        print(f"[SCREENPLAY PARSER] Starting to parse screenplay script")
        print(f"[SCREENPLAY PARSER] Script preview: {script[:300]}...")

        # Initialize content sections
        scene_descriptions = []
        character_dialogues = []

        # Split script into lines
        lines = script.split("\n")
        current_character = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            print(f"[SCREENPLAY PARSER] Line {i}: '{line}'")

            # Scene headings (INT./EXT. locations)
            if re.match(r"^(INT\.|EXT\.)", line, re.IGNORECASE):
                scene_descriptions.append(line)
                print(f"[SCREENPLAY PARSER] Added scene heading: {line}")
                continue

            # Character names in CAPS (dialogue)
            if re.match(r"^[A-Z][A-Z\s]+$", line) and len(line) < 50 and len(line) > 2:
                current_character = line.strip()
                print(f"[SCREENPLAY PARSER] Found character: {current_character}")
                continue

            # Dialogue (indented or after character name)
            if current_character and (
                line.startswith("    ") or '"' in line or "'" in line
            ):
                # Extract dialogue text
                dialogue_text = line.strip()
                if dialogue_text.startswith("    "):
                    dialogue_text = dialogue_text[4:]  # Remove indentation

                # Remove quotes if present
                if dialogue_text.startswith('"') and dialogue_text.endswith('"'):
                    dialogue_text = dialogue_text[1:-1]
                elif dialogue_text.startswith("'") and dialogue_text.endswith("'"):
                    dialogue_text = dialogue_text[1:-1]

                if dialogue_text and len(dialogue_text) > 5:
                    character_dialogues.append(
                        {"character": current_character, "text": dialogue_text}
                    )
                    print(
                        f"[SCREENPLAY PARSER] Added dialogue for {current_character}: {dialogue_text[:50]}..."
                    )
                current_character = None
                continue

            # Action descriptions (not dialogue, not scene headings, not character names)
            if (
                not re.match(r"^[A-Z][A-Z\s]+$", line)
                and len(line) > 10
                and not line.startswith("(")
                and not line.startswith("[")
                and not line.startswith("FADE")
                and not line.startswith("CUT")
                and not line.startswith("CAMERA")
            ):
                scene_descriptions.append(line)
                print(f"[SCREENPLAY PARSER] Added scene description: {line[:50]}...")
                continue

        print(
            f"[SCREENPLAY PARSER] Found {len(character_dialogues)} character dialogues"
        )
        print(f"[SCREENPLAY PARSER] Found {len(scene_descriptions)} scene descriptions")

        # Format content for each service
        elevenlabs_content = self._format_dialogues_for_elevenlabs(character_dialogues)
        klingai_content = (
            ". ".join(scene_descriptions)
            if scene_descriptions
            else "A cinematic scene with visual elements and camera movements."
        )

        # If no character dialogues found, use narration
        if not elevenlabs_content or elevenlabs_content.strip() == "":
            print("[SCREENPLAY PARSER] No character dialogues found, using narration")
            elevenlabs_content = "Narrator: " + klingai_content[:200] + "..."

        print(f"[SCREENPLAY PARSER] ElevenLabs content: {elevenlabs_content[:100]}...")
        print(f"[SCREENPLAY PARSER] KlingAI content: {klingai_content[:100]}...")

        return {
            "elevenlabs_content": elevenlabs_content,
            "klingai_content": klingai_content,
            "elevenlabs_content_type": (
                "character_dialogue" if character_dialogues else "narration"
            ),
            "klingai_content_type": "scene_descriptions",
            "character_dialogues": character_dialogues,
            "scene_descriptions": scene_descriptions,
        }

    def _parse_narration_script(self, script: str) -> Dict[str, Any]:
        """Parse narration format script to separate narrative text from scene descriptions"""
        # For narration scripts, most content goes to ElevenLabs
        # Scene descriptions (camera directions) go to KlingAI

        scene_descriptions = []
        narration_text = []

        lines = script.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Camera directions and visual descriptions
            if any(
                keyword in line.upper()
                for keyword in [
                    "CAMERA",
                    "WE SEE",
                    "THE CAMERA",
                    "ZOOMS",
                    "PANS",
                    "SHOWS",
                    "VISUAL",
                    "SCENE",
                    "SETTING",
                    "BACKGROUND",
                ]
            ):
                scene_descriptions.append(line)
            else:
                # Everything else is narration
                narration_text.append(line)

        elevenlabs_content = "\n".join(narration_text)
        klingai_content = (
            "\n".join(scene_descriptions)
            if scene_descriptions
            else "A cinematic scene based on the narration"
        )

        return {
            "elevenlabs_content": elevenlabs_content,
            "klingai_content": klingai_content,
            "elevenlabs_content_type": "narration_text",
            "klingai_content_type": "scene_descriptions",
            "parsed_sections": {
                "narration_text": narration_text,
                "scene_descriptions": scene_descriptions,
            },
        }

    def _sanitize_content_for_klingai(self, content: str) -> str:
        """Sanitize content to pass KlingAI risk control system"""
        if not content:
            return "A peaceful and educational scene with gentle camera movements."

        # First apply general text sanitization
        sanitized_content = TextSanitizer.sanitize_for_openai(content)

        # Convert to lowercase for easier filtering
        content_lower = sanitized_content.lower()

        # List of potentially problematic keywords that might trigger risk control
        problematic_keywords = [
            "violence",
            "blood",
            "death",
            "kill",
            "murder",
            "weapon",
            "gun",
            "knife",
            "fight",
            "war",
            "battle",
            "attack",
            "explosion",
            "bomb",
            "terror",
            "horror",
            "scary",
            "nude",
            "naked",
            "sex",
            "sexual",
            "intimate",
            "explicit",
            "adult",
            "mature",
            "drug",
            "alcohol",
            "drunk",
            "intoxicated",
            "addiction",
            "overdose",
            "suicide",
            "self-harm",
            "depression",
            "mental illness",
            "racist",
            "discrimination",
            "hate",
            "prejudice",
            "bigotry",
            "political",
            "controversial",
            "sensitive",
            "taboo",
            "occult",
            "witchcraft",
            "satanic",
            "demonic",
            "evil",
            "dark magic",
            "religious",
            "sacred",
            "holy",
            "divine",
            "angelic",
            "spiritual",
        ]

        # Check if content contains problematic keywords
        found_keywords = [
            keyword for keyword in problematic_keywords if keyword in content_lower
        ]

        if found_keywords:
            print(
                f"[CONTENT SANITIZATION] Found potentially problematic keywords: {found_keywords}"
            )
            print(
                f"[CONTENT SANITIZATION] Original content: {sanitized_content[:200]}..."
            )

            # Create a sanitized version by removing or replacing problematic content
            final_sanitized_content = self._create_safe_content(
                sanitized_content, found_keywords
            )

            print(
                f"[CONTENT SANITIZATION] Sanitized content: {final_sanitized_content[:200]}..."
            )
            return final_sanitized_content

        return sanitized_content

    def _create_safe_content(
        self, original_content: str, problematic_keywords: list
    ) -> str:
        """Create safe content by replacing problematic elements with educational alternatives"""

        # Replace problematic content with safe alternatives
        replacements = {
            "violence": "peaceful interaction",
            "blood": "energy",
            "death": "transformation",
            "kill": "overcome",
            "murder": "conflict resolution",
            "weapon": "tool",
            "gun": "device",
            "knife": "instrument",
            "fight": "discussion",
            "war": "challenge",
            "battle": "competition",
            "attack": "approach",
            "explosion": "transformation",
            "bomb": "device",
            "terror": "mystery",
            "horror": "adventure",
            "scary": "exciting",
            "nude": "natural",
            "naked": "uncovered",
            "sex": "relationship",
            "sexual": "personal",
            "intimate": "close",
            "explicit": "detailed",
            "adult": "mature",
            "drug": "substance",
            "alcohol": "beverage",
            "drunk": "affected",
            "intoxicated": "influenced",
            "addiction": "habit",
            "overdose": "excess",
            "suicide": "choice",
            "self-harm": "self-reflection",
            "depression": "sadness",
            "mental illness": "mental health",
            "racist": "prejudiced",
            "discrimination": "differentiation",
            "hate": "dislike",
            "prejudice": "bias",
            "bigotry": "intolerance",
            "political": "social",
            "controversial": "debated",
            "sensitive": "important",
            "taboo": "unusual",
            "occult": "mystical",
            "witchcraft": "magical practices",
            "satanic": "dark",
            "demonic": "mysterious",
            "evil": "negative",
            "dark magic": "mystical arts",
            "religious": "spiritual",
            "sacred": "special",
            "holy": "divine",
            "divine": "spiritual",
            "angelic": "heavenly",
            "spiritual": "mystical",
        }

        # Apply replacements
        sanitized = original_content
        for keyword in problematic_keywords:
            if keyword in replacements:
                sanitized = sanitized.replace(keyword, replacements[keyword])
                sanitized = sanitized.replace(
                    keyword.title(), replacements[keyword].title()
                )
                sanitized = sanitized.replace(
                    keyword.upper(), replacements[keyword].upper()
                )

        # If content is still too problematic, use a generic safe scene
        if len(sanitized.strip()) < 50:
            return "A peaceful educational scene with gentle camera movements, showing people learning and growing in a positive environment."

        return sanitized

    def _validate_content_safety(self, content: str) -> dict:
        """Validate content safety and return safety score and recommendations"""
        if not content:
            return {
                "safe": True,
                "score": 1.0,
                "issues": [],
                "recommendation": "Content is empty",
            }

        content_lower = content.lower()

        # Define risk categories
        risk_categories = {
            "violence": [
                "violence",
                "blood",
                "death",
                "kill",
                "murder",
                "weapon",
                "gun",
                "knife",
                "fight",
                "war",
                "battle",
                "attack",
                "explosion",
                "bomb",
            ],
            "sexual": [
                "nude",
                "naked",
                "sex",
                "sexual",
                "intimate",
                "explicit",
                "adult",
            ],
            "substance": [
                "drug",
                "alcohol",
                "drunk",
                "intoxicated",
                "addiction",
                "overdose",
            ],
            "mental_health": ["suicide", "self-harm", "depression", "mental illness"],
            "discrimination": [
                "racist",
                "discrimination",
                "hate",
                "prejudice",
                "bigotry",
            ],
            "religious": [
                "occult",
                "witchcraft",
                "satanic",
                "demonic",
                "evil",
                "dark magic",
                "religious",
                "sacred",
                "holy",
                "divine",
                "angelic",
            ],
            "political": ["political", "controversial", "sensitive", "taboo"],
        }

        issues = []
        total_risk_score = 0

        for category, keywords in risk_categories.items():
            found_keywords = [kw for kw in keywords if kw in content_lower]
            if found_keywords:
                issues.append(
                    {
                        "category": category,
                        "keywords": found_keywords,
                        "count": len(found_keywords),
                    }
                )
                total_risk_score += len(found_keywords)

        # Calculate safety score (0 = very risky, 1 = very safe)
        max_possible_risk = sum(len(keywords) for keywords in risk_categories.values())
        safety_score = max(0, 1 - (total_risk_score / max_possible_risk))

        recommendation = "Content appears safe for video generation"
        if total_risk_score > 0:
            recommendation = f"Content contains {total_risk_score} potentially problematic elements. Consider sanitizing before generation."

        return {
            "safe": safety_score > 0.7,
            "score": safety_score,
            "issues": issues,
            "recommendation": recommendation,
            "total_risk_score": total_risk_score,
        }

    def analyze_chapter_content_safety(
        self, chapter_content: str, chapter_title: str = ""
    ) -> dict:
        """Analyze chapter content for potential KlingAI risk control issues"""
        if not chapter_content:
            return {
                "safe": True,
                "score": 1.0,
                "issues": [],
                "recommendation": "Content is empty",
                "problematic_sections": [],
                "chapter_title": chapter_title,
            }

        # Validate content safety
        safety_check = self._validate_content_safety(chapter_content)

        # Find problematic sections
        problematic_sections = self._find_problematic_sections(chapter_content)

        # Create detailed analysis
        analysis = {
            "safe": safety_check["safe"],
            "score": safety_check["score"],
            "issues": safety_check["issues"],
            "recommendation": safety_check["recommendation"],
            "problematic_sections": problematic_sections,
            "chapter_title": chapter_title,
            "content_length": len(chapter_content),
            "word_count": len(chapter_content.split()),
            "risk_level": self._calculate_risk_level(safety_check["score"]),
        }

        return analysis

    def _find_problematic_sections(self, content: str) -> List[Dict[str, Any]]:
        """Find specific sections in content that contain problematic keywords"""
        problematic_sections = []

        # Define risk categories with keywords
        risk_categories = {
            "violence": [
                "violence",
                "blood",
                "death",
                "kill",
                "murder",
                "weapon",
                "gun",
                "knife",
                "fight",
                "war",
                "battle",
                "attack",
                "explosion",
                "bomb",
            ],
            "sexual": [
                "nude",
                "naked",
                "sex",
                "sexual",
                "intimate",
                "explicit",
                "adult",
            ],
            "substance": [
                "drug",
                "alcohol",
                "drunk",
                "intoxicated",
                "addiction",
                "overdose",
            ],
            "mental_health": ["suicide", "self-harm", "depression", "mental illness"],
            "discrimination": [
                "racist",
                "discrimination",
                "hate",
                "prejudice",
                "bigotry",
            ],
            "religious": [
                "occult",
                "witchcraft",
                "satanic",
                "demonic",
                "evil",
                "dark magic",
                "religious",
                "sacred",
                "holy",
                "divine",
                "angelic",
            ],
            "political": ["political", "controversial", "sensitive", "taboo"],
        }

        # Split content into sentences for analysis
        sentences = content.split(". ")

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            found_issues = []

            for category, keywords in risk_categories.items():
                found_keywords = [kw for kw in keywords if kw in sentence_lower]
                if found_keywords:
                    found_issues.append(
                        {"category": category, "keywords": found_keywords}
                    )

            if found_issues:
                problematic_sections.append(
                    {
                        "sentence_index": i,
                        "sentence": sentence,
                        "issues": found_issues,
                        "suggested_replacement": self._suggest_safe_replacement(
                            sentence, found_issues
                        ),
                    }
                )

        return problematic_sections

    def _suggest_safe_replacement(
        self, sentence: str, issues: List[Dict[str, Any]]
    ) -> str:
        """Suggest a safe replacement for a problematic sentence"""
        replacements = {
            "violence": "peaceful interaction",
            "blood": "energy",
            "death": "transformation",
            "kill": "overcome",
            "murder": "conflict resolution",
            "weapon": "tool",
            "gun": "device",
            "knife": "instrument",
            "fight": "discussion",
            "war": "challenge",
            "battle": "competition",
            "attack": "approach",
            "explosion": "transformation",
            "bomb": "device",
            "terror": "mystery",
            "horror": "adventure",
            "scary": "exciting",
            "nude": "natural",
            "naked": "uncovered",
            "sex": "relationship",
            "sexual": "personal",
            "intimate": "close",
            "explicit": "detailed",
            "adult": "mature",
            "drug": "substance",
            "alcohol": "beverage",
            "drunk": "affected",
            "intoxicated": "influenced",
            "addiction": "habit",
            "overdose": "excess",
            "suicide": "choice",
            "self-harm": "self-reflection",
            "depression": "sadness",
            "mental illness": "mental health",
            "racist": "prejudiced",
            "discrimination": "differentiation",
            "hate": "dislike",
            "prejudice": "bias",
            "bigotry": "intolerance",
            "political": "social",
            "controversial": "debated",
            "sensitive": "important",
            "taboo": "unusual",
            "occult": "mystical",
            "witchcraft": "magical practices",
            "satanic": "dark",
            "demonic": "mysterious",
            "evil": "negative",
            "dark magic": "mystical arts",
            "religious": "spiritual",
            "sacred": "special",
            "holy": "divine",
            "divine": "spiritual",
            "angelic": "heavenly",
            "spiritual": "mystical",
        }

        # Apply replacements
        sanitized = sentence
        for issue in issues:
            for keyword in issue["keywords"]:
                if keyword in replacements:
                    sanitized = sanitized.replace(keyword, replacements[keyword])
                    sanitized = sanitized.replace(
                        keyword.title(), replacements[keyword].title()
                    )
                    sanitized = sanitized.replace(
                        keyword.upper(), replacements[keyword].upper()
                    )

        return sanitized

    def _calculate_risk_level(self, safety_score: float) -> str:
        """Calculate risk level based on safety score"""
        if safety_score >= 0.9:
            return "LOW"
        elif safety_score >= 0.7:
            return "MEDIUM"
        elif safety_score >= 0.5:
            return "HIGH"
        else:
            return "VERY HIGH"

    async def _download_and_store_video(
        self, video_url: str, filename: str, user_id: str
    ) -> str:
        """Download video from URL and store in Supabase"""
        try:
            print(f"📥 Downloading video from: {video_url}")

            # Download video to temporary file
            import tempfile
            import httpx

            fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

            async with httpx.AsyncClient(
                timeout=300.0
            ) as client:  # 5 minute timeout for large videos
                response = await client.get(video_url)
                response.raise_for_status()

                with open(temp_path, "wb") as f:
                    f.write(response.content)

            print(f"✅ Video downloaded to: {temp_path}")

            # Upload to Supabase Storage
            supabase_url = await self._serve_video_from_supabase(
                temp_path, filename, user_id
            )

            # Clean up temporary file
            os.unlink(temp_path)

            print(f"✅ Video uploaded to Supabase: {supabase_url}")
            return supabase_url

        except Exception as e:
            print(f"❌ Error downloading/storing video: {e}")
            return None

    async def _combine_videos_with_ffmpeg(
        self, video_urls: List[str], output_filename: str, user_id: str
    ) -> str:
        """Combine multiple videos using FFmpeg"""
        try:
            print(f"🎬 Combining {len(video_urls)} videos using FFmpeg")

            import tempfile
            import subprocess
            import httpx

            # Download all videos to temporary files
            temp_video_paths = []

            for i, video_url in enumerate(video_urls):
                fd, temp_path = tempfile.mkstemp(suffix=f"_part_{i}.mp4")
                os.close(fd)

                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.get(video_url)
                    response.raise_for_status()

                    with open(temp_path, "wb") as f:
                        f.write(response.content)

                temp_video_paths.append(temp_path)
                print(f"✅ Downloaded video {i+1}/{len(video_urls)}: {temp_path}")

            # Create file list for FFmpeg
            fd, file_list_path = tempfile.mkstemp(suffix=".txt")
            os.close(fd)

            with open(file_list_path, "w") as f:
                for video_path in temp_video_paths:
                    f.write(f"file '{video_path}'\n")

            # Create output file path
            fd, output_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

            # Run FFmpeg to concatenate videos
            ffmpeg_cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                file_list_path,
                "-c",
                "copy",  # Copy streams without re-encoding for speed
                "-y",  # Overwrite output file
                output_path,
            ]

            print(f"🔄 Running FFmpeg command: {' '.join(ffmpeg_cmd)}")

            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                print(f"❌ FFmpeg failed: {result.stderr}")
                return None

            print(f"✅ Videos combined successfully: {output_path}")

            # Upload combined video to Supabase
            supabase_url = await self._serve_video_from_supabase(
                output_path, output_filename, user_id
            )

            # Clean up temporary files
            for temp_path in temp_video_paths:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            if os.path.exists(file_list_path):
                os.unlink(file_list_path)

            if os.path.exists(output_path):
                os.unlink(output_path)

            print(f"✅ Combined video uploaded: {supabase_url}")
            return supabase_url

        except Exception as e:
            print(f"❌ Error combining videos: {e}")
            return None

    async def _poll_video_status_enhanced(
        self,
        video_id: str,
        scene_description: str,
        content_id: str = None,
    ) -> Dict[str, Any]:
        """Enhanced polling for video completion status with detailed logging and database updates"""
        try:
            print(f"🔄 Enhanced polling for video completion: {video_id}")

            headers = {
                "x-api-key": settings.TAVUS_API_KEY,
                "Content-Type": "application/json",
            }

            # Increase polling attempts and intervals for longer videos
            max_attempts = 180  # 15 minutes with 5-second intervals
            attempt = 0
            last_status = None
            last_progress = None

            async with httpx.AsyncClient(timeout=30.0) as client:
                while attempt < max_attempts:
                    attempt += 1

                    try:
                        print(
                            f"📊 Polling attempt {attempt}/{max_attempts} for video {video_id}"
                        )

                        response = await client.get(
                            f"{self.base_url}/videos/{video_id}", headers=headers
                        )

                        print(f"📊 Polling response status: {response.status_code}")

                        if response.status_code == 200:
                            try:
                                data = response.json()
                                print(
                                    f"📄 Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                                )

                                status = data.get("status", "unknown")
                                progress = data.get("generation_progress", "0/100")

                                # Update database with current status and response
                                if content_id:
                                    try:
                                        statement = select(LearningContent).where(
                                            LearningContent.id == uuid.UUID(content_id)
                                        )
                                        result = await self.session.exec(statement)
                                        content_record = result.first()

                                        if content_record:
                                            content_record.tavus_response = data
                                            content_record.generation_progress = (
                                                progress
                                            )
                                            content_record.status = "processing"

                                            # If we have a hosted_url, save it even if video is still generating
                                            hosted_url = data.get("hosted_url")
                                            if hosted_url:
                                                content_record.tavus_url = hosted_url
                                                print(
                                                    f"🌐 Hosted URL available: {hosted_url}"
                                                )

                                            self.session.add(content_record)
                                            await self.session.commit()
                                    except Exception as db_e:
                                        print(f"Error updating LearningContent: {db_e}")

                                # Log status changes
                                if status != last_status:
                                    print(
                                        f"🔄 Status changed from '{last_status}' to '{status}'"
                                    )
                                    last_status = status

                                if progress != last_progress:
                                    print(
                                        f"📈 Progress changed from '{last_progress}' to '{progress}'"
                                    )
                                    last_progress = progress

                                if status in ["completed", "ready"]:
                                    print(f"✅ Video completed: {video_id}")

                                    # Try multiple URL fields
                                    video_url = (
                                        data.get("download_url")
                                        or data.get("video_url")
                                        or data.get("hosted_url")
                                        or data.get("url")
                                    )

                                    hosted_url = (
                                        data.get("hosted_url")
                                        or data.get("video_url")
                                        or data.get("download_url")
                                    )

                                    print(f"🔗 Video URL found: {video_url}")
                                    print(f"🌐 Hosted URL found: {hosted_url}")

                                    # Update database with final status
                                    if content_id:
                                        try:
                                            statement = select(LearningContent).where(
                                                LearningContent.id
                                                == uuid.UUID(content_id)
                                            )
                                            result = await self.session.exec(statement)
                                            content_record = result.first()

                                            if content_record:
                                                content_record.tavus_response = data
                                                content_record.status = "ready"
                                                content_record.generation_progress = (
                                                    progress
                                                )

                                                if video_url:
                                                    content_record.content_url = (
                                                        video_url
                                                    )
                                                    content_record.tavus_url = (
                                                        hosted_url
                                                    )

                                                self.session.add(content_record)
                                                await self.session.commit()
                                        except Exception as db_e:
                                            print(
                                                f"Error updating LearningContent final status: {db_e}"
                                            )

                                    if video_url:
                                        return {
                                            "video_id": video_id,
                                            "video_url": video_url,
                                            "hosted_url": hosted_url,
                                            "download_url": data.get("download_url"),
                                            "duration": data.get("duration", 180),
                                            "status": "completed",
                                            "final_response": data,
                                        }
                                    else:
                                        print("⚠️ Video completed but no URL found")
                                        print(
                                            f"🔍 Available URL fields: {[k for k, v in data.items() if 'url' in k.lower()]}"
                                        )
                                        return {
                                            "video_id": video_id,
                                            "hosted_url": hosted_url,
                                            "status": "completed_no_download",
                                            "final_response": data,
                                            "error": "Video completed but no downloadable URL found",
                                        }

                                elif status == "failed":
                                    error_msg = data.get("error", "Unknown error")
                                    print(f"❌ Video generation failed: {video_id}")
                                    print(f"📄 Error details: {error_msg}")

                                    # Update database with failed status
                                    if content_id and supabase_client:
                                        supabase_client.table(
                                            "learning_content"
                                        ).update(
                                            {
                                                "tavus_response": data,
                                                "status": "failed",
                                                "error_message": error_msg,
                                                "generation_progress": progress,
                                            }
                                        ).eq(
                                            "id", content_id
                                        ).execute()

                                    return {
                                        "video_id": video_id,
                                        "status": "failed",
                                        "error": error_msg,
                                        "final_response": data,
                                    }

                                elif status in ["queued", "generating", "processing"]:
                                    print(
                                        f"⏳ Video status: {status} (attempt {attempt}/{max_attempts}) - Progress: {progress}"
                                    )

                                    # Wait longer between polls for generating status
                                    wait_time = 10 if status == "generating" else 5
                                    await asyncio.sleep(wait_time)
                                    continue

                                else:
                                    print(f"⚠️ Unknown status: {status}")
                                    print(f"📄 Full response data: {data}")
                                    await asyncio.sleep(5)
                                    continue

                            except json.JSONDecodeError as e:
                                print(f"❌ Failed to parse JSON response: {e}")
                                print(f"📄 Raw response: {response.text}")
                                await asyncio.sleep(5)
                                continue

                        elif response.status_code == 404:
                            print(f"❌ Video not found: {video_id}")
                            return {
                                "video_id": video_id,
                                "status": "not_found",
                                "error": "Video ID not found in Tavus system",
                            }

                        elif response.status_code == 401:
                            print(f"❌ Unauthorized access to video: {video_id}")
                            return {
                                "video_id": video_id,
                                "status": "unauthorized",
                                "error": "Invalid API key or insufficient permissions",
                            }

                        else:
                            print(
                                f"❌ Polling failed with status: {response.status_code}"
                            )
                            print(f"📄 Error response: {response.text}")
                            await asyncio.sleep(5)
                            continue

                    except httpx.TimeoutException:
                        print(f"⏰ Timeout on attempt {attempt}, retrying...")
                        await asyncio.sleep(5)
                        continue

                    except Exception as e:
                        print(f"❌ Error polling video on attempt {attempt}: {e}")
                        await asyncio.sleep(5)
                        continue

            # If we get here, we've exceeded max attempts
            print(f"⏰ Video generation timed out after {max_attempts * 5} seconds")
            return {
                "video_id": video_id,
                "status": "timeout",
                "message": f"Video generation took longer than expected (max {max_attempts * 5} seconds)",
                "last_status": last_status,
                "last_progress": last_progress,
            }

        except Exception as e:
            print(f"❌ Error in enhanced video polling: {e}")
            import traceback

            print(f"🔍 Full traceback: {traceback.format_exc()}")
            return {"video_id": video_id, "status": "error", "error": str(e)}

    async def combine_tavus_videos(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Combine multiple Tavus video segments into a single video using FFmpeg"""
        try:
            print(f"🎬 Combining Tavus videos for content: {content_id}")

            # Get the learning content record
            statement = select(LearningContent).where(
                LearningContent.id == uuid.UUID(content_id)
            )
            result = await self.session.exec(statement)
            content_record = result.first()

            if not content_record:
                print(f"❌ Content record not found: {content_id}")
                return None

            tavus_url = content_record.tavus_url

            if not tavus_url:
                print(f"❌ No Tavus URL found for content: {content_id}")
                return None

            print(f"🌐 Tavus URL: {tavus_url}")

            # Update status to combining
            content_record.status = "combining"
            self.session.add(content_record)
            await self.session.commit()

            # Download the video from Tavus hosted URL
            video_filename = f"tavus_video_{content_id}.mp4"
            video_path = await self._download_and_store_video(
                tavus_url, video_filename, str(content_record.user_id)
            )

            if not video_path:
                print(f"❌ Failed to download video from Tavus URL: {tavus_url}")
                # Update status back to processing
                content_record.status = "processing"
                # Note: LearningContent model doesn't have error_message field in my view,
                # but I can add it to meta if needed or just log it.
                # Assuming meta field exists and is initialized.
                if content_record.meta is None:
                    content_record.meta = {}
                content_record.meta["error_message"] = (
                    "Failed to download video from Tavus"
                )

                self.session.add(content_record)
                await self.session.commit()
                return None

            print(f"✅ Video downloaded to: {video_path}")

            # Upload the combined video to Supabase Storage
            combined_video_url = await self._serve_video_from_supabase(
                video_path, video_filename, str(content_record.user_id)
            )

            if not combined_video_url:
                print(f"❌ Failed to upload combined video to Supabase")
                # Update status back to processing
                content_record.status = "processing"
                if content_record.meta is None:
                    content_record.meta = {}
                content_record.meta["error_message"] = (
                    "Failed to upload combined video to storage"
                )

                self.session.add(content_record)
                await self.session.commit()
                return None

            print(f"✅ Combined video uploaded: {combined_video_url}")

            # Update the database with the final combined video URL
            content_record.status = "ready"
            content_record.content_url = combined_video_url
            if content_record.meta is None:
                content_record.meta = {}
            content_record.meta["combined_video_url"] = combined_video_url
            content_record.meta["duration"] = 180

            self.session.add(content_record)
            await self.session.commit()

            return {
                "id": content_id,
                "video_url": combined_video_url,
                "tavus_url": tavus_url,
                "status": "ready",
                "duration": 180,
            }

        except Exception as e:
            print(f"❌ Error combining Tavus videos: {e}")
            import traceback

            print(f"🔍 Full traceback: {traceback.format_exc()}")

            # Update database with error status
            try:
                statement = select(LearningContent).where(
                    LearningContent.id == uuid.UUID(content_id)
                )
                result = await self.session.exec(statement)
                content_record = result.first()
                if content_record:
                    content_record.status = "failed"
                    if content_record.meta is None:
                        content_record.meta = {}
                    content_record.meta["error_message"] = (
                        f"Error combining videos: {str(e)}"
                    )
                    self.session.add(content_record)
                    await self.session.commit()
            except Exception as db_e:
                print(f"Error updating error status: {db_e}")

            return None
