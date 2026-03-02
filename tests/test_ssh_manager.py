"""Tests for SSH key management."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from lazypassword.ssh_manager import SSHManager, SSHKey


@pytest.fixture
def mock_vault():
    """Create a mock vault for testing."""
    vault = MagicMock()
    vault.add_ssh_key = MagicMock()
    vault.get_ssh_keys = MagicMock(return_value=[])
    vault.get_ssh_key = MagicMock(return_value=None)
    vault.update_ssh_key = MagicMock()
    vault.delete_ssh_key = MagicMock(return_value=True)
    return vault


@pytest.fixture
def sample_ssh_key():
    """Create a sample SSH key for testing."""
    return SSHKey(
        id="test-key-id",
        name="Test Key",
        private_key="-----BEGIN OPENSSH PRIVATE KEY-----\ntest-private-key\n-----END OPENSSH PRIVATE KEY-----",
        public_key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDIhz2GK/XCUj4i6Q5yQJNL1MXMY0RxzPV2QrBqfHrDq test@example.com",
        key_type="ed25519",
        comment="test@example.com"
    )


class TestSSHKey:
    """Tests for SSHKey dataclass."""

    def test_ssh_key_creation(self):
        """Test SSHKey creation."""
        key = SSHKey(
            id="test-id",
            name="My Key",
            private_key="private",
            public_key="public",
            key_type="ed25519",
            comment="test comment"
        )
        
        assert key.id == "test-id"
        assert key.name == "My Key"
        assert key.private_key == "private"
        assert key.public_key == "public"
        assert key.key_type == "ed25519"
        assert key.comment == "test comment"
        assert key.passphrase == ""  # Default

    def test_ssh_key_to_dict(self, sample_ssh_key):
        """Test SSHKey to_dict conversion."""
        data = sample_ssh_key.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == "test-key-id"
        assert data["name"] == "Test Key"
        assert data["key_type"] == "ed25519"

    def test_ssh_key_from_dict(self):
        """Test SSHKey from_dict conversion."""
        data = {
            "id": "test-id",
            "name": "Test Key",
            "private_key": "private",
            "public_key": "public",
            "key_type": "rsa",
            "comment": "test",
            "passphrase": "secret",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        key = SSHKey.from_dict(data)
        
        assert key.id == "test-id"
        assert key.name == "Test Key"
        assert key.key_type == "rsa"
        assert key.passphrase == "secret"


class TestGenerateKeypair:
    """Tests for SSH key pair generation."""

    def test_generate_ed25519_keypair(self):
        """Test generation of ed25519 key pair."""
        private_key, public_key = SSHKey.generate_keypair("ed25519", "test comment")
        
        # Check formats
        assert "BEGIN OPENSSH PRIVATE KEY" in private_key
        assert public_key.startswith("ssh-ed25519")
        assert "test comment" in public_key

    def test_generate_rsa_keypair(self):
        """Test generation of RSA key pair."""
        private_key, public_key = SSHKey.generate_keypair("rsa", "rsa comment")
        
        # Check formats
        assert "BEGIN RSA PRIVATE KEY" in private_key or "BEGIN OPENSSH PRIVATE KEY" in private_key
        assert public_key.startswith("ssh-rsa")
        assert "rsa comment" in public_key

    def test_generate_keypair_invalid_type(self):
        """Test that invalid key type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported key type"):
            SSHKey.generate_keypair("invalid_type")


class TestSSHManagerInit:
    """Tests for SSHManager initialization."""

    def test_ssh_manager_init(self, mock_vault):
        """Test SSHManager initialization."""
        manager = SSHManager(mock_vault)
        
        assert manager.vault == mock_vault


