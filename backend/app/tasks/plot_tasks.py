"""
Deferred Celery task for plot generation after project upload completes (KAN-105/KAN-106).
"""

import asyncio
import logging
import uuid

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=2,
    name="app.tasks.plot_tasks.generate_plot_task",
)
def generate_plot_task(
    self,
    project_id: str,
    book_id: str,
    user_id: str,
    input_prompt: str,
    project_type: str,
):
    """Deferred plot generation for a project after upload completes."""
    return asyncio.run(
        _async_generate_plot(self, project_id, book_id, user_id, input_prompt, project_type)
    )


async def _async_generate_plot(
    task,
    project_id: str,
    book_id: str,
    user_id: str,
    input_prompt: str,
    project_type: str,
):
    from app.core.database import async_session
    from app.api.services.plot import PlotService

    project_uuid = uuid.UUID(project_id)
    book_uuid = uuid.UUID(book_id)
    user_uuid = uuid.UUID(user_id)

    logger.info("[PLOT TASK] Starting plot generation for project=%s", project_id)

    async with async_session() as session:
        try:
            plot_service = PlotService(session)
            await plot_service.generate_plot_from_prompt(
                user_id=user_uuid,
                project_id=project_uuid,
                input_prompt=input_prompt,
                project_type=project_type,
                book_id=book_uuid,
            )
            logger.info("[PLOT TASK] Plot generation complete for project=%s", project_id)
            return {"status": "SUCCESS"}
        except Exception as e:
            logger.error(
                "[PLOT TASK] Plot generation failed for project=%s: %s", project_id, e
            )
            raise task.retry(exc=e, countdown=120)
