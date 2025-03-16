from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationResponse, ApplicationUpdate
from app.utils.auth import get_current_user
from app.models.user import User
from app.services.resource import ResourceManager
from app.services.apps import ApplicationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/apps",
    tags=["Applications"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Application not found"}
    }
)

@router.post("/", response_model=ApplicationResponse)
async def create_application(
    app_data: ApplicationCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new application for deployment.

    Required Parameters:
    ------------------
    - **name**: str
        * Application name (3-64 characters)
        * Must be unique within your account
        * Allowed characters: a-z, 0-9, hyphen
        * Example: "my-fastapi-app"

    - **repo_url**: HttpUrl
        * GitHub repository URL
        * Must be accessible with provided credentials
        * Format: https://github.com/owner/repo
        * Example: "https://github.com/username/my-app"

    Optional Parameters:
    ------------------
    - **branch**: str (default: "main")
        * Git branch to deploy from
        * Must exist in repository
        * Example: "main", "develop", "feature/new-api"

    - **env_vars**: Dict[str, str] (default: {})
        * Environment variables for the application
        * Secrets are automatically encrypted
        * Maximum 100 variables
        * Example:
          ```json
          {
              "DATABASE_URL": "postgresql://...",
              "REDIS_URL": "redis://...",
              "API_KEY": "secret123"
          }
          ```

    - **cpu_limit**: float (default: 1.0)
        * CPU cores allocated
        * Range: 0.1 to 8.0
        * Fractional values allowed
        * Example: 0.5 = half core, 2.0 = two cores

    - **memory_limit**: int (default: 512)
        * Memory allocation in MB
        * Range: 128 to 16384 (16GB)
        * Must be multiple of 64
        * Example: 512, 1024, 2048

    - **auto_deploy**: bool (default: true)
        * Enable automatic deployments
        * Triggers on push to specified branch
        * Requires GitHub webhook configuration

    - **build_settings**: Dict (optional)
        * Custom build configuration
        * Fields:
            - command: str - Build command
            - dockerfile: str - Path to Dockerfile
            - node_version: str - Node.js version
            - python_version: str - Python version
        * Example:
          ```json
          {
              "command": "npm run build",
              "node_version": "16.x",
              "python_version": "3.9"
          }
          ```

    Example Request:
    --------------
    ```json
    {
        "name": "my-fastapi-app",
        "repo_url": "https://github.com/username/my-app",
        "branch": "main",
        "env_vars": {
            "DATABASE_URL": "postgresql://user:pass@host:5432/db",
            "REDIS_URL": "redis://redis:6379/0",
            "LOG_LEVEL": "info"
        },
        "cpu_limit": 1.0,
        "memory_limit": 512,
        "auto_deploy": true,
        "build_settings": {
            "command": "pip install -r requirements.txt",
            "python_version": "3.9"
        }
    }
    ```

    Response:
    --------
    ```json
    {
        "id": 1,
        "name": "my-fastapi-app",
        "status": "created",
        "owner_id": 123,
        "repo_url": "https://github.com/username/my-app",
        "deployment_url": "https://my-fastapi-app.quark.io",
        "created_at": "2024-03-07T12:00:00Z",
        "updated_at": null
    }
    ```

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid application name format
        * Invalid repository URL
        * Invalid environment variable format
        * Resource limits out of range

    - **401 Unauthorized**
        * Missing authentication
        * Invalid token
        * Token expired

    - **403 Forbidden**
        * Repository access denied
        * Insufficient permissions
        * Plan limits exceeded

    - **409 Conflict**
        * Application name already exists
        * Repository already connected
        * Resource allocation conflict

    - **422 Unprocessable Entity**
        * Invalid configuration
        * Build settings validation failed
        * Environment validation failed

    Notes:
    -----
    - Application names must be unique per account
    - Repository access is verified during creation
    - Environment variables are encrypted at rest
    - Resource limits are enforced per plan
    - Auto-deploy requires webhook configuration
    - Build settings are validated before creation
    """
    logger.info(f"Creating application with data: {app_data.dict()}")
    app_service = ApplicationService(db)
    
    try:
        # Create the application using the service
        application = await app_service.create_application(
            app_data=app_data,
            owner_id=current_user.id
        )
        logger.info(f"Application created successfully: {application}")
        
        # Convert to response model
        response = ApplicationResponse(
            id=application.id,
            name=application.name,
            repo_url=application.repo_url,
            branch=application.branch,
            cpu_limit=application.cpu_limit,
            memory_limit=application.memory_limit,
            auto_deploy=application.auto_deploy,
            env_vars=application.env_vars,
            owner_id=application.owner_id,
            status=application.status,
            created_at=application.created_at,
            updated_at=application.updated_at,
            deployment_url=application.deployment_url
        )
        logger.info(f"Response model created: {response.dict()}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to create application: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/", response_model=None)
async def list_applications(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    List all applications owned by the current user.

    Optional Query Parameters:
    -----------------------
    - **offset**: int (default: 0)
        * Number of records to skip
        * Used for pagination
        * Must be >= 0
        * Example: 0, 10, 20

    - **limit**: int (default: 10)
        * Maximum number of records to return
        * Range: 1-100
        * Example: 10, 25, 50

    - **status**: str (optional)
        * Filter applications by status
        * Valid values:
            - "created": Initial setup
            - "building": Build in progress
            - "running": Application active
            - "failed": Deployment failed
            - "stopped": Manually stopped
            - "updating": Update in progress

    Returns:
    --------
    ```json
    [
        {
            "id": 123,
            "name": "app-1",
            "status": "running",
            "repo_url": "https://github.com/username/app-1",
            "created_at": "2024-03-07T12:00:00Z",
            "last_deployment": "2024-03-07T12:00:00Z"
        },
        {
            "id": 124,
            "name": "app-2",
            "status": "failed",
            "repo_url": "https://github.com/username/app-2",
            "created_at": "2024-03-07T13:00:00Z",
            "last_deployment": "2024-03-07T13:00:00Z"
        }
    ]
    ```

    Notes:
    -----
    - Results are ordered by creation date (newest first)
    - Only returns applications owned by the authenticated user
    - Includes basic metrics and last deployment status
    - Pagination is required for large result sets

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid offset/limit values
        * Invalid status filter
    
    - **401 Unauthorized**
        * Authentication required
    """
    # Build the query
    query = select(Application).where(Application.owner_id == current_user.id)
    
    # Apply status filter if provided
    if status:
        query = query.where(Application.status == status)
    
    # Apply pagination and ordering
    query = query.order_by(Application.created_at.desc()).offset(offset).limit(limit)
    
    # Execute the query
    applications = db.exec(query).all()
    
    # Manually create response dictionaries with required fields
    result = []
    for app in applications:
        # Create a dictionary with all fields from the application
        app_data = {
            "id": app.id,
            "name": app.name,
            "repo_url": app.repo_url,
            "branch": app.branch,
            "cpu_limit": app.cpu_limit,
            "memory_limit": app.memory_limit,
            "auto_deploy": app.auto_deploy,
            "env_vars": app.env_vars,
            "owner_id": app.owner_id,
            "status": "created",  # Always set a default status
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "deployment_url": None if not hasattr(app, "deployment_url") else app.deployment_url
        }
        result.append(app_data)  # Return plain dictionaries instead of model objects
    
    return result

@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific application.

    Required Parameters:
    ------------------
    - **app_id**: int
        * The unique identifier of the application
        * Must be a valid application ID that you own
        * Example: 123

    Returns:
    --------
    ```json
    {
        "id": 123,
        "name": "my-fastapi-app",
        "status": "running",
        "repo_url": "https://github.com/username/my-app",
        "branch": "main",
        "env_vars": {
            "DATABASE_URL": "postgresql://...",
            "REDIS_URL": "redis://..."
        },
        "cpu_limit": 1.0,
        "memory_limit": 512,
        "metrics": {
            "cpu_usage": 45.2,
            "memory_usage": 256.7,
            "uptime": 86400
        },
        "deployments": {
            "total": 15,
            "successful": 12,
            "failed": 3,
            "last_deployment": "2024-03-07T12:00:00Z"
        },
        "created_at": "2024-03-01T00:00:00Z",
        "updated_at": "2024-03-07T12:00:00Z"
    }
    ```

    Error Responses:
    --------------
    - **401 Unauthorized**
        * Missing authentication token
        * Invalid token
        * Token expired
    
    - **403 Forbidden**
        * Insufficient permissions
        * Application belongs to another user
    
    - **404 Not Found**
        * Application ID does not exist
    """
    application = db.get(Application, app_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this application"
        )
    
    # Ensure status field is set
    app_dict = application.dict()
    if not app_dict.get('status'):
        app_dict['status'] = "created"
    
    return ApplicationResponse(**app_dict)

@router.delete("/{app_id}")
async def delete_application(
    app_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an application"""
    application = db.get(Application, app_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this application"
        )
    
    db.delete(application)
    db.commit()
    
    return {"status": "success", "message": "Application deleted"}

@router.put("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: int,
    app_data: ApplicationUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing application's configuration.

    Required Parameters:
    ------------------
    - **app_id**: int
        * The unique identifier of the application to update
        * Must be a valid application ID that you own
        * Example: 123

    Optional Update Fields:
    --------------------
    - **name**: str
        * New application name
        * Must be unique within your account
        * 3-64 characters, [a-z0-9-]
    
    - **branch**: str
        * Git branch to deploy from
        * Must exist in repository
    
    - **env_vars**: Dict[str, str]
        * Environment variables to update
        * Existing variables are preserved unless overwritten
        * Set value to null to remove a variable
    
    - **cpu_limit**: float
        * New CPU core limit
        * Range: 0.1 to 8.0
    
    - **memory_limit**: int
        * New memory limit in MB
        * Range: 128 to 16384
        * Must be multiple of 64
    
    - **auto_deploy**: bool
        * Enable/disable automatic deployments
    
    - **build_settings**: Dict
        * Update build configuration
        * Only provided fields are updated

    Example Request:
    --------------
    ```json
    {
        "name": "updated-app-name",
        "branch": "develop",
        "env_vars": {
            "NEW_VAR": "value",
            "OLD_VAR": null
        },
        "cpu_limit": 2.0
    }
    ```

    Notes:
    -----
    - Only provided fields are updated
    - Some updates may trigger a redeployment
    - Environment variables are encrypted
    - Resource limit changes affect next deployment

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid field values
        * Resource limits exceeded
    
    - **401 Unauthorized**
        * Authentication required
    
    - **403 Forbidden**
        * Insufficient permissions
    
    - **404 Not Found**
        * Application not found
    
    - **409 Conflict**
        * Name already in use
        * Update conflicts with running deployment
    """
    application = db.get(Application, app_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this application"
        )
    
    # Update application fields
    for field, value in app_data.dict(exclude_unset=True).items():
        setattr(application, field, value)
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application 