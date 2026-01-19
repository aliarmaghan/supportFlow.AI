"""
This file defines a ProductionConversationAgent class.
It:
    1.Receives a customer message.
    2.Uses memory (DB + cache) to get context.
    3.Uses a classifier to label and search knowledge base
    4.Generates a contextual AI response (with OpenAI).
    5.Stores everything back into memory
    6.Decides if escalation to a human is needed
    7.Provides customer insights (history, categories, escalation rate)
At the bottom, it creates a global instance: production_agent.
"""

import openai
from typing import Dict, Any, List, Optional
import time
from datetime import datetime

from src.models.ticket_models import TicketClassification
from src.tools.knowledge_base import KnowledgeBaseSearch, KnowledgeArticle
from src.memory.production_memory import production_memory
from src.workflows.ticket_classifier import TicketClassifier


class ProductionConversationAgent:
    def __init__(self, api_key: str):
        """
        Initializes:
            OpenAI client (for response generation)
            TicketClassifier (for classification + KB search)
            Memory (conversation storage layer)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.classifier = TicketClassifier(api_key=api_key)
        self.memory = production_memory
    
    def handle_customer_message(self, 
                               customer_id: str, 
                               message: str,
                               conversation_id: Optional[str] = None,
                               customer_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle customer message with production memory system.
        This is the main workflow (entry point).
        Steps inside:
            1.Get or start a conversation
            2.Fetch conversation context + history from memory
            3.Classify message + search KB (via TicketClassifier)
            4.Generate a contextual response (using _generate_contextual_response)
            5.Store interaction (both user + agent messages) in memory
            6.Update status if escalation needed
            7.Return response + metadata
        If something fails → return fallback response (apologize + escalate).
        """
        start_time = time.time()
        
        try:
            # Step 1: Get or create conversation
            if conversation_id is None:
                conversation_id = self.memory.start_or_get_conversation(
                    customer_id=customer_id,
                    initial_message=message,
                    customer_context=customer_context
                )
                is_new_conversation = True
            else:
                is_new_conversation = False
            
            # Step 2: Get conversation context from production memory
            conversation_context = self.memory.get_conversation_context(conversation_id)
            conversation_history = self.memory.get_conversation_history(conversation_id, limit=20)
            
            # Step 3: Classify message and search knowledge base
            classification_result = self.classifier.classify_and_search(message, customer_context)
            classification = classification_result["classification"]
            
            # Step 4: Generate contextual response
            agent_response = self._generate_contextual_response(
                current_message=message,
                classification=classification,
                relevant_articles=classification_result["relevant_articles"],
                conversation_history=conversation_history,
                conversation_context=conversation_context,
                is_new_conversation=is_new_conversation
            )
            
            # Step 5: Store complete interaction in production memory
            processing_time = int((time.time() - start_time) * 1000)
            
            interaction_metadata = {
                'classification': classification.model_dump(),
                'articles_used': [
                    {
                        'id': article.id,
                        'title': article.title,
                        'relevance_score': 1
                    } 
                    for article in classification_result["relevant_articles"]
                ],
                'processing_time_ms': processing_time,
                'tools_used': ['classification', 'knowledge_base_search']
            }
            
            if not is_new_conversation:
                self.memory.add_interaction(
                    conversation_id=conversation_id,
                    user_message=message,
                    agent_response=agent_response,
                    metadata=interaction_metadata
                )
            else:
                # For new conversations, just add the agent response
                self.memory.add_interaction(
                    conversation_id=conversation_id,
                    user_message="",  # Already added in start_or_get_conversation
                    agent_response=agent_response,
                    metadata=interaction_metadata
                )
            
            # Step 6: Check if escalation is needed
            if classification.requires_human_escalation:
                self.memory.update_conversation_status(conversation_id, 'escalated')
            
            return {
                "conversation_id": conversation_id,
                "classification": classification,
                "response": agent_response,
                "relevant_articles": classification_result["relevant_articles"],
                "processing_time_ms": processing_time,
                "escalated": classification.requires_human_escalation,
                "is_new_conversation": is_new_conversation,
                "conversation_context": self.memory.get_conversation_context(conversation_id)
            }
            
        except Exception as e:
            # Log error and return fallback response
            print(f"Error processing message: {e}")
            
            fallback_response = {
                "conversation_id": conversation_id or "error",
                "response": "I apologize, but I'm experiencing technical difficulties. A human agent will assist you shortly.",
                "error": str(e),
                "escalated": True
            }
            
            return fallback_response
    
    def _generate_contextual_response(self, 
                                    current_message: str,
                                    classification: TicketClassification,
                                    relevant_articles: List[KnowledgeArticle],
                                    conversation_history: List[Dict],
                                    conversation_context: Dict,
                                    is_new_conversation: bool) -> str:
        """Generate response using full production context"""
        
        # Build context from articles
        articles_context = ""
        if relevant_articles:
            articles_context = "Available knowledge base information:\n"
            for article in relevant_articles:
                articles_context += f"- {article.title}: {article.content}\n"
        
        # Build conversation context
        context_summary = ""
        if not is_new_conversation and conversation_context:
            context_summary = f"""
            Conversation Context:
            - This is message #{conversation_context.get('message_count', 0) + 1} in this conversation
            - Current status: {conversation_context.get('status', 'unknown')}
            - Previous category: {conversation_context.get('category', 'none')}
            - Duration: {conversation_context.get('duration_minutes', 0):.1f} minutes
            - Customer plan: {conversation_context.get('customer_context', {}).get('plan', 'unknown')}
            """
        
        # Build messages for API
        messages = [
            {
                "role": "system",
                "content": f"""You are a professional SaaS support agent with access to conversation history and knowledge base.

                Current Classification:
                - Category: {classification.category}
                - Priority: {classification.priority}
                - Sentiment: {classification.sentiment}
                - Requires Escalation: {classification.requires_human_escalation}

                {context_summary}

                {articles_context}

                Guidelines:
                - Be professional, empathetic, and solution-focused
                - Reference conversation history when relevant
                - If escalation is required, explain what happens next
                - Provide specific, actionable steps when possible
                - Don't repeat information already discussed in this conversation
                - If you see patterns from previous messages, acknowledge them"""
            }
        ]
        
        # Add recent conversation history
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            if msg["role"] in ["user", "assistant"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def get_customer_insights(self, customer_id: str) -> Dict[str, Any]:
        """Get insights about customer's interaction history"""
        customer_history = self.memory.get_customer_conversation_history(customer_id)
        
        return {
            "total_conversations": len(customer_history),
            "recent_conversations": customer_history,
            "common_categories": self._analyze_common_categories(customer_history),
            "escalation_rate": self._calculate_escalation_rate(customer_history)
        }
    
    def _analyze_common_categories(self, conversations: List[Dict]) -> Dict[str, int]:
        """Analyze most common issue categories for this customer"""
        categories = {}
        for conv in conversations:
            category = conv.get('category')
            if category:
                categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _calculate_escalation_rate(self, conversations: List[Dict]) -> float:
        """Calculate what percentage of conversations get escalated"""
        if not conversations:
            return 0.0
        
        escalated = sum(1 for conv in conversations if conv.get('status') == 'escalated')
        return (escalated / len(conversations)) * 100

# Global instance
production_agent = ProductionConversationAgent