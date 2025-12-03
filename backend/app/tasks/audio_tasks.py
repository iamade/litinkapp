# from app.tasks.celery_app import celery_app
# import asyncio
# from typing import Dict, Any, List
# from app.core.services.script_parser import ScriptParser
# from app.core.database import get_supabase
# from app.core.config import settings
# from datetime import datetime
# from app.core.services.pipeline import PipelineManager, PipelineStep
# from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService


# # Add to imports
# from app.core.services.pipeline import PipelineManager, PipelineStep


# @celery_app.task(bind=True)
# def generate_all_audio_for_video(self, video_generation_id: str):
#     """Main task to generate all audio for a video generation with pipeline support"""

#     pipeline_manager = PipelineManager()

#     try:
#         print(
#             f"[AUDIO GENERATION] Starting audio generation for video: {video_generation_id}"
#         )

#         # Mark audio step as started
#         pipeline_manager.mark_step_started(
#             video_generation_id, PipelineStep.AUDIO_GENERATION
#         )

#         # Get video generation data
#         supabase = get_supabase()
#         video_data = (
#             supabase.table("video_generations")
#             .select("*")
#             .eq("id", video_generation_id)
#             .single()
#             .execute()
#         )

#         if not video_data.data:
#             raise Exception(f"Video generation {video_generation_id} not found")

#         video_gen = video_data.data
#         script_data = video_gen.get("script_data", {})
#         chapter_id = video_gen.get("chapter_id")  # Get chapter_id from video generation
#         user_id = video_gen.get("user_id")  # Get user_id from video generation

#         print(f"[VIDEO AUDIO DEBUG] Video generation ID: {video_generation_id}")
#         print(f"[VIDEO AUDIO DEBUG] Retrieved chapter_id from video_gen: {chapter_id}")
#         print(f"[VIDEO AUDIO DEBUG] Retrieved user_id from video_gen: {user_id}")
#         print(f"[VIDEO AUDIO DEBUG] Video_gen keys: {list(video_gen.keys())}")

#         if not script_data:
#             raise Exception("No script data found for audio generation")

#         # ✅ NEW: Get script_style from the scripts table
#         script_id = video_gen.get("script_id")
#         script_style = "cinematic_movie"  # Default fallback

#         if script_id:
#             try:
#                 script_response = (
#                     supabase.table("scripts")
#                     .select("script_style")
#                     .eq("id", script_id)
#                     .single()
#                     .execute()
#                 )
#                 if script_response.data:
#                     script_style = script_response.data.get(
#                         "script_style", "cinematic_movie"
#                     )
#                     print(f"[SCRIPT STYLE] Fetched from scripts table: {script_style}")
#                 else:
#                     print(
#                         f"[SCRIPT STYLE] Script {script_id} not found, using default: {script_style}"
#                     )
#             except Exception as e:
#                 print(
#                     f"[SCRIPT STYLE] Error fetching script style: {e}, using default: {script_style}"
#                 )
#         else:
#             print(f"[SCRIPT STYLE] No script_id found, using default: {script_style}")

#         # Update status
#         supabase.table("video_generations").update(
#             {"generation_status": "generating_audio"}
#         ).eq("id", video_generation_id).execute()

#         # Parse script for audio components
#         parser = ScriptParser()
#         audio_components = parser.parse_script_for_audio(
#             script_data.get("script", ""),
#             script_data.get("characters", []),
#             script_data.get("scene_descriptions", []),
#             script_style,
#         )

#         print(f"[AUDIO PARSER] Using script style: {script_style}")
#         print(
#             f"[AUDIO PARSER] Characters from script_data: {script_data.get('characters', [])}"
#         )
#         print(f"[AUDIO PARSER] Script sample: {script_data.get('script', '')[:200]}...")
#         print(f"[AUDIO PARSER] Extracted components:")
#         print(f"- Narrator segments: {len(audio_components['narrator_segments'])}")
#         print(f"- Sound effects: {len(audio_components['sound_effects'])}")
#         print(f"- Background music: {len(audio_components['background_music'])}")

#         # Generate all audio types
#         audio_service = ModelsLabV7AudioService()

#         # Generate audio based on script style
#         if script_style == "cinematic_movie":
#             # For cinematic: only background music and sound effects (no narrator, no character voices)
#             narrator_results = []
#             character_results = []
#         else:
#             # For narration: generate narrator voice + background music + sound effects
#             narrator_results = asyncio.run(
#                 generate_narrator_audio(
#                     audio_service,
#                     video_generation_id,
#                     audio_components["narrator_segments"],
#                     chapter_id,
#                     user_id,
#                 )
#             )
#             character_results = []

