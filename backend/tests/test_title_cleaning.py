#!/usr/bin/env python3
"""
Test script to verify title cleaning functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.file_service import FileService

def test_title_cleaning():
    """Test the title cleaning functionality."""
    
    file_service = FileService()
    
    # Test cases with problematic titles from the user's example
    test_titles = [
        "Chapter 1: Reliable, Scalable, and Maintainable Applications. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  3: Reliable, Scalable, and Maintainable Applications",
        "Chapter 2: Reliable, Scalable, and Maintainable Applications. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  3: Maintainability",
        "Chapter 3: Relational Versus Document Databases Today                                                     38: Query Languages for Data",
        "Chapter 8: Storage and Retrieval. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  69: Storage and Retrieval",
        "Chapter 10: Encoding and Evolution. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  111: Modes of Dataflow",
    ]
    
    print("Testing title cleaning functionality:")
    print("=" * 50)
    
    for i, title in enumerate(test_titles, 1):
        cleaned = file_service._clean_chapter_title(title)
        print(f"Original {i}: {title}")
        print(f"Cleaned {i}:  {cleaned}")
        print(f"Is artifact: {file_service._is_title_artifact(cleaned)}")
        print("-" * 30)
    
    # Test similarity detection
    print("\nTesting title similarity:")
    print("=" * 30)
    
    title1 = "Reliable, Scalable, and Maintainable Applications"
    title2 = "Reliable, Scalable, and Maintainable Applications. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .  3: Reliable, Scalable, and Maintainable Applications"
    title3 = "Storage and Retrieval"
    
    print(f"Title 1: {title1}")
    print(f"Title 2: {title2}")
    print(f"Title 3: {title3}")
    print(f"1 similar to 2: {file_service._titles_similar(title1, title2)}")
    print(f"1 similar to 3: {file_service._titles_similar(title1, title3)}")

if __name__ == "__main__":
    test_title_cleaning() 