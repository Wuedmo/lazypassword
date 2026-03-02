"""Git-based versioning for lazypassword vault."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


class GitVersioningError(Exception):
    """Exception for git versioning errors."""
    pass


class VaultVersion:
    """Represents a single vault version/commit."""
    
    def __init__(self, commit_hash: str, message: str, timestamp: str, author: str):
        self.commit_hash = commit_hash
        self.message = message
        self.timestamp = timestamp
        self.author = author
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "message": self.message,
            "timestamp": self.timestamp,
            "author": self.author,
        }


class GitVersioning:
    """Manages git-based versioning for the vault."""
    
    def __init__(self, vault_path: str):
        """
        Initialize git versioning for a vault.
        
        Args:
            vault_path: Path to the vault file
        """
        self.vault_path = Path(vault_path)
        self.vault_dir = self.vault_path.parent
        self.git_dir = self.vault_dir / ".git"
    
    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> str:
        """
        Run a git command.
        
        Args:
            args: Git command arguments
            cwd: Working directory (defaults to vault dir)
            
        Returns:
            Command output
            
        Raises:
            GitVersioningError: If command fails
        """
        cwd = cwd or self.vault_dir
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitVersioningError(f"Git command failed: {e.stderr}")
        except FileNotFoundError:
            raise GitVersioningError("Git not found. Please install git.")
    
    def is_initialized(self) -> bool:
        """Check if git repo is initialized."""
        return self.git_dir.exists()
    
    def initialize(self) -> None:
        """Initialize git repository for versioning."""
        if not self.is_initialized():
            self._run_git(["init"])
            self._run_git(["config", "user.email", "lazypassword@local"])
            self._run_git(["config", "user.name", "LazyPassword"])
    
    def commit(self, message: str) -> str:
        """
        Commit the current vault state.
        
        Args:
            message: Commit message
            
        Returns:
            Commit hash
        """
        if not self.is_initialized():
            self.initialize()
        
        # Stage the vault file
        self._run_git(["add", str(self.vault_path.name)])
        
        # Create commit
        self._run_git(["commit", "-m", message, "--allow-empty"])
        
        # Get the commit hash
        return self._run_git(["rev-parse", "HEAD"])
    
    def get_history(self, limit: int = 50) -> List[VaultVersion]:
        """
        Get commit history.
        
        Args:
            limit: Maximum number of commits to return
            
        Returns:
            List of VaultVersion objects
        """
        if not self.is_initialized():
            return []
        
        try:
            # Format: hash|message|timestamp|author
            output = self._run_git([
                "log",
                f"--max-count={limit}",
                "--pretty=format:%H|%s|%ai|%an",
                "--",
                str(self.vault_path.name)
            ])
            
            if not output:
                return []
            
            versions = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        versions.append(VaultVersion(
                            commit_hash=parts[0][:8],  # Short hash
                            message=parts[1],
                            timestamp=parts[2],
                            author=parts[3]
                        ))
            
            return versions
        except GitVersioningError:
            return []
    
    def rollback(self, commit_hash: str) -> None:
        """
        Rollback vault to a specific commit.
        
        Args:
            commit_hash: Hash of commit to rollback to
        """
        if not self.is_initialized():
            raise GitVersioningError("Git not initialized")
        
        # Checkout the specific version of the vault file
        self._run_git(["checkout", commit_hash, "--", str(self.vault_path.name)])
        
        # Create a new commit to record the rollback
        self.commit(f"Rollback to {commit_hash[:8]}")
    
    def diff(self, commit_hash: str) -> str:
        """
        Get diff between current state and a commit.
        
        Args:
            commit_hash: Hash of commit to compare with
            
        Returns:
            Diff output
        """
        if not self.is_initialized():
            return ""
        
        try:
            return self._run_git([
                "diff",
                commit_hash,
                "--",
                str(self.vault_path.name)
            ])
        except GitVersioningError:
            return ""
    
    def show(self, commit_hash: str) -> Optional[bytes]:
        """
        Get vault content at a specific commit.
        
        Args:
            commit_hash: Hash of commit
            
        Returns:
            Vault content as bytes, or None if not found
        """
        if not self.is_initialized():
            return None
        
        try:
            return self._run_git([
                "show",
                f"{commit_hash}:{self.vault_path.name}"
            ]).encode('utf-8')
        except GitVersioningError:
            return None
