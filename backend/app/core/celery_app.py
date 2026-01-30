import ssl
import logging
import warnings
from urllib.parse import urlparse
import os
import certifi

# Suppress specific Redis SSL warnings for Upstash Redis
warnings.filterwarnings(
    "ignore",
    message=".*ssl_cert_reqs=CERT_NONE.*",
    category=UserWarning,
    module="celery.backends.redis"
)

# Configure logging
logger = logging.getLogger(__name__)

# Check if Celery should be disabled during startup
DISABLE_CELERY = os.getenv('DISABLE_CELERY_ON_STARTUP', 'false').lower() == 'true'

# Global variable to hold the lazily initialized Celery app
_celery_app = None

def get_celery_app():
    """
    Lazy initialization of Celery app to prevent blocking during FastAPI startup.
    Only creates the Celery app when actually needed.
    """
    global _celery_app
    
    if DISABLE_CELERY:
        logger.info("🚫 CELERY: Disabled during startup (DISABLE_CELERY_ON_STARTUP=true)")
        # Return a mock object that doesn't do anything
        return MockCeleryApp()
    
    if _celery_app is not None:
        return _celery_app
    
    # Import Celery only when needed
    from celery import Celery
    from app.core.config import settings
    
    logger.info("🚀 CELERY: Initializing Celery app (lazy loading)")
    
    # Parse Redis URL to determine if SSL is needed
    redis_url = settings.REDIS_URL
    parsed_url = urlparse(redis_url)
    use_ssl = parsed_url.scheme == 'rediss'
    
    logger.info(f"🔍 CELERY: Redis URL scheme: {parsed_url.scheme}")
    logger.info(f"🔍 CELERY: SSL required: {use_ssl}")
    logger.info(f"🔍 CELERY: Redis host: {parsed_url.hostname}")
    
    # Create Celery app
    _celery_app = Celery("worker")
    
    # Configure SSL settings if needed
    if use_ssl:
        logger.info("🔧 CELERY: Configuring SSL settings for Upstash Redis with proper certificates")
        
        # Use proper SSL configuration with certifi for valid certificates
        ssl_config = {
            'ssl_cert_reqs': ssl.CERT_REQUIRED,
            'ssl_check_hostname': True,
            'ssl_ca_certs': certifi.where(),
            'ssl_certfile': None,
            'ssl_keyfile': None,
        }
        
        # Add aggressive timeouts to prevent hanging on Windows
        broker_transport_options = {
            **ssl_config,
            'socket_timeout': 5.0,  # Reduced from 10s to 5s
            'socket_connect_timeout': 5.0,  # Reduced from 10s to 5s
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'retry_on_timeout': True,
            'health_check_interval': 30,
            'connection_pool_kwargs': {
                'socket_timeout': 5.0,
                'socket_connect_timeout': 5.0,
                'retry_on_timeout': True,
            }
        }
        
        result_backend_transport_options = {
            **ssl_config,
            'socket_timeout': 5.0,  # Reduced from 10s to 5s
            'socket_connect_timeout': 5.0,  # Reduced from 10s to 5s
            'socket_keepalive': True,
            'retry_on_timeout': True,
            'connection_pool_kwargs': {
                'socket_timeout': 5.0,
                'socket_connect_timeout': 5.0,
                'retry_on_timeout': True,
            }
        }
        
        _celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            broker_url=settings.CELERY_BROKER_URL,
            result_backend=settings.CELERY_RESULT_BACKEND,
            broker_transport_options=broker_transport_options,
            result_backend_transport_options=result_backend_transport_options,
            redis_backend_use_ssl=ssl_config,
            broker_use_ssl=ssl_config,
            worker_pool='solo',
            worker_concurrency=1,
            task_always_eager=False,
            task_eager_propagates=True,
            broker_connection_retry_on_startup=True,
            broker_connection_retry=True,
            broker_connection_max_retries=2,  # Reduced from 3 to 2
            broker_connection_retry_delay=1.0,  # Add 1s delay between retries
            result_backend_connection_retry=True,
            result_backend_connection_max_retries=2,
        )
        
        logger.info("✅ CELERY: SSL configuration applied")
    else:
        _celery_app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            broker_url=settings.CELERY_BROKER_URL,
            result_backend=settings.CELERY_RESULT_BACKEND,
            worker_pool='solo',
            worker_concurrency=1,
            task_always_eager=False,
            task_eager_propagates=True,
        )
    
    # Autodiscover tasks only when Celery app is actually needed
    _celery_app.autodiscover_tasks(["app.worker"])
    logger.info("✅ CELERY: App initialized and tasks discovered")
    
    return _celery_app

class MockCeleryApp:
    """Mock Celery app that does nothing - used when Celery is disabled"""
    
    def __init__(self):
        self.conf = MockConf()
    
    def __getattr__(self, name):
        # Return a no-op function for any method call
        return lambda *args, **kwargs: None
    
    def autodiscover_tasks(self, *args, **kwargs):
        pass

class MockConf:
    """Mock configuration object"""
    
    def update(self, *args, **kwargs):
        pass
    
    def __getattr__(self, name):
        return None

# Create a property-like access for backward compatibility
class CeleryAppProxy:
    """Proxy object that provides lazy access to the Celery app"""
    
    def __getattr__(self, name):
        return getattr(get_celery_app(), name)
    
    def __call__(self, *args, **kwargs):
        return get_celery_app()(*args, **kwargs)

# Export the proxy as celery_app for backward compatibility
celery_app = CeleryAppProxy()

# Export as 'celery' for Celery CLI compatibility
celery = celery_app

if DISABLE_CELERY:
    logger.info("🚫 CELERY: Completely disabled during startup - FastAPI will start without Celery")
else:
    logger.info("🚀 CELERY: Lazy initialization setup complete - no blocking during import")