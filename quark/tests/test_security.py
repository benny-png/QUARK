import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.security import SecurityMiddleware
from unittest.mock import patch

@pytest.fixture
def app():
    app = FastAPI()
    app.add_middleware(SecurityMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_security_headers(client):
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

def test_rate_limiting(client):
    # Test normal request
    response = client.get("/test")
    assert response.status_code == 200

    # Simulate rate limiting
    with patch('app.middleware.security.SecurityMiddleware._check_rate_limit', return_value=False):
        response = client.get("/test")
        assert response.status_code == 429
        assert response.json()["detail"] == "Too many requests" 