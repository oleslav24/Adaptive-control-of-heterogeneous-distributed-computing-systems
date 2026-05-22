"""Unit tests for web i18n catalogs and helper functions."""

from project.web.i18n import (
    ALGORITHM_LABELS,
    MODE_LABELS,
    MODE_OPTIONS,
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
    assert tr("xx", "mode") == "Mode"
    assert tr("xx", "unknown_key") == "unknown_key"
    # Russian catalog should provide localized mode label.
    assert tr("ru", "mode") != "mode"


def test_catalog_label_fallback_chain() -> None:
    """`catalog_label` returns localized label and falls back safely."""
    assert catalog_label(ALGORITHM_LABELS, "xx", "greedy", "greedy") == "Greedy"
    assert catalog_label(ALGORITHM_LABELS, "en", "max-min", "max-min") == "Max-Min"
    assert catalog_label(ALGORITHM_LABELS, "en", "carbon-aware", "carbon-aware") == "Carbon-aware"
    assert catalog_label(ALGORITHM_LABELS, "ru", "missing", "missing") == "missing"


def test_chart_helpers() -> None:
    """Chart helper labels are localized and stable."""
    assert default_select_label("en") == "(default)"
    assert "Line color" in chart_line_note("en", "latency")
    assert chart_line_note("ru", "latency")


def test_mode_catalog_contains_chapter10() -> None:
    """Chapter10 run mode should be present in options and labels."""
    assert "chapter10" in MODE_OPTIONS
    assert MODE_LABELS["en"]["chapter10"] == "Chapter 10"
    assert "paper-bundle" in MODE_OPTIONS
    assert MODE_LABELS["en"]["paper-bundle"] == "Paper Bundle"
    assert "carbon-study" in MODE_OPTIONS
    assert MODE_LABELS["en"]["carbon-study"] == "Carbon Study"
