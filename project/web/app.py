"""Simple web interface for controlling experiment runs and browsing artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import shlex
import subprocess
import sys
from threading import Lock, Thread
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "config.yaml"
DEFAULT_PORT = 8080
DEFAULT_HOST = "127.0.0.1"
MAX_LOG_LINES = 4000
MAX_PREVIEW_CHARS = 120_000
MAX_CHART_POINTS = 300

TICK_METRIC_RE = re.compile(
    r"t=(?P<time>\d+)\s+queue=(?P<queue>\d+)\s+completed=(?P<completed>\d+)\s+"
    r"latency=(?P<latency>[0-9.]+)\s+throughput=(?P<throughput>[0-9.]+)\s+"
    r"avg_load=(?P<avg_load>[0-9.]+)"
)

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
LANG_OPTIONS = ("en", "ru")

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
        "compare_algorithms": "Compare algorithms (comma)",
        "batch_scenarios": "Batch scenarios (comma)",
        "batch_algorithms": "Batch algorithms (comma)",
        "batch_runs": "Batch runs",
        "repro_runs": "Repro runs",
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
        "compare_algorithms": "Алгоритмы сравнения (через запятую)",
        "batch_scenarios": "Сценарии batch (через запятую)",
        "batch_algorithms": "Алгоритмы batch (через запятую)",
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
    },
    "ru": {
        "queued": "в очереди",
        "running": "выполняется",
        "success": "успешно",
        "failed": "ошибка",
        "stopped": "остановлено",
    },
}


@dataclass(slots=True)
class RunJob:
    """Background experiment process state."""

    id: str
    command: list[str]
    cwd: Path
    status: str = "queued"  # queued | running | success | failed | stopped
    started_at: datetime | None = None
    finished_at: datetime | None = None
    return_code: int | None = None
    log_lines: list[str] = field(default_factory=list)
    process: subprocess.Popen[str] | None = field(default=None, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def command_text(self) -> str:
        """Render command as shell-like string."""
        return " ".join(shlex.quote(part) for part in self.command)

    def append_log(self, line: str) -> None:
        """Append one log line and trim history to cap."""
        with self._lock:
            self.log_lines.append(line.rstrip("\n"))
            if len(self.log_lines) > MAX_LOG_LINES:
                over = len(self.log_lines) - MAX_LOG_LINES
                del self.log_lines[:over]

    def stop(self) -> bool:
        """Request process termination if still running."""
        with self._lock:
            process = self.process
        if process is None or process.poll() is not None:
            return False
        process.terminate()
        return True


class JobManager:
    """Thread-safe registry and executor for background experiment jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, RunJob] = {}
        self._lock = Lock()

    def create(self, command: list[str], cwd: Path) -> RunJob:
        """Create and launch background job for command."""
        job = RunJob(
            id=uuid4().hex[:10],
            command=list(command),
            cwd=cwd,
        )
        with self._lock:
            self._jobs[job.id] = job
        thread = Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    def list_jobs(self) -> list[RunJob]:
        """Return jobs sorted by newest start/finish timestamp."""
        with self._lock:
            jobs = list(self._jobs.values())
        return sorted(
            jobs,
            key=lambda item: item.started_at or item.finished_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    def get(self, job_id: str) -> RunJob | None:
        """Get one job by identifier."""
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job: RunJob) -> None:
        """Worker routine that executes command and captures logs."""
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                job.command,
                cwd=str(job.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            with job._lock:
                job.process = process
            if process.stdout is not None:
                for line in process.stdout:
                    job.append_log(line)
            code = process.wait()
            job.return_code = code
            if code == 0:
                job.status = "success"
            else:
                # Distinguish regular failures from manual stop if possible.
                if job.status != "stopped":
                    job.status = "failed"
        except Exception as exc:  # noqa: BLE001
            job.append_log(f"[web-ui] runner error: {exc!r}")
            job.return_code = -1
            if job.status != "stopped":
                job.status = "failed"
        finally:
            with job._lock:
                job.process = None
            job.finished_at = datetime.now(timezone.utc)


class ExperimentWebServer(ThreadingHTTPServer):
    """Threaded HTTP server with reusable socket and daemon workers."""

    daemon_threads = True
    allow_reuse_address = True


class WebHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard, job control, and artifact browsing."""

    job_manager: ClassVar[JobManager]
    server_version = "TestbedWeb/1.0"

    def do_GET(self) -> None:  # noqa: N802
        """Route GET requests."""
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_dashboard(parsed)
            return
        if parsed.path == "/job":
            self._serve_job(parsed)
            return
        if parsed.path == "/job-data":
            self._serve_job_data(parsed)
            return
        if parsed.path == "/files":
            self._serve_files(parsed)
            return
        if parsed.path == "/download":
            self._serve_download(parsed)
            return
        if parsed.path == "/health":
            self._send_text(HTTPStatus.OK, "ok")
            return
        lang = _lang_from_parsed(parsed)
        self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "not_found"))

    def do_POST(self) -> None:  # noqa: N802
        """Route POST requests."""
        parsed = urlparse(self.path)
        form = self._parse_form()
        if parsed.path == "/run":
            self._start_run(form)
            return
        if parsed.path == "/stop":
            self._stop_run(form)
            return
        lang = _lang_from_form(form)
        self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "not_found"))

    def _serve_dashboard(self, parsed) -> None:
        lang = _lang_from_parsed(parsed)
        jobs = self.job_manager.list_jobs()
        running_rows = [job for job in jobs if job.status == "running"]
        recent_rows = jobs[:20]

        running_html = "".join(_job_row_html(job, lang) for job in running_rows) or (
            f"<tr><td colspan='7'>{escape(_tr(lang, 'no_active_jobs'))}</td></tr>"
        )
        recent_html = "".join(_job_row_html(job, lang) for job in recent_rows) or (
            f"<tr><td colspan='7'>{escape(_tr(lang, 'no_runs_started'))}</td></tr>"
        )

        mode_options = "".join(
            f"<option value='{escape(mode)}'>{escape(mode)}</option>"
            for mode in MODE_OPTIONS
        )
        algorithm_options = "".join(
            f"<option value='{escape(name)}'>{escape(name or '(default)')}</option>"
            for name in ALGORITHM_OPTIONS
        )
        scenario_options = "".join(
            f"<option value='{escape(name)}'>{escape(name or '(default)')}</option>"
            for name in SCENARIO_OPTIONS
        )
        switcher = _language_switcher(
            lang,
            "/",
        )

        body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(_tr(lang, "console_title"))}</h1>
<p>{escape(_tr(lang, "workspace"))}: <code>{escape(str(WORKSPACE_ROOT))}</code></p>
<div class="grid">
  <section class="card">
    <h2>{escape(_tr(lang, "start_experiment"))}</h2>
    <form method="post" action="/run">
      <input type="hidden" name="lang" value="{escape(lang)}" />
      <label>{escape(_tr(lang, "mode"))}</label>
      <select name="mode">{mode_options}</select>

      <label>{escape(_tr(lang, "config_path"))}</label>
      <input type="text" name="config" value="{escape(DEFAULT_CONFIG)}" />

      <label>{escape(_tr(lang, "algorithm"))}</label>
      <select name="algorithm">{algorithm_options}</select>

      <label>{escape(_tr(lang, "scenario"))}</label>
      <select name="scenario">{scenario_options}</select>

      <label>{escape(_tr(lang, "llm_provider"))}</label>
      <input type="text" name="llm_provider" value="" placeholder="auto|openai|mock" />

      <label>{escape(_tr(lang, "compare_algorithms"))}</label>
      <input type="text" name="compare_algorithms" value="" placeholder="round-robin,min-load,greedy" />

      <label>{escape(_tr(lang, "batch_scenarios"))}</label>
      <input type="text" name="batch_scenarios" value="" placeholder="static,peak-load" />

      <label>{escape(_tr(lang, "batch_algorithms"))}</label>
      <input type="text" name="batch_algorithms" value="" placeholder="round-robin,min-load,greedy" />

      <label>{escape(_tr(lang, "batch_runs"))}</label>
      <input type="number" name="batch_runs" value="3" min="1" />

      <label>{escape(_tr(lang, "repro_runs"))}</label>
      <input type="number" name="repro_runs" value="3" min="2" />

      <label>{escape(_tr(lang, "study_seeds"))}</label>
      <input type="text" name="study_seeds" value="42-71" />

      <label>{escape(_tr(lang, "output_dir_override"))}</label>
      <input type="text" name="output_dir" value="" placeholder="outputs" />

      <label>{escape(_tr(lang, "log_level"))}</label>
      <input type="text" name="log_level" value="" placeholder="INFO" />

      <div class="checks">
        <label><input type="checkbox" name="disable_intelligence" /> {escape(_tr(lang, "disable_intelligence"))}</label>
        <label><input type="checkbox" name="disable_llm" /> {escape(_tr(lang, "disable_llm"))}</label>
        <label><input type="checkbox" name="no_plots" /> {escape(_tr(lang, "no_plots"))}</label>
        <label><input type="checkbox" name="no_csv" /> {escape(_tr(lang, "no_csv"))}</label>
        <label><input type="checkbox" name="batch_save_runs" /> {escape(_tr(lang, "batch_save_runs"))}</label>
        <label><input type="checkbox" name="batch_keep_adaptive" /> {escape(_tr(lang, "batch_keep_adaptive"))}</label>
        <label><input type="checkbox" name="study_quick" checked /> {escape(_tr(lang, "study_quick"))}</label>
      </div>
      <button type="submit">{escape(_tr(lang, "run"))}</button>
    </form>
    <p class="hint">{escape(_tr(lang, "mode_mapping"))}: <code>single</code>, <code>compare</code>, <code>batch</code>,
    <code>publication</code>, <code>ab-intelligence</code>, <code>ab-llm</code>, <code>repro-check</code>.</p>
  </section>

  <section class="card">
    <h2>{escape(_tr(lang, "quick_links"))}</h2>
    <ul>
      <li><a href="{escape(_with_lang('/files', lang, path='outputs'))}">{escape(_tr(lang, "browse_outputs"))}</a></li>
      <li><a href="{escape(_with_lang('/files', lang, path='docs'))}">{escape(_tr(lang, "browse_docs"))}</a></li>
      <li><a href="{escape(_with_lang('/files', lang, path='config.yaml'))}">{escape(_tr(lang, "open_config"))}</a></li>
      <li><a href="/health">{escape(_tr(lang, "health_check"))}</a></li>
    </ul>
  </section>
</div>

<section class="card">
  <h2>{escape(_tr(lang, "running_jobs"))}</h2>
  <table>
    <thead>
      <tr><th>{escape(_tr(lang, "id"))}</th><th>{escape(_tr(lang, "status"))}</th><th>{escape(_tr(lang, "started"))}</th><th>{escape(_tr(lang, "finished"))}</th><th>{escape(_tr(lang, "rc"))}</th><th>{escape(_tr(lang, "command"))}</th><th>{escape(_tr(lang, "actions"))}</th></tr>
    </thead>
    <tbody>{running_html}</tbody>
  </table>
</section>

<section class="card">
  <h2>{escape(_tr(lang, "recent_jobs"))}</h2>
  <table>
    <thead>
      <tr><th>{escape(_tr(lang, "id"))}</th><th>{escape(_tr(lang, "status"))}</th><th>{escape(_tr(lang, "started"))}</th><th>{escape(_tr(lang, "finished"))}</th><th>{escape(_tr(lang, "rc"))}</th><th>{escape(_tr(lang, "command"))}</th><th>{escape(_tr(lang, "actions"))}</th></tr>
    </thead>
    <tbody>{recent_html}</tbody>
  </table>
</section>
"""
        self._send_html(
            HTTPStatus.OK,
            _render_layout(_tr(lang, "console_title"), body, auto_refresh_seconds=0, lang=lang),
        )

    def _serve_job(self, parsed) -> None:
        query = parse_qs(parsed.query)
        lang = _lang_from_parsed(parsed)
        job_id = _first(query, "id", "")
        job = self.job_manager.get(job_id)
        if job is None:
            self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "job_not_found"))
            return

        stop_button = ""
        if job.status == "running":
            stop_button = f"""
<form method="post" action="/stop" style="display:inline;">
  <input type="hidden" name="id" value="{escape(job.id)}" />
  <input type="hidden" name="lang" value="{escape(lang)}" />
  <button type="submit">{escape(_tr(lang, "stop_job"))}</button>
</form>
"""
        switcher = _language_switcher(
            lang,
            "/job",
            id=job.id,
        )

        body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(_tr(lang, "job"))} {escape(job.id)}</h1>
