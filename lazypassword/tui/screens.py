"""
Screen definitions for lazypassword TUI.

This module provides all screens for the password manager application.
"""

from typing import List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .keybindings import KeyBindings
from .widgets import (
    ConfirmDialog,
    EntryDetail,
    EntryForm,
    EntryList,
    HelpPanel,
    PasswordEntry,
    PasswordGeneratorWidget,
    PasswordInput,
    StatusBar,
)


class MainScreen(Screen):
    """Main interface with list/detail split."""
    
    CSS = """
    MainScreen {
        align: center top;
    }
    MainScreen #main-container {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }
    MainScreen #list-pane {
        width: 40%;
        height: 100%;
        border: solid $primary;
    }
    MainScreen #detail-pane {
        width: 60%;
        height: 100%;
        border: solid $primary;
    }
    MainScreen #help-overlay {
        align: center middle;
    }
    MainScreen .help-modal {
        width: 80;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1;
        overflow: auto;
    }
    MainScreen #generator-modal {
        align: center middle;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "toggle_help", "Help"),
        ("n", "new_entry", "New Entry"),
        ("e", "edit_entry", "Edit Entry"),
        ("d", "delete_entry", "Delete Entry"),
        ("/", "search", "Search"),
        ("c", "copy_password", "Copy Password"),
        ("u", "copy_username", "Copy Username"),
        ("m", "toggle_mask", "Toggle Mask"),
        ("r", "refresh", "Refresh"),
        ("ctrl+g", "generate", "Generate Password"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entries: List[PasswordEntry] = []
        self._current_entry: Optional[PasswordEntry] = None
        self._show_help = False
    
    def compose(self) -> ComposeResult:
        """Compose the main screen."""
        # Main container with list and detail panes
        with Horizontal(id="main-container"):
            with Container(id="list-pane"):
                yield EntryList(id="entry-list")
            
            with Container(id="detail-pane"):
                yield EntryDetail(id="entry-detail")
        
        # Status bar
        yield StatusBar(id="status-bar")
        
        # Hidden help panel (shown via modal)
        
        yield Footer()
    
    def on_mount(self):
        """Handle mount event."""
        self.load_entries()
    
    def load_entries(self):
        """Load entries into the list."""
        # This would load from the actual password store
        # For now, we'll set empty entries
        entry_list = self.query_one("#entry-list", EntryList)
        entry_list.entries = self._entries
        
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_message(f"Loaded {len(self._entries)} entries")
    
    def on_entry_list_entry_selected(self, event: EntryList.EntrySelected):
        """Handle entry selection."""
        self._current_entry = event.entry
        detail = self.query_one("#entry-detail", EntryDetail)
        detail.entry = event.entry
        
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_message(f"Selected: {event.entry.title}")
    
    def on_entry_list_entry_open(self, event: EntryList.EntryOpen):
        """Handle entry open request."""
        self.action_edit_entry()
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()
    
    def action_new_entry(self):
        """Open new entry screen."""
        self.app.push_screen(EntryEditScreen())
    
    def action_edit_entry(self):
        """Open edit screen for current entry."""
        if self._current_entry:
            self.app.push_screen(EntryEditScreen(self._current_entry))
        else:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.set_message("No entry selected")
    
    def action_delete_entry(self):
        """Show delete confirmation."""
        if not self._current_entry:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.set_message("No entry selected")
            return
        
        def handle_result(confirmed: bool):
            if confirmed:
                self._perform_delete()
        
        self.app.push_screen(
            ConfirmDeleteScreen(self._current_entry.title),
            callback=handle_result
        )
    
    def _perform_delete(self):
        """Perform the actual deletion."""
        if self._current_entry:
            self._entries = [e for e in self._entries if e.id != self._current_entry.id]
            self.load_entries()
            
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.set_message(f"Deleted: {self._current_entry.title}")
            
            self._current_entry = None
            detail = self.query_one("#entry-detail", EntryDetail)
            detail.entry = None
    
    def action_search(self):
        """Enter search mode."""
        entry_list = self.query_one("#entry-list", EntryList)
        entry_list.start_search()
    
    def action_copy_password(self):
        """Copy current entry's password to clipboard."""
        if self._current_entry:
            detail = self.query_one("#entry-detail", EntryDetail)
            detail.copy_field("password")
        else:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.set_message("No entry selected")
    
    def action_copy_username(self):
        """Copy current entry's username to clipboard."""
        if self._current_entry:
            detail = self.query_one("#entry-detail", EntryDetail)
            detail.copy_field("username")
        else:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.set_message("No entry selected")
    
    def action_toggle_mask(self):
        """Toggle password visibility in detail view."""
        if self._current_entry:
            detail = self.query_one("#entry-detail", EntryDetail)
            detail.toggle_password()
    
    def action_refresh(self):
        """Refresh the entries list."""
        self.load_entries()
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.set_message("Refreshed")
    
    def action_generate(self):
        """Show password generator."""
        if self._current_entry:
            self.app.push_screen(
                PasswordGeneratorModal(),
                callback=self._on_generated_password
            )
    
    def _on_generated_password(self, password: Optional[str]):
        """Handle generated password."""
        if password:
            self.action_edit_entry()
            # The edit screen would need to receive the generated password
    
    def action_toggle_help(self):
        """Toggle help panel."""
        self._show_help = not self._show_help
        if self._show_help:
            self.app.push_screen(HelpScreen())
    
    def watch__show_help(self, show: bool):
        """React to help visibility change."""
        if not show:
            pass


