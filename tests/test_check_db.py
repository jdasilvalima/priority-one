"""The connection check reads .env and must never print the password."""

from scripts.check_db import env_value, masked

URL = "postgresql://week_reader.ref:s3cret@pooler.example.com:6543/postgres"


def test_reads_the_value_after_the_first_equals_sign():
    text = f"# comment\nOTHER=1\nDATABASE_URL_READONLY={URL}?a=b\n"
    assert env_value(text, "DATABASE_URL_READONLY") == f"{URL}?a=b"


def test_empty_or_missing_value_gives_nothing():
    assert env_value("DATABASE_URL_READONLY=\n", "DATABASE_URL_READONLY") == ""
    assert env_value("OTHER=1\n", "DATABASE_URL_READONLY") == ""


def test_commented_line_is_ignored():
    assert env_value(f"# DATABASE_URL_READONLY={URL}\n", "DATABASE_URL_READONLY") == ""


def test_error_text_never_shows_the_password():
    text = masked(f"connection failed for {URL}", URL)
    assert "s3cret" not in text
    assert "pooler.example.com" in text


def test_password_the_driver_cannot_parse_is_still_hidden():
    url = "postgresql://week_reader.ref:a%!b$c&d@pooler.example.com:6543/postgres"
    text = masked('invalid percent-encoded token: "a%!b$c&d"', url)
    assert "a%!b" not in text
    assert "invalid percent-encoded token" in text


def test_percent_encoded_password_is_hidden_in_both_forms():
    url = "postgresql://week_reader.ref:p%3Dword@pooler.example.com:6543/postgres"
    assert masked("failed: p%3Dword and p=word", url) == "failed: *** and ***"


def test_password_containing_an_at_sign_is_hidden():
    url = "postgresql://week_reader.ref:pa@ss@pooler.example.com:6543/postgres"
    assert masked("failed: pa@ss", url) == "failed: ***"
