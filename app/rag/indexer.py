"""Repository indexer for RAG system"""

import logging
from typing import List, Dict, Any
from pathlib import Path
import re
from app.rag.vector_store import get_vector_store
from app.github.client import GitHubClient

logger = logging.getLogger(__name__)


class RepositoryIndexer:
    """Indexes repository code into vector store"""
    
    # File extensions to index
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
        ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
        ".sh", ".bash", ".sql", ".html", ".css", ".scss", ".yaml", ".yml",
        ".json", ".xml", ".md", ".txt"
    }
    
    # Files to always index (documentation)
    IMPORTANT_FILES = {
        "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
        "REVIEW_RULES.md", ".aiconfig", "ARCHITECTURE.md"
    }
    
    # Directories to skip
    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", "venv", "env",
        "dist", "build", ".next", ".cache", "coverage"
    }
    
    def __init__(self):
        self.vector_store = get_vector_store()
    
    def should_index_file(self, file_path: str) -> bool:
        """Determine if a file should be indexed"""
        path = Path(file_path)
        
        # Check if in skip directory
        for part in path.parts:
            if part in self.SKIP_DIRS:
                return False
        
        # Always index important files
        if path.name in self.IMPORTANT_FILES:
            return True
        
        # Check extension
        return path.suffix in self.CODE_EXTENSIONS
    
    def chunk_code(self, content: str, file_path: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Split code into chunks for embedding.
        
        Args:
            content: File content
            file_path: Path to the file
            chunk_size: Maximum characters per chunk
            
        Returns:
            List of chunks with metadata
        """
        chunks = []
        lines = content.split("\n")
        
        current_chunk = []
        current_size = 0
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n".join(current_chunk)
                chunks.append({
                    "id": f"{file_path}_L{start_line}-{i-1}",
                    "text": chunk_text,
                    "metadata": {
                        "file_path": file_path,
                        "start_line": start_line,
                        "end_line": i - 1,
                        "chunk_type": "code",
                    }
                })
                
                # Start new chunk
                current_chunk = [line]
                current_size = line_size
                start_line = i
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunks.append({
                "id": f"{file_path}_L{start_line}-{len(lines)}",
                "text": chunk_text,
                "metadata": {
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": len(lines),
                    "chunk_type": "code",
                }
            })
        
        return chunks
    
    async def index_repository(
        self,
        github_client: GitHubClient,
        owner: str,
        repo: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """
        Index an entire repository.
        
        Args:
            github_client: GitHub API client
            owner: Repository owner
            repo: Repository name
            branch: Branch to index
            
        Returns:
            Indexing statistics
        """
        repo_namespace = f"{owner}_{repo}"
        logger.info(f"Starting indexing for {owner}/{repo}")
        
        # Get repository tree
        tree = await github_client.get_repository_tree(owner, repo, branch)
        
        all_chunks = []
        files_indexed = 0
        
        for item in tree:
            if item["type"] != "blob":  # Skip non-files
                continue
            
            file_path = item["path"]
            
            if not self.should_index_file(file_path):
                continue
            
            try:
                # Get file content
                content = await github_client.get_file_content(
                    owner, repo, file_path, ref=branch
                )
                
                # Chunk the content
                chunks = self.chunk_code(content, file_path)
                all_chunks.extend(chunks)
                files_indexed += 1
                
                logger.debug(f"Indexed {file_path} ({len(chunks)} chunks)")
                
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                continue
        
        # Upsert all chunks to vector store
        if all_chunks:
            self.vector_store.upsert_code_chunks(repo_namespace, all_chunks)
        
        stats = {
            "repository": f"{owner}/{repo}",
            "files_indexed": files_indexed,
            "total_chunks": len(all_chunks),
            "branch": branch,
        }
        
        logger.info(f"Indexing complete: {stats}")
        return stats
    
    async def index_pr_files(
        self,
        github_client: GitHubClient,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> List[Dict[str, Any]]:
        """
        Index only files changed in a PR (for incremental updates).
        
        Args:
            github_client: GitHub API client
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of indexed chunks
        """
        repo_namespace = f"{owner}_{repo}"
        
        # Get PR files
        files = await github_client.get_pull_request_files(owner, repo, pr_number)
        
        all_chunks = []
        
        for file in files:
            file_path = file["filename"]
            
            if not self.should_index_file(file_path):
                continue
            
            # Skip deleted files
            if file["status"] == "removed":
                continue
            
            try:
                # Get file content from PR head
                content = await github_client.get_file_content(
                    owner, repo, file_path, ref=file["sha"]
                )
                
                # Chunk the content
                chunks = self.chunk_code(content, file_path)
                all_chunks.extend(chunks)
                
            except Exception as e:
                logger.warning(f"Failed to index PR file {file_path}: {e}")
                continue
        
        return all_chunks


# Singleton instance
_repository_indexer = None


def get_repository_indexer() -> RepositoryIndexer:
    """Get the repository indexer singleton"""
    global _repository_indexer
    if _repository_indexer is None:
        _repository_indexer = RepositoryIndexer()
    return _repository_indexer

