"""Shared HTML layout renderer for the web UI pages."""

from __future__ import annotations

from html import escape


def render_layout(title: str, body: str, auto_refresh_seconds: int = 0, lang: str = "en") -> str:
    """Render full HTML layout around page body content."""
    refresh = (
        f"<meta http-equiv='refresh' content='{auto_refresh_seconds}' />"
        if auto_refresh_seconds > 0
        else ""
    )
    return f"""<!doctype html>
<html lang="{escape(lang)}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  {refresh}
  <style>
    :root {{
      --bg: #f4f7fb;
      --card: #ffffff;
      --line: #d9e2ec;
      --text: #102a43;
      --muted: #486581;
      --accent: #1565c0;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, Arial, sans-serif;
      background: linear-gradient(180deg, #eef4ff 0%, var(--bg) 100%);
      color: var(--text);
    }}
    h1, h2 {{ margin-top: 0; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 16px;
      align-items: start;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
      margin: 14px;
      box-shadow: 0 4px 12px rgba(16, 42, 67, 0.05);
    }}
    form label {{
      display: block;
      margin-top: 10px;
      margin-bottom: 4px;
      font-weight: 600;
      color: var(--muted);
    }}
    input, select, button {{
      width: 100%;
      box-sizing: border-box;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--line);
      font-size: 14px;
    }}
    button {{
      margin-top: 12px;
      cursor: pointer;
      border: none;
      color: #fff;
      background: #0b7285;
      font-weight: 700;
    }}
    button:hover {{ background: #095c6b; }}
    .checks {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .checks label {{
      margin: 0;
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
    }}
    .checks input {{
      width: auto;
      margin: 0;
    }}
    .choice-flags {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 10px;
      margin-top: 6px;
      margin-bottom: 6px;
      padding: 8px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }}
    .choice-flags label {{
      margin: 0;
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
      color: #334e68;
    }}
    .choice-flags input {{
      width: auto;
      margin: 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #f0f4f8;
      color: #243b53;
    }}
    .badge {{
      display: inline-block;
      color: #fff;
      border-radius: 999px;
      padding: 2px 10px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .log {{
      background: #0f172a;
      color: #d1e3ff;
      border-radius: 10px;
      padding: 12px;
      max-height: 65vh;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
    }}
    .preview {{
      max-width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .hint {{
      color: var(--muted);
      font-size: 12px;
    }}
    .is-hidden {{
      display: none !important;
    }}
    .run-estimator {{
      margin-top: 12px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f8fafc;
    }}
    .run-estimator-title {{
      margin: 0 0 4px 0;
      font-size: 13px;
      font-weight: 700;
      color: #243b53;
    }}
    .run-estimator .hint {{
      margin: 2px 0;
    }}
    .insights-list {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.5;
      color: var(--text);
    }}
    .insights-list li {{
      margin: 8px 0;
    }}
    .control-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      align-items: end;
      margin: 8px 0 10px 0;
    }}
    .control-row label {{
      display: inline-flex;
      flex-direction: column;
      gap: 4px;
      min-width: 150px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    .control-row input,
    .control-row select {{
      width: auto;
      min-width: 130px;
    }}
    .control-row input[type="checkbox"] {{
      width: auto;
      min-width: 0;
    }}
    .control-row .check-inline {{
      flex-direction: row;
      align-items: center;
      min-width: 190px;
      padding-bottom: 8px;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0;
      align-items: stretch;
    }}
    .chart-canvas {{
      width: 100%;
      min-height: 240px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #ffffff;
      display: block;
    }}
    .chart-note {{
      margin: 8px 0 0 0;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.4;
    }}
    .run-legend {{
      margin-top: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px 10px;
    }}
    .run-legend-item {{
      display: inline-flex;
      align-items: center;
      font-size: 12px;
      color: #334e68;
    }}
    .run-legend-swatch {{
      width: 14px;
      height: 10px;
      border-radius: 2px;
      margin-right: 6px;
      display: inline-block;
    }}
    .topbar {{
      display: flex;
      justify-content: flex-end;
      margin: 10px 14px 0 14px;
    }}
    .lang-switch {{
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 999px;
      overflow: hidden;
      background: #fff;
    }}
    .lang-link {{
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      color: #334e68;
      text-decoration: none;
      border-right: 1px solid var(--line);
    }}
    .lang-link:last-child {{
      border-right: none;
    }}
    .lang-link.active {{
      background: #1565c0;
      color: #ffffff;
    }}
    @media (max-width: 1024px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
      .checks {{
        grid-template-columns: 1fr;
      }}
      .choice-flags {{
        grid-template-columns: 1fr;
      }}
      .chart-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""