#         # 3. Generate sound effects
#         sound_effect_results = asyncio.run(
#             generate_sound_effects_audio(
#                 audio_service,
#                 video_generation_id,
#                 audio_components["sound_effects"],
#                 chapter_id,
#                 user_id,
#             )
#         )

#         # 4. Generate background music
#         background_music_results = asyncio.run(
#             generate_background_music(
#                 audio_service,
#                 video_generation_id,
#                 audio_components["background_music"],
#                 chapter_id,
#                 user_id,
#             )
#         )

#         # Compile results
#         total_audio_files = (
#             len(narrator_results)
#             + len(sound_effect_results)
#             + len(background_music_results)
#         )

#         # Update video generation with audio file references
#         audio_files_data = {
#             "narrator": narrator_results,
#             "sound_effects": sound_effect_results,
#             "background_music": background_music_results,
#         }

#         supabase.table("video_generations").update(
#             {"audio_files": audio_files_data, "generation_status": "audio_completed"}
#         ).eq("id", video_generation_id).execute()

#         # ✅ NEW: Mark step as completed
#         pipeline_manager.mark_step_completed(
#             video_generation_id,
#             PipelineStep.AUDIO_GENERATION,
#             {
#                 "total_audio_files": total_audio_files,
#                 "audio_files_data": audio_files_data,
#             },
#         )

#         success_message = (
#             f"Audio generation completed! {total_audio_files} audio files created"
#         )
#         print(f"[AUDIO GENERATION SUCCESS] {success_message}")

#         # ✅ NEW: Check for existing images before triggering image generation
#         print(
#             f"[PIPELINE] Checking for existing images before starting image generation"
#         )

#         # Query image_generations table for existing images
#         existing_images_response = (
#             supabase.table("image_generations")
#             .select("id")
#             .eq("video_generation_id", video_generation_id)
#             .eq("status", "completed")
#             .execute()
#         )

#         existing_images_count = len(existing_images_response.data or [])

#         if existing_images_count > 0:
#             print(
#                 f"✅ Found {existing_images_count} existing images, skipping image generation"
#             )
#             # Update video generation status to indicate images are ready
#             supabase.table("video_generations").update(
#                 {"generation_status": "images_completed"}
#             ).eq("id", video_generation_id).execute()
#         else:
#             print(f"[PIPELINE] No existing images found, starting image generation")
#             from app.tasks.image_tasks import generate_all_images_for_video

#             generate_all_images_for_video.delay(video_generation_id)

#         return {
#             "status": "success",
#             "message": success_message + " - Starting image generation...",
#             "audio_files_count": total_audio_files,
#             "audio_data": audio_files_data,
#             "next_step": "image_generation",
#         }

#     except Exception as e:
#         error_message = f"Audio generation failed: {str(e)}"
#         print(f"[AUDIO GENERATION ERROR] {error_message}")

#         # ✅ NEW: Mark step as failed
#         pipeline_manager.mark_step_failed(
#             video_generation_id, PipelineStep.AUDIO_GENERATION, error_message
#         )

#         # Update status to failed
#         try:
#             supabase = get_supabase()
#             supabase.table("video_generations").update(
#                 {
#                     "generation_status": "failed",
#                     "error_message": error_message,
#                     "can_resume": True,  # ✅ Add this
#                     "failed_at_step": "audio_generation",  # ✅ Add this
#                 }
#             ).eq("id", video_generation_id).execute()
#         except:
#             pass

#         raise Exception(error_message)


# async def generate_narrator_audio(
#     audio_service: ModelsLabV7AudioService,
#     video_gen_id: str,
#     narrator_segments: List[Dict[str, Any]],
#     chapter_id: str,
#     user_id: str,
# ) -> List[Dict[str, Any]]:
#     """Generate narrator voice audio"""

#     print(f"[NARRATOR AUDIO] Generating narrator voice...")
#     narrator_results = []
#     supabase = get_supabase()

#     # ✅ Use V7 service voice mapping
#     narrator_voice = audio_service.narrator_voices[
#         "professional"
#     ]  # Professional narrator voice

#     for i, segment in enumerate(narrator_segments):
#         try:
#             scene_id = segment.get("scene", 1)
#             print(
#                 f"[NARRATOR AUDIO] Processing segment {i+1}/{len(narrator_segments)} for scene {scene_id}"
#             )
#             print(
#                 f"[AUDIO GEN] Generating narrator audio for scene_{scene_id}: {segment['text'][:50]}..."
#             )

#             # Generate audio
#             result = await audio_service.generate_tts_audio(
#                 text=segment["text"],
#                 voice_id=narrator_voice,
#                 model_id="eleven_multilingual_v2",  # ✅ V7 specific model
#                 speed=1.0,
#             )

