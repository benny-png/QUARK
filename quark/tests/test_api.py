import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
import jwt
from datetime import datetime, timedelta
from app.main import app
from app.config import settings
from app.models.user import User
from app.models.application import Application
from app.database import get_session

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

@pytest.fixture
def client():
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def auth_headers(client, test_user):
    # Register user
    response = client.post("/auth/register", json=test_user)
    assert response.status_code == 200
    
    # Login
    response = client.post("/auth/login", data=test_user)
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_register_user(client, test_user):
    response = client.post("/auth/register", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]

def test_login_user(client, test_user):
    # Register first
    client.post("/auth/register", json=test_user)
    
    # Try login
    response = client.post("/auth/login", data=test_user)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_create_application(client, auth_headers):
    app_data = {
        "name": "Test App",
        "repo_url": "https://github.com/test/app",
        "branch": "main",
        "cpu_limit": 20.0,
        "memory_limit": 512
    }
    
    response = client.post(
        "/apps/",
        json=app_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == app_data["name"]
    assert data["repo_url"] == app_data["repo_url"]

def test_list_applications(client, auth_headers):
    response = client.get("/apps/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_unauthorized_access(client):
    response = client.get("/apps/")
    assert response.status_code == 401 