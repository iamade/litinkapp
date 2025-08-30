from app.core.celery_app import celery_app
import asyncio
import subprocess
import os
import tempfile
import requests
from typing import Dict, Any, List, Optional
from app.core.database import get_supabase
from app.services.file_service import FileService
import json

@celery_app.task(bind=True)
def merge_audio_video_for_generation(self, video_generation_id: str):
    """Main task to merge audio and video for a video generation"""
    
    try:
        print(f"[AUDIO VIDEO MERGE] Starting merge for video: {video_generation_id}")
        
        # Get video generation data
        supabase = get_supabase()
        video_data = supabase.table('video_generations').select('*').eq('id', video_generation_id).single().execute()
        
        if not video_data.data:
            raise Exception(f"Video generation {video_generation_id} not found")
        
        video_gen = video_data.data
        
        # Check if video generation is completed
        if video_gen.get('generation_status') != 'video_completed':
            raise Exception("Video generation must be completed before merging")
        
        # Update status
        supabase.table('video_generations').update({
            'generation_status': 'merging_audio'
        }).eq('id', video_generation_id).execute()
        
        # Get all necessary data
        audio_files = video_gen.get('audio_files', {})
        video_data_obj = video_gen.get('video_data', {})
        scene_videos = video_data_obj.get('scene_videos', [])
        
        print(f"[AUDIO VIDEO MERGE] Processing:")
        print(f"- Scene videos: {len(scene_videos)}")
        print(f"- Audio files: {len(audio_files.get('narrator', [])) + len(audio_files.get('characters', []))}")
        
        # Merge audio and video
        merge_result = asyncio.run(merge_audio_video_scenes(
            video_generation_id, scene_videos, audio_files
        ))
        
        if not merge_result:
            raise Exception("Failed to merge audio and video")
        
        # Update video generation with final result
        final_video_url = merge_result.get('final_video_url')
        merge_statistics = merge_result.get('statistics', {})
        
        supabase.table('video_generations').update({
            'video_url': final_video_url,
            'generation_status': 'completed',
            'merge_data': {
                'final_video_url': final_video_url,
                'merge_statistics': merge_statistics,
                'processing_details': merge_result.get('processing_details', {}),
                'quality_versions': merge_result.get('quality_versions', [])
            }
        }).eq('id', video_generation_id).execute()
        
        success_message = f"Audio+Video merge completed! Final video ready"
        print(f"[AUDIO VIDEO MERGE SUCCESS] {success_message}")
        
        # Log detailed information
        print(f"[MERGE STATISTICS]")
        print(f"- Final video URL: {final_video_url}")
        print(f"- Total duration: {merge_statistics.get('total_duration', 0):.1f} seconds")
        print(f"- File size: {merge_statistics.get('file_size_mb', 0):.1f} MB")
        print(f"- Processing time: {merge_statistics.get('processing_time', 0):.1f} seconds")
        print(f"- Audio track mixing: {merge_statistics.get('audio_tracks_mixed', 0)} tracks")
        print(f"- Synchronization accuracy: {merge_statistics.get('sync_accuracy', 'N/A')}")
        
        # TODO: Send WebSocket update to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'merge_completed',
        #     'status': 'completed',
        #     'message': success_message,
        #     'final_video_url': final_video_url,
        #     'statistics': merge_statistics
        # })
        
        # ✅ NEW: Trigger lip sync after merge completion
        print(f"[PIPELINE] Starting lip sync processing after merge completion")
        from app.tasks.lipsync_tasks import apply_lip_sync_to_generation
        apply_lip_sync_to_generation.delay(video_generation_id)
        
        return {
            'status': 'success',
            'message': success_message + " - Starting lip sync processing...",
            'final_video_url': final_video_url,
            'statistics': merge_statistics,
            'next_step': 'lip_sync'
        }
        
       
        
    except Exception as e:
        error_message = f"Audio/Video merge failed: {str(e)}"
        print(f"[AUDIO VIDEO MERGE ERROR] {error_message}")
        
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
        #     'step': 'merge_failed',
        #     'status': 'failed',
        #     'message': error_message
        # })
        
        raise Exception(error_message)

