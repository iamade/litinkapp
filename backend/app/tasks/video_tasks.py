from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional
from app.services.modelslab_image_service import ModelsLabImageService
from app.services.modelslab_video_service import ModelsLabVideoService
from app.services.video_service import VideoService
from app.core.database import get_supabase
import json

from app.services.modelslab_v7_video_service import ModelsLabV7VideoService


async def extract_scene_dialogue_and_generate_audio(
    video_gen_id: str,
    scene_id: str,
    scene_description: str,
    script_data: Dict[str, Any],
    user_id: str = None
) -> Dict[str, Any]:
    """Extract dialogue for a specific scene and generate audio"""

    try:
        # Get the full script from script_data
        script = script_data.get('script', '')
        if not script:
            print(f"[DIALOGUE EXTRACTION] No script found for video generation {video_gen_id}")
            return {'dialogue_audio': []}

        # Get scene descriptions for context
        scene_descriptions = script_data.get('scene_descriptions', [])

        # Initialize video service for dialogue extraction
        video_service = VideoService()

        # Extract dialogue per scene
        dialogue_data = await video_service.extract_dialogue_per_scene(
            script=script,
            scene_descriptions=scene_descriptions,
            user_id=user_id
        )

        # Get dialogue for this specific scene
        scene_number = int(scene_id.split('_')[1]) if '_' in scene_id else 1
        scene_dialogues = dialogue_data.get('scene_dialogues', {}).get(scene_number, [])
        scene_audio_files = dialogue_data.get('scene_audio_files', {}).get(scene_number, [])

        print(f"[DIALOGUE EXTRACTION] Scene {scene_number}: {len(scene_dialogues)} dialogues, {len(scene_audio_files)} audio files")

        # Store dialogue audio in database for tracking
        supabase = get_supabase()
        for audio_file in scene_audio_files:
            try:
                supabase.table('video_segments').insert({
                    'video_generation_id': video_gen_id,
                    'scene_id': scene_id,
                    'segment_index': scene_number,
                    'scene_description': scene_description,
                    'audio_url': audio_file.get('audio_url'),
                    'character_name': audio_file.get('character'),
                    'dialogue_text': audio_file.get('text'),
                    'generation_method': 'character_dialogue_audio',
                    'status': 'completed',
                    'processing_service': 'elevenlabs',
                    'metadata': {
                        'character_profile': audio_file.get('character_profile', {}),
                        'scene_number': scene_number,
                        'dialogue_type': 'character_voice'
                    }
                }).execute()
            except Exception as db_error:
                print(f"[DIALOGUE EXTRACTION] Error storing dialogue audio: {db_error}")

        return {
            'dialogue_audio': scene_audio_files,
            'dialogue_count': len(scene_dialogues),
            'audio_count': len(scene_audio_files),
            'scene_number': scene_number
        }

    except Exception as e:
        print(f"[DIALOGUE EXTRACTION] Error extracting dialogue for scene {scene_id}: {e}")
        return {
            'dialogue_audio': [],
            'error': str(e)
        }


