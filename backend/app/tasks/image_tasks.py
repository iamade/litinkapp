from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional
from app.core.database import get_supabase
import json
import logging

from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
from app.services.modelslab_image_service import ModelsLabImageService
from app.core.database import get_supabase
from app.services.pipeline_manager import PipelineManager, PipelineStep
from app.services.modelslab_v7_image_service import ModelsLabV7ImageService
from app.services.standalone_image_service import StandaloneImageService
from app.services.subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_all_images_for_video(self, video_generation_id: str):
    """Main task to generate all images for a video generation with pipeline support"""
    
    pipeline_manager = PipelineManager()
    
    try:
        print(f"[IMAGE GENERATION] Starting image generation for video: {video_generation_id}")
        
        # Mark image step as started
        pipeline_manager.mark_step_started(video_generation_id, PipelineStep.IMAGE_GENERATION)
        
        # Get video generation data
        supabase = get_supabase()
        video_response = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_response.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_response.data
        user_id = video_gen.get('user_id')

        if not user_id:
            raise Exception(f"Video generation {video_generation_id} has no user_id")

        # Get user tier for model selection
        subscription_manager = SubscriptionManager(supabase)
        usage_check = asyncio.run(subscription_manager.check_usage_limits(user_id, "image"))
        user_tier = usage_check["tier"]

        print(f"[IMAGE GENERATION] User {user_id} has {user_tier} tier - will use tier-based model selection")

        # ✅ FIXED: Proper validation of existing images
        existing_image_data = video_gen.get('image_data') or {}
        existing_character_images = existing_image_data.get('character_images') or []
        existing_scene_images = existing_image_data.get('scene_images') or []
        
        # Count ACTUAL successful images with URLs
        successful_character_count = len([img for img in existing_character_images if img and img.get('image_url')])
        successful_scene_count = len([img for img in existing_scene_images if img and img.get('image_url')])
        
        # Get script data to know how many images we need
        script_data = video_gen.get('script_data') or {}
        scene_descriptions = script_data.get('scene_descriptions') or []
        characters = script_data.get('characters') or []
        video_style = script_data.get('video_style', 'realistic')
        
        needed_character_images = len(characters)
        needed_scene_images = len(scene_descriptions)
        
        # ✅ FIXED: Only skip if we have ALL needed successful images
        if (successful_character_count >= needed_character_images and 
            successful_scene_count >= needed_scene_images and
            needed_character_images > 0 and needed_scene_images > 0):
            
            print(f"[IMAGE GENERATION] ✅ All images already exist and are valid:")
            print(f"  - Character images: {successful_character_count}/{needed_character_images}")
            print(f"  - Scene images: {successful_scene_count}/{needed_scene_images}")
            print(f"[IMAGE GENERATION] Skipping generation and proceeding to next step")
            
            # Mark as completed and move to next step
            pipeline_manager.mark_step_completed(
                video_generation_id, 
                PipelineStep.IMAGE_GENERATION, 
                {'message': 'All images already existed', 'image_data': existing_image_data}
            )
            
            # Update status and trigger next step
            supabase.table('video_generations').update({
                'generation_status': 'images_completed'
            }).eq('id', video_generation_id).execute()
            
            # Trigger next step
            print(f"[PIPELINE] Starting video generation after image skip")
            from app.tasks.video_tasks import generate_all_videos_for_generation
            generate_all_videos_for_generation.delay(video_generation_id)
            
            return {
                'status': 'success',
                'message': 'All images already existed - skipped to video generation',
                'existing_images': True,
                'character_images_count': successful_character_count,
                'scene_images_count': successful_scene_count,
                'next_step': 'video_generation'
            }
        
        # ✅ NEW: Clear partial/failed image data before regenerating
        if existing_character_images or existing_scene_images:
            print(f"[IMAGE GENERATION] ⚠️ Found incomplete image data:")
            print(f"  - Character images: {successful_character_count}/{needed_character_images} valid")
            print(f"  - Scene images: {successful_scene_count}/{needed_scene_images} valid")
            print(f"[IMAGE GENERATION] Clearing partial data and regenerating all images")
            
            # Clear the partial data
            supabase.table('video_generations').update({
                'image_data': None  # Clear existing partial data
            }).eq('id', video_generation_id).execute()
        
        # Check if audio generation is completed (unless we're in retry mode)
        current_status = video_gen.get('generation_status')
        if current_status not in ['generating_images', 'retrying'] and current_status != 'audio_completed':
            raise Exception(f"Audio generation must be completed before image generation. Current status: {current_status}")
        
        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'generating_images'
        }).eq('id', video_generation_id).execute()
        
        print(f"[IMAGE GENERATION] Processing:")
        print(f"- Characters: {len(characters)}")
        print(f"- Scenes: {len(scene_descriptions)}")
        print(f"- Video Style: {video_style}")
        
        if not scene_descriptions and not characters:
            raise Exception("No scene descriptions or characters found in script data")
        
        # ✅ FIXED: Generate images using asyncio.run() instead of await
        image_service = ModelsLabV7ImageService()
        
        # 1. Generate character reference images
        character_images = []
        if characters:
            print(f"[IMAGE GENERATION] Generating {len(characters)} character images...")
            character_images = asyncio.run(generate_character_images_optimized(
                image_service, video_generation_id, characters, video_style, user_tier
            ))
        
        # 2. Generate scene images
        scene_images = []
        if scene_descriptions:
            print(f"[IMAGE GENERATION] Generating {len(scene_descriptions)} scene images...")
            scene_images = asyncio.run(generate_scene_images_optimized(
            # scene_images = asyncio.run(generate_scene_images(
                image_service, video_generation_id, scene_descriptions, video_style, user_tier
            ))
        
        # Compile results
        successful_character_images = len([img for img in character_images if img is not None])
        successful_scene_images = len([img for img in scene_images if img is not None])
        total_images = successful_character_images + successful_scene_images
        total_needed = len(characters) + len(scene_descriptions)
        
        success_rate = (total_images / total_needed * 100) if total_needed > 0 else 0
        
        # ✅ CRITICAL: Ensure we have some successful images before proceeding
        if total_images == 0:
            raise Exception(f"No images were successfully generated! Character: {successful_character_images}, Scene: {successful_scene_images}")
        
        # Update video generation with image data
        image_data = {
            'character_images': character_images,
            'scene_images': scene_images,
            'statistics': {
                'total_scenes': len(scene_descriptions),
                'total_characters': len(characters),
                'images_needed_per_scene': 1,
                'character_images_generated': successful_character_images,
                'scene_images_generated': successful_scene_images,
                'total_images_generated': total_images,
                'success_rate': round(success_rate, 1)
            }
        }
        
        print(f"[IMAGE DEBUG] Final image_data structure:")
        print(f"  - Character images: {len(character_images)} items ({successful_character_images} successful)")
        print(f"  - Scene images: {len(scene_images)} items ({successful_scene_images} successful)")
        
        # Debug scene images specifically
        for i, img in enumerate(scene_images):
            if img:
                print(f"  - Scene {i+1}: scene_id={img.get('scene_id')}, has_url={bool(img.get('image_url'))}, url={img.get('image_url', 'NO_URL')[:50]}...")
            else:
                print(f"  - Scene {i+1}: NULL/FAILED")
        
        supabase.table('video_generations').update({
            'image_data': image_data,
            'generation_status': 'images_completed'
        }).eq('id', video_generation_id).execute()

        # Mark step as completed
        pipeline_manager.mark_step_completed(
            video_generation_id, 
            PipelineStep.IMAGE_GENERATION, 
            {'total_images': total_images, 'image_data': image_data}
        )
        
        success_message = f"Image generation completed! {total_images} images created ({successful_character_images} characters, {successful_scene_images} scenes)"
        print(f"[IMAGE GENERATION SUCCESS] {success_message}")
        
        # Log statistics
        print(f"[IMAGE STATISTICS]")
        print(f"- Total characters: {len(characters)}")
        print(f"- Total scenes in script: {len(scene_descriptions)}")
        print(f"- Character images generated: {successful_character_images}/{len(characters)}")
        print(f"- Scene images generated: {successful_scene_images}/{len(scene_descriptions)}")
        print(f"- Success rate: {success_rate:.1f}%")
        
        # For split workflow, video generation starts independently
        # Image generation completion doesn't trigger video generation anymore

        return {
            'status': 'success',
            'message': success_message,
            'statistics': image_data['statistics'],
            'character_images': character_images,
            'scene_images': scene_images
        }
        
    except Exception as e:
        error_message = f"Image generation failed: {str(e)}"
        print(f"[IMAGE GENERATION ERROR] {error_message}")
        
        # Mark step as failed
        try:
            pipeline_manager.mark_step_failed(video_generation_id, PipelineStep.IMAGE_GENERATION, error_message)
        except Exception as pm_error:
            print(f"[PIPELINE] Warning - Failed to mark step failed: {pm_error}")
        
        # Update status to failed
        try:
            supabase = get_supabase()
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message,
                'can_resume': True,
                'failed_at_step': 'image_generation'
            }).eq('id', video_generation_id).execute()
        except Exception as db_error:
            print(f"[IMAGE GENERATION] Database update error: {str(db_error)}")
        
        raise Exception(error_message)
    
