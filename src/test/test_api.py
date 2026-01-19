import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def print_response(title: str, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))

def test_health_check():
    """Test health check endpoint"""
    print("\n🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    return response.status_code == 200

def test_send_message_sync():
    """Test synchronous message sending"""
    print("\n💬 Testing Synchronous Message...")
    
    payload = {
        "customer_id": "api_test_customer_001",
        "message": "Hi! Our payment integration is broken. Customers can't checkout and we're losing sales!",
        "customer_context": {
            "plan": "Enterprise",
            "account_age_months": 12,
            "previous_tickets": 3
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/conversations/message", json=payload)
    print_response("Synchronous Message Response", response)
    
    if response.status_code == 200:
        return response.json()['conversation_id']
    return None

def test_send_message_async():
    """Test asynchronous message sending"""
    print("\n⚡ Testing Asynchronous Message...")
    
    payload = {
        "customer_id": "api_test_customer_002",
        "message": "Can you help me understand my invoice charges?",
        "customer_context": {
            "plan": "Pro",
            "account_age_months": 6,
            "previous_tickets": 1
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/conversations/message/async", json=payload)
    print_response("Async Message Response", response)
    
    if response.status_code == 202:
        task_id = response.json()['task_id']
        
        # Poll for task completion
        print("\n⏳ Polling task status...")
        for i in range(10):
            time.sleep(2)
            status_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
            status = status_response.json()
            print(f"Attempt {i+1}: {status['status']}")
            
            if status['status'] in ['completed', 'failed']:
                print_response("Final Task Status", status_response)
                break
        
        return status.get('result', {}).get('conversation_id')
    
    return None

def test_get_conversation(conversation_id: str):
    """Test getting conversation history"""
    if not conversation_id:
        print("\n⚠️ Skipping: No conversation ID")
        return
    
    print(f"\n📜 Testing Get Conversation History...")
    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}")
    print_response(f"Conversation {conversation_id}", response)

def test_continue_conversation(conversation_id: str):
    """Test continuing an existing conversation"""
    if not conversation_id:
        print("\n⚠️ Skipping: No conversation ID")
        return
    
    print(f"\n💬 Testing Continue Conversation...")
    
    payload = {
        "customer_id": "api_test_customer_001",
        "message": "I checked the logs and I'm seeing error 500. What should I do next?",
        "conversation_id": conversation_id
    }
    
    response = requests.post(f"{BASE_URL}/api/conversations/message", json=payload)
    print_response("Continue Conversation Response", response)

def test_escalate_conversation(conversation_id: str):
    """Test escalating a conversation"""
    if not conversation_id:
        print("\n⚠️ Skipping: No conversation ID")
        return
    
    print(f"\n🚨 Testing Escalate Conversation...")
    response = requests.post(f"{BASE_URL}/api/conversations/{conversation_id}/escalate")
    print_response("Escalation Response", response)

def test_resolve_conversation(conversation_id: str):
    """Test resolving a conversation"""
    if not conversation_id:
        print("\n⚠️ Skipping: No conversation ID")
        return
    
    print(f"\n✅ Testing Resolve Conversation...")
    response = requests.post(f"{BASE_URL}/api/conversations/{conversation_id}/resolve")
    print_response("Resolution Response", response)

def test_customer_insights(customer_id: str = "api_test_customer_001"):
    """Test getting customer insights"""
    print(f"\n📊 Testing Customer Insights...")
    response = requests.get(f"{BASE_URL}/api/customers/{customer_id}/insights")
    print_response(f"Insights for {customer_id}", response)

def test_customer_conversations(customer_id: str = "api_test_customer_001"):
    """Test getting customer conversations"""
    print(f"\n📋 Testing Customer Conversations...")
    response = requests.get(f"{BASE_URL}/api/customers/{customer_id}/conversations")
    print_response(f"Conversations for {customer_id}", response)

def test_analytics_summary():
    """Test system analytics"""
    print(f"\n📈 Testing Analytics Summary...")
    response = requests.get(f"{BASE_URL}/api/analytics/summary")
    print_response("Analytics Summary", response)

def run_comprehensive_api_test():
    """Run all API tests in sequence"""
    print("🚀 STARTING COMPREHENSIVE API TEST")
    print("="*70)
    
    try:
        # Test 1: Health check
        if not test_health_check():
            print("❌ Health check failed. Is the API running?")
            return
        
        # Test 2: Send synchronous message
        conv_id_sync = test_send_message_sync()
        time.sleep(2)
        
        # Test 3: Get conversation history
        test_get_conversation(conv_id_sync)
        time.sleep(2)
        
        # Test 4: Continue conversation
        test_continue_conversation(conv_id_sync)
        time.sleep(2)
        
        # Test 5: Send async message
        conv_id_async = test_send_message_async()
        time.sleep(2)
        
        # Test 6: Customer insights
        test_customer_insights()
        time.sleep(2)
        
        # Test 7: Customer conversations
        test_customer_conversations()
        time.sleep(2)
        
        # Test 8: Escalate conversation
        test_escalate_conversation(conv_id_sync)
        time.sleep(2)
        
        # Test 9: Analytics
        test_analytics_summary()
        time.sleep(2)
        
        # Test 10: Resolve conversation
        test_resolve_conversation(conv_id_sync)
        
        print("\n" + "="*70)
        print("✅ ALL API TESTS COMPLETED!")
        print("="*70)
        print("\n📊 Access Points:")
        print(f"  - API Docs: {BASE_URL}/docs")
        print(f"  - API ReDoc: {BASE_URL}/redoc")
        print(f"  - Flower (Celery): http://localhost:5555")
        print(f"  - Redis Commander: http://localhost:8081")
        print(f"  - PgAdmin: http://localhost:5050")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Is the API server running?")
        print("Start with: uvicorn src.api.main:app --reload")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    print("⚠️  Make sure the API is running on http://localhost:8000")
    print("Start with: uvicorn src.api.main:app --reload\n")
    
    input("Press Enter to start tests...")
    run_comprehensive_api_test()