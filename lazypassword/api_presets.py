"""API key presets for common platforms.

This module defines validation patterns and metadata for API keys
from various platforms like OpenAI, AWS, Stripe, GitHub, etc.
"""

API_KEY_PRESETS = {
    "openai": {
        "name": "OpenAI",
        "description": "OpenAI API key (sk-...)",
        "prefix": "sk-",
        "pattern": r"^sk-[a-zA-Z0-9]{48}$",
        "format": "Bearer",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "requires_secret": False,
        "endpoint": "https://api.openai.com",
        "icon": "🔑",
    },
    "aws": {
        "name": "AWS",
        "description": "AWS Access Key ID and Secret",
        "prefix": "AKIA",
        "pattern": r"^AKIA[0-9A-Z]{16}$",
        "format": "access_key",
        "example": "AKIAIOSFODNN7EXAMPLE",
        "requires_secret": True,
        "endpoint": "",
        "icon": "☁️",
    },
    "stripe": {
        "name": "Stripe",
        "description": "Stripe API key (sk_live_... or sk_test_...)",
        "prefix": "sk_",
        "pattern": r"^sk_(live|test)_[0-9a-zA-Z]{24,}$",
        "format": "Bearer",
        "example": "sk_live_SAMPLE_KEY_NOT_REAL",
        "requires_secret": False,
        "endpoint": "https://api.stripe.com",
        "icon": "💳",
    },
    "github": {
        "name": "GitHub",
        "description": "GitHub Personal Access Token",
        "prefix": "ghp_",
        "pattern": r"^ghp_[0-9a-zA-Z]{36}$",
        "format": "Bearer",
        "example": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "requires_secret": False,
        "endpoint": "https://api.github.com",
        "icon": "🐙",
    },
    "anthropic": {
        "name": "Anthropic",
        "description": "Anthropic Claude API key",
        "prefix": "sk-ant-",
        "pattern": r"^sk-ant-[a-zA-Z0-9-]+$",
        "format": "x-api-key",
        "example": "sk-ant-...",
        "requires_secret": False,
        "endpoint": "https://api.anthropic.com",
        "icon": "🧠",
    },
    "huggingface": {
        "name": "Hugging Face",
        "description": "Hugging Face API token",
        "prefix": "hf_",
        "pattern": r"^hf_[a-zA-Z0-9]+$",
        "format": "Bearer",
        "example": "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "requires_secret": False,
        "endpoint": "https://huggingface.co",
        "icon": "🤗",
    },
    "google": {
        "name": "Google AI",
        "description": "Google AI/Gemini API key",
        "prefix": "",
        "pattern": r"^AIza[0-9A-Za-z_-]{35}$",
        "format": "key",
        "example": "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "requires_secret": False,
        "endpoint": "https://generativelanguage.googleapis.com",
        "icon": "🔍",
    },
    "openrouter": {
        "name": "OpenRouter",
        "description": "OpenRouter API key",
        "prefix": "sk-or-",
        "pattern": r"^sk-or-[a-zA-Z0-9-]+$",
        "format": "Bearer",
        "example": "sk-or-...",
        "requires_secret": False,
        "endpoint": "https://openrouter.ai",
        "icon": "🌐",
    },
    "custom": {
        "name": "Custom",
        "description": "Custom API key format",
        "prefix": "",
        "pattern": ".*",
        "format": "custom",
        "example": "",
        "requires_secret": False,
        "endpoint": "",
        "icon": "🔧",
    },
}


def get_preset(platform: str) -> dict:
    """Get preset for a specific platform.
    
    Args:
        platform: Platform identifier
        
    Returns:
        Preset dictionary or custom preset if not found
    """
    return API_KEY_PRESETS.get(platform, API_KEY_PRESETS["custom"])


def get_platforms() -> list:
    """Get list of supported platform identifiers.
    
    Returns:
        List of platform identifiers
    """
    return list(API_KEY_PRESETS.keys())


def get_platforms_with_metadata() -> list:
    """Get list of platforms with their metadata.
    
    Returns:
        List of tuples (id, name, description, icon)
    """
    return [
        (key, preset["name"], preset["description"], preset.get("icon", "🔑"))
        for key, preset in API_KEY_PRESETS.items()
    ]
