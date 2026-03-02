"""
Custom widgets for lazypassword TUI.

This module provides specialized widgets for password management
with proper styling, focus management, and vim-style navigation.
"""

import secrets
import string
from typing import Callable, List, Optional, Any

from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    ListItem,
    ListView,
    RadioSet,
    RichLog,
    Rule,
    Static,
    Switch,
)
from textual.widget import Widget


class PasswordEntry:
    """Data class representing a password entry."""
    def __init__(
        self,
        id: str,
        title: str,
        username: str = "",
        password: str = "",
        url: str = "",
        notes: str = "",
        tags: List[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        self.id = id
        self.title = title
        self.username = username
        self.password = password
        self.url = url
        self.notes = notes
        self.tags = tags or []
        self.created_at = created_at
        self.updated_at = updated_at
    
    def matches_search(self, query: str) -> bool:
        """Check if entry matches search query."""
        query = query.lower()
        search_text = f"{self.title} {self.username} {self.url} {' '.join(self.tags)}"
        return query in search_text.lower()


class EntryList(Widget):
    """List view of password entries with vim-style navigation and search."""
    
    entries: reactive[List[PasswordEntry]] = reactive([])
    filtered_entries: reactive[List[PasswordEntry]] = reactive([])
    search_query: reactive[str] = reactive("")
    selected_index: reactive[int] = reactive(0)
    
    DEFAULT_CSS = """
    EntryList {
        width: 100%;
        height: 100%;
        border: solid $primary;
        background: $surface;
    }
    EntryList:focus {
        border: solid $primary-light;
    }
    EntryList .search-input {
        dock: top;
        height: 3;
        border: none;
        border-bottom: solid $primary;
        padding: 1;
        background: $surface-darken-1;
    }
    EntryList .list-container {
        height: 1fr;
        overflow: auto;
    }
    EntryList .entry-item {
        height: auto;
        padding: 1;
        border-bottom: solid $surface-darken-1;
    }
    EntryList .entry-item:hover {
        background: $surface-lighten-1;
    }
    EntryList .entry-item.selected {
        background: $primary-darken-2;
    }
    EntryList .entry-item.focused {
        background: $primary;
    }
    EntryList .entry-title {
        text-style: bold;
        color: $text;
    }
    EntryList .entry-meta {
        color: $text-muted;
        text-style: dim;
    }
    EntryList .empty-state {
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
        height: 100%;
    }
    """
    
    def __init__(self, entries: List[PasswordEntry] = None, **kwargs):
        super().__init__(**kwargs)
        self.entries = entries or []
        self.filtered_entries = self.entries.copy()
        self.selected_index = 0
    
    def compose(self):
        """Compose the entry list widget."""
        yield Input(
            placeholder="Press / to search...",
            id="search-input",
            classes="search-input",
            disabled=True,
        )
        
        entries_container = Container(id="entries-container", classes="list-container")
        yield entries_container
    
    def on_mount(self):
        """Refresh display on mount."""
        self.refresh_entries()
    
    def watch_entries(self, entries: List[PasswordEntry]):
        """React to entries changes."""
        self.apply_search()
    
    def watch_search_query(self, query: str):
        """React to search query changes."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = query
        self.apply_search()
    
    def apply_search(self):
        """Apply search filter to entries."""
        if not self.search_query:
            self.filtered_entries = self.entries.copy()
        else:
            self.filtered_entries = [
                e for e in self.entries
                if e.matches_search(self.search_query)
            ]
        self.selected_index = 0
        self.refresh_entries()
    
    def refresh_entries(self):
        """Refresh the entries display."""
        container = self.query_one("#entries-container", Container)
        container.remove_children()
        
        if not self.filtered_entries:
            container.mount(Static(
                "No entries found" if self.search_query else "No entries yet\nPress 'n' to create one",
                classes="empty-state"
            ))
            return
        
        for i, entry in enumerate(self.filtered_entries):
            is_selected = i == self.selected_index
            item_classes = f"entry-item {'selected' if is_selected else ''}"
            
            tags_display = f" [dim]· {' '.join(f'#{tag}' for tag in entry.tags)}[/dim]" if entry.tags else ""
            
            item = Static(
                f"{entry.title}{tags_display}\n[dim]{entry.username or 'no username'}[/dim]",
                classes=item_classes,
                id=f"entry-{i}"
            )
            container.mount(item)
    
    def move_selection(self, direction: int):
        """Move selection by direction amount."""
        if not self.filtered_entries:
            return
        
        new_index = self.selected_index + direction
        self.selected_index = max(0, min(new_index, len(self.filtered_entries) - 1))
        self.refresh_entries()
        
        # Post message about selection change
        self.post_message(self.EntrySelected(self.filtered_entries[self.selected_index]))
    
    def goto_top(self):
        """Jump to top of list."""
        self.selected_index = 0
        self.refresh_entries()
        if self.filtered_entries:
            self.post_message(self.EntrySelected(self.filtered_entries[0]))
    
    def goto_bottom(self):
        """Jump to bottom of list."""
        if self.filtered_entries:
            self.selected_index = len(self.filtered_entries) - 1
            self.refresh_entries()
            self.post_message(self.EntrySelected(self.filtered_entries[self.selected_index]))
    
    def start_search(self):
        """Enable search mode."""
        search_input = self.query_one("#search-input", Input)
        search_input.disabled = False
        search_input.focus()
        self.search_query = ""
    
    def end_search(self):
        """End search mode."""
        search_input = self.query_one("#search-input", Input)
        search_input.disabled = True
        search_input.value = ""
        self.search_query = ""
        self.focus()
    
    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_query = event.value
    
    def on_key(self, event):
        """Handle vim-style navigation keys."""
        if not self.filtered_entries:
            return
        
        key = event.key
        if key == "j" or key == "down":
            self.move_selection(1)
        elif key == "k" or key == "up":
            self.move_selection(-1)
        elif key == "G":
            self.goto_bottom()
        elif key == "enter":
            if self.filtered_entries and self.selected_index < len(self.filtered_entries):
                self.post_message(self.EntryOpen(self.filtered_entries[self.selected_index]))
    
    class EntrySelected(Message):
        """Message sent when entry selection changes."""
        def __init__(self, entry: PasswordEntry):
            super().__init__()
            self.entry = entry
    
    class EntryOpen(Message):
        """Message sent when entry is opened."""
        def __init__(self, entry: PasswordEntry):
            super().__init__()
            self.entry = entry


class EntryDetail(Widget):
    """Detail view showing entry fields."""
    
    entry: reactive[Optional[PasswordEntry]] = reactive(None)
    show_password: reactive[bool] = reactive(False)
    
    DEFAULT_CSS = """
    EntryDetail {
        width: 100%;
        height: 100%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    EntryDetail:focus {
        border: solid $primary-light;
    }
    EntryDetail .detail-header {
        height: auto;
        margin-bottom: 1;
        border-bottom: solid $primary;
    }
    EntryDetail .detail-title {
        text-style: bold;
        color: $primary;
        text-align: left;
    }
    EntryDetail .detail-section {
        margin-top: 1;
        height: auto;
    }
    EntryDetail .field-label {
        color: $text-muted;
        text-style: dim;
    }
    EntryDetail .field-value {
        color: $text;
        margin-left: 2;
    }
    EntryDetail .field-value.password {
        color: $warning;
    }
    EntryDetail .tags-container {
        height: auto;
        margin-top: 1;
    }
    EntryDetail .tag {
        background: $surface-darken-2;
        color: $text;
        padding: 0 1;
        margin-right: 1;
    }
    EntryDetail .empty-state {
        content-align: center middle;
        color: $text-muted;
        height: 100%;
    }
    EntryDetail .notes {
        margin-top: 1;
        padding: 1;
        background: $surface-darken-1;
        border: solid $surface-lighten-1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entry = None
        self.show_password = False
    
    def watch_entry(self, entry: Optional[PasswordEntry]):
        """React to entry changes."""
        self.refresh_detail()
    
    def watch_show_password(self, show: bool):
        """React to password visibility toggle."""
        self.refresh_detail()
    
    def compose(self):
        """Compose the detail view."""
        yield Static("No entry selected", id="detail-content", classes="empty-state")
    
    def refresh_detail(self):
        """Refresh the detail display."""
        content = self.query_one("#detail-content", Static)
        
        if not self.entry:
            content.update("No entry selected\n[dim]Use j/k to navigate entries[/dim]")
            content.classes = "empty-state"
            return
        
        content.classes = ""
        
        # Build detail content
        lines = []
        
        # Header with title
        lines.append(f"[bold]{self.entry.title}[/bold]\n")
        
        # Fields
        if self.entry.username:
            lines.append(f"[dim]Username:[/dim]\n  {self.entry.username}")
        
        if self.entry.password:
            password_display = self.entry.password if self.show_password else "•" * min(len(self.entry.password), 20)
            lines.append(f"\n[dim]Password:[/dim]\n  [{('warning' if self.show_password else 'text')}]{password_display}[/]")
            lines.append(f"[dim]  Press 'm' to {'hide' if self.show_password else 'reveal'}[/dim]")
        
        if self.entry.url:
            lines.append(f"\n[dim]URL:[/dim]\n  {self.entry.url}")
        
        # Tags
        if self.entry.tags:
            lines.append(f"\n[dim]Tags:[/dim] {' '.join(f'[b]#{tag}[/b]' for tag in self.entry.tags)}")
        
        # Notes
        if self.entry.notes:
            lines.append(f"\n[dim]Notes:[/dim]")
            lines.append(f"{self.entry.notes}")
        
        # Metadata
        if self.entry.created_at:
            lines.append(f"\n[dim]Created: {self.entry.created_at}[/dim]")
        
        content.update("\n".join(lines))
    
    def toggle_password(self):
        """Toggle password visibility."""
        self.show_password = not self.show_password
    
    def copy_field(self, field: str):
        """Post message to copy a field to clipboard."""
        if not self.entry:
            return
        
        value = getattr(self.entry, field, "")
        if value:
            self.post_message(self.CopyToClipboard(value, field))
    
    class CopyToClipboard(Message):
        """Message sent when field should be copied to clipboard."""
        def __init__(self, value: str, field_name: str):
            super().__init__()
            self.value = value
            self.field_name = field_name


class StatusBar(Widget):
    """Bottom bar showing current mode/key hints."""
    
    mode: reactive[str] = reactive("NORMAL")
    message: reactive[str] = reactive("")
    
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface-darken-2;
        color: $text;
        padding: 0 1;
        content-align: left middle;
    }
    StatusBar .mode {
        background: $accent;
        color: $text;
        padding: 0 1;
        content-align: center middle;
    }
    StatusBar .keys {
        color: $text-muted;
    }
    StatusBar .message {
        color: $text;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = "NORMAL"
        self.message = ""
    
    def watch_mode(self, mode: str):
        """React to mode changes."""
        self.refresh_status()
    
    def watch_message(self, message: str):
        """React to message changes."""
        self.refresh_status()
    
    def compose(self):
        """Compose the status bar."""
        yield Static("[b]NORMAL[/b]", id="mode-indicator", classes="mode")
    
    def refresh_status(self):
        """Refresh the status bar display."""
        mode_indicator = self.query_one("#mode-indicator", Static)
        mode_indicator.update(f"[b]{self.mode}[/b]")
    
    def set_message(self, message: str, duration: float = 3.0):
        """Set a temporary status message."""
        self.message = message


class HelpPanel(Widget):
    """Overlay help panel with keybindings."""
    
    DEFAULT_CSS = """
    HelpPanel {
        width: auto;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        layer: overlay;
        display: none;
    }
    HelpPanel.visible {
        display: block;
    }
    HelpPanel .help-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
    }
    HelpPanel .help-section {
        margin-top: 1;
    }
    HelpPanel .help-category {
        text-style: bold;
        color: $accent;
    }
    HelpPanel .help-row {
        height: auto;
        margin: 0;
    }
    HelpPanel .key {
        color: $warning;
        width: 12;
    }
    HelpPanel .description {
        color: $text;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self):
        """Compose the help panel."""
        from .keybindings import KeyBindings
        
        yield Static("⌨️  Keyboard Shortcuts", classes="help-title")
        
        help_text = KeyBindings.get_formatted_help()
        yield Static(help_text, classes="help-content")
        yield Static("[dim]Press ? or Esc to close[/dim]", classes="help-footer")
    
    def toggle(self):
        """Toggle help panel visibility."""
        self.toggle_class("visible")


class PasswordInput(Input):
    """Password input with masking toggle."""
    
    DEFAULT_CSS = """
    PasswordInput {
        border: solid $primary;
        background: $surface;
        color: $text;
    }
    PasswordInput:focus {
        border: solid $primary-light;
    }
    """
    
    def __init__(self, password: bool = True, **kwargs):
        super().__init__(password=password, **kwargs)
        self._masked = password
    
    def toggle_mask(self):
        """Toggle password masking."""
        self.password = not self.password


class EntryForm(Widget):
    """Form for creating/editing entries."""
    
    entry: reactive[Optional[PasswordEntry]] = reactive(None)
    
    DEFAULT_CSS = """
    EntryForm {
        width: 100%;
        height: 100%;
        background: $surface;
        padding: 1 2;
    }
    EntryForm .form-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        height: auto;
        margin-bottom: 1;
    }
    EntryForm .form-field {
        margin: 1 0;
        height: auto;
    }
    EntryForm .field-label {
        color: $text;
        height: auto;
        margin-bottom: 0;
    }
    EntryForm Input {
        border: solid $primary-darken-2;
        background: $surface-darken-2;
    }
    EntryForm Input:focus {
        border: solid $primary;
    }
    EntryForm .password-row {
        height: auto;
        layout: horizontal;
    }
    EntryForm .password-row Input {
        width: 1fr;
    }
    EntryForm Button {
        margin-left: 1;
    }
    EntryForm .form-buttons {
        dock: bottom;
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    EntryForm .form-buttons Button {
        margin: 0 1;
    }
    EntryForm #tags-input {
        margin-top: 1;
    }
    """
    
    def __init__(self, entry: PasswordEntry = None, **kwargs):
        super().__init__(**kwargs)
        self.entry = entry
    
    def compose(self):
        """Compose the entry form."""
        is_edit = self.entry is not None
        title = "Edit Entry" if is_edit else "New Entry"
        
        yield Static(title, classes="form-title")
        
        # Title field
        yield Static("Title *", classes="field-label")
        yield Input(
            value=self.entry.title if self.entry else "",
            placeholder="Entry title",
            id="title-input"
        )
        
        # Username field
        yield Static("Username", classes="field-label")
        yield Input(
            value=self.entry.username if self.entry else "",
            placeholder="Username or email",
            id="username-input"
        )
        
        # Password field
        yield Static("Password", classes="field-label")
        with Horizontal(classes="password-row"):
            yield PasswordInput(
                value=self.entry.password if self.entry else "",
                placeholder="Password",
                id="password-input"
            )
            yield Button("Generate", id="generate-btn", variant="primary")
        
        # URL field
        yield Static("URL", classes="field-label")
        yield Input(
            value=self.entry.url if self.entry else "",
            placeholder="https://example.com",
            id="url-input"
        )
        
        # Notes field
        yield Static("Notes", classes="field-label")
        yield Input(
            value=self.entry.notes if self.entry else "",
            placeholder="Additional notes...",
            id="notes-input",
            multiline=True
        )
        
        # Tags field
        yield Static("Tags (comma-separated)", classes="field-label")
        tags_value = ", ".join(self.entry.tags) if self.entry and self.entry.tags else ""
        yield Input(
            value=tags_value,
            placeholder="work, personal, ...",
            id="tags-input"
        )
        
        # Buttons
        with Horizontal(classes="form-buttons"):
            yield Button("Save (Ctrl+S)", id="save-btn", variant="success")
            yield Button("Cancel (Esc)", id="cancel-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        btn_id = event.button.id
        
        if btn_id == "save-btn":
            self.save_entry()
        elif btn_id == "cancel-btn":
            self.post_message(self.Cancelled())
        elif btn_id == "generate-btn":
            self.post_message(self.GeneratePassword())
    
    def save_entry(self):
        """Save the entry and post message."""
        title = self.query_one("#title-input", Input).value.strip()
        
        if not title:
            self.post_message(self.Error("Title is required"))
            return
        
        entry = PasswordEntry(
            id=self.entry.id if self.entry else "",
            title=title,
            username=self.query_one("#username-input", Input).value,
            password=self.query_one("#password-input", PasswordInput).value,
            url=self.query_one("#url-input", Input).value,
            notes=self.query_one("#notes-input", Input).value,
            tags=[t.strip() for t in self.query_one("#tags-input", Input).value.split(",") if t.strip()],
        )
        
        self.post_message(self.Saved(entry))
    
    class Saved(Message):
        """Message sent when entry is saved."""
        def __init__(self, entry: PasswordEntry):
            super().__init__()
            self.entry = entry
    
    class Cancelled(Message):
        """Message sent when editing is cancelled."""
        pass
    
    class GeneratePassword(Message):
        """Message sent when password generation is requested."""
        pass
    
    class Error(Message):
        """Message sent on validation error."""
        def __init__(self, message: str):
            super().__init__()
            self.message = message


class ConfirmDialog(Widget):
    """Yes/no confirmation dialog."""
    
    DEFAULT_CSS = """
    ConfirmDialog {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
        content-align: center middle;
    }
    ConfirmDialog .dialog-message {
        text-align: center;
        margin: 1 0;
        color: $text;
    }
    ConfirmDialog .dialog-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    ConfirmDialog Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self._message = message
    
    def compose(self):
        """Compose the dialog."""
        yield Static(self._message, classes="dialog-message")
        with Horizontal(classes="dialog-buttons"):
            yield Button("Yes (y)", id="yes-btn", variant="success")
            yield Button("No (n)", id="no-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "yes-btn":
            self.post_message(self.Confirmed())
        else:
            self.post_message(self.Cancelled())
        self.remove()
    
    def on_key(self, event):
        """Handle keyboard input."""
        if event.key == "y":
            self.post_message(self.Confirmed())
            self.remove()
        elif event.key == "n" or event.key == "escape":
            self.post_message(self.Cancelled())
            self.remove()
    
    class Confirmed(Message):
        """Message sent when user confirms."""
        pass
    
    class Cancelled(Message):
        """Message sent when user cancels."""
        pass


class PasswordGeneratorWidget(Widget):
    """Widget for generating passwords with options."""
    
    length: reactive[int] = reactive(16)
    include_uppercase: reactive[bool] = reactive(True)
    include_lowercase: reactive[bool] = reactive(True)
    include_numbers: reactive[bool] = reactive(True)
    include_symbols: reactive[bool] = reactive(True)
    generated_password: reactive[str] = reactive("")
    
    DEFAULT_CSS = """
    PasswordGeneratorWidget {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    PasswordGeneratorWidget .generator-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
    }
    PasswordGeneratorWidget .options-row {
        height: auto;
        margin: 1 0;
    }
    PasswordGeneratorWidget Checkbox {
        margin-right: 2;
    }
    PasswordGeneratorWidget .length-row {
        height: auto;
        margin: 1 0;
    }
    PasswordGeneratorWidget .password-display {
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        text-align: center;
        color: $accent;
    }
    PasswordGeneratorWidget .button-row {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    PasswordGeneratorWidget Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self):
        """Compose the password generator."""
        yield Static("🔐 Password Generator", classes="generator-title")
        
        # Character options
        with Horizontal(classes="options-row"):
            yield Checkbox("A-Z", value=True, id="uppercase")
            yield Checkbox("a-z", value=True, id="lowercase")
            yield Checkbox("0-9", value=True, id="numbers")
            yield Checkbox("!@#$", value=True, id="symbols")
        
        # Length
        with Horizontal(classes="length-row"):
            yield Static("Length: ", classes="length-label")
            yield Input(value="16", id="length-input", type="integer")
        
        # Generated password display
        yield Static(
            "[dim]Click Generate to create password[/dim]",
            id="generated-password",
            classes="password-display"
        )
        
        # Buttons
        with Horizontal(classes="button-row"):
            yield Button("Generate", id="generate-btn", variant="primary")
            yield Button("Use Password", id="use-btn", variant="success")
            yield Button("Cancel", id="cancel-btn", variant="error")
    
    def generate_password(self) -> str:
        """Generate a password based on current options."""
        chars = ""
        
        if self.include_uppercase:
            chars += string.ascii_uppercase
        if self.include_lowercase:
            chars += string.ascii_lowercase
        if self.include_numbers:
            chars += string.digits
        if self.include_symbols:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if not chars:
            return ""
        
        # Ensure at least one character from each selected category
        password = []
        if self.include_uppercase:
            password.append(secrets.choice(string.ascii_uppercase))
        if self.include_lowercase:
            password.append(secrets.choice(string.ascii_lowercase))
        if self.include_numbers:
            password.append(secrets.choice(string.digits))
        if self.include_symbols:
            password.append(secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))
        
        # Fill remaining length
        for _ in range(self.length - len(password)):
            password.append(secrets.choice(chars))
        
        # Shuffle
        secrets.SystemRandom().shuffle(password)
        
        return "".join(password)
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        btn_id = event.button.id
        
        if btn_id == "generate-btn":
            self.update_options()
            self.generated_password = self.generate_password()
            display = self.query_one("#generated-password", Static)
            if self.generated_password:
                display.update(f"[b]{self.generated_password}[/b]")
            else:
                display.update("[dim red]Select at least one character type[/dim red]")
        
        elif btn_id == "use-btn":
            if self.generated_password:
                self.post_message(self.PasswordSelected(self.generated_password))
        
        elif btn_id == "cancel-btn":
            self.post_message(self.Cancelled())
    
    def update_options(self):
        """Update options from checkboxes."""
        self.include_uppercase = self.query_one("#uppercase", Checkbox).value
        self.include_lowercase = self.query_one("#lowercase", Checkbox).value
        self.include_numbers = self.query_one("#numbers", Checkbox).value
        self.include_symbols = self.query_one("#symbols", Checkbox).value
        
        try:
            length_val = self.query_one("#length-input", Input).value
            self.length = max(4, min(128, int(length_val)))
        except ValueError:
            self.length = 16
    
    class PasswordSelected(Message):
        """Message sent when password is selected."""
        def __init__(self, password: str):
            super().__init__()
            self.password = password
    
    class Cancelled(Message):
        """Message sent when cancelled."""
        pass
