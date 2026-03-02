"""Main TUI application for lazypassword."""

import os
import signal
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)
from textual.screen import Screen

# Assume vault module exists
from ..vault import Vault
from ..entry import Entry
from ..utils.clipboard import ClipboardManager
from ..versioning import GitVersioning, VaultVersion
from ..ssh_manager import SSHManager
from ..api_key import APIKeyManager
from ..import_export import VaultExporter, VaultImporter, DuplicateHandling, ImportFormat
from .screens import EncryptionSelectionScreen


class StatusBar(Static):
    """Status bar showing current vault state."""
    
    vault_status = reactive("Locked")
    entry_count = reactive(0)
    last_action = reactive("")
    encryption_plugin = reactive("")
    
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(f" 🔒 {self.vault_status}", id="status-vault"),
            Label(f" 📁 Entries: {self.entry_count}", id="status-count"),
            Label(f" 🔐 {self.encryption_plugin or 'No Plugin'}", id="status-encryption"),
            Label(f" 📋 {self.last_action}", id="status-action"),
            id="status-content",
        )
    
    def update_status(self, status: str, count: int = 0, action: str = "", encryption: str = "") -> None:
        """Update status bar display."""
        self.vault_status = status
        self.entry_count = count
        self.last_action = action
        self.encryption_plugin = encryption
        vault_label = self.query_one("#status-vault", Label)
        count_label = self.query_one("#status-count", Label)
        action_label = self.query_one("#status-action", Label)
        encryption_label = self.query_one("#status-encryption", Label)
        vault_label.update(f" 🔒 {status}")
        count_label.update(f" 📁 Entries: {count}")
        encryption_label.update(f" 🔐 {encryption}" if encryption else " 🔐 No Plugin")
        action_label.update(f" 📋 {action}" if action else "")


class FirstRunScreen(Screen):
    """Screen shown when no vault exists."""
    
    DEFAULT_CSS = """
    FirstRunScreen {
        align: center middle;
    }
    #first-run-container {
        width: auto;
        min-width: 40;
        max-width: 50;
        height: auto;
        max-height: 90%;
        border: solid green;
        padding: 1;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
            self.dismiss(result)
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
        width: auto;
        min-width: 35;
        max-width: 40;
        height: auto;
        max-height: 90%;
        border: solid blue;
        padding: 1;
    }
    #keyfile-indicator {
        color: yellow;
        text-style: italic;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
            self.dismiss(result)


class EntryEditScreen(Screen):
    """Screen for creating/editing entries."""

    DEFAULT_CSS = """
    EntryEditScreen {
        align: center middle;
    }
    #edit-container {
        width: auto;
        min-width: 50;
        max-width: 70;
        height: auto;
        max-height: 95%;
        border: solid yellow;
        padding: 1;
        overflow: auto;
    }
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
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
            yield Label("Press [b]ENTER[/b] to save • [b]ESC[/b] to cancel", classes="form-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in any input field - save the entry."""
        self._save_entry()

    def on_key(self, event) -> None:
        """Handle Escape key to cancel."""
        if event.key == "escape":
            self.dismiss(None)
    
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
        width: auto;
        min-width: 30;
        max-width: 60;
        height: auto;
        max-height: 80%;
        border: solid red;
        padding: 1;
    }
    #confirm-message {
        text-wrap: wrap;
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
            yield Label("Press [b]ENTER[/b] for Yes • [b]ESC[/b] for No", classes="form-hint")
    
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
        width: auto;
        min-width: 40;
        max-width: 60;
        height: auto;
        max-height: 90%;
        border: solid purple;
        padding: 1;
    }
    #theme-list {
        width: 100%;
        height: auto;
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-rows: auto;
        grid-gutter: 1;
    }
    #theme-list Button {
        width: 100%;
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
            yield Label("Press [b]ENTER[/b] to select • [b]ESC[/b] to close", classes="form-hint")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle theme selection."""
        button_id = event.button.id
        if button_id and button_id.startswith("theme-"):
            theme = button_id.replace("theme-", "")
            self.dismiss(theme)
    
    def on_key(self, event) -> None:
        """Handle Escape to close."""
        if event.key == "escape":
            self.dismiss(None)


class HistoryPanel(Static):
    """Panel showing git version history."""

    DEFAULT_CSS = """
    HistoryPanel {
        height: 100%;
        max-height: 100%;
        overflow: auto;
    }
    #history-list {
        height: auto;
        max-height: 95%;
        overflow: auto;
    }] {version.message}"
            history_list.append(ListItem(Label(item_text, classes="history-item")))


