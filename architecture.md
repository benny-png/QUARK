Here's a clear and structured project document tailored for Cursor Composer to build a QUARK FastAPI backend application based on the provided architecture. This document includes detailed instructions, file structure, and implementation guidance.

---

# QUARK FastAPI Backend Project Document

**Project Name:** QUARK - Automated Deployment Platform  
**Date:** March 07, 2025  
**Purpose:** To provide Cursor Composer with a comprehensive guide to build a FastAPI-based backend for the QUARK deployment platform, adhering to the specified architecture.

## Project Overview

QUARK is an automated deployment platform designed to run on a single VPS (16GB RAM, 400GB SSD). It provides a robust system for managing containerized deployments, integrating with GitHub, monitoring resources, and serving real-time metrics via a FastAPI backend. This document outlines the implementation details for Cursor Composer to create the backend.

## Objectives

1. Build a FastAPI application with all specified components (API Gateway, Deployment Service, GitHub Integration, Resource Manager, Monitoring Service).
2. Implement a blue-green deployment workflow.
3. Integrate with PostgreSQL, Docker, Huey task queue, and Prometheus for monitoring.
4. Provide real-time updates via WebSockets.
5. Ensure security, resource management, and scalability readiness.

## File Structure

```
quark/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app entry point
│   ├── config.py           # Configuration and environment variables
│   ├── models/             # SQLModel database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── application.py
│   │   ├── deployment.py
│   │   ├── resource.py
│   │   └── metric.py
│   ├── schemas/            # Pydantic schemas for API validation
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── application.py
│   │   ├── deployment.py
│   │   └── metric.py
│   ├── api/                # API endpoint routers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── apps.py
│   │   ├── deployments.py
│   │   ├── github.py
│   │   ├── monitoring.py
│   │   └── ws.py        # WebSocket endpoints
│   ├── services/           # Core business logic
│   │   ├── __init__.py
│   │   ├── deployment.py
│   │   ├── github.py
│   │   ├── resource.py
│   │   └── monitoring.py
│   ├── tasks/              # Huey task definitions
│   │   ├── __init__.py
│   │   └── deployment.py
│   └── utils/              # Utility functions
│       ├── __init__.py
│       ├── auth.py      # JWT and authentication helpers
│       ├── docker.py    # Docker SDK wrappers
│       └── nginx.py     # Nginx configuration management
├── migrations/             # Database migration scripts
├── tests/                  # Unit and integration tests
│   ├── __init__.py
│   └── test_api.py
├── Dockerfile              # Docker configuration for QUARK
├── docker-compose.yml      # Local development services
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## Technology Stack

- **FastAPI**: Core framework for API endpoints.
- **Pydantic V2**: Data validation and serialization.
- **SQLModel**: ORM for PostgreSQL database interactions.
- **Docker SDK for Python**: Container management.
- **Huey**: Task queue with Redis backend.
- **Prometheus**: Metrics collection and storage.
- **Node Exporter & cAdvisor**: Host and container metrics.
- **WebSockets**: Real-time data delivery.
- **Nginx**: Reverse proxy (configured via Python utilities).

## Implementation Instructions

### 1. Setup and Configuration

**`app/config.py`**  
- Define environment variables (e.g., `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`).
- Set resource limits: max CPU (80%), max memory (14GB).
- Configure Docker and Nginx paths.

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:pass@localhost/quark"
    REDIS_URL: str = "redis://localhost:6379"
    JWT_SECRET: str = "your-secret-key"
    MAX_CPU_PERCENT: float = 80.0
    MAX_MEMORY_GB: int = 14
    DOCKER_SOCK: str = "unix:///var/run/docker.sock"
    NGINX_CONF_DIR: str = "/etc/nginx/sites-enabled"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. Database Models

**`app/models/`**  
- Implement SQLModel classes for `Users`, `Applications`, `Deployments`, `Resources`, and `Metrics`.

Example: **`app/models/application.py`**
```python
from sqlmodel import SQLModel, Field
from typing import Optional

class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    repo_url: str
    cpu_limit: float  # Percentage
    memory_limit: int  # MB
    owner_id: int = Field(foreign_key="users.id")
