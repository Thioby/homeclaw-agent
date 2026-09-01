from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import aiohttp

from .constants import (
    ACCESS_TOKEN_SKEW_S,
    CLIENT_ID,
    DEVICE_CODE_DEFAULT_EXPIRES_S,
    DEVICE_CODE_DEFAULT_INTERVAL_S,
    DEVICE_CODE_GRANT_TYPE,
    DEVICE_CODE_MIN_INTERVAL_S,
    DEVICE_CODE_POLL_MARGIN_S,
    DEVICE_CODE_SLOW_DOWN_S,
    DEVICE_CODE_URL,
    OAUTH_SCOPES,
    REFERRER,
    REFRESH_BASE_DELAY_S,
    REFRESH_MAX_RETRIES,
    TOKEN_URL,
)

_TOKEN_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
}

_NETWORK_ERRORS = (
    aiohttp.ClientConnectionError,
    aiohttp.ServerDisconnectedError,
    aiohttp.ClientPayloadError,
    asyncio.TimeoutError,
)


class OAuthRefreshError(Exception):
    def __init__(
        self,
        message: str,
        *,
        is_permanent: bool = False,
        is_entitlement: bool = False,
    ) -> None:
        super().__init__(message)
        self.is_permanent = is_permanent
        self.is_entitlement = is_entitlement


@dataclass(frozen=True, slots=True)
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: float
    interval: float


