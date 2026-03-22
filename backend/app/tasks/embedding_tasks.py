"""
Deferred Celery tasks for generating embeddings after project upload completes.
Decouples slow Google/OpenAI API calls from the upload flow (KAN-105/KAN-106).
"""

import asyncio
import logging
import time
import uuid

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    name="app.tasks.embedding_tasks.generate_project_embeddings_task",
)
def generate_project_embeddings_task(self, project_id: str, book_id: str):
    """Deferred embedding generation for all chapters in a project."""
    return asyncio.run(_async_generate_project_embeddings(self, project_id, book_id))


async def _async_generate_project_embeddings(task, project_id: str, book_id: str):
    from app.core.database import async_session
    from app.core.services.embeddings import EmbeddingsService
    from app.books.models import Chapter as ChapterModel
    from app.projects.models import Project
    from sqlmodel import select

    project_uuid = uuid.UUID(project_id)
    book_uuid = uuid.UUID(book_id)

    logger.info(
        "[EMBED TASK] Starting embedding generation for project=%s book=%s",
        project_id,
        book_id,
    )
    task_start = time.time()

    async with async_session() as session:
        try:
            # Fetch all chapters for the book
            stmt = select(ChapterModel).where(ChapterModel.book_id == book_uuid)
            result = await session.exec(stmt)
            chapters = result.all()

            total = len(chapters)
            if total == 0:
                logger.warning(
                    "[EMBED TASK] No chapters found for book=%s, skipping.", book_id
                )
                return {"status": "skipped", "reason": "no chapters"}

            logger.info("[EMBED TASK] Generating embeddings for %d chapters.", total)

            failed = 0
            for idx, chapter in enumerate(chapters):
                chapter_start = time.time()
                try:
                    embeddings_service = EmbeddingsService(session)
                    await embeddings_service.create_chapter_embeddings(
                        chapter.id, chapter.content or ""
                    )
                    elapsed = time.time() - chapter_start
                    logger.info(
                        "[EMBED TASK] Chapter %d/%d (id=%s) embedded in %.2fs",
                        idx + 1,
                        total,
                        chapter.id,
                        elapsed,
                    )
                except Exception as e:
                    failed += 1
                    logger.error(
                        "[EMBED TASK] Failed to embed chapter %d/%d (id=%s): %s",
                        idx + 1,
                        total,
                        chapter.id,
                        e,
                    )

            total_elapsed = time.time() - task_start
            logger.info(
                "[EMBED TASK] Embedding complete for project=%s: %d/%d chapters in %.2fs",
                project_id,
                total - failed,
                total,
                total_elapsed,
            )

            # Mark project upload_status based on outcome
            proj_stmt = select(Project).where(Project.id == project_uuid)
            proj_result = await session.exec(proj_stmt)
            project = proj_result.first()
            if project:
                if failed > 0 and failed == total:
                    project.upload_status = "completed_partial"
                    logger.warning(
                        "[EMBED TASK] All embeddings failed — marking project as completed_partial"
                    )
                # If some succeeded, project is already "completed"; partial failures are acceptable
                session.add(project)
                await session.commit()

            return {
                "status": "SUCCESS",
                "total": total,
                "embedded": total - failed,
                "failed": failed,
                "elapsed_seconds": round(total_elapsed, 2),
            }

        except Exception as e:
            logger.error(
                "[EMBED TASK] Unexpected error for project=%s: %s", project_id, e
            )
            try:
                # Mark as completed_partial so the upload isn't stuck in "processing"
                proj_stmt = select(Project).where(Project.id == project_uuid)
                proj_result = await session.exec(proj_stmt)
                project = proj_result.first()
                if project and project.upload_status not in ("completed", "failed"):
                    project.upload_status = "completed_partial"
                    session.add(project)
                    await session.commit()
            except Exception as inner_err:
                logger.error(
                    "[EMBED TASK] Could not set completed_partial for project=%s: %s",
                    project_id,
                    inner_err,
                )
            raise self.retry(exc=e, countdown=60)
