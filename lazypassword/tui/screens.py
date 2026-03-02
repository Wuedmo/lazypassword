"""
Additional screens for lazypassword TUI.

This module provides screens for encryption settings, SSH key management,
API key management, and other auxiliary functionality.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.screen import Screen
from textual.widgets import Button, Label, Static, Input, Select, ListView, ListItem

from ..plugins import get_registry
from ..api_key import APIKey, APIKeyManager
from ..api_presets import get_platforms_with_metadata, get_preset


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


class APIKeysScreen(Screen):
    """Screen for managing API keys."""

    CSS = """
    APIKeysScreen {
        align: center middle;
    }
    APIKeysScreen #apikeys-container {
        width: auto;
        min-width: 70;
        max-width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    APIKeysScreen #apikeys-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    APIKeysScreen #apikeys-list {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    APIKeysScreen .apikey-item {
        padding: 1;
        margin: 1 0;
        border: solid $primary-darken-2;
    }
    APIKeysScreen .apikey-item:hover {
        background: $surface-lighten-1;
    }
    APIKeysScreen .apikey-header {
        layout: horizontal;
        height: auto;
    }
    APIKeysScreen .apikey-icon {
        width: 3;
    }
    APIKeysScreen .apikey-name {
        text-style: bold;
        color: $text;
        width: 1fr;
    }
    APIKeysScreen .apikey-platform {
        color: $text-muted;
        width: auto;
    }
    APIKeysScreen .apikey-value {
        color: $text-muted;
        text-style: dim;
        margin-top: 1;
    }
    APIKeysScreen .apikey-tags {
        color: $accent;
        margin-top: 1;
    }
    APIKeysScreen #apikeys-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    APIKeysScreen Button {
        margin: 0 1;
    }
    APIKeysScreen .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    APIKeysScreen #search-input {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("a", "add_key", "Add Key"),
        ("s", "search", "Search"),
    ]

    def __init__(self, api_key_manager: APIKeyManager, **kwargs):
        super().__init__(**kwargs)
        self._api_key_manager = api_key_manager
        self._search_query = ""

    def compose(self) -> ComposeResult:
        """Compose the API keys screen."""
        with Container(id="apikeys-container"):
            yield Static("🔑 API Key Management", id="apikeys-title")
            yield Input(placeholder="Search API keys...", id="search-input")
            yield Vertical(id="apikeys-list")

            yield Horizontal(
                Button("Add Key [a]", id="add-btn", variant="primary"),
                Button("Close", id="close-btn"),
            )
            yield Label("Press [b]ESC[/b] to close", classes="form-hint")

    def on_mount(self):
        """Load API keys on mount."""
        self._load_keys()

    def _load_keys(self):
        """Load and display API keys."""
        key_list = self.query_one("#apikeys-list", Vertical)
        key_list.remove_children()

        try:
            if self._search_query:
                keys = self._api_key_manager.search_in_vault(self._search_query)
            else:
                keys = self._api_key_manager.get_all_from_vault()
            
            for key in keys:
                preset = get_preset(key.platform)
                icon = preset.get("icon", "🔑")
                masked = self._api_key_manager.mask_key(key.key_value)
                tags_str = ", ".join(f"#{t}" for t in key.tags) if key.tags else ""
                
                item_content = (
                    f"{icon} {key.name}\n"
                    f"  Platform: {key.platform}\n"
                    f"  Key: {masked}"
                )
                if tags_str:
                    item_content += f"\n  Tags: {tags_str}"
                
                key_list.mount(
                    Static(item_content, classes="apikey-item"),
                    before=0 if key_list.children else None
                )
                
                # Store key ID on the widget for later reference
                key_list.children[0].key_id = key.id
        except Exception as e:
            key_list.mount(Static(f"Error loading keys: {e}", classes="apikey-item"))

    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes."""
        if event.input.id == "search-input":
            self._search_query = event.value
            self._load_keys()

    def on_click(self, event):
        """Handle clicks on API key items."""
        key_list = self.query_one("#apikeys-list", Vertical)
        for child in key_list.children:
            if child.mouse_over and hasattr(child, 'key_id'):
                self._show_key_detail(child.key_id)
                break

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "add-btn":
            self._add_key()
        elif button_id == "close-btn":
            self.action_close()

    def _add_key(self):
        """Open screen to add a new API key."""
        self.app.push_screen(APIKeyEditScreen(), callback=self._on_key_saved)

    def _show_key_detail(self, key_id: str):
        """Show detail screen for an API key."""
        key = self._api_key_manager.get_from_vault(key_id)
        if key:
            self.app.push_screen(
                APIKeyDetailScreen(key, self._api_key_manager),
                callback=self._on_detail_closed
            )

    def _on_key_saved(self, key_data: Optional[dict]):
        """Handle key save callback."""
        if key_data:
            try:
                api_key = self._api_key_manager.create_key(**key_data)
                self._api_key_manager.add_to_vault(api_key)
                self.app.notify(f"API key '{api_key.name}' added", severity="information")
                self._load_keys()
            except Exception as e:
                self.app.notify(f"Failed to add key: {e}", severity="error")

    def _on_detail_closed(self, result: Optional[str]):
        """Handle detail screen close."""
        if result == "deleted":
            self._load_keys()
        elif result and result.startswith("edited:"):
            self._load_keys()

    def action_add_key(self):
        """Add key action."""
        self._add_key()

    def action_search(self):
        """Focus search input."""
        self.query_one("#search-input", Input).focus()

    def action_close(self):
        """Close the screen."""
        self.dismiss(None)


class APIKeyEditScreen(Screen):
    """Screen for creating/editing API keys."""

    CSS = """
    APIKeyEditScreen {
        align: center middle;
    }
    APIKeyEditScreen #edit-container {
        width: auto;
        min-width: 60;
        max-width: 80;
        height: auto;
        max-height: 95%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    APIKeyEditScreen #edit-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    APIKeyEditScreen .form-field {
        margin: 1 0;
        height: auto;
    }
    APIKeyEditScreen .field-label {
        color: $text;
        margin-bottom: 1;
    }
    APIKeyEditScreen Input {
        width: 100%;
    }
    APIKeyEditScreen Select {
        width: 100%;
    }
    APIKeyEditScreen #platform-select {
        margin-bottom: 1;
    }
    APIKeyEditScreen .validation-hint {
        color: $text-muted;
        text-style: dim;
        margin-top: 1;
    }
    APIKeyEditScreen .validation-error {
        color: $error;
        margin-top: 1;
    }
    APIKeyEditScreen .validation-success {
        color: $success;
        margin-top: 1;
    }
    APIKeyEditScreen #buttons {
        height: auto;
        align: center middle;
        margin-top: 2;
    }
    APIKeyEditScreen Button {
        margin: 0 1;
    }
    APIKeyEditScreen .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    APIKeyEditScreen #preset-info {
        background: $surface-darken-1;
        padding: 1;
        margin: 1 0;
        border: solid $primary-darken-2;
    }
    }
    """

    BINDINGS = [
        ("escape", "close", "Cancel"),
    ]

    def __init__(self, api_key: Optional[APIKey] = None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._is_new = api_key is None
        self._platforms = get_platforms_with_metadata()
        self._platform_options = [(f"{p[3]} {p[1]}", p[0]) for p in self._platforms]

    def compose(self) -> ComposeResult:
        """Compose the edit screen."""
        with Container(id="edit-container"):
            title = "Add API Key" if self._is_new else "Edit API Key"
            yield Static(f"🔑 {title}", id="edit-title")
            
            # Platform selection
            yield Static("Platform:", classes="field-label")
            yield Select(
                self._platform_options,
                value=(self._api_key.platform if self._api_key else "custom"),
                id="platform-select"
            )
            
            # Preset info display
            yield Static("", id="preset-info")
            
            # Name field
            yield Static("Name:", classes="field-label")
            yield Input(
                value=self._api_key.name if self._api_key else "",
                placeholder="e.g., Production API Key",
                id="name-input"
            )
            
            # Key value field
            yield Static("API Key:", classes="field-label")
            yield Input(
                value=self._api_key.key_value if self._api_key else "",
                placeholder="Enter API key...",
                id="key-input",
                password=True
            )
            
            # Secret key field (for AWS-style keys)
            yield Static("Secret Key (if required):", classes="field-label")
            yield Input(
                value=self._api_key.secret_key if self._api_key else "",
                placeholder="Enter secret key...",
                id="secret-input",
                password=True
            )
            
            # Endpoint field
            yield Static("Custom Endpoint (optional):", classes="field-label")
            yield Input(
                value=self._api_key.endpoint if self._api_key else "",
                placeholder="https://api.example.com",
                id="endpoint-input"
            )
            
            # Tags field
            yield Static("Tags (comma-separated):", classes="field-label")
            tags_value = ", ".join(self._api_key.tags) if self._api_key and self._api_key.tags else ""
            yield Input(
                value=tags_value,
                placeholder="production, gpt4, ...",
                id="tags-input"
            )
            
            # Notes field
            yield Static("Notes:", classes="field-label")
            yield Input(
                value=self._api_key.notes if self._api_key else "",
                placeholder="Additional notes...",
                id="notes-input"
            )
            
            # Validation hint
            yield Static("", id="validation-hint", classes="validation-hint")
            
            # Buttons
            with Horizontal(id="buttons"):
                yield Button("Save", id="save-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn")
            
            yield Label("Press [b]ENTER[/b] to save • [b]ESC[/b] to cancel", classes="form-hint")

    def on_mount(self):
        """Update preset info on mount."""
        self._update_preset_info()

    def on_select_changed(self, event: Select.Changed):
        """Handle platform selection change."""
        if event.select.id == "platform-select":
            self._update_preset_info()

    def _update_preset_info(self):
        """Update preset info display based on selected platform."""
        platform_select = self.query_one("#platform-select", Select)
        platform = platform_select.value or "custom"
        
        preset = get_preset(platform)
        info_widget = self.query_one("#preset-info", Static)
        
        info_text = (
            f"[b]{preset['name']}[/b]\n"
            f"{preset['description']}\n"
        )
        if preset.get('example'):
            info_text += f"[dim]Example: {preset['example']}[/dim]"
        
        info_widget.update(info_text)
        
        # Show/hide secret field based on platform
        secret_label = self.query_one("#secret-input", Input)
        if preset.get('requires_secret'):
            secret_label.disabled = False
        else:
            secret_label.disabled = True

    def on_input_changed(self, event: Input.Changed):
        """Validate key format on input."""
        if event.input.id == "key-input":
            self._validate_key()

    def _validate_key(self):
        """Validate the API key format."""
        platform_select = self.query_one("#platform-select", Select)
        key_input = self.query_one("#key-input", Input)
        hint_widget = self.query_one("#validation-hint", Static)
        
        platform = platform_select.value or "custom"
        key_value = key_input.value
        
        if not key_value:
            hint_widget.update("")
            return
        
        is_valid = APIKeyManager.validate_key_format(platform, key_value)
        
        if is_valid:
            hint_widget.update("✓ Valid format")
            hint_widget.classes = "validation-success"
        else:
            preset = get_preset(platform)
            hint_widget.update(f"⚠ Format doesn't match {preset['name']} pattern")
            hint_widget.classes = "validation-error"

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._save_key()
        elif event.button.id == "cancel-btn":
            self.action_close()

    def _save_key(self):
        """Save the API key."""
        platform = self.query_one("#platform-select", Select).value or "custom"
        name = self.query_one("#name-input", Input).value.strip()
        key_value = self.query_one("#key-input", Input).value
        secret_key = self.query_one("#secret-input", Input).value
        endpoint = self.query_one("#endpoint-input", Input).value.strip()
        tags_str = self.query_one("#tags-input", Input).value
        notes = self.query_one("#notes-input", Input).value
        
        if not name:
            self.app.notify("Name is required", severity="error")
            return
        
        if not key_value:
            self.app.notify("API key is required", severity="error")
            return
        
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        
        key_data = {
            "name": name,
            "platform": platform,
            "key_value": key_value,
            "secret_key": secret_key,
            "endpoint": endpoint,
            "tags": tags,
            "notes": notes,
        }
        
        self.dismiss(key_data)

    def action_close(self):
        """Close without saving."""
        self.dismiss(None)


class APIKeyDetailScreen(Screen):
    """Screen for viewing API key details."""

    CSS = """
    APIKeyDetailScreen {
        align: center middle;
    }
    APIKeyDetailScreen #detail-container {
        width: auto;
        min-width: 60;
        max-width: 80;
        height: auto;
        max-height: 95%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    APIKeyDetailScreen #detail-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    APIKeyDetailScreen #key-info {
        margin: 1 0;
    }
    APIKeyDetailScreen .info-row {
        layout: horizontal;
        height: auto;
        margin: 1 0;
    }
    APIKeyDetailScreen .info-label {
        color: $text-muted;
        width: 15;
    }
    APIKeyDetailScreen .info-value {
        color: $text;
        width: 1fr;
    }
    APIKeyDetailScreen .key-value {
        color: $warning;
        background: $surface-darken-2;
        padding: 1;
    }
    APIKeyDetailScreen #copy-buttons {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-gutter: 1;
        margin: 2 0;
    }
    APIKeyDetailScreen #copy-buttons Button {
        width: 100%;
    }
    APIKeyDetailScreen #env-export {
        background: $surface-darken-1;
        border: solid $primary-darken-2;
        padding: 1;
        margin: 1 0;
    }
    APIKeyDetailScreen #action-buttons {
        height: auto;
        align: center middle;
        margin-top: 2;
    }
    APIKeyDetailScreen #action-buttons Button {
        margin: 0 1;
    }
    APIKeyDetailScreen .form-hint {
        text-align: center;
        color: $text-muted;
        padding: 1 0;
    }
    APIKeyDetailScreen .masked {
        color: $text-muted;
    }
        APIKeyDetailScreen #copy-buttons {
            grid-size: 1;
        }
    }
    """

    BINDINGS = [
        ("escape", "close", "Close"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
    ]

    def __init__(self, api_key: APIKey, api_key_manager: APIKeyManager, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._api_key_manager = api_key_manager
        self._show_full_key = False

    def compose(self) -> ComposeResult:
        """Compose the detail screen."""
        preset = get_preset(self._api_key.platform)
        icon = preset.get("icon", "🔑")
        
        with Container(id="detail-container"):
            yield Static(f"{icon} {self._api_key.name}", id="detail-title")
            
            with Vertical(id="key-info"):
                # Platform
                with Horizontal(classes="info-row"):
                    yield Static("Platform:", classes="info-label")
                    yield Static(preset['name'], classes="info-value")
                
                # Key value (masked by default)
                with Horizontal(classes="info-row"):
                    yield Static("Key:", classes="info-label")
                    yield Static(
                        self._api_key.get_masked_key(),
                        id="key-display",
                        classes="info-value key-value"
                    )
                
                # Secret key (if present)
                if self._api_key.secret_key:
                    with Horizontal(classes="info-row"):
                        yield Static("Secret:", classes="info-label")
                        yield Static(
                            self._api_key.get_masked_secret(),
                            id="secret-display",
                            classes="info-value key-value"
                        )
                
                # Endpoint
                if self._api_key.endpoint or preset.get('endpoint'):
                    endpoint = self._api_key.endpoint or preset['endpoint']
                    with Horizontal(classes="info-row"):
                        yield Static("Endpoint:", classes="info-label")
                        yield Static(endpoint, classes="info-value")
                
                # Tags
                if self._api_key.tags:
                    with Horizontal(classes="info-row"):
                        yield Static("Tags:", classes="info-label")
                        yield Static(", ".join(f"#{t}" for t in self._api_key.tags),
                                    classes="info-value")
                
                # Notes
                if self._api_key.notes:
                    with Horizontal(classes="info-row"):
                        yield Static("Notes:", classes="info-label")
                        yield Static(self._api_key.notes, classes="info-value")
                
                # Created/Updated
                with Horizontal(classes="info-row"):
                    yield Static("Created:", classes="info-label")
                    yield Static(self._api_key.created_at[:19], classes="info-value")
            
            # Copy buttons
            with Grid(id="copy-buttons"):
                yield Button("📋 Copy Key", id="copy-key-btn")
                yield Button("📋 Copy Header", id="copy-header-btn")
                yield Button("📋 Copy cURL", id="copy-curl-btn")
                yield Button("📋 Copy Env", id="copy-env-btn")
            
            # Environment export preview
            yield Static(
                f"[dim]{self._api_key.get_env_export()}[/dim]",
                id="env-export"
            )
            
            # Action buttons
            with Horizontal(id="action-buttons"):
                yield Button("👁 Reveal", id="reveal-btn")
                yield Button("✏️ Edit [e]", id="edit-btn")
                yield Button("🗑 Delete [d]", id="delete-btn", variant="error")
                yield Button("Close", id="close-btn")
            
            yield Label("Press [b]ESC[/b] to close", classes="form-hint")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "copy-key-btn":
            self._copy_key()
        elif button_id == "copy-header-btn":
            self._copy_header()
        elif button_id == "copy-curl-btn":
            self._copy_curl()
        elif button_id == "copy-env-btn":
            self._copy_env()
        elif button_id == "reveal-btn":
            self._toggle_reveal()
        elif button_id == "edit-btn":
            self.action_edit()
        elif button_id == "delete-btn":
            self.action_delete()
        elif button_id == "close-btn":
            self.action_close()

    def _copy_key(self):
        """Copy API key to clipboard."""
        try:
            from ..utils.clipboard import ClipboardManager
            clipboard = ClipboardManager()
            clipboard.copy(self._api_key.key_value)
            self.app.notify("API key copied to clipboard", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    def _copy_header(self):
        """Copy Authorization header to clipboard."""
        try:
            from ..utils.clipboard import ClipboardManager
            clipboard = ClipboardManager()
            header = self._api_key.get_authorization_header()
            clipboard.copy(header)
            self.app.notify("Authorization header copied", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    def _copy_curl(self):
        """Copy curl command to clipboard."""
        try:
            from ..utils.clipboard import ClipboardManager
            clipboard = ClipboardManager()
            curl = self._api_key.get_curl_command()
            clipboard.copy(curl)
            self.app.notify("curl command copied", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    def _copy_env(self):
        """Copy environment variable export to clipboard."""
        try:
            from ..utils.clipboard import ClipboardManager
            clipboard = ClipboardManager()
            env = self._api_key.get_env_export()
            clipboard.copy(env)
            self.app.notify("Environment export copied", severity="information")
        except Exception as e:
            self.app.notify(f"Failed to copy: {e}", severity="error")

    def _toggle_reveal(self):
        """Toggle key visibility."""
        self._show_full_key = not self._show_full_key
        
        key_display = self.query_one("#key-display", Static)
        reveal_btn = self.query_one("#reveal-btn", Button)
        
        if self._show_full_key:
            key_display.update(self._api_key.key_value)
            reveal_btn.label = "🙈 Hide"
        else:
            key_display.update(self._api_key.get_masked_key())
            reveal_btn.label = "👁 Reveal"

    def action_edit(self):
        """Edit the API key."""
        self.dismiss(f"edited:{self._api_key.id}")

    def action_delete(self):
        """Delete the API key."""
        self.app.push_screen(
            ConfirmDeleteScreen(f"Delete API key '{self._api_key.name}'?"),
            callback=self._on_delete_confirmed
        )

    def _on_delete_confirmed(self, confirmed: bool):
        """Handle delete confirmation."""
        if confirmed:
            try:
                self._api_key_manager.delete_from_vault(self._api_key.id)
                self.app.notify(f"API key '{self._api_key.name}' deleted", severity="information")
                self.dismiss("deleted")
            except Exception as e:
                self.app.notify(f"Failed to delete: {e}", severity="error")

    def action_close(self):
        """Close the screen."""
        self.dismiss(None)


class ConfirmDeleteScreen(Screen):
    """Confirmation dialog for deletion."""

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    ConfirmDeleteScreen #confirm-container {
        width: auto;
        min-width: 40;
        max-width: 60;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1;
    }
    ConfirmDeleteScreen #confirm-title {
        text-style: bold;
        color: $error;
        text-align: center;
        margin-bottom: 1;
    }
    ConfirmDeleteScreen #confirm-message {
        text-align: center;
        margin: 1 0;
    }
    ConfirmDeleteScreen #confirm-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    ConfirmDeleteScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        """Compose the confirmation screen."""
        with Container(id="confirm-container"):
            yield Static("⚠️ Confirm Deletion", id="confirm-title")
            yield Static(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes, Delete", id="yes-btn", variant="error")
                yield Button("Cancel", id="no-btn")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "yes-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_key(self, event):
        """Handle keyboard input."""
        if event.key == "escape":
            self.dismiss(False)
