"""CLI argument parsing for LazyPassword."""

import argparse
import sys
from typing import Optional

from . import __version__


def parse_args(args: Optional[list] = None):
    """Parse command line arguments.
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="lazypassword",
        description="A simple, secure password manager for the lazy."
    )
    
    parser.add_argument(
        "--vault",
        type=str,
        metavar="PATH",
        help="Path to vault file (default: ~/.config/lazypassword/vault.lpv)"
    )
    
    parser.add_argument(
        "--readonly",
        action="store_true",
        help="Open vault in read-only mode"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    return parser.parse_args(args)