class TestGenerateAndAddKey:
    """Tests for generating and adding keys."""

    def test_generate_keypair_and_store(self, mock_vault):
        """Test generating a new key pair and storing it."""
        manager = SSHManager(mock_vault)
        
        key = manager.generate_keypair("My New Key", "ed25519", "my comment")
        
        assert isinstance(key, SSHKey)
        assert key.name == "My New Key"
        assert key.key_type == "ed25519"
        assert key.comment == "my comment"
        assert key.id is not None
        
        # Should have been added to vault
        mock_vault.add_ssh_key.assert_called_once()

    def test_add_existing_key(self, mock_vault):
        """Test adding an existing key."""
        manager = SSHManager(mock_vault)
        
        key = manager.add_existing_key(
            name="Existing Key",
            private_key="private content",
            public_key="public content",
            key_type="ed25519",
            comment="existing"
        )
        
        assert key.name == "Existing Key"
        assert key.private_key == "private content"
        mock_vault.add_ssh_key.assert_called_once()


class TestGetKey:
    """Tests for retrieving keys."""

    def test_get_key(self, mock_vault):
        """Test getting a key by ID."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Key 1",
                "private_key": "priv1",
                "public_key": "pub1",
                "key_type": "ed25519"
            },
            {
                "id": "key-2",
                "name": "Key 2",
                "private_key": "priv2",
                "public_key": "pub2",
                "key_type": "ed25519"
            }
        ]
        
        manager = SSHManager(mock_vault)
        key = manager.get_key("key-2")
        
        assert key is not None
        assert key.name == "Key 2"
        assert key.id == "key-2"

    def test_get_key_not_found(self, mock_vault):
        """Test getting a non-existent key returns None."""
        mock_vault.get_ssh_keys.return_value = []
        
        manager = SSHManager(mock_vault)
        key = manager.get_key("nonexistent")
        
        assert key is None

    def test_list_keys(self, mock_vault):
        """Test listing all keys."""
        mock_vault.get_ssh_keys.return_value = [
            {"id": "key-1", "name": "Key 1", "private_key": "priv", "public_key": "pub", "key_type": "ed25519"},
            {"id": "key-2", "name": "Key 2", "private_key": "priv", "public_key": "pub", "key_type": "ed25519"}
        ]
        
        manager = SSHManager(mock_vault)
        keys = manager.list_keys()
        
        assert len(keys) == 2
        assert all(isinstance(k, SSHKey) for k in keys)


class TestDeleteKey:
    """Tests for deleting keys."""

    def test_delete_key(self, mock_vault):
        """Test deleting a key."""
        manager = SSHManager(mock_vault)
        
        result = manager.delete_key("key-to-delete")
        
        assert result == True
        mock_vault.delete_ssh_key.assert_called_once_with("key-to-delete")

    def test_delete_key_not_found(self, mock_vault):
        """Test deleting a non-existent key returns False."""
        mock_vault.delete_ssh_key.return_value = False
        
        manager = SSHManager(mock_vault)
        result = manager.delete_key("nonexistent")
        
        assert result == False


class TestExportKey:
    """Tests for exporting keys to files."""

    def test_export_private_key(self, mock_vault, tmp_path):
        """Test exporting private key to file."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private-key-content",
                "public_key": "public-key-content",
                "key_type": "ed25519"
            }
        ]
        
        manager = SSHManager(mock_vault)
        export_path = tmp_path / "exported_key"
        
        result = manager.export_private_key("key-1", str(export_path))
        
        assert result == True
        assert export_path.exists()
        assert export_path.read_text() == "private-key-content"
        # Check permissions (600 on Unix)
        if os.name != 'nt':
            assert oct(export_path.stat().st_mode)[-3:] == '600'

    def test_export_private_key_not_found(self, mock_vault):
        """Test exporting non-existent key raises error."""
        mock_vault.get_ssh_keys.return_value = []
        
        manager = SSHManager(mock_vault)
        
        with pytest.raises(ValueError, match="not found"):
            manager.export_private_key("nonexistent", "/tmp/test")

    def test_export_public_key(self, mock_vault, tmp_path):
        """Test exporting public key to file."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private",
                "public_key": "public-key-content",
                "key_type": "ed25519"
            }
        ]
        
        manager = SSHManager(mock_vault)
        export_path = tmp_path / "exported_key.pub"
        
        result = manager.export_public_key("key-1", str(export_path))
        
        assert result == True
        assert export_path.exists()
        assert export_path.read_text() == "public-key-content"
        # Check permissions (644 on Unix)
        if os.name != 'nt':
            assert oct(export_path.stat().st_mode)[-3:] == '644'


class TestGetFingerprint:
    """Tests for getting key fingerprints."""

    @patch('subprocess.run')
    def test_get_key_fingerprint(self, mock_run, mock_vault, tmp_path):
        """Test getting key fingerprint."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private",
                "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test@example.com",
                "key_type": "ed25519"
            }
        ]
        
        # Mock ssh-keygen output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="256 SHA256:abcdef123456 test@example.com (ED25519)\n"
        )
        
        manager = SSHManager(mock_vault)
        fingerprint = manager.get_key_fingerprint("key-1")
        
        assert "SHA256" in fingerprint

    @patch('subprocess.run')
    def test_get_key_fingerprint_md5(self, mock_run, mock_vault):
        """Test getting MD5 fingerprint."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private",
                "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test@example.com",
                "key_type": "ed25519"
            }
        ]
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="256 MD5:aa:bb:cc:dd test@example.com (ED25519)\n"
        )
        
        manager = SSHManager(mock_vault)
        fingerprint = manager.get_key_fingerprint("key-1", hash_type="md5")
        
        assert "MD5" in fingerprint


class TestAddToSSHAgent:
    """Tests for adding keys to ssh-agent."""

    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_add_to_ssh_agent(self, mock_temp, mock_run, mock_vault):
        """Test adding key to ssh-agent."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private-key",
                "public_key": "public",
                "key_type": "ed25519",
                "passphrase": ""
            }
        ]
        
        # Mock temp file
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_key"
        mock_temp.return_value.__enter__.return_value = mock_file
        
        # Mock ssh-add -l (agent running)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=""),  # ssh-add -l
            MagicMock(returncode=0, stdout="", stderr="")  # ssh-add
        ]
        
        manager = SSHManager(mock_vault)
        result = manager.add_to_ssh_agent("key-1")
        
        assert result == True

    @patch('subprocess.run')
    def test_add_to_ssh_agent_not_running(self, mock_run, mock_vault):
        """Test adding key when ssh-agent is not running."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "private",
                "public_key": "public",
                "key_type": "ed25519"
            }
        ]
        
        # Mock ssh-add -l returns 2 (agent not running)
        mock_run.return_value = MagicMock(returncode=2)
        
        manager = SSHManager(mock_vault)
        
        with pytest.raises(RuntimeError, match="ssh-agent is not running"):
            manager.add_to_ssh_agent("key-1")


class TestGetKeyInfo:
    """Tests for getting key information."""

    @patch('subprocess.run')
    def test_get_key_info(self, mock_run, mock_vault):
        """Test getting comprehensive key info."""
        mock_vault.get_ssh_keys.return_value = [
            {
                "id": "key-1",
                "name": "Test Key",
                "private_key": "-----BEGIN KEY-----\nprivate-key-content\n-----END KEY-----",
                "public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test@example.com",
                "key_type": "ed25519",
                "comment": "test@example.com",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-02T00:00:00"
            }
        ]
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="256 SHA256:abcdef test@example.com (ED25519)\n"
        )
        
        manager = SSHManager(mock_vault)
        info = manager.get_key_info("key-1")
        
        assert info["id"] == "key-1"
        assert info["name"] == "Test Key"
        assert info["key_type"] == "ed25519"
        assert info["has_passphrase"] == False
        assert info["public_key"] == "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test@example.com"
        assert "private_key_masked" in info
        assert info["sha256_fingerprint"] is not None