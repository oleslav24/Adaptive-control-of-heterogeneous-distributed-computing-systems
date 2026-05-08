"""Unit tests for web routing helper module."""

from urllib.parse import urlparse

from project.web.routing import (
    first,
    lang_from_form,
    lang_from_parsed,
    language_switcher,
    with_lang,
)


def test_first_returns_default_and_first_item() -> None:
    """`first` returns first value or fallback when key is missing/empty."""
    assert first({}, "x", "fallback") == "fallback"
    assert first({"x": []}, "x", "fallback") == "fallback"
    assert first({"x": ["a", "b"]}, "x", "fallback") == "a"


def test_lang_extractors_normalize_with_fallback() -> None:
    """Language extractors support RU/EN and fallback to EN for unknown values."""
    assert lang_from_parsed(urlparse("/?lang=ru")) == "ru"
    assert lang_from_parsed(urlparse("/?lang=de")) == "en"
    assert lang_from_form({"lang": ["RU"]}) == "ru"
    assert lang_from_form({"lang": ["unknown"]}) == "en"


def test_with_lang_builds_urls() -> None:
    """URL builder injects lang and skips empty params."""
    assert with_lang("/", "ru") == "/?lang=ru"
    assert with_lang("/job", "en", id="abc", empty="") == "/job?lang=en&id=abc"
    assert with_lang("/health", "en", include_lang=False) == "/health"


def test_language_switcher_marks_active_lang() -> None:
    """Switcher renders RU/EN links and highlights active language."""
    html = language_switcher("ru", "/job", id="abc")
    assert "RUS" in html
    assert "ENG" in html
    assert "class='lang-link active'" in html
    assert "href='/job?lang=ru&amp;id=abc'" in html
