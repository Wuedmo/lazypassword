"""
Key binding definitions for lazypassword TUI.

Provides centralized key binding management with Vim-style navigation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


@dataclass
class KeyHelp:
    """Help text for a key binding."""
    key: str
    description: str
    category: str


class KeyCategory(Enum):
    """Categories for key bindings."""
    NAVIGATION = "navigation"
    ACTIONS = "actions"
    EDITING = "editing"
    SEARCH = "search"
    SYSTEM = "system"


class KeyBindings:
    """
    Centralized key binding definitions.
    
    All key bindings are defined here for easy customization and reference.
    Uses Vim-style navigation patterns.
    """
    
    # Navigation keys
    UP = "k"
    DOWN = "j"
    UP_ALT = "up"
    DOWN_ALT = "down"
    TOP = "g"
    BOTTOM = "G"
    BACK = "h"
    FORWARD = "l"
    LEFT = "left"
    RIGHT = "right"
    
    # Action keys
    SELECT = "enter"
    QUIT = "q"
    BACKSPACE = "backspace"
    DELETE = "d"
    EDIT = "e"
    NEW = "n"
    COPY = "c"
    COPY_USERNAME = "u"
    COPY_PASSWORD = "p"
    
    # Search
    SEARCH = "/"
    CLEAR_SEARCH = "escape"
    NEXT_RESULT = "n"
    PREV_RESULT = "N"
    
    # Editing
    SAVE = "ctrl+s"
    CANCEL = "escape"
    
    # System
    HELP = "?"
    REFRESH = "r"
    TOGGLE_MASK = "m"
    GENERATE = "ctrl+g"
    
    # Multi-key sequences (handled specially)
    GOTO_TOP = "gg"
    
    @classmethod
    def get_all_bindings(cls) -> Dict[str, KeyHelp]:
        """Get all key bindings with their help text."""
        return {
            # Navigation
            cls.UP: KeyHelp(cls.UP, "Move selection up", KeyCategory.NAVIGATION.value),
            cls.DOWN: KeyHelp(cls.DOWN, "Move selection down", KeyCategory.NAVIGATION.value),
            cls.UP_ALT: KeyHelp("↑", "Move selection up", KeyCategory.NAVIGATION.value),
            cls.DOWN_ALT: KeyHelp("↓", "Move selection down", KeyCategory.NAVIGATION.value),
            cls.GOTO_TOP: KeyHelp("gg", "Jump to top", KeyCategory.NAVIGATION.value),
            cls.BOTTOM: KeyHelp(cls.BOTTOM, "Jump to bottom", KeyCategory.NAVIGATION.value),
            cls.BACK: KeyHelp(cls.BACK, "Go back / Left pane", KeyCategory.NAVIGATION.value),
            cls.FORWARD: KeyHelp(cls.FORWARD, "Go forward / Right pane", KeyCategory.NAVIGATION.value),
            cls.LEFT: KeyHelp("←", "Move left", KeyCategory.NAVIGATION.value),
            cls.RIGHT: KeyHelp("→", "Move right", KeyCategory.NAVIGATION.value),
            
            # Actions
            cls.SELECT: KeyHelp("Enter", "Select / Confirm", KeyCategory.ACTIONS.value),
            cls.QUIT: KeyHelp(cls.QUIT, "Quit application", KeyCategory.ACTIONS.value),
            cls.DELETE: KeyHelp(cls.DELETE, "Delete entry", KeyCategory.ACTIONS.value),
            cls.EDIT: KeyHelp(cls.EDIT, "Edit entry", KeyCategory.ACTIONS.value),
            cls.NEW: KeyHelp(cls.NEW, "Create new entry", KeyCategory.ACTIONS.value),
            cls.COPY: KeyHelp(cls.COPY, "Copy to clipboard", KeyCategory.ACTIONS.value),
            cls.COPY_USERNAME: KeyHelp(cls.COPY_USERNAME, "Copy username", KeyCategory.ACTIONS.value),
            cls.COPY_PASSWORD: KeyHelp(cls.COPY_PASSWORD, "Copy password", KeyCategory.ACTIONS.value),
            
            # Search
            cls.SEARCH: KeyHelp(cls.SEARCH, "Search / Filter", KeyCategory.SEARCH.value),
            cls.CLEAR_SEARCH: KeyHelp("Esc", "Clear search / Cancel", KeyCategory.SEARCH.value),
            cls.NEXT_RESULT: KeyHelp(cls.NEXT_RESULT, "Next search result", KeyCategory.SEARCH.value),
            cls.PREV_RESULT: KeyHelp("Shift+N", "Previous search result", KeyCategory.SEARCH.value),
            
            # Editing
            cls.SAVE: KeyHelp("Ctrl+S", "Save changes", KeyCategory.EDITING.value),
            
            # System
            cls.HELP: KeyHelp(cls.HELP, "Show help", KeyCategory.SYSTEM.value),
            cls.REFRESH: KeyHelp(cls.REFRESH, "Refresh data", KeyCategory.SYSTEM.value),
            cls.TOGGLE_MASK: KeyHelp(cls.TOGGLE_MASK, "Toggle password mask", KeyCategory.SYSTEM.value),
            cls.GENERATE: KeyHelp("Ctrl+G", "Generate password", KeyCategory.SYSTEM.value),
        }
    
    @classmethod
    def get_by_category(cls, category: KeyCategory) -> List[KeyHelp]:
        """Get key bindings filtered by category."""
        all_bindings = cls.get_all_bindings()
        return [
            binding for binding in all_bindings.values()
            if binding.category == category.value
        ]
    
    @classmethod
    def get_formatted_help(cls) -> str:
        """Get formatted help text for all bindings."""
        lines = []
        
        categories = [
            ("Navigation", KeyCategory.NAVIGATION.value),
            ("Actions", KeyCategory.ACTIONS.value),
            ("Search", KeyCategory.SEARCH.value),
            ("Editing", KeyCategory.EDITING.value),
            ("System", KeyCategory.SYSTEM.value),
        ]
        
        for cat_name, cat_value in categories:
            lines.append(f"\n[bold cyan]{cat_name}[/bold cyan]")
            bindings = [
                binding for binding in cls.get_all_bindings().values()
                if binding.category == cat_value
            ]
            for binding in bindings:
                lines.append(f"  [yellow]{binding.key:12}[/yellow] {binding.description}")
        
        return "\n".join(lines)
    
    @classmethod
    def get_quick_help(cls) -> List[Tuple[str, str]]:
        """Get quick help for status bar (key, description)."""
        return [
            ("?", "help"),
            ("/", "search"),
            ("n", "new"),
            ("e", "edit"),
            ("d", "delete"),
            ("q", "quit"),
        ]


# Legacy compatibility - direct constants
KEYS = KeyBindings()
