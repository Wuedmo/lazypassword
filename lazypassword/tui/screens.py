"""
Additional screens for lazypassword TUI.

This module provides screens for encryption settings, SSH key management,
and other auxiliary functionality.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..plugin import get_registry


class EncryptionSelectionScreen(Screen):
    """Screen for selecting encryption plugin."""

    CSS = """
    EncryptionSelectionScreen {
        align: center middle;
    }
    EncryptionSelectionScreen #encryption-container {
        width: auto;
        min-width: 50;
        max-width: 70;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    EncryptionSelectionScreen #encryption-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    EncryptionSelectionScreen #encryption-list {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    EncryptionSelectionScreen .plugin-item {
        padding: 1;
        margin: 1 0;
        border: solid $primary-darken-2;
    }
    EncryptionSelectionScreen .plugin-item.selected {
        background: $primary-darken-2;
        border: solid $primary;
    }
    EncryptionSelectionScreen .plugin-name {
        text-style: bold;
        color: $text;
    }
    EncryptionSelectionScreen .plugin-identifier {
        color: $text-muted;
        text-style: dim;
    }
    EncryptionSelectionScreen .plugin-description {
        color: $text;
        margin-top: 1;
    }
    EncryptionSelectionScreen .plugin-security {
        color: $success;
        margin-top: 1;
    }
    EncryptionSelectionScreen .plugin-unavailable {
        color: $error;
        text-style: italic;
    }
    EncryptionSelectionScreen #encryption-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    EncryptionSelectionScreen Button {
        margin: 0 1;
    }
    EncryptionSelectionScreen #current-selection {
        text-align: center;
        color: $text-muted;
        margin: 1 0;
    }
    EncryptionSelectionScreen .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    /* Small screens */
    @media (max-width: 80, max-height: 24) {
        EncryptionSelectionScreen #encryption-container {
            max-width: 100%;
            min-width: auto;
            width: 100%;
            padding: 0 1;
            margin: 0;
        }
        EncryptionSelectionScreen .plugin-item {
            padding: 0 1;
            margin: 0;
        }
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, current_plugin_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self._current_plugin_id = current_plugin_id
        self._plugins = []
        self._selected_index = 0

    def compose(self) -> ComposeResult:
        """Compose the encryption selection screen."""
        with Container(id="encryption-container"):
            yield Static("🔐 Encryption Settings", id="encryption-title")

            current_text = f"Current: {self._current_plugin_id or 'default'}"
            yield Static(current_text, id="current-selection")

            yield Label("Available encryption algorithms:")
            yield Vertical(id="encryption-list")

            yield Label("Press [b]ENTER[/b] to select • [b]ESC[/b] to close", classes="form-hint")

    def on_mount(self):
        """Load available plugins on mount."""
        self._load_plugins()

    def _load_plugins(self):
        """Load and display available encryption plugins."""
        registry = get_registry()
        plugin_list = self.query_one("#encryption-list", Vertical)

        # Get all registered plugins
        all_plugins = registry.list_all_plugins()
        self._plugins = all_plugins

        plugin_list.remove_children()

        for i, plugin_class in enumerate(all_plugins):
            is_selected = plugin_class.identifier == self._current_plugin_id
            is_available = plugin_class.is_available()

            # Create plugin item
            if is_available:
                security_rating = "★" * plugin_class.security_level + "☆" * (5 - plugin_class.security_level)
                item_content = (
                    f"[{plugin_class.name}]\n"
                    f"  ID: {plugin_class.identifier}\n"
                    f"  {plugin_class.description}\n"
                    f"  Security: {security_rating}"
                )
            else:
                item_content = (
                    f"[{plugin_class.name}] (Not Available)\n"
                    f"  ID: {plugin_class.identifier}\n"
                    f"  {plugin_class.description}"
                )

            classes = "plugin-item"
            if is_selected:
                classes += " selected"
                self._selected_index = i
            if not is_available:
                classes += " unavailable"

            plugin_list.mount(Static(item_content, classes=classes))

    def on_click(self, event):
        """Handle click on plugin items."""
        # Find which item was clicked
        plugin_list = self.query_one("#encryption-list", Vertical)
        for i, child in enumerate(plugin_list.children):
            if child.mouse_over:
                self._select_plugin(i)
                break

    def _select_plugin(self, index: int):
        """Select a plugin by index."""
        if 0 <= index < len(self._plugins):
            # Clear previous selection
            plugin_list = self.query_one("#encryption-list", Vertical)
            for child in plugin_list.children:
                classes = set(child.classes)
                if "selected" in classes:
                    classes.remove("selected")
                    child.classes = list(classes)

            # Set new selection
            self._selected_index = index
            new_selection = plugin_list.children[index]
            classes = set(new_selection.classes)
            classes.add("selected")
            new_selection.classes = list(classes)

    def on_key(self, event):
        """Handle keyboard shortcuts - Enter selects, Escape closes."""
        if event.key == "enter":
            self._apply_selection()
        elif event.key == "escape":
            self.action_close()

    def _apply_selection(self):
        """Apply the selected plugin."""
        if 0 <= self._selected_index < len(self._plugins):
            selected_plugin = self._plugins[self._selected_index]

            if not selected_plugin.is_available():
                self.app.notify(
                    f"Plugin '{selected_plugin.name}' is not available",
                    severity="error"
                )
                return

            self.dismiss(selected_plugin.identifier)
        else:
            self.dismiss(None)

    def action_close(self):
        """Close the screen without making a selection."""
        self.dismiss(None)


