"""OVERVIEW:
This file is responsible for caching conversation-related data so that your system:
⚡ Responds faster
💰 Saves OpenAI / LLM calls
🧠 Remembers recent conversation context
🛡️ Still works even if Redis is not available (Windows-safe)
In simple words:
- This file acts as the short-term memory of your AI customer-support system.
- It tries to use Redis (fast, production-ready cache).
- If Redis is not available (very common on Windows), it automatically falls back to an in-memory Python cache.

This file handles:
- Redis connection (if available)
- In-memory cache fallback
- Conversation storage
- Recent message storage (sliding window)
- Message classification caching
- Cache expiration (TTL)
- Health checks
"""

import json
from typing import Optional, Any, Dict
from datetime import timedelta, datetime
import os

# Try to import Redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis not available - using in-memory cache (development only)")


class ConversationCache:
    
    def __init__(self, redis_url: str = None):
        """Reads Redis URL from .env
        - Tries to connect to Redis
        - If Redis fails → switch to in-memory cache
        - Sets cache expiration rules (TTL)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.use_redis = False  # Initialize the attribute first!
        
        # Try Redis first, fall back to in-memory
        if REDIS_AVAILABLE:
            try:
                redis_pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_connect_timeout=2  # Fail fast if Redis unavailable
                )
                self.redis = redis.Redis(connection_pool=redis_pool)
                
                # Test connection
                self.redis.ping()
                self.use_redis = True
                print("✅ Connected to Redis successfully")
                
            except (redis.ConnectionError, redis.TimeoutError) as e:
                print(f"⚠️  Redis connection failed: {e}")
                print("⚠️  Falling back to in-memory cache (development only)")
                self.use_redis = False
                self._init_memory_cache()
        else:
            print("⚠️  Redis not installed - using in-memory cache")
            self.use_redis = False
            self._init_memory_cache()
        
        # Cache TTL settings
        self.conversation_ttl = timedelta(hours=4)
        self.classification_ttl = timedelta(minutes=30)
        self.articles_ttl = timedelta(hours=1)
    
    def _init_memory_cache(self):
        """Initialize in-memory cache as fallback"""
        self.memory_cache = {}
        self.memory_expiry = {}
    
    def _is_expired(self, key: str) -> bool:
        """Check if in-memory cache entry is expired"""
        if key not in self.memory_expiry:
            return True
        return datetime.now() > self.memory_expiry[key]
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Retrieve full conversation context from cache.
        Flow:
        - If Redis → GET conv:{id}
        - If in-memory → dictionary lookup
        - If expired / missing → return None
        💡 Prevents unnecessary DB queries.
        """
        if self.use_redis:
            try:
                cached_data = self.redis.get(f"conv:{conversation_id}")
                if cached_data:
                    return json.loads(cached_data)
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Cache get error: {e}")
        else:
            # In-memory fallback
            key = f"conv:{conversation_id}"
            if key in self.memory_cache and not self._is_expired(key):
                return self.memory_cache[key]
        
        return None
    
    def set_conversation(self, conversation_id: str, conversation_data: Dict):
        """
        - Store conversation data in cache.
        - Uses SETEX in Redis (set + expiry)
        - Uses Python dict with expiry fallback
        """
        if self.use_redis:
            try:
                self.redis.setex(
                    f"conv:{conversation_id}",
                    self.conversation_ttl,
                    json.dumps(conversation_data, default=str)
                )
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Cache set error: {e}")
        else:
            # In-memory fallback
            key = f"conv:{conversation_id}"
            self.memory_cache[key] = conversation_data
            self.memory_expiry[key] = datetime.now() + self.conversation_ttl
    
    def get_recent_messages(self, conversation_id: str, limit: int = 10) -> Optional[list]:
        """- Retrieve last N messages for LLM context.
        - Redis → LRANGE
        - In-memory → list slicing
        - This is how the AI “remembers” recent chat."""
        if self.use_redis:
            try:
                messages = self.redis.lrange(f"messages:{conversation_id}", 0, limit-1)
                return [json.loads(msg) for msg in messages]
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Cache messages get error: {e}")
        else:
            # In-memory fallback
            key = f"messages:{conversation_id}"
            if key in self.memory_cache and not self._is_expired(key):
                return self.memory_cache[key][:limit]
        
        return None
    
    def add_message(self, conversation_id: str, message: Dict):
        """Add a message to cache with sliding window
        - Stores max 50 messages
        - Old messages automatically removed
        - TTL refreshed
        💡 Prevents token explosion in LLM calls.
        """
        if self.use_redis:
            try:
                self.redis.lpush(f"messages:{conversation_id}", json.dumps(message, default=str))
                self.redis.ltrim(f"messages:{conversation_id}", 0, 49)
                self.redis.expire(f"messages:{conversation_id}", self.conversation_ttl)
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Cache message add error: {e}")
        else:
            # In-memory fallback
            key = f"messages:{conversation_id}"
            if key not in self.memory_cache:
                self.memory_cache[key] = []
            
            self.memory_cache[key].insert(0, message)
            self.memory_cache[key] = self.memory_cache[key][:50]  # Keep last 50
            self.memory_expiry[key] = datetime.now() + self.conversation_ttl
    
    def cache_classification(self, message_hash: str, classification: Dict):
        """Cache message classification results.
        Why?
        - Same user messages often repeat
        - Avoid re-running LLM classification
        - Saves money + latency"""
        if self.use_redis:
            try:
                self.redis.setex(
                    f"classification:{message_hash}",
                    self.classification_ttl,
                    json.dumps(classification, default=str)
                )
            except Exception as e:
                print(f"Classification cache error: {e}")
        else:
            # In-memory fallback
            key = f"classification:{message_hash}"
            self.memory_cache[key] = classification
            self.memory_expiry[key] = datetime.now() + self.classification_ttl
    
    def get_cached_classification(self, message_hash: str) -> Optional[Dict]:
        """Retrieves classification if already cached."""
        if self.use_redis:
            try:
                cached = self.redis.get(f"classification:{message_hash}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                print(f"Classification cache get error: {e}")
        else:
            # In-memory fallback
            key = f"classification:{message_hash}"
            if key in self.memory_cache and not self._is_expired(key):
                return self.memory_cache[key]
        
        return None
    
    def invalidate_conversation(self, conversation_id: str):
        """Purpose:
        Clear cache when:
        - Conversation ends
        - Conversation escalates
        - Conversation is closed
        Deletes:
        - Conversation data
        - Message list
        """
        if self.use_redis:
            try:
                self.redis.delete(f"conv:{conversation_id}")
                self.redis.delete(f"messages:{conversation_id}")
            except redis.RedisError as e:
                print(f"Cache invalidation error: {e}")
        else:
            # In-memory fallback
            conv_key = f"conv:{conversation_id}"
            msg_key = f"messages:{conversation_id}"
            
            if conv_key in self.memory_cache:
                del self.memory_cache[conv_key]
                if conv_key in self.memory_expiry:
                    del self.memory_expiry[conv_key]
            
            if msg_key in self.memory_cache:
                del self.memory_cache[msg_key]
                if msg_key in self.memory_expiry:
                    del self.memory_expiry[msg_key]
    
    def clear_cache(self):
        """Purpose:
        - Clears entire cache
        Used for:
        - Testing
        - Debugging
        - Local resets"""
        if self.use_redis:
            try:
                self.redis.flushdb()
            except redis.RedisError as e:
                print(f"Cache clear error: {e}")
        else:
            self.memory_cache.clear()
            self.memory_expiry.clear()
    
    def ping(self):
        """Purpose:
        Health check
        Redis → PING
        In-memory → always healthy
        Used by /health endpoint.
        """
        if self.use_redis:
            return self.redis.ping()
        return True  # In-memory cache is always available


# Global cache instance
conversation_cache = ConversationCache()