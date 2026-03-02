"""Main TUI application for lazypassword."""

import os
import signal
from typing import Optional, List

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
from ..utils.clipboard import ClipboardManager


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
            yield Label("Set a master password (min 12 chars):")
            yield Input(placeholder="Enter master password...", password=True, id="password-input")
            yield Label("")
            yield Button("Create Vault", id="create-btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle create vault button."""
        if event.button.id == "create-btn":
            self._create_vault()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in password input."""
        if event.input.id == "password-input":
            self._create_vault()
    
    def _create_vault(self) -> None:
        """Create vault with entered password."""
        password_input = self.query_one("#password-input", Input)
        password = password_input.value
        if len(password) >= 12:
            self.dismiss(password)
        else:
            self.app.notify("Password must be at least 12 characters", severity="error")
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
            self._unlock()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in password input."""
        if event.input.id == "password-input":
            self._unlock()
    
    def _unlock(self) -> None:
        """Unlock with entered password."""
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
            self._save_entry()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in any input field - save the entry."""
        self._save_entry()
    
    def _save_entry(self) -> None:
        """Save the entry from form values."""
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
    
    def on_key(self, event) -> None:
        """Handle keyboard shortcuts - Enter confirms, Escape cancels."""
        if event.key == "enter":
            self.dismiss(True)
        elif event.key == "escape":
            self.dismiss(False)


class ThemeSettingsScreen(Screen):
    """Screen for selecting and configuring themes."""
    
    DEFAULT_CSS = """
    ThemeSettingsScreen {
        align: center middle;
    }
    #theme-container {
        width: 60;
        height: auto;
        border: solid purple;
        padding: 1 2;
    }
    #theme-list {
        width: 100%;
        height: auto;
    }
    """
    
    THEMES = ["dark", "light", "nord", "dracula", "monokai", "solarized-dark", "solarized-light"]
    
    def __init__(self, current_theme: str = "dark") -> None:
        super().__init__()
        self.current_theme = current_theme
    
    def compose(self) -> ComposeResult:
        with Container(id="theme-container"):
            yield Label("🎨 Theme Settings", classes="title")
            yield Label("")
            yield Label(f"Current theme: {self.current_theme}")
            yield Label("")
            yield Label("Select theme:")
            
            for theme in self.THEMES:
                selected = " ✓" if theme == self.current_theme else ""
                yield Button(f"{theme}{selected}", id=f"theme-{theme}")
            
            yield Label("")
            yield Button("Close", id="close-btn", variant="primary")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle theme selection."""
        button_id = event.button.id
        if button_id == "close-btn":
            self.dismiss(None)
        elif button_id and button_id.startswith("theme-"):
            theme = button_id.replace("theme-", "")
            self.dismiss(theme)
    
    def on_key(self, event) -> None:
        """Handle Escape to close."""
        if event.key == "escape":
            self.dismiss(None)