class UnlockScreen(Screen):
    """Master password unlock screen."""
    
    CSS = """
    UnlockScreen {
        align: center middle;
        background: $surface-darken-2;
    }
    UnlockScreen #unlock-container {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
        content-align: center middle;
    }
    UnlockScreen #unlock-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        margin-bottom: 1;
    }
    UnlockScreen #unlock-icon {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    UnlockScreen #unlock-input {
        width: 100%;
        margin: 1 0;
    }
    UnlockScreen #unlock-error {
        color: $error;
        text-align: center;
        height: auto;
    }
    UnlockScreen #unlock-hint {
        text-align: center;
        color: $text-muted;
        text-style: dim;
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("enter", "submit", "Submit"),
        ("escape", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the unlock screen."""
        with Container(id="unlock-container"):
            yield Static("🔐", id="unlock-icon")
            yield Static("Enter Master Password", id="unlock-title")
            yield PasswordInput(
                placeholder="Master password...",
                id="unlock-input",
                password=True
            )
            yield Static("", id="unlock-error")
            yield Static("[dim]Press Enter to unlock, Esc to quit[/dim]", id="unlock-hint")
    
    def on_mount(self):
        """Focus the password input on mount."""
        self.query_one("#unlock-input", PasswordInput).focus()
    
    def action_submit(self):
        """Submit the master password."""
        password = self.query_one("#unlock-input", PasswordInput).value
        error_label = self.query_one("#unlock-error", Static)
        
        if not password:
            error_label.update("[error]Password required[/error]")
            return
        
        # Validate the password (this would check against the actual store)
        # For now, we just dismiss the screen with the password
        self.dismiss(password)
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()


class FirstRunScreen(Screen):
    """Create master password on first launch."""
    
    CSS = """
    FirstRunScreen {
        align: center middle;
        background: $surface-darken-2;
    }
    FirstRunScreen #first-run-container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 2;
    }
    FirstRunScreen #first-run-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        border-bottom: solid $accent;
        padding-bottom: 1;
        margin-bottom: 1;
    }
    FirstRunScreen #first-run-welcome {
        text-align: center;
        margin-bottom: 1;
    }
    FirstRunScreen .input-label {
        color: $text;
        margin-top: 1;
    }
    FirstRunScreen Input {
        width: 100%;
        margin: 0 0 1 0;
    }
    FirstRunScreen #first-run-error {
        color: $error;
        text-align: center;
        height: auto;
    }
    FirstRunScreen #first-run-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    FirstRunScreen Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        ("enter", "submit", "Submit"),
        ("escape", "quit", "Quit"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the first run screen."""
        with Container(id="first-run-container"):
            yield Static("🔐 lazypassword", id="first-run-title")
            yield Static(
                "Welcome! Let's set up your master password.\n"
                "This password will encrypt all your stored passwords.",
                id="first-run-welcome"
            )
            
            yield Static("Master Password:", classes="input-label")
            yield PasswordInput(id="password-1", password=True)
            
            yield Static("Confirm Password:", classes="input-label")
            yield PasswordInput(id="password-2", password=True)
            
            yield Static("", id="first-run-error")
            
            with Horizontal(id="first-run-buttons"):
                yield Button("Create Vault", id="create-btn", variant="success")
                yield Button("Exit", id="exit-btn", variant="error")
    
    def on_mount(self):
        """Focus the first password input."""
        self.query_one("#password-1", PasswordInput).focus()
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "create-btn":
            self.action_submit()
        else:
            self.action_quit()
    
    def action_submit(self):
        """Submit the new master password."""
        pass1 = self.query_one("#password-1", PasswordInput).value
        pass2 = self.query_one("#password-2", PasswordInput).value
        error_label = self.query_one("#first-run-error", Static)
        
        if not pass1:
            error_label.update("[error]Password cannot be empty[/error]")
            return
        
        if len(pass1) < 8:
            error_label.update("[error]Password must be at least 8 characters[/error]")
            return
        
        if pass1 != pass2:
            error_label.update("[error]Passwords do not match[/error]")
            return
        
        # Password is valid - dismiss with it
        self.dismiss(pass1)
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()


