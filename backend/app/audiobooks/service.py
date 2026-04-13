import uuid
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.audiobooks.models import Audiobook, AudiobookChapter
from app.books.models import Book, Chapter


class AudiobookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_audiobook(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID,
        voice_id: Optional[str] = None,
    ) -> Audiobook:
        """Create an audiobook record with chapter entries for all book chapters."""
        # Fetch book
        book_stmt = select(Book).where(Book.id == book_id)
        book_result = await self.session.exec(book_stmt)
        book = book_result.first()

        if not book:
            raise ValueError(f"Book {book_id} not found")

        # Fetch all chapters for the book
        chapters_stmt = (
            select(Chapter)
            .where(Chapter.book_id == book_id)
            .order_by(Chapter.chapter_number)
        )
        chapters_result = await self.session.exec(chapters_stmt)
        chapters = list(chapters_result.all())

        if not chapters:
            raise ValueError(f"Book {book_id} has no chapters")

        # Estimate total duration (~150 words per minute, ~2.5 seconds per sentence)
        total_chars = sum(len(ch.content or "") for ch in chapters)
        estimated_duration = total_chars / 15.0  # rough seconds estimate

        # Create audiobook
        audiobook = Audiobook(
            user_id=user_id,
            book_id=book_id,
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

        # Store estimated duration for credit reservation (caller can use this)
        audiobook._estimated_duration = estimated_duration

        return audiobook

    async def get_audiobook(
        self, audiobook_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Audiobook]:
        """Get audiobook with chapters, scoped to user."""
        stmt = (
            select(Audiobook)
            .where(Audiobook.id == audiobook_id, Audiobook.user_id == user_id)
            .options(selectinload(Audiobook.chapters))
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def list_user_audiobooks(self, user_id: uuid.UUID) -> List[Audiobook]:
        """List all audiobooks for a user."""
        stmt = (
            select(Audiobook)
            .where(Audiobook.user_id == user_id)
            .order_by(Audiobook.created_at.desc())
        )
        result = await self.session.exec(stmt)
        return list(result.all())

    async def delete_audiobook(
        self, audiobook_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete audiobook. Only allowed if completed or failed."""
        stmt = select(Audiobook).where(
            Audiobook.id == audiobook_id, Audiobook.user_id == user_id
        )
        result = await self.session.exec(stmt)
        audiobook = result.first()

        if not audiobook:
            return False

        if audiobook.status not in ("completed", "failed"):
            raise ValueError(
                f"Cannot delete audiobook in status: {audiobook.status}"
            )

        await self.session.delete(audiobook)
        await self.session.commit()
        return True

    async def update_chapter_audio(
        self,
        chapter_id: uuid.UUID,
        audio_url: str,
        duration: float,
        credits_used: int = 0,
    ) -> Optional[AudiobookChapter]:
        """Update chapter with generated audio and increment parent progress."""
        stmt = select(AudiobookChapter).where(AudiobookChapter.id == chapter_id)
        result = await self.session.exec(stmt)
        chapter = result.first()

        if not chapter:
            return None

        chapter.status = "completed"
        chapter.audio_url = audio_url
        chapter.duration_seconds = duration
        chapter.credits_used = credits_used

        self.session.add(chapter)

        # Update parent audiobook progress
        ab_stmt = select(Audiobook).where(Audiobook.id == chapter.audiobook_id)
        ab_result = await self.session.exec(ab_stmt)
        audiobook = ab_result.first()

        if audiobook:
            audiobook.completed_chapters += 1
            audiobook.total_duration_seconds = (
                (audiobook.total_duration_seconds or 0) + duration
            )
            audiobook.credits_used += credits_used

            if audiobook.completed_chapters >= audiobook.total_chapters:
                audiobook.status = "completed"
            else:
                audiobook.status = "generating"

            self.session.add(audiobook)

        await self.session.commit()
        return chapter

    async def mark_chapter_failed(
        self, chapter_id: uuid.UUID, error_message: str
    ) -> Optional[AudiobookChapter]:
        """Mark a chapter as failed."""
        stmt = select(AudiobookChapter).where(AudiobookChapter.id == chapter_id)
        result = await self.session.exec(stmt)
        chapter = result.first()

        if not chapter:
            return None

        chapter.status = "failed"
        chapter.error_message = error_message
        self.session.add(chapter)

        # Check if all chapters are done (completed or failed)
        ab_stmt = select(Audiobook).where(Audiobook.id == chapter.audiobook_id)
        ab_result = await self.session.exec(ab_stmt)
        audiobook = ab_result.first()

        if audiobook:
            audiobook.completed_chapters += 1
            audiobook.credits_used = audiobook.credits_used  # no change
            self.session.add(audiobook)

            # Check if all chapters are processed
            done_count = audiobook.completed_chapters
            if done_count >= audiobook.total_chapters:
                # Check if any succeeded
                ch_stmt = select(AudiobookChapter).where(
                    AudiobookChapter.audiobook_id == audiobook.id,
                    AudiobookChapter.status == "completed",
                )
                ch_result = await self.session.exec(ch_stmt)
                completed = list(ch_result.all())
                if completed:
                    audiobook.status = "completed"
                else:
                    audiobook.status = "failed"
                self.session.add(audiobook)

        await self.session.commit()
        return chapter

    async def get_chapter_by_number(
        self, audiobook_id: uuid.UUID, chapter_number: int, user_id: uuid.UUID
    ) -> Optional[AudiobookChapter]:
        """Get a specific chapter by audiobook and chapter number, scoped to user."""
        # First verify user owns the audiobook
        ab_stmt = select(Audiobook).where(
            Audiobook.id == audiobook_id, Audiobook.user_id == user_id
        )
        ab_result = await self.session.exec(ab_stmt)
        audiobook = ab_result.first()

        if not audiobook:
            return None

        ch_stmt = select(AudiobookChapter).where(
            AudiobookChapter.audiobook_id == audiobook_id,
            AudiobookChapter.chapter_number == chapter_number,
        )
        ch_result = await self.session.exec(ch_stmt)
        return ch_result.first()