class SSHKeysScreen(Screen):
    """Screen for managing SSH keys."""

    CSS = """
    SSHKeysScreen {
        align: center middle;
    }
    SSHKeysScreen #ssh-container {
        width: auto;
        min-width: 60;
        max-width: 80;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    SSHKeysScreen #ssh-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    SSHKeysScreen #ssh-list {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    SSHKeysScreen .key-item {
        padding: 1;
        margin: 1 0;
        border: solid $primary-darken-2;
    }
    SSHKeysScreen .key-name {
        text-style: bold;
        color: $text;
    }
    SSHKeysScreen .key-fingerprint {
        color: $text-muted;
        text-style: dim;
    }
    SSHKeysScreen #ssh-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    SSHKeysScreen Button {
        margin: 0 1;
    }
    SSHKeysScreen .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    /* Small screens */
    @media (max-width: 80, max-height: 24) {
        SSHKeysScreen #ssh-container {
            max-width: 100%;
            min-width: auto;
            width: 100%;
            padding: 0 1;
            margin: 0;
        }
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
    ]

    def __init__(self, ssh_manager, **kwargs):
        super().__init__(**kwargs)
        self._ssh_manager = ssh_manager

    def compose(self) -> ComposeResult:
        """Compose the SSH keys screen."""
        with Container(id="ssh-container"):
            yield Static("🔑 SSH Key Management", id="ssh-title")
            yield Label("Your SSH Keys:")
            yield Vertical(id="ssh-list")

            yield Horizontal(
                Button("Generate New Key", id="generate-btn", variant="primary"),
                Button("Import Key", id="import-btn"),
            )
            yield Label("Press [b]ESC[/b] to close", classes="form-hint")

    def on_mount(self):
        """Load SSH keys on mount."""
        self._load_keys()

    def _load_keys(self):
        """Load and display SSH keys."""
        key_list = self.query_one("#ssh-list", Vertical)
        key_list.remove_children()

        if self._ssh_manager:
            keys = self._ssh_manager.list_keys()
            for key in keys:
                key_content = (
                    f"[{key.name}]\n"
                    f"  Fingerprint: {key.fingerprint}\n"
                    f"  Algorithm: {key.algorithm}"
                )
                key_list.mount(Static(key_content, classes="key-item"))
        else:
            key_list.mount(Static("No SSH keys found", classes="key-item"))

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "generate-btn":
            self._generate_key()
        elif button_id == "import-btn":
            self._import_key()

    def _generate_key(self):
        """Generate a new SSH key."""
        if self._ssh_manager:
            try:
                key = self._ssh_manager.generate_key()
                self.app.notify(f"Generated SSH key: {key.name}", severity="information")
                self._load_keys()
            except Exception as e:
                self.app.notify(f"Failed to generate key: {e}", severity="error")

    def _import_key(self):
        """Import an existing SSH key."""
        # TODO: Implement key import dialog
        self.app.notify("Key import not yet implemented", severity="warning")

    def action_close(self):
        """Close the screen."""
        self.dismiss(None)
