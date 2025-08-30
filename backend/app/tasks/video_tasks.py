from app.core.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
from app.services.modelslab_service import ModelsLabService
from app.core.database import get_supabase
import json

@celery_app.task(bind=True)
def generate_all_videos_for_generation(self, video_generation_id: str):
    """Main task to generate all videos for a video generation"""
    
    try:
        print(f"[VIDEO GENERATION] Starting video generation for: {video_generation_id}")
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        
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
        modelslab_service = ModelsLabService()
        
        # Generate scene videos
        video_results = asyncio.run(generate_scene_videos(
            modelslab_service, video_generation_id, scene_descriptions, 
            audio_files, image_data, video_style
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
        
        success_message = f"Video generation completed! {successful_videos} videos created for {total_scenes} scenes"
        print(f"[VIDEO GENERATION SUCCESS] {success_message}")
        
        # Log detailed breakdown
        print(f"[VIDEO STATISTICS]")
        print(f"- Scene-by-scene generation status: {successful_videos}/{total_scenes}")
        print(f"- Total video duration: {total_duration:.1f} seconds")
        print(f"- Success rate: {success_rate:.1f}%")
        
        # ✅ NEW: Trigger audio/video merge after video completion
        print(f"[PIPELINE] Starting audio/video merge after video completion")
        from app.tasks.merge_tasks import merge_audio_video_for_generation
        merge_audio_video_for_generation.delay(video_generation_id)
        
        
        # TODO: Send WebSocket update to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'video_generation',
        #     'status': 'completed',
        #     'message': success_message,
        #     'progress': 100,
        #     'videos_generated': successful_videos,
        #     'statistics': video_data_result['statistics']
        # })
        
        return {
            'status': 'success',
            'message': success_message + " - Starting audio/video merge...",
            'statistics': video_data_result['statistics'],
            'video_results': video_results,
            'next_step': 'audio_video_merge'
        }
        
        # # APPROACH 2: Parallel (merge and lip sync simultaneously)
        # print(f"[PIPELINE] Starting audio/video merge and lip sync in parallel")
        # from app.tasks.merge_tasks import merge_audio_video_for_generation
        # from app.tasks.lipsync_tasks import apply_lip_sync_to_generation
        
        # # Start both tasks
        # merge_task = merge_audio_video_for_generation.delay(video_generation_id)
        # lipsync_task = apply_lip_sync_to_generation.delay(video_generation_id)
        
        # return {
        #     'status': 'success',
        #     'message': success_message + " - Starting merge and lip sync...",
        #     'statistics': video_data_result['statistics'],
        #     'video_results': video_results,
        #     'next_steps': ['audio_video_merge', 'lip_sync']
        # }
        
    except Exception as e:
        error_message = f"Video generation failed: {str(e)}"
        print(f"[VIDEO GENERATION ERROR] {error_message}")
        
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
        #     'step': 'video_generation',
        #     'status': 'failed',
        #     'message': error_message
        # })
        
        raise Exception(error_message)

async def generate_scene_videos(
    modelslab_service: ModelsLabService,
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using image-to-video"""
    
    print(f"[SCENE VIDEOS] Generating scene videos...")
    video_results = []
    supabase = get_supabase()
    
    scene_images = image_data.get('scene_images', [])
    model_id = modelslab_service.get_video_model_for_style(video_style)
    
    for i, scene_description in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE VIDEOS] Processing {scene_id}/{len(scene_descriptions)}")
            
            # Find corresponding scene image
            scene_image = None
            for img in scene_images:
                if img and img.get('scene_id') == scene_id:
                    scene_image = img
                    break
            
            if not scene_image:
                print(f"[SCENE VIDEOS] ⚠️ No image found for {scene_id}, using text-to-video")
                # Fall back to text-to-video if no image available
                video_result = await generate_text_to_video_scene(
                    modelslab_service, video_gen_id, scene_id, scene_description, 
                    audio_files, video_style, model_id
                )
            else:
                # Use image-to-video generation
                video_result = await generate_image_to_video_scene(
                    modelslab_service, video_gen_id, scene_id, scene_description,
                    scene_image, audio_files, video_style, model_id
                )
            
            video_results.append(video_result)
            
            if video_result:
                print(f"[SCENE VIDEOS] ✅ Generated {scene_id} - Duration: {video_result.get('duration', 0):.1f}s")
            else:
                print(f"[SCENE VIDEOS] ❌ Failed {scene_id}")
            
        except Exception as e:
            print(f"[SCENE VIDEOS] ❌ Failed {scene_id}: {str(e)}")
            video_results.append(None)
    
    successful_videos = len([r for r in video_results if r is not None])
    print(f"[SCENE VIDEOS] Completed: {successful_videos}/{len(scene_descriptions)} videos")
    return video_results

async def generate_image_to_video_scene(
    modelslab_service: ModelsLabService,
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
        
        # Generate video from image
        result = await modelslab_service.generate_image_to_video(
            image_url=scene_image['image_url'],
            duration=video_duration,
            motion_strength=0.8,
            fps=24,
            width=1024,
            height=576,
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
            'source_image_url': scene_image['image_url'],  # ✅ New column
            'video_url': video_url,
            # 'resolution': '1024x576',  # ❌ REMOVE - column doesn't exist
            'fps': 24,  # ✅ New column
            'width': 1024,  # ✅ Existing column
            'height': 576,  # ✅ Existing column
            'duration_seconds': video_duration,
            'generation_method': 'image_to_video',  # ✅ New column
            'status': 'completed',
            'processing_service': 'modelslab',  # ✅ Existing column
            'processing_model': model_id,  # ✅ Existing column
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
    modelslab_service: ModelsLabService,
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
            width=1024,
            height=576,
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
            # 'resolution': '1024x576',  # ❌ REMOVE - column doesn't exist
            'fps': 24,  # ✅ New column
            'width': 1024,  # ✅ Existing column
            'height': 576,  # ✅ Existing column
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