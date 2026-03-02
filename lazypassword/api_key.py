"""API key management for lazypassword.

This module provides data models and management for API keys
from various platforms like OpenAI, AWS, Stripe, GitHub, etc.
"""

import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from .api_presets import API_KEY_PRESETS, get_preset


@dataclass
class APIKey:
    """An API key entry in the vault."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    platform: str = "custom"  # "openai", "aws", "stripe", "github", "custom"
    key_value: str = ""
    secret_key: str = ""  # For AWS-style keys with both key_id and secret
    endpoint: str = ""  # Custom API endpoint if applicable
    headers: dict = field(default_factory=dict)  # Custom headers
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: list = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert API key to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "APIKey":
        """Create API key from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            platform=data.get("platform", "custom"),
            key_value=data.get("key_value", ""),
            secret_key=data.get("secret_key", ""),
            endpoint=data.get("endpoint", ""),
            headers=data.get("headers", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_masked_key(self) -> str:
        """Get masked version of the key (shows only last 4 chars)."""
        if not self.key_value:
            return ""
        if len(self.key_value) <= 4:
            return "****"
        return "*" * (len(self.key_value) - 4) + self.key_value[-4:]
    
    def get_masked_secret(self) -> str:
        """Get masked version of the secret key."""
        if not self.secret_key:
            return ""
        if len(self.secret_key) <= 4:
            return "****"
        return "*" * (len(self.secret_key) - 4) + self.secret_key[-4:]
    
    def get_authorization_header(self) -> str:
        """Get the Authorization header value for this key."""
        preset = get_preset(self.platform)
        format_type = preset.get("format", "Bearer")
        
        if format_type == "Bearer":
            return f"Bearer {self.key_value}"
        elif format_type == "x-api-key":
            return self.key_value
        elif format_type == "key":
            return f"key={self.key_value}"
        elif format_type == "access_key":
            # AWS uses a different signing mechanism
            return f"AWS4-HMAC-SHA256 Credential={self.key_value}"
        else:
            return self.key_value
    
    def get_curl_command(self) -> str:
        """Get a curl command example for this key."""
        preset = get_preset(self.platform)
        endpoint = self.endpoint or preset.get("endpoint", "https://api.example.com")
        format_type = preset.get("format", "Bearer")
        
        if format_type == "Bearer":
            return f'curl -H "Authorization: Bearer {self.key_value}" {endpoint}/v1/models'
        elif format_type == "x-api-key":
            return f'curl -H "x-api-key: {self.key_value}" {endpoint}/v1/models'
        elif format_type == "key":
            return f'curl "{endpoint}/v1/models?key={self.key_value}"'
        elif format_type == "access_key":
            return f'# AWS requires signed requests\n# Key ID: {self.key_value}\n# Secret: {self.secret_key}'
        else:
            headers = " ".join([f'-H "{k}: {v}"' for k, v in self.headers.items()])
            return f'curl {headers} {endpoint}'
    
    def get_env_export(self) -> str:
        """Get environment variable export command."""
        preset = get_preset(self.platform)
        platform_upper = self.platform.upper().replace("-", "_")
        
        if self.platform == "openai":
            return f'export OPENAI_API_KEY="{self.key_value}"'
        elif self.platform == "aws":
            return f'export AWS_ACCESS_KEY_ID="{self.key_value}"\nexport AWS_SECRET_ACCESS_KEY="{self.secret_key}"'
        elif self.platform == "anthropic":
            return f'export ANTHROPIC_API_KEY="{self.key_value}"'
        elif self.platform == "github":
            return f'export GITHUB_TOKEN="{self.key_value}"'
        elif self.platform == "stripe":
            return f'export STRIPE_API_KEY="{self.key_value}"'
        elif self.platform == "huggingface":
            return f'export HUGGINGFACE_TOKEN="{self.key_value}"'
        elif self.platform == "google":
            return f'export GOOGLE_API_KEY="{self.key_value}"'
        else:
            return f'export {platform_upper}_API_KEY="{self.key_value}"'
    
    def get_icon(self) -> str:
        """Get the icon for this API key's platform."""
        preset = get_preset(self.platform)
        return preset.get("icon", "🔑")


class APIKeyManager:
    """Manager for API key operations."""
    
    def __init__(self, vault=None):
        """Initialize with optional vault reference."""
        self._vault = vault
    
    def set_vault(self, vault):
        """Set the vault reference."""
        self._vault = vault
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique API key ID."""
        return str(uuid.uuid4())
    
    def create_key(
        self,
        name: str,
        platform: str,
        key_value: str,
        secret_key: str = "",
        endpoint: str = "",
        headers: dict = None,
        tags: list = None,
        notes: str = "",
    ) -> APIKey:
        """Create a new API key.
        
        Args:
            name: Display name for the key
            platform: Platform identifier (openai, aws, etc.)
            key_value: The API key value
            secret_key: Optional secret key (for AWS-style keys)
            endpoint: Custom API endpoint
            headers: Custom headers dict
            tags: List of tags
            notes: Additional notes
            
        Returns:
            New APIKey instance
        """
        timestamp = datetime.utcnow().isoformat()
        return APIKey(
            id=self.generate_id(),
            name=name,
            platform=platform,
            key_value=key_value,
            secret_key=secret_key,
            endpoint=endpoint,
            headers=headers or {},
            created_at=timestamp,
            updated_at=timestamp,
            tags=tags or [],
            notes=notes,
        )
    
    @staticmethod
    def validate_key_format(platform: str, key_value: str) -> bool:
        """Validate an API key against its platform's format.
        
        Args:
            platform: Platform identifier
            key_value: The API key to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not key_value:
            return False
        
        preset = get_preset(platform)
        pattern = preset.get("pattern", ".*")
        
        try:
            return bool(re.match(pattern, key_value))
        except re.error:
            return True  # If regex is invalid, accept any value
    
    @staticmethod
    def mask_key(key_value: str) -> str:
        """Mask an API key (show only last 4 chars).
        
        Args:
            key_value: The API key to mask
            
        Returns:
            Masked key string
        """
        if not key_value:
            return ""
        if len(key_value) <= 4:
            return "****"
        return "*" * (len(key_value) - 4) + key_value[-4:]
    
    @staticmethod
    def get_platforms() -> list:
        """Get list of supported platform identifiers.
        
        Returns:
            List of platform identifiers
        """
        return list(API_KEY_PRESETS.keys())
    
    @staticmethod
    def get_platforms_with_metadata() -> list:
        """Get list of platforms with their metadata.
        
        Returns:
            List of tuples (id, name, description, icon)
        """
        return [
            (key, preset["name"], preset["description"], preset.get("icon", "🔑"))
            for key, preset in API_KEY_PRESETS.items()
        ]
    
    @staticmethod
    def get_platform_format(platform: str) -> dict:
        """Get format requirements for a platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            Dictionary with format requirements
        """
        return get_preset(platform)
    
    @staticmethod
    def requires_secret(platform: str) -> bool:
        """Check if a platform requires a secret key.
        
        Args:
            platform: Platform identifier
            
        Returns:
            True if secret key is required
        """
        preset = get_preset(platform)
        return preset.get("requires_secret", False)
    
    # Vault integration methods
    
    def add_to_vault(self, api_key: APIKey) -> str:
        """Add an API key to the vault.
        
        Args:
            api_key: The API key to add
            
        Returns:
            The key ID
        """
        if not self._vault:
            raise ValueError("No vault set")
        return self._vault.add_api_key(api_key.to_dict())
    
    def get_from_vault(self, key_id: str) -> Optional[APIKey]:
        """Get an API key from the vault.
        
        Args:
            key_id: The API key ID
            
        Returns:
            APIKey instance or None if not found
        """
        if not self._vault:
            raise ValueError("No vault set")
        data = self._vault.get_api_key(key_id)
        if data:
            return APIKey.from_dict(data)
        return None
    
    def get_all_from_vault(self) -> list:
        """Get all API keys from the vault.
        
        Returns:
            List of APIKey instances
        """
        if not self._vault:
            raise ValueError("No vault set")
        keys = self._vault.get_api_keys()
        return [APIKey.from_dict(k) for k in keys]
    
    def update_in_vault(self, api_key: APIKey) -> None:
        """Update an API key in the vault.
        
        Args:
            api_key: The API key to update
        """
        if not self._vault:
            raise ValueError("No vault set")
        api_key.update_timestamp()
        self._vault.update_api_key(api_key.id, api_key.to_dict())
    
    def delete_from_vault(self, key_id: str) -> bool:
        """Delete an API key from the vault.
        
        Args:
            key_id: The API key ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if not self._vault:
            raise ValueError("No vault set")
        return self._vault.delete_api_key(key_id)
    
    def search_in_vault(self, query: str) -> list:
        """Search API keys in the vault.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching APIKey instances
        """
        if not self._vault:
            raise ValueError("No vault set")
        
        query_lower = query.lower()
        all_keys = self.get_all_from_vault()
        
        results = []
        for key in all_keys:
            # Search in name, platform, tags, notes
            searchable = f"{key.name} {key.platform} {' '.join(key.tags)} {key.notes}"
            if query_lower in searchable.lower():
                results.append(key)
        
        return results
