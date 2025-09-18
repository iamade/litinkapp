from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
# from app.services.modelslab_audio_service import ModelsLabAudioService
from app.services.script_parser import ScriptParser
from app.core.database import get_supabase
from app.core.config import settings
from datetime import datetime
from app.services.pipeline_manager import PipelineManager, PipelineStep
from app.services.modelslab_v7_audio_service import ModelsLabV7AudioService


# Add to imports
from app.services.pipeline_manager import PipelineManager, PipelineStep

@celery_app.task(bind=True)
def generate_all_audio_for_video(self, video_generation_id: str):
    """Main task to generate all audio for a video generation with pipeline support"""
    
    pipeline_manager = PipelineManager()
    
    try:
        print(f"[AUDIO GENERATION] Starting audio generation for video: {video_generation_id}")
        
        # Mark audio step as started
        pipeline_manager.mark_step_started(video_generation_id, PipelineStep.AUDIO_GENERATION)
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        script_data = video_gen.get('script_data', {})
        
        if not script_data:
            raise Exception("No script data found for audio generation")
        
        # ✅ NEW: Get script_style from the scripts table
        script_id = video_gen.get('script_id')
        script_style = 'cinematic_movie'  # Default fallback
        
        if script_id:
            try:
                script_response = supabase.table('scripts').select('script_style').eq('id', script_id).single().execute()
                if script_response.data:
                    script_style = script_response.data.get('script_style', 'cinematic_movie')
                    print(f"[SCRIPT STYLE] Fetched from scripts table: {script_style}")
                else:
                    print(f"[SCRIPT STYLE] Script {script_id} not found, using default: {script_style}")
            except Exception as e:
                print(f"[SCRIPT STYLE] Error fetching script style: {e}, using default: {script_style}")
        else:
            print(f"[SCRIPT STYLE] No script_id found, using default: {script_style}")
        
        
        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'generating_audio'
        }).eq('id', video_generation_id).execute()
        
        # Parse script for audio components
        parser = ScriptParser()
        audio_components = parser.parse_script_for_audio(
            script_data.get('script', ''),
            script_data.get('characters', []),
            script_data.get('scene_descriptions', []),
            script_style 
        )
        
        print(f"[AUDIO PARSER] Using script style: {script_style}")
        print(f"[AUDIO PARSER] Characters from script_data: {script_data.get('characters', [])}")
        print(f"[AUDIO PARSER] Script sample: {script_data.get('script', '')[:200]}...")
        print(f"[AUDIO PARSER] Extracted components:")
        print(f"- Narrator segments: {len(audio_components['narrator_segments'])}")
        print(f"- Character dialogues: {len(audio_components['character_dialogues'])}")
        print(f"- Sound effects: {len(audio_components['sound_effects'])}")
        print(f"- Background music: {len(audio_components['background_music'])}")
        
        # ✅ Add debug for character dialogues
        if audio_components['character_dialogues']:
            print(f"[CHARACTER DIALOGUES] Found:")
            for i, dialogue in enumerate(audio_components['character_dialogues'][:3]):
                print(f"  {i+1}. {dialogue.get('character', 'Unknown')}: {dialogue.get('text', '')[:50]}...")
        else:
            print(f"[CHARACTER DIALOGUES] ⚠️ No character dialogues found!")
            print(f"[DEBUG] Script style: {script_style}")
            print(f"[DEBUG] Characters available: {script_data.get('characters', [])}")
    
        # Generate all audio types
        audio_service = ModelsLabV7AudioService()
        
        # 1. Generate narrator voice
        narrator_results = asyncio.run(generate_narrator_audio(
            audio_service, video_generation_id, audio_components['narrator_segments']
        ))
        
        # 2. Generate character dialogues
        character_results = asyncio.run(generate_character_audio(
            audio_service, video_generation_id, audio_components['character_dialogues'], script_data.get('characters', [])
        ))
        
        # 3. Generate sound effects
        sound_effect_results = asyncio.run(generate_sound_effects_audio(
            audio_service, video_generation_id, audio_components['sound_effects']
        ))
        
        # 4. Generate background music
        background_music_results = asyncio.run(generate_background_music(
            audio_service, video_generation_id, audio_components['background_music']
        ))
        
        # Compile results
        total_audio_files = (
            len(narrator_results) + len(character_results) + 
            len(sound_effect_results) + len(background_music_results)
        )
        
        # Update video generation with audio file references
        audio_files_data = {
            'narrator': narrator_results,
            'characters': character_results,
            'sound_effects': sound_effect_results,
            'background_music': background_music_results
        }
        
        supabase.table('video_generations').update({
            'audio_files': audio_files_data,
            'generation_status': 'audio_completed'
        }).eq('id', video_generation_id).execute()
        
        # ✅ NEW: Mark step as completed
        pipeline_manager.mark_step_completed(
            video_generation_id, 
            PipelineStep.AUDIO_GENERATION, 
            {'total_audio_files': total_audio_files, 'audio_files_data': audio_files_data}
        )
        
        success_message = f"Audio generation completed! {total_audio_files} audio files created"
        print(f"[AUDIO GENERATION SUCCESS] {success_message}")
        
        # ✅ NEW: Trigger next step in pipeline
        print(f"[PIPELINE] Starting image generation after audio completion")
        from app.tasks.image_tasks import generate_all_images_for_video
        generate_all_images_for_video.delay(video_generation_id)
        
        return {
            'status': 'success',
            'message': success_message + " - Starting image generation...",
            'audio_files_count': total_audio_files,
            'audio_data': audio_files_data,
            'next_step': 'image_generation'
        }
        
    except Exception as e:
        error_message = f"Audio generation failed: {str(e)}"
        print(f"[AUDIO GENERATION ERROR] {error_message}")
        
        # ✅ NEW: Mark step as failed
        pipeline_manager.mark_step_failed(video_generation_id, PipelineStep.AUDIO_GENERATION, error_message)
        
        # Update status to failed
        try:
            supabase = get_supabase()
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message,
                'can_resume': True,  # ✅ Add this
                'failed_at_step': 'audio_generation'  # ✅ Add this
            }).eq('id', video_generation_id).execute()
        except:
            pass
        
        raise Exception(error_message)



