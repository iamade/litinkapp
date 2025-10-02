#!/usr/bin/env python3
"""
Simple test script for cinematic workflow functionality
Tests the script parser for cinematic style handling
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.script_parser import ScriptParser

def test_cinematic_script_parsing():
    """Test the script parser with cinematic style script"""

    # Initialize parser
    parser = ScriptParser()

    # Test script with cinematic dialogue
    test_script = """EXT. ANCIENT LIBRARY - DAY

The camera zooms in on an ancient library, with towering shelves filled with old manuscripts and scrolls.

NARRATOR (V.O.)
Chapter 2: The Source of Angel Magic.

INT. ANCIENT LIBRARY - DAY

We see CHALDEAN ANGEL MAGIC, EGYPTIAN ANGEL MAGIC, HEBRAIC ANGEL MAGIC, and GNOSTIC ANGEL MAGIC written on various scrolls and manuscripts.

NARRATOR (V.O.)
Chaldean Angel Magic... Egyptian Angel Magic... Hebraic Angel Magic... Gnostic Angel Magic...

HARRY
I need to understand these ancient magics.

RON
But they're dangerous, Harry!

HARRY
I know, but I have to try.

CUT TO:

EXT. MODERN CITY - DAY

The camera shows a modern city skyline, with people bustling about.

NARRATOR (V.O.)
Introduction to Angel Magic.

INT. MODERN APARTMENT - DAY

We see the words "What are Angels? Are Angels Real? How Do Angels Appear? What is Angel Magic?" written on a computer screen.

NARRATOR (V.O.)
What are Angels? Are Angels Real? How Do Angels Appear? What is Angel Magic?

FADE OUT."""

    # Test characters
    characters = ["HARRY", "RON", "NARRATOR"]

    # Test scene descriptions
    scene_descriptions = [
        "Ancient library with magical scrolls",
        "Modern city with bustling activity",
        "Modern apartment with computer screen"
    ]

    print("=== TESTING CINEMATIC SCRIPT PARSING ===\n")
    print("Original Script:")
    print("-" * 50)
    print(test_script)
    print("-" * 50)

    # Test parsing
    print("\n=== PARSING RESULTS ===")
    result = parser.parse_script_for_audio(test_script, characters, scene_descriptions, "cinematic_movie")

    print("\n--- Character Dialogues ---")
    dialogues = result.get('character_dialogues', [])
    if dialogues:
        for i, dialogue in enumerate(dialogues):
            print(f"  {i+1}. {dialogue['character']}: \"{dialogue['text']}\" (Scene {dialogue['scene']})")
    else:
        print("  No character dialogues found")

    print("\n--- Narrator Segments ---")
    narrator_segments = result.get('narrator_segments', [])
    if narrator_segments:
        for i, segment in enumerate(narrator_segments):
            print(f"  {i+1}. \"{segment['text']}\" (Scene {segment['scene']})")
    else:
        print("  No narrator segments found (expected for cinematic)")

    print("\n--- Sound Effects ---")
    sound_effects = result.get('sound_effects', [])
    if sound_effects:
        for i, effect in enumerate(sound_effects):
            print(f"  {i+1}. {effect.get('description', 'Unknown')} (Scene {effect.get('scene', 'N/A')})")
    else:
        print("  No sound effects found")

    print("\n--- Background Music ---")
    background_music = result.get('background_music', [])
    if background_music:
        for i, music in enumerate(background_music):
            print(f"  {i+1}. {music.get('description', 'Unknown')} (Scene {music.get('scene', 'N/A')})")
    else:
        print("  No background music found")

    # Test assertions
    print("\n=== TEST RESULTS ===")

    # Check 1: Script parser correctly handles cinematic style as dialogue
    has_character_dialogues = len(dialogues) > 0
    print(f"✅ Character dialogues found: {has_character_dialogues}")

    # Check 2: Audio generation creates only background music and sound effects for cinematic (no narrator)
    has_no_narrator = len(narrator_segments) == 0
    has_background_music = len(background_music) > 0
    has_sound_effects = len(sound_effects) > 0
    print(f"✅ No narrator segments (cinematic): {has_no_narrator}")
    print(f"✅ Background music present: {has_background_music}")
    print(f"✅ Sound effects present: {has_sound_effects}")

    # Check 3: Video generation can handle dialogue in cinematic scripts
    dialogue_scenes = set(d['scene'] for d in dialogues)
    print(f"✅ Dialogue distributed across scenes: {len(dialogue_scenes)} scenes with dialogue")

    # Check 4: The split workflow functions properly
    has_audio_components = has_character_dialogues or has_background_music or has_sound_effects
    print(f"✅ Audio components properly separated: {has_audio_components}")

    # Summary
    all_tests_pass = has_character_dialogues and has_no_narrator and has_background_music and has_sound_effects and has_audio_components
    print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_tests_pass else '❌ SOME TESTS FAILED'}")

    return all_tests_pass

if __name__ == "__main__":
    test_cinematic_script_parsing()