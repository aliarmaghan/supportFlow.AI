"""OVERVIEW:
This file defines structured data models for classifying customer support tickets using Pydantic and Enums. 
Its main purpose is to create a clear, validated, and standardized schema for how an AI system (or backend service) 
should represent the analysis of a support request—including its priority, category, sentiment, escalation needs, and 
suggested knowledge-base articles.

In an agentic or AI-driven customer support system (like the one you’re building), this file typically sits at the 
boundary between LLM outputs and backend logic. It ensures that whatever the AI generates is well-typed, predictable, 
and safe to store or act upon.

🧠 Why This Design Is Strong (Architecturally)
- LLM-safe: Prevents hallucinated fields or invalid values
- Production-ready: Works cleanly with FastAPI, databases, and agents
- Explainable: Every field has semantic meaning for humans
- Extensible: Easy to add new categories, priorities, or metadata later
This file is a schema-layer backbone for an AI-powered support system—bridging natural language understanding with 
deterministic backend behavior.
If you want, next I can:
- Map this schema to your SQLAlchemy models
- Show how an LLM should be prompted to output this exact structure
- Explain where this fits in an agentic workflow (classifier → router → resolver)
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, List
from datetime import datetime

class Priority(str, Enum):
    """
    This class defines the urgency levels of a support ticket.
    - By inheriting from both str and Enum, it ensures:
        - Values are restricted to a fixed set (low, medium, high, urgent)
        - Values serialize cleanly as strings (important for APIs, JSON, and databases)
    - This prevents invalid priorities (like "very_high" or "asap") from entering your system and makes downstream 
    automation (routing, SLA handling, escalation rules) reliable."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"

class Category(str, Enum):
    """This class standardizes what type of problem the customer is facing.
    Each value represents a business-recognized support category such as billing issues, technical problems, bug reports, 
    or feature requests. Using an enum here ensures:
        Consistent categorization across AI predictions, database storage, and analytics
        Easy filtering and reporting (e.g., “show all billing-related tickets”)
        Cleaner training data if you later fine-tune or evaluate models
    This enum reflects domain knowledge encoded directly into your system.
    """
    BILLING = "billing"
    TECHNICAL = "technical"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT_MANAGEMENT = "account_management"
    BUG_REPORT = "bug_report"
    INTEGRATION = "integration"

class TicketClassification(BaseModel):
    """
    This is the core schema of the file. It represents the full structured output of a ticket-classification step, 
    typically produced by an LLM or classification agent.
    Key responsibilities of this class:
    - Validates AI output against strict types (enums, lists, booleans)
    - Acts as a contract between AI agents and backend services
    - Makes responses self-documented using Field(description=...)
    What it captures:
    - Category & Priority → Operational triage
    - Summary → Human-readable explanation for agents or logs
    - Escalation flag → Enables automated handoff to human support
    - Knowledge base suggestions → Powers RAG, FAQ linking, or auto-responses
    - Sentiment → Useful for CX analytics and escalation logic
    - Estimated resolution time → Sets customer expectations or SLAs
    In practice, this model is ideal for:
    - Parsing LLM JSON output
    - Storing structured classifications in the database
    - Driving workflow decisions (auto-resolve vs escalate)
    """
    category: Category = Field(description="Primary category of the support request")
    priority: Priority = Field(description="Urgency level based on business impact")
    summary: str = Field(description="Brief summary of the issue in 1-2 sentences")
    requires_human_escalation: bool = Field(description="Whether this needs immediate human attention")
    suggested_knowledge_base_articles: List[str] = Field(description="Relevant FAQ IDs or article titles")
    sentiment: str = Field(description="Customer emotion: positive, neutral, frustrated, angry")
    estimated_resolution_time: str = Field(description="Estimated time to resolve: immediate, 24h, 48h, 1week")