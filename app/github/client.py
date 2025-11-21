"""GitHub API client for interacting with repositories and PRs"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from app.github.auth import GitHubAuth
from app.models.review import ReviewComment

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for GitHub API operations"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, auth: GitHubAuth, installation_id: int):
        self.auth = auth
        self.installation_id = installation_id
        self._token: Optional[str] = None
    
    async def _get_token(self) -> str:
        """Get or refresh installation token"""
        if not self._token:
            self._token = await self.auth.get_installation_token(self.installation_id)
        return self._token
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to GitHub API"""
        token = await self._get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            
            if response.status_code == 204:  # No content
                return {}
            
            return response.json()
    
    async def get_pull_request_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Get the diff for a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Diff content as string
        """
        token = await self._get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
        }
        
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.text
    
    async def get_pull_request_files(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of file objects
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        files = await self._request("GET", endpoint)
        return files if isinstance(files, list) else []
    
    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str = "main"
    ) -> str:
        """
        Get content of a file from repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            File content as string
        """
        import base64
        
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        
        data = await self._request("GET", endpoint, params=params)
        
        # GitHub returns base64-encoded content
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content
    
    async def list_repository_files(
        self, owner: str, repo: str, path: str = "", ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """
        List files in a repository directory.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Directory path (empty for root)
            ref: Git reference
            
        Returns:
            List of file/directory objects
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        
        data = await self._request("GET", endpoint, params=params)
        return data if isinstance(data, list) else [data]
    
    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comments: List[ReviewComment],
        summary: str,
    ) -> Dict[str, Any]:
        """
        Create a review with comments on a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            comments: List of review comments
            summary: Review summary/body
            
        Returns:
            Created review object
        """
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        
        # Convert ReviewComment objects to GitHub API format
        github_comments = [
            {
                "path": comment.path,
                "line": comment.line,
                "body": comment.body,
                "side": comment.side,
            }
            for comment in comments
        ]
        
        payload = {
            "body": summary,
            "event": "COMMENT",  # Can be APPROVE, REQUEST_CHANGES, or COMMENT
            "comments": github_comments if github_comments else None,
        }
        
        # Remove comments if empty (just post a general comment)
        if not github_comments:
            payload.pop("comments")
        
        return await self._request("POST", endpoint, json=payload)
    
    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> Dict[str, Any]:
        """
        Create a comment on an issue or pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or PR number
            body: Comment body
            
        Returns:
            Created comment object
        """
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        payload = {"body": body}
        
        return await self._request("POST", endpoint, json=payload)
    
    async def get_repository_tree(
        self, owner: str, repo: str, sha: str, recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get repository tree (all files).
        
        Args:
            owner: Repository owner
            repo: Repository name
            sha: Tree SHA or branch name
            recursive: Whether to get tree recursively
            
        Returns:
            List of tree objects
        """
        endpoint = f"/repos/{owner}/{repo}/git/trees/{sha}"
        params = {"recursive": "1" if recursive else "0"}
        
        data = await self._request("GET", endpoint, params=params)
        return data.get("tree", [])

