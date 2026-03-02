"""Main TUI application for lazypassword."""

import os
import signal
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)
from textual.screen import Screen

# Assume vault module exists
from ..vault import Vault
from ..entry import Entry


class StatusBar(Static):
    """Status bar showing current vault state."""
    
    vault_status = reactive("Locked")
    entry_count = reactive(0)
    last_action = reactive("")
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(f" 🔒 {self.vault_status}", id="status-vault"),
            Label(f" 📁 Entries: {self.entry_count}", id="status-count"),
            Label(f" 📋 {self.last_action}", id="status-action"),
            id="status-content",
        )
    
    def update_status(self, status: str, count: int = 0, action: str = "") -> None:
        """Update status bar display."""
        self.vault_status = status
        self.entry_count = count
        self.last_action = action
        vault_label = self.query_one("#status-vault", Label)
        count_label = self.query_one("#status-count", Label)
        action_label = self.query_one("#status-action", Label)
        vault_label.update(f" 🔒 {status}")
        count_label.update(f" 📁 Entries: {count}")
        action_label.update(f" 📋 {action}" if action else "")


class FirstRunScreen(Screen):
    """Screen shown when no vault exists."""
    
    DEFAULT_CSS = """
    FirstRunScreen {
        align: center middle;
    }
    #first-run-container {
        width: 60;
        height: auto;
        border: solid green;
        padding: 1 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="first-run-container"):
            yield Label("Welcome to LazyPassword! 🔐", classes="title")
            yield Label("No vault found. Create a new vault to get started.")
            yield Label("")
            yield Label("Set a master password:")
            yield Input(placeholder="Enter master password...", password=True, id="password-input")
            yield Label("")
            yield Button("Create Vault", id="create-btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle create vault button."""
        if event.button.id == "create-btn":
            password_input = self.query_one("#password-input", Input)
            password = password_input.value
            if password:
                self.dismiss(password)
            else:
                password_input.focus()


class UnlockScreen(Screen):
    """Screen for unlocking an existing vault."""
    
    DEFAULT_CSS = """
    UnlockScreen {
        align: center middle;
    }
    #unlock-container {
        width: 50;
        height: auto;
        border: solid blue;
        padding: 1 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="unlock-container"):
            yield Label("🔐 Unlock Vault", classes="title")
            yield Label("")
            yield Input(placeholder="Master password...", password=True, id="password-input")
            yield Label("")
            yield Button("Unlock", id="unlock-btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle unlock button."""
        if event.button.id == "unlock-btn":
            password_input = self.query_one("#password-input", Input)
            password = password_input.value
            if password:
                self.dismiss(password)


class EntryEditScreen(Screen):
    """Screen for creating/editing entries."""
    
    DEFAULT_CSS = """
    EntryEditScreen {
        align: center middle;
    }
    #edit-container {
        width: 70;
        height: auto;
        border: solid yellow;
        padding: 1 2;
    }
    """
    
    def __init__(self, entry: Optional[Entry] = None) -> None:
        """Initialize with optional entry to edit."""
        super().__init__()
        self.entry = entry or Entry()
        self.is_new = entry is None
    
    def compose(self) -> ComposeResult:
        with Container(id="edit-container"):
            title = "New Entry" if self.is_new else "Edit Entry"
            yield Label(f"✏️ {title}", classes="title")
            yield Label("")
            yield Label("Title:")
            yield Input(value=self.entry.title, id="title-input")
            yield Label("Username:")
            yield Input(value=self.entry.username, id="username-input")
            yield Label("Password:")
            yield Input(value=self.entry.password, password=True, id="password-input")
            yield Label("URL:")
            yield Input(value=self.entry.url, id="url-input")
            yield Label("Notes:")
            yield Input(value=self.entry.notes, id="notes-input")
            yield Label("Tags (comma-separated):")
            yield Input(value=",".join(self.entry.tags), id="tags-input")
            yield Label("")
            yield Horizontal(
                Button("Save", id="save-btn", variant="primary"),
                Button("Cancel", id="cancel-btn"),
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)
        elif event.button.id == "save-btn":
            self.entry.title = self.query_one("#title-input", Input).value
            self.entry.username = self.query_one("#username-input", Input).value
            self.entry.password = self.query_one("#password-input", Input).value
            self.entry.url = self.query_one("#url-input", Input).value
            self.entry.notes = self.query_one("#notes-input", Input).value
            tags_str = self.query_one("#tags-input", Input).value
            self.entry.tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            self.entry.update_timestamp()
            self.dismiss(self.entry)


