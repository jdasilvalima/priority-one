"""The shared password and the session cookie."""

from app.auth import LIFETIME, is_valid, new_token, password_matches

SECRET = "a-long-random-secret"
NOW = 1_800_000_000


def test_fresh_token_is_valid():
    assert is_valid(new_token(SECRET, NOW), SECRET, NOW)


def test_token_is_valid_until_it_expires():
    token = new_token(SECRET, NOW)
    assert is_valid(token, SECRET, NOW + LIFETIME - 1)
    assert not is_valid(token, SECRET, NOW + LIFETIME)


def test_token_signed_with_another_secret_is_refused():
    assert not is_valid(new_token("another-secret", NOW), SECRET, NOW)


def test_expiry_cannot_be_extended_by_hand():
    expires, signature = new_token(SECRET, NOW).split(".")
    assert not is_valid(f"{int(expires) + 3600}.{signature}", SECRET, NOW)


def test_rubbish_tokens_are_refused():
    for token in ("", ".", "abc", "abc.def", "123", "é.é"):
        assert not is_valid(token, SECRET, NOW)


def test_password_must_match_exactly():
    assert password_matches("open sesame", "open sesame")
    assert not password_matches("open sesame ", "open sesame")
    assert not password_matches("é", "open sesame")
