import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from unittest.mock import patch, Mock
from app.main import app
from app.api.ws import manager

@pytest.fixture
def websocket_client():
    return TestClient(app)

@pytest.fixture
def mock_monitoring_service():
    with patch('app.api.ws.MonitoringService') as mock:
        service_instance = Mock()
        service_instance.get_app_metrics.return_value = {
            "cpu_usage": 25.5,
            "memory_usage": 512,
            "network_rx": 1024,
            "network_tx": 2048,
            "timestamp": 1234567890
        }
        mock.return_value = service_instance
        yield mock

def test_websocket_connection(websocket_client, mock_monitoring_service):
    with websocket_client.websocket_connect("/ws/metrics/1") as websocket:
        data = websocket.receive_json()
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "network_rx" in data
        assert "network_tx" in data

@pytest.mark.asyncio
async def test_connection_manager():
    websocket = Mock(spec=WebSocket)
    user_id = 1
    
    await manager.connect(websocket, user_id)
    assert user_id in manager.active_connections
    assert websocket in manager.active_connections[user_id]
    
    await manager.disconnect(websocket, user_id)
    assert user_id not in manager.active_connections

@pytest.mark.asyncio
async def test_send_personal_message():
    websocket = Mock(spec=WebSocket)
    user_id = 1
    message = {"type": "test", "data": "test_message"}
    
    await manager.connect(websocket, user_id)
    await manager.send_personal_message(message, user_id)
    
    websocket.send_json.assert_called_once_with(message) 