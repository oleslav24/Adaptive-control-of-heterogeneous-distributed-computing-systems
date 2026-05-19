"""Localization catalogs and helpers for the web interface."""

from __future__ import annotations

from typing import Mapping


MODE_OPTIONS = (
    "single",
    "compare",
    "batch",
    "publication",
    "paper-bundle",
    "chapter10",
    "ab-intelligence",
    "ab-llm",
    "repro-check",
)
ALGORITHM_OPTIONS = ("", "round-robin", "min-load", "greedy", "carbon-aware")
SCENARIO_OPTIONS = (
    "",
    "static",
    "dynamic-load",
    "peak-load",
    "node-failures",
    "heterogeneous-tasks",
    "mixed",
)
DEFAULT_BATCH_SCENARIOS = (
    "static",
    "dynamic-load",
    "peak-load",
    "node-failures",
    "heterogeneous-tasks",
)
LANG_OPTIONS = ("en", "ru")

MODE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "single": "Single",
        "compare": "Compare",
        "batch": "Batch",
        "publication": "Publication",
        "paper-bundle": "Paper Bundle",
        "chapter10": "Chapter 10",
        "ab-intelligence": "A/B Intelligence",
        "ab-llm": "A/B LLM",
        "repro-check": "Repro Check",
    },
    "ru": {
        "single": "РћРґРёРЅРѕС‡РЅС‹Р№",
        "compare": "РЎСЂР°РІРЅРµРЅРёРµ",
        "batch": "РџР°РєРµС‚РЅС‹Р№",
        "publication": "РџСѓР±Р»РёРєР°С†РёРѕРЅРЅС‹Р№",
        "paper-bundle": "Пакет статьи",
        "chapter10": "Р“Р»Р°РІР° 10",
        "ab-intelligence": "A/B РРЅС‚РµР»Р»РµРєС‚",
        "ab-llm": "A/B LLM",
        "repro-check": "РџСЂРѕРІРµСЂРєР° РІРѕСЃРїСЂРѕРёР·РІРѕРґРёРјРѕСЃС‚Рё",
    },
}

ALGORITHM_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "round-robin": "Round-robin",
        "min-load": "Min-load",
        "greedy": "Greedy",
        "carbon-aware": "Carbon-aware",
    },
    "ru": {
        "round-robin": "РљСЂСѓРіРѕРІРѕР№ (Round-robin)",
        "min-load": "РњРёРЅРёРјР°Р»СЊРЅР°СЏ РЅР°РіСЂСѓР·РєР°",
        "greedy": "Р–Р°РґРЅС‹Р№",
        "carbon-aware": "Углеродно-осознанный",
    },
}

SCENARIO_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "static": "Static",
        "dynamic-load": "Dynamic Load",
        "peak-load": "Peak Load",
        "node-failures": "Node Failures",
        "heterogeneous-tasks": "Heterogeneous Tasks",
        "mixed": "Mixed",
    },
    "ru": {
        "static": "РЎС‚Р°С‚РёС‡РµСЃРєРёР№",
        "dynamic-load": "Р”РёРЅР°РјРёС‡РµСЃРєР°СЏ РЅР°РіСЂСѓР·РєР°",
        "peak-load": "РџРёРєРѕРІР°СЏ РЅР°РіСЂСѓР·РєР°",
        "node-failures": "РћС‚РєР°Р·С‹ СѓР·Р»РѕРІ",
        "heterogeneous-tasks": "Р“РµС‚РµСЂРѕРіРµРЅРЅС‹Рµ Р·Р°РґР°С‡Рё",
        "mixed": "РЎРјРµС€Р°РЅРЅС‹Р№",
    },
}

