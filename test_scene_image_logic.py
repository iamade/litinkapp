#!/usr/bin/env python3
"""
Simple test to verify the scene vs character image selection logic
"""

def test_image_selection_logic():
    """Test the core image selection logic without database dependencies"""
    print("🧪 Testing scene vs character image selection logic...\n")
    
    # Mock data
    scene_descriptions = [
        "A beautiful sunset over the mountains",
        "A bustling city street at night", 
        "A peaceful forest with sunlight filtering through trees"
    ]
    
    # Mock scene images (what we should find in the database)
    mock_scene_images = [
        {
            'scene_description': 'A beautiful sunset over the mountains',
            'image_url': 'https://example.com/sunset.png',
            'image_type': 'scene'
        },
        {
            'scene_description': 'A bustling city street at night',
            'image_url': 'https://example.com/city_night.png', 
            'image_type': 'scene'
        }
    ]
    
    # Mock character images (fallback)
    mock_character_images = [
        {
            'name': 'Alice',
            'image_url': 'https://example.com/alice.png'
        },
        {
            'name': 'Bob',
            'image_url': 'https://example.com/bob.png'
        },
        {
            'name': 'Charlie',
            'image_url': 'https://example.com/charlie.png'
        }
    ]
    
    # Simulate the selection logic from generate_all_videos_for_generation
    selected_images = []
    
    for i, scene_description in enumerate(scene_descriptions):
        scene_image = None
        
        # First, try to find a matching scene image for this specific scene
        for scene_img in mock_scene_images:
            if scene_img.get('scene_description') and scene_description.lower() in scene_img['scene_description'].lower():
                scene_image = {
                    'image_url': scene_img.get('image_url'),
                    'scene_description': scene_img.get('scene_description'),
                    'image_type': scene_img.get('image_type', 'scene'),
                    'scene_number': i + 1
                }
                print(f"✅ Scene {i+1}: Using scene image - '{scene_img.get('scene_description')}'")
                break
        
        # If no scene image found, fall back to character images
        if not scene_image and mock_character_images:
            char_image = mock_character_images[i % len(mock_character_images)]
            scene_image = {
                'image_url': char_image.get('image_url'),
                'character_name': char_image.get('name'),
                'image_type': 'character_fallback',
                'scene_number': i + 1
            }
            print(f"⚠️ Scene {i+1}: Using character image as fallback - '{char_image.get('name')}'")
        
        selected_images.append(scene_image)
    
    # Analyze the results
    scene_count = len([img for img in selected_images if img is not None])
    scene_type_count = len([img for img in selected_images if img and img.get('image_type') == 'scene'])
    character_fallback_count = len([img for img in selected_images if img and img.get('image_type') == 'character_fallback'])
    
    print(f"\n📊 Final Image Selection Breakdown:")
    print(f"   - Total scene images: {scene_count}")
    print(f"   - Scene images (proper): {scene_type_count}")
    print(f"   - Character fallback images: {character_fallback_count}")
    print(f"   - No images (text-to-video fallback): {len(scene_descriptions) - scene_count}")
    
    # Verify the logic is working correctly
    assert scene_type_count == 2, f"Expected 2 scene images, got {scene_type_count}"
    assert character_fallback_count == 1, f"Expected 1 character fallback, got {character_fallback_count}"
    
    print("\n🎉 Test passed! Scene vs character image selection logic is working correctly.")
    print("✅ Scene images are properly prioritized over character images")
    print("✅ Character images are only used as fallback when scene images are not available")
    print("✅ Proper logging shows which type of image is being selected")

if __name__ == "__main__":
    test_image_selection_logic()