```

### 3. API Endpoints

**`app/main.py`**  
- Initialize FastAPI app and include routers.

```python
from fastapi import FastAPI
from app.api import auth, apps, deployments, github, monitoring, ws
from app.config import settings

app = FastAPI(title="QUARK Deployment Platform")

app.include_router(auth.router, prefix="/auth")
app.include_router(apps.router, prefix="/apps")
app.include_router(deployments.router, prefix="/deployments")
app.include_router(github.router, prefix="/github")
app.include_router(monitoring.router, prefix="/metrics")
app.include_router(ws.router, prefix="/ws")
```

**`app/api/deployments.py`**  
- Implement CRUD operations and deployment-specific endpoints (e.g., `/deployments/{id}/rollback`).

```python
from fastapi import APIRouter, Depends
from app.schemas.deployment import DeploymentCreate
from app.services.deployment import DeploymentService
from app.utils.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=dict)
async def create_deployment(deployment: DeploymentCreate, user=Depends(get_current_user)):
    return await DeploymentService().trigger_deployment(deployment, user)
```

### 4. Deployment Service

**`app/services/deployment.py`**  
- Implement blue-green deployment logic using Docker SDK.

```python
from docker import DockerClient
from app.utils.docker import build_image, run_container
from app.utils.nginx import update_nginx_config
from app.models.deployment import Deployment

class DeploymentService:
    def __init__(self):
        self.docker = DockerClient.from_env()

    async def trigger_deployment(self, deployment_data, user):
        # Clone repo, build image
        image_tag = build_image(deployment_data.repo_url, deployment_data.commit_sha)
        
        # Start green container
        green_container = run_container(image_tag, deployment_data)
        
        # Health check
        if not self._check_health(green_container):
            raise Exception("Green container failed health check")
        
        # Update Nginx and cutover traffic
        update_nginx_config(deployment_data.app_id, green_container)
        
        # Cleanup old (blue) container after grace period
        self._schedule_cleanup(deployment_data.app_id)
        
        return {"status": "deployed", "container_id": green_container.id}
```

### 5. Task Queue

**`app/tasks/deployment.py`**  
- Use Huey for background tasks like cleanup.

```python
from huey import RedisHuey
from app.config import settings

huey = RedisHuey("quark", url=settings.REDIS_URL)

@huey.task()
def cleanup_old_container(app_id: int):
    # Logic to remove old container after grace period
    pass
```

### 6. Monitoring Service

**`app/services/monitoring.py`**  
- Collect metrics using Prometheus and push to WebSocket clients.

```python
from prometheus_client import Gauge, CollectorRegistry
from app.utils.docker import get_container_stats

class MonitoringService:
    def __init__(self):
        self.registry = CollectorRegistry()
        self.cpu_gauge = Gauge("cpu_usage", "CPU Usage", ["app_id"], registry=self.registry)

    async def collect_metrics(self, app_id: int):
        stats = get_container_stats(app_id)
        self.cpu_gauge.labels(app_id=app_id).set(stats["cpu_usage"])
        return stats
```

### 7. WebSocket Endpoints

**`app/api/ws.py`**  
- Provide real-time metrics and logs.

```python
from fastapi import APIRouter, WebSocket
from app.services.monitoring import MonitoringService

router = APIRouter()

@router.websocket("/metrics")
async def metrics_websocket(websocket: WebSocket):
    await websocket.accept()
    while True:
        stats = await MonitoringService().collect_metrics(app_id=1)  # Example app_id
        await websocket.send_json(stats)
        await asyncio.sleep(1)
```

### 8. Resource Management

**`app/services/resource.py`**  
- Track and enforce resource limits.

```python
class ResourceManager:
    def check_availability(self, cpu_request: float, memory_request: int) -> bool:
        current_cpu = self._get_current_cpu_usage()
        current_memory = self._get_current_memory_usage()
        return (current_cpu + cpu_request <= settings.MAX_CPU_PERCENT and
                current_memory + memory_request <= settings.MAX_MEMORY_GB * 1024)
```

### 9. Security

**`app/utils/auth.py`**  
- Implement JWT authentication.

```python
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_jwt_token(data: dict):
    return jwt.encode(data, settings.JWT_SECRET, algorithm="HS256")
