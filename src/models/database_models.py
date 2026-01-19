"""OVERVIEW:
This file defines how your data is stored permanently in the database using SQLAlchemy ORM.
Think of it as:
🗄️ Blueprints for database tables (Conversations, Messages, and Knowledge-Base usage)
Instead of writing raw SQL like:
You write Python classes, and SQLAlchemy:
- Converts them into tables
- Handles inserts, updates, deletes
- Maintains relationships between tables
📌 This is your long-term memory, unlike:
- ConversationMemory → temporary (RAM)
- cache.py → fast short-term cache
"""

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


"""Benefits of using a schema (like support)
Organization: Keeps all customer-support-related tables together.
Example: support.conversations vs. hr.employees.

Security: You can give permissions per schema.
Example: Analysts only get read access to support, but not to finance.

Avoid collisions: You could have public.users and support.users — same table name in different schemas.
"""

# ---------------------------
# Conversations Table
# ---------------------------
class ConversationDB(Base):
    """ This Table represent a customer support conversation """
    __tablename__ = 'conversations'
    __table_args__ = {'schema': 'support'}  # keep schema

    # Primary identifiers
    conversation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, nullable=False, index=True)

    # Conversation metadata
    status = Column(String, default='open', index=True)     # open, in_progress, resolved, escalated
    priority = Column(String, index=True)                   # low, medium, high, urgent
    category = Column(String, index=True)                   # billing, technical, etc.

    # Tracking fields
    message_count = Column(Integer, default=0)
    escalated = Column(Boolean, default=False)
    human_agent_id = Column(String, nullable=True)

    # JSON fields
    customer_context = Column(JSON)  # Plan, account info, etc.
    classification_history = Column(JSON, default=list)
    articles_referenced = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    messages = relationship("MessageDB", back_populates="conversation", cascade="all, delete-orphan")
    kb_usages = relationship("KnowledgeBaseUsageDB", back_populates="conversation", cascade="all, delete-orphan")


# ---------------------------
# Messages Table
# ---------------------------
class MessageDB(Base):
    """ This Table represent individual messages in a conversation """
    __tablename__ = 'messages'
    __table_args__ = {'schema': 'support'}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String,
        ForeignKey("support.conversations.conversation_id"),  # explicit FK
        nullable=False,
        index=True
    )

    # Message content
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Processing metadata
    classification_result = Column(JSON, nullable=True)
    tools_used = Column(JSON, default=list)
    processing_time_ms = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationship back to conversation
    conversation = relationship("ConversationDB", back_populates="messages")


# ---------------------------
# Knowledge Base Usage Table
# ---------------------------
class KnowledgeBaseUsageDB(Base):
    """ This Table represent which knowledge-base articles were used and how useful they were"""
    __tablename__ = 'knowledge_base_usage'
    __table_args__ = {'schema': 'support'}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String,
        ForeignKey("support.conversations.conversation_id"),  # explicit FK
        nullable=False,
        index=True
    )

    article_id = Column(String, nullable=False)
    article_title = Column(String)
    relevance_score = Column(Integer)          # How relevant was this article?
    was_helpful = Column(Boolean, nullable=True)  # Customer feedback

    created_at = Column(DateTime, default=func.now())

    # Relationship back to conversation
    conversation = relationship("ConversationDB", back_populates="kb_usages")
