"""LazyPassword - A simple password manager."""

__version__ = "0.1.0"
__author__ = "WdmMaster"

# Lazy imports to avoid Windows editable install issues
def _lazy_import(name):
    import importlib
    return importlib.import_module(f"." + name, package=__name__)

__all__ = ["__version__"]
