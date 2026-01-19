""" OVERVIEW:
This main.py file is the entry point of your Customer Support AI Agent API.
- It uses FastAPI to create a REST API server.
- It defines endpoints where:
    - Customers can send messages and get AI responses.
    - The system can process messages synchronously (real-time) or asynchronously (background).
    - You can check conversation history, escalate to a human agent, resolve conversations, and view analytics.
- It integrates with:
    - OpenAI LLM (via ProductionConversationAgent) for AI responses.
    - Database & Redis for storing and caching conversations.
    - Celery for async/background tasks (summary generation, notifications).
It also provides health checks and error handling.

Think of this file as the control room that wires everything together.
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from sqlalchemy import text, func, and_, desc
from dotenv import load_dotenv

from celery_app import celery_app
# from src.workflows.conversation_agent import ProductionConversationAgent      Use this for open ai api
from src.workflows.conversation_agentGroq import ProductionConversationAgent
from src.workflows.async_tasks import process_message_async, generate_conversation_summary
from src.memory.production_memory import production_memory

from src.api.security import (
    SecurityManager, APIKeyAuth, get_current_user, 
    verify_api_key, rate_limiter
)
from src.api.monitoring import (
    setup_logging, MonitoringMiddleware, HealthCheck,
    ConversationLogger, REQUEST_COUNT, CONVERSATION_COUNT,
    MESSAGE_COUNT, ESCALATION_COUNT, generate_latest, CONTENT_TYPE_LATEST
)

load_dotenv()

# Setup logging
logger = setup_logging()

# Initialize FastAPI
"""Setup Section
app = FastAPI(...) → Starts the API with title, description, version.
CORS Middleware → Allows external frontend apps (React, Streamlit, etc.) to call this API.
"""
app = FastAPI(
    title="Customer Support AI Agent API",
    description="Production-ready AI-powered customer support system with async processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models for API
"""🔹 Data Models (Pydantic classes)
These define the shape of data coming in/out of the API:
- CustomerContext → Info about customer (plan, account age, previous tickets).
- MessageRequest → What a customer sends (customer_id, message, conversation_id, async?).
- MessageResponse → What the AI replies with (conversation_id, response, classification, escalated, model info, etc.).
- AsyncMessageResponse → If async mode is used, returns a task_id so you can check later.
- ConversationHistoryResponse → Returns full history of a conversation.
- CustomerInsightsResponse → Returns insights for a customer (common issues, escalation rate, etc.).
"""

class CustomerContext(BaseModel):
    plan: Optional[str] = "Free"
    account_age_months: Optional[int] = 0
    previous_tickets: Optional[int] = 0

class MessageRequest(BaseModel):
    customer_id: str = Field(..., description="Unique customer identifier")
    message: str = Field(..., min_length=1, description="Customer message")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    customer_context: Optional[CustomerContext] = None
    async_processing: bool = Field(False, description="Process message asynchronously")

class MessageResponse(BaseModel):
    conversation_id: str
    response: str
    classification: Dict[str, Any]
    escalated: bool
    processing_time_ms: int
    is_new_conversation: bool
    model_info: Dict[str, Any]

class AsyncMessageResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    customer_id: str
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class CustomerInsightsResponse(BaseModel):
    customer_id: str
    total_conversations: int
    common_categories: Dict[str, int]
    escalation_rate: float
    recent_conversations: List[Dict[str, Any]]

# Authentication Endpoints
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@app.post("/api/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def login(request: LoginRequest):
    """
    Get access token (JWT) for API access
    In production: verify against database
    """
    # Demo credentials (in production: check database)
    if request.username == "demo" and request.password == "demo123":
        token = SecurityManager.create_access_token(
            data={"sub": request.username, "role": "user"}
        )
        return TokenResponse(access_token=token)
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


# Metrics Endpoint (Prometheus)
@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Enhanced Health Check
@app.get("/health/detailed", tags=["Health"])
async def detailed_health():
    """Detailed health check with metrics"""
    return await HealthCheck.get_health_details()


# Dependency: Get Agent Instance
"""🔹 Helper Dependency
get_agent() → Returns an instance of the AI agent (ProductionConversationAgent) with Groq API key.
    → Used with Depends() in endpoints so you don’t have to re-initialize the agent each time.
