import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

BASE_URL = "http://localhost:8000"

def test_authentication():
    """Test JWT authentication"""
    print("\n🔐 Testing Authentication...")
    
    # Get token
    response = requests.post(f"{BASE_URL}/api/auth/token", json={
        "username": "demo",
        "password": "demo123"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        token = response.json()['access_token']
        print(f"✅ Token received: {token[:20]}...")
        return token
    else:
        print("❌ Authentication failed")
        return None

def test_api_key_auth():
    """Test API key authentication"""
    print("\n🔑 Testing API Key Authentication...")
    
    
    api_key = os.getenv("API_KEY_1")
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "customer_id": "secure_customer_001",
        "message": "Test message with API key auth"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/conversations/message",
        json=payload,
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ API key authentication successful")
        print(json.dumps(response.json(), indent=2)[:200])
    else:
        print(f"❌ Authentication failed: {response.json()}")

def test_rate_limiting():
    """Test rate limiting"""
    print("\n⏱️  Testing Rate Limiting...")
    
    api_key = os.getenv("API_KEY_1")
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Send multiple requests quickly
    for i in range(5):
        payload = {
            "customer_id": "rate_limit_test",
            "message": f"Test message {i}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/conversations/message",
            json=payload,
            headers=headers
        )
        
        print(f"Request {i+1}: {response.status_code}")

def test_metrics():
    """Test Prometheus metrics endpoint"""
    print("\n📊 Testing Metrics...")
    
    response = requests.get(f"{BASE_URL}/metrics")
    
    if response.status_code == 200:
        print("✅ Metrics endpoint accessible")
        metrics = response.text
        print(f"Sample metrics:\n{metrics[:500]}...")
    else:
        print("❌ Metrics endpoint failed")

def test_detailed_health():
    """Test detailed health check"""
    print("\n🏥 Testing Detailed Health Check...")
    
    response = requests.get(f"{BASE_URL}/health/detailed")
    
    if response.status_code == 200:
        print("✅ Detailed health check successful")
        print(json.dumps(response.json(), indent=2))
    else:
        print("❌ Health check failed")

if __name__ == "__main__":
    print("🚀 TESTING SECURITY & MONITORING")
    print("="*60)
    
    test_authentication()
    test_api_key_auth()
    test_rate_limiting()
    test_metrics()
    test_detailed_health()
    
    print("\n✅ Security & Monitoring tests complete!")