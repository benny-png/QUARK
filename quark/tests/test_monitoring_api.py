import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.utils.auth import create_jwt_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    token = create_jwt_token({"sub": "test@example.com", "id": 1})
    return {"Authorization": f"Bearer {token}"}

def test_get_system_metrics(client, auth_headers):
    with patch('app.services.monitoring.MonitoringService.get_system_metrics') as mock:
        mock.return_value = {
            "cpu_percent": 25.5,
            "memory_percent": 60.0,
            "disk_percent": 45.0,
            "timestamp": 1234567890
        }
        
        response = client.get("/metrics/system", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "disk_percent" in data

def test_get_app_metrics(client, auth_headers):
    with patch('app.services.monitoring.MonitoringService.get_app_metrics') as mock:
        mock.return_value = {
            "cpu_usage": 25.5,
            "memory_usage": 512,
            "network_rx": 1024,
            "network_tx": 2048,
            "timestamp": 1234567890
        }
        
        response = client.get("/metrics/apps/1", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "network_rx" in data
        assert "network_tx" in data

def test_get_app_metrics_not_found(client, auth_headers):
    with patch('app.services.monitoring.MonitoringService.get_app_metrics') as mock:
        mock.return_value = {"error": "Application not found"}
        
        response = client.get("/metrics/apps/999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Application not found"

def test_unauthorized_access(client):
    response = client.get("/metrics/system")
    assert response.status_code == 401 