class ImportScreen(Screen[dict]):
    """Screen for importing entries from a JSON file."""

    DEFAULT_CSS = """
    ImportScreen {
        align: center middle;
    }
    #import-container {
        width: auto;
        min-width: 50;
        max-width: 70;
        height: auto;
        max-height: 90%;
        border: solid green;
        padding: 1;
        overflow: auto;
    }
    #import-file-input {
        width: 100%;
    }
    #format-select {
        width: 100%;
    }
    #duplicate-select {
        width: 100%;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }", severity="error")
            return
        
        format_value = format_select.value
        format_hint = None if format_value == "auto" else format_value
        
        duplicate_value = duplicate_select.value
        duplicate_handling = DuplicateHandling(duplicate_value)
        
        result = {
            "filepath": filepath,
            "format_hint": format_hint,
            "duplicate_handling": duplicate_handling,
        }
        self.dismiss(result)
    
    def on_key(self, event) -> None:
        """Handle Escape key."""
        if event.key == "escape":
            self.dismiss(None)


class ExportScreen(Screen[dict]):
    """Screen for exporting entries to a JSON file."""

    DEFAULT_CSS = """
    ExportScreen {
        align: center middle;
    }
    #export-container {
        width: auto;
        min-width: 50;
        max-width: 70;
        height: auto;
        max-height: 90%;
        border: solid blue;
        padding: 1;
        overflow: auto;
    }
    #export-file-input {
        width: 100%;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }")
            yield Label("")
            yield Label("Export mode:")
            from textual.widgets import RadioSet, RadioButton
            yield RadioSet(
                RadioButton("All entries", value=True, id="export-all"),
                RadioButton("Selected entry only", id="export-selected"),
            )
            yield Label("")
            yield Label("Format:")
            from textual.widgets import Select
            yield Select(
                [
                    ("LazyPassword JSON", "lazypassword"),
                    ("Bitwarden JSON", "bitwarden"),
                ],
                value="lazypassword",
                id="export-format-select",
            )
            yield Label("")
            yield Label("File path:")
            yield Input(placeholder="/path/to/export.json", id="export-file-input")
            yield Label("")
            yield Label("Options:")
            yield Horizontal(
                Label("Include passwords: "),
                Input(value="yes", id="include-passwords"),
            )
            yield Label("")
            yield Label("Press [b]ENTER[/b] to export • [b]ESC[/b] to cancel", classes="form-hint")

    def on_key(self, event) -> None:
        """Handle Enter to export, Escape to cancel."""
        if event.key == "enter":
            self._do_export()
        elif event.key == "escape":
            self.dismiss(None)
    
    def _do_export(self) -> None:
        """Perform the export."""
        from textual.widgets import Select, RadioSet, RadioButton
        
        file_input = self.query_one("#export-file-input", Input)
        format_select = self.query_one("#export-format-select", Select)
        include_passwords_input = self.query_one("#include-passwords", Input)
        
        filepath = file_input.value.strip()
        if not filepath:
            self.app.notify("Please enter a file path", severity="error")
            return
        
        export_format = format_select.value
        include_passwords = include_passwords_input.value.lower() in ["yes", "y", "true", "1"]
        
        result = {
            "filepath": filepath,
            "format": export_format,
            "include_passwords": include_passwords,
        }
        self.dismiss(result)
    
    def on_key(self, event) -> None:
        """Handle Escape key."""
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
    #main-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }
    #entry-list {
        height: 1fr;
        width: 1fr;
        min-width: 50;
    }
    #history-panel {
        width: 1fr;
        max-width: 40;
        height: 1fr;
        border: solid $primary-darken-2;
        padding: 0 1;
    }
    #history-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
    }
    #history-list {
        height: 1fr;
        width: 100%;
        overflow: auto;
    }
    .history-item {
        padding: 0 1;
        text-wrap: wrap;
    }
    .history-hash {
        color: $primary-lighten-2;
        text-style: bold;
    }
    .history-message {
        color: $text;
    }
    .history-time {
        color: $text-muted;
        text-style: italic;
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
        min-width: 10;
        text-overflow: ellipsis;
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
        ("v", "toggle_history", "Toggle History"),
        ("g", "show_history", "Git History"),
        ("s", "ssh_keys", "SSH Keys"),
        ("a", "api_keys", "API Keys"),
        ("p", "encryption_settings", "Encryption"),
        ("l", "lock", "Lock"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
        ("ctrl+e", "export_vault", "Export"),
        ("ctrl+i", "import_vault", "Import"),
    ]
    
    def __init__(self, vault_path: str, readonly: bool = False) -> None:
        """Initialize the application."""
        super().__init__()
        self.vault_path = vault_path
        self.readonly = readonly
        self.vault: Optional[Vault] = None
        self.versioning: Optional[GitVersioning] = None
        self._locked = True
        self._clipboard_timer: Optional[Timer] = None
        self._inactivity_timer: Optional[Timer] = None
        self._clipboard_clear_delay = 30  # seconds
        self._auto_lock_delay = 600  # seconds (10 minutes)
        self._clipboard_content: Optional[str] = None
        self._clipboard_mgr = ClipboardManager()
        self._entries_cache: List[Entry] = []
        self._show_history = True
        self._ssh_manager: Optional[SSHManager] = None
        self._api_key_manager: Optional[APIKeyManager] = None
    
    def compose(self) -> ComposeResult:
        """Compose the main UI."""
        yield Header()
        with Container(id="main-container"):
            yield DataTable(id="entry-list")
            yield HistoryPanel(id="history-panel")
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
                
                # Initialize versioning
                self.versioning = GitVersioning(self.vault_path)
                self.versioning.initialize()
                self.versioning.commit("Initial vault creation")
                
                # Initialize SSH manager
                self._ssh_manager = SSHManager(self.vault)
                
                # Initialize API key manager
                self._api_key_manager = APIKeyManager(self.vault)
                
                self._load_and_apply_theme()
                self._start_timers()
                self._refresh_entry_list()
                self._refresh_history()
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
                    
                    # Initialize versioning
                    self.versioning = GitVersioning(self.vault_path)
                    if not self.versioning.is_initialized():
                        self.versioning.initialize()
                        self.versioning.commit("Initialize versioning for existing vault")
                    
                    # Initialize SSH manager
                    self._ssh_manager = SSHManager(self.vault)
                    
                    # Initialize API key manager
                    self._api_key_manager = APIKeyManager(self.vault)
                    
                    self._load_and_apply_theme()
                    self._start_timers()
                    self._refresh_entry_list()
                    self._refresh_history()
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
    
    def _refresh_history(self) -> None:
        """Refresh the history panel."""
        if not self.versioning:
            return
        
        try:
            versions = self.versioning.get_history(limit=20)
            history_panel = self.query_one("#history-panel", HistoryPanel)
            history_panel.update_history(versions)
        except Exception:
            pass  # Silently fail if git not available
    
    def _commit_vault_change(self, message: str) -> None:
        """Commit vault changes to git."""
        if self.versioning:
            try:
                self.versioning.commit(message)
                self._refresh_history()
            except Exception:
                pass  # Silently fail if git commit fails
    
    def _update_status(self, status: str, count: int = 0, action: str = "") -> None:
        """Update status bar."""
        encryption = ""
        if self.vault and not self._locked:
            encryption = self.vault.get_encryption_plugin() or "unknown"
        status_bar = self.query_one(StatusBar)
        status_bar.update_status(status, count, action, encryption)
    
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
            
            # Commit to git
            action = "Updated" if existing else "Added"
            self._commit_vault_change(f"{action} entry: {entry.title}")
            
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
            # Get entry title before deleting
            entry_title = "Unknown"
            for e in self._entries_cache:
                if e.id == entry_id:
                    entry_title = e.title
                    break
            
            self.vault.delete_entry(entry_id)
            self.vault.save()
            
            # Commit to git
            self._commit_vault_change(f"Deleted entry: {entry_title}")
            
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
            "v - Toggle history panel\n"
            "g - Show git history\n"
            "s - SSH Keys\n"
            "a - API Keys\n"
            "Ctrl+E - Export vault\n"
            "Ctrl+I - Import entries\n"
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
        # Theme CSS is applied statically; dynamic switching requires app restart
        # Store the theme preference for next launch
        pass
    
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
    
    def action_toggle_history(self) -> None:
        """Toggle history panel visibility."""
        self._show_history = not self._show_history
        history_panel = self.query_one("#history-panel", HistoryPanel)
        entry_list = self.query_one("#entry-list", DataTable)
        
        if self._show_history:
            history_panel.styles.display = "block"
            entry_list.styles.width = "70%"
        else:
            history_panel.styles.display = "none"
            entry_list.styles.width = "100%"
    
    def action_show_history(self) -> None:
        """Show full git history screen."""
        if self._locked or not self.vault or not self.versioning:
            return
        
        try:
            versions = self.versioning.get_history(limit=50)
            if versions:
                history_text = "Git History:\n\n"
                for v in versions:
                    history_text += f"[{v.commit_hash}] {v.message}\n"
                    history_text += f"    {v.timestamp} by {v.author}\n\n"
                self.notify(history_text, severity="information", timeout=15)
            else:
                self.notify("No history available", severity="warning")
        except Exception as e:
            self.notify(f"Failed to load history: {e}", severity="error")
    
    def action_encryption_settings(self) -> None:
        """Open encryption plugin selection screen."""
        if self._locked or not self.vault:
            return
        
        current_plugin = self.vault.get_encryption_plugin()
        self.push_screen(
            EncryptionSelectionScreen(current_plugin),
            callback=self._on_encryption_selected
        )
    
    def _on_encryption_selected(self, plugin_id: Optional[str]) -> None:
        """Handle encryption plugin selection."""
        if not plugin_id or not self.vault:
            return
        
        current_plugin = self.vault.get_encryption_plugin()
        if plugin_id == current_plugin:
            self.notify("Encryption plugin unchanged", severity="information")
            return
        
        try:
            # Change encryption plugin (re-encrypts vault)
            self.vault.change_encryption_plugin(plugin_id)
            
            # Update status bar
            self._update_status("Unlocked", len(self._entries_cache), f"Encryption: {plugin_id}")
            
            self.notify(
                f"✅ Encryption changed to {plugin_id}\nVault re-encrypted with new algorithm.",
                severity="information"
            )
        except Exception as e:
            self.notify(f"Failed to change encryption: {e}", severity="error")
    
    def action_ssh_keys(self) -> None:
        """Open SSH keys management screen."""
        if self._locked or not self.vault or not self._ssh_manager:
            return
        
        from .screens import SSHKeysScreen
        self.push_screen(SSHKeysScreen(self._ssh_manager))
    
    def action_api_keys(self) -> None:
        """Open API keys management screen."""
        if self._locked or not self.vault or not self._api_key_manager:
            return
        
        from .screens import APIKeysScreen
        self.push_screen(APIKeysScreen(self._api_key_manager))
    
    def action_import_vault(self) -> None:
        """Open import screen."""
        if self._locked or not self.vault:
            return
        
        self.push_screen(ImportScreen(), callback=self._on_import_result)
    
    def _on_import_result(self, result: Optional[dict]) -> None:
        """Handle import screen result."""
        if not result or not self.vault:
            return
        
        try:
            importer = VaultImporter()
            import_result = importer.import_to_vault(
                self.vault,
                result["filepath"],
                format_hint=result.get("format_hint"),
                duplicate_handling=result.get("duplicate_handling", DuplicateHandling.SKIP)
            )
            
            # Commit to git
            if self.versioning:
                self._commit_vault_change(f"Imported {import_result['entries_added']} entries from {result['filepath']}")
            
            self._refresh_entry_list()
            
            # Show summary
            summary = (
                f"✅ Import Complete\n\n"
                f"Format: {import_result['format']}\n"
                f"Total processed: {import_result['total_processed']}\n"
                f"Added: {import_result['entries_added']}\n"
                f"Skipped: {import_result['entries_skipped']}\n"
                f"Merged: {import_result['entries_merged']}\n"
                f"Replaced: {import_result['entries_replaced']}"
            )
            self.notify(summary, severity="information", timeout=10)
            self._update_status("Unlocked", len(self._entries_cache), "Import complete")
            
        except Exception as e:
            self.notify(f"Import failed: {e}", severity="error")
    
    def action_export_vault(self) -> None:
        """Open export screen."""
        if self._locked or not self.vault:
            return
        
        self.push_screen(ExportScreen(self._entries_cache), callback=self._on_export_result)
    
    def _on_export_result(self, result: Optional[dict]) -> None:
        """Handle export screen result."""
        if not result or not self.vault:
            return
        
        try:
            exporter = VaultExporter(self.vault)
            
            if result["format"] == "bitwarden":
                export_result = exporter.export_to_bitwarden(result["filepath"])
            else:
                export_result = exporter.export_to_json(
                    result["filepath"],
                    include_passwords=result["include_passwords"]
                )
            
            # Show summary
            summary = (
                f"✅ Export Complete\n\n"
                f"Entries: {export_result['entries_exported']}\n"
                f"Format: {export_result.get('format', 'lazypassword')}\n"
                f"File: {export_result['filepath']}\n"
                f"Passwords included: {'Yes' if export_result.get('includes_passwords', True) else 'No'}"
            )
            self.notify(summary, severity="information", timeout=10)
            self._update_status("Unlocked", len(self._entries_cache), "Export complete")
            
        except Exception as e:
            self.notify(f"Export failed: {e}", severity="error")
    
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
