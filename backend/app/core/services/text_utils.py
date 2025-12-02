import re
import unicodedata
import tiktoken
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TextSanitizer:
    """Comprehensive text sanitization utility for handling Unicode and encoding issues"""
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Comprehensive text sanitization to handle Unicode escape sequences and problematic characters.
        
        Args:
            text: Raw text that may contain problematic characters
            
        Returns:
            Cleaned text safe for database storage and API calls
        """
        if not text:
            return ""
        
        try:
            # Step 1: Remove null bytes and Unicode null characters
            cleaned = text.replace('\x00', '')
            cleaned = cleaned.replace('\u0000', '')
            
            # Step 2: Handle Unicode escape sequences
            # Remove or replace problematic Unicode escape sequences
            cleaned = re.sub(r'\\u[0-9a-fA-F]{4}', '', cleaned)  # Remove \uXXXX sequences
            cleaned = re.sub(r'\\x[0-9a-fA-F]{2}', '', cleaned)  # Remove \xXX sequences
            
            # Step 3: Normalize Unicode characters
            cleaned = unicodedata.normalize('NFKC', cleaned)
            
            # Step 4: Remove control characters except newlines, tabs, and carriage returns
            cleaned = ''.join(
                char for char in cleaned 
                if unicodedata.category(char)[0] != 'C' or char in '\n\t\r'
            )
            
            # Step 5: Handle other problematic Unicode sequences
            # Remove zero-width characters and other invisible characters
            cleaned = re.sub(r'[\u200B-\u200D\uFEFF]', '', cleaned)  # Zero-width characters
            
            # Step 6: Ensure valid UTF-8 encoding
            cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
            
            # Step 7: Remove excessive whitespace while preserving structure
            cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Remove excessive newlines
            cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Normalize spaces and tabs
            
            return cleaned.strip()
            
        except Exception as e:
            logger.error(f"Error sanitizing text: {e}")
            # Fallback: return a safe version of the content
            try:
                return text.encode('utf-8', errors='ignore').decode('utf-8')
            except:
                return "Content could not be processed due to encoding issues."
    
    @staticmethod
    def sanitize_for_openai(text: str) -> str:
        """
        Additional sanitization specifically for OpenAI API calls.
        
        Args:
            text: Text to be sent to OpenAI API
            
        Returns:
            Text safe for OpenAI API calls
        """
        if not text:
            return ""
        
        # First apply general sanitization
        cleaned = TextSanitizer.sanitize_text(text)
        
        # Additional OpenAI-specific cleaning
        try:
            # Remove any remaining problematic sequences
            cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
            
            # Ensure no null characters remain
            cleaned = cleaned.replace('\x00', '')
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error sanitizing text for OpenAI: {e}")
            return cleaned


class TokenCounter:
    """Token counting and text chunking utilities for OpenAI API calls"""
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize token counter for a specific model.
        
        Args:
            model: OpenAI model name (default: gpt-3.5-turbo)
        """
        self.model = model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base encoding (used by gpt-3.5-turbo and gpt-4)
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text for the specified model.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens for a list of messages (system, user, assistant).
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Total token count
        """
        total_tokens = 0
        
        for message in messages:
            # Add tokens for the message content
            content_tokens = self.count_tokens(message.get('content', ''))
            total_tokens += content_tokens
            
            # Add tokens for the role (typically 4 tokens per message)
            total_tokens += 4
        
        # Add tokens for reply (typically 2 tokens)
        total_tokens += 2
        
        return total_tokens
    
    def estimate_max_content_length(self, max_tokens: int = 16385, reserved_tokens: int = 1000) -> int:
        """
        Estimate maximum content length that can be sent to OpenAI API.
        
        Args:
            max_tokens: Maximum tokens for the model (default: gpt-3.5-turbo limit)
            reserved_tokens: Tokens to reserve for system prompt and response
            
        Returns:
            Estimated maximum characters for content
        """
        available_tokens = max_tokens - reserved_tokens
        # Rough estimate: 1 token ≈ 4 characters
        return available_tokens * 4


class TextChunker:
    """Text chunking utilities for handling large content"""
    
    def __init__(self, token_counter: TokenCounter):
        """
        Initialize text chunker.
        
        Args:
            token_counter: TokenCounter instance for token counting
        """
        self.token_counter = token_counter
    
    def chunk_text_by_tokens(
        self, 
        text: str, 
        max_tokens: int = 12000, 
        overlap_tokens: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks based on token count.
        
        Args:
            text: Text to chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
            
        Returns:
            List of chunk dictionaries with 'text', 'start', 'end', 'tokens' keys
        """
        if not text:
            return []
        
        # Sanitize text first
        text = TextSanitizer.sanitize_for_openai(text)
        
        chunks = []
        start_pos = 0
        
        while start_pos < len(text):
            # Find the end position for this chunk
            end_pos = self._find_chunk_end(text, start_pos, max_tokens)
            
            if end_pos <= start_pos:
                # If we can't find a good break point, force a break
                end_pos = min(start_pos + max_tokens * 4, len(text))
            
            chunk_text = text[start_pos:end_pos]
            token_count = self.token_counter.count_tokens(chunk_text)
            
            chunks.append({
                'text': chunk_text,
                'start': start_pos,
                'end': end_pos,
                'tokens': token_count,
                'size': len(chunk_text)
            })
            
            # Move to next chunk with overlap
            if end_pos >= len(text):
                break
            
            # Find overlap start position
            overlap_start = self._find_overlap_start(text, end_pos, overlap_tokens)
            start_pos = overlap_start
    
    def _find_chunk_end(self, text: str, start_pos: int, max_tokens: int) -> int:
        """
        Find the best end position for a chunk.
        
        Args:
            text: Full text
            start_pos: Starting position
            max_tokens: Maximum tokens for chunk
            
        Returns:
            End position for chunk
        """
        # Start with a reasonable chunk size
        chunk_size = max_tokens * 4  # Rough estimate
        end_pos = min(start_pos + chunk_size, len(text))
        
        # If we're at the end of text, return current position
        if end_pos >= len(text):
            return len(text)
        
        # Try to find a good break point
        chunk_text = text[start_pos:end_pos]
        
        # Look for sentence boundaries
        last_period = chunk_text.rfind('.')
        last_exclamation = chunk_text.rfind('!')
        last_question = chunk_text.rfind('?')
        last_newline = chunk_text.rfind('\n')
        
        # Find the best break point
        break_points = [last_period, last_exclamation, last_question, last_newline]
        best_break = max(break_points)
        
        if best_break > chunk_size * 0.7:  # Only break if we're at least 70% through
            return start_pos + best_break + 1
        
        # If no good break point, check if we're within token limit
        token_count = self.token_counter.count_tokens(chunk_text)
        if token_count <= max_tokens:
            return end_pos
        
        # Reduce chunk size and try again
        return self._find_chunk_end(text, start_pos, max_tokens - 1000)
    
    def _find_overlap_start(self, text: str, end_pos: int, overlap_tokens: int) -> int:
        """
        Find the start position for the next chunk with overlap.
        
        Args:
            text: Full text
            end_pos: End position of current chunk
            overlap_tokens: Number of tokens to overlap
            
        Returns:
            Start position for next chunk
        """
        # Estimate overlap in characters
        overlap_chars = overlap_tokens * 4
        
        # Find a good break point in the overlap area
        overlap_start = max(0, end_pos - overlap_chars)
        
        # Look for sentence boundaries in overlap area
        overlap_text = text[overlap_start:end_pos]
        
        last_period = overlap_text.rfind('.')
        last_exclamation = overlap_text.rfind('!')
        last_question = overlap_text.rfind('?')
        last_newline = overlap_text.rfind('\n')
        
        best_break = max(last_period, last_exclamation, last_question, last_newline)
        
        if best_break > 0:
            return overlap_start + best_break + 1
        
        return overlap_start


