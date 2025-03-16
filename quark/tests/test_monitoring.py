import pytest
from unittest.mock import Mock, patch
from app.services.monitoring import MonitoringService
from app.models.application import Application
from app.models.deployment import Deployment
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@pytest.fixture
def db_session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def monitoring_service(db_session):
    return MonitoringService(db_session)

@pytest.fixture
def mock_docker():
    with patch('app.services.monitoring.DockerManager') as mock:
        docker_instance = Mock()
        docker_instance.get_container_stats.return_value = {
            "cpu_usage": 25.5,
            "memory_usage": 512,
            "network_rx": 1024,
            "network_tx": 2048
        }
        mock.return_value = docker_instance
        yield mock

def test_get_app_metrics_success(db_session, monitoring_service, mock_docker):
    # Create test data
    app = Application(name="Test App", repo_url="test/repo", cpu_limit=50.0, memory_limit=1024, owner_id=1)
    db_session.add(app)
    db_session.commit()

    deployment = Deployment(
        application_id=app.id,
        container_id="test_container",
        status="successful",
        version="1.0.0"
    )
    db_session.add(deployment)
    db_session.commit()

    # Test metrics collection
    metrics = await monitoring_service.get_app_metrics(app.id)
    
    assert "error" not in metrics
    assert metrics["cpu_usage"] == 25.5
    assert metrics["memory_usage"] == 512
    assert metrics["network_rx"] == 1024
    assert metrics["network_tx"] == 2048
    assert "timestamp" in metrics

def test_get_app_metrics_no_app(monitoring_service):
    metrics = await monitoring_service.get_app_metrics(999)
    assert "error" in metrics
    assert metrics["error"] == "Application not found"

def test_get_app_metrics_no_deployment(db_session, monitoring_service):
    # Create app without deployment
    app = Application(name="Test App", repo_url="test/repo", cpu_limit=50.0, memory_limit=1024, owner_id=1)
    db_session.add(app)
    db_session.commit()

    metrics = await monitoring_service.get_app_metrics(app.id)
    assert "error" in metrics
    assert metrics["error"] == "No active deployment found"

def test_get_system_metrics(monitoring_service):
    metrics = await monitoring_service.get_system_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert "disk_percent" in metrics
    assert "timestamp" in metrics 