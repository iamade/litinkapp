#!/usr/bin/env python3
"""
Debug script to test the enhanced script parser functionality
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app', 'services'))

from script_parser import ScriptParser

def test_camera_movement_detection():
    """Test camera movement detection specifically"""
    parser = ScriptParser()
    
    test_texts = [
        "Wide shot of the Dursley household.",
        "Camera zooms in on Vernon Dursley.",
        "Camera pans to show their neat and tidy home.",
        "Close-up on Petunia.",
        "Camera follows Vernon as he walks to the window."
    ]
    
    print("🧪 Testing Camera Movement Detection")
    print("=" * 50)
    
    for i, text in enumerate(test_texts, 1):
        movements = parser._extract_camera_movements(text)
        print(f"Test {i}: '{text}'")
        print(f"  → Detected movements: {movements}")
        print()

def test_dialogue_detection():
    """Test dialogue detection specifically"""
    parser = ScriptParser()
    
    test_lines = [
        "VERNON: I don't want any of that... that magic nonsense in this house!",
        "PETUNIA: As if we'd allow it. We're perfectly normal, thank you very much.",
        'Petunia Dursley says: "That Lily Potter... she\'s so different."',
        "VERNON says: \"They're out there, you know. Watching us.\""
    ]
    
    characters = ["VERNON", "PETUNIA"]
    
    print("🧪 Testing Dialogue Detection")
    print("=" * 50)
    
    for i, line in enumerate(test_lines, 1):
        result = parser._detect_character_dialogue(line, characters)
        print(f"Test {i}: '{line}'")
        print(f"  → Detected: {result}")
        print()

def test_character_action_detection():
    """Test character action detection specifically"""
    parser = ScriptParser()
    
    test_lines = [
        "Vernon Dursley (selecting his tie)",
        "Petunia Dursley (muttering to herself)",
        "Vernon (looking concerned) adjusts his mustache",
        "Close-up on Petunia (gossiping while tending to Dudley)",
        "PETUNIA (scoffs)",
        "VERNON (whispering)"
    ]
    
    print("🧪 Testing Character Action Detection")
    print("=" * 50)
    
    for i, line in enumerate(test_lines, 1):
        actions = parser._extract_character_actions(line)
        print(f"Test {i}: '{line}'")
        print(f"  → Detected actions: {actions}")
        print()

if __name__ == "__main__":
    print("🔍 DEBUG SCRIPT PARSER COMPONENTS")
    print("=" * 60)
    
    test_camera_movement_detection()
    test_dialogue_detection()
    test_character_action_detection()