from src.workflows.conversation_agent import ProductionConversationAgent
import os
from dotenv import load_dotenv
import time

load_dotenv()

def test_production_memory():
    agent = ProductionConversationAgent(api_key=os.getenv("OPENAI_API_KEY"))
    
    customer_context = {
        "plan": "Pro",
        "account_age_months": 8,
        "previous_tickets": 3
    }
    
    print("🏭 Testing Production Memory System")
    print("="*60)
    
    # Test 1: New conversation
    print("\n👤 CUSTOMER: First message")
    result1 = agent.handle_customer_message(
        customer_id="prod_customer_123",
        message="Hi, our Stripe payments suddenly stopped working this morning. Customers are complaining!",
        customer_context=customer_context
    )
    
    conversation_id = result1["conversation_id"]
    
    print(f"🆔 Conversation ID: {conversation_id}")
    print(f"🔍 Category: {result1['classification'].category} | Priority: {result1['classification'].priority}")
    print(f"⚡ Processing time: {result1['processing_time_ms']}ms")
    print(f"🤖 Response: {result1['response']}")
    
    # Wait a moment to simulate time
    time.sleep(2)
    
    # Test 2: Continue conversation
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Follow-up message")
    result2 = agent.handle_customer_message(
        customer_id="prod_customer_123",
        message="I checked our Stripe dashboard. All API keys look correct. What else could be wrong?",
        conversation_id=conversation_id
    )
    
    print(f"🔍 Category: {result2['classification'].category} | Priority: {result2['classification'].priority}")
    print(f"⚡ Processing time: {result2['processing_time_ms']}ms")  
    print(f"🤖 Response: {result2['response']}")
    
    # Wait a moment
    time.sleep(2)
    
    # Test 3: Another follow-up
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Technical details")
    result3 = agent.handle_customer_message(
        customer_id="prod_customer_123",
        message="I'm getting error 401 - unauthorized. But the keys haven't changed since yesterday.",
        conversation_id=conversation_id
    )
    
    print(f"🔍 Category: {result3['classification'].category} | Priority: {result3['classification'].priority}")
    print(f"⚡ Processing time: {result3['processing_time_ms']}ms")
    print(f"🤖 Response: {result3['response']}")
    
    # Show conversation summary
    print("\n" + "="*60)
    print("📊 CONVERSATION SUMMARY FROM DATABASE")
    print("="*60)
    
    final_context = result3["conversation_context"]
    print(f"Conversation ID: {final_context['conversation_id']}")
    print(f"Customer ID: {final_context['customer_id']}")
    print(f"Status: {final_context['status']}")
    print(f"Category: {final_context['category']}")
    print(f"Priority: {final_context['priority']}")
    print(f"Total Messages: {final_context['message_count']}")
    print(f"Duration: {final_context['duration_minutes']:.1f} minutes")
    print(f"Escalated: {final_context['escalated']}")
    print(f"Classifications Made: {len(final_context['classification_history'])}")
    print(f"KB Articles Used: {len(final_context['articles_referenced'])}")

def test_customer_insights():
    agent = ProductionConversationAgent(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("\n🔍 Testing Customer Insights")
    print("="*40)
    
    insights = agent.get_customer_insights("prod_customer_123")
    
    print(f"Total Conversations: {insights['total_conversations']}")
    print(f"Common Categories: {insights['common_categories']}")
    print(f"Escalation Rate: {insights['escalation_rate']:.1f}%")
    
    print("\nRecent Conversations:")
    for conv in insights['recent_conversations']:
        print(f"  - {conv['conversation_id']}: {conv['category']} ({conv['status']})")

if __name__ == "__main__":
    test_production_memory()
    test_customer_insights()