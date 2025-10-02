#!/usr/bin/env python3
"""
Test script for enhanced script parser functionality only
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.script_parser import ScriptParser

def test_enhanced_script_parsing():
    """Test the enhanced script parsing with example script"""
    
    print("🧪 Testing Enhanced Script Parser")
    print("=" * 50)
    
    # Example script with camera movements, character actions, and dialogue
    example_script = """
SCENE 1 - DURSLEY HOUSEHOLD - DAY

Wide shot of the Dursley household. Camera zooms in on Vernon Dursley (selecting his tie). 
Petunia Dursley (muttering to herself) says: "That Lily Potter... she's so different." 
Camera pans to show their neat and tidy home. Vernon (looking concerned) adjusts his mustache. 
Close-up on Petunia (gossiping while tending to Dudley).

VERNON
I don't want any of that... that magic nonsense in this house!

PETUNIA
(scoffs)
As if we'd allow it. We're perfectly normal, thank you very much.

Camera follows Vernon as he walks to the window. He looks out at the street.

VERNON
(whispering)
They're out there, you know. Watching us.

FADE OUT
"""
    
    print("📝 Example Script:")
    print(example_script)
    print("=" * 50)
    
    # Parse script for enhanced prompt generation
    script_parser = ScriptParser()
    characters = ["VERNON", "PETUNIA"]
    
    parsed_components = script_parser.parse_script_for_video_prompt(
        script=example_script,
        characters=characters
    )
    
    print("🔍 Parsed Components:")
    print(f"- Scene descriptions: {len(parsed_components['scene_descriptions'])}")
    for scene in parsed_components['scene_descriptions']:
        print(f"  - Scene {scene['scene_number']}: {scene['description'][:50]}...")
    
    print(f"- Camera movements: {parsed_components['camera_movements']}")
    
    print(f"- Character actions: {len(parsed_components['character_actions'])}")
    for action in parsed_components['character_actions']:
        print(f"  - {action['character']}: {action['action']}")
    
    print(f"- Character dialogues: {len(parsed_components['character_dialogues'])}")
    for dialogue in parsed_components['character_dialogues']:
        print(f"  - {dialogue['attributed_dialogue']}")
    
    print(f"- Scene transitions: {parsed_components['scene_transitions']}")
    print("=" * 50)
    
    # Test enhanced prompt generation (without video service)
    print("🎬 Enhanced Video Prompt (Generated from parsed components):")
    
    prompt_parts = []
    
    # Add scene description
    scene_description = "The Dursley household is contrasted with the magical world as Vernon and Petunia Dursley struggle to come to terms with the death of their sister Lily and her family"
    prompt_parts.append(f"Scene: {scene_description}")
    
    # Add camera movements
    if parsed_components['camera_movements']:
        camera_text = "Camera movements: " + ", ".join(parsed_components['camera_movements'])
        prompt_parts.append(camera_text)
    
    # Add character actions
    if parsed_components['character_actions']:
        actions_by_character = {}
        for action in parsed_components['character_actions']:
            character = action.get('character', 'Unknown')
            action_text = action.get('action', '')
            if character not in actions_by_character:
                actions_by_character[character] = []
            actions_by_character[character].append(action_text)
        
        for character, actions in actions_by_character.items():
            actions_text = f"{character} ({', '.join(actions)})"
            prompt_parts.append(actions_text)
    
    # Add character dialogues with attribution
    if parsed_components['character_dialogues']:
        for dialogue in parsed_components['character_dialogues']:
            attributed_dialogue = dialogue.get('attributed_dialogue', '')
            if attributed_dialogue:
                prompt_parts.append(attributed_dialogue)
    
    # Add scene transitions
    if parsed_components['scene_transitions']:
        transitions_text = "Scene transitions: " + ", ".join(parsed_components['scene_transitions'])
        prompt_parts.append(transitions_text)
    
    # Add quality modifiers
    quality_modifiers = [
        "cinematic realism, natural movement, photorealistic details, smooth camera motion",
        "High quality video production, smooth motion, professional videography",
        "engaging visual storytelling, seamless transitions, cinematic composition"
    ]
    prompt_parts.extend(quality_modifiers)
    
    # Combine all parts
    enhanced_prompt = "\n".join(prompt_parts)
    
    print(enhanced_prompt)
    print("=" * 50)
    
    print("✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    test_enhanced_script_parsing()