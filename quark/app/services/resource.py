from typing import Dict, Optional
import psutil
from app.config import settings
from app.utils.docker import DockerManager
from sqlmodel import Session, select
from app.models.application import Application

class ResourceManager:
    def __init__(self, db: Optional[Session] = None):
        self.docker = DockerManager()
        self.db = db

    def check_availability(self, cpu_request: float, memory_request: int) -> bool:
        """Check if requested resources are available"""
        current_usage = self.get_current_usage()
        
        # Calculate total requested resources including the new request
        total_cpu = current_usage["cpu_percent"] + cpu_request
        total_memory = current_usage["memory_mb"] + memory_request
        
        # Check against limits
        return (total_cpu <= settings.MAX_CPU_PERCENT and
                total_memory <= settings.MAX_MEMORY_GB * 1024)

    def get_current_usage(self) -> Dict:
        """Get current resource usage"""
        # Get host metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Get container metrics if db is available
        container_cpu = 0.0
        container_memory = 0
        
        if self.db:
            # Get all running applications
            applications = self.db.exec(
                select(Application)
            ).all()
            
            for app in applications:
                stats = self.docker.get_container_stats(app.id)
                container_cpu += stats["cpu_usage"]
                container_memory += stats["memory_usage"]
        
        return {
            "cpu_percent": container_cpu,
            "memory_mb": container_memory,
            "host_cpu_percent": cpu_percent,
            "host_memory_percent": memory.percent,
            "host_memory_available": memory.available / (1024 * 1024)  # MB
        }

    def allocate_resources(self, app_id: int, cpu: float, memory: int) -> bool:
        """Allocate resources for an application"""
        if not self.check_availability(cpu, memory):
            return False
            
        # Resources are available, allocation happens when container starts
        return True

    def release_resources(self, app_id: int) -> None:
        """Release resources allocated to an application"""
        # Resources are automatically released when container stops
        pass 