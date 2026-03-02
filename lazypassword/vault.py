"""
Vault management for lazypassword.
Handles encrypted storage of password entries with atomic writes.
"""

import json
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.exceptions import InvalidTag

from lazypassword.crypto import (
    derive_key,
    encrypt,
    decrypt,
    generate_salt,
    secure_wipe,
)


VAULT_VERSION = 1
NONCE_SALT_SIZE = 32  # Combined salt + encrypted data


class VaultError(Exception):
    """Base exception for vault operations."""
    pass


class VaultCorruptedError(VaultError):
    """Raised when vault file is corrupted or invalid."""
    pass


class VaultAuthError(VaultError):
    """Raised when password is incorrect."""
    pass


class Vault:
    """
    Encrypted vault for storing password entries.
    
    The vault file format:
    - First 32 bytes: salt for key derivation
    - Remaining bytes: encrypted JSON data (nonce + ciphertext + tag)
    """
    
    def __init__(self, vault_path: str):
        """
        Initialize vault instance.
        
        Args:
            vault_path: Path to the vault file
        """
        self.vault_path = Path(vault_path)
        self._key: Optional[bytes] = None
        self._salt: Optional[bytes] = None
        self._data: dict = {}
        self._locked = True
    
    def create(self, password: str) -> None:
        """
        Create a new vault with encrypted empty structure.
        
        Args:
            password: Master password for the vault
        """
        self._salt = generate_salt()
        self._key = derive_key(password, self._salt)
        
        # Initialize empty vault structure
        self._data = {
            "version": VAULT_VERSION,
            "entries": [],
            "settings": {
                "auto_lock_timeout": 300,  # 5 minutes
                "clipboard_clear_delay": 30,  # 30 seconds
                "theme": "dark",  # default theme
            }
        }
        
        self._locked = False
        self.save()
    
    def unlock(self, password: str) -> bool:
        """
        Unlock the vault with the provided password.
        
        Args:
            password: Master password to attempt
            
        Returns:
            bool: True if unlock succeeded, False otherwise
        """
        if not self.vault_path.exists():
            return False
        
        try:
            with open(self.vault_path, 'rb') as f:
                file_content = f.read()
            
            if len(file_content) < NONCE_SALT_SIZE + 28:
                raise VaultCorruptedError("Vault file is too small or corrupted")
            
            # Extract salt and encrypted data
            salt = file_content[:NONCE_SALT_SIZE]
            encrypted_data = file_content[NONCE_SALT_SIZE:]
            
            # Derive key and attempt decryption
            key = derive_key(password, salt)
            
            try:
                decrypted = decrypt(encrypted_data, key)
                vault_data = json.loads(decrypted.decode('utf-8'))
                
                # Validate vault structure
                if "version" not in vault_data or "entries" not in vault_data:
                    secure_wipe(bytearray(key))
                    raise VaultCorruptedError("Invalid vault structure")
                
                # Success - store unlocked state
                self._salt = salt
                self._key = key
                self._data = vault_data
                self._locked = False
                return True
                
            except (ValueError, InvalidTag) as e:
                # Decryption failed - wrong password or corrupted
                secure_wipe(bytearray(key))
                return False
                
        except (IOError, OSError) as e:
            raise VaultError(f"Failed to read vault file: {e}")
        except json.JSONDecodeError as e:
            raise VaultCorruptedError(f"Invalid vault data: {e}")
    
    def lock(self) -> None:
        """Lock the vault and securely wipe decrypted data from memory."""
        if self._key:
            secure_wipe(bytearray(self._key))
            self._key = None
        
        self._data = {}
        self._locked = True
    
    def is_locked(self) -> bool:
        """Check if the vault is currently locked."""
        return self._locked
    
    def _ensure_unlocked(self) -> None:
        """Raise error if vault is locked."""
        if self._locked:
            raise VaultError("Vault is locked. Unlock first.")
    
    def _generate_entry_id(self) -> str:
        """Generate a unique entry ID."""
        return str(uuid.uuid4())
    
    def _get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    def add_entry(self, entry: dict) -> str:
        """
        Add a new entry to the vault.
        
        Args:
            entry: Dictionary with entry data (title, username, password, etc.)
            
        Returns:
            str: The generated entry ID
        """
        self._ensure_unlocked()
        
        entry_id = self._generate_entry_id()
        timestamp = self._get_timestamp()
        
        new_entry = {
            "id": entry_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            **entry
        }
        
        self._data["entries"].append(new_entry)
        return entry_id
    
    def update_entry(self, entry_id: str, entry: dict) -> None:
        """
        Update an existing entry.
        
        Args:
            entry_id: ID of the entry to update
            entry: Dictionary with updated fields
            
        Raises:
            VaultError: If entry not found
        """
        self._ensure_unlocked()
        
        for i, existing in enumerate(self._data["entries"]):
            if existing.get("id") == entry_id:
                # Merge updates, preserve id and created_at
                updated = {
                    **existing,
                    **entry,
                    "id": entry_id,  # Prevent ID change
                    "created_at": existing["created_at"],
                    "updated_at": self._get_timestamp(),
                }
                self._data["entries"][i] = updated
                return
        
        raise VaultError(f"Entry with ID '{entry_id}' not found")
    
    def delete_entry(self, entry_id: str) -> None:
        """
        Delete an entry from the vault.
        
        Args:
            entry_id: ID of the entry to delete
            
        Raises:
            VaultError: If entry not found
        """
        self._ensure_unlocked()
        
        for i, entry in enumerate(self._data["entries"]):
            if entry.get("id") == entry_id:
                del self._data["entries"][i]
                return
        
        raise VaultError(f"Entry with ID '{entry_id}' not found")
    
    def get_entries(self) -> list:
        """
        Get all entries from the vault.
        
        Returns:
            list: List of entry dictionaries
        """
        self._ensure_unlocked()
        return list(self._data.get("entries", []))
    
    def search(self, query: str) -> list:
        """
        Search entries by query string.
        
        Args:
            query: Search string (case-insensitive)
            
        Returns:
            list: Matching entries
        """
        self._ensure_unlocked()
        
        if not query:
            return self.get_entries()
        
        query_lower = query.lower()
        results = []
        
        for entry in self._data.get("entries", []):
            # Search in title, username, url, notes
            searchable_fields = [
                entry.get("title", ""),
                entry.get("username", ""),
                entry.get("url", ""),
                entry.get("notes", ""),
            ]
            
            if any(query_lower in field.lower() for field in searchable_fields):
                results.append(entry)
        
        return results
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value from the vault.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        self._ensure_unlocked()
        return self._data.get("settings", {}).get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a setting value in the vault.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self._ensure_unlocked()
        if "settings" not in self._data:
            self._data["settings"] = {}
        self._data["settings"][key] = value
    
    def get_theme(self) -> str:
        """Get the current theme name."""
        return self.get_setting("theme", "dark")
    
    def set_theme(self, theme: str) -> None:
        """
        Set the theme name.
        
        Args:
            theme: Theme name (e.g., 'dark', 'light', 'nord', etc.)
        """
        self.set_setting("theme", theme)
    
    def save(self) -> None:
        """
        Save the vault to disk with atomic write and backup.
        """
        self._ensure_unlocked()
        
        if not self._key or not self._salt:
            raise VaultError("Cannot save: vault not properly initialized")
        
        # Serialize and encrypt
        json_data = json.dumps(self._data, separators=(',', ':')).encode('utf-8')
        encrypted = encrypt(json_data, self._key)
        
        # Combine salt + encrypted data
        file_content = self._salt + encrypted
        
        # Ensure parent directory exists
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create backup if file exists
        if self.vault_path.exists():
            backup_path = self.vault_path.with_suffix('.vault.bak')
            try:
                shutil.copy2(self.vault_path, backup_path)
            except (IOError, OSError):
                pass  # Best effort backup
        
        # Atomic write: write to temp file, then rename
        try:
            fd, temp_path = tempfile.mkstemp(
                dir=self.vault_path.parent,
                prefix='.vault_tmp_'
            )
            try:
                os.write(fd, file_content)
                os.fsync(fd)  # Ensure data is written to disk
            finally:
                os.close(fd)
            
            # Atomic rename
            os.replace(temp_path, self.vault_path)
            
        except (IOError, OSError) as e:
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise VaultError(f"Failed to save vault: {e}")