```

### 10. Docker and Nginx Integration

**`app/utils/docker.py`**  
- Wrapper for Docker SDK operations.

```python
import docker

def build_image(repo_url: str, commit_sha: str) -> str:
    client = docker.from_env()
    # Logic to clone and build image
    return f"quark-app:{commit_sha}"
```

**`app/utils/nginx.py`**  
- Manage Nginx configurations.

```python
def update_nginx_config(app_id: int, container):
    # Generate and reload Nginx config
    pass
```

## Dependencies (`requirements.txt`)

```
fastapi==0.95.0
pydantic==2.0.0
sqlmodel==0.0.8
docker==6.0.0
huey==2.4.4
prometheus-client==0.14.1
uvicorn==0.20.0
psycopg2-binary==2.9.5
redis==4.5.1
python-jose[cryptography]==3.3.0
```

## Development Setup (`docker-compose.yml`)

```yaml
version: "3.8"
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: quark
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
  redis:
    image: redis:6
```

## Instructions for Cursor Composer

1. **Generate Files**: Create the file structure and populate with the provided code snippets.
2. **Complete Logic**: Fill in placeholders (e.g., `_check_health`, `_schedule_cleanup`) with appropriate implementations based on the architecture.
3. **Test**: Add unit tests in `tests/test_api.py` for key endpoints and services.
4. **Run**: Use `docker-compose up` for local testing.

## Notes

- Ensure all async operations use `await` appropriately.
- Validate resource limits during deployment triggers.
- Implement error handling for Docker and database operations.

This document provides a complete blueprint for building the QUARK FastAPI backend. Let me know if you need further clarification!

# QUARK Architecture

## Overview

QUARK is designed as a microservices-based application deployment platform with the following key components:

### 1. Core Components

- **API Server**: FastAPI application handling HTTP requests
- **Resource Manager**: Manages container resources and limits
- **Deployment Service**: Handles application deployment workflow
- **Monitoring Service**: Collects and processes metrics
- **WebSocket Server**: Provides real-time updates

### 2. External Services

- **PostgreSQL**: Primary database
- **Redis**: Caching and task queue
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Nginx**: Reverse proxy and load balancer

## System Architecture

```
                                   ┌─────────────┐
                                   │    Nginx    │
                                   └─────┬───────┘
                                         │
                                   ┌─────┴───────┐
                                   │  API Server │
                                   └─────┬───────┘
                     ┌───────────────────┼───────────────────┐
             ┌───────┴───────┐   ┌──────┴────────┐   ┌──────┴───────┐
             │  PostgreSQL   │   │     Redis     │   │  Prometheus   │
             └───────────────┘   └───────────────┘   └──────────────┘
```

### 3. Key Services

#### Resource Manager
```python
class ResourceManager:
    def check_availability(self, cpu_request: float, memory_request: int) -> bool:
        current_usage = self.get_current_usage()
        return (current_usage["cpu"] + cpu_request <= settings.MAX_CPU_PERCENT and
                current_usage["memory"] + memory_request <= settings.MAX_MEMORY_GB)
```

#### Deployment Service
```python
class DeploymentService:
    async def deploy(self, app_id: int, version: str) -> Deployment:
        # Check resources
        # Build container
        # Start container
        # Update routing
        return deployment
```

#### Monitoring Service
```python
class MonitoringService:
    async def collect_metrics(self, app_id: int) -> Dict:
        container_stats = self.docker.get_stats(app_id)
        return {
            "cpu": container_stats.cpu_percent,
            "memory": container_stats.memory_usage,
            "network": container_stats.network_stats
        }
```

## Security

1. Authentication using JWT
2. Rate limiting
3. Resource isolation
4. HTTPS enforcement
5. Container security

## Scalability

1. Horizontal scaling of API servers
2. Database replication
3. Redis clustering
4. Container orchestration

## Monitoring

1. Application metrics
2. System metrics
3. Container metrics
4. Custom alerts

## Future Improvements

1. Kubernetes integration
2. Multi-region support
3. Advanced auto-scaling
4. Blue-green deployments