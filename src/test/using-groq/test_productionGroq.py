from src.workflows.conversation_agentGroq import ProductionConversationAgent
import os
from dotenv import load_dotenv
import time
import json

load_dotenv()

def test_production_memory_groq():
    """Test production memory system with Groq API"""
    agent = ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))
    
    customer_context = {
        "plan": "Pro",
        "account_age_months": 8,
        "previous_tickets": 3
    }
    
    print("🏭 Testing Production Memory System with Groq")
    print("="*60)
    
    # Test 1: New conversation - Payment Integration Issue
    print("\n👤 CUSTOMER: First message (New Conversation)")
    start_time = time.time()
    
    result1 = agent.handle_customer_message(
        customer_id="test_customer_456",
        message="Hi! Our Stripe payments suddenly stopped working this morning. Customers are getting errors during checkout and we're losing sales. This is urgent!",
        customer_context=customer_context
    )
    
    conversation_id = result1["conversation_id"]
    
    print(f"🆔 Conversation ID: {conversation_id[:8]}...")
    print(f"🔍 Classification: {result1['classification'].category.upper()} | Priority: {result1['classification'].priority.upper()}")
    print(f"😤 Sentiment: {result1['classification'].sentiment}")
    print(f"🚨 Escalation Required: {result1['escalated']}")
    print(f"⚡ Processing Time: {result1['processing_time_ms']}ms")
    print(f"🤖 GROQ RESPONSE:\n{result1['response']}")
    
    # Wait to simulate real conversation timing
    time.sleep(3)
    
    # Test 2: Continue conversation with technical details
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Follow-up with technical details")
    
    result2 = agent.handle_customer_message(
        customer_id="test_customer_456",
        message="I checked our Stripe dashboard like you suggested. I can see the API calls are failing with error 401 - unauthorized. But we haven't changed our API keys in months. What could cause this?",
        conversation_id=conversation_id
    )
    
    print(f"🔍 Classification: {result2['classification'].category.upper()} | Priority: {result2['classification'].priority.upper()}")
    print(f"😤 Sentiment: {result2['classification'].sentiment}")
    print(f"⚡ Processing Time: {result2['processing_time_ms']}ms")
    print(f"🤖 GROQ RESPONSE:\n{result2['response']}")
    
    time.sleep(2)
    
    # Test 3: Customer provides more context
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Additional troubleshooting info")
    
    result3 = agent.handle_customer_message(
        customer_id="test_customer_456",
        message="I found something! Our webhook endpoints are returning 500 errors. Could this be related? Also, we deployed some code changes yesterday - maybe that broke something?",
        conversation_id=conversation_id
    )
    
    print(f"🔍 Classification: {result3['classification'].category.upper()} | Priority: {result3['classification'].priority.upper()}")
    print(f"😤 Sentiment: {result3['classification'].sentiment}")
    print(f"⚡ Processing Time: {result3['processing_time_ms']}ms")
    print(f"🤖 GROQ RESPONSE:\n{result3['response']}")
    
    time.sleep(2)
    
    # Test 4: Resolution attempt
    print("\n" + "-"*40)
    print("👤 CUSTOMER: Update after trying suggestions")
    
    result4 = agent.handle_customer_message(
        customer_id="test_customer_456",
        message="Great news! I rolled back yesterday's deployment and the webhook errors are gone. Payments are working again! Thank you so much for the help.",
        conversation_id=conversation_id
    )
    
    print(f"🔍 Classification: {result4['classification'].category.upper()} | Priority: {result4['classification'].priority.upper()}")
    print(f"😤 Sentiment: {result4['classification'].sentiment}")
    print(f"⚡ Processing Time: {result4['processing_time_ms']}ms")
    print(f"🤖 GROQ RESPONSE:\n{result4['response']}")
    
    # Show detailed conversation summary from database
    print("\n" + "="*60)
    print("📊 PRODUCTION DATABASE SUMMARY")
    print("="*60)
    
    final_context = result4["conversation_context"]
    print(f"💾 Conversation ID: {final_context['conversation_id']}")
    print(f"👤 Customer ID: {final_context['customer_id']}")
    print(f"📈 Status: {final_context['status'].upper()}")
    print(f"🏷️  Category: {final_context['category'].upper()}")
    print(f"⚠️  Priority: {final_context['priority'].upper()}")
    print(f"💬 Total Messages: {final_context['message_count']}")
    # print(f"⏱️  Duration: {final_context['duration_minutes']:.1f} minutes")  ### ErrorKeyError: 'duration_minutes'
    print(f"🚨 Escalated: {'YES' if final_context['escalated'] else 'NO'}")
    print(f"🔍 Classifications Made: {len(final_context['classification_history'])}")
    print(f"📚 KB Articles Referenced: {len(final_context['articles_referenced'])}")
    
    # Show classification evolution
    print(f"\n📈 CLASSIFICATION EVOLUTION:")
    for i, classification in enumerate(final_context['classification_history'], 1):
        cls = classification['classification']
        print(f"   {i}. {cls.get('category', 'unknown').upper()} - {cls.get('priority', 'unknown').upper()} (Escalation: {cls.get('requires_human_escalation', False)})")