# ✅ NEW: Optimized async function for character images  
async def generate_character_images_optimized(
    image_service: ModelsLabV7ImageService,
    video_gen_id: str,
    characters: List[str],
    style: str = "realistic",
    user_tier: str = "free"
) -> List[Dict[str, Any]]:
    """Generate character images with optimizations"""
    
    print(f"[CHARACTER IMAGES OPTIMIZED] Generating images for {len(characters)} characters...")
    character_results = []
    supabase = get_supabase()
    
    for i, character in enumerate(characters):
        try:
            print(f"[CHARACTER IMAGE {i+1}] Processing: {character}")
            
            character_description = f"Detailed character portrait, {style} style, expressive features"
            
            result = await image_service.generate_character_image(
                character_name=character,
                character_description=character_description,
                style=style,
                aspect_ratio="3:4",
                user_tier=user_tier
            )
            
            if result.get('status') == 'success':
                image_url = result.get('image_url')
                
                if not image_url:
                    raise Exception("No image URL in V7 response")
                
                # Store in database
                image_record_data = {
                    'video_generation_id': video_gen_id,
                    'image_type': 'character',
                    'prompt': f"Character: {character}, {character_description}",
                    'image_url': image_url,
                    'character_name': character,
                    'style': style,
                    'status': 'completed',
                    'sequence_order': i + 1,
                    'model_id': result.get('model_used', 'gen4_image'),
                    'aspect_ratio': '3:4',
                    'service_provider': 'modelslab_v7',
                    'generation_time_seconds': result.get('generation_time', 0),
                    'metadata': {
                        'service': 'modelslab_v7',
                        'model_used': result.get('model_used', 'gen4_image'),
                        'generation_time': result.get('generation_time', 0)
                    }
                }
                
                db_result = supabase.table('image_generations').insert(image_record_data).execute()
                
                character_results.append({
                    'id': db_result.data[0]['id'] if db_result.data else None,
                    'character': character,
                    'image_url': image_url,
                    'style': style,
                    'status': 'success'
                })
                
                print(f"[CHARACTER IMAGE {i+1}] ✅ Success: {character}")
                
            else:
                raise Exception(f"V7 Image generation failed: {result.get('error', 'Unknown error')}")
            
            # Brief pause between requests
            await asyncio.sleep(1)
                
        except Exception as e:
            print(f"[CHARACTER IMAGE {i+1}] ❌ Failed {character}: {str(e)}")
            
            # Store failed record
            failed_record_data = {
                'video_generation_id': video_gen_id,
                'image_type': 'character',
                'character_name': character,
                'style': style,
                'status': 'failed',
                'error_message': str(e),
                'sequence_order': i + 1,
                'prompt': f"Character: {character}, {character_description}",
                'model_id': 'gen4_image',
                'aspect_ratio': '3:4',
                'service_provider': 'modelslab_v7',
                'metadata': {'service': 'modelslab_v7', 'error': str(e)}
            }
            supabase.table('image_generations').insert(failed_record_data).execute()
            
            character_results.append({
                'character': character,
                'status': 'failed',
                'error': str(e)
            })
    
    successful_count = len([r for r in character_results if r.get('status') == 'success'])
    print(f"[CHARACTER IMAGES OPTIMIZED] Completed: {successful_count}/{len(characters)} characters")
    return character_results


