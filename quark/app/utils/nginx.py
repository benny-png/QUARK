import os
import subprocess
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class NginxManager:
    TEMPLATE = """
upstream app_{app_id} {{
    server {container_ip}:{container_port};
}}

server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://app_{app_id};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    def __init__(self):
        self.conf_dir = settings.NGINX_CONF_DIR

    def update_config(self, app_id: int, container) -> None:
        """Update Nginx configuration for an application"""
        try:
            # Get container network info
            container_info = container.inspect()
            container_ip = list(container_info["NetworkSettings"]["Networks"].values())[0]["IPAddress"]
            container_port = 8000  # Assuming FastAPI apps run on port 8000

            # Generate config from template
            config = self.TEMPLATE.format(
                app_id=app_id,
                container_ip=container_ip,
                container_port=container_port,
                domain=f"app-{app_id}.quark.local"  # Example domain pattern
            )

            # Write config file
            config_path = os.path.join(self.conf_dir, f"app_{app_id}.conf")
            with open(config_path, "w") as f:
                f.write(config)

            # Test and reload Nginx
            self._test_config()
            self._reload_nginx()

        except Exception as e:
            logger.error(f"Failed to update Nginx config: {str(e)}")
            raise

    def _test_config(self) -> None:
        """Test Nginx configuration"""
        result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Invalid Nginx configuration: {result.stderr}")

    def _reload_nginx(self) -> None:
        """Reload Nginx configuration"""
        result = subprocess.run(["nginx", "-s", "reload"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to reload Nginx: {result.stderr}") 