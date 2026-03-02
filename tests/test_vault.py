"""Tests for vault operations."""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from lazypassword.vault import (
    Vault, VaultError, VaultCorruptedError, VaultAuthError,
    VAULT_VERSION, NONCE_SALT_SIZE
)


@pytest.fixture
def temp_vault_path(tmp_path):
    """Create a temporary path for vault file."""
    return str(tmp_path / "test.vault")


@pytest.fixture
def temp_keyfile(tmp_path):
    """Create a temporary keyfile."""
    keyfile_path = tmp_path / "keyfile.bin"
    keyfile_path.write_bytes(b"test_keyfile_content_12345")
    return str(keyfile_path)


@pytest.fixture
def unlocked_vault(temp_vault_path):
    """Create and unlock a vault for testing."""
    vault = Vault(temp_vault_path)
    vault.create("master_password")
    return vault


class TestVaultCreation:
    """Tests for vault creation."""

    def test_create_vault(self, temp_vault_path):
        """Test that vault can be created successfully."""
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        
        # Vault file should exist
        assert Path(temp_vault_path).exists()
        
        # Vault should be unlocked after creation
        assert not vault.is_locked()
        
        # Vault should have correct structure
        entries = vault.get_entries()
        assert entries == []
        
        # Should have default settings
        assert vault.get_setting("theme") == "dark"
        assert vault.get_setting("auto_lock_timeout") == 300
        assert vault.get_setting("clipboard_clear_delay") == 30

    def test_create_vault_with_keyfile(self, temp_vault_path, temp_keyfile):
        """Test vault creation with keyfile."""
        vault = Vault(temp_vault_path)
        vault.create("master_password", keyfile_path=temp_keyfile)
        
        assert Path(temp_vault_path).exists()
        assert not vault.is_locked()
        
        # Should have keyfile settings
        assert vault.get_setting("has_keyfile") == True
        assert vault.get_setting("keyfile_hash") is not None

    def test_create_vault_creates_parent_dirs(self, tmp_path):
        """Test that creating vault creates parent directories."""
        nested_path = tmp_path / "nested" / "deep" / "vault.vault"
        vault = Vault(str(nested_path))
        vault.create("password")
        
        assert nested_path.exists()


class TestVaultUnlock:
    """Tests for vault unlocking."""

    def test_unlock_vault(self, temp_vault_path):
        """Test that vault can be unlocked with correct password."""
        # Create vault
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        vault.lock()
        
        # Unlock
        result = vault.unlock("master_password")
        
        assert result == True
        assert not vault.is_locked()

    def test_wrong_password(self, temp_vault_path):
        """Test that wrong password returns False."""
        # Create vault
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        vault.lock()
        
        # Try wrong password
        result = vault.unlock("wrong_password")
        
        assert result == False
        assert vault.is_locked()

    def test_unlock_with_keyfile(self, temp_vault_path, temp_keyfile):
        """Test unlocking vault with keyfile."""
        # Create vault with keyfile
        vault = Vault(temp_vault_path)
        vault.create("master_password", keyfile_path=temp_keyfile)
        vault.lock()
        
        # Unlock with keyfile
        result = vault.unlock("master_password", keyfile_path=temp_keyfile)
        
        assert result == True
        assert not vault.is_locked()

    def test_unlock_without_keyfile_when_required(self, temp_vault_path, temp_keyfile):
        """Test that unlocking without keyfile fails when keyfile is required."""
        # Create vault with keyfile
        vault = Vault(temp_vault_path)
        vault.create("master_password", keyfile_path=temp_keyfile)
        vault.lock()
        
        # Try unlock without keyfile - this actually works in current implementation
        # because the key is derived from password only, but validation happens after
        result = vault.unlock("master_password")
        
        # Should fail because keyfile hash check fails
        assert result == False

    def test_unlock_with_wrong_keyfile(self, temp_vault_path, temp_keyfile, tmp_path):
        """Test that unlocking with wrong keyfile fails."""
        # Create vault with keyfile
        vault = Vault(temp_vault_path)
        vault.create("master_password", keyfile_path=temp_keyfile)
        vault.lock()
        
        # Create different keyfile
        wrong_keyfile = tmp_path / "wrong_keyfile.bin"
        wrong_keyfile.write_bytes(b"wrong_content")
        
        # Try unlock with wrong keyfile
        result = vault.unlock("master_password", keyfile_path=str(wrong_keyfile))
        
        assert result == False

    def test_unlock_nonexistent_vault(self, temp_vault_path):
        """Test unlocking non-existent vault returns False."""
        vault = Vault(temp_vault_path)
        
        result = vault.unlock("any_password")
        
        assert result == False

    def test_unlock_corrupted_vault(self, temp_vault_path):
        """Test that corrupted vault raises VaultCorruptedError."""
        # Create corrupted vault file
        Path(temp_vault_path).write_bytes(b"too short")
        
        vault = Vault(temp_vault_path)
        
        with pytest.raises(VaultCorruptedError):
            vault.unlock("password")


