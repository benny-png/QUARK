from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.deployment import DeploymentStatus

class DeploymentBase(BaseModel):
    application_id: int
    commit_sha: str

class DeploymentCreate(DeploymentBase):
    pass

class DeploymentUpdate(BaseModel):
    status: Optional[DeploymentStatus]
    container_id: Optional[str]
    logs: Optional[str]

class DeploymentResponse(DeploymentBase):
    id: int
    status: DeploymentStatus
    container_id: Optional[str]
    logs: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 