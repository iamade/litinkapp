from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "litink_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.ai_tasks", "app.tasks.blockchain_tasks", "app.tasks.audio_tasks","app.tasks.image_tasks",      # ✅ ADD: Missing image tasks
        "app.tasks.video_tasks",      # ✅ ADD: Missing video tasks
        "app.tasks.merge_tasks",      # ✅ ADD: Missing merge tasks
        "app.tasks.lipsync_tasks" ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True, 
)