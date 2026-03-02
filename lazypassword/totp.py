"""TOTP (Time-based One-Time Password) implementation for lazypassword.

Implements RFC 6238 TOTP using the pyotp library for 2FA support.
"""

import base64
import hashlib
import hmac
import struct
import time
from typing import Optional


class TOTPManager:
    """Manager for TOTP (Time-based One-Time Password) operations."""
    
    # Default TOTP parameters per RFC 6238
    DEFAULT_DIGITS = 6
    DEFAULT_INTERVAL = 30  # seconds
    DEFAULT_ALGORITHM = "SHA1"
    
    def __init__(self, digits: int = DEFAULT_DIGITS, interval: int = DEFAULT_INTERVAL):
        """
        Initialize TOTP manager.
        
        Args:
            digits: Number of digits in the OTP code (default 6)
            interval: Time window in seconds (default 30)
        """
        self.digits = digits
        self.interval = interval
    
    @staticmethod
    def generate_secret() -> str:
        """
        Generate a random base32-encoded secret for TOTP.
        
        Returns:
            str: Base32-encoded secret (suitable for QR codes)
        """
        import secrets
        # Generate 20 random bytes (160 bits) for SHA1
        random_bytes = secrets.token_bytes(20)
        # Encode to base32 (without padding for compatibility)
        secret = base64.b32encode(random_bytes).decode('utf-8').rstrip('=')
        return secret
    
    def get_uri(self, secret: str, issuer: str, account: str) -> str:
        """
        Generate an otpauth:// URI for QR code generation.
        
        Args:
            secret: The TOTP secret (base32 encoded)
            issuer: The service name (e.g., "GitHub", "Google")
            account: The account identifier (e.g., user@example.com)
            
        Returns:
            str: otpauth:// URI for QR codes
        """
        from urllib.parse import quote
        
        # Encode parameters for URI
        encoded_issuer = quote(issuer, safe='')
        encoded_account = quote(account, safe='')
        label = f"{encoded_issuer}:{encoded_account}"
        
        uri = (
            f"otpauth://totp/{label}?"
            f"secret={secret}&"
            f"issuer={encoded_issuer}&"
            f"algorithm={self.DEFAULT_ALGORITHM}&"
            f"digits={self.digits}&"
            f"period={self.interval}"
        )
        return uri
    
    def _base32_decode(self, secret: str) -> bytes:
        """
        Decode base32 secret, handling padding.
        
        Args:
            secret: Base32-encoded secret
            
        Returns:
            bytes: Decoded secret
        """
        # Add padding if needed
        padding_needed = 8 - (len(secret) % 8)
        if padding_needed != 8:
            secret += '=' * padding_needed
        return base64.b32decode(secret.upper())
    
    def _get_counter(self, timestamp: Optional[float] = None) -> int:
        """
        Get the current counter value based on timestamp.
        
        Args:
            timestamp: Unix timestamp (default: current time)
            
        Returns:
            int: Counter value
        """
        if timestamp is None:
            timestamp = time.time()
        return int(timestamp) // self.interval
    
    def generate_code(self, secret: str, timestamp: Optional[float] = None) -> str:
        """
        Generate the current TOTP code.
        
        Args:
            secret: The TOTP secret (base32 encoded)
            timestamp: Unix timestamp for code generation (default: current time)
            
        Returns:
            str: 6-digit TOTP code
        """
        if not secret:
            return ""
        
        try:
            # Decode secret
            key = self._base32_decode(secret)
            
            # Get counter
            counter = self._get_counter(timestamp)
            
            # Create HMAC-SHA1
            counter_bytes = struct.pack('>Q', counter)
            hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
            
            # Dynamic truncation
            offset = hmac_digest[-1] & 0x0f
            code = struct.unpack('>I', hmac_digest[offset:offset + 4])[0]
            code &= 0x7fffffff
            code %= 10 ** self.digits
            
            # Zero-pad to desired length
            return str(code).zfill(self.digits)
        except Exception:
            return ""
    
    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code with a time window.
        
        Args:
            secret: The TOTP secret (base32 encoded)
            code: The code to verify
            window: Number of time steps before/after to check (default 1)
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        if not secret or not code:
            return False
        
        # Normalize code
        code = code.strip().replace(' ', '')
        
        current_time = time.time()
        
        # Check codes in the window
        for offset in range(-window, window + 1):
            check_time = current_time + (offset * self.interval)
            expected = self.generate_code(secret, check_time)
            if hmac.compare_digest(expected, code):
                return True
        
        return False
    
    def get_time_remaining(self) -> int:
        """
        Get seconds remaining until current code expires.
        
        Returns:
            int: Seconds remaining (0 to interval-1)
        """
        current_time = time.time()
        elapsed = int(current_time) % self.interval
        return self.interval - elapsed
    
    def get_progress_percentage(self) -> float:
        """
        Get the progress percentage of the current time window.
        
        Returns:
            float: Percentage from 0.0 to 1.0
        """
        remaining = self.get_time_remaining()
        return remaining / self.interval


# Convenience function for quick code generation
def generate_totp_code(secret: str) -> str:
    """
    Generate current TOTP code from secret.
    
    Args:
        secret: Base32-encoded TOTP secret
        
    Returns:
        str: Current 6-digit code
    """
    manager = TOTPManager()
    return manager.generate_code(secret)
