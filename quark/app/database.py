from sqlmodel import create_engine, Session, SQLModel
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create SQLite engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    """Initialize the database, creating all tables"""
    try:
        # Import all models that need to be created
        from app.models.user import User
        from app.models.application import Application
        from app.models.deployment import Deployment
        
        # Create all tables
        logger.info("Creating database tables...")
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise 