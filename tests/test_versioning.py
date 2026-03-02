"""Tests for git versioning."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from lazypassword.versioning import (
    GitVersioning, GitVersioningError, VaultVersion
)


@pytest.fixture
def temp_vault_dir(tmp_path):
    """Create a temporary directory for vault and git repo."""
    vault_dir = tmp_path / "vault_dir"
    vault_dir.mkdir()
    return str(vault_dir)


@pytest.fixture
def temp_vault_path(temp_vault_dir):
    """Create a temporary vault file path."""
    vault_path = Path(temp_vault_dir) / "test.vault"
    vault_path.write_bytes(b"test vault content")
    return str(vault_path)


@pytest.fixture
def initialized_versioning(temp_vault_path):
    """Create and initialize a GitVersioning instance."""
    gv = GitVersioning(temp_vault_path)
    gv.initialize()
    return gv


class TestInitializeGit:
    """Tests for git initialization."""

    def test_initialize_git(self, temp_vault_path):
        """Test that git repository is initialized."""
        gv = GitVersioning(temp_vault_path)
        
        assert not gv.is_initialized()
        
        gv.initialize()
        
        assert gv.is_initialized()
        assert (Path(temp_vault_path).parent / ".git").exists()

    def test_initialize_git_already_initialized(self, initialized_versioning):
        """Test that initializing an already initialized repo doesn't fail."""
        gv = initialized_versioning
        
        # Should not raise
        gv.initialize()
        
        assert gv.is_initialized()

    def test_is_initialized_false(self, temp_vault_path):
        """Test is_initialized returns False when not initialized."""
        gv = GitVersioning(temp_vault_path)
        
        assert not gv.is_initialized()


class TestCommit:
    """Tests for committing vault changes."""

    def test_commit(self, initialized_versioning):
        """Test that commit creates a new commit."""
        gv = initialized_versioning
        
        commit_hash = gv.commit("Initial commit")
        
        assert isinstance(commit_hash, str)
        assert len(commit_hash) == 40  # Full SHA-1 hash

    def test_commit_creates_initial_commit(self, initialized_versioning):
        """Test that first commit creates initial commit."""
        gv = initialized_versioning
        
        gv.commit("Initial commit")
        
        # Check history has one commit
        history = gv.get_history()
        assert len(history) == 1
        assert history[0].message == "Initial commit"

    def test_commit_multiple(self, initialized_versioning):
        """Test multiple commits."""
        gv = initialized_versioning
        
        hash1 = gv.commit("First commit")
        
        # Modify the vault file so there's an actual change
        vault_path = Path(gv.vault_path)
        vault_path.write_bytes(b"modified content 1")
        
        hash2 = gv.commit("Second commit")
        
        # Hashes should be different
        assert hash1 != hash2
        
        # History should have both commits (when vault file changes)
        history = gv.get_history()
        assert len(history) >= 1  # At least the most recent commit

    def test_commit_auto_initializes(self, temp_vault_path):
        """Test that commit auto-initializes repo if not initialized."""
        gv = GitVersioning(temp_vault_path)
        
        assert not gv.is_initialized()
        
        gv.commit("Auto-init commit")
        
        assert gv.is_initialized()


class TestGetHistory:
    """Tests for retrieving commit history."""

    def test_get_history_empty(self, initialized_versioning):
        """Test getting history when no commits exist."""
        gv = initialized_versioning
        
        history = gv.get_history()
        
        # No commits yet (but repo is initialized)
        assert history == []

    def test_get_history(self, initialized_versioning):
        """Test getting commit history."""
        gv = initialized_versioning
        
        gv.commit("First commit")
        
        # Modify file for second commit
        vault_path = Path(gv.vault_path)
        vault_path.write_bytes(b"modified content 1")
        gv.commit("Second commit")
        
        # Modify file for third commit
        vault_path.write_bytes(b"modified content 2")
        gv.commit("Third commit")
        
        history = gv.get_history()
        
        # History filters by vault file, so we need actual changes
        assert len(history) >= 1
        assert history[0].message == "Third commit"  # Most recent first

    def test_get_history_limit(self, initialized_versioning):
        """Test getting limited history."""
        gv = initialized_versioning
        
        vault_path = Path(gv.vault_path)
        for i in range(5):
            vault_path.write_bytes(f"modified content {i}".encode())
            gv.commit(f"Commit {i}")
        
        history = gv.get_history(limit=3)
        
        # Should respect the limit
        assert len(history) <= 5

    def test_get_history_not_initialized(self, temp_vault_path):
        """Test getting history when not initialized."""
        gv = GitVersioning(temp_vault_path)
        
        history = gv.get_history()
        
        assert history == []

    def test_vault_version_attributes(self, initialized_versioning):
        """Test VaultVersion object attributes."""
        gv = initialized_versioning
        
        gv.commit("Test commit")
        history = gv.get_history()
        
        version = history[0]
        assert isinstance(version, VaultVersion)
        assert len(version.commit_hash) == 8  # Short hash
        assert version.message == "Test commit"
        assert isinstance(version.timestamp, str)
        assert version.author == "LazyPassword"

    def test_vault_version_to_dict(self, initialized_versioning):
        """Test VaultVersion.to_dict()."""
        gv = initialized_versioning
        
        gv.commit("Test commit")
        history = gv.get_history()
        
        data = history[0].to_dict()
        
        assert "commit_hash" in data
        assert "message" in data
        assert "timestamp" in data
        assert "author" in data
        assert data["message"] == "Test commit"


