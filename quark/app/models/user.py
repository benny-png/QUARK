from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password: str  # This will store the hashed password
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow) 