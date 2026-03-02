"""Tests for cryptographic functions."""

import pytest
import os
import tempfile
from pathlib import Path

from lazypassword.crypto import (
    generate_salt,
    derive_key,
    derive_key_with_keyfile,
    encrypt,
    decrypt,
    secure_wipe,
    get_keyfile_hash,
)


class TestKeyDerivation:
    """Tests for key derivation functions."""

    def test_derive_key(self):
        """Test key derivation with Argon2id produces consistent 32-byte keys."""
        password = "test_password_123"
        salt = generate_salt()
        
        key1 = derive_key(password, salt)
        key2 = derive_key(password, salt)
        
        # Same password + salt should produce same key
        assert key1 == key2
        assert len(key1) == 32
        
        # Different salt should produce different key
        salt2 = generate_salt()
        key3 = derive_key(password, salt2)
        assert key1 != key3
        
        # Different password should produce different key
        key4 = derive_key("different_password", salt)
        assert key1 != key4

    def test_derive_key_with_keyfile(self):
        """Test key derivation with password + keyfile."""
        password = "test_password_123"
        salt = generate_salt()
        
        # Create a temporary keyfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"keyfile_content_for_testing_12345")
            keyfile_path = f.name
        
        try:
            key = derive_key_with_keyfile(password, salt, keyfile_path)
            
            # Should produce 32-byte key
            assert len(key) == 32
            
            # Same inputs should produce same key
            key2 = derive_key_with_keyfile(password, salt, keyfile_path)
            assert key == key2
            
            # Different keyfile should produce different key
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
                f2.write(b"different_keyfile_content_67890")
                keyfile_path2 = f2.name
            
            try:
                key3 = derive_key_with_keyfile(password, salt, keyfile_path2)
                assert key != key3
            finally:
                os.unlink(keyfile_path2)
        finally:
            os.unlink(keyfile_path)

    def test_derive_key_with_keyfile_not_found(self):
        """Test that FileNotFoundError is raised for missing keyfile."""
        password = "test_password"
        salt = generate_salt()
        
        with pytest.raises(FileNotFoundError):
            derive_key_with_keyfile(password, salt, "/nonexistent/keyfile.txt")

    def test_derive_key_with_empty_keyfile(self):
        """Test that ValueError is raised for empty keyfile."""
        password = "test_password"
        salt = generate_salt()
        
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"")  # Empty file
            keyfile_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Keyfile is empty"):
                derive_key_with_keyfile(password, salt, keyfile_path)
        finally:
            os.unlink(keyfile_path)


class TestEncryptionDecryption:
    """Tests for AES-256-GCM encryption/decryption."""

    def test_encrypt_decrypt(self):
        """Test that encrypt/decrypt roundtrip works correctly."""
        key = os.urandom(32)
        plaintext = b"This is a secret message!"
        
        encrypted = encrypt(plaintext, key)
        decrypted = decrypt(encrypted, key)
        
        assert decrypted == plaintext
        
        # Encrypted should be different from plaintext and include nonce
        assert len(encrypted) > len(plaintext)
        assert encrypted != plaintext

    def test_encrypt_produces_different_ciphertexts(self):
        """Test that encrypting same data twice produces different ciphertexts (due to random nonce)."""
        key = os.urandom(32)
        plaintext = b"Same message"
        
        encrypted1 = encrypt(plaintext, key)
        encrypted2 = encrypt(plaintext, key)
        
        # Should be different due to random nonce
        assert encrypted1 != encrypted2
        
        # But both should decrypt to same plaintext
        assert decrypt(encrypted1, key) == plaintext
        assert decrypt(encrypted2, key) == plaintext

    def test_decrypt_with_wrong_key(self):
        """Test that decryption with wrong key raises exception."""
        from cryptography.exceptions import InvalidTag
        
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        plaintext = b"Secret message"
        
        encrypted = encrypt(plaintext, key1)
        
        with pytest.raises((ValueError, InvalidTag)):
            decrypt(encrypted, key2)

    def test_decrypt_corrupted_data(self):
        """Test that decrypting corrupted data raises exception."""
        from cryptography.exceptions import InvalidTag
        
        key = os.urandom(32)
        plaintext = b"Secret message"
        
        encrypted = encrypt(plaintext, key)
        
        # Corrupt the ciphertext (skip nonce, corrupt middle)
        corrupted = encrypted[:20] + b"\x00" * 10 + encrypted[30:]
        
        with pytest.raises((ValueError, InvalidTag)):
            decrypt(corrupted, key)

    def test_decrypt_too_short_data(self):
        """Test that decrypting data that's too short raises ValueError."""
        key = os.urandom(32)
        
        with pytest.raises(ValueError, match="too short"):
            decrypt(b"short", key)


class TestSaltGeneration:
    """Tests for salt generation."""

    def test_generate_salt(self):
        """Test that salt generation produces 32-byte random salts."""
        salt1 = generate_salt()
        salt2 = generate_salt()
        
        assert len(salt1) == 32
        assert len(salt2) == 32
        # Salts should be different
        assert salt1 != salt2

    def test_generate_salt_randomness(self):
        """Test that multiple salts are unique."""
        salts = [generate_salt() for _ in range(100)]
        assert len(set(salts)) == 100  # All unique


class TestSecureWipe:
    """Tests for secure memory wiping."""

    def test_secure_wipe(self):
        """Test that secure_wipe overwrites data with zeros."""
        data = bytearray(b"sensitive data to be wiped")
        original_len = len(data)
        
        secure_wipe(data)
        
        # Data should be all zeros
        assert all(b == 0 for b in data)
        assert len(data) == original_len

    def test_secure_wipe_empty(self):
        """Test that secure_wipe handles empty bytearray."""
        data = bytearray()
        secure_wipe(data)  # Should not raise
        assert len(data) == 0


class TestKeyfileHash:
    """Tests for keyfile hash generation."""

    def test_get_keyfile_hash(self):
        """Test that keyfile hash is consistent."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"test content for hashing")
            keyfile_path = f.name
        
        try:
            hash1 = get_keyfile_hash(keyfile_path)
            hash2 = get_keyfile_hash(keyfile_path)
            
            # Should be hex string
            assert isinstance(hash1, str)
            assert len(hash1) == 64  # SHA-256 hex is 64 chars
            assert hash1 == hash2  # Consistent
            
            # Different content should produce different hash
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f2:
                f2.write(b"different content")
                keyfile_path2 = f2.name
            
            try:
                hash3 = get_keyfile_hash(keyfile_path2)
                assert hash1 != hash3
            finally:
                os.unlink(keyfile_path2)
        finally:
            os.unlink(keyfile_path)

    def test_get_keyfile_hash_not_found(self):
        """Test that FileNotFoundError is raised for missing keyfile."""
        with pytest.raises(FileNotFoundError):
            get_keyfile_hash("/nonexistent/keyfile.txt")

    def test_get_keyfile_hash_empty_file(self):
        """Test that ValueError is raised for empty keyfile."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b"")
            keyfile_path = f.name
        
        try:
            with pytest.raises(ValueError, match="Keyfile is empty"):
                get_keyfile_hash(keyfile_path)
        finally:
            os.unlink(keyfile_path)