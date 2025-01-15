"""AI Provider plugin system for homeclaw."""
from __future__ import annotations

from .base_client import BaseHTTPClient
from .registry import AIProvider, ProviderRegistry

# Import providers to trigger registration
from . import anthropic  # noqa: F401
from . import anthropic_oauth  # noqa: F401
from . import gemini  # noqa: F401
from . import gemini_oauth  # noqa: F401
from . import groq  # noqa: F401
from . import local  # noqa: F401
from . import openai  # noqa: F401
from . import openrouter  # noqa: F401

__all__ = ["AIProvider", "ProviderRegistry", "BaseHTTPClient"]
