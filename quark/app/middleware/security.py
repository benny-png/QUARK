from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Callable
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        # Rate limiting check
        if not await self._check_rate_limit(request):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"}
            )

        # Add security headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

    async def _check_rate_limit(self, request: Request) -> bool:
        # Implement rate limiting logic here
        return True 