UI_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "console_title": "Experimental Testbed Web Console",
        "workspace": "Workspace",
        "start_experiment": "Start Experiment",
        "mode": "Mode",
        "config_path": "Config path",
        "algorithm": "Algorithm",
        "scenario": "Scenario",
        "llm_provider": "LLM provider",
        "compare_algorithms": "Compare algorithms",
        "batch_scenarios": "Batch scenarios",
        "batch_algorithms": "Batch algorithms",
        "batch_runs": "Batch runs",
        "repro_runs": "Repro runs",
        "job_timeout_seconds": "Job timeout (sec)",
        "study_seeds": "Study seeds",
        "paper_bundle_name": "Paper bundle name",
        "output_dir_override": "Output dir override",
        "log_level": "Log level",
        "disable_intelligence": "disable intelligence",
        "disable_llm": "disable llm",
        "no_plots": "no plots",
        "no_csv": "no csv",
        "batch_save_runs": "batch save runs",
        "batch_keep_adaptive": "batch keep adaptive",
        "study_quick": "publication quick",
        "run": "Run",
        "expected_runs_title": "Expected runs",
        "expected_runs_formula": "Formula",
        "expected_runs_fallback": "Fallback defaults are used for empty selections.",
        "unknown": "unknown",
        "mode_mapping": "Mode mapping",
        "quick_links": "Quick Links",
        "browse_outputs": "Browse outputs",
        "browse_docs": "Browse docs",
        "open_config": "Open config.yaml",
        "health_check": "Health check",
        "running_jobs": "Running Jobs",
        "recent_jobs": "Recent Jobs",
        "no_active_jobs": "No active jobs.",
        "no_runs_started": "No runs started yet.",
        "id": "id",
        "status": "status",
        "started": "started",
        "finished": "finished",
        "rc": "rc",
        "command": "command",
        "actions": "actions",
        "open": "open",
        "job": "Job",
        "back_dashboard": "Back to dashboard",
        "return_code": "Return code",
        "status_details": "Status details",
        "stop_job": "Stop job",
        "latency_avg": "Latency (avg)",
        "throughput": "Throughput",
        "average_load": "Average Load",
        "queue_completed": "Queue / Completed",
        "log": "Log",
        "no_data_yet": "No data yet",
        "queue": "Queue",
        "completed": "Completed",
        "browse": "Browse",
        "download_as_is": "Download as-is",
        "parent": ".. parent",
        "type": "type",
        "name": "name",
        "size_bytes": "size (bytes)",
        "empty": "(empty)",
        "dir": "dir",
        "file": "file",
        "file_page": "File",
        "back_folder": "Back to folder",
        "download": "Download",
        "preview": "Preview",
        "path_not_exist": "Path does not exist.",
        "file_not_found": "File not found.",
        "job_not_found": "Job not found.",
        "invalid_request": "Invalid request",
        "diagnostics_bundle": "Diagnostics bundle",
        "diagnostics_bundle_unavailable": "Diagnostics bundle is available only for failed, timeout, or stopped jobs.",
        "not_found": "Not found.",
        "no_inline_preview": "No inline preview for this file type. Use download.",
    },
    "ru": {
        "console_title": "Р’РµР±-РєРѕРЅСЃРѕР»СЊ СЌРєСЃРїРµСЂРёРјРµРЅС‚Р°Р»СЊРЅРѕРіРѕ СЃС‚РµРЅРґР°",
        "workspace": "Р Р°Р±РѕС‡Р°СЏ РґРёСЂРµРєС‚РѕСЂРёСЏ",
        "start_experiment": "Р—Р°РїСѓСЃРє СЌРєСЃРїРµСЂРёРјРµРЅС‚Р°",
        "mode": "Р РµР¶РёРј",
        "config_path": "РџСѓС‚СЊ Рє РєРѕРЅС„РёРіСѓ",
        "algorithm": "РђР»РіРѕСЂРёС‚Рј",
        "scenario": "РЎС†РµРЅР°СЂРёР№",
        "llm_provider": "РџСЂРѕРІР°Р№РґРµСЂ LLM",
        "compare_algorithms": "РђР»РіРѕСЂРёС‚РјС‹ СЃСЂР°РІРЅРµРЅРёСЏ",
        "batch_scenarios": "РЎС†РµРЅР°СЂРёРё batch",
        "batch_algorithms": "РђР»РіРѕСЂРёС‚РјС‹ batch",
        "batch_runs": "РљРѕР»РёС‡РµСЃС‚РІРѕ batch-РїСЂРѕРіРѕРЅРѕРІ",
        "repro_runs": "РљРѕР»РёС‡РµСЃС‚РІРѕ repro-РїСЂРѕРіРѕРЅРѕРІ",
        "study_seeds": "Seeds РёСЃСЃР»РµРґРѕРІР°РЅРёСЏ",
        "paper_bundle_name": "РРјСЏ paper bundle",
        "output_dir_override": "РџРµСЂРµРѕРїСЂРµРґРµР»РёС‚СЊ output dir",
        "log_level": "РЈСЂРѕРІРµРЅСЊ Р»РѕРіРёСЂРѕРІР°РЅРёСЏ",
        "disable_intelligence": "РѕС‚РєР»СЋС‡РёС‚СЊ РёРЅС‚РµР»Р»РµРєС‚",
        "disable_llm": "РѕС‚РєР»СЋС‡РёС‚СЊ llm",
        "no_plots": "Р±РµР· РіСЂР°С„РёРєРѕРІ",
        "no_csv": "Р±РµР· csv",
        "batch_save_runs": "СЃРѕС…СЂР°РЅСЏС‚СЊ batch-РїСЂРѕРіРѕРЅС‹",
        "batch_keep_adaptive": "РѕСЃС‚Р°РІРёС‚СЊ adaptive РІ batch",
        "study_quick": "Р±С‹СЃС‚СЂС‹Р№ publication",
        "run": "Р—Р°РїСѓСЃС‚РёС‚СЊ",
        "expected_runs_title": "РћР¶РёРґР°РµРјРѕРµ С‡РёСЃР»Рѕ РїСЂРѕРіРѕРЅРѕРІ",
        "expected_runs_formula": "Р¤РѕСЂРјСѓР»Р°",
        "expected_runs_fallback": "Р”Р»СЏ РїСѓСЃС‚С‹С… РІС‹Р±РѕСЂРѕРІ РёСЃРїРѕР»СЊР·СѓСЋС‚СЃСЏ Р·РЅР°С‡РµРЅРёСЏ РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ.",
        "unknown": "РЅРµРёР·РІРµСЃС‚РЅРѕ",
        "mode_mapping": "РЎРѕРїРѕСЃС‚Р°РІР»РµРЅРёРµ СЂРµР¶РёРјРѕРІ",
        "quick_links": "Р‘С‹СЃС‚СЂС‹Рµ СЃСЃС‹Р»РєРё",
        "browse_outputs": "РћС‚РєСЂС‹С‚СЊ outputs",
        "browse_docs": "РћС‚РєСЂС‹С‚СЊ docs",
        "open_config": "РћС‚РєСЂС‹С‚СЊ config.yaml",
        "health_check": "РџСЂРѕРІРµСЂРєР° health",
        "running_jobs": "РђРєС‚РёРІРЅС‹Рµ Р·Р°РґР°С‡Рё",
        "recent_jobs": "РџРѕСЃР»РµРґРЅРёРµ Р·Р°РґР°С‡Рё",
        "no_active_jobs": "РђРєС‚РёРІРЅС‹С… Р·Р°РґР°С‡ РЅРµС‚.",
        "no_runs_started": "Р—Р°РїСѓСЃРєРё РїРѕРєР° РЅРµ РІС‹РїРѕР»РЅСЏР»РёСЃСЊ.",
        "id": "id",
        "status": "СЃС‚Р°С‚СѓСЃ",
        "started": "СЃС‚Р°СЂС‚",
        "finished": "С„РёРЅРёС€",
        "rc": "РєРѕРґ",
        "command": "РєРѕРјР°РЅРґР°",
        "actions": "РґРµР№СЃС‚РІРёСЏ",
        "open": "РѕС‚РєСЂС‹С‚СЊ",
        "job": "Р—Р°РґР°С‡Р°",
        "back_dashboard": "РќР°Р·Р°Рґ РЅР° РґР°С€Р±РѕСЂРґ",
        "return_code": "РљРѕРґ РІРѕР·РІСЂР°С‚Р°",
        "stop_job": "РћСЃС‚Р°РЅРѕРІРёС‚СЊ Р·Р°РґР°С‡Сѓ",
        "latency_avg": "Latency (СЃСЂРµРґРЅСЏСЏ)",
        "throughput": "РџСЂРѕРїСѓСЃРєРЅР°СЏ СЃРїРѕСЃРѕР±РЅРѕСЃС‚СЊ",
        "average_load": "РЎСЂРµРґРЅСЏСЏ Р·Р°РіСЂСѓР·РєР°",
        "queue_completed": "РћС‡РµСЂРµРґСЊ / Р’С‹РїРѕР»РЅРµРЅРѕ",
        "log": "Р›РѕРі",
        "no_data_yet": "Р”Р°РЅРЅС‹С… РїРѕРєР° РЅРµС‚",
        "queue": "РћС‡РµСЂРµРґСЊ",
        "completed": "Р’С‹РїРѕР»РЅРµРЅРѕ",
        "browse": "РџСЂРѕСЃРјРѕС‚СЂ",
        "download_as_is": "РЎРєР°С‡Р°С‚СЊ РєР°Рє РµСЃС‚СЊ",
        "parent": ".. СЂРѕРґРёС‚РµР»СЊСЃРєР°СЏ РїР°РїРєР°",
        "type": "С‚РёРї",
        "name": "РёРјСЏ",
        "size_bytes": "СЂР°Р·РјРµСЂ (Р±Р°Р№С‚)",
        "empty": "(РїСѓСЃС‚Рѕ)",
        "dir": "РїР°РїРєР°",
        "file": "С„Р°Р№Р»",
        "file_page": "Р¤Р°Р№Р»",
        "back_folder": "РќР°Р·Р°Рґ Рє РїР°РїРєРµ",
        "download": "РЎРєР°С‡Р°С‚СЊ",
        "preview": "РџСЂРµРґРїСЂРѕСЃРјРѕС‚СЂ",
        "path_not_exist": "РџСѓС‚СЊ РЅРµ СЃСѓС‰РµСЃС‚РІСѓРµС‚.",
        "file_not_found": "Р¤Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ.",
        "job_not_found": "Р—Р°РґР°С‡Р° РЅРµ РЅР°Р№РґРµРЅР°.",
        "not_found": "РќРµ РЅР°Р№РґРµРЅРѕ.",
        "no_inline_preview": "Р”Р»СЏ СЌС‚РѕРіРѕ С‚РёРїР° С„Р°Р№Р»Р° РЅРµС‚ РїСЂРµРґРїСЂРѕСЃРјРѕС‚СЂР°. РСЃРїРѕР»СЊР·СѓР№С‚Рµ СЃРєР°С‡РёРІР°РЅРёРµ.",
    },
}

