from typing import Dict, List, Optional
import psutil
from prometheus_client import Gauge, CollectorRegistry, Counter, Histogram
from app.utils.docker import DockerManager
from app.models.deployment import Deployment
from sqlmodel import Session, select
import asyncio
import time

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

RESPONSE_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

CPU_USAGE = Gauge(
    'app_cpu_usage_percent',
    'Application CPU usage percentage',
    ['app_id', 'container_id']
)

MEMORY_USAGE = Gauge(
    'app_memory_usage_bytes',
    'Application memory usage in bytes',
    ['app_id', 'container_id']
)

class MonitoringService:
    def __init__(self, db: Optional[Session] = None):
        self.docker = DockerManager()
        self.db = db
        self.registry = CollectorRegistry()
        
        # Prometheus metrics
        self.cpu_gauge = Gauge(
            "container_cpu_usage", 
            "Container CPU Usage Percentage",
            ["app_id", "container_id"],
            registry=self.registry
        )
        self.memory_gauge = Gauge(
            "container_memory_usage",
            "Container Memory Usage MB",
            ["app_id", "container_id"],
            registry=self.registry
        )
        self.host_cpu_gauge = Gauge(
            "host_cpu_usage",
            "Host CPU Usage Percentage",
            registry=self.registry
        )
        self.host_memory_gauge = Gauge(
            "host_memory_usage",
            "Host Memory Usage Percentage",
            registry=self.registry
        )

    async def collect_container_metrics(self, app_id: int) -> Dict:
        """Collect metrics for a specific application's container"""
        deployment = self.db.exec(
            select(Deployment)
            .where(Deployment.application_id == app_id)
            .where(Deployment.status == "successful")
            .order_by(Deployment.created_at.desc())
        ).first()

        if not deployment or not deployment.container_id:
            return {"cpu_usage": 0, "memory_usage": 0}

        stats = self.docker.get_container_stats(deployment.container_id)
        
        # Update Prometheus metrics
        self.cpu_gauge.labels(
            app_id=app_id,
            container_id=deployment.container_id
        ).set(stats["cpu_usage"])
        
        self.memory_gauge.labels(
            app_id=app_id,
            container_id=deployment.container_id
        ).set(stats["memory_usage"])

        return stats

    async def collect_host_metrics(self) -> Dict:
        """Collect host system metrics"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Update Prometheus metrics
        self.host_cpu_gauge.set(cpu_percent)
        self.host_memory_gauge.set(memory.percent)
        
        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_available": memory.available / (1024 * 1024)  # MB
        }

    async def start_metrics_collection(self, app_ids: List[int]) -> None:
        """Start collecting metrics for multiple applications"""
        while True:
            # Collect host metrics
            await self.collect_host_metrics()
            
            # Collect container metrics for each app
            for app_id in app_ids:
                await self.collect_container_metrics(app_id)
            
            await asyncio.sleep(15)  # Collect every 15 seconds 

    async def get_app_metrics(self, app_id: int) -> Dict:
        """Get real-time metrics for an application"""
        try:
            # Get application and its active deployment
            app = self.db.exec(
                select(Application)
                .where(Application.id == app_id)
            ).first()
            
            if not app:
                return {"error": "Application not found"}

            deployment = self.db.exec(
                select(Deployment)
                .where(Deployment.application_id == app_id)
                .where(Deployment.status == "successful")
                .order_by(Deployment.created_at.desc())
            ).first()

            if not deployment or not deployment.container_id:
                return {"error": "No active deployment found"}

            # Get container stats
            stats = self.docker.get_container_stats(deployment.container_id)
            
            # Update Prometheus metrics
            CPU_USAGE.labels(
                app_id=app_id,
                container_id=deployment.container_id
            ).set(stats["cpu_usage"])
            
            MEMORY_USAGE.labels(
                app_id=app_id,
                container_id=deployment.container_id
            ).set(stats["memory_usage"])

            return {
                "cpu_usage": stats["cpu_usage"],
                "memory_usage": stats["memory_usage"],
                "network_rx": stats["network_rx"],
                "network_tx": stats["network_tx"],
                "timestamp": int(time.time())
            }

        except Exception as e:
            return {"error": str(e)}

    async def get_system_metrics(self) -> Dict:
        """Get system-wide metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available": memory.available,
            "disk_percent": disk.percent,
            "disk_free": disk.free,
            "timestamp": int(time.time())
        } 