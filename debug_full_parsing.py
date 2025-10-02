#!/usr/bin/env python3
"""
Debug the full parsing process to see what's happening
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app', 'services'))

from script_parser import ScriptParser

def test_full_parsing():
    """Test the full parsing process with detailed debugging"""
    parser = ScriptParser()
    
    script = """
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
    
    characters = ["VERNON", "PETUNIA"]
    
    print("🔍 DEBUG FULL PARSING PROCESS")
    print("=" * 60)
    
    print("📝 Script lines:")
    lines = script.split('\n')
    for i, line in enumerate(lines, 1):
        print(f"  Line {i}: '{line}'")
    
    print("\n🧪 Testing parse_script_for_video_prompt:")
    result = parser.parse_script_for_video_prompt(script, characters)
    
    print(f"\n📊 Final Result:")
    print(f"- Scenes: {len(result['scene_descriptions'])}")
    print(f"- Camera movements: {len(result['camera_movements'])}")
    print(f"- Character actions: {len(result['character_actions'])}")
    print(f"- Character dialogues: {len(result['character_dialogues'])}")
    print(f"- Scene transitions: {len(result['scene_transitions'])}")
    
    print(f"\n🔍 Detailed Results:")
    print(f"Camera movements: {result['camera_movements']}")
    print(f"Character actions: {result['character_actions']}")
    print(f"Character dialogues: {result['character_dialogues']}")

if __name__ == "__main__":
    test_full_parsing()