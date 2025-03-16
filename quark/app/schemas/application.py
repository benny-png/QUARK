from pydantic import BaseModel, HttpUrl, constr
from typing import Optional, Dict
from datetime import datetime

class ApplicationBase(BaseModel):
    name: constr(min_length=3, max_length=64, regex="^[a-z0-9-]+$")
    repo_url: HttpUrl
    branch: str = "main"
    cpu_limit: float = 1.0  # CPU cores
    memory_limit: int = 512  # MB
    auto_deploy: bool = True
    env_vars: Dict[str, str] = {}

class ApplicationCreate(ApplicationBase):
    """Schema for creating a new application"""
    class Config:
        schema_extra = {
            "example": {
                "name": "my-fastapi-app",
                "repo_url": "https://github.com/username/my-app",
                "branch": "main",
                "cpu_limit": 1.0,
                "memory_limit": 512,
                "auto_deploy": True,
                "env_vars": {
                    "DATABASE_URL": "postgresql://user:pass@host:5432/db",
                    "REDIS_URL": "redis://redis:6379/0"
                }
            }
        }

class ApplicationUpdate(ApplicationBase):
    """Schema for updating an existing application"""
    name: Optional[str] = None
    repo_url: Optional[HttpUrl] = None
    branch: Optional[str] = None
    cpu_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    auto_deploy: Optional[bool] = None
    env_vars: Optional[Dict[str, str]] = None

class ApplicationResponse(ApplicationBase):
    """Schema for application response"""
    id: int
    owner_id: int
    status: Optional[str] = "created"
    created_at: datetime
    updated_at: Optional[datetime] = None
    deployment_url: Optional[str] = None

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "my-fastapi-app",
                "repo_url": "https://github.com/username/my-app",
                "branch": "main",
                "cpu_limit": 1.0,
                "memory_limit": 512,
                "auto_deploy": True,
                "env_vars": {
                    "DATABASE_URL": "postgresql://user:pass@host:5432/db",
                    "REDIS_URL": "redis://redis:6379/0"
                },
                "owner_id": 1,
                "status": "created",
                "created_at": "2024-03-07T12:00:00Z",
                "updated_at": None,
                "deployment_url": None
            }
        } 