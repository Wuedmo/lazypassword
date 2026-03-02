"""Import and export functionality for lazypassword vault data.

Supports multiple formats:
- lazypassword: Native JSON format
- bitwarden: Bitwarden JSON export format
- chrome: Google Chrome Password Manager export format
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from enum import Enum

from lazypassword.entry import Entry


class ImportFormat(Enum):
    """Supported import formats."""
    LAZYPASSWORD = "lazypassword"
    BITWARDEN = "bitwarden"
    CHROME = "chrome"


class ImportError(Exception):
    """Base exception for import operations."""
    pass


class ExportError(Exception):
    """Base exception for export operations."""
    pass


class ValidationError(ImportError):
    """Raised when imported data fails validation."""
    pass


class DuplicateHandling(Enum):
    """How to handle duplicate entries during import."""
    SKIP = "skip"
    MERGE = "merge"
    REPLACE = "replace"


class VaultExporter:
    """Export vault data to various formats."""
    
    CURRENT_EXPORT_VERSION = 1
    
    def __init__(self, vault: Any):
        """
        Initialize exporter with a vault instance.
        
        Args:
            vault: The Vault instance to export from
        """
        self.vault = vault
    
    def export_to_json(
        self, 
        filepath: str, 
        include_passwords: bool = True,
        encrypt: bool = False,
        encryption_password: Optional[str] = None
    ) -> dict:
        """
        Export the entire vault to JSON format.
        
        Args:
            filepath: Path to save the export file
            include_passwords: Whether to include password fields
            encrypt: Whether to encrypt the export
            encryption_password: Password for encrypted export (required if encrypt=True)
            
        Returns:
            dict: Summary of the export operation
            
        Raises:
            ExportError: If export fails
        """
        if self.vault.is_locked():
            raise ExportError("Vault is locked. Unlock first.")
        
        if encrypt and not encryption_password:
            raise ExportError("Encryption password required when encrypt=True")
        
        entries = self.vault.get_entries()
        
        export_data = {
            "version": self.CURRENT_EXPORT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "lazypassword",
            "entries": []
        }
        
        for entry in entries:
            entry_data = dict(entry)
            if not include_passwords:
                entry_data["password"] = ""
            export_data["entries"].append(entry_data)
        
        # Encrypt if requested
        if encrypt:
            from lazypassword.crypto import derive_key, encrypt, generate_salt
            salt = generate_salt()
            key = derive_key(encryption_password, salt)
            json_data = json.dumps(export_data, separators=(',', ':')).encode('utf-8')
            encrypted = encrypt(json_data, key)
            file_content = salt + encrypted
        else:
            file_content = json.dumps(export_data, indent=2).encode('utf-8')
        
        # Write to file
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(file_content)
        except (IOError, OSError) as e:
            raise ExportError(f"Failed to write export file: {e}")
        
        return {
            "entries_exported": len(entries),
            "filepath": str(path.absolute()),
            "encrypted": encrypt,
            "includes_passwords": include_passwords
        }
    
    def export_entries(
        self, 
        entries: list,
        filepath: str,
        include_passwords: bool = True
    ) -> dict:
        """
        Export specific entries to JSON format.
        
        Args:
            entries: List of Entry objects or entry dictionaries to export
            filepath: Path to save the export file
            include_passwords: Whether to include password fields
            
        Returns:
            dict: Summary of the export operation
            
        Raises:
            ExportError: If export fails
        """
        export_data = {
            "version": self.CURRENT_EXPORT_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "lazypassword-entries",
            "entries": []
        }
        
        for entry in entries:
            if isinstance(entry, Entry):
                entry_data = entry.to_dict()
            else:
                entry_data = dict(entry)
            
            if not include_passwords:
                entry_data["password"] = ""
            export_data["entries"].append(entry_data)
        
        # Write to file
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
        except (IOError, OSError) as e:
            raise ExportError(f"Failed to write export file: {e}")
        
        return {
            "entries_exported": len(entries),
            "filepath": str(path.absolute()),
            "includes_passwords": include_passwords
        }
    
    def export_to_bitwarden(self, filepath: str) -> dict:
        """
        Export vault to Bitwarden JSON format.
        
        Args:
            filepath: Path to save the export file
            
        Returns:
            dict: Summary of the export operation
        """
        if self.vault.is_locked():
            raise ExportError("Vault is locked. Unlock first.")
        
        entries = self.vault.get_entries()
        
        # Bitwarden format
        bw_export = {
            "encrypted": False,
            "folders": [],
            "items": []
        }
        
        folder_map = {}  # Map tags to folder IDs
        folder_id = 0
        
        for entry in entries:
            # Create folders from tags
            entry_folders = []
            for tag in entry.get("tags", []):
                if tag not in folder_map:
                    folder_id += 1
                    folder_map[tag] = str(folder_id)
                    bw_export["folders"].append({
                        "id": str(folder_id),
                        "name": tag
                    })
                entry_folders.append(folder_map[tag])
            
            bw_item = {
                "id": entry.get("id", str(uuid.uuid4())),
                "type": 1,  # Login type
                "name": entry.get("title", ""),
                "notes": entry.get("notes", ""),
                "favorite": False,
                "folderId": entry_folders[0] if entry_folders else None,
                "login": {
                    "username": entry.get("username", ""),
                    "password": entry.get("password", ""),
                    "uris": [
                        {"match": None, "uri": entry.get("url", "")}
                    ] if entry.get("url") else []
                },
                "collectionIds": None
            }
            bw_export["items"].append(bw_item)
        
        # Write to file
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(bw_export, f, indent=2)
        except (IOError, OSError) as e:
            raise ExportError(f"Failed to write export file: {e}")
        
        return {
            "entries_exported": len(entries),
            "filepath": str(path.absolute()),
            "format": "bitwarden"
        }


class VaultImporter:
    """Import vault data from various formats."""
    
    @staticmethod
    def import_from_json(filepath: str, encryption_password: Optional[str] = None) -> dict:
        """
        Parse a JSON file and return its contents.
        
        Args:
            filepath: Path to the JSON file
            encryption_password: Password if file is encrypted
            
        Returns:
            dict: Parsed JSON data
            
        Raises:
            ImportError: If file cannot be read or parsed
            ValidationError: If file format is invalid
        """
        path = Path(filepath)
        
        if not path.exists():
            raise ImportError(f"File not found: {filepath}")
        
        try:
            with open(path, 'rb') as f:
                file_content = f.read()
        except (IOError, OSError) as e:
            raise ImportError(f"Failed to read file: {e}")
        
        # Check if encrypted (first bytes look like salt)
        if len(file_content) > 64 and encryption_password:
            try:
                from lazypassword.crypto import derive_key, decrypt
                salt = file_content[:32]
                encrypted_data = file_content[32:]
                key = derive_key(encryption_password, salt)
                decrypted = decrypt(encrypted_data, key)
                data = json.loads(decrypted.decode('utf-8'))
            except Exception as e:
                raise ImportError(f"Failed to decrypt file: {e}")
        else:
            try:
                data = json.loads(file_content.decode('utf-8'))
            except json.JSONDecodeError as e:
                raise ImportError(f"Invalid JSON: {e}")
        
        return data
    
    def detect_format(self, data: dict) -> ImportFormat:
        """
        Detect the format of imported data.
        
        Args:
            data: The parsed JSON data
            
        Returns:
            ImportFormat: Detected format
        """
        # Check for lazypassword format
        if "format" in data and data["format"] in ["lazypassword", "lazypassword-entries"]:
            return ImportFormat.LAZYPASSWORD
        if "version" in data and "entries" in data and isinstance(data["entries"], list):
            if "items" not in data:  # Bitwarden also has items
                return ImportFormat.LAZYPASSWORD
        
        # Check for Bitwarden format
        if "items" in data and isinstance(data["items"], list):
            return ImportFormat.BITWARDEN
        
        # Check for Chrome format
        if isinstance(data, list) and len(data) > 0:
            if all(key in data[0] for key in ["name", "url", "username", "password"]):
                return ImportFormat.CHROME
        
        raise ValidationError("Unable to detect import format")
    
    def validate_lazypassword_format(self, data: dict) -> bool:
        """
        Validate lazypassword format data.
        
        Args:
            data: The parsed JSON data
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Data must be a JSON object")
        
        if "entries" not in data:
            raise ValidationError("Missing 'entries' field")
        
        if not isinstance(data["entries"], list):
            raise ValidationError("'entries' must be a list")
        
        for i, entry in enumerate(data["entries"]):
            if not isinstance(entry, dict):
                raise ValidationError(f"Entry {i} is not an object")
            
            # Check required fields
            if "title" not in entry:
                raise ValidationError(f"Entry {i} missing 'title' field")
        
        return True
    
    def validate_bitwarden_format(self, data: dict) -> bool:
        """
        Validate Bitwarden format data.
        
        Args:
            data: The parsed JSON data
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Data must be a JSON object")
        
        if "items" not in data:
            raise ValidationError("Missing 'items' field")
        
        if not isinstance(data["items"], list):
            raise ValidationError("'items' must be a list")
        
        return True
    
    def validate_chrome_format(self, data: list) -> bool:
        """
        Validate Chrome format data.
        
        Args:
            data: The parsed JSON data (list)
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If data is invalid
        """
        if not isinstance(data, list):
            raise ValidationError("Chrome format must be a JSON array")
        
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                raise ValidationError(f"Entry {i} is not an object")
            
            if "name" not in entry and "url" not in entry:
                raise ValidationError(f"Entry {i} missing 'name' or 'url' field")
        
        return True
    
    def convert_bitwarden_to_entries(self, data: dict) -> list:
        """
        Convert Bitwarden format to lazypassword entries.
        
        Args:
            data: Bitwarden format data
            
        Returns:
            list: List of entry dictionaries
        """
        entries = []
        
        for item in data.get("items", []):
            # Only handle login items (type 1)
            if item.get("type") != 1:
                continue
            
            login = item.get("login", {})
            uris = login.get("uris", [])
            url = uris[0].get("uri", "") if uris else ""
            
            entry = {
                "id": str(uuid.uuid4()),
                "title": item.get("name", ""),
                "username": login.get("username", ""),
                "password": login.get("password", ""),
                "url": url,
                "notes": item.get("notes", ""),
                "tags": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            # Add folder/tag if present
            folder_id = item.get("folderId")
            if folder_id and data.get("folders"):
                for folder in data["folders"]:
                    if folder.get("id") == folder_id:
                        entry["tags"].append(folder.get("name", ""))
                        break
            
            entries.append(entry)
        
        return entries
    
    def convert_chrome_to_entries(self, data: list) -> list:
        """
        Convert Chrome format to lazypassword entries.
        
        Args:
            data: Chrome format data (list)
            
        Returns:
            list: List of entry dictionaries
        """
        entries = []
        
        for item in data:
            entry = {
                "id": str(uuid.uuid4()),
                "title": item.get("name", item.get("url", "Untitled")),
                "username": item.get("username", ""),
                "password": item.get("password", ""),
                "url": item.get("url", ""),
                "notes": "",
                "tags": ["imported-from-chrome"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            entries.append(entry)
        
        return entries
    
    def import_to_vault(
        self, 
        vault: Any, 
        filepath: str,
        format_hint: Optional[str] = None,
        merge: bool = False,
        duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP
    ) -> dict:
        """
        Import entries from a JSON file into a vault.
        
        Args:
            vault: The Vault instance to import into
            filepath: Path to the JSON file
            format_hint: Optional format hint ("lazypassword", "bitwarden", "chrome")
            merge: Whether to merge with existing entries or replace all
            duplicate_handling: How to handle duplicate entries
            
        Returns:
            dict: Summary of the import operation
            
        Raises:
            ImportError: If import fails
            ValidationError: If data format is invalid
        """
        if vault.is_locked():
            raise ImportError("Vault is locked. Unlock first.")
        
        # Parse the file
        data = self.import_from_json(filepath)
        
        # Detect or use specified format
        if format_hint:
            try:
                import_format = ImportFormat(format_hint.lower())
            except ValueError:
                raise ValidationError(f"Unknown format: {format_hint}")
        else:
            import_format = self.detect_format(data)
        
        # Validate and convert based on format
        if import_format == ImportFormat.LAZYPASSWORD:
            self.validate_lazypassword_format(data)
            entries = data.get("entries", [])
        elif import_format == ImportFormat.BITWARDEN:
            self.validate_bitwarden_format(data)
            entries = self.convert_bitwarden_to_entries(data)
        elif import_format == ImportFormat.CHROME:
            self.validate_chrome_format(data)
            entries = self.convert_chrome_to_entries(data)
        else:
            raise ValidationError(f"Unsupported format: {import_format}")
        
        # Get existing entries for duplicate detection
        existing_entries = vault.get_entries()
        existing_set = set()
        for e in existing_entries:
            key = (e.get("title", "").lower(), e.get("username", "").lower(), e.get("url", "").lower())
            existing_set.add(key)
        
        # Import entries
        stats = {
            "added": 0,
            "skipped": 0,
            "merged": 0,
            "replaced": 0,
            "total": len(entries)
        }
        
        if not merge:
            # Clear existing entries if not merging
            for entry in existing_entries[:]:
                vault.delete_entry(entry["id"])
        
        for entry in entries:
            # Check for duplicates
            key = (entry.get("title", "").lower(), entry.get("username", "").lower(), entry.get("url", "").lower())
            is_duplicate = key in existing_set
            
            if is_duplicate:
                if duplicate_handling == DuplicateHandling.SKIP:
                    stats["skipped"] += 1
                    continue
                elif duplicate_handling == DuplicateHandling.REPLACE:
                    # Find and delete the existing entry
                    for existing in vault.get_entries():
                        existing_key = (existing.get("title", "").lower(), 
                                      existing.get("username", "").lower(), 
                                      existing.get("url", "").lower())
                        if existing_key == key:
                            vault.delete_entry(existing["id"])
                            break
                    stats["replaced"] += 1
                elif duplicate_handling == DuplicateHandling.MERGE:
                    # Merge tags and notes
                    for existing in vault.get_entries():
                        existing_key = (existing.get("title", "").lower(), 
                                      existing.get("username", "").lower(), 
                                      existing.get("url", "").lower())
                        if existing_key == key:
                            # Merge tags
                            merged_tags = list(set(existing.get("tags", []) + entry.get("tags", [])))
                            existing["tags"] = merged_tags
                            # Merge notes
                            if entry.get("notes"):
                                if existing.get("notes"):
                                    existing["notes"] += f"\n\n--- Imported ---\n{entry['notes']}"
                                else:
                                    existing["notes"] = entry["notes"]
                            existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                            vault.update_entry(existing["id"], existing)
                            break
                    stats["merged"] += 1
                    continue
            
            # Generate new ID for imported entry
            entry["id"] = str(uuid.uuid4())
            entry["created_at"] = datetime.now(timezone.utc).isoformat()
            entry["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            vault.add_entry(entry)
            stats["added"] += 1
            existing_set.add(key)
        
        vault.save()
        
        return {
            "success": True,
            "format": import_format.value,
            "entries_added": stats["added"],
            "entries_skipped": stats["skipped"],
            "entries_merged": stats["merged"],
            "entries_replaced": stats["replaced"],
            "total_processed": stats["total"]
        }
