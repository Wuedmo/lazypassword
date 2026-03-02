"""AES-256-GCM encryption plugin."""

import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

from ..base import EncryptionPlugin
from ..exceptions import EncryptionError


class AES256GCMPlugin(EncryptionPlugin):
    """AES-256-GCM authenticated encryption plugin.
    
    Uses the cryptography library for AES-256-GCM.
    Provides authenticated encryption with 256-bit keys.
    """
    
    name = "AES-256-GCM"
    identifier = "aes-256-gcm"
    description = "AES-256 in Galois/Counter Mode. Industry standard authenticated encryption."
    security_level = 5
    
    # AES-GCM constants
    NONCE_SIZE = 12  # 96 bits recommended for GCM
    KEY_SIZE = 32  # 256 bits
    TAG_SIZE = 16  # 128 bits (included in ciphertext)
    
    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        self._nonce: bytes = b""
    
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """Encrypt data using AES-256-GCM.
        
        Args:
            data: Plaintext data to encrypt
            key: 32-byte encryption key
            **kwargs: Additional parameters (nonce can be provided for testing)
            
        Returns:
            bytes: nonce (12 bytes) + ciphertext + tag
            
        Raises:
            EncryptionError: If encryption fails
        """
        if len(key) != self.KEY_SIZE:
            raise EncryptionError(f"Invalid key size: {len(key)} bytes, expected {self.KEY_SIZE}")
        
        try:
            # Use provided nonce or generate random one
            self._nonce = kwargs.get('nonce', os.urandom(self.NONCE_SIZE))
            
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(self._nonce, data, None)
            
            # Store nonce for serialization
            self._params['nonce'] = self._nonce.hex()
            
            # Return nonce + ciphertext (which includes tag)
            return self._nonce + ciphertext
            
        except Exception as e:
            raise EncryptionError(f"AES-256-GCM encryption failed: {e}")
    
    def decrypt(self, encrypted_data: bytes, key: bytes, **kwargs) -> bytes:
        """Decrypt data using AES-256-GCM.
        
        Args:
            encrypted_data: nonce (12 bytes) + ciphertext + tag
            key: 32-byte encryption key
            **kwargs: Additional parameters (nonce can be provided)
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            EncryptionError: If decryption fails (wrong key, corrupted data)
        """
        if len(key) != self.KEY_SIZE:
            raise EncryptionError(f"Invalid key size: {len(key)} bytes, expected {self.KEY_SIZE}")
        
        min_length = self.NONCE_SIZE + self.TAG_SIZE + 1  # At least 1 byte of ciphertext
        if len(encrypted_data) < min_length:
            raise EncryptionError(f"Encrypted data too short: {len(encrypted_data)} bytes")
        
        try:
            # Extract nonce from data or kwargs
            if 'nonce' in kwargs:
                nonce = kwargs['nonce']
                if isinstance(nonce, str):
                    nonce = bytes.fromhex(nonce)
                ciphertext = encrypted_data
            else:
                nonce = encrypted_data[:self.NONCE_SIZE]
                ciphertext = encrypted_data[self.NONCE_SIZE:]
            
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None)
            
        except InvalidTag:
            raise EncryptionError("Decryption failed: invalid authentication tag (wrong password or corrupted data)")
        except Exception as e:
            raise EncryptionError(f"AES-256-GCM decryption failed: {e}")
    
    def get_key_size(self) -> int:
        """Return the required key size (32 bytes for AES-256)."""
        return self.KEY_SIZE
    
    def serialize_params(self) -> dict:
        """Serialize plugin-specific parameters."""
        return {
            'nonce': self._nonce.hex() if self._nonce else '',
            'algorithm': 'AES-256-GCM'
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if cryptography library is available."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            return True
        except ImportError:
            return False
