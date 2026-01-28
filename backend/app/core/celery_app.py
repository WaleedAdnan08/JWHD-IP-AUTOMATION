from celery import Celery
from app.core.config import settings

celery_app = Celery("worker", broker=settings.CELERY_BROKER_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Add compatibility settings for Python 3.14
    worker_pool="solo",  # Use solo pool for Windows compatibility
    worker_concurrency=1,  # Single worker process
    task_always_eager=False,  # Ensure tasks run asynchronously
    task_eager_propagates=True,  # Propagate exceptions in eager mode
)

# Auto-discover tasks from modules
celery_app.autodiscover_tasks(["app.worker"])