<p><a href="{escape(_with_lang('/', lang))}">{escape(_tr(lang, "back_dashboard"))}</a> | <a href="{escape(_with_lang('/files', lang, path='outputs'))}">{escape(_tr(lang, "browse_outputs"))}</a></p>
<div class="card">
  <p>{escape(_tr(lang, "status"))}: <span id="job-status">{_status_badge(job.status, lang)}</span></p>
  <p>{escape(_tr(lang, "started"))}: <code id="job-started">{escape(_fmt_dt(job.started_at))}</code></p>
  <p>{escape(_tr(lang, "finished"))}: <code id="job-finished">{escape(_fmt_dt(job.finished_at))}</code></p>
  <p>{escape(_tr(lang, "return_code"))}: <code id="job-rc">{escape(str(job.return_code))}</code></p>
  <p>{escape(_tr(lang, "command"))}:</p>
  <pre id="job-command">{escape(job.command_text())}</pre>
  {stop_button}
</div>
<div class="chart-grid">
  <section class="card">
    <h2>{escape(_tr(lang, "latency_avg"))}</h2>
    <canvas id="chart-latency" class="chart-canvas" width="900" height="260"></canvas>
  </section>
  <section class="card">
    <h2>{escape(_tr(lang, "throughput"))}</h2>
    <canvas id="chart-throughput" class="chart-canvas" width="900" height="260"></canvas>
  </section>
  <section class="card">
    <h2>{escape(_tr(lang, "average_load"))}</h2>
    <canvas id="chart-load" class="chart-canvas" width="900" height="260"></canvas>
  </section>
  <section class="card">
    <h2>{escape(_tr(lang, "queue_completed"))}</h2>
    <canvas id="chart-queue-completed" class="chart-canvas" width="900" height="260"></canvas>
  </section>
