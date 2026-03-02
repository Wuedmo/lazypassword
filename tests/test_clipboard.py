"""Tests for clipboard operations."""

import pytest
import sys
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from lazypassword.utils.clipboard import ClipboardManager


class TestClipboardManagerInit:
    """Tests for ClipboardManager initialization."""

    def test_init_detects_os(self):
        """Test that ClipboardManager detects OS on init."""
        with patch('platform.system') as mock_system:
            mock_system.return_value = "Darwin"
            
            manager = ClipboardManager()
            
            assert manager._os == "darwin"

    def test_init_sets_commands(self):
        """Test that commands are set during init."""
        with patch('platform.system') as mock_system:
            mock_system.return_value = "Darwin"
            
            manager = ClipboardManager()
            
            assert manager._copy_cmd is not None
            assert manager._clear_cmd is not None


class TestCopy:
    """Tests for copy functionality."""

    @patch('pyperclip.copy')
    @patch('platform.system')
    def test_copy_with_pyperclip(self, mock_system, mock_pyperclip):
        """Test copying with pyperclip."""
        mock_system.return_value = "Linux"
        
        manager = ClipboardManager()
        result = manager.copy("test text")
        
        assert result == True
        mock_pyperclip.assert_called_once_with("test text")

    @patch('pyperclip.copy')
    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_copy_fallback_to_command(self, mock_system, mock_popen, mock_pyperclip):
        """Test fallback to OS command when pyperclip fails."""
        mock_system.return_value = "Darwin"
        mock_pyperclip.side_effect = ImportError()
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        manager = ClipboardManager()
        result = manager.copy("test text")
        
        assert result == True

    @patch('pyperclip.copy')
    @patch('platform.system')
    def test_copy_pyperclip_exception(self, mock_system, mock_pyperclip):
        """Test handling of pyperclip exception."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = Exception("Copy failed")
        
        # Mock fallback command - needs to return False when command fails
        with patch.object(ClipboardManager, 'get_os_clipboard_command', return_value=(None, None)):
            manager = ClipboardManager()
            result = manager.copy("test")
            # Should fall back and fail gracefully when no command available
            assert result == False

    @patch('pyperclip.copy')
    @patch('platform.system')
    def test_copy_no_command_available(self, mock_system, mock_pyperclip):
        """Test copying when no command is available."""
        mock_system.return_value = "UnknownOS"
        mock_pyperclip.side_effect = ImportError()
        
        manager = ClipboardManager()
        result = manager.copy("test text")
        
        assert result == False


class TestClear:
    """Tests for clear functionality."""

    @patch('pyperclip.copy')
    @patch('platform.system')
    def test_clear_with_pyperclip(self, mock_system, mock_pyperclip):
        """Test clearing with pyperclip."""
        mock_system.return_value = "Linux"
        
        manager = ClipboardManager()
        result = manager.clear()
        
        assert result == True
        mock_pyperclip.assert_called_once_with("")

    @patch('pyperclip.copy')
    @patch('subprocess.run')
    @patch('platform.system')
    def test_clear_fallback_to_command(self, mock_system, mock_run, mock_pyperclip):
        """Test fallback to OS command when clearing."""
        mock_system.return_value = "Darwin"
        mock_pyperclip.side_effect = ImportError()
        
        mock_run.return_value = MagicMock(returncode=0)
        
        manager = ClipboardManager()
        result = manager.clear()
        
        assert result == True


class TestGetOSClipboardCommand:
    """Tests for OS-specific clipboard command detection."""

    @patch('platform.system')
    def test_macos_commands(self, mock_system):
        """Test macOS clipboard commands."""
        mock_system.return_value = "Darwin"
        
        manager = ClipboardManager()
        copy_cmd, clear_cmd = manager.get_os_clipboard_command()
        
        assert copy_cmd == ["pbcopy"]
        assert clear_cmd == ["pbcopy"]

    @patch('platform.system')
    def test_windows_commands(self, mock_system):
        """Test Windows clipboard commands."""
        mock_system.return_value = "Windows"
        
        manager = ClipboardManager()
        copy_cmd, clear_cmd = manager.get_os_clipboard_command()
        
        assert copy_cmd == ["clip"]
        # Clear command uses cmd /c echo off | clip
        assert clear_cmd == ["cmd", "/c", "echo off | clip"]

    @patch('platform.system')
    @patch('shutil.which')
    def test_linux_xclip_commands(self, mock_which, mock_system):
        """Test Linux xclip commands."""
        mock_system.return_value = "Linux"
        mock_which.side_effect = lambda x: x if x == "xclip" else None
        
        # Mock environ to not be Wayland
        with patch.dict('os.environ', {}, clear=True):
            manager = ClipboardManager()
            copy_cmd, clear_cmd = manager.get_os_clipboard_command()
            
            assert "xclip" in copy_cmd
            assert "xclip" in clear_cmd

    @patch('platform.system')
    @patch('shutil.which')
    def test_linux_xsel_commands(self, mock_which, mock_system):
        """Test Linux xsel fallback commands."""
        mock_system.return_value = "Linux"
        mock_which.side_effect = lambda x: x if x == "xsel" else None
        
        with patch.dict('os.environ', {}, clear=True):
            manager = ClipboardManager()
            copy_cmd, clear_cmd = manager.get_os_clipboard_command()
            
            assert "xsel" in copy_cmd
            assert "xsel" in clear_cmd

    @patch('platform.system')
    @patch('shutil.which')
    def test_linux_wlcopy_commands(self, mock_which, mock_system):
        """Test Linux wl-copy (Wayland) commands."""
        mock_system.return_value = "Linux"
        mock_which.side_effect = lambda x: x if x == "wl-copy" else None
        
        with patch.dict('os.environ', {'WAYLAND_DISPLAY': 'wayland-1'}):
            manager = ClipboardManager()
            copy_cmd, clear_cmd = manager.get_os_clipboard_command()
            
            assert "wl-copy" in copy_cmd

    @patch('platform.system')
    @patch('shutil.which')
    def test_linux_no_commands_available(self, mock_which, mock_system):
        """Test when no clipboard commands are available on Linux."""
        mock_system.return_value = "Linux"
        mock_which.return_value = None
        
        with patch.dict('os.environ', {}, clear=True):
            manager = ClipboardManager()
            copy_cmd, clear_cmd = manager.get_os_clipboard_command()
            
            assert copy_cmd is None
            assert clear_cmd is None

    @patch('platform.system')
    def test_unknown_os_commands(self, mock_system):
        """Test unknown OS returns None commands."""
        mock_system.return_value = "UnknownOS"
        
        manager = ClipboardManager()
        copy_cmd, clear_cmd = manager.get_os_clipboard_command()
        
        assert copy_cmd is None
        assert clear_cmd is None


class TestCopyCommandExecution:
    """Tests for copy command execution."""

    @patch('pyperclip.copy')
    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_copy_command_list(self, mock_system, mock_popen, mock_pyperclip):
        """Test copy with command as list."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        manager = ClipboardManager()
        manager._copy_cmd = ["test-copy-cmd"]
        result = manager.copy("test text")
        
        mock_popen.assert_called_once()
        assert result == True

    @patch('pyperclip.copy')
    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_copy_command_string(self, mock_system, mock_popen, mock_pyperclip):
        """Test copy with command as string (uses shell=True)."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        
        manager = ClipboardManager()
        manager._copy_cmd = "copy-cmd"
        result = manager.copy("test text")
        
        call_args = mock_popen.call_args
        assert call_args[1]['shell'] == True

    @patch('pyperclip.copy')
    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_copy_command_failure(self, mock_system, mock_popen, mock_pyperclip):
        """Test copy when command fails."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        
        mock_proc = MagicMock()
        mock_proc.returncode = 1  # Failure
        mock_popen.return_value = mock_proc
        
        manager = ClipboardManager()
        manager._copy_cmd = ["test-copy-cmd"]
        result = manager.copy("test text")
        
        assert result == False

    @patch('pyperclip.copy')
    @patch('subprocess.Popen')
    @patch('platform.system')
    def test_copy_exception(self, mock_system, mock_popen, mock_pyperclip):
        """Test copy when exception occurs."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        mock_popen.side_effect = Exception("Command failed")
        
        manager = ClipboardManager()
        manager._copy_cmd = ["test-copy-cmd"]
        result = manager.copy("test text")
        
        assert result == False


class TestClearCommandExecution:
    """Tests for clear command execution."""

    @patch('pyperclip.copy')
    @patch('subprocess.run')
    @patch('platform.system')
    def test_clear_command_list(self, mock_system, mock_run, mock_pyperclip):
        """Test clear with command as list."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        
        mock_run.return_value = MagicMock(returncode=0)
        
        manager = ClipboardManager()
        manager._clear_cmd = ["test-clear-cmd"]
        result = manager.clear()
        
        mock_run.assert_called_once()
        assert result == True

    @patch('pyperclip.copy')
    @patch('subprocess.run')
    @patch('platform.system')
    def test_clear_command_failure(self, mock_system, mock_run, mock_pyperclip):
        """Test clear when command fails."""
        mock_system.return_value = "Linux"
        mock_pyperclip.side_effect = ImportError()
        
        mock_run.return_value = MagicMock(returncode=1)
        
        manager = ClipboardManager()
        manager._clear_cmd = ["test-clear-cmd"]
        result = manager.clear()
        
        assert result == False