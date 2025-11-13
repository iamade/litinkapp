#!/usr/bin/env python3
"""
Debug dialogue pattern matching specifically
"""

import re

def test_dialogue_patterns():
    """Test different dialogue patterns"""
    
    test_lines = [
        'Petunia Dursley says: "That Lily Potter... she\'s so different."',
        'VERNON says: "They\'re out there, you know. Watching us."',
        'Petunia says: "That Lily Potter... she\'s so different."',
        'Vernon says: "They\'re out there, you know. Watching us."'
    ]
    
    print("🔍 Testing Dialogue Patterns")
    print("=" * 50)
    
    # Test pattern 1: CHARACTER says: "dialogue"
    pattern1 = r'^([A-Z][A-Za-z\s]+)\s+says:\s*"([^"]*)"$'
    pattern1_insensitive = r'^([A-Z][A-Za-z\s]+)\s+says:\s*"([^"]*)"$'
    
    for i, line in enumerate(test_lines, 1):
        print(f"Test {i}: '{line}'")
        
        # Test with case-sensitive
        match1 = re.match(pattern1, line)
        print(f"  Pattern 1 (case-sensitive): {match1}")
        
        # Test with case-insensitive
        match2 = re.match(pattern1_insensitive, line, re.IGNORECASE)
        print(f"  Pattern 1 (case-insensitive): {match2}")
        
        if match2:
            print(f"    Character: '{match2.group(1)}'")
            print(f"    Dialogue: '{match2.group(2)}'")
        
        print()

if __name__ == "__main__":
    test_dialogue_patterns()