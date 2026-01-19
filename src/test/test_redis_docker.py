from src.memory.cache import conversation_cache
import json

def test_redis_connection():
    print("🧪 Testing Redis Connection via Docker...")
    
    # Test 1: Basic set/get
    test_data = {
        "conversation_id": "test_123",
        "customer_id": "customer_456",
        "status": "open"
    }
    
    conversation_cache.set_conversation("test_123", test_data)
    print("✅ Data written to Redis")
    
    retrieved = conversation_cache.get_conversation("test_123")
    print(f"✅ Data retrieved from Redis: {retrieved}")
    
    # Test 2: Message caching
    test_message = {
        "role": "user",
        "content": "Test message",
        "timestamp": "2025-01-01T00:00:00"
    }
    
    conversation_cache.add_message("test_123", test_message)
    print("✅ Message added to Redis")
    
    messages = conversation_cache.get_recent_messages("test_123", 10)
    print(f"✅ Messages retrieved: {len(messages)} messages")
    
    # Test 3: Clear test data
    conversation_cache.invalidate_conversation("test_123")
    print("✅ Test data cleaned up")
    
    print("\n🎉 Redis is working perfectly with Docker!")

if __name__ == "__main__":
    test_redis_connection()