#             # ✅ FIXED: Extract audio URL from correct response structure
#             audio_url = None
#             duration = 0

#             if result.get("status") == "success":
#                 audio_url = result.get("audio_url")
#                 duration = result.get("audio_time", 0)

#                 if not audio_url:
#                     raise Exception("No audio URL in V7 response")
#             else:
#                 raise Exception(
#                     f"V7 Audio generation failed: {result.get('error', 'Unknown error')}"
#                 )

#             # ✅ FIXED: Use correct column names for database
#             print(
#                 f"[DEBUG] Inserting narrator audio record for video_gen {video_gen_id}"
#             )
#             print(f"[DEBUG] Audio record chapter_id: {chapter_id}, user_id: {user_id}")
#             scene_id = segment.get("scene", 1)

#             # Get script_id from video generation
#             script_id = None
#             try:
#                 video_data = (
#                     supabase.table("video_generations")
#                     .select("script_id")
#                     .eq("id", video_gen_id)
#                     .single()
#                     .execute()
#                 )
#                 if video_data.data:
#                     script_id = video_data.data.get("script_id")
#             except Exception as e:
#                 print(f"[DEBUG] Could not get script_id from video generation: {e}")

#             audio_record_data = {
#                 "video_generation_id": video_gen_id,
#                 "user_id": user_id,  # Add user_id
#                 "chapter_id": chapter_id,  # Add chapter_id
#                 "script_id": script_id,  # Add script_id
#                 "audio_type": "narrator",
#                 "text_content": segment["text"],
#                 "voice_id": narrator_voice,
#                 "audio_url": audio_url,
#                 "duration": float(duration),  # ✅ Use 'duration' (check your schema)
#                 "generation_status": "completed",  # ✅ Use 'generation_status'
#                 "sequence_order": i + 1,
#                 "model_id": result.get(
#                     "model_used", "eleven_multilingual_v2"
#                 ),  # ✅ Add model_id
#                 "scene_id": f"scene_{scene_id}",  # ✅ Store scene_id at top level for merge compatibility
#                 "metadata": {
#                     "chapter_id": chapter_id,
#                     "line_number": segment.get("line_number", i + 1),
#                     "scene": scene_id,
#                     "service": "modelslab_v7",  # ✅ Updated service name
#                     "model_used": result.get("model_used", "eleven_multilingual_v2"),
#                 },
#             }

#             # Insert to database
#             audio_record = (
#                 supabase.table("audio_generations").insert(audio_record_data).execute()
#             )

#             narrator_results.append(
#                 {
#                     "id": audio_record.data[0]["id"],
#                     "scene": segment.get("scene", 1),
#                     "audio_url": audio_url,
#                     "duration": duration,
#                     "text": segment["text"],
#                 }
#             )

#             print(
#                 f"[NARRATOR AUDIO] ✅ Generated segment {i+1} - Duration: {duration}s"
#             )

#         except Exception as e:
#             print(f"[NARRATOR AUDIO] ❌ Failed segment {i+1}: {str(e)}")

#             # ✅ FIXED: Use correct column names for failed records
#             failed_record_data = {
#                 "video_generation_id": video_gen_id,
#                 "user_id": user_id,  # Add user_id
#                 "chapter_id": chapter_id,  # Add chapter_id
#                 "audio_type": "narrator",
#                 "text_content": segment["text"],
#                 "voice_id": narrator_voice,
#                 "generation_status": "failed",  # ✅ Use 'generation_status'
#                 "error_message": str(e),
#                 "sequence_order": i + 1,
#                 "model_id": "eleven_multilingual_v2",  # ✅ Add model_id
#                 "metadata": {
#                     "chapter_id": chapter_id,
#                     "line_number": segment.get("line_number", i + 1),
#                     "scene": segment.get("scene", 1),
#                     "service": "modelslab_v7",
#                 },
#             }
#             supabase.table("audio_generations").insert(failed_record_data).execute()

#     print(
#         f"[NARRATOR AUDIO] Completed: {len(narrator_results)}/{len(narrator_segments)} segments"
#     )
#     return narrator_results


# async def generate_character_audio(
#     audio_service: ModelsLabV7AudioService,
#     video_gen_id: str,
#     character_dialogues: List[Dict[str, Any]],
#     chapter_id: str,
#     user_id: str,
# ) -> List[Dict[str, Any]]:
#     """Generate character voice audio for cinematic scripts"""

#     print(f"[CHARACTER AUDIO] Generating character voices...")
#     character_results = []
#     supabase = get_supabase()

