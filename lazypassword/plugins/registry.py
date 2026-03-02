"""Plugin registry for managing encryption plugins."""

from typing import Dict, List, Optional, Type

from .base import EncryptionPlugin
from .exceptions import PluginNotFoundError


class PluginRegistry:
    """Central registry for encryption plugins."""
    
    _instance: Optional['PluginRegistry'] = None
    
    def __new__(cls) -> 'PluginRegistry':
        """Singleton pattern to ensure one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._plugins: Dict[str, Type[EncryptionPlugin]] = {}
            cls._instance._default_identifier: str = "aes-256-gcm"
        return cls._instance
    
    def register(self, plugin_class: Type[EncryptionPlugin]) -> None:
        """Register a plugin class.
        
        Args:
            plugin_class: Plugin class inheriting from EncryptionPlugin
            
        Raises:
            ValueError: If plugin doesn't have required attributes
        """
        if not issubclass(plugin_class, EncryptionPlugin):
            raise ValueError(f"Plugin must inherit from EncryptionPlugin: {plugin_class}")
        
        if not plugin_class.identifier:
            raise ValueError(f"Plugin must have an identifier: {plugin_class}")
        
        self._plugins[plugin_class.identifier] = plugin_class
    
    def get_plugin(self, identifier: str) -> EncryptionPlugin:
        """Get a plugin instance by identifier.
        
        Args:
            identifier: Plugin identifier (e.g., "aes-256-gcm")
            
        Returns:
            EncryptionPlugin: Plugin instance
            
        Raises:
            PluginNotFoundError: If plugin not found or not available
        """
        if identifier not in self._plugins:
            raise PluginNotFoundError(f"Plugin not found: {identifier}")
        
        plugin_class = self._plugins[identifier]
        
        if not plugin_class.is_available():
            raise PluginNotFoundError(f"Plugin not available: {identifier}")
        
        return plugin_class()
    
    def list_available_plugins(self) -> List[Type[EncryptionPlugin]]:
        """List all available plugins.
        
        Returns:
            list: List of available plugin classes
        """
        return [p for p in self._plugins.values() if p.is_available()]
    
    def list_all_plugins(self) -> List[Type[EncryptionPlugin]]:
        """List all registered plugins (including unavailable).
        
        Returns:
            list: List of all registered plugin classes
        """
        return list(self._plugins.values())
    
    def get_default_plugin(self) -> EncryptionPlugin:
        """Get the default plugin instance (AES-256-GCM).
        
        Returns:
            EncryptionPlugin: Default plugin instance
            
        Raises:
            PluginNotFoundError: If default plugin not available
        """
        return self.get_plugin(self._default_identifier)
    
    def get_default_identifier(self) -> str:
        """Get the default plugin identifier.
        
        Returns:
            str: Default plugin identifier
        """
        return self._default_identifier
    
    def set_default_plugin(self, identifier: str) -> None:
        """Set the default plugin.
        
        Args:
            identifier: Plugin identifier to use as default
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if identifier not in self._plugins:
            raise PluginNotFoundError(f"Cannot set default: plugin not found: {identifier}")
        
        self._default_identifier = identifier
    
    def is_registered(self, identifier: str) -> bool:
        """Check if a plugin is registered.
        
        Args:
            identifier: Plugin identifier
            
        Returns:
            bool: True if plugin is registered
        """
        return identifier in self._plugins
    
    def is_available(self, identifier: str) -> bool:
        """Check if a plugin is registered and available.
        
        Args:
            identifier: Plugin identifier
            
        Returns:
            bool: True if plugin is registered and available
        """
        if identifier not in self._plugins:
            return False
        return self._plugins[identifier].is_available()


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry.
    
    Returns:
        PluginRegistry: Global registry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
