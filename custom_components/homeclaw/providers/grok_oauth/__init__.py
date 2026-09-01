from __future__ import annotations

from .auth import (
    DeviceCode,
    InflightRefreshGate,
    OAuthRefreshError,
    TokenSet,
    poll_device_code_token,
    request_device_code,
)
from .provider import GrokOAuthProvider

__all__ = [
    "DeviceCode",
    "GrokOAuthProvider",
    "InflightRefreshGate",
    "OAuthRefreshError",
    "TokenSet",
    "is_oauth_zero_cost_provider",
    "poll_device_code_token",
    "request_device_code",
]


def is_oauth_zero_cost_provider(provider_name: str) -> bool:
    return provider_name in ("anthropic_oauth", "grok_oauth")