async def generate_narrator_audio(
    audio_service: ModelsLabV7AudioService, 
    video_gen_id: str, 
    narrator_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate narrator voice audio"""
    
    print(f"[NARRATOR AUDIO] Generating narrator voice...")
    narrator_results = []
    supabase = get_supabase()
    
    # ✅ Use V7 service voice mapping
    narrator_voice = audio_service.character_voices['narrator']  # Professional narrator voice
    
    for i, segment in enumerate(narrator_segments):
        try:
            print(f"[NARRATOR AUDIO] Processing segment {i+1}/{len(narrator_segments)}")
            
            # Generate audio
            result = await audio_service.generate_tts_audio(
                text=segment['text'],
                voice_id=narrator_voice,
                model_id="eleven_multilingual_v2",  # ✅ V7 specific model
                speed=1.0
            )
            
            # ✅ FIXED: Extract audio URL from correct response structure
            audio_url = None
            duration = 0
            
            if result.get('status') == 'success':
                audio_url = result.get('audio_url')
                duration = result.get('audio_time', 0)
                
                if not audio_url:
                    raise Exception("No audio URL in V7 response")
            else:
                raise Exception(f"V7 Audio generation failed: {result.get('error', 'Unknown error')}")
            
            # ✅ FIXED: Use correct column names for database
            audio_record_data = {
                'video_generation_id': video_gen_id,
                'audio_type': 'narrator',
                'text_content': segment['text'],
                'voice_id': narrator_voice,
                'audio_url': audio_url,
                'duration': float(duration),  # ✅ Use 'duration' (check your schema)
                'status': 'completed',  # ✅ Use 'status' (check your schema)
                'sequence_order': i + 1,
                'model_id': result.get('model_used', 'eleven_multilingual_v2'),  # ✅ Add model_id
                'metadata': {
                    'line_number': segment.get('line_number', i + 1),
                    'scene': segment.get('scene', 1),
                    'service': 'modelslab_v7',  # ✅ Updated service name
                    'model_used': result.get('model_used', 'eleven_multilingual_v2')
                }
            }
            
            # Insert to database
            audio_record = supabase.table('audio_generations').insert(audio_record_data).execute()
            
            narrator_results.append({
                'id': audio_record.data[0]['id'],
                'scene': segment.get('scene', 1),
                'audio_url': audio_url,
                'duration': duration,
                'text': segment['text']
            })
            
            print(f"[NARRATOR AUDIO] ✅ Generated segment {i+1} - Duration: {duration}s")
            
        except Exception as e:
            print(f"[NARRATOR AUDIO] ❌ Failed segment {i+1}: {str(e)}")
            
            # ✅ FIXED: Use correct column names for failed records
            failed_record_data = {
                'video_generation_id': video_gen_id,
                'audio_type': 'narrator',
                'text_content': segment['text'],
                'voice_id': narrator_voice,
                'status': 'failed',  # ✅ Use 'status'
                'error_message': str(e),
                'sequence_order': i + 1,
                'model_id': 'eleven_multilingual_v2',  # ✅ Add model_id
                'metadata': {
                    'line_number': segment.get('line_number', i + 1),
                    'scene': segment.get('scene', 1),
                    'service': 'modelslab_v7'
                }
            }
            supabase.table('audio_generations').insert(failed_record_data).execute()
    
    print(f"[NARRATOR AUDIO] Completed: {len(narrator_results)}/{len(narrator_segments)} segments")
    return narrator_results

async def generate_sound_effects_audio(
    audio_service: ModelsLabV7AudioService,  # ✅ Updated type hint
    video_gen_id: str, 
    sound_effects: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate sound effects audio"""
    
    print(f"[SOUND EFFECTS] Generating sound effects...")
    effects_results = []
    supabase = get_supabase()
    
    for i, effect in enumerate(sound_effects):
        try:
            print(f"[SOUND EFFECTS] Processing effect {i+1}/{len(sound_effects)}: {effect['description']}")
            
            # ✅ Use V7 sound effects generation
            result = await audio_service.generate_sound_effect(
                description=effect['description'],
                duration=min(30.0, max(3.0, effect.get('duration', 10.0))),  # V7 limits
                model_id="eleven_sound_effect"
            )
            
            if result.get('status') == 'success':
                audio_url = result.get('audio_url')
                duration = result.get('audio_time', 10)
                
                if not audio_url:
                    raise Exception("No audio URL in V7 response")
                    
                # Store in database
                audio_data = {
                    'video_generation_id': video_gen_id,
                    'audio_type': 'sfx',
                    'text_content': effect['description'],
                    'audio_url': audio_url,
                    'duration': float(duration),
                    'sequence_order': i + 1,
                    'generation_status': 'completed',
                    'metadata': {
                        'effect_type': 'ambient',
                        'service': 'modelslab_v7',
                        'model_used': result.get('model_used', 'eleven_sound_effect')
                    }
                }
                
                db_result = supabase.table('audio_generations').insert(audio_data).execute()
                
                effects_results.append({
                    'effect_id': i + 1,
                    'audio_url': audio_url,
                    'description': effect['description'],
                    'duration': duration,
                    'db_id': db_result.data[0]['id'] if db_result.data else None
                })
                
                print(f"[SOUND EFFECTS] ✅ Effect {i+1} completed: {audio_url}")
            else:
                raise Exception(f"V7 API returned error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"[SOUND EFFECTS] ❌ Failed: {effect['description']} - {str(e)}")
            
            # Store failed record
            failed_audio_data = {
                'video_generation_id': video_gen_id,
                'audio_type': 'sfx',
                'text_content': effect['description'],
                'error_message': str(e),
                'sequence_order': i + 1,
                'generation_status': 'failed',
                'metadata': {'service': 'modelslab_v7'}
            }
            supabase.table('audio_generations').insert(failed_audio_data).execute()
            continue
    
    print(f"[SOUND EFFECTS] Completed: {len(effects_results)}/{len(sound_effects)} effects")
    return effects_results



async def generate_character_audio(
    audio_service: ModelsLabV7AudioService,
    video_gen_id: str,
    character_dialogues: List[Dict[str, Any]],
    characters: List[str]
) -> List[Dict[str, Any]]:
    """Generate character dialogue audio"""
    
    print(f"[CHARACTER AUDIO] Generating character voices...")
    character_results = []
    supabase = get_supabase()
    
    # Create voice mapping for characters
    character_voice_map = {}
    for character in characters:
        voice_id = audio_service.assign_character_voice(character)
        character_voice_map[character.upper()] = voice_id
        print(f"[CHARACTER VOICE] {character} -> {voice_id}")
    
    for i, dialogue in enumerate(character_dialogues):
        try:
            character_name = dialogue['character'].upper()
            voice_id = character_voice_map.get(character_name, audio_service.character_voices['male_adult'])
            
            print(f"[CHARACTER AUDIO] Processing {character_name} dialogue {i+1}/{len(character_dialogues)}")
            
            # ✅ FIX: Use correct emotion parameter
            result = await audio_service.generate_tts_audio(
                text=dialogue['text'],
                voice_id=voice_id,
                speed=1.0,
                model_id="eleven_multilingual_v2",
            )
            
            # ✅ FIXED: Extract audio URL from correct response structure
            audio_url = None
            duration = 0
            
            if result.get('status') == 'success':
                audio_url = result.get('audio_url')
                duration = result.get('audio_time', 0)
                
                if not audio_url:
                    raise Exception("No audio URL in V7 response")
            else:
                raise Exception(f"V7 Audio generation failed: {result.get('error', 'Unknown error')}")
            
            # ✅ FIXED: Use correct column names for database
            audio_record_data = {
                'video_generation_id': video_gen_id,
                'audio_type': 'character',
                'text_content': dialogue['text'],
                'voice_id': voice_id,
                'audio_url': audio_url,
                'duration': float(duration),  # Use 'duration' not 'duration_seconds'
                'generation_status': 'completed',  # Use 'generation_status' not 'status'
                'sequence_order': i + 1,
                'metadata': {
                    'character': character_name,
                    'line_number': dialogue.get('line_number', i + 1),
                    'scene': dialogue.get('scene', 1),
                    'service': 'modelslab_v7',
                    'model_used': result.get('model_used', 'eleven_multilingual_v2')
                }
            }
            
            # Insert to database
            audio_record = supabase.table('audio_generations').insert(audio_record_data).execute()
            
            character_results.append({
                'id': audio_record.data[0]['id'],
                'character': character_name,
                'scene': dialogue['scene'],
                'audio_url': audio_url,
                'duration': duration,
                'text': dialogue['text']
            })
            
            print(f"[CHARACTER AUDIO] ✅ Generated {character_name} dialogue - Duration: {duration:.1f}s")
            
        except Exception as e:
            print(f"[CHARACTER AUDIO] ❌ Failed {dialogue['character']} dialogue {i+1}: {str(e)}")
            
            # ✅ FIXED: Use correct column names for failed records
            failed_record_data = {
                'video_generation_id': video_gen_id,
                'audio_type': 'character',
                'text_content': dialogue['text'],
                'voice_id': voice_id,
                'generation_status': 'failed',
                'error_message': str(e),
                'sequence_order': i + 1,
                'metadata': {
                    'character': dialogue['character'],
                    'line_number': dialogue.get('line_number', i + 1),
                    'scene': dialogue.get('scene', 1),
                    'service': 'modelslab_v7'
                }
            }
            supabase.table('audio_generations').insert(failed_record_data).execute()
    
    unique_characters = len(set([d['character'] for d in character_dialogues]))
    print(f"[CHARACTER AUDIO] Completed: {len(character_results)} dialogues for {unique_characters} characters")
    return character_results

async def generate_background_music(
    audio_service: ModelsLabV7AudioService,  # ✅ Updated type hint
    video_gen_id: str,
    music_cues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate background music"""
    
    print(f"[BACKGROUND MUSIC] Generating background music...")
    music_results = []
    supabase = get_supabase()
    
    for i, music_cue in enumerate(music_cues):
        try:
            print(f"[BACKGROUND MUSIC] Processing scene {music_cue['scene']}: {music_cue['description']}")
            
            # ✅ Use V7 music generation
            result = await audio_service.generate_background_music(
                description=music_cue['description'],
                model_id="music_v1",
                duration=30.0  # V7 music generation duration
            )
            
            if result.get('status') == 'success':
                audio_url = result.get('audio_url')
                duration = result.get('audio_time', 30.0)
                
                if not audio_url:
                    raise Exception("No audio URL in V7 response")
                    
                # Store in database
                audio_record = supabase.table('audio_generations').insert({
                    'video_generation_id': video_gen_id,
                    'audio_type': 'music',
                    'text_content': music_cue['description'],
                    'audio_url': audio_url,
                    'duration': float(duration),
                    'generation_status': 'completed',
                    'sequence_order': i + 1,
                    'metadata': {
                        'music_type': music_cue.get('type', 'background_music'),
                        'scene': music_cue['scene'],
                        'service': 'modelslab_v7',
                        'model_used': result.get('model_used', 'music_v1')
                    }
                }).execute()
                
                music_results.append({
                    'id': audio_record.data[0]['id'],
                    'scene': music_cue['scene'],
                    'audio_url': audio_url,
                    'description': music_cue['description'],
                    'duration': duration
                })
                
                print(f"[BACKGROUND MUSIC] ✅ Generated for Scene {music_cue['scene']}")
            else:
                raise Exception(f"V7 API returned error: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"[BACKGROUND MUSIC] ❌ Failed for Scene {music_cue['scene']}: {str(e)}")
            
            # Store failed record
            supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'music',
                'text_content': music_cue['description'],
                'generation_status': 'failed',
                'error_message': str(e),
                'sequence_order': i + 1,
                'metadata': {'service': 'modelslab_v7'}
            }).execute()
    
    print(f"[BACKGROUND MUSIC] Completed: {len(music_results)}/{len(music_cues)} music tracks")
    return music_results


