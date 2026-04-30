import asyncio
import uuid
from typing import Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from app.tasks.celery_app import celery_app
from app.audiobooks.models import Audiobook, AudiobookChapter
from app.books.models import Chapter
from app.subscriptions.models import UserSubscription
from app.credits.service import CreditService, credits_for_audio_duration
from app.core.services.tts import tts_router
from app.core.database import get_session
from sqlmodel import select
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@asynccontextmanager
async def session_scope():
    """Context manager wrapper for get_session generator."""
    async for session in get_session():
        yield session


@celery_app.task(bind=True)
def generate_audiobook_task(
    self, audiobook_id: str, reservation_id: Optional[str] = None
):
    """Generate audiobook by processing each chapter through TTS.

    KAN-176: ``reservation_id`` is propagated from the /listen/generate route
    so this task can settle the existing credit reservation instead of creating
    a fresh deduction transaction (which double-charged and leaked reservations).
    """

    async def _generate():
        logger.info(
            f"[AUDIOBOOK] Starting generation for audiobook: {audiobook_id} "
            f"reservation={reservation_id}"
        )

        async with session_scope() as session:
            # Fetch audiobook with metadata
            ab_stmt = select(Audiobook).where(Audiobook.id == uuid.UUID(audiobook_id))
            ab_result = await session.exec(ab_stmt)
            audiobook = ab_result.first()

            if not audiobook:
                raise Exception(f"Audiobook {audiobook_id} not found")

            user_id = audiobook.user_id
            voice_id = audiobook.voice_id

            # Get user tier
            sub_stmt = select(UserSubscription).where(
                UserSubscription.user_id == user_id
            )
            sub_result = await session.exec(sub_stmt)
            subscription = sub_result.first()
            user_tier = subscription.tier if subscription else "free"

            # Mark as generating
            audiobook.status = "generating"
            session.add(audiobook)
            await session.commit()

            # Fetch all audiobook chapters in order
            ch_stmt = (
                select(AudiobookChapter)
                .where(AudiobookChapter.audiobook_id == audiobook.id)
                .order_by(AudiobookChapter.chapter_number)
            )
            ch_result = await session.exec(ch_stmt)
            ab_chapters = list(ch_result.all())

            credit_service = CreditService(session)
            max_chars = tts_router.max_chars_per_request(user_tier)

            for ab_chapter in ab_chapters:
                try:
                    logger.info(
                        f"[AUDIOBOOK] Processing chapter {ab_chapter.chapter_number}/{audiobook.total_chapters}"
                    )

                    # Fetch source chapter content
                    src_stmt = select(Chapter).where(
                        Chapter.id == ab_chapter.chapter_id
                    )
                    src_result = await session.exec(src_stmt)
                    source_chapter = src_result.first()

                    if not source_chapter or not source_chapter.content:
                        logger.warning(
                            f"[AUDIOBOOK] Chapter {ab_chapter.chapter_number} has no content"
                        )
                        raise Exception("No content available")

                    content = source_chapter.content
                    audio_urls = []
                    total_duration = 0.0
                    chapter_credits = 0

                    # Split content into chunks if needed
                    chunks = _split_text(content, max_chars)

                    for i, chunk in enumerate(chunks):
                        logger.info(
                            f"[AUDIOBOOK] Synthesizing chunk {i+1}/{len(chunks)} for chapter {ab_chapter.chapter_number}"
                        )

                        # Synthesize via TTS router
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

                    # Calculate credits. Do not deduct per chapter here.
                    # KAN-176: settle the route-created reservation once at
                    # finalization with the actual total credits used.
                    chapter_credits = credits_for_audio_duration(total_duration)

                    # Update chapter with primary audio URL (first chunk or concatenated)
                    primary_url = audio_urls[0] if audio_urls else None
                    if len(audio_urls) > 1:
                        # Store all URLs as JSON string for future concatenation
                        import json

                        primary_url = audio_urls[
                            0
                        ]  # Frontend can request merge separately

                    if primary_url:
                        # Re-fetch to avoid stale session issues
                        ch_stmt2 = select(AudiobookChapter).where(
                            AudiobookChapter.id == ab_chapter.id
                        )
                        ch_result2 = await session.exec(ch_stmt2)
                        fresh_chapter = ch_result2.first()

                        fresh_chapter.status = "completed"
                        fresh_chapter.audio_url = primary_url
                        fresh_chapter.duration_seconds = total_duration
                        fresh_chapter.credits_used = chapter_credits
                        session.add(fresh_chapter)

                        # Update audiobook progress
                        ab_stmt2 = select(Audiobook).where(Audiobook.id == audiobook.id)
                        ab_result2 = await session.exec(ab_stmt2)
                        fresh_ab = ab_result2.first()
                        fresh_ab.completed_chapters += 1
                        fresh_ab.total_duration_seconds = (
                            fresh_ab.total_duration_seconds or 0
                        ) + total_duration
                        fresh_ab.credits_used += chapter_credits

                        if fresh_ab.completed_chapters >= fresh_ab.total_chapters:
                            fresh_ab.status = "completed"
                        else:
                            fresh_ab.status = "generating"

                        session.add(fresh_ab)
                        await session.commit()

                        logger.info(
                            f"[AUDIOBOOK] ✅ Chapter {ab_chapter.chapter_number} complete ({total_duration:.1f}s, {chapter_credits} credits)"
                        )
                    else:
                        raise Exception("No audio URL returned from TTS")

                except Exception as e:
                    logger.error(
                        f"[AUDIOBOOK] ❌ Chapter {ab_chapter.chapter_number} failed: {e}"
                    )
                    try:
                        ch_stmt3 = select(AudiobookChapter).where(
                            AudiobookChapter.id == ab_chapter.id
                        )
                        ch_result3 = await session.exec(ch_stmt3)
                        fresh_ch = ch_result3.first()
                        fresh_ch.status = "failed"
                        fresh_ch.error_message = str(e)
                        session.add(fresh_ch)

                        # Update audiobook progress even on failure
                        ab_stmt3 = select(Audiobook).where(Audiobook.id == audiobook.id)
                        ab_result3 = await session.exec(ab_stmt3)
                        fresh_ab = ab_result3.first()
                        fresh_ab.completed_chapters += 1

                        if fresh_ab.completed_chapters >= fresh_ab.total_chapters:
                            fresh_ab.status = "completed"  # Partial success
                        else:
                            fresh_ab.status = "generating"

                        session.add(fresh_ab)
                        await session.commit()
                    except Exception as update_err:
                        logger.error(
                            f"[AUDIOBOOK] Failed to update chapter error: {update_err}"
                        )

            # Final status check
            ab_final = select(Audiobook).where(Audiobook.id == audiobook.id)
            final_result = await session.exec(ab_final)
            final_ab = final_result.first()

            if final_ab and final_ab.completed_chapters >= final_ab.total_chapters:
                # Check if any chapters succeeded
                success_stmt = select(AudiobookChapter).where(
                    AudiobookChapter.audiobook_id == audiobook.id,
                    AudiobookChapter.status == "completed",
                )
                success_result = await session.exec(success_stmt)
                successful = list(success_result.all())

                if not successful:
                    final_ab.status = "failed"
                    final_ab.error_message = "All chapters failed"
                    session.add(final_ab)
                    if reservation_id:
                        released = await credit_service.release_reservation(
                            uuid.UUID(reservation_id)
                        )
                        if not released:
                            logger.warning(
                                "[AUDIOBOOK] Credit reservation release failed for %s",
                                reservation_id,
                            )
                    await session.commit()
                else:
                    if reservation_id:
                        confirmed = await credit_service.confirm_deduction(
                            uuid.UUID(reservation_id),
                            actual_amount=final_ab.credits_used or 0,
                        )
                        if not confirmed:
                            logger.error(
                                "[AUDIOBOOK] Credit reservation confirmation failed for %s",
                                reservation_id,
                            )
                        await session.commit()
                    logger.info(
                        f"[AUDIOBOOK] ✅ Audiobook complete: {len(successful)}/{final_ab.total_chapters} chapters, "
                        f"{final_ab.total_duration_seconds:.1f}s total, {final_ab.credits_used} credits used"
                    )

            return {"status": "success", "audiobook_id": audiobook_id}

    return asyncio.run(_generate())


def _split_text(text: str, max_chars: int) -> list:
    """Split text into chunks that fit within TTS character limits.
    Tries to split on sentence boundaries."""
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks = []
    # Split on sentence boundaries
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in ".!?\n" and len(current) > 0:
            sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    # Group sentences into chunks
    chunk = ""
    for sentence in sentences:
        if len(chunk) + len(sentence) > max_chars and chunk:
            chunks.append(chunk.strip())
            chunk = sentence
        else:
            chunk += " " + sentence if chunk else sentence

    if chunk.strip():
        # If single chunk is still too long, hard split
        while len(chunk) > max_chars:
            chunks.append(chunk[:max_chars].strip())
            chunk = chunk[max_chars:]
        if chunk.strip():
            chunks.append(chunk.strip())

    return chunks
