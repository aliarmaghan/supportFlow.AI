from src.workflows.conversation_agent import ConversationAgent
import os
from dotenv import load_dotenv

load_dotenv()

def test_multi_turn_conversation():
    agent = ConversationAgent(api_key=os.getenv("OPENAI_API_KEY"))
    
    customer_context = {
        "plan": "Pro",
        "account_age_months": 6,
        "previous_tickets": 2
    }
    
    print("🤖 Testing Multi-Turn Conversation with Memory")
    print("="*60)
    
    # Turn 1: Initial problem
    print("\n👤 CUSTOMER: Initial message")
    message1 = "Hi, I'm having trouble with our Stripe integration. Payments are failing and customers can't complete purchases."
    
    result1 = agent.handle_customer_message(
        customer_id="cust_12345",
        message=message1,
        customer_context=customer_context
    )
    
    conversation_id = result1["conversation_id"]
    
    print(f"🔍 Classification: {result1['classification'].category} - {result1['classification'].priority}")
    print(f"🤖 AGENT: {result1['response']}")
    
    # Turn 2: Follow-up with more details
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Follow-up message")
    message2 = "I checked the Stripe dashboard like you suggested. I'm seeing error code 402 - authentication failed. What does this mean?"
    
    result2 = agent.handle_customer_message(
        customer_id="cust_12345",
        message=message2,
        conversation_id=conversation_id
    )
    
    print(f"🔍 Classification: {result2['classification'].category} - {result2['classification'].priority}")
    print(f"🤖 AGENT: {result2['response']}")
    
    # Turn 3: Customer provides more context
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Additional context")
    message3 = "I found the API keys section. It looks like we might be using test keys in production. How do I fix this?"
    
    result3 = agent.handle_customer_message(
        customer_id="cust_12345",
        message=message3,
        conversation_id=conversation_id
    )
    
    print(f"🔍 Classification: {result3['classification'].category} - {result3['classification'].priority}")
    print(f"🤖 AGENT: {result3['response']}")
    
    # Show conversation summary
    print("\n" + "="*60)
    print("📊 CONVERSATION SUMMARY")
    print("="*60)
    
    status = agent.get_conversation_status(conversation_id)
    summary = status["conversation_summary"]
    
    print(f"Conversation ID: {summary['conversation_id']}")
    print(f"Total Messages: {summary['message_count']}")
    print(f"Duration: {summary['duration_minutes']:.1f} minutes")
    print(f"Classifications Made: {len(summary['classification_history'])}")
    print(f"Articles Referenced: {len(summary['articles_referenced'])}")
    print(f"Escalated: {summary['escalated']}")
    print(f"Status: {summary['resolution_status']}")

def test_new_vs_continuing_conversation():
    """Test the difference between new and continuing conversations"""
    agent = ConversationAgent(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("\n🧪 Testing New vs Continuing Conversation Context")
    print("="*60)
    
    # Same message, but one is new conversation, one continues existing
    message = "My billing dashboard won't load. Can you help?"
    
    # New conversation
    result_new = agent.handle_customer_message(
        customer_id="cust_67890",
        message=message
    )
    
    print("🆕 NEW CONVERSATION RESPONSE:")
    print(result_new['response'])
    
    # Follow-up in same conversation  
    result_followup = agent.handle_customer_message(
        customer_id="cust_67890",
        message="Actually, let me clarify - it loads but shows zero data even though I know we have active subscriptions.",
        conversation_id=result_new['conversation_id']
    )
    
    print("\n🔄 FOLLOW-UP RESPONSE:")
    print(result_followup['response'])

if __name__ == "__main__":
    test_multi_turn_conversation()
    test_new_vs_continuing_conversation()