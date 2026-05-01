from fastapi import HTTPException, Request
from utils.redis_client import redis_client
from logger import get_logger
import time

logger = get_logger()

def rate_limit(requests: int, window: int):
    """
    Simple Redis-based rate limiter.
    requests: Number of allowed requests
    window: Window size in seconds
    """
    async def decorator(request: Request):
        if not redis_client.client:
            return  # Skip if Redis is down

        # Use client IP as the key
        client_ip = request.client.host
        key = f"rate_limit:{request.url.path}:{client_ip}"
        
        try:
            # Increment and set TTL if new
            current = redis_client.client.incr(key)
            if current == 1:
                redis_client.client.expire(key, window)
            
            if current > requests:
                ttl = redis_client.client.ttl(key)
                logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
                raise HTTPException(
                    status_code=429, 
                    detail={
                        "error": "Too Many Requests",
                        "retry_after_seconds": ttl
                    }
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return  # Fail open if Redis has issues

    return decorator
