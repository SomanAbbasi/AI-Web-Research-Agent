import pytest

from ai_web_research_agent.services.url_normalizer import normalize_url


def test_normalize_removes_fragment():
    assert (
        normalize_url(
            "https://example.com/products#details"
        )
        == "https://example.com/products"
    )


def test_normalize_root_url():
    assert (
        normalize_url("https://example.com")
        == "https://example.com/"
    )


def test_normalize_removes_trailing_slash():
    assert (
        normalize_url(
            "https://example.com/products/"
        )
        == "https://example.com/products"
    )


def test_normalize_lowercases_hostname():
    assert (
        normalize_url(
            "https://EXAMPLE.COM/products"
        )
        == "https://example.com/products"
    )


def test_invalid_scheme():
    with pytest.raises(ValueError):
        normalize_url(
            "ftp://example.com/file.txt"
        )


def test_invalid_url():
    with pytest.raises(ValueError):
        normalize_url("not-a-url")