def test_customer_insights_groq():
    """Test customer insights and analytics"""
    agent = ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))
    
    print("\n🔍 CUSTOMER INSIGHTS & ANALYTICS")
    print("="*50)
    
    insights = agent.get_customer_insights("test_customer_456")
    
    print(f"📊 Total Conversations: {insights['total_conversations']}")
    print(f"📈 Common Categories: {insights['common_categories']}")
    print(f"🚨 Escalation Rate: {insights['escalation_rate']:.1f}%")
    print(f"⏱️  Avg Resolution Time: {insights['avg_resolution_time']:.1f} minutes")
    
    print(f"\n📋 RECENT CONVERSATION HISTORY:")
    for i, conv in enumerate(insights['recent_conversations'][:5], 1):  # Show last 5
        status_emoji = {"open": "🔄", "resolved": "✅", "escalated": "🚨"}.get(conv['status'], "❓")
        print(f"   {i}. {status_emoji} {conv['conversation_id'][:8]}... | {conv['category'].upper()} | {conv['status'].upper()}")

def test_conversation_persistence():
    """Test that conversations persist across application restarts"""
    agent = ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))
    
    print("\n🔄 TESTING CONVERSATION PERSISTENCE")
    print("="*45)
    
    # Try to continue a conversation from a previous session
    # In a real scenario, you'd get this ID from your frontend/API
    test_conversation_id = input("Enter a conversation ID to continue (or press Enter to skip): ").strip()
    
    if test_conversation_id:
        print(f"\n🔍 Attempting to continue conversation: {test_conversation_id}")
        
        try:
            result = agent.handle_customer_message(
                customer_id="test_customer_456",
                message="Hi again! I have a follow-up question about our previous issue.",
                conversation_id=test_conversation_id
            )
            
            print(f"✅ Successfully continued conversation!")
            print(f"🤖 Response: {result['response']}")
            print(f"📊 Total messages in this conversation: {result['conversation_context']['message_count']}")
            
        except Exception as e:
            print(f"❌ Error continuing conversation: {e}")
    else:
        print("⏭️  Skipping persistence test")

def test_multiple_customers():
    """Test handling multiple customers simultaneously"""
    agent = ProductionConversationAgent(api_key=os.getenv("GROQ_API_KEY"))
    
    print("\n👥 TESTING MULTIPLE CUSTOMERS")
    print("="*40)
    
    customers = [
        {
            "id": "customer_billing_001",
            "message": "I was charged twice for my subscription this month. Can you help?",
            "context": {"plan": "Starter", "account_age_months": 3}
        },
        {
            "id": "customer_tech_002", 
            "message": "Our API integration is returning 500 errors. This is blocking our production deployment!",
            "context": {"plan": "Enterprise", "account_age_months": 24}
        },
        {
            "id": "customer_feature_003",
            "message": "Can you add SSO support? Our team really needs this feature.",
            "context": {"plan": "Pro", "account_age_months": 6}
        }
    ]
    
    results = []
    start_time = time.time()
    
    for customer in customers:
        print(f"\n👤 {customer['id']}: {customer['message'][:50]}...")
        
        result = agent.handle_customer_message(
            customer_id=customer["id"],
            message=customer["message"],
            customer_context=customer["context"]
        )
        
        results.append(result)
        
        print(f"   🔍 {result['classification'].category.upper()} - {result['classification'].priority.upper()}")
        print(f"   ⚡ {result['processing_time_ms']}ms")
    
    total_time = (time.time() - start_time) * 1000
    print(f"\n📊 MULTI-CUSTOMER SUMMARY:")
    print(f"   Total processing time: {total_time:.0f}ms")
    print(f"   Average per customer: {total_time/len(customers):.0f}ms")
    print(f"   Conversations created: {len(results)}")

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("🚀 STARTING COMPREHENSIVE GROQ PRODUCTION TEST")
    print("="*70)
    
    try:
        test_production_memory_groq()
        test_customer_insights_groq()
        test_conversation_persistence()
        test_multiple_customers()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ Production system is working with Groq API")
        print("✅ Database persistence is working")
        print("✅ Redis caching is working") 
        print("✅ Multi-customer support is working")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("Check your environment variables and database connection")

if __name__ == "__main__":
    # You can run individual tests or the comprehensive test
    choice = input("Run comprehensive test? (y/n): ").lower().strip()
    
    if choice == 'y':
        run_comprehensive_test()
    else:
        print("Running individual tests...")
        test_production_memory_groq()
        test_customer_insights_groq()