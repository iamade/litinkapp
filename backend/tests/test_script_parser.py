#!/usr/bin/env python3
"""
Test script for the dynamic script parser
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.video_service import VideoService

def test_script_parser():
    """Test the script parser with the provided example"""
    
    # Initialize video service
    video_service = VideoService()
    
    # Test script from the user
    test_script = """EXT. ANCIENT LIBRARY - DAY

The camera zooms in on an ancient library, with towering shelves filled with old manuscripts and scrolls. 

NARRATOR (V.O.)
Chapter 2: The Source of Angel Magic.

INT. ANCIENT LIBRARY - DAY

We see CHALDEAN ANGEL MAGIC, EGYPTIAN ANGEL MAGIC, HEBRAIC ANGEL MAGIC, and GNOSTIC ANGEL MAGIC written on various scrolls and manuscripts. 

NARRATOR (V.O.)
Chaldean Angel Magic... Egyptian Angel Magic... Hebraic Angel Magic... Gnostic Angel Magic...

CUT TO:

EXT. MEDIEVAL CASTLE - NIGHT

The camera pans over a medieval castle, with torches flickering in the darkness. 

NARRATOR (V.O.)
Chapter 3: The Survival of Angel Magic.

INT. MEDIEVAL CASTLE - NIGHT

We see DARK AGE ANGEL MAGIC, ISLAMIC ANGEL MAGIC, MEDIEVAL ANGEL MAGIC, and RENAISSANCE ANGEL MAGIC written on various scrolls and manuscripts. 

NARRATOR (V.O.)
Dark Age Angel Magic... Islamic Angel Magic... Medieval Angel Magic... Renaissance Angel Magic...

CUT TO:

EXT. MODERN CITY - DAY

The camera shows a modern city skyline, with people bustling about. 

NARRATOR (V.O.)
Introduction to Angel Magic.

INT. MODERN APARTMENT - DAY

We see the words "What are Angels? Are Angels Real? How Do Angels Appear? What is Angel Magic?" written on a computer screen. 

NARRATOR (V.O.)
What are Angels? Are Angels Real? How Do Angels Appear? What is Angel Magic?

CUT TO:

INT. ANCIENT LIBRARY - DAY

The camera zooms in on a worn, leather-bound book titled "The Source of Angel Magic" as a hand flips through its pages. 

NARRATOR (V.O.)
The modern world has rediscovered Angels...

CUT TO:

EXT. ANCIENT TEMPLE - DAY

The camera shows an ancient temple, with people gathered around, studying ancient symbols and rituals. 

NARRATOR (V.O.)
The fascination with Angels is not a cult phenomenon...

CUT TO:

INT. ANCIENT LIBRARY - DAY

The camera shows various illustrations of Angelic beings and symbols drawn from astrology, alchemy, and theology.

NARRATOR (V.O.)
Over the years, Angel Magic has acquired a complex array of ideas and symbols...

CUT TO:

EXT. ANCIENT TEMPLE - DAY

The camera shows a group of people in a circle, performing a ritual with candles and incense. 

NARRATOR (V.O.)
The growth and transformation of Angel Magic over the centuries is one of the most interesting developments in the history of human thought...

CUT TO:

INT. ANCIENT LIBRARY - DAY

The camera shows a group of scholars discussing ancient manuscripts and scrolls. 

NARRATOR (V.O.)
There has always been a great deal of controversy surrounding the origins of Angel Magic...

CUT TO:

EXT. ANCIENT TEMPLE - DAY

The camera shows a man in ceremonial robes, raising his hands towards the sky. 

NARRATOR (V.O.)
The Angel Magi of the Renaissance believed that Angel Magic was among the oldest forms of worship known to mankind...

CUT TO:

INT. ANCIENT LIBRARY - DAY

The camera zooms in on a page from an ancient manuscript, with the words "The Source of Angel Magic" written in beautiful calligraphy. 

NARRATOR (V.O.)
...Here, for the first time, is the complete story.

FADE OUT."""
    
    print("=== TESTING SCRIPT PARSER ===\n")
    print("Original Script:")
    print("-" * 50)
    print(test_script)
    print("-" * 50)
    
    # Test screenplay parsing
    print("\n=== PARSED CONTENT (Cinematic Movie) ===")
    result = video_service._parse_script_for_services(test_script, "cinematic_movie")
    
    print("\n--- ElevenLabs Content ---")
    print(f"Type: {result['elevenlabs_content_type']}")
    print(f"Content: {result['elevenlabs_content']}")
    
    print("\n--- KlingAI Content ---")
    print(f"Type: {result['klingai_content_type']}")
    print(f"Content: {result['klingai_content']}")
    
    print("\n--- Parsed Sections ---")
    if 'parsed_sections' in result:
        sections = result['parsed_sections']
        if 'scene_descriptions' in sections:
            print(f"\nScene Descriptions ({len(sections['scene_descriptions'])} items):")
            for i, desc in enumerate(sections['scene_descriptions']):
                print(f"  {i+1}. {desc}")
        
        if 'narrator_dialogue' in sections:
            print(f"\nNarrator Dialogue ({len(sections['narrator_dialogue'])} items):")
            for i, dialogue in enumerate(sections['narrator_dialogue']):
                print(f"  {i+1}. \"{dialogue}\"")
        
        if 'character_dialogue' in sections:
            print(f"\nCharacter Dialogue ({len(sections['character_dialogue'])} items):")
            for i, dialogue in enumerate(sections['character_dialogue']):
                print(f"  {i+1}. \"{dialogue}\"")

if __name__ == "__main__":
    test_script_parser() 