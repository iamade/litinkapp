"""
KAN-176: Audiobook /listen API contract tests (test-first).

Covers:
- POST /listen/generate: credit reservation + task dispatch
- GET  /listen/ (list): user audiobook listing
- GET  /listen/{id}: audiobook detail + ownership scoping
- GET  /listen/{id}/chapters/{n}/audio: chapter audio retrieval
- DELETE /listen/{id}: deletion status gate
- GET  /listen/voices: voice listing
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _async_gen(*items):
    """Turn a list of items into an async generator."""
    for item in items:
        yield item


def _make_mock_session():
    """Create a session mock whose sync/async methods match SQLModel AsyncSession."""
    session = MagicMock()
    session.exec = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_mock_audiobook(**overrides):
    """Create a mock Audiobook with sensible defaults."""
    m = MagicMock()
    m.id = overrides.get("id", uuid.uuid4())
    m.user_id = overrides.get("user_id", uuid.uuid4())
    m.book_id = overrides.get("book_id", uuid.uuid4())
    m.title = overrides.get("title", "Audiobook: Test Book")
    m.status = overrides.get("status", "pending")
    m.voice_id = overrides.get("voice_id", "voice-1")
    m.total_chapters = overrides.get("total_chapters", 3)
    m.completed_chapters = overrides.get("completed_chapters", 0)
    m.total_duration_seconds = overrides.get("total_duration_seconds", 0.0)
    m.error_message = overrides.get("error_message", None)
    m.credits_reserved = overrides.get("credits_reserved", 30)
    m.credits_used = overrides.get("credits_used", 0)
    m.created_at = overrides.get("created_at", None)
    m.updated_at = overrides.get("updated_at", None)
    m._estimated_duration = overrides.get("_estimated_duration", 300.0)
    return m


# ---------------------------------------------------------------------------
# 1. POST /listen/generate — success path (test route directly)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_audiobook_success():
    """KAN-176: generate_audiobook reserves credits, creates audiobook,
    dispatches task with reservation_id, returns 202."""
    from app.audiobooks.routes import generate_audiobook
    from app.audiobooks.schemas import AudiobookGenerateRequest

    user_id = uuid.uuid4()
    book_id = uuid.uuid4()
    audiobook_id = uuid.uuid4()
    reservation_id = uuid.uuid4()

    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}
    request = AudiobookGenerateRequest(book_id=book_id, voice_id="voice-1")

    mock_session = _make_mock_session()
    mock_audiobook = _make_mock_audiobook(
        id=audiobook_id, user_id=user_id, book_id=book_id
    )

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.select") as mock_select, patch(
        "app.audiobooks.routes.AudiobookService"
    ) as mock_svc_cls, patch(
        "app.audiobooks.routes.CreditService"
    ) as mock_credit_cls, patch(
        "app.audiobooks.tasks.generate_audiobook_task"
    ) as mock_task:
        # Setup subscription query
        mock_sub = MagicMock()
        mock_sub.tier = "free"
        mock_sub_result = MagicMock()
        mock_sub_result.first.return_value = mock_sub
        mock_session.exec.return_value = mock_sub_result

        # Setup audiobook service
        mock_svc = AsyncMock()
        mock_svc.create_audiobook.return_value = mock_audiobook
        mock_svc_cls.return_value = mock_svc

        # Setup credit service
        mock_credit = AsyncMock()
        mock_credit.reserve_credits.return_value = reservation_id
        mock_credit_cls.return_value = mock_credit

        result = await generate_audiobook(request=request, user=mock_user)

        # Verify credit reservation
        mock_credit.reserve_credits.assert_called_once()

        # Verify task dispatched WITH reservation_id
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0]
        assert call_args[0] == str(audiobook_id), "First arg must be audiobook_id"
        assert (
            len(call_args) >= 2
        ), f"Expected delay(audiobook_id, reservation_id), got delay{call_args}"
        assert call_args[1] == str(
            reservation_id
        ), f"Expected reservation_id={reservation_id} as 2nd arg, got {call_args[1]}"

        # Verify response
        assert result.status == "pending"
        assert result.credits_reserved == 300


# ---------------------------------------------------------------------------
# 2. POST /listen/generate — credit reservation failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_audiobook_insufficient_credits():
    """KAN-176: 402 when credit reservation fails, audiobook deleted."""
    from app.audiobooks.routes import generate_audiobook
    from app.audiobooks.schemas import AudiobookGenerateRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    book_id = uuid.uuid4()
    audiobook_id = uuid.uuid4()

    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}
    request = AudiobookGenerateRequest(book_id=book_id, voice_id="voice-1")

    mock_session = _make_mock_session()
    mock_audiobook = _make_mock_audiobook(id=audiobook_id)

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.select") as mock_select, patch(
        "app.audiobooks.routes.AudiobookService"
    ) as mock_svc_cls, patch(
        "app.audiobooks.routes.CreditService"
    ) as mock_credit_cls:
        mock_sub = MagicMock()
        mock_sub.tier = "free"
        mock_sub_result = MagicMock()
        mock_sub_result.first.return_value = mock_sub
        mock_session.exec.return_value = mock_sub_result

        mock_svc = AsyncMock()
        mock_svc.create_audiobook.return_value = mock_audiobook
        mock_svc_cls.return_value = mock_svc

        mock_credit = AsyncMock()
        mock_credit.reserve_credits.side_effect = ValueError("Insufficient")
        mock_credit_cls.return_value = mock_credit

        try:
            await generate_audiobook(request=request, user=mock_user)
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 402
            assert "Insufficient" in e.detail

        # Verify audiobook was deleted
        mock_session.delete.assert_called_once_with(mock_audiobook)


# ---------------------------------------------------------------------------
# 3. POST /listen/generate — book not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_audiobook_book_not_found():
    """KAN-176: 400 when book doesn't exist."""
    from app.audiobooks.routes import generate_audiobook
    from app.audiobooks.schemas import AudiobookGenerateRequest
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    book_id = uuid.uuid4()

    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}
    request = AudiobookGenerateRequest(book_id=book_id)

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.select") as mock_select, patch(
        "app.audiobooks.routes.AudiobookService"
    ) as mock_svc_cls:
        mock_sub = MagicMock()
        mock_sub.tier = "free"
        mock_sub_result = MagicMock()
        mock_sub_result.first.return_value = mock_sub
        mock_session.exec.return_value = mock_sub_result

        mock_svc = AsyncMock()
        mock_svc.create_audiobook.side_effect = ValueError("Book not found")
        mock_svc_cls.return_value = mock_svc

        try:
            await generate_audiobook(request=request, user=mock_user)
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 400


