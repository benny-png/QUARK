from typing import Dict, Optional, Any
from fastapi import HTTPException, status
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class QuarkError(Exception):
    """Base exception for Quark application"""
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

class ResourceNotFoundError(QuarkError):
    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} with id {resource_id} not found",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "id": resource_id}
        )

class ValidationError(QuarkError):
    def __init__(self, message: str, field_errors: Dict[str, str]):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field_errors": field_errors}
        )

class ResourceLimitExceededError(QuarkError):
    def __init__(self, resource: str, limit: float, current: float):
        super().__init__(
            message=f"{resource} limit exceeded",
            code="RESOURCE_LIMIT_EXCEEDED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "resource": resource,
                "limit": limit,
                "current": current,
                "exceeded_by": current - limit
            }
        )

class DeploymentError(QuarkError):
    def __init__(self, message: str, deployment_id: int, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="DEPLOYMENT_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"deployment_id": deployment_id, **(details or {})}
        )

class AuthenticationError(QuarkError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class GitHubError(QuarkError):
    def __init__(self, message: str, github_error: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="GITHUB_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"github_error": github_error}
        )

class DockerError(QuarkError):
    def __init__(self, message: str, container_id: Optional[str] = None, error_details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="DOCKER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "container_id": container_id,
                "error_details": error_details
            }
        )

class DatabaseError(QuarkError):
    def __init__(self, message: str, operation: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={
                "operation": operation,
                **(details or {})
            }
        ) 