</div>
<div class="card">
  <h2>{escape(_tr(lang, "log"))}</h2>
  <pre class="log" id="job-log"></pre>
</div>
<script>
const jobId = {json.dumps(job.id)};
const lang = {json.dumps(lang)};
const i18n = {{
  noData: {json.dumps(_tr(lang, "no_data_yet"))},
  latency: {json.dumps(_tr(lang, "latency_avg"))},
  throughput: {json.dumps(_tr(lang, "throughput"))},
  avgLoad: {json.dumps(_tr(lang, "average_load"))},
  queue: {json.dumps(_tr(lang, "queue"))},
  completed: {json.dumps(_tr(lang, "completed"))}
}};

function drawSeries(canvasId, times, values, color, label) {{
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth || 900;
  const cssHeight = canvas.clientHeight || 260;
  if (canvas.width !== Math.floor(cssWidth * dpr) || canvas.height !== Math.floor(cssHeight * dpr)) {{
    canvas.width = Math.floor(cssWidth * dpr);
    canvas.height = Math.floor(cssHeight * dpr);
  }}
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = cssWidth;
  const h = cssHeight;
  const padL = 46;
  const padR = 14;
  const padT = 14;
  const padB = 30;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#cbd5e1";
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

  if (!times.length || !values.length) {{
    ctx.fillStyle = "#64748b";
    ctx.font = "13px Segoe UI, Tahoma, Arial";
    ctx.fillText(i18n.noData, padL, h / 2);
    return;
  }}

  let minY = Math.min(...values);
  let maxY = Math.max(...values);
  if (minY === maxY) {{
    minY = minY - 1;
    maxY = maxY + 1;
  }}
  const minX = times[0];
  const maxX = times[times.length - 1] === minX ? minX + 1 : times[times.length - 1];

  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * plotW;
  const yToPx = (y) => padT + (1 - (y - minY) / (maxY - minY)) * plotH;

  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {{
    const y = padT + (i / 4) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }}

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < values.length; i += 1) {{
    const px = xToPx(times[i]);
    const py = yToPx(values[i]);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }}
  ctx.stroke();

  const lastX = xToPx(times[times.length - 1]);
  const lastY = yToPx(values[values.length - 1]);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(lastX, lastY, 3.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#0f172a";
  ctx.font = "12px Segoe UI, Tahoma, Arial";
  ctx.fillText(label, padL, 12);
  ctx.fillText(`t: ${{minX}} .. ${{times[times.length - 1]}}`, padL, h - 10);
  ctx.fillText(`min: ${{minY.toFixed(3)}}`, w - 140, 12);
  ctx.fillText(`max: ${{maxY.toFixed(3)}}`, w - 140, 26);
}}

