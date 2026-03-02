"""Entry point for LazyPassword application."""

import os
import sys
from pathlib import Path

from .cli import parse_args


def main():
    """Main entry point for LazyPassword."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Determine vault path
        if args.vault:
            vault_path = Path(args.vault).expanduser().resolve()
        else:
            # Default: ~/.config/lazypassword/vault.lpv
            config_dir = Path.home() / ".config" / "lazypassword"
            vault_path = config_dir / "vault.lpv"
        
        # Create config directory if it doesn't exist
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Import and launch the app
        from .app import LazyPasswordApp
        
        app = LazyPasswordApp(
            vault_path=vault_path,
            readonly=args.readonly
        )
        app.run()
        
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