STATUS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "queued": "queued",
        "running": "running",
        "success": "success",
        "failed": "failed",
        "stopped": "stopped",
        "timeout": "timeout",
    },
    "ru": {
        "queued": "РІ РѕС‡РµСЂРµРґРё",
        "running": "РІС‹РїРѕР»РЅСЏРµС‚СЃСЏ",
        "success": "СѓСЃРїРµС€РЅРѕ",
        "failed": "РѕС€РёР±РєР°",
        "stopped": "РѕСЃС‚Р°РЅРѕРІР»РµРЅРѕ",
    },
}


def normalize_lang(raw: str, *, default: str = "en") -> str:
    """Normalize language code with fallback."""
    lang = str(raw).strip().lower()
    if lang in LANG_OPTIONS:
        return lang
    return default


def tr(lang: str, key: str) -> str:
    """Translate UI key for selected language with fallback to English."""
    table = UI_TEXT.get(lang, UI_TEXT["en"])
    if key in table:
        return table[key]
    return UI_TEXT["en"].get(key, key)


def catalog_label(
    labels: Mapping[str, Mapping[str, str]],
    lang: str,
    value: str,
    fallback: str,
) -> str:
    """Get localized label for select options with English fallback."""
    table = labels.get(lang, labels.get("en", {}))
    if value in table:
        return table[value]
    return labels.get("en", {}).get(value, fallback)


