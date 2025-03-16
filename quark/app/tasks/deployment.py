from app.utils.docker import DockerManager
from app.models.deployment import Deployment
from sqlmodel import Session, select
from app.database import engine
import logging
import asyncio

logger = logging.getLogger(__name__)

async def cleanup_old_container(app_id: int) -> None:
    """Clean up old containers for an application"""
    try:
        docker = DockerManager()
        
        with Session(engine) as db:
            # Get previous successful deployment
            old_deployment = db.exec(
                select(Deployment)
                .where(Deployment.application_id == app_id)
                .where(Deployment.status == "successful")
                .order_by(Deployment.created_at.desc())
            ).first()

            if old_deployment and old_deployment.container_id:
                logger.info(f"Cleaning up old container {old_deployment.container_id}")
                docker.stop_container(old_deployment.container_id)
                old_deployment.container_id = None
                db.commit()

    except Exception as e:
        logger.error(f"Failed to cleanup old container: {str(e)}")
        raise

async def cleanup_failed_deployments() -> None:
    """Clean up failed deployment containers"""
    try:
        docker = DockerManager()
        
        with Session(engine) as db:
            failed_deployments = db.exec(
                select(Deployment)
                .where(Deployment.status == "failed")
                .where(Deployment.container_id.isnot(None))
            ).all()

            for deployment in failed_deployments:
                logger.info(f"Cleaning up failed deployment container {deployment.container_id}")
                docker.stop_container(deployment.container_id)
                deployment.container_id = None
                db.commit()

    except Exception as e:
        logger.error(f"Failed to cleanup failed deployments: {str(e)}")
        raise 