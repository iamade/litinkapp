#!/usr/bin/env python3
"""
Test script to verify audio-scene association and mapping functionality.
This script tests the prepare_audio_tracks function to ensure it correctly
maps audio files to their corresponding scenes.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.tasks.merge_tasks import prepare_audio_tracks

async def test_audio_scene_mapping():
    """Test the audio scene mapping functionality"""
    
    print("🧪 Testing Audio-Scene Mapping...")
    
    # Mock audio files data structure (similar to what would come from database)
    mock_audio_files = {
        'narrator': [
            {
                'audio_url': 'http://example.com/narrator1.mp3',
                'scene_id': 'scene_1',  # Top level scene_id
                'metadata': {'scene': 1}  # Also in metadata for backward compatibility
            },
            {
                'audio_url': 'http://example.com/narrator2.mp3',
                'scene_id': 'scene_2',
                'metadata': {'scene': 2}
            }
        ],
        'characters': [
            {
                'audio_url': 'http://example.com/character1.mp3',
                'scene_id': 'scene_1',
                'metadata': {'scene': 1}
            },
            {
                'audio_url': 'http://example.com/character2.mp3',
                'scene_id': 'scene_2',
                'metadata': {'scene': 2}
            }
        ],
        'sound_effects': [
            {
                'audio_url': 'http://example.com/sfx1.mp3',
                'scene_id': 'scene_1',
                'metadata': {'scene': 1}
            }
        ]
    }
    
    # Mock scene videos
    mock_scene_videos = [
        {'scene_id': 'scene_1', 'video_url': 'http://example.com/scene1.mp4'},
        {'scene_id': 'scene_2', 'video_url': 'http://example.com/scene2.mp4'}
    ]
    
    print("📋 Test Data:")
    print(f"- Narrator files: {len(mock_audio_files['narrator'])}")
    print(f"- Character files: {len(mock_audio_files['characters'])}")
    print(f"- Sound effect files: {len(mock_audio_files['sound_effects'])}")
    print(f"- Scene videos: {len(mock_scene_videos)}")
    
    # Test the prepare_audio_tracks function
    result = await prepare_audio_tracks(mock_audio_files, mock_scene_videos)
    
    print("\n✅ Test Results:")
    print(f"Total audio files processed: {result['summary']['total_audio_files']}")
    print(f"Scenes with audio: {result['summary']['scenes_with_audio']}")
    
    # Check scene mapping
    scene_audio_tracks = result['scene_audio_tracks']
    print(f"\n🎯 Scene Audio Mapping:")
    for scene_id, tracks in scene_audio_tracks.items():
        narrator_count = len(tracks['narrator'])
        character_count = len(tracks['characters'])
        sfx_count = len(tracks['sound_effects'])
        print(f"Scene {scene_id}: {narrator_count} narrator, {character_count} character, {sfx_count} sfx files")
    
    # Verify the mapping is correct
    expected_scene_1_audio = 3  # 1 narrator + 1 character + 1 sfx
    expected_scene_2_audio = 2  # 1 narrator + 1 character
    
    scene_1_total = (len(scene_audio_tracks.get('scene_1', {}).get('narrator', [])) +
                    len(scene_audio_tracks.get('scene_1', {}).get('characters', [])) +
                    len(scene_audio_tracks.get('scene_1', {}).get('sound_effects', [])))
    
    scene_2_total = (len(scene_audio_tracks.get('scene_2', {}).get('narrator', [])) +
                    len(scene_audio_tracks.get('scene_2', {}).get('characters', [])) +
                    len(scene_audio_tracks.get('scene_2', {}).get('sound_effects', [])))
    
    print(f"\n🔍 Verification:")
    print(f"Scene 1: Expected {expected_scene_1_audio} audio files, Got {scene_1_total}")
    print(f"Scene 2: Expected {expected_scene_2_audio} audio files, Got {scene_2_total}")
    
    if (scene_1_total == expected_scene_1_audio and 
        scene_2_total == expected_scene_2_audio and
        len(scene_audio_tracks) == 2):
        print("\n🎉 SUCCESS: Audio-scene mapping is working correctly!")
        return True
    else:
        print("\n❌ FAILURE: Audio-scene mapping is not working as expected!")
        return False

async def test_backward_compatibility():
    """Test backward compatibility with metadata-based scene mapping"""
    
    print("\n🧪 Testing Backward Compatibility (metadata-based scene mapping)...")
    
    # Mock audio files with only metadata scene info (old format)
    mock_audio_files_old_format = {
        'narrator': [
            {
                'audio_url': 'http://example.com/narrator1.mp3',
                'metadata': {'scene': 1}  # Only in metadata
            }
        ],
        'characters': [
            {
                'audio_url': 'http://example.com/character1.mp3',
                'metadata': {'scene': 1}  # Only in metadata
            }
        ]
    }
    
    mock_scene_videos = [
        {'scene_id': 'scene_1', 'video_url': 'http://example.com/scene1.mp4'}
    ]
    
    result = await prepare_audio_tracks(mock_audio_files_old_format, mock_scene_videos)
    
    scene_audio_tracks = result['scene_audio_tracks']
    scene_1_total = (len(scene_audio_tracks.get('scene_1', {}).get('narrator', [])) +
                    len(scene_audio_tracks.get('scene_1', {}).get('characters', [])))
    
    print(f"Backward compatibility test: {scene_1_total} audio files mapped to scene_1")
    
    if scene_1_total == 2:
        print("✅ SUCCESS: Backward compatibility working!")
        return True
    else:
        print("❌ FAILURE: Backward compatibility broken!")
        return False

if __name__ == "__main__":
    print("🔧 Audio-Scene Association Test Suite")
    print("=" * 50)
    
    # Run tests
    test1_success = asyncio.run(test_audio_scene_mapping())
    test2_success = asyncio.run(test_backward_compatibility())
    
    print("\n" + "=" * 50)
    if test1_success and test2_success:
        print("🎊 ALL TESTS PASSED! Audio-scene association is working correctly.")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED! Check the implementation.")
        sys.exit(1)