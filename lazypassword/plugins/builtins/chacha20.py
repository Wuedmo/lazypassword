"""ChaCha20-Poly1305 encryption plugin."""

import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.exceptions import InvalidTag

from ..base import EncryptionPlugin
from ..exceptions import EncryptionError


class ChaCha20Poly1305Plugin(EncryptionPlugin):
    """ChaCha20-Poly1305 authenticated encryption plugin.
    
    Uses the cryptography library for ChaCha20-Poly1305.
    Modern alternative to AES-GCM, especially fast on mobile/ARM devices.
    """
    
    name = "ChaCha20-Poly1305"
    identifier = "chacha20-poly1305"
    description = "ChaCha20 stream cipher with Poly1305 MAC. Modern, fast on mobile devices."
    security_level = 5
    
    # ChaCha20-Poly1305 constants
    NONCE_SIZE = 12  # 96 bits
    KEY_SIZE = 32  # 256 bits
    TAG_SIZE = 16  # 128 bits
    
    def __init__(self):
        """Initialize the plugin."""
        super().__init__()
        self._nonce: bytes = b""
    
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """Encrypt data using ChaCha20-Poly1305.
        
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
            
            chacha = ChaCha20Poly1305(key)
            ciphertext = chacha.encrypt(self._nonce, data, None)
            
            # Store nonce for serialization
            self._params['nonce'] = self._nonce.hex()
            
            # Return nonce + ciphertext (which includes tag)
            return self._nonce + ciphertext
            
        except Exception as e:
            raise EncryptionError(f"ChaCha20-Poly1305 encryption failed: {e}")
    
    def decrypt(self, encrypted_data: bytes, key: bytes, **kwargs) -> bytes:
        """Decrypt data using ChaCha20-Poly1305.
        
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
            
            chacha = ChaCha20Poly1305(key)
            return chacha.decrypt(nonce, ciphertext, None)
            
        except InvalidTag:
            raise EncryptionError("Decryption failed: invalid authentication tag (wrong password or corrupted data)")
        except Exception as e:
            raise EncryptionError(f"ChaCha20-Poly1305 decryption failed: {e}")
    
    def get_key_size(self) -> int:
        """Return the required key size (32 bytes)."""
        return self.KEY_SIZE
    
    def serialize_params(self) -> dict:
        """Serialize plugin-specific parameters."""
        return {
            'nonce': self._nonce.hex() if self._nonce else '',
            'algorithm': 'ChaCha20-Poly1305'
        }
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if cryptography library is available."""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
            return True
        except ImportError:
            return False