#     # Get available character voices
#     available_voices = list(audio_service.character_voices.items())
#     character_voice_mapping = {}  # Track which voice is assigned to which character

#     for i, dialogue in enumerate(character_dialogues):
#         try:
#             character_name = dialogue["character"]
#             scene_id = dialogue.get("scene", 1)
#             print(
#                 f"[CHARACTER AUDIO] Processing dialogue {i+1}/{len(character_dialogues)} for {character_name} in scene {scene_id}"
#             )
#             print(
#                 f"[AUDIO GEN] Generating character audio for {character_name} in scene_{scene_id}: {dialogue['text'][:50]}..."
#             )

#             # Assign voice to character if not already assigned
#             if character_name not in character_voice_mapping:
#                 # Cycle through voices based on character index or name hash for consistency
#                 voice_index = hash(character_name) % len(available_voices)
#                 voice_name, voice_id = available_voices[voice_index]
#                 character_voice_mapping[character_name] = {
#                     "voice_name": voice_name,
#                     "voice_id": voice_id,
#                 }
#                 print(
#                     f"[CHARACTER AUDIO] Assigned voice '{voice_name}' to {character_name}"
#                 )

#             voice_info = character_voice_mapping[character_name]

#             # Generate audio
#             result = await audio_service.generate_tts_audio(
#                 text=dialogue["text"],
#                 voice_id=voice_info["voice_id"],
#                 model_id="eleven_multilingual_v2",
#                 speed=1.0,
#             )

#             # Extract audio URL and duration
#             audio_url = None
#             duration = 0

#             if result.get("status") == "success":
#                 audio_url = result.get("audio_url")
#                 duration = result.get("audio_time", 0)

#                 if not audio_url:
#                     raise Exception("No audio URL in V7 response")
#             else:
#                 raise Exception(
#                     f"V7 Audio generation failed: {result.get('error', 'Unknown error')}"
#                 )

#             # Store in database
#             scene_id = dialogue.get("scene", 1)

#             # Get script_id from video generation
#             script_id = None
#             try:
#                 video_data = (
#                     supabase.table("video_generations")
#                     .select("script_id")
#                     .eq("id", video_gen_id)
#                     .single()
#                     .execute()
#                 )
#                 if video_data.data:
#                     script_id = video_data.data.get("script_id")
#             except Exception as e:
#                 print(f"[DEBUG] Could not get script_id from video generation: {e}")

#             audio_record_data = {
#                 "video_generation_id": video_gen_id,
#                 "user_id": user_id,
#                 "chapter_id": chapter_id,
#                 "script_id": script_id,  # Add script_id
#                 "audio_type": "character",
#                 "text_content": dialogue["text"],
#                 "voice_id": voice_info["voice_id"],
#                 "audio_url": audio_url,
#                 "duration": float(duration),
#                 "generation_status": "completed",
#                 "sequence_order": i + 1,
#                 "model_id": result.get("model_used", "eleven_multilingual_v2"),
#                 "scene_id": f"scene_{scene_id}",  # ✅ Store scene_id at top level for merge compatibility
#                 "metadata": {
#                     "chapter_id": chapter_id,
#                     "character_name": character_name,
#                     "voice_name": voice_info["voice_name"],
#                     "line_number": dialogue.get("line_number", i + 1),
#                     "scene": scene_id,
#                     "service": "modelslab_v7",
#                     "model_used": result.get("model_used", "eleven_multilingual_v2"),
#                 },
#             }

#             audio_record = (
#                 supabase.table("audio_generations").insert(audio_record_data).execute()
#             )

#             character_results.append(
#                 {
#                     "id": audio_record.data[0]["id"],
#                     "character": character_name,
#                     "voice_name": voice_info["voice_name"],
#                     "voice_id": voice_info["voice_id"],
#                     "scene": dialogue.get("scene", 1),
#                     "audio_url": audio_url,
#                     "duration": duration,
#                     "text": dialogue["text"],
#                 }
#             )

#             print(
#                 f"[CHARACTER AUDIO] ✅ Generated dialogue {i+1} for {character_name} - Duration: {duration}s"
#             )

#         except Exception as e:
#             print(
#                 f"[CHARACTER AUDIO] ❌ Failed dialogue {i+1} for {dialogue.get('character', 'Unknown')}: {str(e)}"
#             )

#             # Get voice info for failed record
#             character_name = dialogue["character"]
#             voice_info = character_voice_mapping.get(
#                 character_name, {"voice_name": "unknown", "voice_id": "unknown"}
#             )

