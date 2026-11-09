"""One shared password and a signed session cookie. Single sign-on replaces this in production."""

import hashlib
import hmac

LIFETIME = 8 * 3600


def _signature(expires: int, secret: str) -> str:
    return hmac.new(secret.encode(), str(expires).encode(), hashlib.sha256).hexdigest()


def new_token(secret: str, now: float) -> str:
    expires = int(now) + LIFETIME
    return f"{expires}.{_signature(expires, secret)}"


def is_valid(token: str, secret: str, now: float) -> bool:
    expires, _, signature = token.partition(".")
    if not (expires.isascii() and expires.isdigit()):
        return False
    matches = hmac.compare_digest(signature.encode(), _signature(int(expires), secret).encode())
    return matches and int(expires) > now


def password_matches(given: str, expected: str) -> bool:
    return hmac.compare_digest(given.encode(), expected.encode())
