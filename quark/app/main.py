from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, apps, deployments, github, monitoring, ws
from app.database import init_db
from app.middleware.error_handler import error_handler_middleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create logger
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="QUARK Deployment Platform",
    description="A modern application deployment and management platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add error handler middleware
app.middleware("http")(error_handler_middleware)

# Mount routers without additional prefixes since they already have their own
app.include_router(auth.router)  # Already has /auth prefix
app.include_router(apps.router)  # Already has /apps prefix
app.include_router(deployments.router)  # Already has /deployments prefix
app.include_router(github.router)  # Already has /github prefix
app.include_router(monitoring.router)  # Already has /metrics prefix
app.include_router(ws.router)  # Already has /ws prefix

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Application started, database initialized")

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 