#             failed_record_data = {
#                 "video_generation_id": video_gen_id,
#                 "user_id": user_id,
#                 "chapter_id": chapter_id,
#                 "audio_type": "character",
#                 "text_content": dialogue["text"],
#                 "voice_id": voice_info["voice_id"],
#                 "generation_status": "failed",
#                 "error_message": str(e),
#                 "sequence_order": i + 1,
#                 "model_id": "eleven_multilingual_v2",
#                 "metadata": {
#                     "chapter_id": chapter_id,
#                     "character_name": character_name,
#                     "voice_name": voice_info["voice_name"],
#                     "line_number": dialogue.get("line_number", i + 1),
#                     "scene": dialogue.get("scene", 1),
#                     "service": "modelslab_v7",
#                 },
#             }
#             supabase.table("audio_generations").insert(failed_record_data).execute()

#     # Store character voice mappings in video generation
#     if character_voice_mapping:
#         supabase.table("video_generations").update(
#             {"character_voice_mappings": character_voice_mapping}
#         ).eq("id", video_gen_id).execute()
#         print(f"[CHARACTER AUDIO] Stored voice mappings: {character_voice_mapping}")

#     print(
#         f"[CHARACTER AUDIO] Completed: {len(character_results)}/{len(character_dialogues)} dialogues"
#     )
#     return character_results


# async def generate_sound_effects_audio(
#     audio_service: ModelsLabV7AudioService,  # ✅ Updated type hint
#     video_gen_id: str,
#     sound_effects: List[Dict[str, Any]],
#     chapter_id: str,
#     user_id: str,
# ) -> List[Dict[str, Any]]:
#     """Generate sound effects audio"""

#     print(f"[SOUND EFFECTS] Generating sound effects...")
#     effects_results = []
#     supabase = get_supabase()

#     for i, effect in enumerate(sound_effects):
#         try:
#             print(
#                 f"[SOUND EFFECTS] Processing effect {i+1}/{len(sound_effects)}: {effect['description']}"
#             )

#             # ✅ Use V7 sound effects generation
#             result = await audio_service.generate_sound_effect(
#                 description=effect["description"],
#                 duration=min(30.0, max(3.0, effect.get("duration", 10.0))),  # V7 limits
#                 model_id="eleven_sound_effect",
#             )

#             if result.get("status") == "success":
#                 audio_url = result.get("audio_url")
#                 duration = result.get("audio_time", 10)

#                 if not audio_url:
#                     raise Exception("No audio URL in V7 response")

#                 # Store in database
#                 # Get script_id from video generation
#                 script_id = None
#                 try:
#                     video_data = (
#                         supabase.table("video_generations")
#                         .select("script_id")
#                         .eq("id", video_gen_id)
#                         .single()
#                         .execute()
#                     )
#                     if video_data.data:
#                         script_id = video_data.data.get("script_id")
#                 except Exception as e:
#                     print(f"[DEBUG] Could not get script_id from video generation: {e}")

#                 audio_data = {
#                     "video_generation_id": video_gen_id,
#                     "user_id": user_id,  # Add user_id
#                     "chapter_id": chapter_id,  # Add chapter_id
#                     "script_id": script_id,  # Add script_id
#                     "audio_type": "sfx",
#                     "text_content": effect["description"],
#                     "audio_url": audio_url,
#                     "duration": float(duration),
#                     "sequence_order": i + 1,
#                     "generation_status": "completed",
#                     "metadata": {
#                         "chapter_id": chapter_id,
#                         "effect_type": "ambient",
#                         "service": "modelslab_v7",
#                         "model_used": result.get("model_used", "eleven_sound_effect"),
#                     },
#                 }

#                 db_result = (
#                     supabase.table("audio_generations").insert(audio_data).execute()
#                 )

#                 effects_results.append(
#                     {
#                         "effect_id": i + 1,
#                         "audio_url": audio_url,
#                         "description": effect["description"],
#                         "duration": duration,
#                         "db_id": db_result.data[0]["id"] if db_result.data else None,
#                     }
#                 )

#                 print(f"[SOUND EFFECTS] ✅ Effect {i+1} completed: {audio_url}")
#             else:
#                 raise Exception(
#                     f"V7 API returned error: {result.get('error', 'Unknown error')}"
#                 )

#         except Exception as e:
#             print(f"[SOUND EFFECTS] ❌ Failed: {effect['description']} - {str(e)}")

#             # Store failed record
#             failed_audio_data = {
#                 "video_generation_id": video_gen_id,
#                 "user_id": user_id,  # Add user_id
#                 "chapter_id": chapter_id,  # Add chapter_id
#                 "audio_type": "sfx",
#                 "text_content": effect["description"],
#                 "error_message": str(e),
#                 "sequence_order": i + 1,
#                 "generation_status": "failed",
#                 "metadata": {"chapter_id": chapter_id, "service": "modelslab_v7"},
#             }
#             supabase.table("audio_generations").insert(failed_audio_data).execute()
#             continue

