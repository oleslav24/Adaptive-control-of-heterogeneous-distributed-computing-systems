"""Unit tests for web i18n catalogs and helper functions."""

from project.web.i18n import (
    ALGORITHM_LABELS,
    chart_line_note,
    catalog_label,
    default_select_label,
    normalize_lang,
    tr,
)


def test_normalize_lang_uses_supported_value() -> None:
    """Known languages are normalized, unsupported values fallback to English."""
    assert normalize_lang("RU") == "ru"
    assert normalize_lang("en") == "en"
    assert normalize_lang("de") == "en"
    assert normalize_lang("") == "en"


def test_tr_fallback_chain() -> None:
    """`tr` resolves by language, then English, then original key."""
    assert tr("ru", "mode") == "Режим"
    assert tr("xx", "mode") == "Mode"
    assert tr("xx", "unknown_key") == "unknown_key"


def test_catalog_label_fallback_chain() -> None:
    """`catalog_label` returns localized label and falls back safely."""
    assert catalog_label(ALGORITHM_LABELS, "ru", "greedy", "greedy") == "Жадный"
    assert catalog_label(ALGORITHM_LABELS, "xx", "greedy", "greedy") == "Greedy"
    assert catalog_label(ALGORITHM_LABELS, "ru", "missing", "missing") == "missing"


def test_chart_helpers() -> None:
    """Chart helper labels are localized and stable."""
    assert default_select_label("ru") == "(по умолчанию)"
    assert default_select_label("en") == "(default)"
    assert "Цвет линии" in chart_line_note("ru", "latency")
    assert "Line color" in chart_line_note("en", "latency")