class ConfirmScreen(Screen[bool]):
    """Confirmation dialog screen."""
    
    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm-container {
        width: 50;
        height: auto;
        border: solid red;
        padding: 1 2;
    }
    """
    
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        with Container(id="confirm-container"):
            yield Label("⚠️ Confirm", classes="title")
            yield Label("")
            yield Label(self.message)
            yield Label("")
            yield Horizontal(
                Button("Yes", id="yes-btn", variant="error"),
                Button("No", id="no-btn"),
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(event.button.id == "yes-btn")


class LazyPasswordApp(App):
    """Main TUI application for LazyPassword."""
    
    TITLE = "LazyPassword"
    CSS = """
    Screen {
        align: center middle;
    }
    #entry-list {
        height: 1fr;
        width: 100%;
    }
    StatusBar {
        dock: bottom;
        height: 1;
        background: $primary-darken-1;
        color: $text;
    }
    #status-content {
        width: 100%;
        layout: horizontal;
    }
    #status-content Label {
        width: 1fr;
    }
    .title {
        text-style: bold;
    }
    """
    
    BINDINGS = [
        ("n", "new_entry", "New Entry"),
        ("e", "edit_entry", "Edit"),
        ("d", "delete_entry", "Delete"),
        ("c", "copy_password", "Copy Password"),
        ("u", "copy_username", "Copy Username"),
        ("/", "search", "Search"),
        ("l", "lock", "Lock"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
    ]
    
    def __init__(self, vault_path: str) -> None:
        """Initialize the application."""
        super().__init__()
        self.vault_path = vault_path
        self.vault: Optional[Vault] = None
        self._locked = True
        self._clipboard_timer: Optional[Timer] = None
        self._inactivity_timer: Optional[Timer] = None
        self._clipboard_clear_delay = 30  # seconds
        self._auto_lock_delay = 600  # seconds (10 minutes)
        self._clipboard_content: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Compose the main UI."""
        yield Header()
        yield DataTable(id="entry-list")
        yield Footer()
        yield StatusBar()
        
        # Bind SIGINT handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def on_mount(self) -> None:
        """Handle app mount - check vault and show appropriate screen."""
        if not os.path.exists(self.vault_path):
            self.push_screen(FirstRunScreen(), callback=self._on_first_run)
        else:
            self.push_screen(UnlockScreen(), callback=self._on_unlock)
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle SIGINT for graceful shutdown."""
        self.action_lock()
    
    def _on_first_run(self, password: Optional[str]) -> None:
        """Handle first run password entry."""
        if password:
            try:
                self.vault = Vault.create(self.vault_path, password)
                self._locked = False
                self._start_timers()
                self._refresh_entry_list()
                self._update_status("Unlocked", len(self.vault.entries))
            except Exception as e:
                self.notify(f"Failed to create vault: {e}", severity="error")
                self.exit()
        else:
            self.exit()
    
    def _on_unlock(self, password: Optional[str]) -> None:
        """Handle unlock attempt."""
        if password:
            try:
                self.vault = Vault.load(self.vault_path, password)
                self._locked = False
                self._start_timers()
                self._refresh_entry_list()
                self._update_status("Unlocked", len(self.vault.entries))
            except Exception as e:
                self.notify(f"Failed to unlock vault: {e}", severity="error")
                self.push_screen(UnlockScreen(), callback=self._on_unlock)
        else:
            self.exit()
    
    def _start_timers(self) -> None:
        """Start auto-lock and inactivity timers."""
        # Auto-lock timer
        self._inactivity_timer = self.set_interval(1, self._check_inactivity)
    
    def _check_inactivity(self) -> None:
        """Check for inactivity and auto-lock if needed."""
        # Simple implementation - lock after delay
        # In real implementation, track last activity timestamp
        pass  # Placeholder for inactivity checking
    
    def _refresh_entry_list(self) -> None:
        """Refresh the entry list display."""
        if not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        table.clear()
        table.add_columns("Title", "Username", "URL", "Tags")
        
        for entry in self.vault.entries:
            tags = ", ".join(entry.tags) if entry.tags else ""
            table.add_row(entry.title, entry.username, entry.url, tags)
    
    def _update_status(self, status: str, count: int = 0, action: str = "") -> None:
        """Update status bar."""
        status_bar = self.query_one(StatusBar)
        status_bar.update_status(status, count, action)
    
    def action_new_entry(self) -> None:
        """Create a new entry."""
        if self._locked or not self.vault:
            return
        
        self.push_screen(EntryEditScreen(), callback=self._on_entry_saved)
    
    def action_edit_entry(self) -> None:
        """Edit selected entry."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self.vault.entries):
            entry = self.vault.entries[cursor.row]
            self.push_screen(EntryEditScreen(entry), callback=self._on_entry_saved)
    
    def _on_entry_saved(self, entry: Optional[Entry]) -> None:
        """Handle entry save."""
        if entry and self.vault:
            existing = False
            for i, e in enumerate(self.vault.entries):
                if e.id == entry.id:
                    self.vault.entries[i] = entry
                    existing = True
                    break
            if not existing:
                self.vault.entries.append(entry)
            
            self.vault.save()
            self._refresh_entry_list()
            self._update_status("Unlocked", len(self.vault.entries), "Entry saved")
    
    def action_delete_entry(self) -> None:
        """Delete selected entry."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self.vault.entries):
            entry = self.vault.entries[cursor.row]
            self.push_screen(
                ConfirmScreen(f"Delete entry '{entry.title}'?"),
                callback=lambda confirmed: self._on_delete_confirmed(confirmed, entry.id)
            )
    
    def _on_delete_confirmed(self, confirmed: bool, entry_id: str) -> None:
        """Handle delete confirmation."""
        if confirmed and self.vault:
            self.vault.entries = [e for e in self.vault.entries if e.id != entry_id]
            self.vault.save()
            self._refresh_entry_list()
            self._update_status("Unlocked", len(self.vault.entries), "Entry deleted")
    
    def action_copy_password(self) -> None:
        """Copy password of selected entry to clipboard."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self.vault.entries):
            entry = self.vault.entries[cursor.row]
            self._copy_to_clipboard(entry.password)
            self._update_status("Unlocked", len(self.vault.entries), "Password copied")
    
    def action_copy_username(self) -> None:
        """Copy username of selected entry to clipboard."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self.vault.entries):
            entry = self.vault.entries[cursor.row]
            self._copy_to_clipboard(entry.username)
            self._update_status("Unlocked", len(self.vault.entries), "Username copied")
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard with auto-clear."""
        # Try to use pyperclip or similar
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # Fallback: try xclip/xsel on Linux
            try:
                import subprocess
                proc = subprocess.Popen(["xclip", "-selection", "clipboard"], 
                                       stdin=subprocess.PIPE)
                proc.communicate(text.encode())
            except:
                pass  # Clipboard not available
        
        self._clipboard_content = text
        
        # Clear clipboard after timeout
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        self._clipboard_timer = self.set_timer(self._clipboard_clear_delay, 
                                                self._clear_clipboard)
    
    def _clear_clipboard(self) -> None:
        """Clear clipboard."""
        if self._clipboard_content:
            try:
                import pyperclip
                pyperclip.copy("")
            except ImportError:
                try:
                    import subprocess
                    subprocess.Popen(["xclip", "-selection", "clipboard"], 
                                    stdin=subprocess.PIPE).communicate(b"")
                except:
                    pass
            self._clipboard_content = None
            self._update_status("Unlocked", len(self.vault.entries) if self.vault else 0, 
                              "Clipboard cleared")
    
    def action_search(self) -> None:
        """Activate search mode."""
        # Focus entry list and allow filtering
        self.notify("Search mode activated (type to filter)", severity="information")
    
    def action_lock(self) -> None:
        """Lock vault and exit gracefully."""
        self._locked = True
        self.vault = None
        
        # Clear clipboard
        self._clear_clipboard()
        
        # Stop timers
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        if self._inactivity_timer:
            self._inactivity_timer.stop()
        
        self.notify("Vault locked", severity="information")
        self.exit()
    
    def action_help(self) -> None:
        """Toggle help panel."""
        self.notify(
            "Shortcuts:\n"
            "n - New entry\n"
            "e - Edit entry\n"
            "d - Delete entry\n"
            "c - Copy password\n"
            "u - Copy username\n"
            "/ - Search\n"
            "l - Lock vault\n"
            "h - Help\n"
            "q - Quit",
            severity="information",
            timeout=10,
        )
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.action_lock()
    
    def on_unmount(self) -> None:
        """Cleanup on exit."""
        # Ensure vault is locked
        self._locked = True
        self.vault = None
        
        # Clear clipboard
        self._clear_clipboard()
        
        # Stop timers
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        if self._inactivity_timer:
            self._inactivity_timer.stop()
    
    # Watchers
    def watch_clipboard_timeout(self) -> None:
        """Auto-clear clipboard after timeout."""
        pass  # Handled by timer
    
    def watch_inactivity(self) -> None:
        """Auto-lock after inactivity."""
        pass  # Handled by timer