async def generate_scene_images_optimized(
    image_service: ModelsLabV7ImageService,
    video_gen_id: str,
    scene_descriptions: List[Dict[str, Any]],
    style: str = "cinematic",
    user_tier: str = "free"
) -> List[Dict[str, Any]]:
    """Generate scene images sequentially with optimizations"""
    
    print(f"[SCENE IMAGES OPTIMIZED] Generating images for {len(scene_descriptions)} scenes...")
    scene_results = []
    supabase = get_supabase()
    
    for i, scene in enumerate(scene_descriptions):
        try:
            # Handle different scene description formats
            if isinstance(scene, dict):
                scene_text = scene.get('description', scene.get('text', str(scene)))
                scene_number = scene.get('scene_number', i + 1)
            else:
                scene_text = str(scene)
                scene_number = i + 1
            
            print(f"[SCENE IMAGE {i+1}] Processing: {scene_text[:50]}...")
            
            # ✅ OPTIMIZATION: Try with shorter timeout first
            result = await image_service.generate_scene_image(
                scene_description=scene_text,
                style=style,
                aspect_ratio="16:9",
                user_tier=user_tier
            )
            
            if result.get('status') == 'success':
                image_url = result.get('image_url')
                
                if not image_url:
                    raise Exception("No image URL in V7 response")
                
                # Store in database
                image_record_data = {
                    'video_generation_id': video_gen_id,
                    'image_type': 'scene',
                    'prompt': f"Scene: {scene_text}",
                    'image_url': image_url,
                    'scene_number': scene_number,
                    'style': style,
                    'status': 'completed',
                    'sequence_order': i + 1,
                    'model_id': result.get('model_used', 'gen4_image'),
                    'aspect_ratio': '16:9',
                    'service_provider': 'modelslab_v7',
                    'generation_time_seconds': result.get('generation_time', 0),
                    'metadata': {
                        'service': 'modelslab_v7',
                        'model_used': result.get('model_used', 'gen4_image'),
                        'generation_time': result.get('generation_time', 0)
                    }
                }
                
                db_result = supabase.table('image_generations').insert(image_record_data).execute()
                
                scene_results.append({
                    'id': db_result.data[0]['id'] if db_result.data else None,
                    'scene_number': scene_number,
                    'image_url': image_url,
                    'description': scene_text,
                    'style': style,
                    'status': 'success'
                })
                
                print(f"[SCENE IMAGE {i+1}] ✅ Success: {image_url[:50]}...")
                
            else:
                raise Exception(f"V7 Image generation failed: {result.get('error', 'Unknown error')}")
            
            # ✅ OPTIMIZATION: Brief pause between requests
            await asyncio.sleep(2)
                
        except Exception as e:
            print(f"[SCENE IMAGE {i+1}] ❌ Failed: {str(e)}")
            
            # Store failed record
            failed_record_data = {
                'video_generation_id': video_gen_id,
                'image_type': 'scene',
                'scene_number': scene_number if 'scene_number' in locals() else i + 1,
                'prompt': scene_text if 'scene_text' in locals() else 'Unknown scene',
                'style': style,
                'status': 'failed',
                'error_message': str(e),
                'sequence_order': i + 1,
                'model_id': 'gen4_image',
                'aspect_ratio': '16:9',
                'service_provider': 'modelslab_v7',
                'metadata': {'service': 'modelslab_v7', 'error': str(e)}
            }
            supabase.table('image_generations').insert(failed_record_data).execute()
            
            scene_results.append({
                'scene_number': scene_number if 'scene_number' in locals() else i + 1,
                'status': 'failed',
                'error': str(e)
            })
    
    successful_count = len([r for r in scene_results if r.get('status') == 'success'])
    print(f"[SCENE IMAGES OPTIMIZED] Completed: {successful_count}/{len(scene_descriptions)} scenes")
    return scene_results


    
