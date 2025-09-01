from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List
from app.services.modelslab_service import ModelsLabService
from app.core.database import get_supabase
import json

@celery_app.task(bind=True)
def generate_all_images_for_video(self, video_generation_id: str):
    """Main task to generate all images for a video generation"""
    
    try:
        print(f"[IMAGE GENERATION] Starting image generation for video: {video_generation_id}")
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        script_data = video_gen.get('script_data', {})
        
        if not script_data:
            raise Exception("No script data found for image generation")
        
        # Check if audio generation is completed
        if video_gen.get('generation_status') != 'audio_completed':
            raise Exception("Audio generation must be completed before image generation")
        
        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'generating_images'
        }).eq('id', video_generation_id).execute()
        
        # Extract data
        characters = script_data.get('characters', [])
        scene_descriptions = script_data.get('scene_descriptions', [])
        video_style = script_data.get('video_style', 'realistic')
        
        print(f"[IMAGE GENERATION] Processing:")
        print(f"- Characters: {len(characters)}")
        print(f"- Scenes: {len(scene_descriptions)}")
        print(f"- Video Style: {video_style}")
        
        # Generate images
        modelslab_service = ModelsLabService()
        
        # 1. Generate character reference images
        character_results = asyncio.run(generate_character_images(
            modelslab_service, video_generation_id, characters, video_style
        ))
        
        # 2. Generate scene images
        scene_results = asyncio.run(generate_scene_images(
            modelslab_service, video_generation_id, scene_descriptions, video_style
        ))
        
        # Compile results
        total_character_images = len(character_results)
        total_scene_images = len(scene_results)
        total_images = total_character_images + total_scene_images
        
        success_character_images = len([r for r in character_results if r is not None])
        success_scene_images = len([r for r in scene_results if r is not None])
        success_total = success_character_images + success_scene_images
        
        success_rate = (success_total / total_images * 100) if total_images > 0 else 0
        
        # Update video generation with image data
        image_data = {
            'character_images': character_results,
            'scene_images': scene_results,
            'statistics': {
                'total_scenes': len(scene_descriptions),
                'images_needed_per_scene': 1,  # Can be configurable
                'character_images_generated': success_character_images,
                'scene_images_generated': success_scene_images,
                'total_images_generated': success_total,
                'success_rate': round(success_rate, 2)
            }
        }
        
        supabase.table('video_generations').update({
            'image_data': image_data,
            'generation_status': 'images_completed'
        }).eq('id', video_generation_id).execute()
        
        success_message = f"Image generation completed! {success_total} images created for {len(scene_descriptions)} scenes"
        print(f"[IMAGE GENERATION SUCCESS] {success_message}")
        
        # Log detailed breakdown
        print(f"[IMAGE STATISTICS]")
        print(f"- Total scenes in script: {len(scene_descriptions)}")
        print(f"- Images needed per scene: 1")
        print(f"- Character images generated: {success_character_images}/{len(characters)}")
        print(f"- Scene images generated: {success_scene_images}/{len(scene_descriptions)}")
        print(f"- Success rate: {success_rate:.1f}%")
        
         # ✅ NEW: Trigger video generation after image completion
        print(f"[PIPELINE] Starting video generation after image completion")
        from app.tasks.video_tasks import generate_all_videos_for_generation
        generate_all_videos_for_generation.delay(video_generation_id)
        
        
        # TODO: Send WebSocket update to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'image_generation',
        #     'status': 'completed',
        #     'message': success_message,
        #     'progress': 100,
        #     'character_images': success_character_images,
        #     'scene_images': success_scene_images,
        #     'statistics': image_data['statistics']
        # })
        
        return {
            'status': 'success',
            'message': success_message,
            'statistics': image_data['statistics'],
            'character_images': character_results,
            'scene_images': scene_results,
            'next_step': 'video_generation'
        }
        
    except Exception as e:
        error_message = f"Image generation failed: {str(e)}"
        print(f"[IMAGE GENERATION ERROR] {error_message}")
        
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
        #     'step': 'image_generation',
        #     'status': 'failed',
        #     'message': error_message
        # })
        
        raise Exception(error_message)