#     print(
#         f"[SOUND EFFECTS] Completed: {len(effects_results)}/{len(sound_effects)} effects"
#     )
#     return effects_results


# async def generate_background_music(
#     audio_service: ModelsLabV7AudioService,  # ✅ Updated type hint
#     video_gen_id: str,
#     music_cues: List[Dict[str, Any]],
#     chapter_id: str,
#     user_id: str,
# ) -> List[Dict[str, Any]]:
#     """Generate background music"""

#     print(f"[BACKGROUND MUSIC] Generating background music...")
#     music_results = []
#     supabase = get_supabase()

#     for i, music_cue in enumerate(music_cues):
#         try:
#             scene_id = music_cue["scene"]
#             print(
#                 f"[BACKGROUND MUSIC] Processing scene {scene_id}: {music_cue['description']}"
#             )
#             print(
#                 f"[AUDIO GEN] Generating background music for scene_{scene_id}: {music_cue['description'][:50]}..."
#             )

#             # ✅ Use V7 music generation
#             result = await audio_service.generate_background_music(
#                 description=music_cue["description"],
#                 model_id="music_v1",
#                 duration=30.0,  # V7 music generation duration
#             )

#             if result.get("status") == "success":
#                 audio_url = result.get("audio_url")
#                 duration = result.get("audio_time", 30.0)

#                 if not audio_url:
#                     raise Exception("No audio URL in V7 response")

#                 # Store in database
#                 scene_id = music_cue["scene"]

#                 # Get script_id from video generation
#                 script_id = None
#                 try:
#                     video_data = (
#                         supabase.table("video_generations")
#                         .select("script_id")
#                         .eq("id", video_gen_id)
#                         .single()
#                         .execute()
#                     )
#                     if video_data.data:
#                         script_id = video_data.data.get("script_id")
#                 except Exception as e:
#                     print(f"[DEBUG] Could not get script_id from video generation: {e}")

#                 audio_record = (
#                     supabase.table("audio_generations")
#                     .insert(
#                         {
#                             "video_generation_id": video_gen_id,
#                             "user_id": user_id,  # Add user_id
#                             "chapter_id": chapter_id,  # Add chapter_id
#                             "script_id": script_id,  # Add script_id
#                             "audio_type": "music",
#                             "text_content": music_cue["description"],
#                             "audio_url": audio_url,
#                             "duration": float(duration),
#                             "generation_status": "completed",
#                             "sequence_order": i + 1,
#                             "scene_id": f"scene_{scene_id}",  # ✅ Store scene_id at top level for merge compatibility
#                             "metadata": {
#                                 "chapter_id": chapter_id,
#                                 "music_type": music_cue.get("type", "background_music"),
#                                 "scene": scene_id,
#                                 "service": "modelslab_v7",
#                                 "model_used": result.get("model_used", "music_v1"),
#                             },
#                         }
#                     )
#                     .execute()
#                 )

#                 music_results.append(
#                     {
#                         "id": audio_record.data[0]["id"],
#                         "scene": music_cue["scene"],
#                         "audio_url": audio_url,
#                         "description": music_cue["description"],
#                         "duration": duration,
#                     }
#                 )

#                 print(f"[BACKGROUND MUSIC] ✅ Generated for Scene {music_cue['scene']}")
#             else:
#                 raise Exception(
#                     f"V7 API returned error: {result.get('error', 'Unknown error')}"
#                 )

#         except Exception as e:
#             print(
#                 f"[BACKGROUND MUSIC] ❌ Failed for Scene {music_cue['scene']}: {str(e)}"
#             )

#             # Store failed record
#             supabase.table("audio_generations").insert(
#                 {
#                     "video_generation_id": video_gen_id,
#                     "user_id": user_id,  # Add user_id
#                     "chapter_id": chapter_id,  # Add chapter_id
#                     "audio_type": "music",
#                     "text_content": music_cue["description"],
#                     "generation_status": "failed",
#                     "error_message": str(e),
#                     "sequence_order": i + 1,
#                     "metadata": {"chapter_id": chapter_id, "service": "modelslab_v7"},
#                 }
#             ).execute()

#     print(
#         f"[BACKGROUND MUSIC] Completed: {len(music_results)}/{len(music_cues)} music tracks"
#     )
#     return music_results


