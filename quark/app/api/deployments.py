from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentResponse, DeploymentStatus
from app.services.deployment import DeploymentService
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/deployments",
    tags=["Deployments"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Resource not found"}
    }
)

@router.post("/", response_model=DeploymentResponse)
async def create_deployment(
    deployment: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new deployment for an application.

    This endpoint initiates a deployment process with extensive configuration options
    for controlling how your application is deployed.

    Required Parameters:
    ------------------
    - **app_id**: int
        * The ID of the application to deploy
        * Must be an existing application that you have access to
    
    - **version**: str
        * Git tag, branch, or commit hash to deploy
        * Must exist in the linked repository
        * Example: "v1.0.0" or "main" or "abc123def"

    Optional Parameters:
    ------------------
    - **environment**: str (default: "production")
        * Target deployment environment
        * Valid options: "development", "staging", "production"
        * Affects configuration and resource allocation
    
    - **config**: Dict[str, str] (default: {})
        * Environment variables and configuration
        * Secrets are automatically encrypted
        * Example: {"DATABASE_URL": "postgresql://...", "API_KEY": "..."}
    
    - **replicas**: int (default: 1)
        * Number of container instances to run
        * Range: 1-100
        * Auto-scaling may adjust this number
    
    - **strategy**: str (default: "rolling")
        * Deployment strategy to use
        * Options:
            - "rolling": Update instances one at a time
            - "blue-green": Deploy new version alongside old
            - "canary": Gradually shift traffic
    
    - **health_check**: Dict (default: {"path": "/health", "interval": 10})
        * Health check configuration
        * Fields:
            - path: str - HTTP endpoint to check
            - interval_seconds: int - Time between checks (5-300)
            - timeout_seconds: int - Check timeout (1-60)
            - healthy_threshold: int - Successes needed (1-10)
            - unhealthy_threshold: int - Failures needed (1-10)
    
    - **rollback**: Dict (default: {"auto": true, "threshold": 20})
        * Automatic rollback settings
        * Fields:
            - auto: bool - Enable auto rollback
            - threshold_percent: int - Error rate to trigger (0-100)
            - timeout_minutes: int - Maximum rollback wait (1-60)

    Example Request:
    --------------
    ```json
    {
        "app_id": 1,
        "version": "v1.0.0",
        "environment": "production",
        "config": {
            "DATABASE_URL": "postgresql://...",
            "REDIS_URL": "redis://...",
            "LOG_LEVEL": "info"
        },
        "replicas": 2,
        "strategy": "blue-green",
        "health_check": {
            "path": "/api/health",
            "interval_seconds": 15,
            "timeout_seconds": 5,
            "healthy_threshold": 3,
            "unhealthy_threshold": 2
        },
        "rollback": {
            "auto": true,
            "threshold_percent": 25,
            "timeout_minutes": 30
        }
    }
    ```

    Response:
    --------
    ```json
    {
        "id": 1,
        "status": "in_progress",
        "application_id": 1,
        "version": "v1.0.0",
        "environment": "production",
        "created_at": "2024-03-07T11:00:00Z",
        "updated_at": "2024-03-07T11:00:00Z",
        "container_ids": ["abc123"],
        "logs_url": "/deployments/1/logs",
        "metrics_url": "/deployments/1/metrics"
    }
    ```

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid parameter values
        * Missing required fields
        * Invalid configuration format
    
    - **401 Unauthorized**
        * Missing authentication token
        * Invalid token
        * Token expired
    
    - **403 Forbidden**
        * Insufficient permissions
        * Application access denied
        * Environment restrictions
    
    - **404 Not Found**
        * Application not found
        * Version not found in repository
    
    - **409 Conflict**
        * Deployment already in progress
        * Environment locked
        * Resource conflict
    
    - **422 Unprocessable Entity**
        * Resource limits exceeded
        * Invalid configuration values
        * Strategy not supported

    Notes:
    -----
    - Deployments are asynchronous operations
    - Progress can be monitored via the logs_url
    - Real-time metrics available via metrics_url
    - Rollback operations are logged and auditable
    - Configuration values are encrypted at rest
    - Resource limits are enforced per environment
    """
    service = DeploymentService(db)
    
    # Create deployment record
    deployment_record = await service.create_deployment(
        deployment.application_id,
        deployment.commit_sha
    )
    
    # Trigger the deployment process
    deployment_record = await service.trigger_deployment(deployment_record.id)
    
    return deployment_record

@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    Get detailed information about a specific deployment.

    This endpoint provides comprehensive details about a deployment including:
    - Deployment status and progress
    - Container information
    - Resource utilization
    - Logs and events
    - Health check results
    - Rollback history

    Parameters:
    - **deployment_id**: Required, the ID of the deployment to retrieve

    Returns:
    ```json
    {
        "id": 1,
        "application_id": 123,
        "status": "running",
        "version": "v1.0.0",
        "environment": "production",
        "containers": [
            {
                "id": "abc123",
                "status": "healthy",
                "created_at": "2024-03-07T11:00:00Z",
                "metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 256.7,
                    "network_rx": 1024,
                    "network_tx": 2048
                }
            }
        ],
        "config": {
            "DATABASE_URL": "postgresql://...",
            "REDIS_URL": "redis://..."
        },
        "health_checks": [
            {
                "endpoint": "/health",
                "status": "passed",
                "latency_ms": 42
            }
        ],
        "events": [
            {
                "type": "container_started",
                "timestamp": "2024-03-07T11:00:05Z",
                "message": "Container abc123 started successfully"
            }
        ],
        "created_at": "2024-03-07T11:00:00Z",
        "updated_at": "2024-03-07T11:00:10Z"
    }
    ```

    Notes:
    - Real-time metrics are included if the deployment is active
    - Event history is limited to last 100 events
    - Config values are encrypted in transit and at rest
    - Health check results are cached for 60 seconds

    Raises:
    - **401**: Not authenticated
    - **403**: Not authorized to view this deployment
    - **404**: Deployment not found
    """
    deployment = db.get(Deployment, deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    return deployment

@router.get("/application/{app_id}", response_model=List[DeploymentResponse])
async def list_application_deployments(
    app_id: int,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by deployment status"),
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user)
):
    """
    List all deployments for an application with filtering and pagination.

    This endpoint returns a chronological history of deployments including:
    - Successful and failed deployments
    - Rollbacks and hotfixes
    - Blue-green deployment transitions
    - Canary deployments

    Query Parameters:
    - **limit**: Maximum number of deployments to return (default: 10, max: 100)
    - **offset**: Number of deployments to skip (default: 0)
    - **status**: Filter by deployment status (optional)
        - pending: Deployment created but not started
        - in_progress: Deployment is currently running
        - successful: Deployment completed successfully
        - failed: Deployment failed
        - rolled_back: Deployment was rolled back

    Returns:
    ```json
    [
        {
            "id": 1,
            "status": "successful",
            "version": "v1.0.0",
            "environment": "production",
            "created_at": "2024-03-07T11:00:00Z",
            "completed_at": "2024-03-07T11:02:00Z",
            "duration_seconds": 120,
            "metrics": {
                "success_rate": 100,
                "error_count": 0,
                "rollback_count": 0
            }
        }
    ]
    ```

    Notes:
    - Results are ordered by creation date (newest first)
    - Includes both active and historical deployments
    - Metrics are aggregated for completed deployments
    - Duration is calculated for completed deployments only

    Raises:
    - **400**: Invalid query parameters
    - **401**: Not authenticated
    - **403**: Not authorized to view this application
    - **404**: Application not found
    """
    query = select(Deployment).where(Deployment.application_id == app_id)
    
    if status:
        query = query.where(Deployment.status == status)
    
    query = query.order_by(Deployment.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    deployments = db.exec(query).all()
    return deployments 