# ---------------------------------------------------------------------------
# 4. GET /listen/ — list user audiobooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_audiobooks_empty():
    """KAN-176: list audiobooks returns empty list."""
    from app.audiobooks.routes import list_audiobooks

    user_id = uuid.uuid4()
    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.select") as mock_select, patch(
        "app.audiobooks.routes.AudiobookService"
    ) as mock_svc_cls:
        mock_sub = MagicMock()
        mock_sub.tier = "free"
        mock_sub_result = MagicMock()
        mock_sub_result.first.return_value = mock_sub
        mock_session.exec.side_effect = [mock_sub_result, MagicMock()]

        mock_svc = AsyncMock()
        mock_svc.list_user_audiobooks.return_value = []
        mock_svc_cls.return_value = mock_svc

        result = await list_audiobooks(user=mock_user)
        assert isinstance(result, list)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# 5. GET /listen/{id} — not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_audiobook_not_found():
    """KAN-176: 404 when audiobook doesn't exist or wrong user."""
    from app.audiobooks.routes import get_audiobook
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    audiobook_id = uuid.uuid4()
    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.AudiobookService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.get_audiobook.return_value = None
        mock_svc_cls.return_value = mock_svc

        try:
            await get_audiobook(audiobook_id=audiobook_id, user=mock_user)
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 404


# ---------------------------------------------------------------------------
# 6. GET /listen/{id}/chapters/{n}/audio — chapter not completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_chapter_audio_not_completed():
    """KAN-176: 202 when chapter is still generating."""
    from app.audiobooks.routes import get_chapter_audio
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    audiobook_id = uuid.uuid4()
    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.AudiobookService") as mock_svc_cls:
        mock_chapter = MagicMock()
        mock_chapter.status = "generating"
        mock_svc = AsyncMock()
        mock_svc.get_chapter_by_number.return_value = mock_chapter
        mock_svc_cls.return_value = mock_svc

        try:
            await get_chapter_audio(
                audiobook_id=audiobook_id, chapter_number=1, user=mock_user
            )
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 202


# ---------------------------------------------------------------------------
# 7. DELETE /listen/{id} — wrong status guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_audiobook_wrong_status():
    """KAN-176: 400 when deleting audiobook in pending/generating status."""
    from app.audiobooks.routes import delete_audiobook
    from fastapi import HTTPException

    user_id = uuid.uuid4()
    audiobook_id = uuid.uuid4()
    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.AudiobookService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.delete_audiobook.side_effect = ValueError("Cannot delete")
        mock_svc_cls.return_value = mock_svc

        try:
            await delete_audiobook(audiobook_id=audiobook_id, user=mock_user)
            assert False, "Expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 400


# ---------------------------------------------------------------------------
# 8. GET /listen/voices — voice listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_voices():
    """KAN-176: list_voices returns available TTS voices."""
    from app.audiobooks.routes import list_voices

    user_id = uuid.uuid4()
    mock_user = {"id": str(user_id), "email": "test@litinkai.com"}

    mock_session = _make_mock_session()

    with patch(
        "app.audiobooks.routes.get_session", return_value=_async_gen(mock_session)
    ), patch("app.audiobooks.routes.select") as mock_select, patch(
        "app.audiobooks.routes.tts_router"
    ) as mock_router:
        mock_sub = MagicMock()
        mock_sub.tier = "free"
        mock_sub_result = MagicMock()
        mock_sub_result.first.return_value = mock_sub
        mock_session.exec.return_value = mock_sub_result

        mock_voice = MagicMock()
        mock_voice.id = "voice-1"
        mock_voice.name = "Ethan"
        mock_voice.language = "en-US"
        mock_voice.gender = "male"
        mock_voice.preview_url = "https://example.com/preview.mp3"
        mock_router.list_voices = AsyncMock(return_value=[mock_voice])

        result = await list_voices(user=mock_user)

        assert len(result) == 1
        assert result[0].voice_id == "voice-1"
        assert result[0].name == "Ethan"


# ---------------------------------------------------------------------------
# 9. Task credit settlement contract
# ---------------------------------------------------------------------------


def test_generate_audiobook_task_uses_reservation_settlement_not_fresh_deduct():
    """KAN-176: task must accept reservation_id and settle that reservation.

    This guards against the previous double-charge/leaked-reservation contract:
    route reserved credits, but task created a fresh deduction and never settled
    the reservation.
    """
    import inspect
    from app.audiobooks import tasks

    signature = inspect.signature(tasks.generate_audiobook_task)
    assert "reservation_id" in signature.parameters

    source = inspect.getsource(tasks.generate_audiobook_task)
    assert "confirm_deduction" in source
    assert "release_reservation" in source
    assert "deduct_for_operation" not in source