# @celery_app.task(bind=True)
# def generate_chapter_audio_task(
#     self,
#     audio_type: str,
#     text_content: str,
#     user_id: str,
#     chapter_id: str,
#     scene_number: int,
#     voice_id: str = None,
#     emotion: str = "neutral",
#     speed: float = 1.0,
#     duration: float = None,
#     record_id: str = None,
# ):
#     """Generate audio for a chapter scene"""

#     from app.core.services.elevenlabs import ElevenLabsService
#     from app.core.services.modelslab_v7_audio import ModelsLabV7AudioService
#     from app.core.database import get_supabase

#     supabase = get_supabase()

#     try:
#         print(
#             f"[CHAPTER AUDIO] Starting {audio_type} generation for chapter {chapter_id}, scene {scene_number}, user {user_id}"
#         )
#         print(
#             f"[DEBUG] Audio type received: {audio_type}, user_id: {user_id}, chapter_id: {chapter_id}"
#         )
#         print(f"[DEBUG] Task parameters - record_id: {record_id}, voice_id: {voice_id}")

#         # Get the existing record to check its chapter_id
#         existing_record = (
#             supabase.table("audio_generations")
#             .select("*")
#             .eq("id", record_id)
#             .single()
#             .execute()
#         )
#         if existing_record.data:
#             record_chapter_id = existing_record.data.get("chapter_id")
#             record_user_id = existing_record.data.get("user_id")
#             print(
#                 f"[DEBUG] Existing record chapter_id: {record_chapter_id}, user_id: {record_user_id}"
#             )
#             print(
#                 f"[DEBUG] Parameter vs Record chapter_id match: {chapter_id == record_chapter_id}"
#             )
#             # Use record's chapter_id if it exists and differs
#             if record_chapter_id and record_chapter_id != chapter_id:
#                 print(
#                     f"[WARNING] Chapter ID mismatch! Using record's chapter_id: {record_chapter_id} instead of parameter: {chapter_id}"
#                 )
#                 chapter_id = record_chapter_id
#         else:
#             print(f"[ERROR] Record {record_id} not found!")

#         # Update status to processing
#         supabase.table("audio_generations").update(
#             {"generation_status": "processing"}
#         ).eq("id", record_id).execute()

#         # Get user's subscription tier
#         subscription_response = (
#             supabase.table("user_subscriptions")
#             .select("tier")
#             .eq("user_id", user_id)
#             .eq("status", "active")
#             .execute()
#         )
#         user_tier = "free"  # Default to free
#         if subscription_response.data:
#             user_tier = subscription_response.data[0].get("tier", "free")

#         print(f"[DEBUG] User tier: {user_tier}")

#         # Choose service based on user tier and audio type
#         use_elevenlabs = user_tier == "pro" and audio_type in ["narrator", "character"]

#         if use_elevenlabs:
#             # Use ElevenLabs for voice generation (pro users only)
#             audio_service = ElevenLabsService(supabase_client=supabase)
#             result = audio_service.generate_enhanced_speech(
#                 text=text_content,
#                 voice_id=voice_id or "21m00Tcm4TlvDq8ikWAM",
#                 user_id=user_id,
#                 emotion=emotion,
#                 speed=speed,
#             )

#             if result and result.get("audio_url"):
#                 audio_url = result["audio_url"]
#                 audio_duration = None  # ElevenLabs doesn't return duration directly
#             else:
#                 raise Exception("Failed to generate audio with ElevenLabs")
#         else:
#             # Use ModelsLab for all audio types (free/basic users or non-voice audio)
#             audio_service = ModelsLabV7AudioService()

#             if audio_type in [
#                 "music",
#                 "sound_effect",
#                 "background_music",
#                 "sfx",
#                 "narrator",
#                 "character",
#             ]:
#                 if audio_type in ["narrator", "character"]:
#                     # Use TTS for voice
#                     result = asyncio.run(
#                         audio_service.generate_tts_audio(
#                             text=text_content,
#                             voice_id=voice_id or "en-US-Neural2-D",  # Default voice
#                             model_id="eleven_multilingual_v2",
#                             speed=speed,
#                         )
#                     )
#                 else:
#                     # Sound effects and music
#                     if audio_type == "music":
#                         result = asyncio.run(
#                             audio_service.generate_sound_effect(
#                                 description=text_content, duration=duration or 30.0
#                             )
#                         )
#                     else:
#                         result = asyncio.run(
#                             audio_service.generate_sound_effect(
#                                 description=text_content, duration=duration or 10.0
#                             )
#                         )

#                 if result.get("status") == "success":
#                     audio_url = result.get("audio_url")
#                     audio_duration = result.get("audio_time", duration)
#                 else:
#                     raise Exception(
#                         f"Failed to generate {audio_type}: {result.get('error', 'Unknown error')}"
#                     )
#             # Use ModelsLab for sound effects and music
#             audio_service = ModelsLabV7AudioService()

