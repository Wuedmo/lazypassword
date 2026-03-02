"""Plugin loader for dynamically loading plugins."""

import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Optional

from .base import EncryptionPlugin
from .exceptions import PluginError
from .registry import get_registry


def load_builtin_plugins() -> None:
    """Load all built-in plugins."""
    registry = get_registry()
    
    # Import and register built-in plugins
    from .builtins import AES256GCMPlugin, ChaCha20Poly1305Plugin
    
    registry.register(AES256GCMPlugin)
    registry.register(ChaCha20Poly1305Plugin)


def load_plugins(directory: str) -> List[str]:
    """Dynamically load plugins from a directory.
    
    Scans the directory for Python files and attempts to load
    any classes that inherit from EncryptionPlugin.
    
    Args:
        directory: Path to directory containing plugin files
        
    Returns:
        list: List of successfully loaded plugin identifiers
    """
    registry = get_registry()
    loaded: List[str] = []
    
    plugin_dir = Path(directory)
    if not plugin_dir.exists() or not plugin_dir.is_dir():
        return loaded
    
    # Add directory to Python path temporarily
    if str(plugin_dir) not in sys.path:
        sys.path.insert(0, str(plugin_dir))
    
    # Scan for Python files
    for file_path in plugin_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue
        
        try:
            loaded_from_file = _load_plugin_file(file_path)
            loaded.extend(loaded_from_file)
        except Exception as e:
            # Log but don't fail - individual plugin failures shouldn't break everything
            print(f"Warning: Failed to load plugin from {file_path}: {e}")
    
    return loaded


def _load_plugin_file(file_path: Path) -> List[str]:
    """Load plugins from a single Python file.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        list: List of loaded plugin identifiers
    """
    registry = get_registry()
    loaded: List[str] = []
    
    # Load module from file
    spec = importlib.util.spec_from_file_location(
        file_path.stem,
        file_path
    )
    
    if spec is None or spec.loader is None:
        raise PluginError(f"Cannot load module from {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[file_path.stem] = module
    spec.loader.exec_module(module)
    
    # Find plugin classes in module
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        
        # Check if it's a class (not instance) and inherits from EncryptionPlugin
        if (isinstance(attr, type) and 
            issubclass(attr, EncryptionPlugin) and 
            attr is not EncryptionPlugin and
            attr.identifier):  # Has an identifier set
            
            try:
                registry.register(attr)
                loaded.append(attr.identifier)
            except Exception as e:
                print(f"Warning: Failed to register plugin {attr_name}: {e}")
    
    return loaded


def load_user_plugins() -> List[str]:
    """Load plugins from user configuration directory.
    
    Loads plugins from ~/.config/lazypassword/plugins/
    
    Returns:
        list: List of loaded plugin identifiers
    """
    user_plugin_dir = Path.home() / ".config" / "lazypassword" / "plugins"
    return load_plugins(str(user_plugin_dir))


def get_default_user_plugin_dir() -> str:
    """Get the default user plugin directory path.
    
    Returns:
        str: Path to user plugin directory
    """
    return str(Path.home() / ".config" / "lazypassword" / "plugins")


def ensure_user_plugin_dir() -> str:
    """Ensure the user plugin directory exists.
    
    Returns:
        str: Path to user plugin directory
    """
    plugin_dir = Path.home() / ".config" / "lazypassword" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    return str(plugin_dir)


def init_plugins() -> None:
    """Initialize the plugin system.
    
    Loads built-in plugins and user plugins.
    """
    # Load built-in plugins first
    load_builtin_plugins()
    
    # Then load user plugins (they can override built-ins if needed)
    try:
        load_user_plugins()
    except Exception as e:
        # Don't fail if user plugins can't load
        print(f"Warning: Failed to load user plugins: {e}")