# Update the service initialization in generate_all_videos_for_generation
async def generate_scene_videos(
    modelslab_service: ModelsLabV7VideoService,  # ✅ Updated type hint
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using V7 Veo 2 image-to-video"""
    
    print(f"[SCENE VIDEOS V7] Generating scene videos with Veo 2...")
    video_results = []
    supabase = get_supabase()
    
    scene_images = image_data.get('scenes', [])  # Updated to match V7 response format
    model_id = modelslab_service.get_video_model_for_style(video_style)
    
    for i, scene_description in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE VIDEOS V7] Processing {scene_id}/{len(scene_descriptions)}")
            
            # Find scene image
            scene_image = None
            if i < len(scene_images) and scene_images[i] is not None:
                scene_image = scene_images[i]
            
            if not scene_image or not scene_image.get('image_url'):
                print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                video_results.append(None)
                continue
            
            # Find audio for lip sync
            scene_audio = find_scene_audio(scene_id, audio_files)
            
            # ✅ Generate video using V7 Veo 2
            result = await modelslab_service.enhance_video_for_scene(
                scene_description=scene_description,
                image_url=scene_image['image_url'],
                audio_url=scene_audio.get('audio_url') if scene_audio else None,
                style=video_style,
                include_lipsync=bool(scene_audio)
            )
            
            if result.get('status') == 'success':
                enhanced_video = result.get('enhanced_video', {})
                video_url = enhanced_video.get('video_url')
                has_lipsync = enhanced_video.get('has_lipsync', False)
                
                if video_url:
                    # Store in database
                    video_record = supabase.table('video_segments').insert({
                        'video_generation_id': video_gen_id,
                        'scene_id': scene_id,
                        'segment_index': i + 1,
                        'scene_description': scene_description,
                        'source_image_url': scene_image['image_url'],
                        'video_url': video_url,
                        'duration_seconds': 5.0,  # Veo 2 default
                        'generation_method': 'veo2_image_to_video',
                        'status': 'completed',
                        'processing_service': 'modelslab_v7',
                        'processing_model': model_id,
                        'metadata': {
                            'model_id': model_id,
                            'video_style': video_style,
                            'service': 'modelslab_v7',
                            'has_lipsync': has_lipsync,
                            'veo2_enhanced': True
                        }
                    }).execute()
                    
                    video_results.append({
                        'id': video_record.data[0]['id'],
                        'scene_id': scene_id,
                        'video_url': video_url,
                        'duration': 5.0,
                        'source_image': scene_image['image_url'],
                        'method': 'veo2_image_to_video',
                        'model': model_id,
                        'has_lipsync': has_lipsync
                    })
                    
                    print(f"[SCENE VIDEOS V7] ✅ Generated {scene_id} - Lip sync: {has_lipsync}")
                else:
                    raise Exception("No video URL in V7 response")
            else:
                raise Exception(f"V7 Video generation failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"[SCENE VIDEOS V7] ❌ Failed {scene_id}: {str(e)}")
            
            # Store failed record
            try:
                supabase.table('video_segments').insert({
                    'video_generation_id': video_gen_id,
                    'scene_id': scene_id,
                    'segment_index': i + 1,
                    'scene_description': scene_description,
                    'generation_method': 'veo2_image_to_video',
                    'status': 'failed',
                    'error_message': str(e),
                    'processing_service': 'modelslab_v7',
                    'processing_model': model_id,
                    'metadata': {'service': 'modelslab_v7', 'veo2_enhanced': False}
                }).execute()
            except:
                pass
            
            video_results.append(None)
    
    successful_videos = len([r for r in video_results if r is not None])
    print(f"[SCENE VIDEOS V7] Completed: {successful_videos}/{len(scene_descriptions)} videos")
    return video_results

def find_scene_audio(scene_id: str, audio_files: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the primary audio file for a scene (for lip sync)"""
    
    # Priority: Character dialogue > Narrator > None
    character_audio = audio_files.get('characters', [])
    narrator_audio = audio_files.get('narrator', [])
    
    scene_number = int(scene_id.split('_')[1]) if '_' in scene_id else 1
    
    # Look for character dialogue first
    for audio in character_audio:
        if audio.get('scene') == scene_number and audio.get('audio_url'):
            return audio
    
    # Fall back to narrator audio
    for audio in narrator_audio:
        if audio.get('scene') == scene_number and audio.get('audio_url'):
            return audio
    
    return None

def update_pipeline_step(video_generation_id: str, step_name: str, status: str, error_message: str = None):
    """Update pipeline step status"""
    try:
        supabase = get_supabase()
        
        update_data = {
            'status': status,
            # ✅ FIX: Remove 'updated_at' field since it's not in schema
        }
        
        if status == 'processing':
            update_data['started_at'] = 'now()'
        elif status in ['completed', 'failed']:
            update_data['completed_at'] = 'now()'
            
        if error_message:
            update_data['error_message'] = error_message
            
        # ✅ FIX: Only update existing columns
        result = supabase.table('pipeline_steps').update(update_data).eq(
            'video_generation_id', video_generation_id
        ).eq('step_name', step_name).execute()
        
        print(f"[PIPELINE] Updated step {step_name} to {status}")
        
    except Exception as e:
        print(f"[PIPELINE] Error updating step {step_name}: {e}")

@celery_app.task(bind=True)
def generate_all_videos_for_generation(self, video_generation_id: str):
    """Main task to generate all videos for a video generation"""
    
    try:
        print(f"[VIDEO GENERATION] Starting video generation for: {video_generation_id}")
        
        # ✅ Update pipeline step to processing
        update_pipeline_step(video_generation_id, 'video_generation', 'processing')
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        user_id = video_gen.get('user_id')  # Get user_id from video generation record

        # Check if image generation is completed
        if video_gen.get('generation_status') != 'images_completed':
            raise Exception("Image generation must be completed before video generation")

        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'generating_video'
        }).eq('id', video_generation_id).execute()

        # Get script data and generated assets
        script_data = video_gen.get('script_data', {})
        audio_files = video_gen.get('audio_files', {})
        image_data = video_gen.get('image_data', {})

        scene_descriptions = script_data.get('scene_descriptions', [])
        video_style = script_data.get('video_style', 'realistic')
        
        print(f"[VIDEO GENERATION] Processing:")
        print(f"- Scenes: {len(scene_descriptions)}")
        print(f"- Video Style: {video_style}")
        print(f"- Audio Files: {len(audio_files.get('narrator', [])) + len(audio_files.get('characters', []))}")
        print(f"- Scene Images: {len(image_data.get('scene_images', []))}")
        
        # Generate videos
        modelslab_service = ModelsLabV7VideoService()

        # Generate scene videos sequentially with key scene shots
        video_results = asyncio.run(generate_scene_videos(
            modelslab_service, video_generation_id, scene_descriptions,
            audio_files, image_data, video_style, script_data, user_id
        ))
        
        # Compile results
        successful_videos = len([r for r in video_results if r is not None])
        total_scenes = len(scene_descriptions)
        success_rate = (successful_videos / total_scenes * 100) if total_scenes > 0 else 0
        
        # Calculate total video duration
        total_duration = sum([v.get('duration', 0) for v in video_results if v is not None])
        
        # Update video generation with video data
        video_data_result = {
            'scene_videos': video_results,
            'statistics': {
                'total_scenes': total_scenes,
                'videos_generated': successful_videos,
                'total_duration': total_duration,
                'success_rate': round(success_rate, 2)
            }
        }
        
        supabase.table('video_generations').update({
            'video_data': video_data_result,
            'generation_status': 'video_completed'
        }).eq('id', video_generation_id).execute()
        
        # ✅ Update pipeline step to completed
        update_pipeline_step(video_generation_id, 'video_generation', 'completed')
        
        success_message = f"Video generation completed! {successful_videos} videos created for {total_scenes} scenes"
        print(f"[VIDEO GENERATION SUCCESS] {success_message}")
        
        # Log detailed breakdown
        print(f"[VIDEO STATISTICS]")
        print(f"- Scene-by-scene generation status: {successful_videos}/{total_scenes}")
        print(f"- Total video duration: {total_duration:.1f} seconds")
        print(f"- Success rate: {success_rate:.1f}%")
        
        # ✅ Trigger audio/video merge after video completion
        print(f"[PIPELINE] Starting audio/video merge after video completion")
        from app.tasks.merge_tasks import merge_audio_video_for_generation
        merge_audio_video_for_generation.delay(video_generation_id)
        
        return {
            'status': 'success',
            'message': success_message + " - Starting audio/video merge...",
            'statistics': video_data_result['statistics'],
            'video_results': video_results,
            'next_step': 'audio_video_merge'
        }
        
    except Exception as e:
        error_message = f"Video generation failed: {str(e)}"
        print(f"[VIDEO GENERATION ERROR] {error_message}")
        
        # ✅ Update pipeline step to failed
        update_pipeline_step(video_generation_id, 'video_generation', 'failed', error_message)
        
        # Update status to failed
        try:
            supabase = get_supabase()
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message
            }).eq('id', video_generation_id).execute()
        except:
            pass
        
        raise Exception(error_message)
    
    
