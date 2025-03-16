from typing import Optional
from datetime import datetime
from sqlmodel import Session, select
from app.models.deployment import Deployment, DeploymentStatus
from app.models.application import Application
from app.utils.docker import DockerManager
from app.utils.nginx import NginxManager
from app.services.resource import ResourceManager
from app.tasks.deployment import cleanup_old_container, cleanup_failed_deployments
import logging

logger = logging.getLogger(__name__)

class DeploymentService:
    def __init__(self, db: Session):
        self.db = db
        self.docker = DockerManager()
        self.nginx = NginxManager()
        self.resource_manager = ResourceManager()

    async def create_deployment(self, application_id: int, commit_sha: str) -> Deployment:
        """Create a new deployment record"""
        application = self.db.exec(
            select(Application).where(Application.id == application_id)
        ).first()
        if not application:
            raise ValueError("Application not found")

        deployment = Deployment(
            application_id=application_id,
            commit_sha=commit_sha,
            status=DeploymentStatus.PENDING
        )
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    async def trigger_deployment(self, deployment_id: int) -> Deployment:
        """Execute the deployment process"""
        deployment = self.db.get(Deployment, deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")

        application = self.db.get(Application, deployment.application_id)
        
        try:
            # Update status to building
            deployment.status = DeploymentStatus.BUILDING
            self.db.commit()

            # Build the image
            image_tag = self.docker.build_image(
                application.repo_url,
                deployment.commit_sha
            )

            # Check resource availability
            if not self.resource_manager.check_availability(
                application.cpu_limit,
                application.memory_limit
            ):
                raise Exception("Insufficient resources available")

            # Update status to deploying
            deployment.status = DeploymentStatus.DEPLOYING
            self.db.commit()

            # Start the new container
            container = self.docker.run_container(
                image_tag,
                application.id,
                application.cpu_limit,
                application.memory_limit
            )

            # Update deployment with container ID
            deployment.container_id = container.id
            self.db.commit()

            # Health check
            if await self._check_health(container):
                # Update Nginx configuration
                self.nginx.update_config(application.id, container)
                
                # Schedule cleanup of old containers
                await cleanup_old_container(application.id)

                deployment.status = DeploymentStatus.SUCCESSFUL
            else:
                raise Exception("Health check failed")

        except Exception as e:
            logger.error(f"Deployment failed: {str(e)}")
            deployment.status = DeploymentStatus.FAILED
            deployment.logs = str(e)
            
            # Cleanup failed deployment
            if deployment.container_id:
                self.docker.stop_container(deployment.container_id)

        finally:
            deployment.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(deployment)

        return deployment

    async def _check_health(self, container: 'Container') -> bool:
        """Check if the container is healthy"""
        try:
            # Wait for container to be ready
            import time
            time.sleep(5)  # Give the application time to start

            # Get container inspection info
            info = container.inspect()
            
            # Check if container is running
            if info["State"]["Running"]:
                # You could add additional health checks here
                # For example, making an HTTP request to a health endpoint
                return True
            
            return False
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False 