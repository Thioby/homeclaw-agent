"""Tests for anthropic_oauth.pkce."""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import FrozenInstanceError

import pytest

from custom_components.homeclaw.providers.anthropic_oauth.pkce import (
    PKCEPair,
    generate_pkce,
)


class TestPKCEPair:
    def test_default_method_is_s256(self):
        pair = PKCEPair(verifier="v", challenge="c")
        assert pair.method == "S256"

    def test_pair_is_frozen(self):
        pair = PKCEPair(verifier="v", challenge="c")
        with pytest.raises(FrozenInstanceError):
            pair.verifier = "x"  # type: ignore[misc]


class TestGeneratePKCE:
    def test_returns_pkce_pair(self):
        pair = generate_pkce()
        assert isinstance(pair, PKCEPair)

    def test_method_is_s256(self):
        pair = generate_pkce()
        assert pair.method == "S256"

    def test_verifier_is_url_safe_no_padding(self):
        pair = generate_pkce()
        assert re.fullmatch(r"[A-Za-z0-9_-]+", pair.verifier)
        assert "=" not in pair.verifier

    def test_verifier_length_is_86_chars(self):
        pair = generate_pkce()
        assert len(pair.verifier) == 86

    def test_challenge_is_sha256_of_verifier(self):
        pair = generate_pkce()
        digest = hashlib.sha256(pair.verifier.encode()).digest()
        expected = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        assert pair.challenge == expected

    def test_two_calls_produce_different_verifiers(self):
        a = generate_pkce()
        b = generate_pkce()
        assert a.verifier != b.verifier