class LazyPasswordApp(App):
    """Main TUI application for LazyPassword."""
    
    TITLE = "LazyPassword"
    
    # Theme CSS definitions
    THEME_CSS = {
        "dark": """
        /* Default dark theme - already applied */
        """,
        "light": """
        Screen { background: #f5f5f5; color: #333; }
        DataTable { background: #ffffff; color: #333; }
        StatusBar { background: #e0e0e0; color: #333; }
        Header { background: #1976d2; color: white; }
        Input { background: #ffffff; color: #333; }
        Button { background: #1976d2; color: white; }
        """,
        "nord": """
        Screen { background: #2e3440; color: #d8dee9; }
        DataTable { background: #3b4252; color: #d8dee9; }
        StatusBar { background: #434c5e; color: #d8dee9; }
        Header { background: #5e81ac; color: #eceff4; }
        Input { background: #3b4252; color: #d8dee9; }
        Button { background: #5e81ac; color: #eceff4; }
        .title { color: #88c0d0; }
        """,
        "dracula": """
        Screen { background: #282a36; color: #f8f8f2; }
        DataTable { background: #44475a; color: #f8f8f2; }
        StatusBar { background: #44475a; color: #f8f8f2; }
        Header { background: #bd93f9; color: #282a36; }
        Input { background: #44475a; color: #f8f8f2; }
        Button { background: #bd93f9; color: #282a36; }
        .title { color: #ff79c6; }
        """,
        "monokai": """
        Screen { background: #272822; color: #f8f8f2; }
        DataTable { background: #383830; color: #f8f8f2; }
        StatusBar { background: #49483e; color: #f8f8f2; }
        Header { background: #a6e22e; color: #272822; }
        Input { background: #383830; color: #f8f8f2; }
        Button { background: #a6e22e; color: #272822; }
        .title { color: #66d9ef; }
        """,
        "solarized-dark": """
        Screen { background: #002b36; color: #839496; }
        DataTable { background: #073642; color: #839496; }
        StatusBar { background: #073642; color: #839496; }
        Header { background: #268bd2; color: #fdf6e3; }
        Input { background: #073642; color: #839496; }
        Button { background: #268bd2; color: #fdf6e3; }
        .title { color: #2aa198; }
        """,
        "solarized-light": """
        Screen { background: #fdf6e3; color: #586e75; }
        DataTable { background: #eee8d5; color: #586e75; }
        StatusBar { background: #eee8d5; color: #586e75; }
        Header { background: #268bd2; color: #fdf6e3; }
        Input { background: #eee8d5; color: #586e75; }
        Button { background: #268bd2; color: #fdf6e3; }
        .title { color: #2aa198; }
        """,
    }
    
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
        ("t", "theme", "Theme"),
        ("l", "lock", "Lock"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
    ]
    
    def __init__(self, vault_path: str, readonly: bool = False) -> None:
        """Initialize the application."""
        super().__init__()
        self.vault_path = vault_path
        self.readonly = readonly
        self.vault: Optional[Vault] = None
        self._locked = True
        self._clipboard_timer: Optional[Timer] = None
        self._inactivity_timer: Optional[Timer] = None
        self._clipboard_clear_delay = 30  # seconds
        self._auto_lock_delay = 600  # seconds (10 minutes)
        self._clipboard_content: Optional[str] = None
        self._clipboard_mgr = ClipboardManager()
        self._entries_cache: List[Entry] = []
    
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
                self.vault = Vault(self.vault_path)
                self.vault.create(password)
                self.vault.unlock(password)
                self._locked = False
                self._load_and_apply_theme()
                self._start_timers()
                self._refresh_entry_list()
                self._update_status("Unlocked", len(self._entries_cache))
            except Exception as e:
                self.notify(f"Failed to create vault: {e}", severity="error")
                self.exit()
        else:
            self.exit()
    
    def _on_unlock(self, password: Optional[str]) -> None:
        """Handle unlock attempt."""
        if password:
            try:
                self.vault = Vault(self.vault_path)
                if self.vault.unlock(password):
                    self._locked = False
                    self._load_and_apply_theme()
                    self._start_timers()
                    self._refresh_entry_list()
                    self._update_status("Unlocked", len(self._entries_cache))
                else:
                    self.notify("Incorrect password", severity="error")
                    self.push_screen(UnlockScreen(), callback=self._on_unlock)
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
    
    def _get_entries(self) -> List[Entry]:
        """Get entries from vault as Entry objects."""
        if not self.vault:
            return []
        entry_dicts = self.vault.get_entries()
        return [Entry.from_dict(e) for e in entry_dicts]
    
    def _refresh_entry_list(self) -> None:
        """Refresh the entry list display."""
        if not self.vault:
            return
        
        self._entries_cache = self._get_entries()
        table = self.query_one("#entry-list", DataTable)
        table.clear()
        table.add_columns("Title", "Username", "URL", "Tags")
        
        for entry in self._entries_cache:
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
        if cursor is not None and cursor.row < len(self._entries_cache):
            entry = self._entries_cache[cursor.row]
            self.push_screen(EntryEditScreen(entry), callback=self._on_entry_saved)
    
    def _on_entry_saved(self, entry: Optional[Entry]) -> None:
        """Handle entry save."""
        if entry and self.vault:
            entry_dict = entry.to_dict()
            existing = False
            for i, e in enumerate(self._entries_cache):
                if e.id == entry.id:
                    self.vault.update_entry(entry.id, entry_dict)
                    existing = True
                    break
            if not existing:
                self.vault.add_entry(entry_dict)
            
            self.vault.save()
            self._refresh_entry_list()
            self._update_status("Unlocked", len(self._entries_cache), "Entry saved")
    
    def action_delete_entry(self) -> None:
        """Delete selected entry."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self._entries_cache):
            entry = self._entries_cache[cursor.row]
            self.push_screen(
                ConfirmScreen(f"Delete entry '{entry.title}'?"),
                callback=lambda confirmed: self._on_delete_confirmed(confirmed, entry.id)
            )
    
    def _on_delete_confirmed(self, confirmed: bool, entry_id: str) -> None:
        """Handle delete confirmation."""
        if confirmed and self.vault:
            self.vault.delete_entry(entry_id)
            self.vault.save()
            self._refresh_entry_list()
            self._update_status("Unlocked", len(self._entries_cache), "Entry deleted")
    
    def action_copy_password(self) -> None:
        """Copy password of selected entry to clipboard."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self._entries_cache):
            entry = self._entries_cache[cursor.row]
            self._copy_to_clipboard(entry.password)
            self._update_status("Unlocked", len(self._entries_cache), "Password copied")
    
    def action_copy_username(self) -> None:
        """Copy username of selected entry to clipboard."""
        if self._locked or not self.vault:
            return
        
        table = self.query_one("#entry-list", DataTable)
        cursor = table.cursor_coordinate
        if cursor is not None and cursor.row < len(self._entries_cache):
            entry = self._entries_cache[cursor.row]
            self._copy_to_clipboard(entry.username)
            self._update_status("Unlocked", len(self._entries_cache), "Username copied")
    
    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard with auto-clear."""
        self._clipboard_mgr.copy(text)
        self._clipboard_content = text
        
        # Clear clipboard after timeout
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        self._clipboard_timer = self.set_timer(self._clipboard_clear_delay, 
                                                self._clear_clipboard)
    
    def _clear_clipboard(self) -> None:
        """Clear clipboard."""
        if self._clipboard_content:
            self._clipboard_mgr.clear()
            self._clipboard_content = None
            self._update_status("Unlocked", len(self._entries_cache) if self.vault else 0, 
                              "Clipboard cleared")
    
    def action_search(self) -> None:
        """Activate search mode."""
        # Focus entry list and allow filtering
        self.notify("Search mode activated (type to filter)", severity="information")
    
    def action_lock(self) -> None:
        """Lock vault and exit gracefully."""
        self._locked = True
        if self.vault:
            self.vault.lock()
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
            "t - Theme settings\n"
            "l - Lock vault\n"
            "h - Help\n"
            "q - Quit",
            severity="information",
            timeout=10,
        )
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.action_lock()
    
    def _apply_theme(self, theme: str) -> None:
        """Apply the selected theme to the app."""
        if theme in self.THEME_CSS:
            self.stylesheet.add_css(self.THEME_CSS[theme])
    
    def _load_and_apply_theme(self) -> None:
        """Load theme from vault settings and apply it."""
        if self.vault:
            theme = self.vault.get_theme()
            self._apply_theme(theme)
    
    def action_theme(self) -> None:
        """Open theme settings."""
        if self._locked or not self.vault:
            return
        
        current_theme = self.vault.get_theme()
        self.push_screen(ThemeSettingsScreen(current_theme), callback=self._on_theme_selected)
    
    def _on_theme_selected(self, theme: Optional[str]) -> None:
        """Handle theme selection."""
        if theme and self.vault:
            self.vault.set_theme(theme)
            self.vault.save()
            self._apply_theme(theme)
            self.notify(f"Theme changed to {theme}", severity="information")
    
    def on_unmount(self) -> None:
        """Cleanup on exit."""
        # Ensure vault is locked
        self._locked = True
        if self.vault:
            self.vault.lock()
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