class TestVaultOperations:
    """Tests for vault operations."""

    def test_add_entry(self, unlocked_vault):
        """Test adding an entry to vault."""
        entry = {
            "title": "Test Entry",
            "username": "testuser",
            "password": "testpass",
            "url": "https://example.com",
            "notes": "Test notes"
        }
        
        entry_id = unlocked_vault.add_entry(entry)
        
        assert isinstance(entry_id, str)
        assert len(entry_id) > 0
        
        entries = unlocked_vault.get_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "Test Entry"
        assert entries[0]["username"] == "testuser"
        assert entries[0]["id"] == entry_id

    def test_update_entry(self, unlocked_vault):
        """Test updating an existing entry."""
        # Add entry
        entry_id = unlocked_vault.add_entry({
            "title": "Original Title",
            "username": "original_user",
            "password": "original_pass"
        })
        
        # Update entry
        unlocked_vault.update_entry(entry_id, {
            "title": "Updated Title",
            "password": "updated_pass"
        })
        
        entries = unlocked_vault.get_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "Updated Title"
        assert entries[0]["username"] == "original_user"  # Unchanged
        assert entries[0]["password"] == "updated_pass"

    def test_update_entry_not_found(self, unlocked_vault):
        """Test that updating non-existent entry raises error."""
        with pytest.raises(VaultError, match="not found"):
            unlocked_vault.update_entry("nonexistent-id", {"title": "New Title"})

    def test_delete_entry(self, unlocked_vault):
        """Test deleting an entry."""
        # Add entries
        entry_id1 = unlocked_vault.add_entry({"title": "Entry 1"})
        entry_id2 = unlocked_vault.add_entry({"title": "Entry 2"})
        
        # Delete first entry
        unlocked_vault.delete_entry(entry_id1)
        
        entries = unlocked_vault.get_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "Entry 2"

    def test_delete_entry_not_found(self, unlocked_vault):
        """Test that deleting non-existent entry raises error."""
        with pytest.raises(VaultError, match="not found"):
            unlocked_vault.delete_entry("nonexistent-id")

    def test_search(self, unlocked_vault):
        """Test searching entries."""
        # Add entries
        unlocked_vault.add_entry({
            "title": "GitHub Account",
            "username": "myuser",
            "url": "https://github.com"
        })
        unlocked_vault.add_entry({
            "title": "Gmail",
            "username": "myuser@gmail.com",
            "url": "https://gmail.com"
        })
        unlocked_vault.add_entry({
            "title": "Bank Account",
            "username": "banker",
            "url": "https://bank.com"
        })
        
        # Search by title
        results = unlocked_vault.search("git")
        assert len(results) == 1
        assert results[0]["title"] == "GitHub Account"
        
        # Search by username
        results = unlocked_vault.search("myuser")
        assert len(results) == 2
        
        # Search by URL
        results = unlocked_vault.search("gmail")
        assert len(results) == 1
        
        # Case insensitive search
        results = unlocked_vault.search("GITHUB")
        assert len(results) == 1
        
        # Empty search returns all
        results = unlocked_vault.search("")
        assert len(results) == 3

    def test_search_no_matches(self, unlocked_vault):
        """Test search with no matches."""
        unlocked_vault.add_entry({"title": "Test Entry"})
        
        results = unlocked_vault.search("nonexistent")
        assert len(results) == 0


