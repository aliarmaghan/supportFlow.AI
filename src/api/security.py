"""OVERVIEW:
The security.py file is like a security guard for your FastAPI application.
It handles three big tasks:
    User Authentication — creating and verifying login tokens (using JWT).
    API Key Authentication — allowing trusted services (like microservices or admin tools) to connect securely.
    Rate Limiting — preventing users from sending too many requests too quickly.
So, it ensures:
    Only authorized users or systems can access protected routes.  
    Passwords are stored safely (hashed, not plain text).
    The system is protected from abuse through rate limits.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Security Configuration
"""
Purpose: Define settings for JWT tokens.
    SECRET_KEY → like a master key used to sign and verify tokens.
    ALGORITHM → defines the encryption method (HS256 is common).
    ACCESS_TOKEN_EXPIRE_MINUTES → how long the token remains valid (24 hours here).
"""
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
"""This sets up bcrypt, a strong and secure password hashing algorithm.
It ensures passwords are never stored in plain text."""
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
"""This enables Bearer Token authentication in FastAPI —
it looks for the token in the Authorization header of requests."""
security = HTTPBearer()


class SecurityManager:
    """Handles authentication and authorization"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Takes a plain password → returns a hashed version (safe to store in DB)."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Checks if a user’s entered password matches the stored hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token
        Steps:
            Copy user info (like {"user_id": 123}).
            Add expiry (exp) and issue time (iat).
            Encode all info into a signed token using the SECRET_KEY.
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Checks if the token is valid:
            Decodes it using the same secret key.
            If invalid/expired → raises HTTPException(401).
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


# API Key based authentication (simpler for machine-to-machine)
class APIKeyAuth:
    """
    This is for machine-to-machine authentication —
    for example, if a backend microservice wants to call your API securely.
    """
    
    def __init__(self):
        # In production, store these in database
        """Stores a list of valid API keys (in a real app, you’d store these in a database or environment variables)."""
        self.valid_api_keys = {
            os.getenv("API_KEY_1", "test-key-123"): {
                "name": "Test Client",
                "permissions": ["read", "write"]
            },
            os.getenv("API_KEY_2", "admin-key-456"): {
                "name": "Admin Client",
                "permissions": ["read", "write", "admin"]
            }
        }
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """Verify API key and return client info
        If invalid → raises a 403 Forbidden error."""
        if api_key in self.valid_api_keys:
            return self.valid_api_keys[api_key]
        
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )


# Dependency for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Extracts the token from the request header. 
    Calls SecurityManager.verify_token(token) to check if it’s valid.
    Returns decoded user info.
    """
    token = credentials.credentials
    return SecurityManager.verify_token(token)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Dependency to verify API key
    """
    api_key = credentials.credentials
    auth = APIKeyAuth()
    return auth.verify_api_key(api_key)


# Rate limiting decorator
from functools import wraps
from fastapi import Request
import time

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}  # {client_id: [(timestamp, count)]}
    
    def check_rate_limit(self, client_id: str, max_requests: int = 100, window: int = 60) -> bool:
        """
        Check if client has exceeded rate limit
        max_requests: Maximum requests allowed
        window: Time window in seconds
        Stores timestamps of requests.
        Removes old requests outside the time window.
        If the client exceeds the limit → returns False.
        """
        now = time.time()
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Remove old requests outside the window
        self.requests[client_id] = [
            req for req in self.requests[client_id]
            if now - req < window
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_id]) >= max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True


rate_limiter = RateLimiter()