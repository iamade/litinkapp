#!/usr/bin/env python3
"""
Test script for enhanced video generation prompt structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.script_parser import ScriptParser
from app.services.modelslab_v7_video_service import ModelsLabV7VideoService

def test_enhanced_prompt_generation():
    """Test the enhanced prompt generation with example script"""
    
    print("🧪 Testing Enhanced Video Prompt Generation")
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
    print(f"- Camera movements: {parsed_components['camera_movements']}")
    print(f"- Character actions: {len(parsed_components['character_actions'])}")
    for action in parsed_components['character_actions']:
        print(f"  - {action['character']}: {action['action']}")
    print(f"- Character dialogues: {len(parsed_components['character_dialogues'])}")
    for dialogue in parsed_components['character_dialogues']:
        print(f"  - {dialogue['attributed_dialogue']}")
    print(f"- Scene transitions: {parsed_components['scene_transitions']}")
    print("=" * 50)
    
    # Create enhanced prompt
    video_service = ModelsLabV7VideoService()
    
    scene_description = "The Dursley household is contrasted with the magical world as Vernon and Petunia Dursley struggle to come to terms with the death of their sister Lily and her family"
    
    enhanced_prompt = video_service._create_enhanced_video_prompt(
        scene_description=scene_description,
        style="cinematic",
        camera_movements=parsed_components['camera_movements'],
        character_actions=parsed_components['character_actions'],
        character_dialogues=parsed_components['character_dialogues'],
        scene_transitions=parsed_components['scene_transitions']
    )
    
    print("🎬 Enhanced Video Prompt:")
    print(enhanced_prompt)
    print("=" * 50)
    
    # Compare with old prompt
    old_prompt = video_service._create_scene_video_prompt(scene_description, "cinematic")
    print("📋 Old Prompt (for comparison):")
    print(old_prompt)
    print("=" * 50)
    
    print("✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    test_enhanced_prompt_generation()