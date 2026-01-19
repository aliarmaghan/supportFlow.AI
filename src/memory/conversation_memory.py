"""OVERVIEW:
This file defines how conversations are stored, updated, and retrieved in memory while your application is running.
Think of this file as:
    🧠 The brain’s short-term memory for conversations
It:
- Stores conversations in Python memory (not database)
- Keeps track of:
    - Messages (user + assistant)
    - Conversation status
    - Classification results
    - Articles used
    - Escalation & resolution state
Formats conversation history so it can be sent to LLMs (like OpenAI)
📌 Important note for beginners
- This is a development / prototype memory system.
- In production, this would usually be replaced by:
    - A database (Postgres, MongoDB)
    - Or Redis-backed persistent memory"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid

@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ConversationContext:
    conversation_id: str
    customer_id: str
    messages: List[Message] = field(default_factory=list)
    classification_history: List[Dict] = field(default_factory=list)
    articles_referenced: List[str] = field(default_factory=list)
    escalated: bool = False
    resolution_status: str = "open"  # open, in_progress, resolved, escalated
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

class ConversationMemory:
    def __init__(self):
        # In production, this would be a database
        self.conversations: Dict[str, ConversationContext] = {}
    
    def start_conversation(self, customer_id: str, initial_message: str) -> str:
        """Start a new conversation and return conversation_id"""
        conversation_id = str(uuid.uuid4())
        
        context = ConversationContext(
            conversation_id=conversation_id,
            customer_id=customer_id
        )
        
        # Add initial user message
        context.messages.append(Message(
            role="user",
            content=initial_message
        ))
        
        self.conversations[conversation_id] = context
        return conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to existing conversation"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.conversations[conversation_id].messages.append(message)
        self.conversations[conversation_id].updated_at = datetime.now()
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get conversation history in OpenAI format"""
        if conversation_id not in self.conversations:
            return []
        
        context = self.conversations[conversation_id]
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in context.messages
        ]
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation summary for context"""
        if conversation_id not in self.conversations:
            return {}
        
        context = self.conversations[conversation_id]
        return {
            "conversation_id": conversation_id,
            "customer_id": context.customer_id,
            "message_count": len(context.messages),
            "classification_history": context.classification_history,
            "articles_referenced": context.articles_referenced,
            "escalated": context.escalated,
            "resolution_status": context.resolution_status,
            "duration_minutes": (context.updated_at - context.created_at).total_seconds() / 60
        }
    
    def update_classification(self, conversation_id: str, classification: Dict):
        """Store classification result in memory"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].classification_history.append({
                "timestamp": datetime.now().isoformat(),
                "classification": classification
            })
    
    def add_referenced_articles(self, conversation_id: str, article_ids: List[str]):
        """Track which articles were used"""
        if conversation_id in self.conversations:
            self.conversations[conversation_id].articles_referenced.extend(article_ids)