"""Unit tests for shared web layout renderer."""

from project.web.layout import render_layout


def test_render_layout_without_refresh() -> None:
    """Layout should not include refresh meta when seconds <= 0."""
    html = render_layout("Title", "<main>body</main>", auto_refresh_seconds=0, lang="en")
    assert "<meta http-equiv='refresh'" not in html
    assert "<main>body</main>" in html
    assert "<html lang=\"en\">" in html


def test_render_layout_with_refresh_and_escaped_title_lang() -> None:
    """Layout should include refresh meta and escape title/lang attributes."""
    html = render_layout(
        "<unsafe>",
        "<section>ok</section>",
        auto_refresh_seconds=5,
        lang="ru\" onclick=\"x\"",
    )
    assert "<meta http-equiv='refresh' content='5' />" in html
    assert "<title>&lt;unsafe&gt;</title>" in html
    assert "lang=\"ru&quot; onclick=&quot;x&quot;\"" in html
