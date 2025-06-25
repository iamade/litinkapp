#!/usr/bin/env python3
"""
Test script to analyze chunking performance and identify bottlenecks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.file_service import FileService
import time

def test_chunking_performance():
    """Test the chunking performance with a sample text"""
    
    # Sample text that might cause issues
    sample_text = """
    Chapter 1: Introduction
    
    This is a sample chapter with some content. It contains multiple paragraphs
    that should be processed efficiently.
    
    Chapter 2: Background
    
    Another chapter with different content. This should also be processed.
    
    Chapter 3: Methodology
    
    Yet another chapter with more content to test the chunking algorithm.
    """ * 1000  # Repeat to make it longer
    
    print(f"Sample text length: {len(sample_text)} characters")
    
    file_service = FileService()
    
    # Test the chunking
    start_time = time.time()
    chunks = file_service._split_content_into_chunks(sample_text, 12)
    end_time = time.time()
    
    print(f"Chunking took {end_time - start_time:.2f} seconds")
    print(f"Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
        print(f"Chunk {i+1}: {len(chunk['content'])} chars - {chunk['title']}")
    
    if len(chunks) > 5:
        print(f"... and {len(chunks) - 5} more chunks")

if __name__ == "__main__":
    test_chunking_performance() 