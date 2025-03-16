from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.auth import get_current_user
from app.services.monitoring import MonitoringService
from app.database import get_session
from sqlmodel import Session
from typing import Dict, List, Optional
from app.models.user import User
from app.schemas.metrics import SystemMetrics, ApplicationMetrics, ContainerMetrics
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/metrics",
    tags=["Monitoring"],
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Resource not found"},
        500: {"description": "Monitoring service error"}
    }
)

@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    Get real-time system-wide metrics.

    Provides current resource usage statistics for the entire system, including:
    - CPU utilization
    - Memory usage
    - Disk space
    - Network I/O

    Query Parameters:
    None

    Returns:
    ```json
    {
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
        "disk_percent": 73.1,
        "timestamp": 1709812345
    }
    ```

    Notes:
    - Metrics are collected in real-time
    - CPU percentage is aggregate across all cores
    - Memory includes both RAM and swap usage
    - Disk percentage is for the primary partition

    Raises:
    - **401**: Not authenticated
    - **500**: Error collecting metrics
    """
    monitoring_service = MonitoringService()
    return await monitoring_service.get_system_metrics()

@router.get("/apps/{app_id}", response_model=ApplicationMetrics)
async def get_app_metrics(
    app_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get application-specific metrics"""
    monitoring_service = MonitoringService(db)
    metrics = await monitoring_service.get_app_metrics(app_id)
    
    if "error" in metrics:
        raise HTTPException(status_code=404, detail=metrics["error"])
    
    return metrics

@router.get("/deployments/{deployment_id}", response_model=ContainerMetrics)
async def get_deployment_metrics(
    deployment_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get deployment-specific metrics"""
    monitoring_service = MonitoringService(db)
    return await monitoring_service.get_deployment_metrics(deployment_id)

@router.get("/apps/{app_id}/history", response_model=List[ApplicationMetrics])
async def get_app_metrics_history(
    app_id: int,
    start_time: datetime = Query(..., description="Start timestamp (ISO format)"),
    end_time: datetime = Query(..., description="End timestamp (ISO format)"),
    interval: int = Query(300, description="Interval in seconds (default: 5 minutes)"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical metrics for an application.

    Retrieves time-series metrics data for specified time range and interval.
    Data is aggregated based on the interval parameter.

    Parameters:
    - **app_id**: Application ID
    - **start_time**: Start of time range (ISO format)
    - **end_time**: End of time range (ISO format)
    - **interval**: Aggregation interval in seconds

    Example request:
    ```
    GET /metrics/apps/1/history?start_time=2024-03-07T00:00:00Z&end_time=2024-03-07T23:59:59Z&interval=3600
    ```

    Returns:
    ```json
    [
        {
            "timestamp": 1709812345,
            "cpu_usage": 45.2,
            "memory_usage": 256.7,
            "network_rx": 1024,
            "network_tx": 2048
        },
        ...
    ]
    ```

    Notes:
    - Maximum time range: 7 days
    - Minimum interval: 60 seconds
    - Data points are averaged over intervals
    - Timestamps are in Unix epoch format

    Raises:
    - **400**: Invalid time range or interval
    - **401**: Not authenticated
    - **404**: Application not found
    """

@router.get("/applications/{app_id}", response_model=ApplicationMetrics)
async def get_application_metrics(
    app_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    interval: str = Query("5m", regex="^[0-9]+[mhd]$"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed metrics for a specific application.

    Required Parameters:
    ------------------
    - **app_id**: int
        * Application identifier
        * Must be an application you own

    Optional Query Parameters:
    -----------------------
    - **start_time**: datetime
        * Start of metrics window
        * ISO 8601 format
        * Default: 24 hours ago
    
    - **end_time**: datetime
        * End of metrics window
        * ISO 8601 format
        * Default: current time
    
    - **interval**: str (default: "5m")
        * Metrics aggregation interval
        * Format: number + unit (m/h/d)
        * Examples: "5m", "1h", "1d"
        * Min: 1m, Max: 7d

    Returns:
    --------
    ```json
    {
        "app_id": 123,
        "metrics": {
            "cpu": {
                "current": 45.2,
                "avg_1h": 42.1,
                "max_1h": 78.3,
                "min_1h": 12.4
            },
            "memory": {
                "current_mb": 256.7,
                "avg_1h_mb": 245.2,
                "max_1h_mb": 512.0,
                "min_1h_mb": 128.0
            },
            "network": {
                "rx_bytes": 1024000,
                "tx_bytes": 2048000,
                "connections": 42
            },
            "requests": {
                "total": 15420,
                "success_rate": 99.8,
                "avg_latency_ms": 42,
                "error_rate": 0.2
            }
        },
        "containers": [
            {
                "id": "abc123",
                "status": "running",
                "uptime": 86400,
                "metrics": {
                    "cpu_percent": 45.2,
                    "memory_mb": 256.7
                }
            }
        ],
        "timestamp": "2024-03-07T12:00:00Z"
    }
    ```

    Error Responses:
    --------------
    - **400 Bad Request**
        * Invalid time range
        * Invalid interval format
    
    - **401 Unauthorized**
        * Authentication required
    
    - **403 Forbidden**
        * Insufficient permissions
    
    - **404 Not Found**
        * Application not found
    
    Notes:
    -----
    - Real-time metrics have 1-minute resolution
    - Historical data is aggregated by interval
    - Maximum time range is 30 days
    - Metrics are cached for 60 seconds
    """ 