function drawDualSeries(canvasId, times, aVals, bVals, aColor, bColor, aLabel, bLabel) {{
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssWidth = canvas.clientWidth || 900;
  const cssHeight = canvas.clientHeight || 260;
  if (canvas.width !== Math.floor(cssWidth * dpr) || canvas.height !== Math.floor(cssHeight * dpr)) {{
    canvas.width = Math.floor(cssWidth * dpr);
    canvas.height = Math.floor(cssHeight * dpr);
  }}
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = cssWidth;
  const h = cssHeight;
  const padL = 46;
  const padR = 14;
  const padT = 14;
  const padB = 30;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#cbd5e1";
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

  if (!times.length || !aVals.length || !bVals.length) {{
    ctx.fillStyle = "#64748b";
    ctx.font = "13px Segoe UI, Tahoma, Arial";
    ctx.fillText(i18n.noData, padL, h / 2);
    return;
  }}
  const values = aVals.concat(bVals);
  let minY = Math.min(...values);
  let maxY = Math.max(...values);
  if (minY === maxY) {{
    minY = minY - 1;
    maxY = maxY + 1;
  }}
  const minX = times[0];
  const maxX = times[times.length - 1] === minX ? minX + 1 : times[times.length - 1];
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * plotW;
  const yToPx = (y) => padT + (1 - (y - minY) / (maxY - minY)) * plotH;

  ctx.strokeStyle = "#e2e8f0";
  for (let i = 0; i <= 4; i += 1) {{
    const y = padT + (i / 4) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }}

  function drawLine(vals, color) {{
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < vals.length; i += 1) {{
      const px = xToPx(times[i]);
      const py = yToPx(vals[i]);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
  }}
  drawLine(aVals, aColor);
  drawLine(bVals, bColor);

  ctx.font = "12px Segoe UI, Tahoma, Arial";
  ctx.fillStyle = aColor;
  ctx.fillText(aLabel, padL, 12);
  ctx.fillStyle = bColor;
  ctx.fillText(bLabel, padL + 100, 12);
  ctx.fillStyle = "#0f172a";
  ctx.fillText(`t: ${{minX}} .. ${{times[times.length - 1]}}`, padL, h - 10);
}}

function updateJobView(data) {{
  document.getElementById("job-status").innerHTML = data.status_badge_html;
  document.getElementById("job-started").textContent = data.started_at;
  document.getElementById("job-finished").textContent = data.finished_at;
  document.getElementById("job-rc").textContent = String(data.return_code);
  document.getElementById("job-command").textContent = data.command;

  const logEl = document.getElementById("job-log");
  const wasNearBottom = (logEl.scrollTop + logEl.clientHeight) >= (logEl.scrollHeight - 24);
  logEl.textContent = data.log_text;
  if (wasNearBottom) {{
    logEl.scrollTop = logEl.scrollHeight;
  }}

  const metrics = data.metrics || {{}};
  const t = metrics.time || [];
  drawSeries("chart-latency", t, metrics.latency || [], "#2563eb", i18n.latency);
  drawSeries("chart-throughput", t, metrics.throughput || [], "#16a34a", i18n.throughput);
  drawSeries("chart-load", t, metrics.avg_load || [], "#dc2626", i18n.avgLoad);
  drawDualSeries(
    "chart-queue-completed",
    t,
    metrics.queue || [],
    metrics.completed || [],
    "#7c3aed",
    "#0f766e",
    i18n.queue,
    i18n.completed
  );
}}

let pollTimer = null;
async function pollJobData() {{
  try {{
    const response = await fetch(`/job-data?id=${{encodeURIComponent(jobId)}}&lang=${{encodeURIComponent(lang)}}`, {{
      cache: "no-store"
    }});
    if (!response.ok) return;
    const data = await response.json();
    updateJobView(data);
    if (data.status !== "running" && data.status !== "queued") {{
      if (pollTimer) {{
        clearInterval(pollTimer);
        pollTimer = null;
      }}
    }}
  }} catch (_err) {{
    // Ignore temporary network errors during polling.
  }}
}}

pollJobData();
pollTimer = setInterval(pollJobData, 2000);
</script>
"""
        self._send_html(
            HTTPStatus.OK,
            _render_layout(f"{_tr(lang, 'job')} {job.id}", body, auto_refresh_seconds=0, lang=lang),
        )

    def _serve_job_data(self, parsed) -> None:
        """Return JSON payload with live job status, logs, and chart metrics."""
        query = parse_qs(parsed.query)
        lang = _lang_from_parsed(parsed)
        job_id = _first(query, "id", "")
        job = self.job_manager.get(job_id)
        if job is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": _tr(lang, "job_not_found")})
            return
        self._send_json(HTTPStatus.OK, _job_payload(job, lang))

    def _serve_files(self, parsed) -> None:
        query = parse_qs(parsed.query)
        lang = _lang_from_parsed(parsed)
        raw_path = _first(query, "path", "outputs")
        try:
            path = _resolve_path(raw_path)
        except ValueError as exc:
            self._send_text(HTTPStatus.BAD_REQUEST, str(exc))
            return

        if not path.exists():
            self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "path_not_exist"))
            return

        rel = _rel_workspace(path)
        parent_link = ""
        if path != WORKSPACE_ROOT:
            parent_link = (
                f"<p><a href='{escape(_with_lang('/files', lang, path=_rel_workspace(path.parent)))}'>{escape(_tr(lang, 'parent'))}</a></p>"
            )

        if path.is_dir():
            rows: list[str] = []
            items = sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
            for item in items:
                item_rel = _rel_workspace(item)
                if item.is_dir():
                    rows.append(
                        "<tr>"
                        f"<td>{escape(_tr(lang, 'dir'))}</td><td><a href='{escape(_with_lang('/files', lang, path=item_rel))}'>{escape(item.name)}</a></td>"
                        "<td>-</td>"
                        "</tr>"
                    )
                else:
                    size = item.stat().st_size
                    rows.append(
                        "<tr>"
                        f"<td>{escape(_tr(lang, 'file'))}</td><td><a href='{escape(_with_lang('/files', lang, path=item_rel))}'>{escape(item.name)}</a></td>"
                        f"<td>{size}</td>"
                        "</tr>"
                    )
            table_body = "".join(rows) or f"<tr><td colspan='3'>{escape(_tr(lang, 'empty'))}</td></tr>"
            switcher = _language_switcher(
                lang,
                "/files",
                path=rel,
            )
            body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(_tr(lang, "browse"))}: <code>{escape(rel)}</code></h1>
<p><a href="{escape(_with_lang('/', lang))}">{escape(_tr(lang, "back_dashboard"))}</a> | <a href="{escape(_with_lang('/download', lang, path=rel))}">{escape(_tr(lang, "download_as_is"))}</a></p>
{parent_link}
<table>
  <thead><tr><th>{escape(_tr(lang, "type"))}</th><th>{escape(_tr(lang, "name"))}</th><th>{escape(_tr(lang, "size_bytes"))}</th></tr></thead>
  <tbody>{table_body}</tbody>
</table>
"""
            self._send_html(HTTPStatus.OK, _render_layout(f"{_tr(lang, 'browse')}: {rel}", body, lang=lang))
            return

        download_url = _with_lang("/download", lang, path=rel)
        preview_html = _build_preview_html(path, rel, lang)
        switcher = _language_switcher(
            lang,
            "/files",
            path=rel,
        )
        body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(_tr(lang, "file_page"))}: <code>{escape(rel)}</code></h1>