# async def generate_character_images(
#     image_service: ModelsLabV7ImageService,
#     video_gen_id: str,
#     characters: List[str],
#     style: str = "realistic"
# ) -> List[Dict[str, Any]]:
#     """Generate character images using V7 service"""
    
#     print(f"[CHARACTER IMAGES] Generating images for {len(characters)} characters...")
#     character_results = []
#     supabase = get_supabase()
    
#     for i, character in enumerate(characters):
#         try:
#             print(f"[CHARACTER IMAGES] Processing character {i+1}/{len(characters)}: {character}")
            
#             character_description = f"Detailed character portrait, {style} style, expressive features"
            
#             result = await image_service.generate_character_image(
#                 character_name=character,
#                 character_description=character_description,
#                 style=style,
#                 aspect_ratio="3:4"
#             )
            
#             if result.get('status') == 'success':
#                 image_url = result.get('image_url')
                
#                 if not image_url:
#                     raise Exception("No image URL in V7 response")
                
#                 # ✅ FIXED: Use ALL available columns
#                 image_record_data = {
#                     'video_generation_id': video_gen_id,
#                     'image_type': 'character',
#                     'prompt': f"Character: {character}, {character_description}",
#                     'image_url': image_url,
#                     'character_name': character,
#                     'style': style,
#                     'status': 'completed',
#                     'sequence_order': i + 1,
#                     'model_id': result.get('model_used', 'gen4_image'),
#                     'aspect_ratio': '3:4',
#                     'service_provider': 'modelslab_v7',
#                     'generation_time_seconds': result.get('generation_time', 0),
#                     'metadata': {
#                         'service': 'modelslab_v7',
#                         'model_used': result.get('model_used', 'gen4_image'),
#                         'generation_time': result.get('generation_time', 0)
#                     }
#                 }
                
