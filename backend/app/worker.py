from app.core.celery_app import celery_app
import json
import logging

# Export celery app for Celery CLI compatibility
# This allows: python -m celery -A app.worker worker
celery = celery_app
app = celery_app  # Alternative export name

# Configure a separate logger for the worker that writes to stdout
# In a production environment, this might write to a file or an external service
worker_logger = logging.getLogger("celery_worker")
worker_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
worker_logger.addHandler(handler)

@celery_app.task(acks_late=True)
def write_log_entry(log_data: dict):
    """
    Celery task to handle log entries asynchronously.
    It receives the log record as a dictionary and writes it to the output.
    """
    try:
        # For now, we print the JSON-serialized log data to stdout
        # This will be captured by the Celery worker process logs
        log_json = json.dumps(log_data)
        worker_logger.info(log_json)
    except Exception as e:
        # Fallback in case of error to ensure we see the failure in worker logs
        print(f"Error processing log entry: {e}")

@celery_app.task(
    bind=True,
    acks_late=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=125,
    retry_jitter=True
)
def process_document_extraction_task(self, job_id: str, document_id: str, storage_key: str):
    """
    Celery task to process document extraction.
    Wraps the async job_service method and includes automatic retry logic.
    """
    import asyncio
    from app.services.jobs import job_service
    from app.db.mongodb import connect_to_mongo, close_mongo_connection
    
    async def run_async_task():
        # Ensure DB connection is available in this process/thread
        await connect_to_mongo()
        try:
            await job_service.process_document_extraction(job_id, document_id, storage_key)
        finally:
            await close_mongo_connection()
            
    try:
        asyncio.run(run_async_task())
    except Exception as e:
        worker_logger.error(f"Failed to run async extraction task: {e}")
        # The autoretry_for argument will handle the retry logic
        raise
