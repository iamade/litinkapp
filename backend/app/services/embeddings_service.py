import openai
from typing import List, Dict, Any, Optional
import numpy as np
from supabase import Client
from app.core.config import settings
import logging
from app.services.text_utils import TextSanitizer

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for generating and managing vector embeddings for RAG functionality"""
    
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text using OpenAI"""
        try:
            # Sanitize text before sending to OpenAI
            sanitized_text = TextSanitizer.sanitize_for_openai(text)
            
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=sanitized_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks for embedding"""
        # Sanitize text first
        sanitized_text = TextSanitizer.sanitize_text(text)
        
        chunks = []
        start = 0
        
        while start < len(sanitized_text):
            end = start + chunk_size
            chunk_text = sanitized_text[start:end]
            
            # Try to break at sentence boundaries
            if end < len(sanitized_text):
                last_period = chunk_text.rfind('.')
                last_exclamation = chunk_text.rfind('!')
                last_question = chunk_text.rfind('?')
                last_newline = chunk_text.rfind('\n')
                
                break_point = max(last_period, last_exclamation, last_question, last_newline)
                if break_point > chunk_size * 0.7:  # Only break if we're at least 70% through
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                'text': chunk_text.strip(),
                'start': start,
                'end': end,
                'size': len(chunk_text)
            })
            
            start = end - overlap
            if start >= len(sanitized_text):
                break
        
        return chunks
    
    async def create_chapter_embeddings(self, chapter_id: str, content: str) -> bool:
        """Create embeddings for a chapter's content"""
        try:
            # Get chapter info
            chapter_response = self.db.table('chapters').select('*, books(*)').eq('id', chapter_id).single().execute()
            if not chapter_response.data:
                raise ValueError(f"Chapter {chapter_id} not found")
            
            chapter = chapter_response.data
            book_id = chapter['book_id']
            
            # Delete existing embeddings for this chapter
            self.db.table('chapter_embeddings').delete().eq('chapter_id', chapter_id).execute()
            
            # Chunk the content
            chunks = await self.chunk_text(content)
            
            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                embedding = await self.generate_embedding(chunk['text'])
                
                # Store embedding
                embedding_data = {
                    'chapter_id': chapter_id,
                    'book_id': book_id,
                    'content_chunk': chunk['text'],
                    'embedding': embedding,
                    'chunk_index': i,
                    'chunk_size': chunk['size'],
                    'metadata': {
                        'start_pos': chunk['start'],
                        'end_pos': chunk['end']
                    }
                }
                
                self.db.table('chapter_embeddings').insert(embedding_data).execute()
            
            logger.info(f"Created {len(chunks)} embeddings for chapter {chapter_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating chapter embeddings: {e}")
            return False
    
    async def create_book_embeddings(self, book_id: str, title: str, description: str = None, content: str = None) -> bool:
        """Create embeddings for book-level content"""
        try:
            # Delete existing embeddings for this book
            self.db.table('book_embeddings').delete().eq('book_id', book_id).execute()
            
            embeddings_created = 0
            
            # Title embedding
            if title:
                title_embedding = await self.generate_embedding(title)
                self.db.table('book_embeddings').insert({
                    'book_id': book_id,
                    'content_chunk': title,
                    'embedding': title_embedding,
                    'chunk_index': 0,
                    'chunk_size': len(title),
                    'chunk_type': 'title'
                }).execute()
                embeddings_created += 1
            
            # Description embedding
            if description:
                desc_embedding = await self.generate_embedding(description)
                self.db.table('book_embeddings').insert({
                    'book_id': book_id,
                    'content_chunk': description,
                    'embedding': desc_embedding,
                    'chunk_index': 0,
                    'chunk_size': len(description),
                    'chunk_type': 'description'
                }).execute()
                embeddings_created += 1
            
            # Content embedding (if provided)
            if content:
                content_chunks = await self.chunk_text(content, chunk_size=2000)
                for i, chunk in enumerate(content_chunks):
                    content_embedding = await self.generate_embedding(chunk['text'])
                    self.db.table('book_embeddings').insert({
                        'book_id': book_id,
                        'content_chunk': chunk['text'],
                        'embedding': content_embedding,
                        'chunk_index': i,
                        'chunk_size': chunk['size'],
                        'chunk_type': 'content',
                        'metadata': {
                            'start_pos': chunk['start'],
                            'end_pos': chunk['end']
                        }
                    }).execute()
                    embeddings_created += 1
            
            logger.info(f"Created {embeddings_created} embeddings for book {book_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating book embeddings: {e}")
            return False
    
    async def search_similar_chapters(self, query: str, book_id: str = None, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar chapter content using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)
            
            # Build the query
            query_builder = self.db.rpc('match_chapter_embeddings', {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            })
            
            # Add book filter if specified
            if book_id:
                query_builder = query_builder.eq('book_id', book_id)
            
            response = query_builder.execute()
            
            if not response.data:
                return []
            
            # Get full chapter details for results
            chapter_ids = [item['chapter_id'] for item in response.data]
            chapters_response = self.db.table('chapters').select('*').in_('id', chapter_ids).execute()
            
            # Combine results
            results = []
            for item in response.data:
                chapter = next((c for c in chapters_response.data if c['id'] == item['chapter_id']), None)
                if chapter:
                    results.append({
                        'chapter': chapter,
                        'content_chunk': item['content_chunk'],
                        'similarity': item['similarity'],
                        'chunk_index': item['chunk_index']
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar chapters: {e}")
            return []
    
    async def search_similar_books(self, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar books using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)
            
            # Search book embeddings
            response = self.db.rpc('match_book_embeddings', {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }).execute()
            
            if not response.data:
                return []
            
            # Get full book details for results
            book_ids = list(set([item['book_id'] for item in response.data]))
            books_response = self.db.table('books').select('*').in_('id', book_ids).execute()
            
            # Combine results
            results = []
            for item in response.data:
                book = next((b for b in books_response.data if b['id'] == item['book_id']), None)
                if book:
                    results.append({
                        'book': book,
                        'content_chunk': item['content_chunk'],
                        'similarity': item['similarity'],
                        'chunk_type': item['chunk_type']
                    })
            
            # Sort by similarity
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar books: {e}")
            return []
    
    async def get_context_for_chapter(self, chapter_id: str, query: str = None, context_chunks: int = 3) -> List[Dict[str, Any]]:
        """Get relevant context chunks for a chapter using similarity search"""
        try:
            # Get chapter content
            chapter_response = self.db.table('chapters').select('*').eq('id', chapter_id).single().execute()
            if not chapter_response.data:
                return []
            
            chapter = chapter_response.data
            
            # Use chapter title and content as query if no specific query provided
            if not query:
                query = f"{chapter['title']} {chapter['content'][:500]}"
            
            # Search for similar content within the same book
            similar_chunks = await self.search_similar_chapters(
                query=query,
                book_id=chapter['book_id'],
                limit=context_chunks,
                threshold=0.6
            )
            
            return similar_chunks
            
        except Exception as e:
            logger.error(f"Error getting context for chapter: {e}")
            return [] 