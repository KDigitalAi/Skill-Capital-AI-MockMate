"""
Rate limiter utility for API endpoints
Simple in-memory rate limiting per user
"""

from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, Request
import threading
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Simple in-memory rate limiter
    Tracks requests per user_id with a sliding window approach
    """
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed per window
            window_seconds: Time window in seconds (default: 60 = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Dictionary: user_id -> list of timestamps
        self._requests: Dict[str, list] = defaultdict(list)
        # Lock for thread-safe operations
        self._lock = threading.Lock()
    
    def is_allowed(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if request is allowed for the given user_id
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed: bool, remaining_requests: int)
        """
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.window_seconds)
        
        with self._lock:
            # Get request timestamps for this user
            user_requests = self._requests[user_id]
            
            # Remove requests outside the time window
            user_requests[:] = [ts for ts in user_requests if ts > window_start]
            
            # Check if limit exceeded
            if len(user_requests) >= self.max_requests:
                remaining = 0
                return False, remaining
            
            # Add current request
            user_requests.append(current_time)
            remaining = self.max_requests - len(user_requests)
            
            return True, remaining
    
    def get_remaining(self, user_id: str) -> int:
        """
        Get remaining requests for a user without consuming a request
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of remaining requests in the current window
        """
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=self.window_seconds)
        
        with self._lock:
            user_requests = self._requests[user_id]
            # Remove old requests
            user_requests[:] = [ts for ts in user_requests if ts > window_start]
            remaining = max(0, self.max_requests - len(user_requests))
            return remaining

# Global rate limiter instance for users
_rate_limiter = RateLimiter(max_requests=30, window_seconds=60)

# Global rate limiter instance for sessions (60 requests/min)
_session_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)

def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter

def get_session_rate_limiter() -> RateLimiter:
    """Get the global session rate limiter instance (60 requests/min)"""
    return _session_rate_limiter


def check_rate_limit(user_id: str) -> None:
    """
    Check rate limit for a user and raise HTTPException if exceeded
    
    Args:
        user_id: User identifier
        
    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    limiter = get_rate_limiter()
    is_allowed, remaining = limiter.is_allowed(user_id)
    
    if not is_allowed:
        logger.warning(f"[RATE-LIMITER] Rate limit exceeded for user_id: {user_id}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum 30 requests per minute. Please try again later."
        )


async def rate_limit_by_user_id(user_id: Optional[str] = None) -> None:
    """
    FastAPI dependency for rate limiting by user_id parameter
    
    Usage:
        @router.post("/endpoint/{user_id}")
        async def my_endpoint(
            user_id: str,
            _: None = Depends(rate_limit_by_user_id)
        ):
            ...
    
    Or with query parameter:
        @router.get("/endpoint")
        async def my_endpoint(
            user_id: str = Query(...),
            _: None = Depends(rate_limit_by_user_id)
        ):
            ...
    """
    if user_id:
        check_rate_limit(user_id)
    # If no user_id, skip rate limiting (for endpoints without user_id)


def check_session_rate_limit(session_id: str) -> None:
    """
    Check rate limit for a session and raise HTTPException if exceeded
    
    Args:
        session_id: Session identifier
        
    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    limiter = get_session_rate_limiter()
    is_allowed, remaining = limiter.is_allowed(session_id)
    
    if not is_allowed:
        logger.warning(f"[RATE-LIMITER] Rate limit exceeded for session_id: {session_id}")
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum 60 requests per minute per session. Please try again later."
        )


async def rate_limit_by_session_id(session_id: str) -> None:
    """
    FastAPI dependency for rate limiting by session_id path parameter
    
    Usage:
        @router.get("/endpoint/{session_id}/feedback")
        async def my_endpoint(
            session_id: str,
            _: None = Depends(rate_limit_by_session_id)
        ):
            ...
    """
    check_session_rate_limit(session_id)

