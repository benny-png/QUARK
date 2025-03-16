from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    SUCCESSFUL = "successful"
    FAILED = "failed"

class Deployment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="application.id")
    commit_sha: str
    status: DeploymentStatus = Field(default=DeploymentStatus.PENDING)
    container_id: Optional[str] = None
    logs: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow) 