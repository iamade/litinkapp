from celery import Celery
from app.core.config import settings



# Create Celery app with RabbitMQ broker and Redis backend
celery_app = Celery(
    "litink_tasks",
    broker=f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
)

# Configure Celery with comprehensive settings
celery_app.conf.update(
    # Serialization settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["application/json"],
    
    # Task tracking and monitoring
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    result_extended=True,
    result_backend_always_retry=True,
    
    # Result backend settings
    result_backend_max_retires=10,
    result_expires=3600,  # 1 hour
    
    # Task execution limits
    task_time_limit=5 * 60,  # 5 minutes hard limit
    task_soft_time_limit=5 * 60,  # 5 minutes soft limit
    
    # Reliability settings
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker crashes
    
    # Worker performance settings
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_max_memory_per_child=50000,  # KB - restart if exceeds ~50MB
    
    # Retry settings
    task_default_retry_delay=300,  # 5 minutes between retries
    task_max_retries=3,
    
    # Queue settings
    task_default_queue="litink_tasks",
    task_create_missing_queues=True,
    
    # Timezone settings (from original config)
    timezone="UTC",
    enable_utc=True,
    
    # # Connection retry
    # broker_connection_retry_on_startup=True,
    
    # Logging format
    worker_log_format="[%(asctime)s:%(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
)

# Auto-discover tasks from specific modules
celery_app.autodiscover_tasks(
    packages=[
        "app.tasks.ai_tasks",
        "app.tasks.blockchain_tasks", 
        "app.tasks.audio_tasks",
        "app.tasks.image_tasks",
        "app.tasks.video_tasks",
        "app.tasks.merge_tasks",
        "app.tasks.lipsync_tasks",
        "app.core.emails",  # Added from your new config
    ],
    related_name="tasks",
    force=True,
)

# Create Celery app
# celery_app = Celery(
#     "litink_tasks",
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND,
#     include=["app.tasks.ai_tasks", "app.tasks.blockchain_tasks", "app.tasks.audio_tasks","app.tasks.image_tasks",      # ✅ ADD: Missing image tasks
#         "app.tasks.video_tasks",      # ✅ ADD: Missing video tasks
#         "app.tasks.merge_tasks",      # ✅ ADD: Missing merge tasks
#         "app.tasks.lipsync_tasks" ]
# )

# # Configure Celery
# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
#     task_track_started=True,
#     task_time_limit=30 * 60,  # 30 minutes
#     task_soft_time_limit=25 * 60,  # 25 minutes
#     worker_prefetch_multiplier=1,
#     worker_max_tasks_per_child=1000,
#     broker_connection_retry_on_startup=True, 
# )