def create_safe_openai_messages(
    system_prompt: str,
    user_content: str,
    max_tokens: int = 16385,
    reserved_tokens: int = 1000
) -> Tuple[List[Dict[str, str]], int]:
    """
    Create safe OpenAI messages that won't exceed token limits.
    
    Args:
        system_prompt: System prompt
        user_content: User content
        max_tokens: Maximum tokens for the model
        reserved_tokens: Tokens to reserve for response
        
    Returns:
        Tuple of (messages, total_tokens)
    """
    token_counter = TokenCounter()
    chunker = TextChunker(token_counter)
    
    # Sanitize content
    system_prompt = TextSanitizer.sanitize_for_openai(system_prompt)
    user_content = TextSanitizer.sanitize_for_openai(user_content)
    
    # Count system prompt tokens
    system_tokens = token_counter.count_tokens(system_prompt)
    
    # Calculate available tokens for user content
    available_tokens = max_tokens - reserved_tokens - system_tokens - 10  # Buffer
    
    if available_tokens <= 0:
        raise ValueError(f"System prompt too long: {system_tokens} tokens")
    
    # Check if user content fits
    user_tokens = token_counter.count_tokens(user_content)
    
    if user_tokens <= available_tokens:
        # Content fits, return as is
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        total_tokens = system_tokens + user_tokens + 10  # +10 for message overhead
        return messages, total_tokens
    else:
        # Content too long, need to chunk
        chunks = chunker.chunk_text_by_tokens(user_content, available_tokens, 0)
        
        if not chunks:
            raise ValueError("Could not create valid chunks from content")
        
        # Use the first chunk
        first_chunk = chunks[0]
        truncated_content = first_chunk['text']
        
        # Add truncation notice
        if len(chunks) > 1:
            truncated_content += "\n\n[Content truncated due to length limits]"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": truncated_content}
        ]
        
        total_tokens = token_counter.count_message_tokens(messages)
        return messages, total_tokens 