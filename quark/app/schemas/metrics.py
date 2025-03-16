from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    timestamp: int

class ContainerMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    network_rx_bytes: int
    network_tx_bytes: int
    timestamp: int

class ApplicationMetrics(BaseModel):
    app_id: int
    containers: List[ContainerMetrics]
    total_cpu: float
    total_memory: float
    timestamp: int 