def default_select_label(lang: str) -> str:
    """Localized label for empty select value."""
    if lang == "ru":
        return "(РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ)"
    return "(default)"


def insights_title(lang: str) -> str:
    """Localized title for researcher insights card."""
    if lang == "ru":
        return "Р’С‹РІРѕРґС‹ РёСЃСЃР»РµРґРѕРІР°С‚РµР»СЊСЃРєРѕРіРѕ Р°РіРµРЅС‚Р°"
    return "Researcher Insights"


def insights_placeholder(lang: str) -> str:
    """Localized placeholder for insights list before enough data arrives."""
    if lang == "ru":
        return "РќРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РґР°РЅРЅС‹С… РґР»СЏ РІС‹РІРѕРґРѕРІ."
    return "Not enough data for conclusions yet."


def chart_line_note(lang: str, series: str) -> str:
    """Localized explanatory text for each chart line."""
    notes_ru = {
        "latency": "Р¦РІРµС‚ Р»РёРЅРёРё = РѕС‚РґРµР»СЊРЅС‹Р№ РїСЂРѕРіРѕРЅ (Р»РµРіРµРЅРґР°: СЃС†РµРЅР°СЂРёР№/Р°Р»РіРѕСЂРёС‚Рј); РјРµС‚СЂРёРєР°: СЃСЂРµРґРЅСЏСЏ Р·Р°РґРµСЂР¶РєР° Р·Р°РґР°С‡ (РЅРёР¶Рµ Р»СѓС‡С€Рµ).",
        "throughput": "Р¦РІРµС‚ Р»РёРЅРёРё = РѕС‚РґРµР»СЊРЅС‹Р№ РїСЂРѕРіРѕРЅ (Р»РµРіРµРЅРґР°: СЃС†РµРЅР°СЂРёР№/Р°Р»РіРѕСЂРёС‚Рј); РјРµС‚СЂРёРєР°: РїСЂРѕРїСѓСЃРєРЅР°СЏ СЃРїРѕСЃРѕР±РЅРѕСЃС‚СЊ (РІС‹С€Рµ Р»СѓС‡С€Рµ).",
        "avg_load": "Р¦РІРµС‚ Р»РёРЅРёРё = РѕС‚РґРµР»СЊРЅС‹Р№ РїСЂРѕРіРѕРЅ (Р»РµРіРµРЅРґР°: СЃС†РµРЅР°СЂРёР№/Р°Р»РіРѕСЂРёС‚Рј); РјРµС‚СЂРёРєР°: СЃСЂРµРґРЅСЏСЏ Р·Р°РіСЂСѓР·РєР° СѓР·Р»РѕРІ.",
        "queue": "Р¦РІРµС‚ Р»РёРЅРёРё = РѕС‚РґРµР»СЊРЅС‹Р№ РїСЂРѕРіРѕРЅ (Р»РµРіРµРЅРґР°: СЃС†РµРЅР°СЂРёР№/Р°Р»РіРѕСЂРёС‚Рј); СЃРїР»РѕС€РЅР°СЏ Р»РёРЅРёСЏ = СЂР°Р·РјРµСЂ РѕС‡РµСЂРµРґРё.",
        "completed": "РўРѕС‚ Р¶Рµ С†РІРµС‚ РїСЂРѕРіРѕРЅР°: РїСѓРЅРєС‚РёСЂРЅР°СЏ Р»РёРЅРёСЏ = РІС‹РїРѕР»РЅРµРЅРЅС‹Рµ Р·Р°РґР°С‡Рё (РЅР°РєРѕРїРёС‚РµР»СЊРЅРѕ).",
    }
    notes_en = {
        "latency": "Line color = sub-run (legend: scenario/algorithm); metric: average task latency (lower is better).",
        "throughput": "Line color = sub-run (legend: scenario/algorithm); metric: system throughput (higher is better).",
        "avg_load": "Line color = sub-run (legend: scenario/algorithm); metric: average node load.",
        "queue": "Line color = sub-run (legend: scenario/algorithm); solid line = queue size.",
        "completed": "Same sub-run color: dashed line = completed tasks (cumulative).",
    }
    table = notes_ru if lang == "ru" else notes_en
    return table.get(series, series)

