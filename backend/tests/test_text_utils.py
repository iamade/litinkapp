#!/usr/bin/env python3
"""
Test script for text utilities (sanitization and token counting)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.text_utils import TextSanitizer, TokenCounter, TextChunker, create_safe_openai_messages

def test_text_sanitization():
    """Test text sanitization functionality"""
    print("=== Testing Text Sanitization ===")
    
    # Test cases with problematic content
    test_cases = [
        # Null bytes and Unicode issues
        ("Hello\x00World\u0000", "HelloWorld"),
        ("Text with \\u0000 and \\x00", "Text with  and "),
        
        # Control characters
        ("Text with \x01\x02\x03 control chars", "Text with  control chars"),
        
        # Zero-width characters
        ("Text with \u200B\u200C\u200D zero-width chars", "Text with  zero-width chars"),
        
        # Excessive whitespace
        ("Text   with   multiple   spaces\n\n\n\nand newlines", "Text with multiple spaces\n\nand newlines"),
        
        # Normal text (should remain unchanged)
        ("This is normal text with punctuation.", "This is normal text with punctuation."),
        
        # Empty text
        ("", ""),
        (None, ""),
    ]
    
    for i, (input_text, expected) in enumerate(test_cases):
        if input_text is None:
            result = TextSanitizer.sanitize_text("")
        else:
            result = TextSanitizer.sanitize_text(input_text)
        
        print(f"Test {i+1}:")
        print(f"  Input: {repr(input_text)}")
        print(f"  Expected: {repr(expected)}")
        print(f"  Result: {repr(result)}")
        print(f"  Pass: {result == expected}")
        print()

def test_token_counting():
    """Test token counting functionality"""
    print("=== Testing Token Counting ===")
    
    token_counter = TokenCounter()
    
    test_texts = [
        "Hello world",
        "This is a longer text with more words to test token counting.",
        "A" * 1000,  # Long text
        "",  # Empty text
    ]
    
    for i, text in enumerate(test_texts):
        token_count = token_counter.count_tokens(text)
        print(f"Test {i+1}:")
        print(f"  Text: {repr(text[:50])}{'...' if len(text) > 50 else ''}")
        print(f"  Length: {len(text)} characters")
        print(f"  Tokens: {token_count}")
        print()

def test_safe_message_creation():
    """Test safe OpenAI message creation"""
    print("=== Testing Safe Message Creation ===")
    
    # Test with short content
    try:
        messages, token_count = create_safe_openai_messages(
            system_prompt="You are a helpful assistant.",
            user_content="Hello, how are you?",
            max_tokens=16385,
            reserved_tokens=1000
        )
        print("Short content test:")
        print(f"  Messages created: {len(messages)}")
        print(f"  Token count: {token_count}")
        print(f"  Pass: {token_count < 16385}")
        print()
    except Exception as e:
        print(f"Short content test failed: {e}")
        print()
    
    # Test with long content
    long_content = "This is a very long text. " * 10000  # Very long text
    try:
        messages, token_count = create_safe_openai_messages(
            system_prompt="You are a helpful assistant.",
            user_content=long_content,
            max_tokens=16385,
            reserved_tokens=1000
        )
        print("Long content test:")
        print(f"  Messages created: {len(messages)}")
        print(f"  Token count: {token_count}")
        print(f"  Content truncated: {'[Content truncated' in messages[1]['content']}")
        print(f"  Pass: {token_count < 16385}")
        print()
    except Exception as e:
        print(f"Long content test failed: {e}")
        print()

def test_text_chunking():
    """Test text chunking functionality"""
    print("=== Testing Text Chunking ===")
    
    token_counter = TokenCounter()
    chunker = TextChunker(token_counter)
    
    # Test with medium-length text
    test_text = "This is a test text. " * 100  # Medium length text
    
    chunks = chunker.chunk_text_by_tokens(test_text, max_tokens=100, overlap_tokens=20)
    
    print(f"Original text length: {len(test_text)} characters")
    print(f"Number of chunks: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"  Text: {chunk['text'][:50]}...")
        print(f"  Tokens: {chunk['tokens']}")
        print(f"  Size: {chunk['size']} characters")
        print()

def main():
    """Run all tests"""
    print("Testing Text Utilities\n")
    
    test_text_sanitization()
    test_token_counting()
    test_safe_message_creation()
    test_text_chunking()
    
    print("All tests completed!")

if __name__ == "__main__":
    main() 