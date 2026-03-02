"""Cryptographically secure password generator."""

import secrets
import string


class PasswordGenerator:
    """Generate secure passwords with customizable character sets."""
    
    def __init__(self, length: int = 16):
        """Initialize password generator with default settings.
        
        Args:
            length: Password length (default: 16)
        """
        self.length = length
        self.include_uppercase = True
        self.include_lowercase = True
        self.include_numbers = True
        self.include_symbols = True
        
        # Character sets
        self._uppercase = string.ascii_uppercase
        self._lowercase = string.ascii_lowercase
        self._numbers = string.digits
        self._symbols = string.punctuation
    
    def generate(self) -> str:
        """Generate a password based on current settings.
        
        Ensures at least one character from each selected charset.
        
        Returns:
            Generated password string
            
        Raises:
            ValueError: If no character sets are selected
        """
        # Build pool of allowed characters
        char_pool = ""
        required_chars = []
        
        if self.include_uppercase:
            char_pool += self._uppercase
            required_chars.append(secrets.choice(self._uppercase))
        
        if self.include_lowercase:
            char_pool += self._lowercase
            required_chars.append(secrets.choice(self._lowercase))
        
        if self.include_numbers:
            char_pool += self._numbers
            required_chars.append(secrets.choice(self._numbers))
        
        if self.include_symbols:
            char_pool += self._symbols
            required_chars.append(secrets.choice(self._symbols))
        
        if not char_pool:
            raise ValueError("At least one character set must be enabled")
        
        # Fill remaining length with random characters from pool
        remaining_length = self.length - len(required_chars)
        if remaining_length < 0:
            raise ValueError(
                f"Password length ({self.length}) must be at least "
                f"the number of required character sets ({len(required_chars)})"
            )
        
        password_chars = required_chars + [
            secrets.choice(char_pool) for _ in range(remaining_length)
        ]
        
        # Shuffle to avoid predictable positions for required chars
        secrets.SystemRandom().shuffle(password_chars)
        
        return "".join(password_chars)
    
    def set_length(self, length: int) -> None:
        """Set the password length.
        
        Args:
            length: New password length (must be >= 1)
            
        Raises:
            ValueError: If length is less than 1
        """
        if length < 1:
            raise ValueError("Password length must be at least 1")
        self.length = length
    
    def toggle_uppercase(self) -> bool:
        """Toggle uppercase characters on/off.
        
        Returns:
            New state of include_uppercase
        """
        self.include_uppercase = not self.include_uppercase
        return self.include_uppercase
    
    def toggle_lowercase(self) -> bool:
        """Toggle lowercase characters on/off.
        
        Returns:
            New state of include_lowercase
        """
        self.include_lowercase = not self.include_lowercase
        return self.include_lowercase
    
    def toggle_numbers(self) -> bool:
        """Toggle numeric characters on/off.
        
        Returns:
            New state of include_numbers
        """
        self.include_numbers = not self.include_numbers
        return self.include_numbers
    
    def toggle_symbols(self) -> bool:
        """Toggle symbol characters on/off.
        
        Returns:
            New state of include_symbols
        """
        self.include_symbols = not self.include_symbols
        return self.include_symbols
