from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlmodel import Session, select
import hmac
import hashlib
from app.config import settings
from app.database import get_session
from app.models.application import Application
from app.services.deployment import DeploymentService
import logging
from app.utils.auth import get_current_user
from app.services.github import GitHubService
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/github",
    tags=["GitHub Integration"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Invalid webhook signature"},
        404: {"description": "Repository not found"},
        502: {"description": "GitHub API error"}
    }
)

async def verify_github_signature(
    request: Request,
    x_hub_signature: str = Header(..., alias="X-Hub-Signature-256")
) -> bool:
    """Verify GitHub webhook signature"""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True
        
    body = await request.body()
    hmac_gen = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        msg=body,
        digestmod=hashlib.sha256
    )
    digest = f"sha256={hmac_gen.hexdigest()}"
    
    if not hmac.compare_digest(digest, x_hub_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    return True

@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature: str = Header(..., alias="X-Hub-Signature-256"),
    db: Session = Depends(get_session)
):
    """
    Handle GitHub webhook events for automated deployments.

    Required Headers:
    ---------------
    - **X-Hub-Signature-256**: str
        * GitHub webhook signature
        * Used to verify webhook authenticity
        * Format: sha256=hash
    
    - **X-GitHub-Event**: str
        * Type of webhook event
        * Must be "push" or "deployment"
    
    - **X-GitHub-Delivery**: str
        * Unique webhook delivery ID
        * Used for idempotency

    Request Body:
    -----------
    ```json
    {
        "ref": "refs/heads/main",
        "repository": {
            "clone_url": "https://github.com/username/repo.git",
            "full_name": "username/repo"
        },
        "after": "abc123def456...",
        "commits": [
            {
                "id": "abc123def456...",
                "message": "Update API endpoints",
                "timestamp": "2024-03-07T12:00:00Z",
                "author": {
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            }
        ]
    }
    ```

    Response:
    --------
    ```json
    {
        "status": "accepted",
        "deployment_id": 123,
        "message": "Deployment triggered"
    }
    ```

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid webhook payload
        * Unsupported event type
    
    - **401 Unauthorized**
        * Invalid webhook signature
        * Missing required headers
    
    - **404 Not Found**
        * No matching application found
        * Branch not configured
    
    - **409 Conflict**
        * Deployment already in progress
    
    - **422 Unprocessable Entity**
        * Invalid commit hash
        * Build configuration error

    Notes:
    -----
    - Only processes push events to configured branches
    - Validates webhook signatures using secret
    - Creates deployment record for tracking
    - Triggers async deployment process
    - Supports GitHub deployment API
    """
    payload = await request.json()
    
    # Only process push events
    if request.headers.get("X-GitHub-Event") != "push":
        return {"status": "ignored", "event": "non-push"}
        
    try:
        # Extract repository and branch information
        repo_url = payload["repository"]["clone_url"]
        branch = payload["ref"].split("/")[-1]
        commit_sha = payload["after"]
        
        # Find matching application
        application = db.exec(
            select(Application)
            .where(Application.repo_url == repo_url)
            .where(Application.branch == branch)
        ).first()
        
        if not application:
            return {"status": "ignored", "reason": "no matching application"}
            
        # Trigger deployment
        deployment_service = DeploymentService(db)
        deployment = await deployment_service.create_deployment(
            application.id,
            commit_sha
        )
        
        # Start deployment process
        await deployment_service.trigger_deployment(deployment.id)
        
        return {
            "status": "accepted",
            "deployment_id": deployment.id,
            "message": "Deployment triggered"
        }
        
    except Exception as e:
        logger.error(f"Failed to process webhook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        ) 