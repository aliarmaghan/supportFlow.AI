"""
This file defines a ProductionConversationMemory class that acts as the brain for storing, retrieving, and managing customer 
support conversations.
It connects:
1. Database (PostgreSQL via SQLAlchemy) → for permanent storage
2. Cache (Redis) → for fast retrieval of recent context
3. Business logic → handling messages, classifications, knowledge base usage, and conversation status

So the main goal:
👉 Keep track of every customer conversation, update it with AI + human responses, store metadata (like urgency, category, 
escalation), and make it fast by caching.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from src.database.connection import db_manager
from src.memory.cache import conversation_cache
from src.models.database_models import ConversationDB, MessageDB, KnowledgeBaseUsageDB
from src.models.ticket_models import TicketClassification


class ProductionConversationMemory:
    
    def __init__(self):
        """Sets up cache (Redis) and database manager (Postgres).These will be used in all other methods."""
        self.cache = conversation_cache
        self.db_manager = db_manager
    
    def start_or_get_conversation(self, customer_id: str, initial_message: str, 
                                customer_context: Dict[str, Any] = None) -> str:
        """
        Start new conversation or get existing active one for customer.
        If a customer already has an active conversation (open/in progress in last 4 hours), continue it.
        Otherwise, start a new conversation.
        Adds the first user message and caches it.
        """
        # Check for recent active conversation (within last 4 hours)
        with self.db_manager.get_session() as session:
            recent_conversation = session.query(ConversationDB).filter(
                and_(
                    ConversationDB.customer_id == customer_id,
                    ConversationDB.status.in_(['open', 'in_progress']),
                    ConversationDB.updated_at > datetime.now() - timedelta(hours=4)
                )
            ).order_by(desc(ConversationDB.updated_at)).first()
            
            if recent_conversation:
                # Continue existing conversation
                conversation_id = recent_conversation.conversation_id
                self._add_message(conversation_id, "user", initial_message, session)
                return conversation_id
            
            # Create new conversation
            new_conversation = ConversationDB(
                customer_id=customer_id,
                customer_context=customer_context or {},
                status='open',
                message_count=1
            )
            
            session.add(new_conversation)
            session.flush()  # Get the ID without committing yet
            
            conversation_id = new_conversation.conversation_id
            
            # Add initial message
            self._add_message(conversation_id, "user", initial_message, session)
            
            # Cache the conversation
            self._cache_conversation(new_conversation)
            
            return conversation_id
    
    def add_interaction(self, conversation_id: str, user_message: str, 
                       agent_response: str, metadata: Dict[str, Any] = None):
        """
        Add a complete user-agent interaction to the conversation
        Adds a user message + AI assistant response into the conversation.
        Updates conversation stats:
            message_count
            classification (category, priority, escalation flags)
            articles_used (knowledge base usage tracking)
        Updates both DB + Cache.
        """
        with self.db_manager.get_session() as session:
            # Add user message (if not already added)
            user_msg = self._add_message(conversation_id, "user", user_message, session)
            
            # Add agent response
            agent_msg = self._add_message(conversation_id, "assistant", agent_response, session, metadata)
            
            # Update conversation metadata
            conversation = session.query(ConversationDB).filter_by(
                conversation_id=conversation_id
            ).first()
            
            if conversation:
                conversation.message_count += 2  # User + assistant
                conversation.updated_at = datetime.now()
                
                # Update classification history if provided
                if metadata and 'classification' in metadata:
                    classification = metadata['classification']
                    if not conversation.classification_history:
                        conversation.classification_history = []
                    
                    conversation.classification_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'classification': classification
                    })
                    
                    # Update conversation-level fields
                    if isinstance(classification, dict):
                        conversation.category = classification.get('category')
                        conversation.priority = classification.get('priority')
                        conversation.escalated = classification.get('requires_human_escalation', False)
                
                # Track knowledge base usage
                if metadata and 'articles_used' in metadata:
                    self._track_kb_usage(conversation_id, metadata['articles_used'], session)
                
                # Cache updated conversation
                self._cache_conversation(conversation)
    
    def get_conversation_history(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get conversation history with caching
        Fetches the last N messages from cache (fast).
        If cache misses → fetch from DB, then push into cache.
        """
        # Try cache first for recent messages
        cached_messages = self.cache.get_recent_messages(conversation_id, limit)
        if cached_messages:
            return cached_messages
        
        # Fall back to database
        with self.db_manager.get_session() as session:
            messages = session.query(MessageDB).filter_by(
                conversation_id=conversation_id
            ).order_by(MessageDB.created_at).limit(limit).all()
            
            history = []
            for msg in messages:
                history.append({
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat(),
                    'metadata': {
                        'classification_result': msg.classification_result,
                        'tools_used': msg.tools_used,
                        'processing_time_ms': msg.processing_time_ms
                    }
                })
            
            # Cache for next time
            if history:
                for msg in history:
                    self.cache.add_message(conversation_id, msg)
            
            return history
    
    def get_conversation_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full conversation context including metadata
        Retrieves metadata about the conversation (status, priority, category, history, etc).
        First check cache, then DB.
        Used when AI needs context beyond just messages.
        """
        # Check cache first
        cached_context = self.cache.get_conversation(conversation_id)
        if cached_context:
            return cached_context
        
        # Get from database
        with self.db_manager.get_session() as session:
            conversation = session.query(ConversationDB).filter_by(
                conversation_id=conversation_id
            ).first()
            
            if not conversation:
                return None
            print("=="*50)
            context = {
                'conversation_id': conversation.conversation_id,
                'customer_id': conversation.customer_id,
                'status': conversation.status,
                'priority': conversation.priority,
                'category': conversation.category,
                'message_count': conversation.message_count,
                'escalated': conversation.escalated,
                'customer_context': conversation.customer_context,
                'classification_history': conversation.classification_history or [],
                'articles_referenced': conversation.articles_referenced or [],
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat(),
                'duration_minutes': (conversation.updated_at - conversation.created_at).total_seconds() / 60
            }
            
            # Cache it
            self.cache.set_conversation(conversation_id, context)
            
            return context
    
    def update_conversation_status(self, conversation_id: str, status: str, 
                                 human_agent_id: str = None):
        """
        Update conversation status (open, in_progress, resolved, escalated)
        Changes conversation state:
            open
            in_progress
            resolved (also records resolved_at)
            escalated (assigns to human agent)
        Invalidates cache so new state is consistent
        """
        with self.db_manager.get_session() as session:
            conversation = session.query(ConversationDB).filter_by(
                conversation_id=conversation_id
            ).first()
            
            if conversation:
                conversation.status = status
                conversation.updated_at = datetime.now()
                
                if status == 'resolved':
                    conversation.resolved_at = datetime.now()
                
                if status == 'escalated':
                    conversation.escalated = True
                    conversation.human_agent_id = human_agent_id
                
                # Invalidate cache
                self.cache.invalidate_conversation(conversation_id)
    
    def get_customer_conversation_history(self, customer_id: str, 
                                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get customer's recent conversations for context.
        Returns a summary list of past conversations for a given customer (last N).
        Useful for long-term memory or customer support dashboards.
        """
        with self.db_manager.get_session() as session:
            conversations = session.query(ConversationDB).filter_by(
                customer_id=customer_id
            ).order_by(desc(ConversationDB.created_at)).limit(limit).all()
            
            return [
                {
                    'conversation_id': conv.conversation_id,
                    'status': conv.status,
                    'category': conv.category,
                    'priority': conv.priority,
                    'message_count': conv.message_count,
                    'created_at': conv.created_at.isoformat(),
                    'resolved_at': conv.resolved_at.isoformat() if conv.resolved_at else None
                }
                for conv in conversations
            ]
    
    def _add_message(self, conversation_id: str, role: str, content: str, 
                    session: Session, metadata: Dict[str, Any] = None) -> MessageDB:
        """Internal method to add message to database
            Actually writes a message (user/assistant) into DB.
            Adds metadata like classification, tools used, processing time.
            Pushes the message into Redis cache too.
        """
        message = MessageDB(
            conversation_id=conversation_id,
            role=role,
            content=content,
            classification_result=metadata.get('classification') if metadata else None,
            tools_used=metadata.get('tools_used', []) if metadata else [],
            processing_time_ms=metadata.get('processing_time_ms') if metadata else None
        )
        
        session.add(message)
        session.flush()
        
        # Add to cache
        self.cache.add_message(conversation_id, {
            'role': role,
            'content': content,
            'timestamp': message.created_at.isoformat(),
            'metadata': metadata or {}
        })
        
        return message
    
    def _cache_conversation(self, conversation: ConversationDB):
        """Cache conversation object
            Takes a conversation object and stores a lightweight context snapshot in Redis.
            So that next time we don’t have to hit DB.
        """
        context = {
            'conversation_id': conversation.conversation_id,
            'customer_id': conversation.customer_id,
            'status': conversation.status,
            'priority': conversation.priority,
            'category': conversation.category,
            'message_count': conversation.message_count,
            'escalated': conversation.escalated,
            'customer_context': conversation.customer_context,
            'classification_history': conversation.classification_history or [],
            'articles_referenced': conversation.articles_referenced or []
        }
        self.cache.set_conversation(conversation.conversation_id, context)
    
    def _track_kb_usage(self, conversation_id: str, articles: List[Dict], session: Session):
        """Track knowledge base article usage.
            Records which knowledge base articles were used in this conversation.
            Helps later for analytics: e.g. “Which KB articles solved the most issues?”
        """
        for article in articles:
            usage = KnowledgeBaseUsageDB(
                conversation_id=conversation_id,
                article_id=article.get('id', 'unknown'),
                article_title=article.get('title', ''),
                relevance_score=article.get('relevance_score', 0)
            )
            session.add(usage)

# Global instance
"""Creates a global instance of the memory manager class so it can be reused everywhere."""
production_memory = ProductionConversationMemory()