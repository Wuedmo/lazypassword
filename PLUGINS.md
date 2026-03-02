# Writing Custom Encryption Plugins for LazyPassword

LazyPassword's plugin architecture allows you to add custom encryption algorithms. This guide shows you how to write your own encryption plugin.

## Overview

Encryption plugins must inherit from `EncryptionPlugin` and implement the required methods. Your plugin can be loaded from:

1. The built-in plugins directory
2. Your user plugins directory: `~/.config/lazypassword/plugins/`

## Plugin Structure

A minimal encryption plugin looks like this:

```python
from lazypassword.plugins import EncryptionPlugin
from lazypassword.plugins.exceptions import EncryptionError

class MyEncryptionPlugin(EncryptionPlugin):
    """My custom encryption algorithm."""
    
    # Required metadata
    name = "My Encryption"
    identifier = "my-encryption"
    description = "Description of my encryption method"
    security_level = 4  # 1-5 rating
    
    def __init__(self):
        super().__init__()
        self._nonce = b""
    
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """Encrypt data.
        
        Args:
            data: Plaintext data to encrypt
            key: Encryption key (must be get_key_size() bytes)
            **kwargs: Additional parameters
            
        Returns:
            bytes: Encrypted data
        """
        # Your encryption logic here
        # Store any parameters needed for decryption in self._params
        
        self._params['nonce'] = self._nonce.hex()
        return encrypted_data
    
    def decrypt(self, encrypted_data: bytes, key: bytes, **kwargs) -> bytes:
        """Decrypt data.
        
        Args:
            encrypted_data: Encrypted data from encrypt()
            key: Encryption key
            **kwargs: Parameters (usually from serialize_params)
            
        Returns:
            bytes: Decrypted plaintext
        """
        # Your decryption logic here
        
        return plaintext
    
    def get_key_size(self) -> int:
        """Return the required key size in bytes."""
        return 32  # 256 bits
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if dependencies are installed."""
        try:
            # Import any required libraries
            import my_crypto_library
            return True
        except ImportError:
            return False
```

## Installation

### User Plugins Directory

Create the user plugins directory:

```bash
mkdir -p ~/.config/lazypassword/plugins
```

Save your plugin as a Python file:

```bash
# Save the plugin
~/.config/lazypassword/plugins/my_plugin.py
```

The plugin will be automatically loaded on startup.

## Vault Format

Your encrypted data will be stored in the vault with a header:

```
[version:1][plugin_id_len][plugin_id][salt:32][your_encrypted_data]
```

## Example: Fernet-Based Plugin

Here's a complete example using Fernet from the `cryptography` library:

```python
# ~/.config/lazypassword/plugins/fernet_plugin.py

from cryptography.fernet import Fernet, InvalidToken
from lazypassword.plugins import EncryptionPlugin
from lazypassword.plugins.exceptions import EncryptionError
import base64

class FernetPlugin(EncryptionPlugin):
    """Fernet symmetric encryption plugin."""
    
    name = "Fernet Encryption"
    identifier = "fernet"
    description = "Fernet guarantees that a message encrypted using it cannot be manipulated or read without the key."
    security_level = 4
    
    def __init__(self):
        super().__init__()
    
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """Encrypt data using Fernet."""
        if len(key) < 32:
            raise EncryptionError("Key must be at least 32 bytes")
        
        # Fernet requires base64-encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(key[:32])
        f = Fernet(fernet_key)
        
        encrypted = f.encrypt(data)
        return encrypted
    
    def decrypt(self, encrypted_data: bytes, key: bytes, **kwargs) -> bytes:
        """Decrypt data using Fernet."""
        if len(key) < 32:
            raise EncryptionError("Key must be at least 32 bytes")
        
        fernet_key = base64.urlsafe_b64encode(key[:32])
        f = Fernet(fernet_key)
        
        try:
            return f.decrypt(encrypted_data)
        except InvalidToken:
            raise EncryptionError("Decryption failed: invalid token")
    
    def get_key_size(self) -> int:
        """Returns 32 bytes (256 bits)."""
        return 32
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if cryptography library is available."""
        try:
            from cryptography.fernet import Fernet
            return True
        except ImportError:
            return False
```

## Testing Your Plugin

You can test your plugin before installing it:

```python
from lazypassword.plugins.registry import get_registry

# Register your plugin
from my_plugin import MyEncryptionPlugin
registry = get_registry()
registry.register(MyEncryptionPlugin)

# Get instance and test
plugin = registry.get_plugin("my-encryption")

# Test encryption/decryption
key = b"0" * plugin.get_key_size()  # Test key
data = b"Hello, World!"

encrypted = plugin.encrypt(data, key)
decrypted = plugin.decrypt(encrypted, key)

assert decrypted == data
print("Plugin test passed!")
```

## Security Considerations

1. **Never hardcode keys** - Always use the key passed to encrypt/decrypt
2. **Validate key size** - Check that the key is the expected length
3. **Use authenticated encryption** - Prefer algorithms that authenticate data integrity
4. **Store nonces/IVs** - Store any required parameters in `self._params`
5. **Clear sensitive data** - Wipe sensitive data from memory when possible

## Error Handling

Always raise `EncryptionError` for encryption/decryption failures:

```python
from lazypassword.plugins.exceptions import EncryptionError

try:
    # Your encryption logic
    result = cipher.encrypt(data)
except Exception as e:
    raise EncryptionError(f"Encryption failed: {e}")
```

## Plugin Discovery

Plugins are loaded from:

1. Built-in plugins (shipped with LazyPassword)
2. User plugins (`~/.config/lazypassword/plugins/`)

Each plugin is loaded from `.py` files. All classes inheriting from `EncryptionPlugin` with a non-empty `identifier` attribute are registered.

## Troubleshooting

### Plugin not showing up

1. Check `identifier` is unique and not empty
2. Check the plugin file is in the correct directory
3. Verify `is_available()` returns `True` (dependencies installed)
4. Check for import errors in the plugin file

### Encryption fails

1. Verify key size matches `get_key_size()`
2. Check you're raising `EncryptionError` for failures
3. Look at the Lazypassword logs for error messages

### Decryption fails

1. Ensure nonce/IV is correctly stored and retrieved
2. Verify the algorithm produces deterministic output
3. Check for any encoding issues

## Built-in Plugins Reference

LazyPassword includes these built-in plugins:

- **aes-256-gcm**: AES-256-GCM authenticated encryption
- **chacha20-poly1305**: ChaCha20-Poly1305 authenticated encryption

You can reference their implementation at:
`lazypassword/plugins/builtins/`
