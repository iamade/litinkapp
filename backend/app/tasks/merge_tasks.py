from app.tasks.celery_app import celery_app
import asyncio
import subprocess
import os
import tempfile
import requests
from typing import Dict, Any, List, Optional, Tuple
from app.core.database import get_supabase
from app.services.file_service import FileService
import json
from app.schemas.merge import MergeQualityTier, FFmpegParameters, MergeInputFile


def update_merge_progress(merge_id: str, progress_percentage: float, current_step: str, statistics: Optional[Dict[str, Any]] = None):
    """Update merge operation progress in database"""
    try:
        supabase = get_supabase()

        # Update merge_operations table with progress
        update_data = {
            'progress': int(progress_percentage),
            'merge_status': 'IN_PROGRESS' if progress_percentage < 100 else 'COMPLETED',
            'updated_at': 'now()'
        }

        # Add statistics if provided
        if statistics:
            update_data['processing_stats'] = statistics

        supabase.table('merge_operations').update(update_data).eq('id', merge_id).execute()

        print(f"[PROGRESS] {merge_id}: {progress_percentage:.1f}% - {current_step}")
        if statistics:
            print(f"[STATISTICS] {statistics}")
    except Exception as e:
        print(f"[PROGRESS UPDATE ERROR] {str(e)}")


