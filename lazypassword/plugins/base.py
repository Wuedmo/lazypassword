"""Base classes for encryption plugins."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class EncryptionPlugin(ABC):
    """Abstract base class for encryption plugins.
    
    All encryption plugins must inherit from this class and implement
    the required methods.
    """
    
    # Plugin metadata - must be set by subclasses
    name: str = ""
    identifier: str = ""
    description: str = ""
    security_level: int = 5  # 1-5 rating
    
    def __init__(self):
        """Initialize the plugin."""
        self._params: Dict[str, Any] = {}
    
    @abstractmethod
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """Encrypt data.
        
        Args:
            data: Plaintext data to encrypt
            key: Encryption key (must be get_key_size() bytes)
            **kwargs: Additional plugin-specific parameters
            
        Returns:
            bytes: Encrypted data (format depends on plugin)
            
        Raises:
            EncryptionError: If encryption fails
        """
        pass
    
    @abstractmethod
    def decrypt(self, encrypted_data: bytes, key: bytes, **kwargs) -> bytes:
        """Decrypt data.
        
        Args:
            encrypted_data: Encrypted data from encrypt()
            key: Encryption key (must be get_key_size() bytes)
            **kwargs: Additional plugin-specific parameters (usually from serialize_params)
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            EncryptionError: If decryption fails
        """
        pass
    
    @abstractmethod
    def get_key_size(self) -> int:
        """Return the required key size in bytes.
        
        Returns:
            int: Key size in bytes (e.g., 32 for AES-256)
        """
        pass
    
    def serialize_params(self) -> Dict[str, Any]:
        """Serialize plugin-specific parameters (nonce, salt, etc.).
        
        These parameters are stored with the encrypted data and passed
        back to decrypt() via kwargs.
        
        Returns:
            dict: Serialized parameters
        """
        return dict(self._params)
    
    def deserialize_params(self, params: Dict[str, Any]) -> None:
        """Deserialize plugin-specific parameters.
        
        Args:
            params: Parameters dictionary (usually from serialize_params)
        """
        self._params = dict(params)
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if this plugin can be used (dependencies installed).
        
        Returns:
            bool: True if plugin is available
        """
        return True
    
    @classmethod
    def get_security_rating(cls) -> str:
        """Get a visual security rating.
        
        Returns:
            str: Star rating (e.g., "★★★★★")
        """
        return "★" * cls.security_level + "☆" * (5 - cls.security_level)