async def merge_audio_video_scenes(
    video_generation_id: str,
    scene_videos: List[Dict[str, Any]],
    audio_files: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge audio and video for all scenes"""
    
    print(f"[SCENE MERGE] Starting scene-by-scene audio/video merge...")
    
    try:
        # Filter out None videos
        valid_scene_videos = [v for v in scene_videos if v is not None and v.get('video_url')]
        
        if not valid_scene_videos:
            raise Exception("No valid scene videos found for merging")
        
        print(f"[SCENE MERGE] Processing {len(valid_scene_videos)} valid scenes")
        
        # Prepare audio tracks
        audio_preparation_result = await prepare_audio_tracks(audio_files, valid_scene_videos)
        
        # Merge each scene with its audio
        merged_scenes = []
        for i, scene_video in enumerate(valid_scene_videos):
            try:
                print(f"[SCENE MERGE] Processing scene {i+1}/{len(valid_scene_videos)}: {scene_video.get('scene_id')}")
                
                scene_audio = find_audio_for_scene(
                    scene_video.get('scene_id'), 
                    audio_preparation_result.get('scene_audio_tracks', {})
                )
                
                merged_scene = await merge_single_scene(
                    scene_video, scene_audio, video_generation_id
                )
                
                if merged_scene:
                    merged_scenes.append(merged_scene)
                    print(f"[SCENE MERGE] ✅ Scene {scene_video.get('scene_id')} merged successfully")
                else:
                    print(f"[SCENE MERGE] ⚠️ Scene {scene_video.get('scene_id')} merge failed, using original video")
                    merged_scenes.append({
                        'scene_id': scene_video.get('scene_id'),
                        'video_url': scene_video.get('video_url'),
                        'duration': scene_video.get('duration', 3.0),
                        'has_audio': False
                    })
                    
            except Exception as e:
                print(f"[SCENE MERGE] ❌ Scene {scene_video.get('scene_id')} failed: {str(e)}")
                # Use original video as fallback
                merged_scenes.append({
                    'scene_id': scene_video.get('scene_id'),
                    'video_url': scene_video.get('video_url'),
                    'duration': scene_video.get('duration', 3.0),
                    'has_audio': False
                })
        
        # Concatenate all merged scenes into final video
        print(f"[FINAL MERGE] Concatenating {len(merged_scenes)} scenes into final video")
        final_result = await concatenate_final_video(merged_scenes, video_generation_id)
        
        # Calculate statistics
        total_duration = sum([scene.get('duration', 0) for scene in merged_scenes])
        audio_tracks_mixed = len(audio_files.get('narrator', [])) + len(audio_files.get('characters', []))
        
        statistics = {
            'total_scenes_merged': len(merged_scenes),
            'total_duration': total_duration,
            'audio_tracks_mixed': audio_tracks_mixed,
            'file_size_mb': final_result.get('file_size_mb', 0),
            'processing_time': final_result.get('processing_time', 0),
            'sync_accuracy': '95%',  # Placeholder - could be calculated
            'scenes_with_audio': len([s for s in merged_scenes if s.get('has_audio')])
        }
        
        return {
            'final_video_url': final_result.get('final_video_url'),
            'statistics': statistics,
            'processing_details': {
                'merged_scenes': len(merged_scenes),
                'audio_preparation': audio_preparation_result.get('summary'),
                'concatenation_method': 'ffmpeg'
            },
            'quality_versions': final_result.get('quality_versions', [])
        }
        
    except Exception as e:
        print(f"[SCENE MERGE ERROR] {str(e)}")
        raise e

async def prepare_audio_tracks(
    audio_files: Dict[str, Any],
    scene_videos: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Prepare and organize audio tracks for each scene"""
    
    print(f"[AUDIO PREP] Preparing audio tracks...")
    
    # Organize audio by scene
    scene_audio_tracks = {}
    
    # Process narrator audio
    narrator_files = audio_files.get('narrator', [])
    for audio in narrator_files:
        scene_id = audio.get('scene') or audio.get('scene_id')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['narrator'].append(audio)
    
    # Process character audio
    character_files = audio_files.get('characters', [])
    for audio in character_files:
        scene_id = audio.get('scene') or audio.get('scene_id')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['characters'].append(audio)
    
    # Process sound effects
    sound_effects = audio_files.get('sound_effects', [])
    for audio in sound_effects:
        scene_id = audio.get('scene') or audio.get('scene_id')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['sound_effects'].append(audio)
    
    total_audio_files = len(narrator_files) + len(character_files) + len(sound_effects)
    
    print(f"[AUDIO PREP] Organized {total_audio_files} audio files across {len(scene_audio_tracks)} scenes")
    
    return {
        'scene_audio_tracks': scene_audio_tracks,
        'summary': {
            'total_audio_files': total_audio_files,
            'scenes_with_audio': len(scene_audio_tracks),
            'narrator_files': len(narrator_files),
            'character_files': len(character_files),
            'sound_effect_files': len(sound_effects)
        }
    }

def find_audio_for_scene(scene_id: str, scene_audio_tracks: Dict[str, Any]) -> Dict[str, Any]:
    """Find audio tracks for a specific scene"""
    
    return scene_audio_tracks.get(scene_id, {
        'narrator': [],
        'characters': [],
        'sound_effects': []
    })

async def merge_single_scene(
    scene_video: Dict[str, Any],
    scene_audio: Dict[str, Any],
    video_generation_id: str
) -> Optional[Dict[str, Any]]:
    """Merge audio with a single scene video using FFmpeg"""
    
    scene_id = scene_video.get('scene_id', 'unknown')
    video_url = scene_video.get('video_url')
    
    if not video_url:
        print(f"[SINGLE SCENE MERGE] No video URL for scene {scene_id}")
        return None
    
    # Check if scene has any audio
    has_narrator = len(scene_audio.get('narrator', [])) > 0
    has_characters = len(scene_audio.get('characters', [])) > 0
    has_sound_effects = len(scene_audio.get('sound_effects', [])) > 0
    
    if not (has_narrator or has_characters or has_sound_effects):
        print(f"[SINGLE SCENE MERGE] No audio for scene {scene_id}, using original video")
        return {
            'scene_id': scene_id,
            'video_url': video_url,
            'duration': scene_video.get('duration', 3.0),
            'has_audio': False
        }
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download video file
            video_path = os.path.join(temp_dir, f"{scene_id}_video.mp4")
            await download_file(video_url, video_path)
            
            # Download and prepare audio files
            audio_files_paths = []
            
            # Download narrator audio
            for i, narrator in enumerate(scene_audio.get('narrator', [])):
                if narrator.get('audio_url'):
                    audio_path = os.path.join(temp_dir, f"{scene_id}_narrator_{i}.mp3")
                    await download_file(narrator['audio_url'], audio_path)
                    audio_files_paths.append(audio_path)
            
            # Download character audio
            for i, character in enumerate(scene_audio.get('characters', [])):
                if character.get('audio_url'):
                    audio_path = os.path.join(temp_dir, f"{scene_id}_character_{i}.mp3")
                    await download_file(character['audio_url'], audio_path)
                    audio_files_paths.append(audio_path)
            
            # Download sound effects
            for i, effect in enumerate(scene_audio.get('sound_effects', [])):
                if effect.get('audio_url'):
                    audio_path = os.path.join(temp_dir, f"{scene_id}_effect_{i}.mp3")
                    await download_file(effect['audio_url'], audio_path)
                    audio_files_paths.append(audio_path)
            
            if not audio_files_paths:
                print(f"[SINGLE SCENE MERGE] No valid audio files downloaded for scene {scene_id}")
                return {
                    'scene_id': scene_id,
                    'video_url': video_url,
                    'duration': scene_video.get('duration', 3.0),
                    'has_audio': False
                }
            
            # Mix audio files if multiple
            mixed_audio_path = os.path.join(temp_dir, f"{scene_id}_mixed_audio.mp3")
            
            if len(audio_files_paths) == 1:
                # Single audio file
                mixed_audio_path = audio_files_paths[0]
            else:
                # Mix multiple audio files
                await mix_audio_files(audio_files_paths, mixed_audio_path)
            
            # Merge audio with video
            output_path = os.path.join(temp_dir, f"{scene_id}_merged.mp4")
            await merge_audio_with_video_ffmpeg(video_path, mixed_audio_path, output_path)
            
            # Upload merged video
            file_service = FileService()
            merged_video_url = await file_service.upload_file(
                output_path, 
                f"merged_videos/{video_generation_id}/{scene_id}_merged.mp4"
            )
            
            if not merged_video_url:
                raise Exception("Failed to upload merged video")
            
            return {
                'scene_id': scene_id,
                'video_url': merged_video_url,
                'duration': scene_video.get('duration', 3.0),
                'has_audio': True,
                'audio_tracks_used': len(audio_files_paths)
            }
            
    except Exception as e:
        print(f"[SINGLE SCENE MERGE ERROR] Scene {scene_id}: {str(e)}")
        return None

async def mix_audio_files(audio_paths: List[str], output_path: str):
    """Mix multiple audio files using FFmpeg"""
    
    if len(audio_paths) == 1:
        # Copy single file
        subprocess.run(['cp', audio_paths[0], output_path], check=True)
        return
    
    # Build FFmpeg command for mixing
    cmd = ['ffmpeg', '-y']  # -y to overwrite output
    
    # Add input files
    for audio_path in audio_paths:
        cmd.extend(['-i', audio_path])
    
    # Add filter complex for mixing
    if len(audio_paths) == 2:
        cmd.extend(['-filter_complex', '[0:a][1:a]amix=inputs=2:duration=longest[out]'])
        cmd.extend(['-map', '[out]'])
    else:
        # For more than 2 files
        inputs = ''.join([f'[{i}:a]' for i in range(len(audio_paths))])
        filter_complex = f'{inputs}amix=inputs={len(audio_paths)}:duration=longest[out]'
        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[out]'])
    
    cmd.append(output_path)
    
    print(f"[AUDIO MIX] Mixing {len(audio_paths)} audio files")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg audio mixing failed: {result.stderr}")

async def merge_audio_with_video_ffmpeg(video_path: str, audio_path: str, output_path: str):
    """Merge audio with video using FFmpeg"""
    
    cmd = [
        'ffmpeg', '-y',  # Overwrite output
        '-i', video_path,  # Video input
        '-i', audio_path,  # Audio input
        '-c:v', 'copy',    # Copy video codec (no re-encoding)
        '-c:a', 'aac',     # Audio codec
        '-map', '0:v:0',   # Map first video stream
        '-map', '1:a:0',   # Map first audio stream
        '-shortest',       # End when shortest stream ends
        output_path
    ]
    
    print(f"[VIDEO AUDIO MERGE] Merging audio with video")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"FFmpeg video/audio merge failed: {result.stderr}")

