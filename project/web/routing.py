"""HTTP/query helpers for web UI routing and language links."""

from __future__ import annotations

from html import escape
from typing import Mapping
from urllib.parse import parse_qs, urlencode

from project.web.i18n import normalize_lang


def first(mapping: Mapping[str, list[str]], key: str, default: str = "") -> str:
    """Read first value from parsed query/form mapping."""
    values = mapping.get(key, [])
    if not values:
        return default
    return values[0]


def lang_from_parsed(parsed) -> str:
    """Extract language from parsed URL query."""
    query = parse_qs(parsed.query)
    return normalize_lang(first(query, "lang", "en"), default="en")


def lang_from_form(form: Mapping[str, list[str]]) -> str:
    """Extract language from submitted form payload."""
    return normalize_lang(first(form, "lang", "en"), default="en")


def with_lang(route: str, lang: str, include_lang: bool = True, **params: str) -> str:
    """Build URL with language and optional query params."""
    payload: dict[str, str] = {}
    if include_lang:
        payload["lang"] = lang
    for key, value in params.items():
        if value is None:
            continue
        text = str(value)
        if not text:
            continue
        payload[key] = text
    if not payload:
        return route
    return f"{route}?{urlencode(payload)}"


def language_switcher(lang: str, route: str, include_lang: bool = True, **params: str) -> str:
    """Render language toggle links for current page."""
    ru_url = with_lang(route, "ru", include_lang=include_lang, **params)
    en_url = with_lang(route, "en", include_lang=include_lang, **params)
    ru_class = "lang-link active" if lang == "ru" else "lang-link"
    en_class = "lang-link active" if lang == "en" else "lang-link"
    return (
        "<nav class='lang-switch'>"
        f"<a class='{ru_class}' href='{escape(ru_url)}'>RUS</a>"
        f"<a class='{en_class}' href='{escape(en_url)}'>ENG</a>"
        "</nav>"
    )