"""
def get_agent() -> ProductionConversationAgent:
    """Dependency to get agent instance"""
    return ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))


# Health Check Endpoints
"""🔹 Health Check:
- root() → Returns API basic info.
- health_check() → Verifies if database, Redis, and AI model are working.
"""
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API info"""
    return {
        "service": "Customer Support AI Agent",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint with proper error handling"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {}
    }
    
    # Check Database
    try:
        from src.database.connection import db_manager
        from sqlalchemy import text
        
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()
        
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis/Cache
    try:
        from src.memory.cache import conversation_cache
        
        # Use the ping method
        conversation_cache.ping()
        
        if conversation_cache.use_redis:
            health_status["services"]["redis"] = "connected"
        else:
            health_status["services"]["redis"] = "in-memory (development mode)"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check AI Model availability
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            health_status["services"]["ai_model"] = "groq-llama-3.1-70b (configured)"
        else:
            health_status["services"]["ai_model"] = "not configured"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["ai_model"] = f"error: {str(e)}"
    
    # Return appropriate status code
    if health_status["status"] == "healthy":
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)

# Conversation Endpoints
@app.post("/api/conversations/message", 
          response_model=MessageResponse,
          tags=["Conversations"],
          status_code=status.HTTP_200_OK)
async def send_message(
    request: MessageRequest,
    background_tasks: BackgroundTasks,
    agent: ProductionConversationAgent = Depends(get_agent),
    auth: Dict[str, Any] = Depends(verify_api_key)  # Add API key auth

):
    """
    Send a message and get instant AI response (synchronous processing)
    Requires API key authentication
        - Customer sends a message → Agent replies immediately.
        - If conversation is resolved, schedules a summary task in the background.
    """

    # Rate limiting
    if not rate_limiter.check_rate_limit(request.customer_id, max_requests=100, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:

        # Create conversation logger
        conv_logger = ConversationLogger(
            conversation_id=request.conversation_id or "new",
            customer_id=request.customer_id
        )
        conv_logger.info(f"Processing message from {request.customer_id}")

        result = agent.handle_customer_message(
            customer_id=request.customer_id,
            message=request.message,
            conversation_id=request.conversation_id,
            customer_context=request.customer_context.model_dump() if request.customer_context else None
        )
        
        # Update metrics
        MESSAGE_COUNT.labels(type='user').inc()
        MESSAGE_COUNT.labels(type='assistant').inc()

        if result['is_new_conversation']:
            CONVERSATION_COUNT.labels(status='created').inc()
        
        if result['escalated']:
            ESCALATION_COUNT.labels(
                priority=result['classification'].priority
            ).inc()
        
        # Log completion
        conv_logger.info(
            f"Message processed successfully",
            duration_ms=result['processing_time_ms'],
            escalated=result['escalated']
        )

        # If resolved, generate summary in background
        if result['conversation_context'].get('status') == 'resolved':
            background_tasks.add_task(
                generate_conversation_summary.delay,
                result['conversation_id']
            )
        
        return MessageResponse(
            conversation_id=result['conversation_id'],
            response=result['response'],
            classification=result['classification'].model_dump(),
            escalated=result['escalated'],
            processing_time_ms=result['processing_time_ms'],
            is_new_conversation=result['is_new_conversation'],
            model_info=result['model_info']
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.post("/api/conversations/message/async",
          response_model=AsyncMessageResponse,
          tags=["Conversations"],
          status_code=status.HTTP_202_ACCEPTED)
async def send_message_async(request: MessageRequest):
    """
    Send a message for asynchronous processing (non-urgent)
    Returns task_id to check status later
    send_message_async() → Same as above but runs in async/background.
        - Customer gets a task_id to check later instead of waiting.
    """
    try:
        task = process_message_async.delay(
            customer_id=request.customer_id,
            message=request.message,
            conversation_id=request.conversation_id,
            customer_context=request.customer_context.model_dump() if request.customer_context else None
        )
        
        return AsyncMessageResponse(
            task_id=task.id,
            status="processing",
            message="Message queued for processing. Use task_id to check status."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error queuing message: {str(e)}")


@app.get("/api/tasks/{task_id}",
         tags=["Conversations"])
async def get_task_status(task_id: str):
    """
    Check if async task is still pending, processing, success, or failed.
    """
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=celery_app)
    
    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'status': 'pending',
            'message': 'Task is waiting to be processed'
        }
    elif task.state == 'STARTED':
        response = {
            'task_id': task_id,
            'status': 'processing',
            'message': 'Task is currently being processed'
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'status': 'completed',
            'result': task.result
        }
    elif task.state == 'FAILURE':
        response = {
            'task_id': task_id,
            'status': 'failed',
            'error': str(task.info)
        }
    else:
        response = {
            'task_id': task_id,
            'status': task.state
        }
    
    return response


@app.get("/api/conversations/{conversation_id}",
         response_model=ConversationHistoryResponse,
         tags=["Conversations"])
async def get_conversation(conversation_id: str):
    """
    Fetch full history + metadata (status, category, priority, etc.).
    """
    try:
        context = production_memory.get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        history = production_memory.get_conversation_history(conversation_id, limit=100)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            customer_id=context['customer_id'],
            messages=history,
            metadata={
                'status': context.get('status'),
                'category': context.get('category'),
                'priority': context.get('priority'),
                'escalated': context.get('escalated'),
                'message_count': context.get('message_count'),
                'duration_minutes': context.get('duration_minutes'),
                'created_at': context.get('created_at'),
                'updated_at': context.get('updated_at')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


@app.post("/api/conversations/{conversation_id}/escalate",
          tags=["Conversations"])
async def escalate_conversation(conversation_id: str, background_tasks: BackgroundTasks):
    """
    Mark a conversation as escalated to a human. Sends email notification in background.
    """
    try:
        context = production_memory.get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update status
        production_memory.update_conversation_status(conversation_id, 'escalated')
        
        # Send notification in background
        from src.workflows.async_tasks import send_escalation_email
        background_tasks.add_task(
            send_escalation_email.delay,
            conversation_id=conversation_id,
            customer_id=context['customer_id'],
            priority=context.get('priority', 'medium')
        )
        
        return {
            'conversation_id': conversation_id,
            'status': 'escalated',
            'message': 'Conversation escalated to human agent'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error escalating conversation: {str(e)}")


@app.post("/api/conversations/{conversation_id}/resolve",
          tags=["Conversations"])
async def resolve_conversation(conversation_id: str, background_tasks: BackgroundTasks):
    """
    Mark conversation as resolved. Schedules summary generation.
    """
    try:
        context = production_memory.get_conversation_context(conversation_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update status
        production_memory.update_conversation_status(conversation_id, 'resolved')
        
        # Generate summary in background
        background_tasks.add_task(
            generate_conversation_summary.delay,
            conversation_id
        )
        
        return {
            'conversation_id': conversation_id,
            'status': 'resolved',
            'message': 'Conversation marked as resolved'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving conversation: {str(e)}")


# Customer Insights Endpoints
@app.get("/api/customers/{customer_id}/insights",
         response_model=CustomerInsightsResponse,
         tags=["Customers"])
async def get_customer_insights(
    customer_id: str,
    agent: ProductionConversationAgent = Depends(get_agent)
):
    """
    Returns analytics per customer (how many conversations, most common categories, escalation rate, etc.).
    """
    try:
        insights = agent.get_customer_insights(customer_id)
        
        return CustomerInsightsResponse(
            customer_id=customer_id,
            total_conversations=insights['total_conversations'],
            common_categories=insights['common_categories'],
            escalation_rate=insights['escalation_rate'],
            recent_conversations=insights['recent_conversations']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving insights: {str(e)}")


@app.get("/api/customers/{customer_id}/conversations",
         tags=["Customers"])
async def get_customer_conversations(customer_id: str, limit: int = 10):
    """
    Returns all conversations for a given customer.
    """
    try:
        conversations = production_memory.get_customer_conversation_history(customer_id, limit)
        
        return {
            'customer_id': customer_id,
            'conversations': conversations,
            'total': len(conversations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")


# Analytics Endpoints
@app.get("/api/analytics/summary",
         tags=["Analytics"])
async def get_analytics_summary():
    """
    Returns overall system stats:
        - Total conversations
        - By status (open, resolved, escalated)
        - By category (billing, technical, etc.)
        - Escalation rate
    """
    try:
        from src.database.connection import db_manager
        from src.models.database_models import ConversationDB
        from sqlalchemy import func,text  # Make sure text is imported
        
        with db_manager.get_session() as session:
            # Total conversations
            total_convs = session.query(func.count(ConversationDB.conversation_id)).scalar() or 0
            
            # By status
            status_counts = session.query(
                ConversationDB.status,
                func.count(ConversationDB.conversation_id)
            ).group_by(ConversationDB.status).all()
            
            # By category
            category_counts = session.query(
                ConversationDB.category,
                func.count(ConversationDB.conversation_id)
            ).filter(ConversationDB.category.isnot(None)).group_by(
                ConversationDB.category
            ).all()
            
            # Escalation rate
            escalated_count = session.query(func.count(ConversationDB.conversation_id)).filter(
                ConversationDB.escalated == True
            ).scalar() or 0
            
            return {
                'total_conversations': total_convs,
                'by_status': {status: count for status, count in status_counts},
                'by_category': {cat: count for cat, count in category_counts if cat},
                'escalation_rate': (escalated_count / total_convs * 100) if total_convs > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """
    Custom exception handlers → Format errors as JSON with details & timestamps.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# Runs the FastAPI server on port 8000.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)