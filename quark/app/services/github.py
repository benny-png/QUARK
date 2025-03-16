from typing import Optional, Dict, Any
import aiohttp
from fastapi import HTTPException, status
from app.config import settings
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {settings.GITHUB_TOKEN}"
        }

    async def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature"""
        if not settings.GITHUB_WEBHOOK_SECRET:
            logger.warning("GITHUB_WEBHOOK_SECRET not set, skipping signature verification")
            return True

        hmac_gen = hmac.new(
            settings.GITHUB_WEBHOOK_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        digest = f"sha256={hmac_gen.hexdigest()}"
        
        if not hmac.compare_digest(digest, signature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook signature"
            )
        return True

    async def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}"
            ) as response:
                if response.status == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Repository not found"
                    )
                elif response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="GitHub API error"
                    )
                return await response.json()

    async def create_deployment_status(
        self,
        owner: str,
        repo: str,
        deployment_id: int,
        state: str,
        description: Optional[str] = None,
        environment_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update deployment status on GitHub"""
        data = {
            "state": state,
            "description": description or f"Deployment {state}",
            "environment_url": environment_url
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                f"{self.base_url}/repos/{owner}/{repo}/deployments/{deployment_id}/statuses",
                json=data
            ) as response:
                if response.status != 201:
                    logger.error(
                        f"Failed to create deployment status: {await response.text()}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to update GitHub deployment status"
                    )
                return await response.json()

    async def get_commit(
        self,
        owner: str,
        repo: str,
        commit_sha: str
    ) -> Dict[str, Any]:
        """Get commit information"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{commit_sha}"
            ) as response:
                if response.status == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Commit not found"
                    )
                elif response.status != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="GitHub API error"
                    )
                return await response.json() 