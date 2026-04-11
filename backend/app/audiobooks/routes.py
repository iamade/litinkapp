import uuid
from typing import List
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_session
from app.audiobooks.models import Audiobook, AudiobookChapter
from app.audiobooks.schemas import (
    AudiobookGenerateRequest,
    AudiobookResponse,
    AudiobookDetailResponse,
    AudiobookChapterResponse,
    VoiceOptionResponse,
)
from app.audiobooks.service import AudiobookService
from app.credits.service import CreditService, credits_for_audio_duration
from app.core.services.tts import tts_router
from app.subscriptions.models import UserSubscription
from sqlmodel import select

router = APIRouter()


@router.post("/generate", response_model=AudiobookResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_audiobook(
    request: AudiobookGenerateRequest,
    user=Depends(get_current_user),
):
    """Create a new audiobook generation job for a book."""
    user_id = uuid.UUID(user["id"])

    async for session in get_session():
        # Get user tier for credit estimation
        sub_stmt = select(UserSubscription).where(
            UserSubscription.user_id == user_id
        )
        sub_result = await session.exec(sub_stmt)
        subscription = sub_result.first()
        user_tier = subscription.tier if subscription else "free"

        service = AudiobookService(session)

        # Create audiobook with chapter records
        try:
            audiobook = await service.create_audiobook(
                user_id=user_id,
                book_id=request.book_id,
                voice_id=request.voice_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Estimate credit cost
        estimated_duration = getattr(audiobook, "_estimated_duration", 300.0)
        estimated_credits = credits_for_audio_duration(estimated_duration)

        # Reserve credits
        credit_service = CreditService(session)
        try:
            reservation = await credit_service.reserve_credits(
                user_id=user_id,
                amount=estimated_credits,
                operation_type="audio_gen",
                metadata={
                    "audiobook_id": str(audiobook.id),
                    "book_id": str(request.book_id),
                    "estimated_duration": estimated_duration,
                },
            )
            audiobook.credits_reserved = estimated_credits
            audiobook.status = "pending"
            session.add(audiobook)
            await session.commit()
            await session.refresh(audiobook)
        except Exception as e:
            # If credit reservation fails, delete the audiobook
            await session.delete(audiobook)
            await session.commit()
            raise HTTPException(status_code=402, detail=f"Insufficient credits: {str(e)}")

        # Dispatch Celery task
        from app.audiobooks.tasks import generate_audiobook_task
        generate_audiobook_task.delay(str(audiobook.id))

        return audiobook


@router.get("/voices", response_model=List[VoiceOptionResponse])
async def list_voices(
    user=Depends(get_current_user),
):
    """List available TTS voices for audiobook generation."""
    user_id = uuid.UUID(user["id"])

    async for session in get_session():
        # Get user tier
        sub_stmt = select(UserSubscription).where(
            UserSubscription.user_id == user_id
        )
        sub_result = await session.exec(sub_stmt)
        subscription = sub_result.first()
        user_tier = subscription.tier if subscription else "free"

    voices = await tts_router.list_voices(user_tier)
    return [
        VoiceOptionResponse(
            voice_id=v.id,
            name=v.name,
            language=getattr(v, "language", None),
            gender=getattr(v, "gender", None),
            preview_url=getattr(v, "preview_url", None),
        )
        for v in voices
    ]


@router.get("/{audiobook_id}", response_model=AudiobookDetailResponse)
async def get_audiobook(
    audiobook_id: uuid.UUID,
    user=Depends(get_current_user),
):
    """Get audiobook status with all chapters."""
    user_id = uuid.UUID(user["id"])

    async for session in get_session():
        service = AudiobookService(session)
        audiobook = await service.get_audiobook(audiobook_id, user_id)

        if not audiobook:
            raise HTTPException(status_code=404, detail="Audiobook not found")

        return audiobook


@router.get(
    "/{audiobook_id}/chapters/{chapter_number}/audio",
    response_model=AudiobookChapterResponse,
)
async def get_chapter_audio(
    audiobook_id: uuid.UUID,
    chapter_number: int,
    user=Depends(get_current_user),
):
    """Get audio for a specific chapter."""
    user_id = uuid.UUID(user["id"])

    async for session in get_session():
        service = AudiobookService(session)
        chapter = await service.get_chapter_by_number(
            audiobook_id, chapter_number, user_id
        )

        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")

        if chapter.status != "completed":
            raise HTTPException(
                status_code=202,
                detail=f"Chapter audio is {chapter.status}",
            )

        return chapter


@router.delete("/{audiobook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audiobook(
    audiobook_id: uuid.UUID,
    user=Depends(get_current_user),
):
    """Delete an audiobook. Only allowed when completed or failed."""
    user_id = uuid.UUID(user["id"])

    async for session in get_session():
        service = AudiobookService(session)
        try:
            deleted = await service.delete_audiobook(audiobook_id, user_id)
            if not deleted:
                raise HTTPException(status_code=404, detail="Audiobook not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