@dataclass(frozen=True, slots=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float


def _positive_seconds(value: Any, default: float) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return default
    if not seconds or seconds <= 0:
        return default
    return seconds


def _exp_from_jwt(token: str) -> float | None:
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    payload += "=" * ((4 - len(payload) % 4) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    exp = claims.get("exp")
    if isinstance(exp, (int, float)):
        return float(exp)
    return None


def _token_set_from_payload(data: dict[str, Any], fallback_refresh: str) -> TokenSet:
    access = data.get("access_token") or ""
    refresh = data.get("refresh_token") or fallback_refresh
    if not access or not refresh:
        raise OAuthRefreshError("Token response missing access_token or refresh_token", is_permanent=True)
    expires_in = data.get("expires_in")
    if expires_in:
        expires_at = time.time() + _positive_seconds(expires_in, 3600.0)
    else:
        expires_at = _exp_from_jwt(access) or (time.time() + 3600.0)
    return TokenSet(access_token=access, refresh_token=refresh, expires_at=expires_at)


async def _read_json(resp: aiohttp.ClientResponse) -> dict[str, Any]:
    try:
        data = await resp.json(content_type=None)
    except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


async def request_device_code(session: aiohttp.ClientSession) -> DeviceCode:
    payload = {
        "client_id": CLIENT_ID,
        "scope": " ".join(OAUTH_SCOPES),
        "referrer": REFERRER,
    }
    async with session.post(DEVICE_CODE_URL, data=payload, headers=_TOKEN_HEADERS) as resp:
        data = await _read_json(resp)
        if resp.status != 200:
            detail = data.get("error_description") or data.get("error") or str(resp.status)
            raise OAuthRefreshError(
                f"Device code request failed: {resp.status} — {str(detail)[:300]}",
                is_permanent=True,
            )
    device_code = data.get("device_code") or ""
    user_code = data.get("user_code") or ""
    verification_uri = data.get("verification_uri") or ""
    if not device_code or not user_code or not verification_uri:
        raise OAuthRefreshError(
            "Device code response missing device_code / user_code / verification_uri",
            is_permanent=True,
        )
    complete = data.get("verification_uri_complete") or verification_uri
    return DeviceCode(
        device_code=device_code,
        user_code=user_code,
        verification_uri=verification_uri,
        verification_uri_complete=complete,
        expires_in=_positive_seconds(data.get("expires_in"), DEVICE_CODE_DEFAULT_EXPIRES_S),
        interval=max(
            _positive_seconds(data.get("interval"), DEVICE_CODE_DEFAULT_INTERVAL_S),
            DEVICE_CODE_MIN_INTERVAL_S,
        ),
    )


async def poll_device_code_token(
    session: aiohttp.ClientSession,
    device: DeviceCode,
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    now: Callable[[], float] = time.time,
) -> TokenSet:
    deadline = now() + device.expires_in
    interval = device.interval
    while now() < deadline:
        async with session.post(
            TOKEN_URL,
            data={
                "grant_type": DEVICE_CODE_GRANT_TYPE,
                "client_id": CLIENT_ID,
                "device_code": device.device_code,
            },
            headers=_TOKEN_HEADERS,
        ) as resp:
            data = await _read_json(resp)
            if resp.status == 200:
                return _token_set_from_payload(data, "")
            error = str(data.get("error") or "")
            remaining = max(0.0, deadline - now())
            if error == "authorization_pending":
                await sleep(min(interval + DEVICE_CODE_POLL_MARGIN_S, remaining or interval))
                continue
            if error == "slow_down":
                interval += DEVICE_CODE_SLOW_DOWN_S
                await sleep(min(interval + DEVICE_CODE_POLL_MARGIN_S, remaining or interval))
                continue
            if error in ("access_denied", "authorization_denied"):
                raise OAuthRefreshError("Grok device authorization was denied", is_permanent=True)
            if error == "expired_token":
                raise OAuthRefreshError("Grok device code expired", is_permanent=True)
            detail = data.get("error_description") or error or f"HTTP {resp.status}"
            raise OAuthRefreshError(
                f"Device token exchange failed: {resp.status} — {str(detail)[:300]}",
                is_permanent=True,
            )
    raise OAuthRefreshError("Grok device authorization timed out", is_permanent=True)


async def _do_refresh(session: aiohttp.ClientSession, refresh_token_value: str) -> TokenSet:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
        "client_id": CLIENT_ID,
    }
    async with session.post(TOKEN_URL, data=payload, headers=_TOKEN_HEADERS) as resp:
        data = await _read_json(resp)
        if resp.status >= 500:
            raise aiohttp.ServerDisconnectedError(f"5xx: {resp.status}")
        if resp.status in (402, 403):
            detail = data.get("error_description") or data.get("error") or f"HTTP {resp.status}"
            raise OAuthRefreshError(
                f"Grok subscription is not entitled to Grok Build: {detail}",
                is_permanent=True,
                is_entitlement=True,
            )
        if resp.status != 200:
            body = json.dumps(data) if data else ""
            is_permanent = resp.status in (400, 401) or '"invalid_grant"' in body or data.get("error") == "invalid_grant"
            raise OAuthRefreshError(
                f"Token refresh failed: {resp.status} — {body[:300]}",
                is_permanent=is_permanent,
            )
        return _token_set_from_payload(data, refresh_token_value)


async def refresh_with_retry(
    session: aiohttp.ClientSession,
    read_refresh_token: Callable[[], Awaitable[str]],
) -> TokenSet:
    last_error: Exception | None = None
    for attempt in range(REFRESH_MAX_RETRIES + 1):
        if attempt > 0:
            await asyncio.sleep(REFRESH_BASE_DELAY_S * (2 ** (attempt - 1)))
        current_refresh = await read_refresh_token()
        if not current_refresh:
            raise OAuthRefreshError("No refresh token available", is_permanent=True)
        try:
            return await _do_refresh(session, current_refresh)
        except _NETWORK_ERRORS as err:
            last_error = err
            continue
        except OAuthRefreshError as err:
            if err.is_permanent:
                raise
            last_error = err
            continue
    raise OAuthRefreshError(
        f"Token refresh exhausted {REFRESH_MAX_RETRIES} retries: {last_error}",
        is_permanent=False,
    )


def access_token_is_fresh(access_token: str, expires_at: float, *, now: Callable[[], float] | None = None) -> bool:
    clock = now or time.time
    if access_token and expires_at and clock() < expires_at - ACCESS_TOKEN_SKEW_S:
        return True
    jwt_exp = _exp_from_jwt(access_token) if access_token else None
    if jwt_exp is not None:
        return clock() < jwt_exp - ACCESS_TOKEN_SKEW_S
    return False


class InflightRefreshGate:
    def __init__(self) -> None:
        self._task: asyncio.Task[TokenSet] | None = None
        self._lock = asyncio.Lock()

    async def refresh(
        self,
        session: aiohttp.ClientSession,
        read_refresh_token: Callable[[], Awaitable[str]],
    ) -> TokenSet:
        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(refresh_with_retry(session, read_refresh_token))
        try:
            return await self._task
        finally:
            async with self._lock:
                if self._task is not None and self._task.done():
                    self._task = None
