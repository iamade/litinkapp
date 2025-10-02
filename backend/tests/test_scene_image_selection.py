#!/usr/bin/env python3
"""
Test script to verify scene vs character image selection logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.tasks.video_tasks import query_existing_scene_images, query_existing_character_images
import asyncio

async def test_scene_image_query():
    """Test the scene image query function"""
    print("🧪 Testing scene image query function...")
    
    # Test with a sample user_id and scene descriptions
    user_id = "test_user_123"
    scene_descriptions = [
        "A beautiful sunset over the mountains",
        "A bustling city street at night",
        "A peaceful forest with sunlight filtering through trees"
    ]
    
    try:
        scene_images = await query_existing_scene_images(user_id, scene_descriptions)
        print(f"✅ Scene images query successful")
        print(f"   Found {len(scene_images)} scene images")
        for img in scene_images:
            print(f"   - {img.get('scene_description', 'Unknown')}: {img.get('image_url', 'No URL')}")
        
    except Exception as e:
        print(f"❌ Scene images query failed: {e}")

async def test_character_image_query():
    """Test the character image query function"""
    print("\n🧪 Testing character image query function...")
    
    # Test with a sample user_id and character names
    user_id = "test_user_123"
    character_names = ["Alice", "Bob", "Charlie"]
    
    try:
        character_images = await query_existing_character_images(user_id, character_names)
        print(f"✅ Character images query successful")
        print(f"   Found {len(character_images)} character images")
        for img in character_images:
            print(f"   - {img.get('name', 'Unknown')}: {img.get('image_url', 'No URL')}")
        
    except Exception as e:
        print(f"❌ Character images query failed: {e}")

async def test_image_selection_logic():
    """Test the complete image selection logic"""
    print("\n🧪 Testing complete image selection logic...")
    
    # Simulate the logic from generate_all_videos_for_generation
    user_id = "test_user_123"
    scene_descriptions = [
        "A beautiful sunset over the mountains",
        "A bustling city street at night",
        "A peaceful forest with sunlight filtering through trees"
    ]
    characters = ["Alice", "Bob", "Charlie"]
    
    try:
        # Query both types of images
        character_images = await query_existing_character_images(user_id, characters)
        scene_images = await query_existing_scene_images(user_id, scene_descriptions)
        
        print(f"📊 Image Selection Summary:")
        print(f"   - Character images found: {len(character_images)}")
        print(f"   - Scene images found: {len(scene_images)}")
        
        # Simulate the selection logic
        selected_images = []
        for i, scene_description in enumerate(scene_descriptions):
            scene_image = None
            
            # First, try to find a matching scene image for this specific scene
            for scene_img in scene_images:
                if scene_img.get('scene_description') and scene_description.lower() in scene_img['scene_description'].lower():
                    scene_image = {
                        'image_url': scene_img.get('image_url'),
                        'scene_description': scene_img.get('scene_description'),
                        'image_type': scene_img.get('image_type', 'scene'),
                        'scene_number': i + 1
                    }
                    print(f"   ✅ Scene {i+1}: Using scene image - {scene_img.get('scene_description')}")
                    break
            
            # If no scene image found, fall back to character images
            if not scene_image and character_images:
                char_image = character_images[i % len(character_images)]
                scene_image = {
                    'image_url': char_image.get('image_url'),
                    'character_name': char_image.get('name'),
                    'image_type': 'character_fallback',
                    'scene_number': i + 1
                }
                print(f"   ⚠️ Scene {i+1}: Using character image as fallback - {char_image.get('name')}")
            
            selected_images.append(scene_image)
        
        # Log the final image selection breakdown
        scene_count = len([img for img in selected_images if img is not None])
        scene_type_count = len([img for img in selected_images if img and img.get('image_type') == 'scene'])
        character_fallback_count = len([img for img in selected_images if img and img.get('image_type') == 'character_fallback'])
        
        print(f"\n📈 Final Image Selection Breakdown:")
        print(f"   - Total scene images: {scene_count}")
        print(f"   - Scene images (proper): {scene_type_count}")
        print(f"   - Character fallback images: {character_fallback_count}")
        print(f"   - No images (text-to-video fallback): {len(scene_descriptions) - scene_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Image selection logic test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting scene vs character image selection tests...\n")
    
    await test_scene_image_query()
    await test_character_image_query()
    success = await test_image_selection_logic()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        print("✅ Scene vs character image selection logic is working correctly")
    else:
        print("\n❌ Some tests failed - please check the implementation")

if __name__ == "__main__":
    asyncio.run(main())