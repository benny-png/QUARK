from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./quark.db"
    
    # Security
    JWT_SECRET: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Resource Limits
    MAX_CPU_PERCENT: float = 80.0
    MAX_MEMORY_GB: int = 14
    
    # Docker
    DOCKER_SOCK: str = "unix:///var/run/docker.sock"
    DOCKER_REGISTRY: Optional[str] = None
    
    # Nginx
    NGINX_CONF_DIR: str = "/etc/nginx/sites-enabled"
    
    # GitHub
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 