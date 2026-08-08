"""
Authentication — password hashing and JWT issue/verify.

WHY THESE MATTER
----------------
This is the only security boundary in the application. Every protected
endpoint routes through `get_current_user` -> `verify_access_token`, so a
regression here is an authentication bypass rather than a feature bug.

Four properties are worth pinning down, and each has a well-known failure
mode behind it:

  * Hashes are salted — identical passwords must not produce identical
    hashes, or the database leaks which users share a password.
  * The plaintext never appears in the hash.
  * A token signed with the wrong key, tampered with, or already expired
    must raise the credentials exception rather than validate.
  * `verify_access_token` raises the exception it is GIVEN, so callers
    control the HTTP response — worth locking in, since a bare raise here
    would surface as a 500 instead of a 401.

Expiry is tested by minting a token with a negative lifetime via a patched
constant, so no test has to sleep.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, status

from backend.src.core import oauth2
from backend.src.core.oauth2 import create_access_token, verify_access_token
from backend.src.core.utils import hash_password, verify_password


@pytest.fixture
def credentials_exception() -> HTTPException:
    """The same 401 the real dependency builds and passes in."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


class TestPasswordHashing:
    """Argon2 hashing via passlib."""

    def test_correct_password_verifies(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_wrong_password_is_rejected(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", hashed) is False

    def test_hash_is_not_the_plaintext(self):
        password = "super-secret-value"
        assert password not in hash_password(password)

    def test_hashes_are_salted(self):
        """
        Identical passwords must hash differently. Without a per-hash salt,
        the users table reveals which accounts share a password.
        """
        assert hash_password("same-password") != hash_password("same-password")

    def test_both_salted_hashes_still_verify(self):
        """Salting must not break verification — the other half of the property."""
        password = "same-password"
        for _ in range(2):
            assert verify_password(password, hash_password(password)) is True

    def test_verification_is_case_sensitive(self):
        hashed = hash_password("CaseSensitive")
        assert verify_password("casesensitive", hashed) is False

    def test_uses_argon2(self):
        """Argon2 hashes carry an identifying prefix."""
        assert hash_password("anything").startswith("$argon2")


class TestAccessTokens:
    """JWT creation and verification."""

    def test_round_trip_preserves_the_user_id(self):
        token = create_access_token({"user_id": 42})
        assert verify_access_token(token, HTTPException(status_code=401)).user_id == "42"

    def test_token_carries_an_expiry_claim(self):
        payload = jwt.decode(
            create_access_token({"user_id": 1}),
            oauth2.SECRET_KEY,
            algorithms=[oauth2.ALGORITHM],
        )
        assert "exp" in payload
        assert payload["user_id"] == 1

    def test_original_payload_is_not_mutated(self):
        """
        `create_access_token` copies before adding `exp`. If it stopped doing
        so, the caller's dict would silently gain an expiry key.
        """
        data = {"user_id": 7}
        create_access_token(data)
        assert data == {"user_id": 7}

    def test_garbage_token_is_rejected(self, credentials_exception):
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token("not-a-real-token", credentials_exception)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_signed_with_another_key_is_rejected(self, credentials_exception):
        """The core forgery case: valid structure, wrong signature."""
        forged = jwt.encode(
            {
                "user_id": 1,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            },
            "an-attackers-secret-key",
            algorithm=oauth2.ALGORITHM,
        )
        with pytest.raises(HTTPException):
            verify_access_token(forged, credentials_exception)

    def test_tampered_token_is_rejected(self, credentials_exception):
        """Flipping payload characters must invalidate the signature."""
        token = create_access_token({"user_id": 1})
        header, payload, signature = token.split(".")
        tampered = f"{header}.{payload[:-4]}XXXX.{signature}"
        with pytest.raises(HTTPException):
            verify_access_token(tampered, credentials_exception)

    def test_expired_token_is_rejected(self, monkeypatch, credentials_exception):
        """
        Minted with a negative lifetime so the test is instant and has no
        sleep or flakiness.
        """
        monkeypatch.setattr(oauth2, "ACCESS_TOKEN_EXPIRE_MINUTES", -10)
        expired = create_access_token({"user_id": 1})
        with pytest.raises(HTTPException):
            verify_access_token(expired, credentials_exception)

    def test_raises_the_exception_it_was_given(self):
        """
        The caller supplies the exception, so the HTTP response stays under
        the router's control rather than becoming a generic 500.
        """
        sentinel = HTTPException(status_code=418, detail="teapot")
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token("bad-token", sentinel)
        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == "teapot"

    def test_empty_token_is_rejected(self, credentials_exception):
        with pytest.raises(HTTPException):
            verify_access_token("", credentials_exception)