class TestVaultSaveAndLoad:
    """Tests for vault persistence."""

    def test_save_and_load(self, temp_vault_path):
        """Test that vault can be saved and loaded."""
        # Create and populate vault
        vault1 = Vault(temp_vault_path)
        vault1.create("master_password")
        entry_id = vault1.add_entry({
            "title": "Test Entry",
            "username": "testuser",
            "password": "testpass"
        })
        vault1.save()  # Explicitly save before locking
        vault1.lock()
        
        # Load vault in new instance
        vault2 = Vault(temp_vault_path)
        result = vault2.unlock("master_password")
        
        assert result == True
        entries = vault2.get_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "Test Entry"

    def test_save_creates_backup(self, temp_vault_path):
        """Test that saving creates a backup."""
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        vault.add_entry({"title": "Entry 1"})
        
        # Save again (creates backup)
        vault.save()
        
        backup_path = Path(temp_vault_path).with_suffix('.vault.bak')
        assert backup_path.exists()


class TestCorruptedVault:
    """Tests for corrupted vault handling."""

    def test_corrupted_vault_invalid_json(self, temp_vault_path):
        """Test handling of corrupted vault data."""
        # Create a vault
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        vault.lock()
        
        # Corrupt the file by modifying encrypted bytes
        with open(temp_vault_path, 'rb') as f:
            data = f.read()
        
        # Corrupt after salt
        corrupted = data[:NONCE_SALT_SIZE] + b"\x00" * (len(data) - NONCE_SALT_SIZE)
        
        with open(temp_vault_path, 'wb') as f:
            f.write(corrupted)
        
        # Try to unlock - should fail but not crash
        vault2 = Vault(temp_vault_path)
        result = vault2.unlock("master_password")
        assert result == False

    def test_corrupted_vault_too_short(self, temp_vault_path):
        """Test handling of truncated vault file."""
        # Create a file that's too short
        Path(temp_vault_path).write_bytes(b"short")
        
        vault = Vault(temp_vault_path)
        
        with pytest.raises(VaultCorruptedError):
            vault.unlock("password")


class TestVaultSettings:
    """Tests for vault settings."""

    def test_settings_theme(self, unlocked_vault):
        """Test theme setting."""
        assert unlocked_vault.get_setting("theme") == "dark"
        
        unlocked_vault.set_setting("theme", "light")
        assert unlocked_vault.get_setting("theme") == "light"
        
        # Test via dedicated method
        assert unlocked_vault.get_theme() == "light"
        
        unlocked_vault.set_theme("nord")
        assert unlocked_vault.get_theme() == "nord"

    def test_settings_timeouts(self, unlocked_vault):
        """Test timeout settings."""
        assert unlocked_vault.get_setting("auto_lock_timeout") == 300
        assert unlocked_vault.get_setting("clipboard_clear_delay") == 30
        
        unlocked_vault.set_setting("auto_lock_timeout", 600)
        unlocked_vault.set_setting("clipboard_clear_delay", 60)
        
        assert unlocked_vault.get_setting("auto_lock_timeout") == 600
        assert unlocked_vault.get_setting("clipboard_clear_delay") == 60

    def test_settings_default_value(self, unlocked_vault):
        """Test that missing settings return default."""
        assert unlocked_vault.get_setting("nonexistent_key", "default") == "default"


class TestVaultKeyfileIntegration:
    """Tests for keyfile integration."""

    def test_keyfile_integration(self, temp_vault_path, temp_keyfile):
        """Test full keyfile integration workflow."""
        # Create vault with keyfile
        vault1 = Vault(temp_vault_path)
        vault1.create("master_password", keyfile_path=temp_keyfile)
        vault1.add_entry({"title": "Secret Entry"})
        vault1.save()  # Explicitly save
        vault1.lock()
        
        # Check has_keyfile when locked (returns False since we can't decrypt)
        # but unlock should require keyfile
        vault2 = Vault(temp_vault_path)
        
        # Without keyfile should fail
        result = vault2.unlock("master_password")
        assert result == False
        
        # With keyfile should succeed
        result = vault2.unlock("master_password", keyfile_path=temp_keyfile)
        assert result == True
        
        entries = vault2.get_entries()
        assert len(entries) == 1
        assert entries[0]["title"] == "Secret Entry"

    def test_keyfile_path_storage(self, temp_vault_path, temp_keyfile):
        """Test that keyfile path can be stored."""
        vault = Vault(temp_vault_path)
        vault.create("master_password")
        
        vault.set_keyfile_path(temp_keyfile)
        assert vault.get_keyfile_path() == temp_keyfile