# Text Utilities Guide

This guide explains how to use the new text sanitization and token counting utilities to handle the errors you encountered.

## Overview

The new utilities address three main issues:

1. **Unicode escape sequence errors** (`\u0000 cannot be converted to text`)
2. **Invalid enum values** (`invalid input value for enum book_status: "PUBLISHED"`)
3. **Context length exceeded errors** (`context_length_exceeded`)

## Text Sanitization

### Problem

Your application was encountering Unicode escape sequence errors like:

```
Error creating chapter embeddings: {'code': '22P05', 'details': '\\u0000 cannot be converted to text.', 'hint': None, 'message': 'unsupported Unicode escape sequence'}
```

### Solution

Use the `TextSanitizer` class to clean text before database storage and API calls:

```python
from app.services.text_utils import TextSanitizer

# For general text cleaning (database storage)
cleaned_text = TextSanitizer.sanitize_text(raw_text)

# For OpenAI API calls (additional cleaning)
api_safe_text = TextSanitizer.sanitize_for_openai(raw_text)
```

### What it does:

- Removes null bytes (`\x00`, `\u0000`)
- Handles Unicode escape sequences (`\uXXXX`, `\xXX`)
- Normalizes Unicode characters
- Removes control characters (except newlines, tabs, carriage returns)
- Removes zero-width characters
- Ensures valid UTF-8 encoding
- Normalizes whitespace

## Token Counting and Chunking

### Problem

Your application was hitting OpenAI's token limits:

```
AI validation failed: Error code: 400 - {'error': {'message': "This model's maximum context length is 16385 tokens. However, your messages resulted in 181945 tokens. Please reduce the length of the messages.", 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}}
```

### Solution

Use the `TokenCounter` and `TextChunker` classes:

```python
from app.services.text_utils import TokenCounter, TextChunker

# Count tokens in text
token_counter = TokenCounter()
token_count = token_counter.count_tokens("Your text here")

# Chunk large text
chunker = TextChunker(token_counter)
chunks = chunker.chunk_text_by_tokens(large_text, max_tokens=12000, overlap_tokens=500)
```

### Safe OpenAI Message Creation

Use the `create_safe_openai_messages` function to automatically handle token limits:

```python
from app.services.text_utils import create_safe_openai_messages

messages, total_tokens = create_safe_openai_messages(
    system_prompt="You are a helpful assistant.",
    user_content=large_content,
    max_tokens=16385,  # gpt-3.5-turbo limit
    reserved_tokens=1000  # Reserve tokens for response
)
```

## Integration Points

### 1. File Processing (file_service.py)

The `_clean_text_content` method now uses `TextSanitizer.sanitize_text()`.

### 2. AI Service (ai_service.py)

All OpenAI API calls now use:

- `TextSanitizer.sanitize_for_openai()` for text cleaning
- `create_safe_openai_messages()` for token management

### 3. Embeddings Service (embeddings_service.py)

Text is sanitized before creating embeddings and chunking.

### 4. Video Service (video_service.py)

Content is sanitized before sending to video generation APIs.

## Usage Examples

### Basic Text Sanitization

```python
from app.services.text_utils import TextSanitizer

# Clean text for database storage
raw_text = "Hello\x00World\u0000 with \u200B invisible chars"
clean_text = TextSanitizer.sanitize_text(raw_text)
# Result: "HelloWorld with  invisible chars"
```

### Token Counting

```python
from app.services.text_utils import TokenCounter

counter = TokenCounter()
text = "This is a test message for token counting."
tokens = counter.count_tokens(text)
print(f"Text has {tokens} tokens")
```

### Safe OpenAI API Calls

```python
from app.services.text_utils import create_safe_openai_messages

# This will automatically handle long content
messages, token_count = create_safe_openai_messages(
    system_prompt="You are an expert editor.",
    user_content=very_long_content,
    max_tokens=16385,
    reserved_tokens=2000
)

# Use messages directly with OpenAI API
response = await openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    temperature=0.7
)
```

### Text Chunking

```python
from app.services.text_utils import TokenCounter, TextChunker

counter = TokenCounter()
chunker = TextChunker(counter)

# Split large text into manageable chunks
chunks = chunker.chunk_text_by_tokens(
    large_text,
    max_tokens=12000,
    overlap_tokens=500
)

for chunk in chunks:
    print(f"Chunk: {chunk['text'][:100]}...")
    print(f"Tokens: {chunk['tokens']}")
```

## Error Handling

The utilities include robust error handling:

```python
try:
    cleaned_text = TextSanitizer.sanitize_text(problematic_text)
except Exception as e:
    # Fallback to basic cleaning
    cleaned_text = problematic_text.encode('utf-8', errors='ignore').decode('utf-8')
```

## Testing

Run the test script to verify everything works:

```bash
cd backend
python test_text_utils.py
```

## Configuration

The utilities use these default settings:

- **Max tokens for gpt-3.5-turbo**: 16385
- **Reserved tokens for responses**: 1000-2000 (configurable)
- **Chunk overlap**: 500 tokens
- **Max chunk size**: 12000 tokens

## Dependencies

Add to `requirements.txt`:

```
tiktoken==0.5.2
```

## Migration Guide

### For Existing Code

1. **Replace manual text cleaning**:

   ```python
   # Old
   cleaned = text.replace('\x00', '').replace('\u0000', '')

   # New
   from app.services.text_utils import TextSanitizer
   cleaned = TextSanitizer.sanitize_text(text)
   ```

2. **Replace manual token limiting**:

   ```python
   # Old
   content = content[:2000]  # Arbitrary truncation

   # New
   from app.services.text_utils import create_safe_openai_messages
   messages, tokens = create_safe_openai_messages(system_prompt, content)
   ```

3. **Replace manual chunking**:

   ```python
   # Old
   chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]

   # New
   from app.services.text_utils import TokenCounter, TextChunker
   counter = TokenCounter()
   chunker = TextChunker(counter)
   chunks = chunker.chunk_text_by_tokens(text, max_tokens=12000)
   ```

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure `tiktoken` is installed
2. **Token counting errors**: The utility falls back to character-based estimation
3. **Sanitization too aggressive**: Adjust the sanitization rules in `TextSanitizer`

### Debug Mode

Enable debug logging to see what's happening:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- **Token counting**: Fast for most text, but can be slow for very large documents
- **Text sanitization**: Very fast, minimal performance impact
- **Chunking**: Efficient for large texts, uses sentence boundaries when possible

## Best Practices

1. **Always sanitize text** before database storage or API calls
2. **Use token counting** before sending to OpenAI APIs
3. **Implement chunking** for large documents
4. **Test with your actual data** to ensure proper handling
5. **Monitor token usage** to optimize costs

## Support

If you encounter issues:

1. Check the test script output
2. Verify your text contains the problematic characters
3. Ensure all dependencies are installed
4. Review the error logs for specific issues
