"""
🌱 Big Picture: What is this file?
-This file defines background tasks that Celery workers will run.
- Each task is like a recipe → FastAPI (or another service) can say:
    👉 “Hey Celery, please run process_message_async with these inputs”
    and Celery runs it in the background, separate from your main app.
So the goal of this file:
- Define tasks for customer support (message processing, escalation, summaries, etc.).
- Add error handling, retries, and periodic scheduling.
- Allow scaling: tasks can run on multiple workers at the same time.

Overview:
- Defines a base task (CallbackTask) that automatically handles success/failure logging.
Implements multiple tasks:
- process_message_async → Handle customer chat message.
- send_escalation_email → Notify humans if AI escalates.
- generate_conversation_summary → AI-powered summary of conversation.
- update_kb_index → Update knowledge base (e.g., embeddings, search index).
- cleanup_old_conversations → Archive conversations older than 90 days.
Defines periodic tasks: runs KB updates every 6h, cleanup daily.
"""

from celery import Task
from celery_app import celery_app
from typing import Dict, Any, Optional
import time
from datetime import datetime
import os

from src.workflows.conversation_agentGroq import ProductionConversationAgent
from src.memory.production_memory import production_memory


class CallbackTask(Task):
    """Base task with error handling and callbacks"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        print(f"❌ Task {task_id} failed: {exc}")
        # In production, you'd log to monitoring service
    
    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        print(f"✅ Task {task_id} completed successfully")


@celery_app.task(bind=True, base=CallbackTask, name='process_message_async')
def process_message_async(self, customer_id: str, message: str, 
                         conversation_id: Optional[str] = None,
                         customer_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Process customer message asynchronously
    Use this for non-urgent messages or batch processing
    Main task for handling a customer message.
    Calls ProductionConversationAgent (your AI bot).
    If escalation is needed → triggers another Celery task (send_escalation_email).
    Returns response data (conversation ID, AI reply, etc.).
    """
    print(f"🔄 Processing message for customer {customer_id}")
    
    try:
        agent = ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))
        
        result = agent.handle_customer_message(
            customer_id=customer_id,
            message=message,
            conversation_id=conversation_id,
            customer_context=customer_context
        )
        
        # If escalation needed, trigger notification
        if result.get('escalated'):
            send_escalation_email.delay(
                conversation_id=result['conversation_id'],
                customer_id=customer_id,
                priority=result['classification'].priority
            )
        
        return {
            'status': 'success',
            'conversation_id': result['conversation_id'],
            'response': result['response'],
            'escalated': result.get('escalated', False),
            'processing_time_ms': result.get('processing_time_ms', 0)
        }
        
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


