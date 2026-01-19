"""
Overview:
This file configures and launches Celery for your project.
Think of it as the entry point for background workers.

- Loads environment variables (.env file).
- Creates a Celery app named customer_support.
- Configures task queues, serialization, and worker behavior.
- Tells Celery where to find your task functions (src.workflows.async_tasks).
- Defines task routing so different types of jobs go to different queues.
- Allows running Celery directly from this file (celery -A celery_app worker -l info).
"""

from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery
celery_app = Celery(
    'customer_support',     #Creates a Celery instance named customer_support.
    broker=os.getenv('REDIS_URL'),      # Uses Redis as the message broker.
    backend=os.getenv('REDIS_URL'),
    include=['src.workflows.async_tasks']  # Where our tasks are defined
)

# Celery Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    worker_prefetch_multiplier=4,   # Controls worker efficiency (prefetch_multiplier=4 → worker grabs 4 tasks at a time).
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing (optional but good practice)
celery_app.conf.task_routes = {
    'src.workflows.async_tasks.process_message_async': {'queue': 'messages'},
    'src.workflows.async_tasks.send_escalation_email': {'queue': 'notifications'},
    'src.workflows.async_tasks.generate_conversation_summary': {'queue': 'analytics'},
    'src.workflows.async_tasks.update_kb_index': {'queue': 'maintenance'},
}

if __name__ == '__main__':
    celery_app.start()