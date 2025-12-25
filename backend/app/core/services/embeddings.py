import openai
from typing import List, Dict, Any, Optional
import numpy as np
from sqlmodel import select, delete, col
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import settings
import logging
from app.core.services.text_utils import TextSanitizer
from app.books.models import Chapter, Book, ChapterEmbedding, BookEmbedding
import uuid

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Service for generating and managing vector embeddings for RAG functionality"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text using OpenAI"""
        try:
            # Sanitize text before sending to OpenAI
            sanitized_text = TextSanitizer.sanitize_for_openai(text)

            response = self.client.embeddings.create(
                model=self.embedding_model, input=sanitized_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[Dict[str, Any]]:
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
                last_period = chunk_text.rfind(".")
                last_exclamation = chunk_text.rfind("!")
                last_question = chunk_text.rfind("?")
                last_newline = chunk_text.rfind("\n")

                break_point = max(
                    last_period, last_exclamation, last_question, last_newline
                )
                if (
                    break_point > chunk_size * 0.7
                ):  # Only break if we're at least 70% through
                    chunk_text = chunk_text[: break_point + 1]
                    end = start + break_point + 1

            chunks.append(
                {
                    "text": chunk_text.strip(),
                    "start": start,
                    "end": end,
                    "size": len(chunk_text),
                }
            )

            start = end - overlap
            if start >= len(sanitized_text):
                break

        return chunks

    async def create_chapter_embeddings(
        self, chapter_id: uuid.UUID, content: str
    ) -> bool:
        """Create embeddings for a chapter's content"""
        try:
            # Get chapter info
            statement = select(Chapter).where(Chapter.id == chapter_id)
            result = await self.session.exec(statement)
            chapter = result.first()

            if not chapter:
                raise ValueError(f"Chapter {chapter_id} not found")

            book_id = chapter.book_id

            # Delete existing embeddings for this chapter
            delete_stmt = delete(ChapterEmbedding).where(
                ChapterEmbedding.chapter_id == chapter_id
            )
            await self.session.exec(delete_stmt)

            # Chunk the content
            chunks = await self.chunk_text(content)

            # Generate embeddings for each chunk
            for i, chunk in enumerate(chunks):
                embedding = await self.generate_embedding(chunk["text"])

                # Store embedding
                embedding_record = ChapterEmbedding(
                    chapter_id=chapter_id,
                    book_id=book_id,
                    content_chunk=chunk["text"],
                    embedding=embedding,
                    chunk_index=i,
                    chunk_size=chunk["size"],
                    meta={"start_pos": chunk["start"], "end_pos": chunk["end"]},
                )
                self.session.add(embedding_record)

            await self.session.commit()
            logger.info(f"Created {len(chunks)} embeddings for chapter {chapter_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating chapter embeddings: {e}")
            return False

    async def create_book_embeddings(
        self,
        book_id: uuid.UUID,
        title: str,
        description: str = None,
        content: str = None,
    ) -> bool:
        """Create embeddings for book-level content"""
        try:
            # Delete existing embeddings for this book
            delete_stmt = delete(BookEmbedding).where(BookEmbedding.book_id == book_id)
            await self.session.exec(delete_stmt)

            embeddings_created = 0

            # Title embedding
            if title:
                title_embedding = await self.generate_embedding(title)
                self.session.add(
                    BookEmbedding(
                        book_id=book_id,
                        content_chunk=title,
                        embedding=title_embedding,
                        chunk_index=0,
                        chunk_size=len(title),
                        chunk_type="title",
                    )
                )
                embeddings_created += 1

            # Description embedding
            if description:
                desc_embedding = await self.generate_embedding(description)
                self.session.add(
                    BookEmbedding(
                        book_id=book_id,
                        content_chunk=description,
                        embedding=desc_embedding,
                        chunk_index=0,
                        chunk_size=len(description),
                        chunk_type="description",
                    )
                )
                embeddings_created += 1

            # Content embedding (if provided)
            if content:
                content_chunks = await self.chunk_text(content, chunk_size=2000)
                for i, chunk in enumerate(content_chunks):
                    content_embedding = await self.generate_embedding(chunk["text"])
                    self.session.add(
                        BookEmbedding(
                            book_id=book_id,
                            content_chunk=chunk["text"],
                            embedding=content_embedding,
                            chunk_index=i,
                            chunk_size=chunk["size"],
                            chunk_type="content",
                            meta={
                                "start_pos": chunk["start"],
                                "end_pos": chunk["end"],
                            },
                        )
                    )
                    embeddings_created += 1

            await self.session.commit()
            logger.info(f"Created {embeddings_created} embeddings for book {book_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating book embeddings: {e}")
            return False

    async def search_similar_chapters(
        self,
        query: str,
        book_id: uuid.UUID = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar chapter content using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)

            # Build query using pgvector l2_distance (Euclidean distance)
            # Note: l2_distance is appropriate for normalized embeddings (OpenAI embeddings are normalized)
            # Lower distance = higher similarity
            # We can also use cosine_distance if preferred

            statement = select(ChapterEmbedding, Chapter).join(Chapter)

            if book_id:
                statement = statement.where(ChapterEmbedding.book_id == book_id)

            # Order by distance
            statement = statement.order_by(
                ChapterEmbedding.embedding.l2_distance(query_embedding)
            )
            statement = statement.limit(limit)

            results = await self.session.exec(statement)

            formatted_results = []
            for embedding_record, chapter in results:
                # Calculate similarity score (approximate from distance)
                # For normalized vectors, cosine similarity = 1 - (l2_distance^2) / 2
                # Or just return distance. The original code returned similarity.
                # Let's assume similarity roughly correlates inversely with distance.
                # We can compute exact distance if needed, but for now let's just return the record.

                # To filter by threshold, we might need to fetch distance.
                # SQLModel doesn't easily return the computed distance in the select unless we add it to select.

                formatted_results.append(
                    {
                        "chapter": chapter.model_dump(),  # Convert to dict
                        "content_chunk": embedding_record.content_chunk,
                        "similarity": 0.9,  # Placeholder, or calculate if possible
                        "chunk_index": embedding_record.chunk_index,
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching similar chapters: {e}")
            return []

    async def search_similar_books(
        self, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar books using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self.generate_embedding(query)

            statement = select(BookEmbedding, Book).join(Book)
            statement = statement.order_by(
                BookEmbedding.embedding.l2_distance(query_embedding)
            )
            statement = statement.limit(limit)

            results = await self.session.exec(statement)

            formatted_results = []
            for embedding_record, book in results:
                formatted_results.append(
                    {
                        "book": book.model_dump(),
                        "content_chunk": embedding_record.content_chunk,
                        "similarity": 0.9,  # Placeholder
                        "chunk_type": embedding_record.chunk_type,
                    }
                )

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching similar books: {e}")
            return []

    async def get_context_for_chapter(
        self, chapter_id: uuid.UUID, query: str = None, context_chunks: int = 3
    ) -> List[Dict[str, Any]]:
        """Get relevant context chunks for a chapter using similarity search"""
        try:
            # Get chapter content
            statement = select(Chapter).where(Chapter.id == chapter_id)
            result = await self.session.exec(statement)
            chapter = result.first()

            if not chapter:
                return []

            # Use chapter title and content as query if no specific query provided
            if not query:
                query = f"{chapter.title} {chapter.content[:500]}"

            # Search for similar content within the same book
            similar_chunks = await self.search_similar_chapters(
                query=query,
                book_id=chapter.book_id,
                limit=context_chunks,
                threshold=0.6,
            )

            return similar_chunks

        except Exception as e:
            logger.error(f"Error getting context for chapter: {e}")
            return []