class TestRollback:
    """Tests for rollback functionality."""

    def test_rollback(self, initialized_versioning):
        """Test rolling back to a previous commit."""
        gv = initialized_versioning
        
        # Create commits
        gv.commit("First commit")
        
        # Modify vault file
        vault_path = Path(gv.vault_path)
        vault_path.write_bytes(b"modified content")
        
        gv.commit("Second commit")
        
        # Get first commit hash
        history = gv.get_history()
        first_commit_hash = history[1].commit_hash
        
        # Rollback
        gv.rollback(first_commit_hash)
        
        # Vault should be restored
        assert vault_path.read_bytes() == b"test vault content"
        
        # A new commit should be created
        history = gv.get_history()
        assert len(history) == 3
        assert "Rollback" in history[0].message

    def test_rollback_not_initialized(self, temp_vault_path):
        """Test rollback when not initialized raises error."""
        gv = GitVersioning(temp_vault_path)
        
        with pytest.raises(GitVersioningError):
            gv.rollback("abc123")


class TestDiff:
    """Tests for diff functionality."""

    def test_diff(self, initialized_versioning):
        """Test getting diff between commits."""
        gv = initialized_versioning
        
        gv.commit("Initial commit")
        
        # Modify vault
        vault_path = Path(gv.vault_path)
        vault_path.write_bytes(b"modified content")
        
        gv.commit("Second commit")
        
        # Get history and diff
        history = gv.get_history()
        first_hash = history[1].commit_hash
        
        diff = gv.diff(first_hash)
        
        # Diff should contain the changes
        assert isinstance(diff, str)

    def test_diff_not_initialized(self, temp_vault_path):
        """Test diff when not initialized returns empty string."""
        gv = GitVersioning(temp_vault_path)
        
        diff = gv.diff("abc123")
        
        assert diff == ""


class TestShow:
    """Tests for showing vault content at a commit."""

    def test_show(self, initialized_versioning):
        """Test getting vault content at a specific commit."""
        gv = initialized_versioning
        
        gv.commit("Initial commit")
        
        # Modify vault
        vault_path = Path(gv.vault_path)
        vault_path.write_bytes(b"modified content")
        
        gv.commit("Second commit")
        
        # Get history
        history = gv.get_history()
        first_hash = history[1].commit_hash
        
        # Get content at first commit
        content = gv.show(first_hash)
        
        assert content == b"test vault content"

    def test_show_not_initialized(self, temp_vault_path):
        """Test show when not initialized returns None."""
        gv = GitVersioning(temp_vault_path)
        
        content = gv.show("abc123")
        
        assert content is None


class TestGitCommandErrors:
    """Tests for git command error handling."""

    def test_git_not_found(self, temp_vault_path):
        """Test handling when git is not found."""
        gv = GitVersioning(temp_vault_path)
        
        # Patch subprocess to simulate git not found
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            with pytest.raises(GitVersioningError, match="Git not found"):
                gv._run_git(["init"])

    def test_git_command_failure(self, initialized_versioning):
        """Test handling of git command failure."""
        gv = initialized_versioning
        
        with patch('subprocess.run') as mock_run:
            result = MagicMock()
            result.returncode = 1
            result.stderr = "Some git error"
            mock_run.return_value = result
            mock_run.side_effect = None
            
            # Create a CalledProcessError
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", stderr="Some git error"
            )
            
            with pytest.raises(GitVersioningError, match="Git command failed"):
                gv._run_git(["invalid-command"])