#                 db_result = supabase.table('image_generations').insert(image_record_data).execute()
                
#                 character_results.append({
#                     'id': db_result.data[0]['id'] if db_result.data else None,
#                     'character': character,
#                     'image_url': image_url,
#                     'style': style,
#                     'status': 'success'
#                 })
                
#                 print(f"[CHARACTER IMAGES] ✅ Generated {character}")
                
#             else:
#                 raise Exception(f"V7 Image generation failed: {result.get('error', 'Unknown error')}")
                
#         except Exception as e:
#             print(f"[CHARACTER IMAGES] ❌ Failed {character}: {str(e)}")
            
#             # ✅ FIXED: Use ALL available columns for failed records too
#             failed_record_data = {
#                 'video_generation_id': video_gen_id,
#                 'image_type': 'character',
#                 'character_name': character,
#                 'style': style,
#                 'status': 'failed',
#                 'error_message': str(e),
#                 'sequence_order': i + 1,
#                 'prompt': f"Character: {character}, {character_description}",
#                 'model_id': 'gen4_image',
#                 'aspect_ratio': '3:4',
#                 'service_provider': 'modelslab_v7',
#                 'metadata': {'service': 'modelslab_v7'}
#             }
#             supabase.table('image_generations').insert(failed_record_data).execute()
            
#             character_results.append({
#                 'character': character,
#                 'status': 'failed',
#                 'error': str(e)
#             })
    
#     print(f"[CHARACTER IMAGES] Completed: {len([r for r in character_results if r.get('status') == 'success'])}/{len(characters)} characters")
#     return character_results


# async def generate_scene_images(
#     image_service: ModelsLabV7ImageService,
#     video_gen_id: str,
#     scene_descriptions: List[Dict[str, Any]],
#     style: str = "cinematic"
# ) -> List[Dict[str, Any]]:
#     """Generate scene images using V7 service"""
    
#     print(f"[SCENE IMAGES] Generating images for {len(scene_descriptions)} scenes...")
#     scene_results = []
#     supabase = get_supabase()
    
#     for i, scene in enumerate(scene_descriptions):
#         try:
#             # Handle different scene description formats
#             if isinstance(scene, dict):
#                 scene_text = scene.get('description', scene.get('text', str(scene)))
#                 scene_number = scene.get('scene_number', i + 1)
#             else:
#                 scene_text = str(scene)
#                 scene_number = i + 1
            
#             print(f"[SCENE IMAGES] Processing scene {i+1}/{len(scene_descriptions)}: {scene_text[:50]}...")
            
#             result = await image_service.generate_scene_image(
#                 scene_description=scene_text,
#                 style=style,
#                 aspect_ratio="16:9"
#             )
            
#             if result.get('status') == 'success':
#                 image_url = result.get('image_url')
                
#                 if not image_url:
#                     raise Exception("No image URL in V7 response")
                
#                 # ✅ FIXED: Use ALL available columns including scene_number
#                 image_record_data = {
#                     'video_generation_id': video_gen_id,
#                     'image_type': 'scene',
#                     'prompt': f"Scene: {scene_text}",
#                     'image_url': image_url,
#                     'scene_number': scene_number,  # ✅ Now this column exists
#                     'style': style,
#                     'status': 'completed',
#                     'sequence_order': i + 1,
#                     'model_id': result.get('model_used', 'gen4_image'),
#                     'aspect_ratio': '16:9',
#                     'service_provider': 'modelslab_v7',
#                     'generation_time_seconds': result.get('generation_time', 0),
#                     'metadata': {
#                         'service': 'modelslab_v7',
#                         'model_used': result.get('model_used', 'gen4_image'),
#                         'generation_time': result.get('generation_time', 0)
#                     }
#                 }
                
