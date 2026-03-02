"""
Cryptographic utilities for lazypassword.
Uses Argon2id for key derivation and AES-256-GCM for encryption.
"""

import os
import secrets
from typing import Union

from argon2.low_level import hash_secret_raw, Type
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Argon2id parameters (OWASP recommended minimum)
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536  # 64 MB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 32


def generate_salt() -> bytes:
    """Generate a random 32-byte salt."""
    return secrets.token_bytes(ARGON2_SALT_LEN)


def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte key from password using Argon2id.
    
    Args:
        password: The user's master password
        salt: Random salt bytes
        
    Returns:
        32-byte derived key
    """
    password_bytes = password.encode('utf-8')
    
    key = hash_secret_raw(
        secret=password_bytes,
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID
    )
    
    # Wipe password bytes from memory
    secure_wipe(bytearray(password_bytes))
    
    return key


def encrypt(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        data: Plaintext data to encrypt
        key: 32-byte encryption key
        
    Returns:
        bytes: nonce (12 bytes) + ciphertext + tag (16 bytes)
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    # nonce + ciphertext (which includes auth tag)
    return nonce + ciphertext


def decrypt(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        encrypted_data: nonce (12 bytes) + ciphertext + tag (16 bytes)
        key: 32-byte encryption key
        
    Returns:
        bytes: Decrypted plaintext
        
    Raises:
        ValueError: If decryption fails (wrong key, corrupted data)
    """
    if len(encrypted_data) < 28:  # 12 (nonce) + 16 (minimum ciphertext with tag)
        raise ValueError("Invalid encrypted data: too short")
    
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def secure_wipe(data: bytearray) -> None:
    """
    Securely wipe memory by overwriting with zeros.
    
    Args:
        data: bytearray to wipe
    """
    for i in range(len(data)):
        data[i] = 0
