"""Localization catalogs and helpers for the web interface."""

from __future__ import annotations

from typing import Mapping


MODE_OPTIONS = (
    "single",
    "compare",
    "batch",
    "publication",
    "ab-intelligence",
    "ab-llm",
    "repro-check",
)
ALGORITHM_OPTIONS = ("", "round-robin", "min-load", "greedy")
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
        "ab-intelligence": "A/B Intelligence",
        "ab-llm": "A/B LLM",
        "repro-check": "Repro Check",
    },
    "ru": {
        "single": "Одиночный",
        "compare": "Сравнение",
        "batch": "Пакетный",
        "publication": "Публикационный",
        "ab-intelligence": "A/B Интеллект",
        "ab-llm": "A/B LLM",
        "repro-check": "Проверка воспроизводимости",
    },
}

ALGORITHM_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "round-robin": "Round-robin",
        "min-load": "Min-load",
        "greedy": "Greedy",
    },
    "ru": {
        "round-robin": "Круговой (Round-robin)",
        "min-load": "Минимальная нагрузка",
        "greedy": "Жадный",
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
        "static": "Статический",
        "dynamic-load": "Динамическая нагрузка",
        "peak-load": "Пиковая нагрузка",
        "node-failures": "Отказы узлов",
        "heterogeneous-tasks": "Гетерогенные задачи",
        "mixed": "Смешанный",
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
        "console_title": "Веб-консоль экспериментального стенда",
        "workspace": "Рабочая директория",
        "start_experiment": "Запуск эксперимента",
        "mode": "Режим",
        "config_path": "Путь к конфигу",
        "algorithm": "Алгоритм",
        "scenario": "Сценарий",
        "llm_provider": "Провайдер LLM",
        "compare_algorithms": "Алгоритмы сравнения",
        "batch_scenarios": "Сценарии batch",
        "batch_algorithms": "Алгоритмы batch",
        "batch_runs": "Количество batch-прогонов",
        "repro_runs": "Количество repro-прогонов",
        "study_seeds": "Seeds исследования",
        "output_dir_override": "Переопределить output dir",
        "log_level": "Уровень логирования",
        "disable_intelligence": "отключить интеллект",
        "disable_llm": "отключить llm",
        "no_plots": "без графиков",
        "no_csv": "без csv",
        "batch_save_runs": "сохранять batch-прогоны",
        "batch_keep_adaptive": "оставить adaptive в batch",
        "study_quick": "быстрый publication",
        "run": "Запустить",
        "expected_runs_title": "Ожидаемое число прогонов",
        "expected_runs_formula": "Формула",
        "expected_runs_fallback": "Для пустых выборов используются значения по умолчанию.",
        "unknown": "неизвестно",
        "mode_mapping": "Сопоставление режимов",
        "quick_links": "Быстрые ссылки",
        "browse_outputs": "Открыть outputs",
        "browse_docs": "Открыть docs",
        "open_config": "Открыть config.yaml",
        "health_check": "Проверка health",
        "running_jobs": "Активные задачи",
        "recent_jobs": "Последние задачи",
        "no_active_jobs": "Активных задач нет.",
        "no_runs_started": "Запуски пока не выполнялись.",
        "id": "id",
        "status": "статус",
        "started": "старт",
        "finished": "финиш",
        "rc": "код",
        "command": "команда",
        "actions": "действия",
        "open": "открыть",
        "job": "Задача",
        "back_dashboard": "Назад на дашборд",
        "return_code": "Код возврата",
        "stop_job": "Остановить задачу",
        "latency_avg": "Latency (средняя)",
        "throughput": "Пропускная способность",
        "average_load": "Средняя загрузка",
        "queue_completed": "Очередь / Выполнено",
        "log": "Лог",
        "no_data_yet": "Данных пока нет",
        "queue": "Очередь",
        "completed": "Выполнено",
        "browse": "Просмотр",
        "download_as_is": "Скачать как есть",
        "parent": ".. родительская папка",
        "type": "тип",
        "name": "имя",
        "size_bytes": "размер (байт)",
        "empty": "(пусто)",
        "dir": "папка",
        "file": "файл",
        "file_page": "Файл",
        "back_folder": "Назад к папке",
        "download": "Скачать",
        "preview": "Предпросмотр",
        "path_not_exist": "Путь не существует.",
        "file_not_found": "Файл не найден.",
        "job_not_found": "Задача не найдена.",
        "not_found": "Не найдено.",
        "no_inline_preview": "Для этого типа файла нет предпросмотра. Используйте скачивание.",
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
        "queued": "в очереди",
        "running": "выполняется",
        "success": "успешно",
        "failed": "ошибка",
        "stopped": "остановлено",
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
        return "(по умолчанию)"
    return "(default)"


def insights_title(lang: str) -> str:
    """Localized title for researcher insights card."""
    if lang == "ru":
        return "Выводы исследовательского агента"
    return "Researcher Insights"


def insights_placeholder(lang: str) -> str:
    """Localized placeholder for insights list before enough data arrives."""
    if lang == "ru":
        return "Недостаточно данных для выводов."
    return "Not enough data for conclusions yet."


def chart_line_note(lang: str, series: str) -> str:
    """Localized explanatory text for each chart line."""
    notes_ru = {
        "latency": "Цвет линии = отдельный прогон (легенда: сценарий/алгоритм); метрика: средняя задержка задач (ниже лучше).",
        "throughput": "Цвет линии = отдельный прогон (легенда: сценарий/алгоритм); метрика: пропускная способность (выше лучше).",
        "avg_load": "Цвет линии = отдельный прогон (легенда: сценарий/алгоритм); метрика: средняя загрузка узлов.",
        "queue": "Цвет линии = отдельный прогон (легенда: сценарий/алгоритм); сплошная линия = размер очереди.",
        "completed": "Тот же цвет прогона: пунктирная линия = выполненные задачи (накопительно).",
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