async def generate_character_images(
    modelslab_service: ModelsLabService,
    video_gen_id: str,
    characters: List[str],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate character reference images"""
    
    print(f"[CHARACTER IMAGES] Generating character reference images...")
    character_results = []
    supabase = get_supabase()
    
    model_id = modelslab_service.get_model_for_style(video_style)
    
    for i, character in enumerate(characters):
        try:
            print(f"[CHARACTER IMAGES] Processing character {i+1}/{len(characters)}: {character}")
            
            # Create detailed character prompt
            character_prompt = create_character_image_prompt(character, video_style)
            
            # Generate image
            result = await modelslab_service.generate_image(
                prompt=character_prompt,
                model_id=model_id,
                width=1024,
                height=576,  # 16:9 for video
                samples=1,
                steps=30,
                guidance_scale=7.5,
                enhance_prompt=True
            )
            
            # Handle response
            if result.get('status') == 'success':
                image_url = result.get('output', [{}])[0] if result.get('output') else None
                if isinstance(image_url, dict):
                    image_url = image_url.get('url') or image_url.get('image_url')
            else:
                # Wait for completion if async
                request_id = result.get('id')
                if request_id:
                    final_result = await modelslab_service.wait_for_completion(request_id)
                    output = final_result.get('output', [])
                    image_url = output[0] if output else None
                    if isinstance(image_url, dict):
                        image_url = image_url.get('url') or image_url.get('image_url')
                else:
                    raise Exception("Failed to get image URL")
            
            if not image_url:
                raise Exception("No image URL returned from API")
            
            # Store in database
            image_record = supabase.table('image_generations').insert({
                'video_generation_id': video_gen_id,
                'image_type': 'character',
                'character_name': character,
                'image_prompt': character_prompt,
                'image_url': image_url,
                'status': 'completed',
                'metadata': {
                    'model_id': model_id,
                    'style': video_style,
                    'service': 'modelslab',
                    'width': 1024,
                    'height': 576
                }
            }).execute()
            
            character_results.append({
                'id': image_record.data[0]['id'],
                'character': character,
                'image_url': image_url,
                'prompt': character_prompt,
                'model': model_id
            })
            
            print(f"[CHARACTER IMAGES] ✅ Generated {character}")
            
        except Exception as e:
            print(f"[CHARACTER IMAGES] ❌ Failed {character}: {str(e)}")
            
            # Store failed record
            try:
                supabase.table('image_generations').insert({
                    'video_generation_id': video_gen_id,
                    'image_type': 'character',
                    'character_name': character,
                    'image_prompt': create_character_image_prompt(character, video_style),
                    'status': 'failed',
                    'error_message': str(e),
                    'metadata': {
                        'model_id': model_id,
                        'style': video_style,
                        'service': 'modelslab'
                    }
                }).execute()
            except:
                pass
            
            character_results.append(None)
    
    successful_characters = len([r for r in character_results if r is not None])
    print(f"[CHARACTER IMAGES] Completed: {successful_characters}/{len(characters)} characters")
    return character_results

async def generate_scene_images(
    modelslab_service: ModelsLabService,
    video_gen_id: str,
    scene_descriptions: List[str],
    video_style: str
) -> List[Dict[str, Any]]:
    """Generate scene images for video generation"""
    
    print(f"[SCENE IMAGES] Generating scene images...")
    scene_results = []
    supabase = get_supabase()
    
    model_id = modelslab_service.get_model_for_style(video_style)
    
    for i, scene_description in enumerate(scene_descriptions):
        try:
            scene_id = f"scene_{i+1}"
            print(f"[SCENE IMAGES] Processing {scene_id}/{len(scene_descriptions)}")
            
            # Create cinematic scene prompt
            scene_prompt = create_scene_image_prompt(scene_description, video_style)
            
            # Generate image
            result = await modelslab_service.generate_image(
                prompt=scene_prompt,
                model_id=model_id,
                width=1024,
                height=576,  # 16:9 for video
                samples=1,
                steps=30,
                guidance_scale=7.5,
                enhance_prompt=True
            )
            
            # Handle response
            if result.get('status') == 'success':
                image_url = result.get('output', [{}])[0] if result.get('output') else None
                if isinstance(image_url, dict):
                    image_url = image_url.get('url') or image_url.get('image_url')
            else:
                # Wait for completion if async
                request_id = result.get('id')
                if request_id:
                    final_result = await modelslab_service.wait_for_completion(request_id)
                    output = final_result.get('output', [])
                    image_url = output[0] if output else None
                    if isinstance(image_url, dict):
                        image_url = image_url.get('url') or image_url.get('image_url')
                else:
                    raise Exception("Failed to get image URL")
            
            if not image_url:
                raise Exception("No image URL returned from API")
            
            # Store in database
            image_record = supabase.table('image_generations').insert({
                'video_generation_id': video_gen_id,
                'image_type': 'scene',
                'scene_id': scene_id,
                'scene_description': scene_description,
                'image_prompt': scene_prompt,
                'image_url': image_url,
                'status': 'completed',
                'metadata': {
                    'model_id': model_id,
                    'style': video_style,
                    'service': 'modelslab',
                    'width': 1024,
                    'height': 576,
                    'scene_index': i
                }
            }).execute()
            
            scene_results.append({
                'id': image_record.data[0]['id'],
                'scene_id': scene_id,
                'scene_description': scene_description,
                'image_url': image_url,
                'prompt': scene_prompt,
                'model': model_id
            })
            
            print(f"[SCENE IMAGES] ✅ Generated {scene_id}")
            
        except Exception as e:
            print(f"[SCENE IMAGES] ❌ Failed scene {i+1}: {str(e)}")
            
            # Store failed record
            try:
                supabase.table('image_generations').insert({
                    'video_generation_id': video_gen_id,
                    'image_type': 'scene',
                    'scene_id': f"scene_{i+1}",
                    'scene_description': scene_description,
                    'image_prompt': create_scene_image_prompt(scene_description, video_style),
                    'status': 'failed',
                    'error_message': str(e),
                    'metadata': {
                        'model_id': model_id,
                        'style': video_style,
                        'service': 'modelslab',
                        'scene_index': i
                    }
                }).execute()
            except:
                pass
            
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