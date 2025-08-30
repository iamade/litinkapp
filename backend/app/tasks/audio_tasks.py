from celery import Celery
import asyncio
from typing import Dict, Any, List
from app.services.modelslab_audio_service import ModelsLabAudioService
from app.services.script_parser import ScriptParser
from app.core.database import get_supabase
from app.core.config import settings
from datetime import datetime
import json

celery_app = Celery('audio_tasks')

@celery_app.task(bind=True)
def generate_all_audio_for_video(self, video_generation_id: str):
    """Main task to generate all audio for a video generation"""
    
    try:
        print(f"[AUDIO GENERATION] Starting audio generation for video: {video_generation_id}")
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        script_data = video_gen.get('script_data', {})
        
        if not script_data:
            raise Exception("No script data found for audio generation")
        
        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'generating_audio'
        }).eq('id', video_generation_id).execute()
        
        # Parse script for audio components
        parser = ScriptParser()
        audio_components = parser.parse_script_for_audio(
            script_data.get('script', ''),
            script_data.get('characters', []),
            script_data.get('scene_descriptions', [])
        )
        
        print(f"[AUDIO PARSER] Extracted components:")
        print(f"- Narrator segments: {len(audio_components['narrator_segments'])}")
        print(f"- Character dialogues: {len(audio_components['character_dialogues'])}")
        print(f"- Sound effects: {len(audio_components['sound_effects'])}")
        print(f"- Background music: {len(audio_components['background_music'])}")
        
        # Generate all audio types
        audio_service = ModelsLabAudioService()
        
        # 1. Generate narrator voice
        narrator_results = asyncio.run(generate_narrator_audio(
            audio_service, video_generation_id, audio_components['narrator_segments']
        ))
        
        # 2. Generate character dialogues
        character_results = asyncio.run(generate_character_audio(
            audio_service, video_generation_id, audio_components['character_dialogues'], script_data.get('characters', [])
        ))
        
        # 3. Generate sound effects
        sound_effect_results = asyncio.run(generate_sound_effects(
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
        
        success_message = f"Audio generation completed! {total_audio_files} audio files created"
        print(f"[AUDIO GENERATION SUCCESS] {success_message}")
        
        # TODO: Send WebSocket update to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'audio_generation',
        #     'status': 'completed',
        #     'message': success_message,
        #     'progress': 100,
        #     'audio_files': total_audio_files
        # })
        
        # ✅ NEW: Trigger image generation after audio completion
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
        
        # Update status to failed
        try:
            supabase = get_supabase()
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message
            }).eq('id', video_generation_id).execute()
        except:
            pass
        
        # TODO: Send error to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'audio_generation',
        #     'status': 'failed',
        #     'message': error_message
        # })
        
        raise Exception(error_message)