#                 db_result = supabase.table('image_generations').insert(image_record_data).execute()
                
#                 scene_results.append({
#                     'id': db_result.data[0]['id'] if db_result.data else None,
#                     'scene_number': scene_number,
#                     'image_url': image_url,
#                     'description': scene_text,
#                     'style': style,
#                     'status': 'success'
#                 })
                
#                 print(f"[SCENE IMAGES] ✅ Generated scene {scene_number}")
                
#             else:
#                 raise Exception(f"V7 Image generation failed: {result.get('error', 'Unknown error')}")
                
#         except Exception as e:
#             print(f"[SCENE IMAGES] ❌ Failed scene {i+1}: {str(e)}")
            
#             # ✅ FIXED: Use ALL available columns for failed records
#             failed_record_data = {
#                 'video_generation_id': video_gen_id,
#                 'image_type': 'scene',
#                 'scene_number': scene_number if 'scene_number' in locals() else i + 1,
#                 'prompt': scene_text if 'scene_text' in locals() else 'Unknown scene',
#                 'style': style,
#                 'status': 'failed',
#                 'error_message': str(e),
#                 'sequence_order': i + 1,
#                 'model_id': 'gen4_image',
#                 'aspect_ratio': '16:9',
#                 'service_provider': 'modelslab_v7',
#                 'metadata': {'service': 'modelslab_v7'}
#             }
#             supabase.table('image_generations').insert(failed_record_data).execute()
            
#             scene_results.append({
#                 'scene_number': scene_number if 'scene_number' in locals() else i + 1,
#                 'status': 'failed',
#                 'error': str(e)
#             })
    
#     print(f"[SCENE IMAGES] Completed: {len([r for r in scene_results if r.get('status') == 'success'])}/{len(scene_descriptions)} scenes")
#     return scene_results

def create_character_image_prompt(character: str, style: str) -> str:
    """Create detailed prompt for character image generation"""
    
    style_modifiers = {
        "realistic": "photorealistic, high-resolution portrait, professional lighting, detailed features",
        "cinematic": "cinematic lighting, dramatic composition, film-like quality, professional cinematography",
        "animated": "animated character design, stylized features, vibrant colors, cartoon style",
        "fantasy": "fantasy art style, magical atmosphere, mystical lighting, detailed fantasy character",
        "comic": "comic book style, bold lines, vibrant colors, superhero aesthetic",
        "artistic": "artistic rendering, painterly style, creative composition, artistic flair"
    }
    
    base_prompt = f"Character portrait of {character}, "
    style_prompt = style_modifiers.get(style.lower(), style_modifiers["realistic"])
    technical_prompt = ", 16:9 aspect ratio, high quality, detailed, professional"
    
    return base_prompt + style_prompt + technical_prompt


