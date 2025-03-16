from sqlmodel import Session, select
from typing import List, Optional
from app.models.application import Application
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from fastapi import HTTPException, status
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ApplicationService:
    def __init__(self, db: Session):
        self.db = db

    async def create_application(self, app_data: ApplicationCreate, owner_id: int) -> Application:
        """Create a new application"""
        try:
            logger.info(f"Creating application in service with data: {app_data.dict()}")
            
            # Create application with explicit fields
            application = Application(
                name=app_data.name,
                repo_url=app_data.repo_url,
                branch=app_data.branch,
                cpu_limit=app_data.cpu_limit,
                memory_limit=app_data.memory_limit,
                auto_deploy=app_data.auto_deploy,
                env_vars=app_data.env_vars,
                owner_id=owner_id,
                status="created",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            logger.info(f"Application object created: {application.dict()}")
            
            self.db.add(application)
            logger.info("Application added to session")
            
            self.db.commit()
            logger.info("Transaction committed")
            
            self.db.refresh(application)
            logger.info(f"Application refreshed from DB: {application.dict()}")
            
            return application
            
        except Exception as e:
            logger.error(f"Failed to create application in service: {str(e)}", exc_info=True)
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create application: {str(e)}"
            )

    async def get_application(self, app_id: int, owner_id: int) -> Application:
        """Get application by ID"""
        application = self.db.exec(
            select(Application)
            .where(Application.id == app_id)
            .where(Application.owner_id == owner_id)
        ).first()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        return application

    async def list_applications(self, owner_id: int) -> List[Application]:
        """List all applications for a user"""
        return self.db.exec(
            select(Application)
            .where(Application.owner_id == owner_id)
            .order_by(Application.created_at.desc())
        ).all()

    async def update_application(
        self, 
        app_id: int, 
        owner_id: int, 
        app_data: ApplicationUpdate
    ) -> Application:
        """Update an application"""
        application = await self.get_application(app_id, owner_id)
        
        # Update only provided fields
        update_data = app_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(application, key, value)
        
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    async def delete_application(self, app_id: int, owner_id: int) -> None:
        """Delete an application"""
        application = await self.get_application(app_id, owner_id)
        self.db.delete(application)
        self.db.commit() 