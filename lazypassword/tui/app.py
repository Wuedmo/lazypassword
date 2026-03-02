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
from ..import_export import VaultExporter, VaultImporter, DuplicateHandling, ImportFormat
from ..api_key import APIKeyManager
from .screens import APIKeysScreen


class StatusBar(Static):
    """Status bar showing current vault state."""

    vault_status = reactive("Locked")
    entry_count = reactive(0)
    last_action = reactive("")
    encryption_plugin = reactive("")
    current_theme = reactive("dark")

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(f" 🔒 {self.vault_status}", id="status-vault"),
            Label(f" 📁 Entries: {self.entry_count}", id="status-count"),
            Label(f" 🔐 {self.encryption_plugin or 'No Plugin'}", id="status-encryption"),
            Label(f" 🎨 {self.current_theme}", id="status-theme"),
            Label(f" 📋 {self.last_action}", id="status-action"),
            id="status-content",
        )

    def update_status(self, status: str, count: int = 0, action: str = "", encryption: str = "", theme: str = "") -> None:
        """Update status bar display."""
        self.vault_status = status
        self.entry_count = count
        self.last_action = action
        self.encryption_plugin = encryption
        if theme:
            self.current_theme = theme
        vault_label = self.query_one("#status-vault", Label)
        count_label = self.query_one("#status-count", Label)
        action_label = self.query_one("#status-action", Label)
        encryption_label = self.query_one("#status-encryption", Label)
        theme_label = self.query_one("#status-theme", Label)
        vault_label.update(f" 🔒 {status}")
        count_label.update(f" 📁 Entries: {count}")
        encryption_label.update(f" 🔐 {encryption}" if encryption else " 🔐 No Plugin")
        theme_label.update(f" 🎨 {self.current_theme}")
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
    """

    def compose(self) -> ComposeResult:
        with Container(id="first-run-container"):
            yield Label("Welcome to LazyPassword! 🔐", classes="title")
            yield Label("No vault found. Create a new vault to get started.")
            yield Label("")
            yield Label("Set a master password (min 12 chars):")
            yield Input(placeholder="Enter master password...", password=True, id="password-input")
            yield Label("")
            yield Horizontal(
                Label("Use keyfile (additional security): "),
                Label("[ ]", id="keyfile-checkbox"),
                id="keyfile-row"
            )
            yield Label("  Select a file to use as an additional authentication factor.")
            yield Label("")
            yield Label("Press [b]ENTER[/b] to create vault • [b]ESC[/b] to exit", classes="form-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in password input."""
        if event.input.id == "password-input":
            self._create_vault()

    def on_key(self, event) -> None:
        """Handle Escape key to exit."""
        if event.key == "escape":
            self.dismiss(None)

    def on_click(self, event) -> None:
        """Handle clicks on the checkbox area."""
        checkbox = self.query_one("#keyfile-checkbox", Label)
        current = checkbox.renderable
        if "✓" in str(current):
            checkbox.update("[ ]")
        else:
            checkbox.update("[✓]")
    
    def _create_vault(self) -> None:
        """Create vault with entered password."""
        password_input = self.query_one("#password-input", Input)
        password = password_input.value
        
        checkbox = self.query_one("#keyfile-checkbox", Label)
        use_keyfile = "✓" in str(checkbox.renderable)
        
        if len(password) >= 12:
            result = {"password": password, "use_keyfile": use_keyfile}
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
    """

    def __init__(self, requires_keyfile: bool = False) -> None:
        super().__init__()
        self.requires_keyfile = requires_keyfile

    def compose(self) -> ComposeResult:
        with Container(id="unlock-container"):
            yield Label("🔐 Unlock Vault", classes="title")
            if self.requires_keyfile:
                yield Label("ℹ️ This vault requires a keyfile", id="keyfile-indicator")
            yield Label("")
            yield Input(placeholder="Master password...", password=True, id="password-input")
            yield Label("")
            yield Label("Press [b]ENTER[/b] to unlock • [b]ESC[/b] to exit", classes="form-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in password input."""
        if event.input.id == "password-input":
            self._unlock()
    
    def on_key(self, event) -> None:
        """Handle Escape key to exit."""
        if event.key == "escape":
            self.dismiss(None)
    
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
        width: auto;
        min-width: 50;
        max-width: 70;
        height: auto;
        max-height: 95%;
        border: solid yellow;
        padding: 1 2;
        overflow: auto;
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
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
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
        padding: 1 2;
        overflow: auto;
    }
    #theme-grid {
        grid-size: 2;
        grid-gutter: 1;
        height: auto;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
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
            
            with Grid(id="theme-grid"):
                for theme in self.THEMES:
                    selected = " ✓" if theme == self.current_theme else ""
                    yield Button(f"{theme}{selected}", id=f"theme-{theme}")
            
            yield Label("")
            yield Label("Press [b]ENTER[/b] to select • [b]ESC[/b] to close", classes="form-hint")
    
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
        padding: 1 2;
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
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="import-container"):
            yield Label("📥 Import Entries", classes="title")
            yield Label("")
            yield Label("File path:")
            yield Input(placeholder="/path/to/export.json", id="import-file-input")
            yield Label("")
            yield Label("Format:")
            yield Input(value="lazypassword", id="format-select")
            yield Label("")
            yield Label("Duplicate handling:")
            yield Input(value="skip", id="duplicate-select")
            yield Label("")
            yield Label("Press [b]ENTER[/b] to import • [b]ESC[/b] to cancel", classes="form-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key to submit."""
        self._do_import()
    
    def on_key(self, event) -> None:
        """Handle Escape key to cancel."""
        if event.key == "escape":
            self.dismiss(None)
    
    def _do_import(self) -> None:
        """Perform import."""
        file_input = self.query_one("#import-file-input", Input)
        format_input = self.query_one("#format-select", Input)
        duplicate_input = self.query_one("#duplicate-select", Input)
        
        result = {
            "file_path": file_input.value,
            "format": format_input.value,
            "duplicate_handling": duplicate_input.value,
        }
        self.dismiss(result)


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
        border: solid cyan;
        padding: 1 2;
    }
    #export-file-input {
        width: 100%;
    }
    #export-format-select {
        width: 100%;
    }
    .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="export-container"):
            yield Label("📤 Export Entries", classes="title")
            yield Label("")
            yield Label("Export file path:")
            yield Input(placeholder="/path/to/export.json", id="export-file-input")
            yield Label("")
            yield Label("Format:")
            yield Input(value="lazypassword", id="export-format-select")
            yield Label("")
            yield Label("Press [b]ENTER[/b] to export • [b]ESC[/b] to cancel", classes="form-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key to submit."""
        self._do_export()
    
    def on_key(self, event) -> None:
        """Handle Escape key to cancel."""
        if event.key == "escape":
            self.dismiss(None)
    
    def _do_export(self) -> None:
        """Perform export."""
        file_input = self.query_one("#export-file-input", Input)
        format_input = self.query_one("#export-format-select", Input)
        
        result = {
            "file_path": file_input.value,
            "format": format_input.value,
        }
        self.dismiss(result)


class HistoryPanel(Static):
    """Panel showing git version history."""
    
    def compose(self) -> ComposeResult:
        yield Label("📜 History", id="history-title")
        yield ListView(id="history-list")
    
    def update_history(self, versions: list) -> None:
        """Update the history list with versions."""
        history_list = self.query_one("#history-list", ListView)
        history_list.clear()
        
        for version in versions:
            item_text = f"[{version.commit_hash}] {version.message}"
            history_list.append(ListItem(Label(item_text, classes="history-item")))


class LazyPasswordApp(App):
    """Main TUI application for LazyPassword."""
    
    TITLE = "LazyPassword"
    
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
        width: 70%;
    }
    #history-panel {
        width: 30%;
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
        ("a", "api_keys", "API Keys"),
        ("v", "toggle_history", "Toggle History"),
        ("g", "show_history", "Git History"),
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
        self.versioning: Optional[GitVersioning] = None
        self.api_key_manager: Optional[APIKeyManager] = None
        self._locked = True
        self._clipboard_timer: Optional[Timer] = None
        self._inactivity_timer: Optional[Timer] = None
        self._clipboard_clear_delay = 30
        self._auto_lock_delay = 600
        self._clipboard_content: Optional[str] = None
        self._clipboard_mgr = ClipboardManager()
        self._entries_cache: List[Entry] = []
        self._show_history = True
    
    def compose(self) -> ComposeResult:
        """Compose the main UI."""
        yield Header()
        with Container(id="main-container"):
            yield DataTable(id="entry-list")
            yield HistoryPanel(id="history-panel")
        yield Footer()
        yield StatusBar()
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
    
    def _on_first_run(self, password_data: Optional[dict]) -> None:
        """Handle first run password entry."""
        if password_data and isinstance(password_data, dict):
            try:
                password = password_data.get("password", "")
                use_keyfile = password_data.get("use_keyfile", False)
                
                self.vault = Vault(self.vault_path)
                self.vault.create(password)
                self.vault.unlock(password)
                self._locked = False
                
                self.versioning = GitVersioning(self.vault_path)
                self.versioning.initialize()
                self.versioning.commit("Initial vault creation")
                
                self.api_key_manager = APIKeyManager(self.vault)
                
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
                    
                    self.versioning = GitVersioning(self.vault_path)
                    if not self.versioning.is_initialized():
                        self.versioning.initialize()
                        self.versioning.commit("Initialize versioning for existing vault")
                    
                    self.api_key_manager = APIKeyManager(self.vault)
                    
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
        self._inactivity_timer = self.set_interval(1, self._check_inactivity)
    
    def _check_inactivity(self) -> None:
        """Check for inactivity and auto-lock if needed."""
        pass
    
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
            pass
    
    def _commit_vault_change(self, message: str) -> None:
        """Commit vault changes to git."""
        if self.versioning:
            try:
                self.versioning.commit(message)
                self._refresh_history()
            except Exception:
                pass
    
    def _update_status(self, status: str, count: int = 0, action: str = "", theme: str = "") -> None:
        """Update status bar."""
        status_bar = self.query_one(StatusBar)
        # Get current theme if not provided
        if not theme and self.vault:
            theme = self.vault.get_theme()
        status_bar.update_status(status, count, action, theme=theme)
    
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
            entry_title = "Unknown"
            for e in self._entries_cache:
                if e.id == entry_id:
                    entry_title = e.title
                    break
            
            self.vault.delete_entry(entry_id)
            self.vault.save()
            
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
        
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        self._clipboard_timer = self.set_timer(self._clipboard_clear_delay, self._clear_clipboard)
    
    def _clear_clipboard(self) -> None:
        """Clear clipboard."""
        if self._clipboard_content:
            self._clipboard_mgr.clear()
            self._clipboard_content = None
            self._update_status("Unlocked", len(self._entries_cache) if self.vault else 0, "Clipboard cleared")
    
    def action_search(self) -> None:
        """Activate search mode."""
        self.notify("Search mode activated (type to filter)", severity="information")
    
    def action_lock(self) -> None:
        """Lock vault and exit gracefully."""
        self._locked = True
        if self.vault:
            self.vault.lock()
        self.vault = None
        
        self._clear_clipboard()
        
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
            "a - API Keys\n"
            "v - Toggle history panel\n"
            "g - Show git history\n"
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
        # Update status bar to show current theme
        self._update_status("Unlocked", len(self._entries_cache) if self._entries_cache else 0, theme=theme)
        # Note: Full theme application requires app restart due to Textual CSS limitations

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
    
    def action_api_keys(self) -> None:
        """Open API keys management screen."""
        if self._locked or not self.vault or not self.api_key_manager:
            return
        
        self.push_screen(APIKeysScreen(self.api_key_manager))
    
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
    
    def on_unmount(self) -> None:
        """Cleanup on exit."""
        self._locked = True
        if self.vault:
            self.vault.lock()
        self.vault = None
        
        self._clear_clipboard()
        
        if self._clipboard_timer:
            self._clipboard_timer.stop()
        if self._inactivity_timer:
            self._inactivity_timer.stop()