async def generate_narrator_audio(
    audio_service: ModelsLabAudioService, 
    video_gen_id: str, 
    narrator_segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate narrator voice audio"""
    
    print(f"[NARRATOR AUDIO] Generating narrator voice...")
    narrator_results = []
    supabase = get_supabase()
    
    # Use consistent narrator voice
    narrator_voice = audio_service.narrator_voices[0]  # Default female narrator
    
    for i, segment in enumerate(narrator_segments):
        try:
            print(f"[NARRATOR AUDIO] Processing segment {i+1}/{len(narrator_segments)}")
            
            # Generate audio
            result = await audio_service.generate_tts_audio(
                text=segment['text'],
                voice_id=narrator_voice,
                speed=1.0,
                pitch=1.0
            )
            
            # Handle async response
            if result.get('status') == 'success':
                audio_url = result.get('output', [{}])[0].get('audio_url')
            else:
                # Wait for completion if async
                request_id = result.get('id')
                if request_id:
                    final_result = await audio_service.wait_for_completion(request_id)
                    audio_url = final_result.get('output', [{}])[0].get('audio_url')
                else:
                    raise Exception("Failed to get audio URL")
            
            # Estimate duration
            duration = ScriptParser().estimate_audio_duration(segment['text'])
            
            # Store in database
            audio_record = supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'narrator',
                'scene_id': f"scene_{segment['scene']}",
                'text_content': segment['text'],
                'voice_id': narrator_voice,
                'audio_url': audio_url,
                'duration_seconds': duration,
                'status': 'completed',
                'metadata': {
                    'line_number': segment['line_number'],
                    'service': 'modelslab'
                }
            }).execute()
            
            narrator_results.append({
                'id': audio_record.data[0]['id'],
                'scene': segment['scene'],
                'audio_url': audio_url,
                'duration': duration,
                'text': segment['text']
            })
            
            print(f"[NARRATOR AUDIO] ✅ Generated segment {i+1} - Duration: {duration:.1f}s")
            
        except Exception as e:
            print(f"[NARRATOR AUDIO] ❌ Failed segment {i+1}: {str(e)}")
            
            # Store failed record
            supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'narrator',
                'scene_id': f"scene_{segment['scene']}",
                'text_content': segment['text'],
                'voice_id': narrator_voice,
                'status': 'failed',
                'error_message': str(e)
            }).execute()
    
    print(f"[NARRATOR AUDIO] Completed: {len(narrator_results)}/{len(narrator_segments)} segments")
    return narrator_results

async def generate_character_audio(
    audio_service: ModelsLabAudioService,
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
            
            # Generate audio
            result = await audio_service.generate_tts_audio(
                text=dialogue['text'],
                voice_id=voice_id,
                speed=1.0,
                pitch=1.0
            )
            
            # Handle response
            if result.get('status') == 'success':
                audio_url = result.get('output', [{}])[0].get('audio_url')
            else:
                request_id = result.get('id')
                if request_id:
                    final_result = await audio_service.wait_for_completion(request_id)
                    audio_url = final_result.get('output', [{}])[0].get('audio_url')
                else:
                    raise Exception("Failed to get audio URL")
            
            duration = ScriptParser().estimate_audio_duration(dialogue['text'])
            
            # Store in database
            audio_record = supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'character',
                'scene_id': f"scene_{dialogue['scene']}",
                'character_name': character_name,
                'text_content': dialogue['text'],
                'voice_id': voice_id,
                'audio_url': audio_url,
                'duration_seconds': duration,
                'status': 'completed',
                'metadata': {
                    'line_number': dialogue['line_number'],
                    'service': 'modelslab'
                }
            }).execute()
            
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
            
            supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'character',
                'scene_id': f"scene_{dialogue['scene']}",
                'character_name': dialogue['character'],
                'text_content': dialogue['text'],
                'status': 'failed',
                'error_message': str(e)
            }).execute()
    
    unique_characters = len(set([d['character'] for d in character_dialogues]))
    print(f"[CHARACTER AUDIO] Completed: {len(character_results)} dialogues for {unique_characters} characters")
    return character_results

async def generate_sound_effects(
    audio_service: ModelsLabAudioService,
    video_gen_id: str,
    sound_effects: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate sound effects audio"""
    
    print(f"[SOUND EFFECTS] Generating sound effects...")
    sound_results = []
    supabase = get_supabase()
    
    for i, effect in enumerate(sound_effects):
        try:
            print(f"[SOUND EFFECTS] Processing effect {i+1}/{len(sound_effects)}: {effect['description']}")
            
            # Generate sound effect
            result = await audio_service.generate_sound_effect(
                description=effect['description'],
                duration=5.0  # Default 5 seconds
            )
            
            # Handle response
            if result.get('status') == 'success':
                audio_url = result.get('output', [{}])[0].get('audio_url')
            else:
                request_id = result.get('id')
                if request_id:
                    final_result = await audio_service.wait_for_completion(request_id)
                    audio_url = final_result.get('output', [{}])[0].get('audio_url')
                else:
                    raise Exception("Failed to get audio URL")
            
            # Store in database
            audio_record = supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'sound_effects',
                'scene_id': f"scene_{effect.get('scene', 1)}",
                'text_content': effect['description'],
                'audio_url': audio_url,
                'duration_seconds': 5.0,
                'status': 'completed',
                'metadata': {
                    'effect_type': effect.get('type', 'general'),
                    'line_number': effect.get('line_number'),
                    'service': 'modelslab'
                }
            }).execute()
            
            sound_results.append({
                'id': audio_record.data[0]['id'],
                'scene': effect.get('scene', 1),
                'audio_url': audio_url,
                'description': effect['description'],
                'duration': 5.0
            })
            
            print(f"[SOUND EFFECTS] ✅ Generated: {effect['description']}")
            
        except Exception as e:
            print(f"[SOUND EFFECTS] ❌ Failed: {effect['description']} - {str(e)}")
            
            supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'sound_effects',
                'scene_id': f"scene_{effect.get('scene', 1)}",
                'text_content': effect['description'],
                'status': 'failed',
                'error_message': str(e)
            }).execute()
    
    print(f"[SOUND EFFECTS] Completed: {len(sound_results)}/{len(sound_effects)} effects")
    return sound_results

async def generate_background_music(
    audio_service: ModelsLabAudioService,
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
            
            # Generate background music
            result = await audio_service.generate_sound_effect(
                description=music_cue['description'],
                duration=30.0  # Longer duration for background music
            )
            
            # Handle response
            if result.get('status') == 'success':
                audio_url = result.get('output', [{}])[0].get('audio_url')
            else:
                request_id = result.get('id')
                if request_id:
                    final_result = await audio_service.wait_for_completion(request_id)
                    audio_url = final_result.get('output', [{}])[0].get('audio_url')
                else:
                    raise Exception("Failed to get audio URL")
            
            # Store in database
            audio_record = supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'background_music',
                'scene_id': f"scene_{music_cue['scene']}",
                'text_content': music_cue['description'],
                'audio_url': audio_url,
                'duration_seconds': 30.0,
                'status': 'completed',
                'metadata': {
                    'music_type': music_cue.get('type', 'background_music'),
                    'scene': music_cue['scene'],
                    'service': 'modelslab'
                }
            }).execute()
            
            music_results.append({
                'id': audio_record.data[0]['id'],
                'scene': music_cue['scene'],
                'audio_url': audio_url,
                'description': music_cue['description'],
                'duration': 30.0
            })
            
            print(f"[BACKGROUND MUSIC] ✅ Generated for Scene {music_cue['scene']}")
            
        except Exception as e:
            print(f"[BACKGROUND MUSIC] ❌ Failed for Scene {music_cue['scene']}: {str(e)}")
            
            supabase.table('audio_generations').insert({
                'video_generation_id': video_gen_id,
                'audio_type': 'background_music',
                'scene_id': f"scene_{music_cue['scene']}",
                'text_content': music_cue['description'],
                'status': 'failed',
                'error_message': str(e)
            }).execute()
    
    print(f"[BACKGROUND MUSIC] Completed: {len(music_results)}/{len(music_cues)} music tracks")
    return music_results