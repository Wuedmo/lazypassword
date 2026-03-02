"""Tests for TOTP generation."""

import pytest
import time
import base64
from unittest.mock import patch

from lazypassword.totp import TOTPManager, generate_totp_code


class TestGenerateSecret:
    """Tests for TOTP secret generation."""

    def test_generate_secret(self):
        """Test that generate_secret produces valid base32 secrets."""
        manager = TOTPManager()
        
        secret = manager.generate_secret()
        
        # Should be a string
        assert isinstance(secret, str)
        
        # Should be base32 encoded (A-Z, 2-7)
        assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567' for c in secret)
        
        # Should be 32 characters (no padding)
        assert len(secret) == 32

    def test_generate_secret_uniqueness(self):
        """Test that generated secrets are unique."""
        manager = TOTPManager()
        
        secrets = [manager.generate_secret() for _ in range(100)]
        
        assert len(set(secrets)) == 100

    def test_generate_secret_static_method(self):
        """Test static method for secret generation."""
        secret = TOTPManager.generate_secret()
        
        assert isinstance(secret, str)
        assert len(secret) == 32


class TestGenerateCode:
    """Tests for TOTP code generation."""

    def test_generate_code(self):
        """Test generating TOTP code."""
        manager = TOTPManager()
        
        # Use a known secret
        secret = "JBSWY3DPEHPK3PXP"  # Known test secret
        
        code = manager.generate_code(secret)
        
        # Should be a string of 6 digits
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_consistent(self):
        """Test that same secret + timestamp produces same code."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        timestamp = 1234567890.0
        
        code1 = manager.generate_code(secret, timestamp)
        code2 = manager.generate_code(secret, timestamp)
        
        assert code1 == code2

    def test_generate_code_different_timestamps(self):
        """Test that different timestamps produce different codes."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        code1 = manager.generate_code(secret, 1234567890.0)
        code2 = manager.generate_code(secret, 1234567920.0)  # 30 seconds later
        
        assert code1 != code2

    def test_generate_code_empty_secret(self):
        """Test generating code with empty secret."""
        manager = TOTPManager()
        
        code = manager.generate_code("")
        
        assert code == ""

    def test_generate_code_invalid_secret(self):
        """Test generating code with invalid secret."""
        manager = TOTPManager()
        
        code = manager.generate_code("invalid!!!")
        
        assert code == ""

    def test_generate_code_different_digits(self):
        """Test generating codes with different digit lengths."""
        manager8 = TOTPManager(digits=8)
        secret = "JBSWY3DPEHPK3PXP"
        
        code = manager8.generate_code(secret)
        
        assert len(code) == 8

    def test_generate_code_convenience_function(self):
        """Test the convenience function generate_totp_code."""
        secret = "JBSWY3DPEHPK3PXP"
        
        code = generate_totp_code(secret)
        
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()


class TestVerifyCode:
    """Tests for TOTP code verification."""

    def test_verify_code_valid(self):
        """Test verifying a valid code."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        # Generate current code
        code = manager.generate_code(secret)
        
        # Verify it
        result = manager.verify_code(secret, code)
        
        assert result == True

    def test_verify_code_invalid(self):
        """Test verifying an invalid code."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        result = manager.verify_code(secret, "000000")
        
        assert result == False

    def test_verify_code_with_window(self):
        """Test verification with time window."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        # Get current timestamp and generate code for previous interval
        current_time = time.time()
        previous_time = current_time - 30  # Previous interval
        code = manager.generate_code(secret, previous_time)
        
        # Should verify with window=1
        result = manager.verify_code(secret, code, window=1)
        
        assert result == True

    def test_verify_code_empty(self):
        """Test verifying empty code."""
        manager = TOTPManager()
        
        assert manager.verify_code("secret", "") == False
        assert manager.verify_code("", "123456") == False

    def test_verify_code_with_spaces(self):
        """Test that spaces are stripped from code."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        code = manager.generate_code(secret)
        code_with_spaces = f"{code[:3]} {code[3:]}"
        
        result = manager.verify_code(secret, code_with_spaces)
        
        assert result == True


class TestGetURI:
    """Tests for otpauth URI generation."""

    def test_get_uri(self):
        """Test generating otpauth URI."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        uri = manager.get_uri(secret, "GitHub", "user@example.com")
        
        # Check URI format
        assert uri.startswith("otpauth://totp/")
        assert "secret=JBSWY3DPEHPK3PXP" in uri
        assert "issuer=GitHub" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_get_uri_with_special_chars(self):
        """Test URI with special characters in issuer/account."""
        manager = TOTPManager()
        secret = "JBSWY3DPEHPK3PXP"
        
        uri = manager.get_uri(secret, "My App", "user@domain.com")
        
        # Should be URL encoded
        assert "%40" in uri  # @ symbol encoded
        assert "My%20App" in uri  # space encoded


class TestTimeRemaining:
    """Tests for time remaining calculations."""

    @patch('time.time')
    def test_get_time_remaining(self, mock_time):
        """Test getting time remaining in current interval."""
        mock_time.return_value = 1234567897.0  # 7 seconds into interval
        
        manager = TOTPManager(interval=30)
        remaining = manager.get_time_remaining()
        
        assert remaining == 23  # 30 - 7 = 23

    @patch('time.time')
    def test_get_progress_percentage(self, mock_time):
        """Test getting progress percentage."""
        mock_time.return_value = 1234567897.0  # 7 seconds into interval
        
        manager = TOTPManager(interval=30)
        progress = manager.get_progress_percentage()
        
        assert progress == 23 / 30


class TestBase32Decoding:
    """Tests for base32 secret decoding."""

    def test_base32_decode(self):
        """Test base32 decoding with padding."""
        manager = TOTPManager()
        
        # Test various secret lengths
        secrets = [
            "JBSWY3DPEHPK3PXP",  # 16 chars
            "JBSWY3DPEHPK3PX",   # 15 chars (needs padding)
            "JBSWY3DPEHPK3",     # 13 chars (needs padding)
        ]
        
        for secret in secrets:
            decoded = manager._base32_decode(secret)
            assert isinstance(decoded, bytes)
            assert len(decoded) > 0


class TestCounterCalculation:
    """Tests for TOTP counter calculation."""

    def test_get_counter(self):
        """Test counter calculation."""
        manager = TOTPManager(interval=30)
        
        counter = manager._get_counter(1234567890.0)
        
        expected = int(1234567890.0) // 30
        assert counter == expected

    def test_get_counter_default_time(self):
        """Test counter with default current time."""
        manager = TOTPManager(interval=30)
        
        with patch('time.time') as mock_time:
            mock_time.return_value = 1234567890.0
            counter = manager._get_counter()
            
            assert counter == 1234567890 // 30