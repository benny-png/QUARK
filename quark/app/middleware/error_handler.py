from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.utils.errors import QuarkError
import logging
from typing import Union, Dict
import traceback
from sqlalchemy.exc import SQLAlchemyError
from docker.errors import DockerException
from github import GithubException
import json
import uuid

logger = logging.getLogger(__name__)

async def error_handler_middleware(request: Request, call_next):
    """Global error handler middleware"""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        error_id = str(uuid.uuid4())
        
        if isinstance(exc, QuarkError):
            # Handle custom application errors
            logger.error(f"Application error: {exc.code} - {exc.message}", 
                        extra={"details": exc.details})
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_dict()
            )
        
        elif isinstance(exc, SQLAlchemyError):
            # Handle database errors
            logger.error(f"Database error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": "DATABASE_ERROR",
                    "message": "Database operation failed",
                    "error_id": error_id,
                    "details": {"error": str(exc)}
                }
            )
        
        elif isinstance(exc, DockerException):
            # Handle Docker-related errors
            logger.error(f"Docker error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": "DOCKER_ERROR",
                    "message": "Docker operation failed",
                    "error_id": error_id,
                    "details": {"error": str(exc)}
                }
            )
        
        elif isinstance(exc, GithubException):
            # Handle GitHub API errors
            logger.error(f"GitHub API error: {exc.data.get('message')}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "code": "GITHUB_ERROR",
                    "message": "GitHub operation failed",
                    "error_id": error_id,
                    "details": exc.data
                }
            )
        
        else:
            # Handle unexpected errors
            logger.critical(
                f"Unexpected error: {str(exc)}",
                extra={
                    "error_id": error_id,
                    "path": request.url.path,
                    "method": request.method,
                    "traceback": traceback.format_exc()
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "error_id": error_id,
                    "details": {
                        "error": str(exc) if str(exc) else "Unknown error",
                        "support_message": "Please contact support with this error ID"
                    }
                }
            )

def generate_error_id() -> str:
    """Generate a unique error ID for tracking"""
    return str(uuid.uuid4()) 