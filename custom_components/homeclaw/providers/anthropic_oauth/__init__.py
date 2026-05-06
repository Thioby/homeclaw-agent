"""Anthropic OAuth subpackage for HomeClaw.

Ported from opencode-anthropic-auth v1.8.0 (MIT, © Ex Machina).
"""

from __future__ import annotations

from .auth import (
    AuthorizationRequest,
    OAuthRefreshError,
    TokenSet,
    authorize,
    create_api_key,
    exchange_code,
)
from .provider import AnthropicOAuthProvider

__all__ = [
    "AnthropicOAuthProvider",
    "AuthorizationRequest",
    "OAuthRefreshError",
    "TokenSet",
    "authorize",
    "create_api_key",
    "exchange_code",
    "is_oauth_zero_cost_provider",
]


def is_oauth_zero_cost_provider(provider_name: str) -> bool:
    """Provider names whose model usage is unlimited under OAuth subscription.

    Used by the Settings/Models UI to render cost as 0 for these providers.
    """
    return provider_name == "anthropic_oauth"
