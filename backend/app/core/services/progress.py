"""
Progress tracking store for book uploads.
Uses an in-memory store with async queue for SSE streaming.
"""

from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import time


@dataclass
class ProgressState:
    """Track progress state for a book upload."""

    book_id: str
    percent: int = 0
    message: str = "Starting..."
    details: str = ""
    stage: str = "init"  # init, upload, toc, ocr, ai, chapters, done
    total_pages: int = 0
    current_page: int = 0
    total_chapters: int = 0
    current_chapter: int = 0
    started_at: float = field(default_factory=time.time)
    completed_steps: list = field(default_factory=list)
    is_complete: bool = False
    error: Optional[str] = None


class ProgressStore:
    """In-memory store for tracking upload progress."""

    def __init__(self):
        self._progress: Dict[str, ProgressState] = {}
        self._queues: Dict[str, asyncio.Queue] = {}

    def create(self, book_id: str) -> ProgressState:
        """Create a new progress state for a book."""
        state = ProgressState(book_id=book_id)
        self._progress[book_id] = state
        self._queues[book_id] = asyncio.Queue()
        return state

    def get(self, book_id: str) -> Optional[ProgressState]:
        """Get progress state for a book."""
        return self._progress.get(book_id)

    def get_queue(self, book_id: str) -> Optional[asyncio.Queue]:
        """Get the async queue for SSE streaming."""
        return self._queues.get(book_id)

    async def update(
        self,
        book_id: str,
        percent: Optional[int] = None,
        message: Optional[str] = None,
        details: Optional[str] = None,
        stage: Optional[str] = None,
        total_pages: Optional[int] = None,
        current_page: Optional[int] = None,
        total_chapters: Optional[int] = None,
        current_chapter: Optional[int] = None,
        completed_step: Optional[str] = None,
        is_complete: bool = False,
        error: Optional[str] = None,
    ):
        """Update progress and push to queue for SSE."""
        state = self._progress.get(book_id)
        if not state:
            return

        if percent is not None:
            state.percent = percent
        if message is not None:
            state.message = message
        if details is not None:
            state.details = details
        if stage is not None:
            state.stage = stage
        if total_pages is not None:
            state.total_pages = total_pages
        if current_page is not None:
            state.current_page = current_page
        if total_chapters is not None:
            state.total_chapters = total_chapters
        if current_chapter is not None:
            state.current_chapter = current_chapter
        if completed_step:
            state.completed_steps.append(completed_step)
        if is_complete:
            state.is_complete = True
        if error:
            state.error = error

        # Push update to queue for SSE streaming
        queue = self._queues.get(book_id)
        if queue:
            await queue.put(self._state_to_dict(state))

    def _state_to_dict(self, state: ProgressState) -> dict:
        """Convert state to dict for JSON serialization."""
        elapsed = time.time() - state.started_at

        # Estimate remaining time based on progress
        if state.percent > 0 and state.percent < 100:
            estimated_total = elapsed / (state.percent / 100)
            remaining = max(0, estimated_total - elapsed)
        else:
            remaining = 0

        return {
            "percent": state.percent,
            "message": state.message,
            "details": state.details,
            "stage": state.stage,
            "total_pages": state.total_pages,
            "current_page": state.current_page,
            "total_chapters": state.total_chapters,
            "current_chapter": state.current_chapter,
            "completed_steps": state.completed_steps,
            "is_complete": state.is_complete,
            "error": state.error,
            "elapsed_seconds": int(elapsed),
            "remaining_seconds": int(remaining),
        }

    def cleanup(self, book_id: str):
        """Remove progress state after completion."""
        self._progress.pop(book_id, None)
        self._queues.pop(book_id, None)


# Global singleton
progress_store = ProgressStore()