@celery_app.task(bind=True)
def generate_character_image_task(
    self,
    character_name: str,
    character_description: str,
    user_id: str,
    chapter_id: Optional[str] = None,
    character_id: Optional[str] = None,
    style: str = "realistic",
    aspect_ratio: str = "3:4",
    custom_prompt: Optional[str] = None,
    record_id: Optional[str] = None,
    user_tier: str = "free"
):
    """
    Unified asynchronous Celery task for generating character images.
    Supports both standalone character images (chapter-based) and character record images (plot-based).

    Args:
        character_name: Name of the character
        character_description: Description of the character
        user_id: User ID for database association
        chapter_id: Optional chapter ID for metadata association
        character_id: Optional character record ID - if provided, updates characters table
        style: Visual style (realistic, cinematic, animated, fantasy)
        aspect_ratio: Image aspect ratio
        custom_prompt: Optional custom prompt additions
        record_id: Image generation record ID for tracking
        user_tier: User subscription tier for model selection

    Returns:
        Dict containing task result with record_id and status
    """
    try:
        logger.info(f"[CharacterImageTask] Starting generation for {character_name}")
        logger.info(f"[CharacterImageTask] Parameters: user={user_id}, chapter={chapter_id}, character={character_id}, record={record_id}, tier={user_tier}")

        # Get database connection
        supabase = get_supabase()

        # Update character status to 'generating' if character_id provided
        if character_id:
            try:
                supabase.table('characters').update({
                    'image_generation_status': 'generating',
                    'image_generation_task_id': self.request.id,
                    'updated_at': 'now()'
                }).eq('id', character_id).execute()
                logger.info(f"[CharacterImageTask] Updated character {character_id} status to 'generating'")
            except Exception as char_update_error:
                logger.warning(f"[CharacterImageTask] Failed to update character status: {char_update_error}")

        # Create standalone image service instance
        image_service = StandaloneImageService(supabase)

        # Generate the character image using the existing service
        result = asyncio.run(image_service.generate_character_image(
            character_name=character_name,
            character_description=character_description,
            user_id=user_id,
            style=style,
            aspect_ratio=aspect_ratio,
            custom_prompt=custom_prompt,
            user_tier=user_tier
        ))

        image_url = result.get('image_url')
        generation_time = result.get('generation_time', 0)
        model_used = result.get('model_used', 'gen4_image')

        # Update the image_generations record with the result
        update_data = {
            'status': 'completed',
            'image_url': image_url,
            'generation_time_seconds': generation_time,
            'updated_at': 'now()',
            'character_id': character_id,
            'model_id': model_used
        }

        supabase.table('image_generations').update(update_data).eq('id', record_id).execute()
        logger.info(f"[CharacterImageTask] Updated image_generations record {record_id}")

        # If character_id provided, also update the characters table
        if character_id and image_url:
            try:
                character_update_data = {
                    'image_url': image_url,
                    'image_generation_status': 'completed',
                    'image_generation_prompt': result.get('prompt_used', custom_prompt or f"Character portrait: {character_name}"),
                    'image_metadata': {
                        'model_used': model_used,
                        'generation_time': generation_time,
                        'aspect_ratio': aspect_ratio,
                        'style': style,
                        'service': 'modelslab_v7',
                        'task_id': self.request.id,
                        'image_generation_record_id': record_id
                    },
                    'generation_method': 'async_celery',
                    'model_used': model_used,
                    'updated_at': 'now()'
                }

                supabase.table('characters').update(character_update_data).eq('id', character_id).execute()
                logger.info(f"[CharacterImageTask] Updated character {character_id} with image URL: {image_url}")

            except Exception as char_update_error:
                logger.error(f"[CharacterImageTask] Failed to update character record: {char_update_error}")

        logger.info(f"[CharacterImageTask] Successfully generated character image: {record_id}")

        return {
            'status': 'success',
            'record_id': record_id,
            'character_id': character_id,
            'character_name': character_name,
            'image_url': image_url,
            'message': 'Character image generated successfully',
            'generation_time': generation_time,
            'model_used': model_used
        }

    except Exception as e:
        error_message = f"Character image generation failed: {str(e)}"
        logger.error(f"[CharacterImageTask] {error_message}")

        # Update image_generations record with error
        try:
            if record_id:
                supabase = get_supabase()
                supabase.table('image_generations').update({
                    'status': 'failed',
                    'error_message': error_message,
                    'updated_at': 'now()'
                }).eq('id', record_id).execute()
        except Exception as db_error:
            logger.error(f"[CharacterImageTask] Failed to update image_generations with error: {db_error}")

        # Update character record with failed status if character_id provided
        try:
            if character_id:
                supabase = get_supabase()
                supabase.table('characters').update({
                    'image_generation_status': 'failed',
                    'image_metadata': {
                        'error': error_message,
                        'task_id': self.request.id,
                        'failed_at': 'now()'
                    },
                    'updated_at': 'now()'
                }).eq('id', character_id).execute()
        except Exception as char_error:
            logger.error(f"[CharacterImageTask] Failed to update character with error status: {char_error}")

        raise Exception(error_message)

def create_scene_image_prompt(scene_description: str, style: str) -> str:
    """Create detailed prompt for scene image generation"""
    
    style_modifiers = {
        "realistic": "photorealistic scene, natural lighting, high detail, realistic environment",
        "cinematic": "cinematic composition, dramatic lighting, film-like atmosphere, professional cinematography",
        "animated": "animated scene, stylized environment, vibrant colors, cartoon background",
        "fantasy": "fantasy landscape, magical atmosphere, mystical environment, fantasy art style",
        "comic": "comic book scene, bold composition, dynamic angles, comic art style",
        "artistic": "artistic scene, painterly environment, creative composition, artistic style"
    }
    
    base_prompt = f"Scene: {scene_description}, "
    style_prompt = style_modifiers.get(style.lower(), style_modifiers["realistic"])
    technical_prompt = ", 16:9 aspect ratio, high quality, detailed background, cinematic framing"
    
    return base_prompt + style_prompt + technical_prompt