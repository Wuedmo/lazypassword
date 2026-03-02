"""Cross-platform clipboard operations."""

import platform
import subprocess
import shutil
from typing import Optional, Tuple


class ClipboardManager:
    """Manage clipboard operations across different operating systems."""
    
    def __init__(self):
        """Initialize clipboard manager and detect OS."""
        self._os = platform.system().lower()
        self._copy_cmd, self._clear_cmd = self.get_os_clipboard_command()
    
    def copy(self, text: str) -> bool:
        """Copy text to clipboard.
        
        Tries pyperclip first, falls back to OS-specific commands.
        
        Args:
            text: Text to copy to clipboard
            
        Returns:
            True if successful, False otherwise
        """
        # Try pyperclip first
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            pass  # Fall through to direct commands
        except Exception:
            pass  # Fall through to direct commands
        
        # Fallback to OS-specific commands
        if not self._copy_cmd:
            return False
        
        try:
            if isinstance(self._copy_cmd, list):
                # Command with arguments
                proc = subprocess.Popen(
                    self._copy_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                proc.communicate(text.encode('utf-8'))
                return proc.returncode == 0
            else:
                # Single command string
                proc = subprocess.Popen(
                    self._copy_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=True
                )
                proc.communicate(text.encode('utf-8'))
                return proc.returncode == 0
        except Exception:
            return False
    
    def clear(self) -> bool:
        """Clear the clipboard.
        
        Tries pyperclip first, falls back to OS-specific commands.
        
        Returns:
            True if successful, False otherwise
        """
        # Try pyperclip first
        try:
            import pyperclip
            pyperclip.copy("")
            return True
        except ImportError:
            pass
        except Exception:
            pass
        
        # Fallback to OS-specific commands
        if not self._clear_cmd:
            return False
        
        try:
            if isinstance(self._clear_cmd, list):
                proc = subprocess.run(
                    self._clear_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return proc.returncode == 0
            else:
                proc = subprocess.run(
                    self._clear_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return proc.returncode == 0
        except Exception:
            return False
    
    def get_os_clipboard_command(self) -> Tuple[Optional[list], Optional[list]]:
        """Get the appropriate clipboard commands for the current OS.
        
        Returns:
            Tuple of (copy_command, clear_command) where each is either
            a list of command arguments or None if not available
        """
        if self._os == "darwin":  # macOS
            return ["pbcopy"], ["pbcopy"]
        
        elif self._os == "windows":
            return ["clip"], ["cmd", "/c", "echo off | clip"]
        
        elif self._os == "linux":
            # Check for Wayland
            wayland_display = platform.os.environ.get("WAYLAND_DISPLAY") if hasattr(platform, 'os') else None
            
            # Try wl-copy for Wayland
            if wayland_display and shutil.which("wl-copy"):
                return ["wl-copy"], ["wl-copy", "--clear"]
            
            # Try xclip for X11
            if shutil.which("xclip"):
                return (
                    ["xclip", "-selection", "clipboard", "-in"],
                    ["xclip", "-selection", "clipboard", "-in", "/dev/null"]
                )
            
            # Try xsel as fallback
            if shutil.which("xsel"):
                return (
                    ["xsel", "--clipboard", "--input"],
                    ["xsel", "--clipboard", "--delete"]
                )
            
            # No clipboard tool found
            return None, None
        
        else:
            # Unknown OS
            return None, None