async def generate_scene_videos(
    modelslab_service: ModelsLabV7VideoService,  # ✅ Updated type hint
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str,
    script_data: Dict[str, Any] = None,
    user_id: str = None
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using V7 Veo 2 image-to-video with sequential processing and key scene shots"""

    print(f"[SCENE VIDEOS V7] Generating scene videos sequentially with key scene shots...")
    video_results = []
    supabase = get_supabase()

    scene_images = image_data.get('scenes', [])  # Updated to match V7 response format
    model_id = modelslab_service.get_video_model_for_style(video_style)

    # Track the previous scene's key scene shot for continuity
    previous_key_scene_shot = None

    for i, scene_description in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE VIDEOS V7] Processing {scene_id}/{len(scene_descriptions)} (Sequential)")

            # Determine the starting image for this scene
            starting_image_url = None

            if i == 0:
                # First scene: use the original scene image
                scene_image = None
                if i < len(scene_images) and scene_images[i] is not None:
                    scene_image = scene_images[i]

                if not scene_image or not scene_image.get('image_url'):
                    print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                    video_results.append(None)
                    continue

                starting_image_url = scene_image['image_url']
                print(f"[SCENE VIDEOS V7] Using original scene image for {scene_id}")
            else:
                # Subsequent scenes: use the previous scene's key scene shot
                if previous_key_scene_shot:
                    starting_image_url = previous_key_scene_shot
                    print(f"[SCENE VIDEOS V7] Using previous key scene shot for {scene_id}: {starting_image_url}")
                else:
                    # Fallback to original scene image if no previous key scene shot
                    scene_image = None
                    if i < len(scene_images) and scene_images[i] is not None:
                        scene_image = scene_images[i]

                    if scene_image and scene_image.get('image_url'):
                        starting_image_url = scene_image['image_url']
                        print(f"[SCENE VIDEOS V7] Using fallback scene image for {scene_id} (no previous key scene shot)")
                    else:
                        print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                        video_results.append(None)
                        continue

            # Extract dialogue for this scene and generate audio
            scene_dialogue_data = await extract_scene_dialogue_and_generate_audio(
                video_gen_id, scene_id, scene_description, script_data or {}, user_id
            )

            # Find audio for lip sync (legacy support)
            scene_audio = find_scene_audio(scene_id, audio_files)

            # ✅ Generate video using V7 Veo 2 with dialogue integration
            result = await modelslab_service.enhance_video_for_scene(
                scene_description=scene_description,
                image_url=starting_image_url,
                audio_url=scene_audio.get('audio_url') if scene_audio else None,
                dialogue_audio=scene_dialogue_data.get('dialogue_audio', []),
                style=video_style,
                include_lipsync=bool(scene_audio) or bool(scene_dialogue_data.get('dialogue_audio'))
            )

            if result.get('status') == 'success':
                enhanced_video = result.get('enhanced_video', {})
                video_url = enhanced_video.get('video_url')
                has_lipsync = enhanced_video.get('has_lipsync', False)

                if video_url:
                    # Extract the last frame as key scene shot for the next scene
                    key_scene_shot_url = None
                    try:
                        from app.services.video_service import VideoService
                        video_service = VideoService()
                        frame_filename = f"key_scene_shot_{video_gen_id}_{scene_id}.jpg"
                        key_scene_shot_url = await video_service.extract_last_frame_from_video(
                            video_url, frame_filename, user_id
                        )

                        if key_scene_shot_url:
                            print(f"[SCENE VIDEOS V7] ✅ Extracted key scene shot for {scene_id}: {key_scene_shot_url}")
                            previous_key_scene_shot = key_scene_shot_url  # Update for next scene
                        else:
                            print(f"[SCENE VIDEOS V7] ⚠️ Failed to extract key scene shot for {scene_id}")
                    except Exception as frame_error:
                        print(f"[SCENE VIDEOS V7] ⚠️ Error extracting key scene shot for {scene_id}: {frame_error}")

                    # Store in database
                    video_record = supabase.table('video_segments').insert({
                        'video_generation_id': video_gen_id,
                        'scene_id': scene_id,
                        'segment_index': i + 1,
                        'scene_description': scene_description,
                        'source_image_url': starting_image_url,
                        'video_url': video_url,
                        'key_scene_shot_url': key_scene_shot_url,
                        'duration_seconds': 5.0,  # Veo 2 default
                        'generation_method': 'veo2_image_to_video_sequential',
                        'status': 'completed',
                        'processing_service': 'modelslab_v7',
                        'processing_model': model_id,
                        'metadata': {
                            'model_id': model_id,
                            'video_style': video_style,
                            'service': 'modelslab_v7',
                            'has_lipsync': has_lipsync,
                            'veo2_enhanced': True,
                            'dialogue_audio_count': len(scene_dialogue_data.get('dialogue_audio', [])),
                            'character_dialogue_integrated': True,
                            'sequential_processing': True,
                            'scene_sequence': i + 1,
                            'used_previous_key_scene': i > 0,
                            'key_scene_extraction_success': key_scene_shot_url is not None
                        }
                    }).execute()

                    video_results.append({
                        'id': video_record.data[0]['id'],
                        'scene_id': scene_id,
                        'video_url': video_url,
                        'key_scene_shot_url': key_scene_shot_url,
                        'duration': 5.0,
                        'source_image': starting_image_url,
                        'method': 'veo2_image_to_video_sequential',
                        'model': model_id,
                        'has_lipsync': has_lipsync,
                        'scene_sequence': i + 1
                    })

                    print(f"[SCENE VIDEOS V7] ✅ Generated {scene_id} - Lip sync: {has_lipsync}, Key scene shot: {key_scene_shot_url is not None}")
                else:
                    raise Exception("No video URL in V7 response")
            else:
                raise Exception(f"V7 Video generation failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"[SCENE VIDEOS V7] ❌ Failed {scene_id}: {str(e)}")

            # Store failed record
            try:
                supabase.table('video_segments').insert({
                    'video_generation_id': video_gen_id,
                    'scene_id': scene_id,
                    'segment_index': i + 1,
                    'scene_description': scene_description,
                    'generation_method': 'veo2_image_to_video_sequential',
                    'status': 'failed',
                    'error_message': str(e),
                    'processing_service': 'modelslab_v7',
                    'processing_model': model_id,
                    'metadata': {
                        'service': 'modelslab_v7',
                        'veo2_enhanced': False,
                        'sequential_processing': True,
                        'scene_sequence': i + 1
                    }
                }).execute()
            except:
                pass

            video_results.append(None)

    successful_videos = len([r for r in video_results if r is not None])
    print(f"[SCENE VIDEOS V7] Sequential generation completed: {successful_videos}/{len(scene_descriptions)} videos")
    return video_results


async def generate_image_to_video_scene(
    modelslab_service: ModelsLabVideoService,
    video_gen_id: str,
    scene_id: str,
    scene_description: str,
    scene_image: Dict[str, Any],
    audio_files: Dict[str, Any],
    video_style: str,
    model_id: str
) -> Dict[str, Any]:
    """Generate video from scene image using image-to-video"""
    
    try:
        supabase = get_supabase()
        
        # Calculate video duration based on audio
        all_audio = (
            audio_files.get('narrator', []) + 
            audio_files.get('characters', []) + 
            audio_files.get('sound_effects', [])
        )
        video_duration = modelslab_service.calculate_video_duration_from_audio(all_audio, scene_id)
        
         # Generate video from image with retry logic for rate limiting
        max_retries = 3
        retry_delay = 30  # seconds
        
        for attempt in range(max_retries):
            try:
                result = await modelslab_service.generate_image_to_video(
                    image_url=scene_image['image_url'],
                    duration=video_duration,
                    motion_strength=0.8,
                    fps=24,
                    width=512,
                    height=288,
                    model_id=model_id
                )
                
                # Check for rate limiting
                if result.get('status') == 'error' and 'rate limit' in result.get('message', '').lower():
                    if attempt < max_retries - 1:
                        print(f"[VIDEO] Rate limited, waiting {retry_delay}s before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {max_retries} attempts")
                
                # Handle successful response
                if result.get('status') == 'success':
                    output = result.get('output', [])
                    if output:
                        video_url = output[0] if isinstance(output[0], str) else output[0].get('video_url')
                    else:
                        raise Exception("No video URL in success response")
                elif result.get('status') == 'processing':
                    # Wait for completion
                    request_id = result.get('id')
                    if request_id:
                        final_result = await modelslab_service.wait_for_completion(request_id)
                        output = final_result.get('output', [])
                        if output:
                            video_url = output[0] if isinstance(output[0], str) else output[0].get('video_url')
                        else:
                            raise Exception("No video URL after completion")
                    else:
                        raise Exception("No request ID for async processing")
                else:
                    raise Exception(f"API error: {result.get('message', 'Unknown error')}")
                
                break  # Success, exit retry loop
                
            except Exception as e:
                if attempt < max_retries - 1 and 'rate limit' in str(e).lower():
                    print(f"[VIDEO] Retry {attempt + 1}/{max_retries} failed: {e}")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise e
        
        if not video_url:
            raise Exception("No video URL returned from API")
        
        # Store in database
        video_record = supabase.table('video_segments').insert({
            'video_generation_id': video_gen_id,
            'scene_id': scene_id,
            'segment_index': int(scene_id.split('_')[1]) if '_' in scene_id else 1,
            'scene_description': scene_description,
            'source_image_url': scene_image['image_url'],
            'video_url': video_url,
            'fps': 24,
            'width': 512,
            'height': 288,
            'duration_seconds': video_duration,
            'generation_method': 'image_to_video',
            'status': 'completed',
            'processing_service': 'modelslab',
            'processing_model': model_id,
            'metadata': {
                'model_id': model_id,
                'video_style': video_style,
                'service': 'modelslab',
                'motion_strength': 0.8,
                'source_image_id': scene_image.get('id')
            }
        }).execute()
        
        return {
            'id': video_record.data[0]['id'],
            'scene_id': scene_id,
            'video_url': video_url,
            'duration': video_duration,
            'source_image': scene_image['image_url'],
            'method': 'image_to_video',
            'model': model_id
        }
        
    except Exception as e:
        print(f"[IMAGE_TO_VIDEO] ❌ Failed {scene_id}: {str(e)}")
        
        # Store failed record
        try:
            supabase.table('video_segments').insert({
                'video_generation_id': video_gen_id,
                'scene_id': scene_id,
                'segment_index': int(scene_id.split('_')[1]) if '_' in scene_id else 1,
                'scene_description': scene_description,
                'source_image_url': scene_image.get('image_url'),
                'generation_method': 'image_to_video',
                'status': 'failed',
                'error_message': str(e),
                'processing_service': 'modelslab',
                'processing_model': model_id,
                'metadata': {
                    'model_id': model_id,
                    'video_style': video_style,
                    'service': 'modelslab'
                }
            }).execute()
        except:
            pass
        
        return None

async def generate_text_to_video_scene(
    modelslab_service: ModelsLabVideoService,
    video_gen_id: str,
    scene_id: str,
    scene_description: str,
    audio_files: Dict[str, Any],
    video_style: str,
    model_id: str
) -> Dict[str, Any]:
    """Generate video from text description using text-to-video (fallback)"""
    
    try:
        supabase = get_supabase()
        
        # Calculate video duration based on audio
        all_audio = (
            audio_files.get('narrator', []) + 
            audio_files.get('characters', []) + 
            audio_files.get('sound_effects', [])
        )
        video_duration = modelslab_service.calculate_video_duration_from_audio(all_audio, scene_id)
        
        # Create video prompt
        video_prompt = create_video_prompt(scene_description, video_style)
        
        # Generate video from text
        result = await modelslab_service.generate_text_to_video(
            prompt=video_prompt,
            duration=video_duration,
            fps=24,
            width=512,
            height=288,
            model_id=model_id
        )
        
        # Handle response
        if result.get('status') == 'success':
            video_url = result.get('output', [{}])[0] if result.get('output') else None
            if isinstance(video_url, dict):
                video_url = video_url.get('url') or video_url.get('video_url')
        else:
            # Wait for completion if async
            request_id = result.get('id')
            if request_id:
                final_result = await modelslab_service.wait_for_completion(request_id, max_wait_time=600)  # 10 minutes
                output = final_result.get('output', [])
                video_url = output[0] if output else None
                if isinstance(video_url, dict):
                    video_url = video_url.get('url') or video_url.get('video_url')
            else:
                raise Exception("Failed to get video URL")
        
        if not video_url:
            raise Exception("No video URL returned from API")
        
        # Store in database
        video_record = supabase.table('video_segments').insert({
            'video_generation_id': video_gen_id,
            'scene_id': scene_id,
            'segment_index': int(scene_id.split('_')[1]) if '_' in scene_id else 1,  # ✅ Existing column
            'scene_description': scene_description,  # ✅ New column
            'video_url': video_url,
            'fps': 24,  # ✅ New column
            'width': 512,  # ✅ Existing column
            'height': 288,  # ✅ Existing column
            'duration_seconds': video_duration,
            'generation_method': 'text_to_video',  # ✅ New column
            'status': 'completed',
            'processing_service': 'modelslab',  # ✅ Existing column
            'processing_model': model_id,  # ✅ Existing column
            'metadata': {
                'model_id': model_id,
                'video_style': video_style,
                'service': 'modelslab',
                'video_prompt': video_prompt
            }
        }).execute()
        
        return {
            'id': video_record.data[0]['id'],
            'scene_id': scene_id,
            'video_url': video_url,
            'duration': video_duration,
            'prompt': video_prompt,
            'method': 'text_to_video',
            'model': model_id
        }
        
    except Exception as e:
        print(f"[TEXT_TO_VIDEO] ❌ Failed {scene_id}: {str(e)}")
        
        # Store failed record
        try:
             supabase.table('video_segments').insert({
                'video_generation_id': video_gen_id,
                'scene_id': scene_id,
                'segment_index': int(scene_id.split('_')[1]) if '_' in scene_id else 1,
                'scene_description': scene_description,
                'generation_method': 'text_to_video',
                'status': 'failed',
                'error_message': str(e),
                'processing_service': 'modelslab',
                'processing_model': model_id,
                'metadata': {
                    'model_id': model_id,
                    'video_style': video_style,
                    'service': 'modelslab'
                }
            }).execute()
        except:
            pass
        
        return None

def create_video_prompt(scene_description: str, style: str) -> str:
    """Create detailed prompt for video generation"""
    
    style_modifiers = {
        "realistic": "photorealistic video, natural movement, realistic physics",
        "cinematic": "cinematic video, dramatic movement, film-like motion",
        "animated": "animated video, stylized movement, cartoon animation",
        "fantasy": "fantasy video, magical movement, mystical atmosphere",
        "comic": "comic book style video, dynamic movement, superhero action",
        "artistic": "artistic video, creative movement, artistic motion"
    }
    
    base_prompt = f"Video scene: {scene_description}, "
    style_prompt = style_modifiers.get(style.lower(), style_modifiers["realistic"])
    technical_prompt = ", 24fps, smooth motion, high quality, 16:9 aspect ratio"
    
    return base_prompt + style_prompt + technical_prompt