"""Encryption plugins for lazypassword.

This package provides a plugin architecture for encryption algorithms,
allowing users to select different encryption methods and even write
custom plugins.

Example:
    from lazypassword.plugins import EncryptionPlugin, get_registry
    
    # List available plugins
    registry = get_registry()
    for plugin_class in registry.list_available_plugins():
        print(f"{plugin_class.name}: {plugin_class.description}")
    
    # Get a plugin instance
    plugin = registry.get_plugin("aes-256-gcm")
    
    # Encrypt data
    encrypted = plugin.encrypt(data, key)

Writing Custom Plugins:
    Create a Python file in ~/.config/lazypassword/plugins/ with:
    
    from lazypassword.plugins import EncryptionPlugin
    
    class MyPlugin(EncryptionPlugin):
        name = "My Encryption"
        identifier = "my-encryption"
        description = "Description of my encryption method"
        security_level = 4
        
        def encrypt(self, data, key, **kwargs):
            # Your encryption logic
            return encrypted_data
        
        def decrypt(self, encrypted_data, key, **kwargs):
            # Your decryption logic
            return plaintext
        
        def get_key_size(self):
            return 32  # 256 bits
        
        @classmethod
        def is_available(cls):
            return True  # Check dependencies
"""

from .base import EncryptionPlugin
from .exceptions import EncryptionError, PluginError, PluginNotFoundError
from .loader import (
    init_plugins,
    load_builtin_plugins,
    load_plugins,
    load_user_plugins,
    ensure_user_plugin_dir,
)
from .registry import PluginRegistry, get_registry

__all__ = [
    # Base classes
    "EncryptionPlugin",
    # Exceptions
    "EncryptionError",
    "PluginError",
    "PluginNotFoundError",
    # Registry
    "PluginRegistry",
    "get_registry",
    # Loader
    "init_plugins",
    "load_builtin_plugins",
    "load_plugins",
    "load_user_plugins",
    "ensure_user_plugin_dir",
]