class EntryEditScreen(Screen):
    """Full-screen entry editing."""
    
    CSS = """
    EntryEditScreen {
        background: $surface-darken-2;
    }
    EntryEditScreen #edit-container {
        width: 80%;
        height: 90%;
        align: center middle;
        background: $surface;
        border: thick $primary;
    }
    """
    
    BINDINGS = [
        ("ctrl+s", "save", "Save"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, entry: Optional[PasswordEntry] = None, **kwargs):
        super().__init__(**kwargs)
        self._entry = entry
    
    def compose(self) -> ComposeResult:
        """Compose the edit screen."""
        with Container(id="edit-container"):
            yield EntryForm(entry=self._entry)
    
    def on_entry_form_saved(self, event: EntryForm.Saved):
        """Handle form save."""
        self.dismiss(event.entry)
    
    def on_entry_form_cancelled(self, event: EntryForm.Cancelled):
        """Handle form cancel."""
        self.dismiss(None)
    
    def on_entry_form_generate_password(self, event: EntryForm.GeneratePassword):
        """Handle password generation request."""
        self.app.push_screen(
            PasswordGeneratorModal(),
            callback=self._on_password_generated
        )
    
    def _on_password_generated(self, password: Optional[str]):
        """Handle generated password."""
        if password:
            form = self.query_one(EntryForm)
            password_input = form.query_one("#password-input", PasswordInput)
            password_input.value = password
    
    def action_save(self):
        """Save the entry."""
        form = self.query_one(EntryForm)
        form.save_entry()
    
    def action_cancel(self):
        """Cancel editing."""
        self.dismiss(None)


class HelpScreen(ModalScreen):
    """Full help overlay."""
    
    CSS = """
    HelpScreen {
        align: center middle;
        background: $background-darken-1 80%;
    }
    HelpScreen #help-container {
        width: 80;
        height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }
    HelpScreen #help-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        padding-bottom: 1;
    }
    HelpScreen #help-content {
        height: 1fr;
        overflow: auto;
        padding: 1;
    }
    HelpScreen #help-footer {
        text-align: center;
        color: $text-muted;
        border-top: solid $surface-darken-2;
        padding-top: 1;
    }
    """
    
    BINDINGS = [
        ("?", "close", "Close"),
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Container(id="help-container"):
            yield Static("⌨️  Keyboard Shortcuts", id="help-title")
            
            help_text = KeyBindings.get_formatted_help()
            yield Static(help_text, id="help-content")
            
            yield Static("Press ? or Esc to close", id="help-footer")
    
    def action_close(self):
        """Close the help screen."""
        self.dismiss()


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Confirm deletion modal."""
    
    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
        background: $background-darken-1 60%;
    }
    ConfirmDeleteScreen #delete-container {
        width: 50;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1;
    }
    """
    
    BINDINGS = [
        ("y", "confirm", "Yes"),
        ("n", "cancel", "No"),
        ("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, entry_title: str, **kwargs):
        super().__init__(**kwargs)
        self._title = entry_title
    
    def compose(self) -> ComposeResult:
        """Compose the confirm dialog."""
        with Container(id="delete-container"):
            yield ConfirmDialog(
                f"Delete entry '{self._title}'?\n\nThis cannot be undone."
            )
    
    def on_confirm_dialog_confirmed(self, event: ConfirmDialog.Confirmed):
        """Handle confirmation."""
        self.dismiss(True)
    
    def on_confirm_dialog_cancelled(self, event: ConfirmDialog.Cancelled):
        """Handle cancellation."""
        self.dismiss(False)
    
    def action_confirm(self):
        """Confirm deletion."""
        self.dismiss(True)
    
    def action_cancel(self):
        """Cancel deletion."""
        self.dismiss(False)


class PasswordGeneratorModal(ModalScreen[str]):
    """Password generator modal."""
    
    CSS = """
    PasswordGeneratorModal {
        align: center middle;
        background: $background-darken-1 60%;
    }
    """
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the generator modal."""
        yield PasswordGeneratorWidget()
    
    def on_password_generator_widget_password_selected(
        self, event: PasswordGeneratorWidget.PasswordSelected
    ):
        """Handle password selection."""
        self.dismiss(event.password)
    
    def on_password_generator_widget_cancelled(
        self, event: PasswordGeneratorWidget.Cancelled
    ):
        """Handle cancellation."""
        self.dismiss(None)
    
    def action_cancel(self):
        """Cancel and close."""
        self.dismiss(None)