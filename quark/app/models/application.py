from sqlmodel import SQLModel, Field
from typing import Optional, Dict
from datetime import datetime

class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    repo_url: str
    branch: str = Field(default="main")
    cpu_limit: float
    memory_limit: int
    auto_deploy: bool = True
    env_vars: Dict[str, str] = Field(default_factory=dict)
    owner_id: int = Field(foreign_key="user.id")
    status: str = Field(default="created")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    deployment_url: Optional[str] = None 