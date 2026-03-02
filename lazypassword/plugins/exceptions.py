"""Plugin exceptions for lazypassword."""


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin is not found."""
    pass


class EncryptionError(PluginError):
    """Raised when encryption or decryption fails."""
    pass