#             if audio_type == "music":
#                 # For music, we'd need a music generation service
#                 # For now, use sound effect as placeholder
#                 result = asyncio.run(
#                     audio_service.generate_sound_effect(
#                         description=text_content, duration=duration or 30.0
#                     )
#                 )
#             else:
#                 # Sound effects or ambiance
#                 result = asyncio.run(
#                     audio_service.generate_sound_effect(
#                         description=text_content, duration=duration or 10.0
#                     )
#                 )

#             if result.get("status") == "success":
#                 audio_url = result.get("audio_url")
#                 audio_duration = result.get("audio_time", duration)
#             else:
#                 raise Exception(
#                     f"Failed to generate {audio_type}: {result.get('error', 'Unknown error')}"
#                 )

#         # Update the record with success
#         update_data = {
#             "audio_url": audio_url,
#             "generation_status": "completed",
#             "duration": audio_duration,
#             "chapter_id": chapter_id,
#             "model_id": "elevenlabs" if use_elevenlabs else "modelslab",
#             "metadata": {
#                 "chapter_id": chapter_id,
#                 "scene_number": scene_number,
#                 "audio_type": audio_type,
#                 "voice_id": voice_id,
#                 "emotion": emotion,
#                 "speed": speed,
#                 "service_used": "elevenlabs" if use_elevenlabs else "modelslab",
#             },
#         }

#         supabase.table("audio_generations").update(update_data).eq(
#             "id", record_id
#         ).execute()

#         print(
#             f"[CHAPTER AUDIO] ✅ {audio_type} generation completed for chapter {chapter_id}"
#         )
#         return {"status": "success", "audio_url": audio_url, "record_id": record_id}

#     except Exception as e:
#         error_message = f"Chapter audio generation failed: {str(e)}"
#         print(f"[CHAPTER AUDIO ERROR] {error_message}")

#         # Update record with failure
#         supabase.table("audio_generations").update(
#             {"generation_status": "failed", "error_message": error_message}
#         ).eq("id", record_id).execute()

#         raise Exception(error_message)


# @celery_app.task(bind=True)
# def export_chapter_audio_mix_task(
#     self,
#     export_id: str,
#     chapter_id: str,
#     user_id: str,
#     audio_files: list,
#     export_format: str = "mp3",
#     mix_settings: dict = None,
# ):
#     """Export mixed audio for a chapter"""

#     from app.services.elevenlabs_service import ElevenLabsService
#     from app.core.database import get_supabase

#     supabase = get_supabase()

#     try:
#         print(f"[AUDIO EXPORT] Starting export for chapter {chapter_id}")

#         # Update export status to processing
#         supabase.table("audio_exports").update({"status": "processing"}).eq(
#             "id", export_id
#         ).execute()

#         # Prepare audio tracks for mixing
#         audio_tracks = []
#         for audio_file in audio_files:
#             if audio_file.get("audio_url"):
#                 track_info = {
#                     "url": audio_file["audio_url"],
#                     "type": audio_file.get("audio_type"),
#                     "volume": (
#                         mix_settings.get(f"{audio_file.get('audio_type')}_volume", 1.0)
#                         if mix_settings
#                         else 1.0
#                     ),
#                 }
#                 audio_tracks.append(track_info)

#         if not audio_tracks:
#             raise Exception("No valid audio tracks found for mixing")

#         # Use ElevenLabs service for mixing (it has mix_audio_tracks method)
#         audio_service = ElevenLabsService(supabase_client=supabase)
#         mix_result = audio_service.mix_audio_tracks(audio_tracks, user_id)

#         if mix_result and mix_result.get("audio_url"):
#             download_url = mix_result["audio_url"]

#             # Update export record with success
#             supabase.table("audio_exports").update(
#                 {"status": "completed", "download_url": download_url}
#             ).eq("id", export_id).execute()

#             print(f"[AUDIO EXPORT] ✅ Export completed for chapter {chapter_id}")
#             return {
#                 "status": "success",
#                 "download_url": download_url,
#                 "export_id": export_id,
#             }
#         else:
#             raise Exception("Failed to mix audio tracks")

#     except Exception as e:
#         error_message = f"Audio export failed: {str(e)}"
#         print(f"[AUDIO EXPORT ERROR] {error_message}")

#         # Update export record with failure
#         supabase.table("audio_exports").update(
#             {"status": "failed", "error_message": error_message}
#         ).eq("id", export_id).execute()

#         raise Exception(error_message)