<p><a href="{escape(_with_lang('/', lang))}">{escape(_tr(lang, "back_dashboard"))}</a> |
<a href="{escape(_with_lang('/files', lang, path=_rel_workspace(path.parent)))}">{escape(_tr(lang, "back_folder"))}</a> |
<a href="{escape(download_url)}">{escape(_tr(lang, "download"))}</a></p>
{preview_html}
"""
        self._send_html(HTTPStatus.OK, _render_layout(f"{_tr(lang, 'file_page')}: {rel}", body, lang=lang))

    def _serve_download(self, parsed) -> None:
        query = parse_qs(parsed.query)
        lang = _lang_from_parsed(parsed)
        raw_path = _first(query, "path", "")
        try:
            path = _resolve_path(raw_path)
        except ValueError as exc:
            self._send_text(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if not path.exists() or path.is_dir():
            self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "file_not_found"))
            return
        mime_type, _ = mimetypes.guess_type(path.name)
        content_type = mime_type or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            f"inline; filename={path.name}",
        )
        self.end_headers()
        self.wfile.write(data)

    def _start_run(self, form: dict[str, list[str]]) -> None:
        lang = _lang_from_form(form)
        command = _build_run_command(form)
        job = self.job_manager.create(command=command, cwd=WORKSPACE_ROOT)
        self._redirect(_with_lang("/job", lang, id=job.id))

    def _stop_run(self, form: dict[str, list[str]]) -> None:
        lang = _lang_from_form(form)
        job_id = _first(form, "id", "")
        job = self.job_manager.get(job_id)
        if job is None:
            self._send_text(HTTPStatus.NOT_FOUND, _tr(lang, "job_not_found"))
            return
        stopped = job.stop()
        if stopped:
            job.status = "stopped"
            job.append_log("[web-ui] stop requested.")
        self._redirect(_with_lang("/job", lang, id=job_id))

    def _parse_form(self) -> dict[str, list[str]]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        return parse_qs(raw, keep_blank_values=True)

    def _send_text(self, status: HTTPStatus, text: str) -> None:
        data = text.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, status: HTTPStatus, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        """Send JSON response with UTF-8 encoding."""
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """Silence routine access logs to keep console output clean."""
        return


def _first(mapping: dict[str, list[str]], key: str, default: str = "") -> str:
    """Read first value from parsed query/form mapping."""
    values = mapping.get(key, [])
    if not values:
        return default
    return values[0]


def _tr(lang: str, key: str) -> str:
    """Translate UI key for selected language with fallback to English."""
    table = UI_TEXT.get(lang, UI_TEXT["en"])
    if key in table:
        return table[key]
    return UI_TEXT["en"].get(key, key)


def _lang_from_parsed(parsed) -> str:
    """Extract language from query string; default to English."""
    query = parse_qs(parsed.query)
    lang = _first(query, "lang", "en").strip().lower()
    if lang in LANG_OPTIONS:
        return lang
    return "en"


def _lang_from_form(form: dict[str, list[str]]) -> str:
    """Extract language from posted form; default to English."""
    lang = _first(form, "lang", "en").strip().lower()
    if lang in LANG_OPTIONS:
        return lang
    return "en"


def _with_lang(route: str, lang: str, include_lang: bool = True, **params: str) -> str:
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


def _language_switcher(lang: str, route: str, include_lang: bool = True, **params: str) -> str:
    """Render language toggle links for current page."""
    ru_url = _with_lang(route, "ru", include_lang=include_lang, **params)
    en_url = _with_lang(route, "en", include_lang=include_lang, **params)
    ru_class = "lang-link active" if lang == "ru" else "lang-link"
    en_class = "lang-link active" if lang == "en" else "lang-link"
    return (
        "<nav class='lang-switch'>"
        f"<a class='{ru_class}' href='{escape(ru_url)}'>RUS</a>"
        f"<a class='{en_class}' href='{escape(en_url)}'>ENG</a>"
        "</nav>"
    )


def _is_checked(form: dict[str, list[str]], name: str) -> bool:
    """Interpret checkbox field as boolean."""
    value = _first(form, name, "")
    return value.lower() in {"on", "1", "true", "yes"}


def _safe_int(text: str, fallback: int, minimum: int | None = None) -> int:
    """Parse integer with fallback and optional minimum."""
    try:
        value = int(text.strip())
    except Exception:  # noqa: BLE001
        value = fallback
    if minimum is not None:
        value = max(minimum, value)
    return value


def _build_run_command(form: dict[str, list[str]]) -> list[str]:
    """Build CLI command from web form fields."""
    config = _first(form, "config", DEFAULT_CONFIG).strip() or DEFAULT_CONFIG
    mode = _first(form, "mode", "single").strip().lower()
    mode = mode if mode in MODE_OPTIONS else "single"

    command: list[str] = [
        sys.executable,
        "-m",
        "project.experiments.run",
        "--config",
        config,
    ]

    algorithm = _first(form, "algorithm", "").strip()
    if algorithm:
        command.extend(["--algorithm", algorithm])

    scenario = _first(form, "scenario", "").strip()
    if scenario:
        command.extend(["--scenario", scenario])

    llm_provider = _first(form, "llm_provider", "").strip()
    if llm_provider:
        command.extend(["--llm-provider", llm_provider])

    output_dir = _first(form, "output_dir", "").strip()
    if output_dir:
        command.extend(["--output-dir", output_dir])

    log_level = _first(form, "log_level", "").strip()
    if log_level:
        command.extend(["--log-level", log_level])

    if _is_checked(form, "disable_intelligence"):
        command.append("--disable-intelligence")
    if _is_checked(form, "disable_llm"):
        command.append("--disable-llm")
    if _is_checked(form, "no_plots"):
        command.append("--no-plots")
    if _is_checked(form, "no_csv"):
        command.append("--no-csv")

    if mode == "compare":
        command.append("--compare")
        compare_algorithms = _first(form, "compare_algorithms", "").strip()
        if compare_algorithms:
            command.extend(["--compare-algorithms", compare_algorithms])

    elif mode == "batch":
        command.append("--batch")
        batch_scenarios = _first(form, "batch_scenarios", "").strip()
        if batch_scenarios:
            command.extend(["--batch-scenarios", batch_scenarios])
        batch_algorithms = _first(form, "batch_algorithms", "").strip()
        if batch_algorithms:
            command.extend(["--batch-algorithms", batch_algorithms])
        batch_runs = _safe_int(_first(form, "batch_runs", "3"), fallback=3, minimum=1)
        command.extend(["--batch-runs", str(batch_runs)])
        if _is_checked(form, "batch_save_runs"):
            command.append("--batch-save-runs")
        if _is_checked(form, "batch_keep_adaptive"):
            command.append("--batch-keep-adaptive")

    elif mode == "publication":
        command.append("--publication-study")
        if _is_checked(form, "study_quick"):
            command.append("--study-quick")
        study_seeds = _first(form, "study_seeds", "42-71").strip()
        if study_seeds:
            command.extend(["--study-seeds", study_seeds])

    elif mode == "ab-intelligence":
        command.append("--ab-intelligence")

    elif mode == "ab-llm":
        command.append("--ab-llm")

    elif mode == "repro-check":
        command.append("--repro-check")
        repro_runs = _safe_int(_first(form, "repro_runs", "3"), fallback=3, minimum=2)
        command.extend(["--repro-runs", str(repro_runs)])

    return command


def _resolve_path(raw: str) -> Path:
    """Resolve user path and ensure it stays inside workspace root."""
    candidate = (raw or "").strip()
    if not candidate:
        path = WORKSPACE_ROOT / "outputs"
    else:
        path = Path(candidate)
        if not path.is_absolute():
            path = WORKSPACE_ROOT / path
    resolved = path.resolve()
    try:
        resolved.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError("Path must stay within workspace root.") from exc
    return resolved


def _rel_workspace(path: Path) -> str:
    """Return path relative to workspace using forward slashes."""
    return path.resolve().relative_to(WORKSPACE_ROOT).as_posix()


def _fmt_dt(value: datetime | None) -> str:
    """Format datetime for UI tables."""
    if value is None:
        return "-"
    return value.astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _status_badge(status: str, lang: str = "en") -> str:
    """Render status as colored badge."""
    color = {
        "queued": "#6b7280",
        "running": "#2563eb",
        "success": "#16a34a",
        "failed": "#dc2626",
        "stopped": "#b45309",
    }.get(status, "#6b7280")
    label = STATUS_LABELS.get(lang, STATUS_LABELS["en"]).get(status, status)
    return (
        f"<span class='badge' style='background:{color}'>"
        f"{escape(label)}</span>"
    )


def _job_row_html(job: RunJob, lang: str) -> str:
    """Render one row of job list table."""
    command = escape(job.command_text())
    open_url = _with_lang("/job", lang, id=job.id)
    return (
        "<tr>"
        f"<td><a href='{escape(open_url)}'><code>{escape(job.id)}</code></a></td>"
        f"<td>{_status_badge(job.status, lang)}</td>"
        f"<td>{escape(_fmt_dt(job.started_at))}</td>"
        f"<td>{escape(_fmt_dt(job.finished_at))}</td>"
        f"<td><code>{escape(str(job.return_code))}</code></td>"
        f"<td><code>{command}</code></td>"
        f"<td><a href='{escape(open_url)}'>{escape(_tr(lang, 'open'))}</a></td>"
        "</tr>"
    )


def _job_payload(job: RunJob, lang: str) -> dict[str, object]:
    """Serialize job state for live UI polling endpoint."""
    with job._lock:
        lines = list(job.log_lines)
    metrics = _extract_metrics_from_logs(lines)
    return {
        "id": job.id,
        "status": job.status,
        "status_badge_html": _status_badge(job.status, lang),
        "started_at": _fmt_dt(job.started_at),
        "finished_at": _fmt_dt(job.finished_at),
        "return_code": job.return_code,
        "command": job.command_text(),
        "log_text": "\n".join(lines),
        "metrics": metrics,
        "lang": lang,
    }


def _extract_metrics_from_logs(lines: list[str]) -> dict[str, list[float | int]]:
    """Extract timeseries metrics from simulation loop log lines."""
    points: list[dict[str, float | int]] = []
    for line in lines:
        match = TICK_METRIC_RE.search(line)
        if match is None:
            continue
        points.append(
            {
                "time": int(match.group("time")),
                "queue": int(match.group("queue")),
                "completed": int(match.group("completed")),
                "latency": float(match.group("latency")),
                "throughput": float(match.group("throughput")),
                "avg_load": float(match.group("avg_load")),
            }
        )
    if len(points) > MAX_CHART_POINTS:
        points = points[-MAX_CHART_POINTS:]

    if not points:
        return {
            "time": [],
            "queue": [],
            "completed": [],
            "latency": [],
            "throughput": [],
            "avg_load": [],
        }
    return {
        "time": [int(item["time"]) for item in points],
        "queue": [int(item["queue"]) for item in points],
        "completed": [int(item["completed"]) for item in points],
        "latency": [float(item["latency"]) for item in points],
        "throughput": [float(item["throughput"]) for item in points],
        "avg_load": [float(item["avg_load"]) for item in points],
    }


def _build_preview_html(path: Path, rel: str, lang: str) -> str:
    """Build safe preview block for common file types."""
    suffix = path.suffix.lower()
    download_url = _with_lang("/download", lang, path=rel)

    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg"}:
        return (
            "<div class='card'>"
            f"<h2>{escape(_tr(lang, 'preview'))}</h2>"
            f"<img src='{escape(download_url)}' alt='{escape(path.name)}' class='preview' />"
            "</div>"
        )

    if suffix in {".txt", ".log", ".md", ".json", ".csv", ".yaml", ".yml"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_PREVIEW_CHARS:
            text = text[:MAX_PREVIEW_CHARS] + "\n... [truncated]"
        return (
            "<div class='card'>"
            f"<h2>{escape(_tr(lang, 'preview'))}</h2>"
            f"<pre class='log'>{escape(text)}</pre>"
            "</div>"
        )

    return (
        "<div class='card'>"
        f"<p>{escape(_tr(lang, 'no_inline_preview'))}</p>"
        "</div>"
    )


def _render_layout(title: str, body: str, auto_refresh_seconds: int = 0, lang: str = "en") -> str:
    """Render full HTML layout around body content."""
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


def _build_parser() -> ArgumentParser:
    """Create CLI parser for web app startup."""
    parser = ArgumentParser(description="Run local web UI for experiment testbed.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port.")
    return parser


def main() -> None:
    """Start threaded HTTP server for web interface."""
    args = _build_parser().parse_args()
    manager = JobManager()
    WebHandler.job_manager = manager
    server = ExperimentWebServer((str(args.host), int(args.port)), WebHandler)
    print(f"[web-ui] running at http://{args.host}:{args.port}")
    print(f"[web-ui] workspace: {WORKSPACE_ROOT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
