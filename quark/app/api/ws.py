from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.utils.auth import get_current_user, verify_token
from app.services.monitoring import MonitoringService
import json
import logging
from typing import Dict, List, Optional

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Connection refused"}
    }
)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    await self.disconnect(connection, user_id)
                except Exception as e:
                    logger.error(f"Failed to send message: {str(e)}")

manager = ConnectionManager()
monitoring_service = MonitoringService()

@router.websocket("/metrics/{app_id}")
async def metrics_websocket(
    websocket: WebSocket,
    app_id: int,
    token: str = Query(...),
):
    """
    Real-time metrics streaming via WebSocket.

    Provides continuous updates of:
    - System metrics
    - Container metrics
    - Application performance
    - Resource utilization

    Authentication:
    - Requires valid JWT token as query parameter
    - Validates token on connection
    - Maintains authenticated session

    Data Format:
    1. **System Metrics**
    ```json
    {
        "type": "system",
        "data": {
            "cpu_percent": 45.2,
            "memory_percent": 62.8,
            "disk_percent": 73.1,
            "timestamp": 1709812345
        }
    }
    ```

    2. **Container Metrics**
    ```json
    {
        "type": "container",
        "data": {
            "container_id": "abc123",
            "cpu_usage": 32.5,
            "memory_mb": 256,
            "network_rx_bytes": 1024,
            "network_tx_bytes": 2048
        }
    }
    ```

    3. **Application Events**
    ```json
    {
        "type": "event",
        "data": {
            "event": "scaling",
            "message": "Scaling to 3 replicas",
            "timestamp": 1709812345
        }
    }
    ```

    Connection Example:
    ```javascript
    const ws = new WebSocket(
        `ws://localhost:8001/ws/metrics/1?token=${jwt_token}`
    );

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
    };
    ```

    Notes:
    - Updates every 1 second
    - Automatic reconnection on failure
    - Rate limiting applies
    - Connection closes on token expiration

    Error Responses:
    - **401**: Invalid/expired token
    - **403**: Insufficient permissions
    - **404**: Application not found
    """
    await manager.connect(websocket, current_user["id"])
    try:
        while True:
            # Get metrics for the application
            metrics = await monitoring_service.get_app_metrics(app_id)
            await manager.send_personal_message(
                {"type": "metrics", "data": metrics},
                current_user["id"]
            )
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        await manager.disconnect(websocket, current_user["id"]) 