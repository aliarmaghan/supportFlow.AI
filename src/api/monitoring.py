"""OVERVIEW:
The monitoring.py file is like the "CCTV + health check system" of your FastAPI project.
It does three major things:
    🧾 Logging:
    Captures detailed information about what’s happening inside your app (like requests, errors, or conversations) and stores them in structured JSON format for easy analysis.

    📊 Metrics Tracking (Prometheus):
    Measures important statistics — how many requests were made, how long they took, how many conversations/messages occurred, etc.

    ❤️ Health Monitoring:
    Continuously checks if your system’s components (like the database or cache) are working properly and how fast they respond.

In simple words:
This file helps you observe, debug, and measure your system’s behavior — like a smart monitoring dashboard for your app."""


import logging
import time
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import json
import sys

# Prometheus Metrics
"""
These are special variables that track data over time.
Prometheus is a monitoring tool that collects such metrics.

Here are the metrics defined:

| Metric Variable      | Type      | Tracks What                                                   |
| -------------------- | --------- | ------------------------------------------------------------- |
| `REQUEST_COUNT`      | Counter   | How many total API requests are made (and their status codes) |
| `REQUEST_DURATION`   | Histogram | How long each request takes (in seconds)                      |
| `CONVERSATION_COUNT` | Counter   | Total conversations created                                   |
| `MESSAGE_COUNT`      | Counter   | Total number of messages (user/assistant)                     |
| `ESCALATION_COUNT`   | Counter   | How many escalations occurred (like urgent customer issues)   |

"""
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

CONVERSATION_COUNT = Counter(
    'conversations_total',
    'Total conversations created',
    ['status']
)

MESSAGE_COUNT = Counter(
    'messages_total',
    'Total messages processed',
    ['type']  # user, assistant
)

ESCALATION_COUNT = Counter(
    'escalations_total',
    'Total escalations',
    ['priority']
)


# Structured JSON Logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better parsing"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(), # when it happened
            'level': record.levelname,  # info/warning/error
            'logger': record.name,  # where it happened
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'customer_id'):
            log_data['customer_id'] = record.customer_id
        if hasattr(record, 'conversation_id'):
            log_data['conversation_id'] = record.conversation_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        return json.dumps(log_data)


def setup_logging():
    """Creates a root logger for the whole app.
        Sets log level to INFO.
        Adds a console handler that outputs logs to the terminal in JSON format.
        Reduces noise from external libraries (like uvicorn).
    """
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Reduce noise from some libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logger


# Request logging middleware
class MonitoringMiddleware(BaseHTTPMiddleware):
    """Starts a timer when a request begins.
        Calls the next function to actually process the request.
        Calculates how long it took.
        Increments Prometheus metrics for that request.
        Logs info about the request (method, path, status code, duration, IP address)."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # Log request
        logger = logging.getLogger(__name__)
        logger.info(
            f"{request.method} {request.url.path} {response.status_code}",
            extra={
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'client_ip': request.client.host if request.client else 'unknown'
            }
        )
        
        return response


# Health check with detailed metrics
class HealthCheck:
    """This checks if your app’s key components (like the database or cache) are healthy and responding fast."""
    
    @staticmethod
    async def get_health_details():
        """Creates a base health dictionary with status = “healthy”.
            Checks Database connection:
                Executes a simple SELECT 1.
                Measures how long it takes (latency).
                Marks database as healthy/unhealthy.
            Checks Cache (Redis or in-memory):
                Uses conversation_cache.ping().
                Measures latency.
                Marks healthy/unhealthy.
            Adds system metrics:
                total requests,
                total conversations so far."""
        from src.database.connection import db_manager
        from src.memory.cache import conversation_cache
        from sqlalchemy import text
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'metrics': {}
        }
        
        # Database check
        try:
            start = time.time()
            with db_manager.get_session() as session:
                session.execute(text("SELECT 1"))
            db_latency = round((time.time() - start) * 1000, 2)
            
            health['services']['database'] = {
                'status': 'healthy',
                'latency_ms': db_latency
            }
        except Exception as e:
            health['services']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Cache check
        try:
            start = time.time()
            conversation_cache.ping()
            cache_latency = round((time.time() - start) * 1000, 2)
            
            health['services']['cache'] = {
                'status': 'healthy' if conversation_cache.use_redis else 'in-memory',
                'latency_ms': cache_latency
            }
        except Exception as e:
            health['services']['cache'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health['status'] = 'degraded'
        
        # Add system metrics
        health['metrics'] = {
            'total_requests': REQUEST_COUNT._metrics,
            'conversation_count': CONVERSATION_COUNT._metrics,
        }
        
        # Add system metrics (simplified to avoid errors)
        # try:
        #     health['metrics'] = {
        #         'total_requests': 'available',
        #         'conversation_count': 'available',
        #     }
        # except Exception as e:
        #     health['metrics'] = {
        #         'error': str(e)
        #     }
        
        return health


# Context logger for conversation tracking
class ConversationLogger:
    """This adds context-based logging for customer support or chatbot interactions.
        Each log includes:
            conversation_id
            customer_id
            custom message (like “User message received”)
        Methods
            info() → for normal logs
            error() → for errors
            warning() → for warnings"""
    
    def __init__(self, conversation_id: str, customer_id: str):
        self.logger = logging.getLogger(__name__)
        self.conversation_id = conversation_id
        self.customer_id = customer_id
    
    def info(self, message: str, **kwargs):
        """Log info with context"""
        self.logger.info(
            message,
            extra={
                'conversation_id': self.conversation_id,
                'customer_id': self.customer_id,
                **kwargs
            }
        )
    
    def error(self, message: str, **kwargs):
        """Log error with context"""
        self.logger.error(
            message,
            extra={
                'conversation_id': self.conversation_id,
                'customer_id': self.customer_id,
                **kwargs
            }
        )
    
    def warning(self, message: str, **kwargs):
        """Log warning with context"""
        self.logger.warning(
            message,
            extra={
                'conversation_id': self.conversation_id,
                'customer_id': self.customer_id,
                **kwargs
            }
        )