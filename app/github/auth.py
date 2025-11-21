"""GitHub App authentication using JWT and installation tokens"""

import jwt
import time
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)


class GitHubAuth:
    """Handles GitHub App authentication"""

    def __init__(self):
        self.settings = get_settings()
        self._installation_tokens: Dict[int, Dict[str, any]] = {}
        self._github_time_offset: Optional[int] = None
    
    async def _get_github_time_offset(self) -> int:
        """
        Get the time offset between local system and GitHub servers.
        This handles cases where system time is different from GitHub's time.
        """
        if self._github_time_offset is not None:
            return self._github_time_offset

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.github.com/")
                # GitHub returns Date header with server time
                if "Date" in response.headers:
                    from email.utils import parsedate_to_datetime
                    from datetime import timezone
                    github_time = parsedate_to_datetime(response.headers["Date"])
                    local_time = datetime.now(timezone.utc)
                    offset = int((local_time - github_time).total_seconds())
                    self._github_time_offset = offset
                    logger.info(f"GitHub time offset: {offset} seconds")
                    return offset
        except Exception as e:
            logger.warning(f"Could not determine GitHub time offset: {e}")

        self._github_time_offset = 0
        return 0

    def generate_jwt(self, time_offset: int = 0) -> str:
        """
        Generate a JWT for GitHub App authentication.
        Valid for 10 minutes.

        Args:
            time_offset: Time offset in seconds to adjust for clock differences
        """
        now = int(time.time()) - time_offset

        # Use conservative expiration time
        payload = {
            "iat": now - 60,  # Issued at time (60 seconds in the past to account for clock drift)
            "exp": now + (5 * 60),  # Expiration time (5 minutes)
            "iss": str(self.settings.github_app_id),  # GitHub App ID as string
        }

        # Sign the JWT with the private key
        token = jwt.encode(
            payload,
            self.settings.github_private_key,
            algorithm="RS256"
        )

        return token
    
    async def get_installation_token(self, installation_id: int) -> str:
        """
        Get an installation access token for a specific installation.
        Tokens are cached and reused until they expire.

        Args:
            installation_id: The GitHub App installation ID

        Returns:
            Installation access token
        """
        # Check if we have a cached token that's still valid
        if installation_id in self._installation_tokens:
            cached = self._installation_tokens[installation_id]
            expires_at = datetime.fromisoformat(cached["expires_at"].replace("Z", "+00:00"))

            # If token expires in more than 5 minutes, reuse it
            if expires_at > datetime.utcnow() + timedelta(minutes=5):
                logger.debug(f"Using cached token for installation {installation_id}")
                return cached["token"]

        # Get time offset from GitHub servers
        time_offset = await self._get_github_time_offset()

        # Generate new installation token with time offset
        jwt_token = self.generate_jwt(time_offset)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()
            data = response.json()

        # Cache the token
        self._installation_tokens[installation_id] = {
            "token": data["token"],
            "expires_at": data["expires_at"],
        }

        logger.info(f"Generated new installation token for installation {installation_id}")
        return data["token"]
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify that a webhook payload was sent by GitHub.
        
        Args:
            payload: Raw webhook payload bytes
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        import hmac
        import hashlib
        
        if not signature:
            return False
        
        # GitHub sends signature as "sha256=<hash>"
        if not signature.startswith("sha256="):
            return False
        
        expected_signature = signature.split("=")[1]
        
        # Calculate HMAC
        mac = hmac.new(
            self.settings.github_webhook_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        
        calculated_signature = mac.hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(calculated_signature, expected_signature)


# Singleton instance
_github_auth: Optional[GitHubAuth] = None


def get_github_auth() -> GitHubAuth:
    """Get the GitHub auth singleton instance"""
    global _github_auth
    if _github_auth is None:
        _github_auth = GitHubAuth()
    return _github_auth

