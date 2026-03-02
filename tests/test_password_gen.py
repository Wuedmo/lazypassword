"""Tests for password generator."""

import pytest
import string
from collections import Counter

from lazypassword.utils.password_gen import PasswordGenerator


class TestPasswordGeneratorInit:
    """Tests for PasswordGenerator initialization."""

    def test_default_init(self):
        """Test default initialization."""
        gen = PasswordGenerator()
        
        assert gen.length == 16
        assert gen.include_uppercase == True
        assert gen.include_lowercase == True
        assert gen.include_numbers == True
        assert gen.include_symbols == True

    def test_custom_length_init(self):
        """Test initialization with custom length."""
        gen = PasswordGenerator(length=32)
        
        assert gen.length == 32


class TestPasswordGeneration:
    """Tests for password generation."""

    def test_generate_default(self):
        """Test generating password with default settings."""
        gen = PasswordGenerator()
        
        password = gen.generate()
        
        assert isinstance(password, str)
        assert len(password) == 16
        # Should contain at least one of each charset
        assert any(c in string.ascii_uppercase for c in password)
        assert any(c in string.ascii_lowercase for c in password)
        assert any(c in string.digits for c in password)
        assert any(c in string.punctuation for c in password)

    def test_generate_length(self):
        """Test generating password of specific length."""
        for length in [8, 16, 32, 64]:
            gen = PasswordGenerator(length=length)
            password = gen.generate()
            
            assert len(password) == length

    def test_generate_only_lowercase(self):
        """Test generating password with only lowercase."""
        gen = PasswordGenerator()
        gen.include_uppercase = False
        gen.include_numbers = False
        gen.include_symbols = False
        
        password = gen.generate()
        
        assert all(c in string.ascii_lowercase for c in password)

    def test_generate_only_numbers(self):
        """Test generating password with only numbers."""
        gen = PasswordGenerator()
        gen.include_uppercase = False
        gen.include_lowercase = False
        gen.include_symbols = False
        
        password = gen.generate()
        
        assert all(c in string.digits for c in password)

    def test_generate_no_charset_selected(self):
        """Test that error is raised when no charset is selected."""
        gen = PasswordGenerator()
        gen.include_uppercase = False
        gen.include_lowercase = False
        gen.include_numbers = False
        gen.include_symbols = False
        
        with pytest.raises(ValueError, match="character set"):
            gen.generate()

    def test_generate_length_too_short(self):
        """Test that error is raised when length is too short for required charsets."""
        gen = PasswordGenerator(length=2)  # 2 chars but need 4 (one of each)
        
        with pytest.raises(ValueError, match="must be at least"):
            gen.generate()

    def test_generate_randomness(self):
        """Test that generated passwords are random."""
        gen = PasswordGenerator(length=16)
        
        passwords = [gen.generate() for _ in range(100)]
        
        # All passwords should be unique (very high probability)
        assert len(set(passwords)) == 100

    def test_generate_distribution(self):
        """Test that all character types are included in reasonable distribution."""
        gen = PasswordGenerator(length=100)
        
        password = gen.generate()
        
        # Count character types
        counts = Counter({
            'uppercase': sum(1 for c in password if c in string.ascii_uppercase),
            'lowercase': sum(1 for c in password if c in string.ascii_lowercase),
            'digits': sum(1 for c in password if c in string.digits),
            'symbols': sum(1 for c in password if c in string.punctuation),
        })
        
        # Each type should have at least some representation
        # (minimum 1 is guaranteed, but should have reasonable distribution)
        assert counts['uppercase'] >= 1
        assert counts['lowercase'] >= 1
        assert counts['digits'] >= 1
        assert counts['symbols'] >= 1

    def test_generate_minimum_one_of_each(self):
        """Test that password always contains at least one of each selected charset."""
        # Run many times to ensure consistency
        gen = PasswordGenerator(length=10)
        
        for _ in range(100):
            password = gen.generate()
            
            assert any(c in string.ascii_uppercase for c in password), f"Missing uppercase: {password}"
            assert any(c in string.ascii_lowercase for c in password), f"Missing lowercase: {password}"
            assert any(c in string.digits for c in password), f"Missing digits: {password}"
            assert any(c in string.punctuation for c in password), f"Missing symbols: {password}"


class TestToggleMethods:
    """Tests for charset toggle methods."""

    def test_toggle_uppercase(self):
        """Test toggling uppercase characters."""
        gen = PasswordGenerator()
        
        initial = gen.include_uppercase
        result = gen.toggle_uppercase()
        
        assert result == (not initial)
        assert gen.include_uppercase == (not initial)
        
        # Toggle back
        result = gen.toggle_uppercase()
        assert result == initial

    def test_toggle_lowercase(self):
        """Test toggling lowercase characters."""
        gen = PasswordGenerator()
        
        initial = gen.include_lowercase
        result = gen.toggle_lowercase()
        
        assert result == (not initial)
        assert gen.include_lowercase == (not initial)

    def test_toggle_numbers(self):
        """Test toggling number characters."""
        gen = PasswordGenerator()
        
        initial = gen.include_numbers
        result = gen.toggle_numbers()
        
        assert result == (not initial)
        assert gen.include_numbers == (not initial)

    def test_toggle_symbols(self):
        """Test toggling symbol characters."""
        gen = PasswordGenerator()
        
        initial = gen.include_symbols
        result = gen.toggle_symbols()
        
        assert result == (not initial)
        assert gen.include_symbols == (not initial)


class TestSetLength:
    """Tests for setting password length."""

    def test_set_length(self):
        """Test setting password length."""
        gen = PasswordGenerator()
        
        gen.set_length(32)
        
        assert gen.length == 32
        assert len(gen.generate()) == 32

    def test_set_length_validates(self):
        """Test that setting invalid length raises error."""
        gen = PasswordGenerator()
        
        with pytest.raises(ValueError, match="at least 1"):
            gen.set_length(0)
        
        with pytest.raises(ValueError, match="at least 1"):
            gen.set_length(-5)


class TestPasswordWithLimitedCharsets:
    """Tests for generating passwords with limited character sets."""

    def test_uppercase_and_lowercase_only(self):
        """Test generating password with only uppercase and lowercase."""
        gen = PasswordGenerator()
        gen.include_numbers = False
        gen.include_symbols = False
        
        password = gen.generate()
        
        assert any(c in string.ascii_uppercase for c in password)
        assert any(c in string.ascii_lowercase for c in password)
        assert not any(c in string.digits for c in password)
        assert not any(c in string.punctuation for c in password)

    def test_numbers_and_symbols_only(self):
        """Test generating password with only numbers and symbols."""
        gen = PasswordGenerator()
        gen.include_uppercase = False
        gen.include_lowercase = False
        
        password = gen.generate()
        
        assert not any(c in string.ascii_letters for c in password)
        assert any(c in string.digits for c in password)
        assert any(c in string.punctuation for c in password)

    def test_single_charset(self):
        """Test generating password with single charset."""
        # Only lowercase
        gen = PasswordGenerator(length=20)
        gen.include_uppercase = False
        gen.include_numbers = False
        gen.include_symbols = False
        
        password = gen.generate()
        
        assert all(c in string.ascii_lowercase for c in password)
        assert len(password) == 20