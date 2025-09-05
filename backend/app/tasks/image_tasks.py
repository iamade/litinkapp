from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
from app.core.database import get_supabase
import json

from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
from app.services.modelslab_image_service import ModelsLabImageService
from app.core.database import get_supabase
from app.services.pipeline_manager import PipelineManager, PipelineStep

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
        image_service = ModelsLabImageService()
        
        # 1. Generate character reference images
        character_images = []
        if characters:
            print(f"[IMAGE GENERATION] Generating {len(characters)} character images...")
            character_images = asyncio.run(generate_character_images(
                image_service, video_generation_id, characters, video_style
            ))
        
        # 2. Generate scene images  
        scene_images = []
        if scene_descriptions:
            print(f"[IMAGE GENERATION] Generating {len(scene_descriptions)} scene images...")
            scene_images = asyncio.run(generate_scene_images(
                image_service, video_generation_id, scene_descriptions, video_style
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
        
        # Only proceed to next step if we have some successful images
        if total_images > 0:
            print(f"[PIPELINE] Starting video generation after image completion")
            from app.tasks.video_tasks import generate_all_videos_for_generation
            generate_all_videos_for_generation.delay(video_generation_id)
        else:
            raise Exception("Cannot proceed to video generation - no images were created")
        
        return {
            'status': 'success',
            'message': success_message + " - Starting video generation...",
            'statistics': image_data['statistics'],
            'character_images': character_images,
            'scene_images': scene_images,
            'next_step': 'video_generation'
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
    
async def generate_character_images(
    image_service: ModelsLabImageService,
    video_gen_id: str,
    characters: List[str],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate character reference images with proper error handling"""
    
    print(f"[CHARACTER IMAGES] Generating character reference images...")
    character_results = []
    supabase = get_supabase()
    
    for i, character in enumerate(characters):
        try:
            print(f"[CHARACTER IMAGES] Processing character {i+1}/{len(characters)}: {character}")
            
            # Create character description
            character_description = f"detailed portrait of {character}, clear facial features, expressive"
            
            # Use the updated service method
            result = await image_service.generate_character_reference_image(
                character_name=character,
                character_description=character_description,
                style=video_style
            )
            
            # Handle response
            if result.get('status') == 'success':
                output_urls = result.get('output', [])
                if output_urls:
                    image_url = output_urls[0]
                    
                    # ✅ Use the correct column names that exist in database
                    try:
                        image_record = supabase.table('image_generations').insert({
                            'video_generation_id': video_gen_id,
                            'image_type': 'character',
                            'character_name': character,
                            'image_prompt': f"Character: {character}",  # Using existing column
                            'text_prompt': character_description,        # Using new column
                            'style': video_style,                        # Using new column
                            'image_url': image_url,
                            'sequence_order': i + 1,
                            'status': 'completed',
                            'metadata': {
                                'character_name': character,
                                'service': 'modelslab',
                                'model': image_service.get_image_model_for_style(video_style),
                                'width': 512,
                                'height': 768,
                                'generation_order': i + 1
                            }
                        }).execute()
                        
                        character_results.append({
                            'id': image_record.data[0]['id'],
                            'character': character,
                            'image_url': image_url,
                            'style': video_style
                        })
                        
                        print(f"[CHARACTER IMAGES] ✅ Generated {character}: {image_url}")
                        
                    except Exception as db_error:
                        print(f"[CHARACTER IMAGES] Database insert error: {db_error}")
                        # Fallback to minimal required fields
                        try:
                            image_record = supabase.table('image_generations').insert({
                                'video_generation_id': video_gen_id,
                                'image_url': image_url,
                                'status': 'completed'
                            }).execute()
                            
                            character_results.append({
                                'id': image_record.data[0]['id'],
                                'character': character,
                                'image_url': image_url,
                                'style': video_style
                            })
                            print(f"[CHARACTER IMAGES] ✅ Generated {character} (minimal data): {image_url}")
                        except Exception as fallback_error:
                            print(f"[CHARACTER IMAGES] Fallback insert also failed: {fallback_error}")
                            character_results.append(None)
                else:
                    raise Exception("No image URL in response")
            else:
                raise Exception(f"API returned error: {result.get('message', 'Unknown error')}")
            
        except Exception as e:
            print(f"[CHARACTER IMAGES] ❌ Failed {character}: {str(e)}")
            
            # Store failed record
            try:
                supabase.table('image_generations').insert({
                    'video_generation_id': video_gen_id,
                    'image_type': 'character',
                    'character_name': character,
                    'text_prompt': f"Character: {character}",
                    'style': video_style,
                    'status': 'failed',
                    'error_message': str(e),
                    'sequence_order': i + 1
                }).execute()
            except Exception as db_error:
                print(f"[CHARACTER IMAGES] Database error logging failure: {str(db_error)}")
            
            character_results.append(None)
    
    successful_characters = len([r for r in character_results if r is not None])
    print(f"[CHARACTER IMAGES] Completed: {successful_characters}/{len(characters)} characters")
    return character_results

async def generate_scene_images(
    image_service: ModelsLabImageService,
    video_gen_id: str,
    scene_descriptions: List[str],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate scene images with proper error handling"""
    
    print(f"[SCENE IMAGES] Generating scene images...")
    scene_results = []
    supabase = get_supabase()
    
    for i, scene_desc in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE IMAGES] Processing {scene_id}/{len(scene_descriptions)}")
            
            # ✅ FIXED: Use video-compatible dimensions (512x288 for 16:9 ratio)
            result = await image_service.generate_scene_image(
                scene_description=scene_desc,
                style=video_style,
                width=512,  # ✅ Fixed: Max 512 for video compatibility
                height=288  # ✅ Fixed: 16:9 ratio within limits
            )
            
            # Handle response
            if result.get('status') == 'success':
                output_urls = result.get('output', [])
                if output_urls:
                    image_url = output_urls[0]
                    
                    try:
                        image_record = supabase.table('image_generations').insert({
                            'video_generation_id': video_gen_id,
                            'image_type': 'scene',
                            'scene_id': scene_id,
                            'scene_description': scene_desc,
                            'image_prompt': f"Scene: {scene_desc[:100]}...",
                            'text_prompt': scene_desc,
                            'style': video_style,
                            'image_url': image_url,
                            'width': 512,      # ✅ Fixed: Update metadata
                            'height': 288,     # ✅ Fixed: Update metadata
                            'sequence_order': i + 1,
                            'status': 'completed',
                            'metadata': {
                                'scene_number': i + 1,
                                'scene_id': scene_id,
                                'service': 'modelslab',
                                'model': image_service.get_image_model_for_style(video_style),
                                'width': 512,      # ✅ Fixed: Video-compatible width
                                'height': 288,     # ✅ Fixed: Video-compatible height
                                'generation_order': i + 1
                            }
                        }).execute()
                        
                        scene_result = {
                            'id': image_record.data[0]['id'],
                            'scene_id': scene_id,
                            'image_url': image_url,
                            'description': scene_desc,
                            'style': video_style,
                            'width': 512,      # ✅ Fixed: Add dimensions to result
                            'height': 288,     # ✅ Fixed: Add dimensions to result
                            'metadata': {
                                'scene_number': i + 1,
                                'generation_order': i + 1
                            }
                        }
                        scene_results.append(scene_result)
                        
                        print(f"[SCENE IMAGES] ✅ Generated {scene_id}: {image_url}")
                        
                    except Exception as db_error:
                        print(f"[SCENE IMAGES] Database insert error: {db_error}")
                        # Even if DB insert fails, try to continue with the image URL
                        scene_result = {
                            'scene_id': scene_id,
                            'image_url': image_url,
                            'description': scene_desc,
                            'style': video_style,
                            'width': 512,
                            'height': 288
                        }
                        scene_results.append(scene_result)
                        print(f"[SCENE IMAGES] ✅ Generated {scene_id} (no DB): {image_url}")
                else:
                    raise Exception("No image URL in response")
            else:
                raise Exception(f"API returned error: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"[SCENE IMAGES] ❌ Failed scene {i+1}: {str(e)}")
            scene_results.append(None)
    
    successful_scenes = len([r for r in scene_results if r is not None])
    print(f"[SCENE IMAGES] Completed: {successful_scenes}/{len(scene_descriptions)} scenes")
    return scene_results

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