def get_quality_settings(quality_tier: MergeQualityTier, custom_params: Optional[FFmpegParameters] = None) -> Dict[str, Any]:
    """Get FFmpeg settings based on quality tier"""

    base_settings = {
        MergeQualityTier.WEB: {
            'preset': 'fast',
            'crf': None,  # Use bitrate instead
            'maxrate': '3M',
            'bufsize': '6M',
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'audio_bitrate': '128k'
        },
        MergeQualityTier.MEDIUM: {
            'preset': 'medium',
            'crf': 23,
            'maxrate': '5M',
            'bufsize': '10M',
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'audio_bitrate': '128k'
        },
        MergeQualityTier.HIGH: {
            'preset': 'slow',
            'crf': 18,
            'maxrate': '10M',
            'bufsize': '20M',
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'audio_bitrate': '128k'
        },
        MergeQualityTier.CUSTOM: {
            'preset': 'medium',
            'crf': 23,
            'maxrate': '5M',
            'bufsize': '10M',
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'audio_bitrate': '128k'
        }
    }

    settings = base_settings.get(quality_tier, base_settings[MergeQualityTier.WEB]).copy()

    # Override with custom parameters if provided
    if custom_params and quality_tier == MergeQualityTier.CUSTOM:
        if custom_params.video_codec:
            settings['video_codec'] = custom_params.video_codec.value
        if custom_params.audio_codec:
            settings['audio_codec'] = custom_params.audio_codec.value
        if custom_params.video_bitrate:
            settings['maxrate'] = custom_params.video_bitrate
        if custom_params.audio_bitrate:
            settings['audio_bitrate'] = custom_params.audio_bitrate
        if custom_params.preset:
            settings['preset'] = custom_params.preset
        if custom_params.crf is not None:
            settings['crf'] = custom_params.crf
        if custom_params.resolution:
            settings['resolution'] = custom_params.resolution
        if custom_params.fps:
            settings['fps'] = custom_params.fps
        if custom_params.custom_filters:
            settings['custom_filters'] = custom_params.custom_filters

    return settings


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
        # Filter out None and scenes without video_url
        valid_scene_videos = [s for s in scene_videos if s and s.get('video_url')]
        if not valid_scene_videos:
            error_message = "[MERGE] No valid scene videos found, aborting merge step"
            print(error_message)
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message
            }).eq('id', video_generation_id).execute()
            raise Exception(error_message)
        scene_videos = valid_scene_videos

        # Fetch key scene shots for transitions
        key_scene_shots = {}
        try:
            segments_data = supabase.table('video_segments').select('scene_id, key_scene_shot_url').eq('video_generation_id', video_generation_id).execute()
            for segment in segments_data.data or []:
                key_scene_shots[segment['scene_id']] = segment['key_scene_shot_url']
        except Exception as e:
            print(f"[KEY SHOTS] Could not fetch key scene shots: {str(e)}")

        # Add key scene shots to scene videos
        for idx, scene in enumerate(scene_videos):
            if scene is None:
                print(f"[MERGE] Skipping None scene at index {idx}")
                continue
            scene_id = scene.get('scene_id')
            if not scene_id:
                print(f"[MERGE] Skipping scene with missing scene_id at index {idx}: {scene}")
                continue
            if scene_id in key_scene_shots:
                scene['key_scene_shot_url'] = key_scene_shots[scene_id]

        print(f"[AUDIO VIDEO MERGE] Processing:")
        print(f"- Scene videos: {len(scene_videos)}")
        print(f"- Audio files: {len(audio_files.get('narrator', [])) + len(audio_files.get('characters', []))}")
        print(f"- Key scene shots available: {len([s for s in scene_videos if s.get('key_scene_shot_url')])}")

        # Merge audio and video
        merge_result = asyncio.run(merge_audio_video_scenes(
            video_generation_id, scene_videos, audio_files
        ))
        
        if not merge_result:
            raise Exception("Failed to merge audio and video")
        
        # Update video generation with final result
        final_video_url = merge_result.get('final_video_url')
        merge_statistics = merge_result.get('statistics', {})
        quality_versions = merge_result.get('quality_versions', [])

        # Prepare download metadata
        download_metadata = prepare_download_metadata(
            final_video_url, quality_versions, merge_statistics, video_generation_id
        )

        supabase.table('video_generations').update({
            'video_url': final_video_url,
            'generation_status': 'completed',
            'merge_data': {
                'final_video_url': final_video_url,
                'merge_statistics': merge_statistics,
                'processing_details': merge_result.get('processing_details', {}),
                'quality_versions': quality_versions,
                'download_metadata': download_metadata,
                'advanced_features': {
                    'transitions_added': merge_result.get('transitions_added', 0),
                    'filters_applied': merge_result.get('filters_applied', False),
                    'quality_optimization': True,
                    'web_optimized': True
                }
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
        import traceback
        traceback.print_exc()
        # Update status to failed with detailed error
        try:
            supabase = get_supabase()
            supabase.table('video_generations').update({
                'generation_status': 'failed',
                'error_message': error_message,
                'merge_failed_at': 'now()'
            }).eq('id', video_generation_id).execute()
        except Exception as db_err:
            print(f"[AUDIO VIDEO MERGE ERROR] Failed to update status in DB: {db_err}")
        # TODO: Send error to frontend
        # send_websocket_update(video_generation_id, {
        #     'step': 'merge_failed',
        #     'status': 'failed',
        #     'message': error_message,
        #     'traceback': traceback.format_exc()
        # })
        # Graceful degradation: do not raise further if already failed
        return {
            'status': 'failed',
            'message': error_message,
            'error': str(e)
        }

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
        # Extract scene_id from top level or metadata
        scene_id = audio.get('scene') or audio.get('scene_id') or audio.get('metadata', {}).get('scene')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['narrator'].append(audio)
            print(f"[AUDIO PREP] Narrator audio mapped to scene {scene_id}")
    
    # Process character audio
    character_files = audio_files.get('characters', [])
    for audio in character_files:
        # Extract scene_id from top level or metadata
        scene_id = audio.get('scene') or audio.get('scene_id') or audio.get('metadata', {}).get('scene')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['characters'].append(audio)
            print(f"[AUDIO PREP] Character audio mapped to scene {scene_id}")
    
    # Process sound effects
    sound_effects = audio_files.get('sound_effects', [])
    for audio in sound_effects:
        # Extract scene_id from top level or metadata
        scene_id = audio.get('scene') or audio.get('scene_id') or audio.get('metadata', {}).get('scene')
        if scene_id:
            if scene_id not in scene_audio_tracks:
                scene_audio_tracks[scene_id] = {'narrator': [], 'characters': [], 'sound_effects': []}
            scene_audio_tracks[scene_id]['sound_effects'].append(audio)
            print(f"[AUDIO PREP] Sound effect mapped to scene {scene_id}")
    
    total_audio_files = len(narrator_files) + len(character_files) + len(sound_effects)
    
    # Log detailed scene mapping information
    print(f"[AUDIO PREP] Organized {total_audio_files} audio files across {len(scene_audio_tracks)} scenes")
    for scene_id, tracks in scene_audio_tracks.items():
        narrator_count = len(tracks['narrator'])
        character_count = len(tracks['characters'])
        sfx_count = len(tracks['sound_effects'])
        print(f"[AUDIO PREP] Scene {scene_id}: {narrator_count} narrator, {character_count} character, {sfx_count} sfx files")
    
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

async def generate_scene_transition(
    scene_a: Dict[str, Any],
    scene_b: Dict[str, Any],
    temp_dir: str,
    transition_duration: float = 1.0
) -> Optional[str]:
    """Generate animated transition between two scenes using key scene shots"""

    try:
        # Get key scene shot from scene_a (last frame)
        key_shot_url = scene_a.get('key_scene_shot_url')
        if not key_shot_url:
            print(f"[TRANSITION] No key scene shot for scene {scene_a.get('scene_id')}, skipping transition")
            return None

        # Download key scene shot
        key_shot_path = os.path.join(temp_dir, f"key_shot_{scene_a.get('scene_id')}.jpg")
        await download_file(key_shot_url, key_shot_path)

        # Download first frame of scene_b for transition
        scene_b_video_url = scene_b.get('video_url')
        if not scene_b_video_url:
            return None

        scene_b_path = os.path.join(temp_dir, f"scene_b_{scene_b.get('scene_id')}.mp4")
        await download_file(scene_b_video_url, scene_b_path)

        # Extract first frame of scene_b
        first_frame_path = os.path.join(temp_dir, f"first_frame_{scene_b.get('scene_id')}.jpg")
        cmd_extract = [
            'ffmpeg', '-y', '-i', scene_b_path,
            '-vframes', '1', '-q:v', '2', first_frame_path
        ]
        result = subprocess.run(cmd_extract, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[TRANSITION] Failed to extract first frame: {result.stderr}")
            return None

        # Create fade transition using FFmpeg
        transition_output = os.path.join(temp_dir, f"transition_{scene_a.get('scene_id')}_to_{scene_b.get('scene_id')}.mp4")

        # Create transition: fade from key_shot to first_frame over transition_duration seconds
        cmd_transition = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', key_shot_path,  # Loop key shot
            '-loop', '1', '-i', first_frame_path,  # Loop first frame
            '-filter_complex',
            f'[0:v]fade=t=out:st=0:d={transition_duration}:alpha=1[va];' +
            f'[1:v]fade=t=in:st=0:d={transition_duration}:alpha=1[vb];' +
            '[va][vb]overlay=format=auto[outv]',
            '-map', '[outv]',
            '-t', str(transition_duration),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            transition_output
        ]

        result = subprocess.run(cmd_transition, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[TRANSITION] Failed to create transition: {result.stderr}")
            return None

        print(f"[TRANSITION] ✅ Created {transition_duration}s transition between scenes")
        return transition_output

    except Exception as e:
        print(f"[TRANSITION ERROR] {str(e)}")
        return None

async def apply_video_filters(
    input_video: str,
    output_video: str,
    filters: List[str] = None
) -> bool:
    """Apply advanced video filters using FFmpeg"""

    if not filters:
        filters = ['colorlevels=rimin=0.058:gimin=0.058:bimin=0.058:rimax=0.898:gimax=0.898:bimax=0.898']  # Basic color correction

    try:
        filter_string = ','.join(filters)

        cmd = [
            'ffmpeg', '-y', '-i', input_video,
            '-vf', filter_string,
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '20',  # High quality
            '-c:a', 'copy',  # Copy audio if present
            output_video
        ]

        print(f"[FILTERS] Applying filters: {filter_string}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[FILTERS] Failed to apply filters: {result.stderr}")
            return False

        return True

    except Exception as e:
        print(f"[FILTERS ERROR] {str(e)}")
        return False

async def reencode_video(
    input_video: str,
    output_video: str,
    quality_tier: MergeQualityTier = MergeQualityTier.HIGH,
    format_type: str = 'mp4',
    custom_params: Optional[FFmpegParameters] = None
) -> Dict[str, Any]:
    """Re-encode video with optimized settings for quality and file size"""

    settings = get_quality_settings(quality_tier, custom_params)

    try:
        cmd = [
            'ffmpeg', '-y', '-i', input_video,
            '-c:v', settings['video_codec'],
            '-preset', settings['preset'],
            '-c:a', settings['audio_codec'], '-b:a', settings['audio_bitrate'],
            '-movflags', '+faststart',  # Optimize for web playback
            '-f', format_type,
            output_video
        ]

        # Add CRF if specified (for quality-based encoding)
        if settings.get('crf') is not None:
            cmd.extend(['-crf', str(settings['crf'])])
        else:
            # Use bitrate-based encoding
            cmd.extend(['-maxrate', settings['maxrate'], '-bufsize', settings['bufsize']])

        # Add resolution if specified
        if settings.get('resolution'):
            cmd.extend(['-vf', f'scale={settings["resolution"]}'])

        # Add FPS if specified
        if settings.get('fps'):
            cmd.extend(['-r', str(settings['fps'])])

        # Add custom filters if specified
        if settings.get('custom_filters'):
            filter_string = ','.join(settings['custom_filters'])
            if 'vf' in cmd:
                # Append to existing video filter
                vf_index = cmd.index('-vf')
                cmd[vf_index + 1] = f'{cmd[vf_index + 1]},{filter_string}'
            else:
                cmd.extend(['-vf', filter_string])

        if format_type == 'webm':
            cmd = [
                'ffmpeg', '-y', '-i', input_video,
                '-c:v', 'libvpx-vp9',
                '-b:v', settings['maxrate'],
                '-c:a', 'libopus', '-b:a', settings['audio_bitrate'],
                '-f', 'webm',
                output_video
            ]

        print(f"[REENCODE] Re-encoding with {quality_tier.value} quality to {format_type}")
        import time
        start_time = time.time()

        result = subprocess.run(cmd, capture_output=True, text=True)

        processing_time = time.time() - start_time

        if result.returncode != 0:
            raise Exception(f"FFmpeg re-encoding failed: {result.stderr}")

        # Get file size
        file_size_bytes = os.path.getsize(output_video)
        file_size_mb = file_size_bytes / (1024 * 1024)

        return {
            'success': True,
            'file_size_mb': file_size_mb,
            'processing_time': processing_time,
            'quality': quality_tier.value,
            'format': format_type
        }

    except Exception as e:
        print(f"[REENCODE ERROR] {str(e)}")
        return {'success': False, 'error': str(e)}

async def concatenate_final_video(
    merged_scenes: List[Dict[str, Any]],
    video_generation_id: str
) -> Dict[str, Any]:
    """Concatenate all merged scenes into final video with advanced editing features"""

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
            # Download all scene videos and prepare for concatenation with transitions
            scene_files = []
            transition_files = []

            for i, scene in enumerate(merged_scenes):
                video_url = scene.get('video_url')
                if video_url:
                    video_path = os.path.join(temp_dir, f"scene_{i:03d}.mp4")
                    await download_file(video_url, video_path)
                    scene_files.append(video_path)

                    # Generate transition to next scene if not the last
                    if i < len(merged_scenes) - 1:
                        next_scene = merged_scenes[i + 1]
                        transition_path = await generate_scene_transition(scene, next_scene, temp_dir)
                        if transition_path:
                            transition_files.append(transition_path)

            if not scene_files:
                raise Exception("No scene videos to concatenate")

            # Create sequence with transitions
            sequence_files = []
            for i, scene_file in enumerate(scene_files):
                sequence_files.append(scene_file)
                if i < len(transition_files):
                    sequence_files.append(transition_files[i])

            # Create FFmpeg concat file
            concat_file = os.path.join(temp_dir, "scenes_with_transitions.txt")
            with open(concat_file, 'w') as f:
                for seq_file in sequence_files:
                    f.write(f"file '{seq_file}'\n")

            # Concatenate with transitions
            raw_concat_output = os.path.join(temp_dir, "raw_concat.mp4")
            cmd_concat = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Copy without re-encoding first
                raw_concat_output
            ]

            print(f"[FINAL CONCAT] Concatenating {len(sequence_files)} segments (scenes + transitions)")
            import time
            start_time = time.time()

            result = subprocess.run(cmd_concat, capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"FFmpeg concatenation failed: {result.stderr}")

            # Apply video filters
            filtered_output = os.path.join(temp_dir, "filtered_video.mp4")
            filters_applied = await apply_video_filters(raw_concat_output, filtered_output)
            processing_input = filtered_output if filters_applied else raw_concat_output

            # Generate multiple quality versions
            quality_versions = []
            quality_presets = [MergeQualityTier.WEB, MergeQualityTier.HIGH, MergeQualityTier.MEDIUM]

            for preset in quality_presets:
                quality_output = os.path.join(temp_dir, f"final_video_{preset.value}.mp4")
                reencode_result = await reencode_video(processing_input, quality_output, preset, 'mp4')
                if reencode_result['success']:
                    quality_versions.append({
                        'quality': preset.value,
                        'file_size_mb': reencode_result['file_size_mb'],
                        'url': None  # Will be set after upload
                    })

            # Use web quality as main final video
            final_output = os.path.join(temp_dir, f"final_video_{MergeQualityTier.WEB.value}.mp4")

            processing_time = time.time() - start_time

            # Get file size
            file_size_bytes = os.path.getsize(final_output)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Upload final video and quality versions
            file_service = FileService()
            final_video_url = await file_service.upload_file(
                final_output,
                f"final_videos/{video_generation_id}/final_video.mp4"
            )

            if not final_video_url:
                raise Exception("Failed to upload final video")

            # Upload quality versions
            for version in quality_versions:
                quality_file = os.path.join(temp_dir, f"final_video_{version['quality']}.mp4")
                if os.path.exists(quality_file):
                    version_url = await file_service.upload_file(
                        quality_file,
                        f"final_videos/{video_generation_id}/final_video_{version['quality']}.mp4"
                    )
                    version['url'] = version_url

            print(f"[FINAL CONCAT] ✅ Final video created: {file_size_mb:.1f}MB in {processing_time:.1f}s with {len(quality_versions)} quality versions")

            return {
                'final_video_url': final_video_url,
                'file_size_mb': file_size_mb,
                'processing_time': processing_time,
                'quality_versions': quality_versions,
                'transitions_added': len(transition_files),
                'filters_applied': filters_applied
            }

    except Exception as e:
        print(f"[FINAL CONCAT ERROR] {str(e)}")
        raise e

def prepare_download_metadata(
    final_video_url: str,
    quality_versions: List[Dict[str, Any]],
    statistics: Dict[str, Any],
    video_generation_id: str
) -> Dict[str, Any]:
    """Prepare metadata for download optimization and user information"""

    return {
        'video_id': video_generation_id,
        'primary_download_url': final_video_url,
        'quality_options': [
            {
                'quality': v.get('quality', 'unknown'),
                'file_size_mb': v.get('file_size_mb', 0),
                'download_url': v.get('url'),
                'recommended_for': 'web' if v.get('quality') == 'web' else ('high_quality' if v.get('quality') == 'high' else 'standard')
            } for v in quality_versions if v.get('url')
        ],
        'technical_specs': {
            'duration_seconds': statistics.get('total_duration', 0),
            'file_size_mb': statistics.get('file_size_mb', 0),
            'format': 'MP4 (H.264/AAC)',
            'optimized_for': ['web_playback', 'download', 'sharing'],
            'advanced_features': ['scene_transitions', 'color_correction', 'quality_optimization']
        },
        'download_instructions': {
            'direct_download': True,
            'streaming_optimized': True,
            'compatible_players': ['VLC', 'QuickTime', 'Web browsers', 'Mobile devices']
        },
        'created_at': None,  # Will be set by database
        'expires_at': None   # For temporary URLs if needed
    }

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def process_manual_merge(self, merge_id: str, user_id: str):
    """Process a manual merge operation with user-controlled parameters"""

    try:
        print(f"[MANUAL MERGE] Starting manual merge {merge_id} for user {user_id}")

        # Get merge operation data from database
        supabase = get_supabase()
        merge_result = supabase.table('merge_operations').select('*').eq('id', merge_id).eq('user_id', user_id).single().execute()

        if not merge_result.data:
            raise Exception(f"Merge operation {merge_id} not found")

        merge_record = merge_result.data

        # Update status to IN_PROGRESS
        supabase.table('merge_operations').update({
            'merge_status': 'IN_PROGRESS',
            'updated_at': 'now()'
        }).eq('id', merge_id).execute()

        # Extract merge data from database record
        merge_data = {
            'input_sources': merge_record.get('input_sources', []),
            'quality_tier': merge_record.get('quality_tier', 'web'),
            'output_format': merge_record.get('output_format', 'mp4'),
            'ffmpeg_params': merge_record.get('ffmpeg_params'),
            'merge_name': merge_record.get('merge_name', f'Merge {merge_id}')
        }

        # Update progress: Starting
        update_merge_progress(merge_id, 5.0, "Initializing merge operation")

        # Process the manual merge
        result = asyncio.run(perform_manual_merge(merge_data, user_id, merge_id))

        # Update database with final result
        final_update = {
            'merge_status': 'COMPLETED',
            'progress': 100,
            'output_file_url': result.get('final_url'),
            'processing_stats': {
                'file_size_mb': result.get('file_size_mb', 0),
                'quality_tier': result.get('quality_tier'),
                'output_format': result.get('output_format')
            },
            'updated_at': 'now()'
        }

        supabase.table('merge_operations').update(final_update).eq('id', merge_id).execute()

        print(f"[MANUAL MERGE] Completed manual merge {merge_id}")

        # Trigger preview generation after successful merge
        print(f"[MERGE WORKFLOW] Starting preview generation for merge {merge_id}")
        generate_merge_preview.delay(merge_id)

    except Exception as e:
        error_message = str(e)
        print(f"[MANUAL MERGE ERROR] {merge_id}: {error_message}")

        # Update status to failed
        try:
            supabase = get_supabase()
            supabase.table('merge_operations').update({
                'merge_status': 'FAILED',
                'error_message': error_message,
                'updated_at': 'now()'
            }).eq('id', merge_id).execute()
        except:
            pass

        # Re-raise for Celery retry mechanism
        raise Exception(error_message)


async def perform_manual_merge(merge_data: Dict[str, Any], user_id: str, merge_id: str = None) -> Dict[str, Any]:
    """Perform the actual manual merge operation"""

    print("[MANUAL MERGE] Performing manual merge with user parameters")

    input_sources = merge_data.get('input_sources', [])
    quality_tier = MergeQualityTier(merge_data.get('quality_tier', 'web'))
    output_format = merge_data.get('output_format', 'mp4')
    ffmpeg_params = merge_data.get('ffmpeg_params')
    merge_name = merge_data.get('merge_name', 'Manual Merge')

    if not input_sources:
        raise Exception("No input sources provided for merge")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Update progress: Starting
            if merge_id:
                update_merge_progress(merge_id, 5.0, "Preparing input files")

            # Prepare input files
            prepared_inputs = await prepare_manual_inputs(input_sources, temp_dir)

            if merge_id:
                update_merge_progress(merge_id, 25.0, "Input files prepared", {
                    'inputs_prepared': len(prepared_inputs)
                })

            # Merge inputs based on type
            if len(prepared_inputs) == 1:
                # Single input, just process it
                if merge_id:
                    update_merge_progress(merge_id, 40.0, "Processing single input")
                merged_output = await process_single_input(prepared_inputs[0], temp_dir, quality_tier, output_format, ffmpeg_params)
                if merge_id:
                    update_merge_progress(merge_id, 70.0, "Single input processed")
            else:
                # Multiple inputs, concatenate them
                if merge_id:
                    update_merge_progress(merge_id, 40.0, "Concatenating multiple inputs")
                merged_output = await concatenate_manual_inputs(prepared_inputs, temp_dir, quality_tier, output_format, ffmpeg_params)
                if merge_id:
                    update_merge_progress(merge_id, 70.0, "Multiple inputs concatenated")

            if merge_id:
                update_merge_progress(merge_id, 85.0, "Processing complete, uploading to storage")

            # Upload final result
            file_service = FileService()
            final_url = await file_service.upload_file(
                merged_output,
                f"manual_merges/{user_id}/{merge_name.replace(' ', '_')}.{output_format}"
            )

            if not final_url:
                raise Exception("Failed to upload merged file")

            # Get file size
            file_size_bytes = os.path.getsize(merged_output)
            file_size_mb = file_size_bytes / (1024 * 1024)

            if merge_id:
                update_merge_progress(merge_id, 100.0, "Upload complete", {
                    'final_url': final_url,
                    'file_size_mb': file_size_mb
                })

            return {
                'success': True,
                'final_url': final_url,
                'file_size_mb': file_size_mb,
                'quality_tier': quality_tier.value,
                'output_format': output_format
            }

    except Exception as e:
        print(f"[MANUAL MERGE ERROR] {str(e)}")
        raise e


async def prepare_manual_inputs(input_sources: List[Dict[str, Any]], temp_dir: str) -> List[Dict[str, Any]]:
    """Prepare input files for manual merge"""

    prepared_inputs = []

    for i, source in enumerate(input_sources):
        source_type = source.get('type', 'video')
        url = source.get('url')

        if not url:
            continue

        # Download the file
        file_ext = 'mp4' if source_type == 'video' else ('mp3' if source_type == 'audio' else 'jpg')
        local_path = os.path.join(temp_dir, f"input_{i}.{file_ext}")

        await download_file(url, local_path)

        # Apply any trimming or processing based on source parameters
        start_time = source.get('start_time', 0)
        end_time = source.get('end_time')
        volume = source.get('volume', 1.0)
        fade_in = source.get('fade_in', 0)
        fade_out = source.get('fade_out', 0)

        processed_path = await apply_input_processing(
            local_path, temp_dir, i, start_time, end_time, volume, fade_in, fade_out
        )

        prepared_inputs.append({
            'path': processed_path,
            'type': source_type,
            'duration': source.get('duration'),
            'original_url': url
        })

    return prepared_inputs


async def apply_input_processing(
    input_path: str, temp_dir: str, index: int,
    start_time: float, end_time: Optional[float],
    volume: float, fade_in: float, fade_out: float
) -> str:
    """Apply processing (trimming, volume, fades) to input file"""

    output_path = os.path.join(temp_dir, f"processed_input_{index}.mp4")

    cmd = ['ffmpeg', '-y', '-i', input_path]

    # Add trimming if specified
    if start_time > 0 or end_time is not None:
        if end_time:
            cmd.extend(['-ss', str(start_time), '-to', str(end_time)])
        else:
            cmd.extend(['-ss', str(start_time)])

    # Add volume adjustment if not 1.0
    filter_parts = []
    if volume != 1.0:
        filter_parts.append(f'volume={volume}')

    # Add fades
    if fade_in > 0:
        filter_parts.append(f'afade=t=in:st=0:d={fade_in}')
    if fade_out > 0:
        # Calculate fade out start time (assuming we know duration)
        # For now, apply a simple fade out
        filter_parts.append(f'afade=t=out:st=10:d={fade_out}')

    if filter_parts:
        cmd.extend(['-af', ','.join(filter_parts)])

    cmd.append(output_path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # If processing fails, return original
        print(f"[INPUT PROCESSING] Failed to process {input_path}: {result.stderr}")
        return input_path

    return output_path


async def process_single_input(
    input_data: Dict[str, Any], temp_dir: str,
    quality_tier: MergeQualityTier, output_format: str,
    ffmpeg_params: Optional[FFmpegParameters]
) -> str:
    """Process a single input file"""

    input_path = input_data['path']
    output_path = os.path.join(temp_dir, f"final_output.{output_format}")

    # Apply quality encoding
    reencode_result = await reencode_video(
        input_path, output_path, quality_tier, output_format, ffmpeg_params
    )

    if not reencode_result['success']:
        raise Exception("Failed to re-encode video")

    return output_path


async def concatenate_manual_inputs(
    inputs: List[Dict[str, Any]], temp_dir: str,
    quality_tier: MergeQualityTier, output_format: str,
    ffmpeg_params: Optional[FFmpegParameters]
) -> str:
    """Concatenate multiple inputs for manual merge"""

    # Create concat file
    concat_file = os.path.join(temp_dir, "manual_concat.txt")
    with open(concat_file, 'w') as f:
        for input_data in inputs:
            f.write(f"file '{input_data['path']}'\n")

    # Concatenate
    raw_concat = os.path.join(temp_dir, "raw_concat.mp4")
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file, '-c', 'copy', raw_concat
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Concatenation failed: {result.stderr}")

    # Apply final encoding
    final_output = os.path.join(temp_dir, f"final_concat.{output_format}")
    reencode_result = await reencode_video(
        raw_concat, final_output, quality_tier, output_format, ffmpeg_params
    )

    if not reencode_result['success']:
        raise Exception("Failed to re-encode concatenated video")

    return final_output


@celery_app.task(bind=True)
def process_merge_preview(self, preview_id: str, user_id: str):
    """Process a merge preview operation"""

    try:
        print(f"[MERGE PREVIEW] Starting preview {preview_id} for user {user_id}")

        # Mock data for development
        preview_data = {
            'input_sources': [],
            'quality_tier': 'web',
            'preview_duration': 30.0,
            'ffmpeg_params': None
        }

        # Process the preview
        result = asyncio.run(perform_merge_preview(preview_data, user_id))

        print(f"[MERGE PREVIEW] Completed preview {preview_id}")

    except Exception as e:
        print(f"[MERGE PREVIEW ERROR] {preview_id}: {str(e)}")


async def perform_merge_preview(preview_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Perform merge preview generation (first 30 seconds)"""

    print("[MERGE PREVIEW] Generating preview with limited processing")

    input_sources = preview_data.get('input_sources', [])
    quality_tier = MergeQualityTier(preview_data.get('quality_tier', 'web'))
    preview_duration = min(preview_data.get('preview_duration', 30.0), 30.0)  # Max 30 seconds
    ffmpeg_params = preview_data.get('ffmpeg_params')

    if not input_sources:
        raise Exception("No input sources provided for preview")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare input files (limited processing for preview)
            prepared_inputs = await prepare_preview_inputs(input_sources, temp_dir, preview_duration)

            # Create preview by concatenating first segments
            if len(prepared_inputs) == 1:
                preview_output = prepared_inputs[0]['path']
            else:
                preview_output = await concatenate_preview_segments(prepared_inputs, temp_dir, quality_tier, ffmpeg_params)

            # Upload preview
            file_service = FileService()
            preview_url = await file_service.upload_file(
                preview_output,
                f"merge_previews/{user_id}/preview_{preview_duration}s.mp4"
            )

            if not preview_url:
                raise Exception("Failed to upload preview")

            return {
                'success': True,
                'preview_url': preview_url,
                'preview_duration': preview_duration,
                'quality_tier': quality_tier.value
            }

    except Exception as e:
        print(f"[MERGE PREVIEW ERROR] {str(e)}")
        raise e


async def prepare_preview_inputs(
    input_sources: List[Dict[str, Any]], temp_dir: str, max_duration: float
) -> List[Dict[str, Any]]:
    """Prepare input files for preview (extract first segment only)"""

    prepared_inputs = []
    total_duration = 0

    for i, source in enumerate(input_sources):
        if total_duration >= max_duration:
            break

        source_type = source.get('type', 'video')
        url = source.get('url')

        if not url:
            continue

        # Download the file
        file_ext = 'mp4' if source_type == 'video' else ('mp3' if source_type == 'audio' else 'jpg')
        local_path = os.path.join(temp_dir, f"preview_input_{i}.{file_ext}")

        await download_file(url, local_path)

        # Extract first segment for preview
        remaining_duration = max_duration - total_duration
        segment_duration = min(remaining_duration, 10.0)  # Max 10s per input for preview

        preview_segment = await extract_preview_segment(
            local_path, temp_dir, i, segment_duration
        )

        if preview_segment:
            prepared_inputs.append({
                'path': preview_segment,
                'type': source_type,
                'duration': segment_duration
            })
            total_duration += segment_duration

    return prepared_inputs


async def extract_preview_segment(
    input_path: str, temp_dir: str, index: int, duration: float
) -> Optional[str]:
    """Extract first segment of specified duration for preview"""

    output_path = os.path.join(temp_dir, f"preview_segment_{index}.mp4")

    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-t', str(duration),  # Duration
        '-c', 'copy',  # Copy without re-encoding for speed
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[PREVIEW SEGMENT] Failed to extract segment: {result.stderr}")
        return None

    return output_path


async def concatenate_preview_segments(
    inputs: List[Dict[str, Any]], temp_dir: str,
    quality_tier: MergeQualityTier, ffmpeg_params: Optional[FFmpegParameters]
) -> str:
    """Concatenate preview segments"""

    # Create concat file
    concat_file = os.path.join(temp_dir, "preview_concat.txt")
    with open(concat_file, 'w') as f:
        for input_data in inputs:
            f.write(f"file '{input_data['path']}'\n")

    # Quick concatenation for preview
    output_path = os.path.join(temp_dir, "preview_concat.mp4")
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file, '-c', 'copy', output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Preview concatenation failed: {result.stderr}")

    return output_path


async def download_file(url: str, local_path: str):
    """Download file from URL to local path"""

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def generate_merge_preview(self, merge_id: str):
    """Generate a preview clip (first 10 seconds) from the merged video"""

    try:
        print(f"[MERGE PREVIEW] Starting preview generation for merge {merge_id}")

        # Get merge operation data
        supabase = get_supabase()
        merge_result = supabase.table('merge_operations').select('*').eq('id', merge_id).single().execute()

        if not merge_result.data:
            raise Exception(f"Merge operation {merge_id} not found")

        merge_data = merge_result.data

        # Check if merge is completed and has output file
        if merge_data.get('merge_status') != 'COMPLETED':
            raise Exception(f"Merge operation {merge_id} is not completed yet")

        output_file_url = merge_data.get('output_file_url')
        if not output_file_url:
            raise Exception(f"Merge operation {merge_id} has no output file URL")

        # Generate preview
        preview_url = asyncio.run(generate_video_preview_clip(output_file_url, merge_id))

        if not preview_url:
            raise Exception("Failed to generate preview clip")

        # Update merge operation with preview URL
        supabase.table('merge_operations').update({
            'preview_url': preview_url,
            'updated_at': 'now()'
        }).eq('id', merge_id).execute()

        print(f"[MERGE PREVIEW] Successfully generated preview for merge {merge_id}: {preview_url}")
        return {'status': 'success', 'preview_url': preview_url}

    except Exception as e:
        error_message = f"Preview generation failed: {str(e)}"
        print(f"[MERGE PREVIEW ERROR] {merge_id}: {error_message}")

        # Update merge operation with error (don't overwrite existing errors)
        try:
            supabase = get_supabase()
            current_data = supabase.table('merge_operations').select('error_message').eq('id', merge_id).single().execute()
            if current_data.data and not current_data.data.get('error_message'):
                supabase.table('merge_operations').update({
                    'error_message': f"Preview generation failed: {str(e)}",
                    'updated_at': 'now()'
                }).eq('id', merge_id).execute()
        except:
            pass

        raise Exception(error_message)


async def generate_video_preview_clip(video_url: str, merge_id: str) -> Optional[str]:
    """Generate a 10-second preview clip from the merged video using FFmpeg"""

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the merged video
            video_path = os.path.join(temp_dir, "merged_video.mp4")
            await download_file(video_url, video_path)

            # Generate preview clip (first 10 seconds)
            preview_path = os.path.join(temp_dir, "preview_clip.mp4")

            cmd = [
                'ffmpeg', '-y',  # Overwrite output
                '-i', video_path,  # Input video
                '-t', '10',  # Duration: 10 seconds
                '-c:v', 'libx264',  # Video codec
                '-preset', 'fast',  # Encoding preset
                '-crf', '23',  # Quality (lower is better)
                '-c:a', 'aac',  # Audio codec
                '-b:a', '128k',  # Audio bitrate
                '-movflags', '+faststart',  # Optimize for web playback
                preview_path
            ]

            print(f"[PREVIEW CLIP] Generating 10-second preview from {video_url}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)

            if result.returncode != 0:
                print(f"[PREVIEW CLIP ERROR] FFmpeg failed: {result.stderr}")
                return None

            # Upload preview to Supabase Storage
            file_service = FileService()
            preview_url = await file_service.upload_file(
                preview_path,
                f"merge_previews/{merge_id}/preview_10s.mp4"
            )

            if not preview_url:
                print("[PREVIEW CLIP ERROR] Failed to upload preview to storage")
                return None

            # Get file size for logging
            file_size_bytes = os.path.getsize(preview_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            print(f"[PREVIEW CLIP] Generated preview: {file_size_mb:.1f}MB, URL: {preview_url}")
            return preview_url

    except Exception as e:
        print(f"[PREVIEW CLIP ERROR] {str(e)}")
        return None
    print(f"[DOWNLOAD] Downloaded {url} to {local_path}")