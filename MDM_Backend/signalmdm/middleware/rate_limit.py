import logging
import time
from fastapi import Request
from starlette.responses import JSONResponse
from core.redis_client import get_redis

logger = logging.getLogger(__name__)

class RateLimitingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from fastapi import Request
        request = Request(scope, receive=receive)
        path = request.url.path
        
        limit = None
        key_suffix = ""
        
        if path in ("/health", "/api/v1/health"):
            limit = 20
            key_suffix = "health"
        elif path in ("/api/v1/auth/login", "/api/v1/auth/login/"):
            limit = 10
            key_suffix = "login"
            
        if limit is not None:
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0].strip()
            elif request.client:
                ip = request.client.host
            else:
                ip = "unknown"
                
            try:
                r = get_redis()
                current_minute = int(time.time()) // 60
                redis_key = f"rate_limit:{ip}:{key_suffix}:{current_minute}"
                
                pipe = r.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, 60)
                current_count = pipe.execute()[0]
                
                if current_count > limit:
                    logger.warning("[rate_limit] Rate limit exceeded for IP %s on path %s (%d/%d)", ip, path, current_count, limit)
                    response = JSONResponse(
                        status_code=429,
                        content={"detail": "Too many requests. Please try again later."}
                    )
                    await response(scope, receive, send)
                    return
            except Exception as exc:
                logger.error("[rate_limit] Redis rate limiting error (failing open): %s", exc)
                
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception("[rate_limit] Unhandled exception in rate limit middleware: %s", exc)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
            await response(scope, receive, send)

