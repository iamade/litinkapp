"""
AudiobookService — orchestrates book-to-audiobook pipeline.
Plan 13 Part 1: Listen Mode.

Location per spec: app/core/services/audiobook_service.py
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.audiobooks.models import Audiobook, AudiobookChapter
from app.books.models import Book, Chapter
from app.core.services.tts import tts_router
from app.credits.service import credits_for_audio_duration


class AudiobookService:
    """Orchestrates the book-to-audiobook generation pipeline."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_audiobook(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        tts_config: Optional[Dict[str, Any]] = None,
    ) -> Audiobook:
        """Full pipeline: get chapters → clean text → chunk → TTS API → metadata → store.

        Creates an Audiobook record and AudiobookChapter records for all chapters.
        Does NOT run TTS — that's handled by the Celery task.
        """
        voice_id = tts_config.get("voice_id") if tts_config else None

        # Fetch book (project)
        book_stmt = select(Book).where(Book.id == project_id)
        book_result = await self.session.exec(book_stmt)
        book = book_result.first()

        if not book:
            raise ValueError(f"Book/project {project_id} not found")

        # Fetch chapters
        chapters_stmt = (
            select(Chapter)
            .where(Chapter.book_id == project_id)
            .order_by(Chapter.chapter_number)
        )
        chapters_result = await self.session.exec(chapters_stmt)
        chapters = list(chapters_result.all())

        if not chapters:
            raise ValueError(f"Book {project_id} has no chapters")

        # Create audiobook record
        audiobook = Audiobook(
            user_id=user_id,
            book_id=project_id,
            title=f"Audiobook: {book.title}",
            voice_id=voice_id,
            total_chapters=len(chapters),
            completed_chapters=0,
            total_duration_seconds=0.0,
            status="pending",
        )
        self.session.add(audiobook)
        await self.session.commit()
        await self.session.refresh(audiobook)

        # Create chapter records
        for chapter in chapters:
            ab_chapter = AudiobookChapter(
                audiobook_id=audiobook.id,
                chapter_id=chapter.id,
                chapter_number=chapter.chapter_number,
                status="pending",
            )
            self.session.add(ab_chapter)

        await self.session.commit()
        await self.session.refresh(audiobook)

        return audiobook

    async def generate_chapter_audio(
        self,
        chapter_text: str,
        tts_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Single chapter TTS generation. Handles text chunking for API limits.

        Returns dict with audio_url, duration, credits_used.
        """
        user_tier = tts_config.get("user_tier", "free")
        voice_id = tts_config.get("voice_id")

        max_chars = tts_router.max_chars_per_request(user_tier)
        chunks = _split_text(chapter_text, max_chars)

        audio_urls = []
        total_duration = 0.0

        for chunk in chunks:
            result = await tts_router.synthesize(
                text=chunk,
                user_tier=user_tier,
                voice_id=voice_id,
            )
            audio_url = result.get("audio_url") or result.get("url")
            duration = result.get("duration", 0.0)

            if audio_url:
                audio_urls.append(audio_url)
                total_duration += duration

        credits_used = credits_for_audio_duration(total_duration)

        return {
            "audio_url": audio_urls[0] if audio_urls else None,
            "all_urls": audio_urls,
            "duration": total_duration,
            "credits_used": credits_used,
            "chunks_processed": len(audio_urls),
        }


def _split_text(text: str, max_chars: int) -> List[str]:
    """Split text into chunks respecting sentence boundaries."""
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in ".!?\n" and current.strip():
            sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    chunk = ""
    for sentence in sentences:
        if len(chunk) + len(sentence) > max_chars and chunk:
            chunks.append(chunk.strip())
            chunk = sentence
        else:
            chunk += " " + sentence if chunk else sentence

    if chunk.strip():
        while len(chunk) > max_chars:
            chunks.append(chunk[:max_chars].strip())
            chunk = chunk[max_chars:]
        if chunk.strip():
            chunks.append(chunk.strip())

    return chunks