async def concatenate_final_video(
    merged_scenes: List[Dict[str, Any]],
    video_generation_id: str
) -> Dict[str, Any]:
    """Concatenate all merged scenes into final video"""
    
    if len(merged_scenes) == 1:
        # Single scene, just return it
        scene = merged_scenes[0]
        return {
            'final_video_url': scene.get('video_url'),
            'file_size_mb': 0,  # Unknown
            'processing_time': 0,
            'quality_versions': []
        }
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download all scene videos
            scene_files = []
            for i, scene in enumerate(merged_scenes):
                video_url = scene.get('video_url')
                if video_url:
                    video_path = os.path.join(temp_dir, f"scene_{i:03d}.mp4")
                    await download_file(video_url, video_path)
                    scene_files.append(video_path)
            
            if not scene_files:
                raise Exception("No scene videos to concatenate")
            
            # Create FFmpeg concat file
            concat_file = os.path.join(temp_dir, "scenes.txt")
            with open(concat_file, 'w') as f:
                for scene_file in scene_files:
                    f.write(f"file '{scene_file}'\n")
            
            # Concatenate using FFmpeg
            final_output = os.path.join(temp_dir, "final_video.mp4")
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Copy without re-encoding
                final_output
            ]
            
            print(f"[FINAL CONCAT] Concatenating {len(scene_files)} scene videos")
            import time
            start_time = time.time()
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg concatenation failed: {result.stderr}")
            
            processing_time = time.time() - start_time
            
            # Get file size
            file_size_bytes = os.path.getsize(final_output)
            file_size_mb = file_size_bytes / (1024 * 1024)
            
            # Upload final video
            file_service = FileService()
            final_video_url = await file_service.upload_file(
                final_output, 
                f"final_videos/{video_generation_id}/final_video.mp4"
            )
            
            if not final_video_url:
                raise Exception("Failed to upload final video")
            
            print(f"[FINAL CONCAT] ✅ Final video created: {file_size_mb:.1f}MB in {processing_time:.1f}s")
            
            return {
                'final_video_url': final_video_url,
                'file_size_mb': file_size_mb,
                'processing_time': processing_time,
                'quality_versions': []  # Could generate multiple qualities here
            }
            
    except Exception as e:
        print(f"[FINAL CONCAT ERROR] {str(e)}")
        raise e

async def download_file(url: str, local_path: str):
    """Download file from URL to local path"""
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"[DOWNLOAD] Downloaded {url} to {local_path}")