@celery_app.task(bind=True, base=CallbackTask, name='send_escalation_email')
def send_escalation_email(self, conversation_id: str, customer_id: str, 
                         priority: str) -> Dict[str, Any]:
    """
    Send escalation notification to human agents
    In production, this would integrate with email service (SendGrid, SES, etc.)

    If AI cannot handle → sends email to human support team.
    Builds email data (to, subject, body).
    In real life → would call SendGrid / SES / SMTP service.
    Has retry logic (try again after 60s, up to 3 times if failed).
    """
    print(f"📧 Sending escalation email for conversation {conversation_id}")
    
    try:
        # Get conversation context
        context = production_memory.get_conversation_context(conversation_id)
        
        # Simulate email sending (replace with actual email service)
        email_data = {
            'to': 'support-team@company.com',
            'subject': f'[{priority.upper()}] Escalated Support Ticket',
            'body': f"""
            A customer support conversation requires human attention.
            
            Conversation ID: {conversation_id}
            Customer ID: {customer_id}
            Priority: {priority.upper()}
            Category: {context.get('category', 'unknown')}
            Duration: {context.get('duration_minutes', 0):.1f} minutes
            
            Please review and respond within appropriate SLA.
            """,
            'timestamp': datetime.now().isoformat()
        }
        
        # In production: send_email_service(email_data)
        print(f"✅ Escalation email sent: {email_data['subject']}")
        
        return {
            'status': 'sent',
            'email_data': email_data,
            'sent_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Failed to send escalation email: {e}")
        # Retry logic
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(bind=True, base=CallbackTask, name='generate_conversation_summary')
def generate_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
    """
    Generate AI summary of conversation for analytics/reporting
    Run this after conversation is resolved
    Runs after conversation ends.
    Stores summary with metadata (message count, resolution time, category).
    Useful for analytics & reports.
    """
    print(f"📊 Generating summary for conversation {conversation_id}")
    
    try:
        from groq import Groq
        
        # Get full conversation
        history = production_memory.get_conversation_history(conversation_id, limit=100)
        context = production_memory.get_conversation_context(conversation_id)
        
        # Build conversation text
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in history
        ])
        
        # Generate summary with AI
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            model="openai/gpt-oss-120",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a concise summary of this customer support conversation. Include: main issue, resolution steps taken, outcome, and any follow-up needed."
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{conversation_text}"
                }
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content
        
        # Store summary (you could save this to database)
        summary_data = {
            'conversation_id': conversation_id,
            'summary': summary,
            'generated_at': datetime.now().isoformat(),
            'message_count': len(history),
            'category': context.get('category'),
            'resolution_time_minutes': context.get('duration_minutes', 0)
        }
        
        print(f"✅ Summary generated: {summary[:100]}...")
        
        return summary_data
        
    except Exception as e:
        print(f"❌ Failed to generate summary: {e}")
        return {'status': 'error', 'error': str(e)}


@celery_app.task(bind=True, base=CallbackTask, name='update_kb_index')
def update_kb_index(self, new_articles: list = None) -> Dict[str, Any]:
    """
    Update knowledge base index
    Run this periodically or when new articles are added
    """
    print("📚 Updating knowledge base index...")
    
    try:
        # In production, this would:
        # - Rebuild search indexes
        # - Update embeddings
        # - Refresh cache
        
        time.sleep(2)  # Simulate processing
        
        print("✅ Knowledge base index updated")
        
        return {
            'status': 'success',
            'updated_at': datetime.now().isoformat(),
            'articles_processed': len(new_articles) if new_articles else 0
        }
        
    except Exception as e:
        print(f"❌ Failed to update KB index: {e}")
        return {'status': 'error', 'error': str(e)}


@celery_app.task(bind=True, base=CallbackTask, name='cleanup_old_conversations')
def cleanup_old_conversations(self, days_old: int = 90) -> Dict[str, Any]:
    """
    Archive old resolved conversations
    Run this as a scheduled task (daily/weekly)
    """
    print(f"🧹 Cleaning up conversations older than {days_old} days...")
    
    try:
        from datetime import timedelta
        from src.database.connection import db_manager
        from src.models.database_models import ConversationDB
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        with db_manager.get_session() as session:
            old_conversations = session.query(ConversationDB).filter(
                ConversationDB.status == 'resolved',
                ConversationDB.resolved_at < cutoff_date
            ).all()
            
            archived_count = len(old_conversations)
            
            # In production: Move to archive storage, update status
            for conv in old_conversations:
                conv.status = 'archived'
            
            print(f"✅ Archived {archived_count} old conversations")
            
            return {
                'status': 'success',
                'archived_count': archived_count,
                'cutoff_date': cutoff_date.isoformat()
            }
            
    except Exception as e:
        print(f"❌ Failed to cleanup conversations: {e}")
        return {'status': 'error', 'error': str(e)}


# Periodic tasks configuration
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Configure periodic background tasks
    Hooks into Celery’s scheduler.
        Adds repeating jobs:
        Run update_kb_index every 6h.
        Run cleanup_old_conversations daily at 2 AM.
    """
    
    # Run KB index update every 6 hours
    sender.add_periodic_task(
        21600.0,  # 6 hours in seconds
        update_kb_index.s(),
        name='update-kb-index-every-6h'
    )
    
    # Run cleanup every day at 2 AM
    sender.add_periodic_task(
        86400.0,  # 24 hours
        cleanup_old_conversations.s(days_old=90),
        name='cleanup-old-conversations-daily'
    )