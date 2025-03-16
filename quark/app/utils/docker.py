import docker
import tempfile
import os
import git
from typing import Dict, Optional
from app.config import settings

class DockerManager:
    def __init__(self):
        self.client = docker.from_env()

    def build_image(self, repo_url: str, commit_sha: str) -> str:
        """Clone repository and build Docker image"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Clone the repository
            repo = git.Repo.clone_from(repo_url, temp_dir)
            repo.git.checkout(commit_sha)

            # Build the image
            image_tag = f"quark-app:{commit_sha}"
            self.client.images.build(
                path=temp_dir,
                tag=image_tag,
                rm=True
            )
            return image_tag

    def run_container(self, image_tag: str, app_id: int, cpu_limit: float, memory_limit: int) -> docker.models.containers.Container:
        """Run a container with resource limits"""
        container = self.client.containers.run(
            image_tag,
            detach=True,
            name=f"quark-app-{app_id}",
            cpu_period=100000,  # Default period in microseconds
            cpu_quota=int(cpu_limit * 100000),  # Percentage of CPU period
            mem_limit=f"{memory_limit}m",
            environment={
                "APP_ID": str(app_id)
            }
        )
        return container

    def get_container_stats(self, container_id: str) -> Dict:
        """Get container resource usage statistics"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage and memory usage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_usage = (cpu_delta / system_delta) * 100.0
            
            memory_usage = stats["memory_stats"]["usage"] / (1024 * 1024)  # Convert to MB
            
            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage
            }
        except docker.errors.NotFound:
            return {"cpu_usage": 0, "memory_usage": 0}

    def stop_container(self, container_id: str) -> None:
        """Stop and remove a container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
        except docker.errors.NotFound:
            pass 