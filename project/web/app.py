"""Simple web interface for controlling experiment runs and browsing artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from project.web.commands import build_run_command as _build_run_command
from project.web.dashboard_views import build_dashboard_html as _build_dashboard_html
from project.web.file_routes import (
    build_download_response as _build_download_response,
    build_files_response as _build_files_response,
)
from project.web.i18n import (
    chart_line_note as _chart_line_note,
    insights_placeholder as _insights_placeholder,
    insights_title as _insights_title,
    tr as _tr,
)
from project.web.job_views import (
    fmt_dt as _fmt_dt,
    status_badge as _status_badge,
)
from project.web.job_routes import build_job_data_response as _build_job_data_response
from project.web.layout import render_layout as _render_layout
from project.web.jobs import JobManager, RunJob
from project.web.payloads import job_payload as _job_payload
from project.web.route_responses import RouteResponse as _RouteResponse
from project.web.routing import (
    first as _first,
    lang_from_form as _lang_from_form,
    lang_from_parsed as _lang_from_parsed,
    language_switcher as _language_switcher,
    with_lang as _with_lang,
)


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = "config.yaml"
DEFAULT_PORT = 8080
DEFAULT_HOST = "127.0.0.1"


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
        html = _build_dashboard_html(
            lang,
            jobs,
            workspace_root=WORKSPACE_ROOT,
            default_config=DEFAULT_CONFIG,
        )
        self._send_html(HTTPStatus.OK, html)

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
    <canvas id="chart-latency" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(_chart_line_note(lang, "latency"))}</p>
    <div id="legend-latency" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-throughput" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(_chart_line_note(lang, "throughput"))}</p>
    <div id="legend-throughput" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-load" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(_chart_line_note(lang, "avg_load"))}</p>
    <div id="legend-load" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-queue-completed" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(_chart_line_note(lang, "queue"))}<br />{escape(_chart_line_note(lang, "completed"))}</p>
    <div id="legend-queue-completed" class="run-legend"></div>
  </section>
</div>
<div class="card">
  <h2>{escape(_insights_title(lang))}</h2>
  <ul id="job-insights" class="insights-list">
    <li>{escape(_insights_placeholder(lang))}</li>
  </ul>
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
  axisX: (lang === "ru" ? "\\u0412\\u0440\\u0435\\u043c\\u044f (t)" : "Time (t)"),
  axisY: (lang === "ru" ? "\\u0417\\u043d\\u0430\\u0447\\u0435\\u043d\\u0438\\u0435" : "Value"),
  runWord: (lang === "ru" ? "\\u041f\\u0440\\u043e\\u0433\\u043e\\u043d" : "Run"),
  unknown: {json.dumps(_tr(lang, "unknown"))},
  insightsPlaceholder: {json.dumps(_insights_placeholder(lang))},
  latency: {json.dumps(_tr(lang, "latency_avg"))},
  throughput: {json.dumps(_tr(lang, "throughput"))},
  avgLoad: {json.dumps(_tr(lang, "average_load"))},
  queueCompleted: {json.dumps(_tr(lang, "queue_completed"))}
}};

const runPalette = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#7c3aed",
  "#0f766e",
  "#ea580c",
  "#0891b2",
  "#be123c"
];

function colorForRun(index) {{
  if (index < runPalette.length) {{
    return runPalette[index];
  }}
  const hue = (index * 47) % 360;
  return `hsl(${{hue}}, 72%, 42%)`;
}}

function normalizeRuns(metrics) {{
  const rawRuns = Array.isArray(metrics.runs) ? metrics.runs : [];
  const runs = [];
  for (let i = 0; i < rawRuns.length; i += 1) {{
    const run = rawRuns[i] || {{}};
    const time = Array.isArray(run.time) ? run.time.map((v) => Number(v)) : [];
    if (!time.length) continue;
    runs.push({{
      runIndex: Number.isFinite(Number(run.run_index)) ? Number(run.run_index) : (i + 1),
      time,
      queue: Array.isArray(run.queue) ? run.queue.map((v) => Number(v)) : [],
      completed: Array.isArray(run.completed) ? run.completed.map((v) => Number(v)) : [],
      latency: Array.isArray(run.latency) ? run.latency.map((v) => Number(v)) : [],
      throughput: Array.isArray(run.throughput) ? run.throughput.map((v) => Number(v)) : [],
      avg_load: Array.isArray(run.avg_load) ? run.avg_load.map((v) => Number(v)) : [],
      scenario: String(run.scenario || ""),
      algorithm: String(run.algorithm || ""),
      scenarioLabel: String(run.scenario_label || ""),
      algorithmLabel: String(run.algorithm_label || "")
    }});
  }}
  if (runs.length) return runs;

  const time = Array.isArray(metrics.time) ? metrics.time.map((v) => Number(v)) : [];
  if (!time.length) return [];
  return [{{
    runIndex: 1,
    time,
    queue: Array.isArray(metrics.queue) ? metrics.queue.map((v) => Number(v)) : [],
    completed: Array.isArray(metrics.completed) ? metrics.completed.map((v) => Number(v)) : [],
    latency: Array.isArray(metrics.latency) ? metrics.latency.map((v) => Number(v)) : [],
    throughput: Array.isArray(metrics.throughput) ? metrics.throughput.map((v) => Number(v)) : [],
    avg_load: Array.isArray(metrics.avg_load) ? metrics.avg_load.map((v) => Number(v)) : [],
    scenario: "",
    algorithm: "",
    scenarioLabel: "",
    algorithmLabel: ""
  }}];
}}

function runDescriptorText(run) {{
  const scenarioLabel = String(run.scenarioLabel || run.scenario || "").trim();
  const algorithmLabel = String(run.algorithmLabel || run.algorithm || "").trim();
  const scenarioPart = scenarioLabel || i18n.unknown;
  const algorithmPart = algorithmLabel || i18n.unknown;
  return `${{scenarioPart}} / ${{algorithmPart}}`;
}}

function renderRunLegend(containerId, runs) {{
  const container = document.getElementById(containerId);
  if (!container) return;
  while (container.firstChild) {{
    container.removeChild(container.firstChild);
  }}
  for (let i = 0; i < runs.length; i += 1) {{
    const run = runs[i];
    const item = document.createElement("span");
    item.className = "run-legend-item";
    const swatch = document.createElement("span");
    swatch.className = "run-legend-swatch";
    swatch.style.backgroundColor = colorForRun(i);
    const label = document.createElement("span");
    label.textContent = `${{i18n.runWord}} ${{run.runIndex}}: ${{runDescriptorText(run)}}`;
    item.appendChild(swatch);
    item.appendChild(label);
    container.appendChild(item);
  }}
}}

function formatTick(value) {{
  if (!Number.isFinite(value)) return "";
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toFixed(0);
  if (abs >= 100) return value.toFixed(1);
  if (abs >= 10) return value.toFixed(2);
  if (abs >= 1) return value.toFixed(3);
  return value.toFixed(4);
}}

function drawSeries(canvasId, runs, metricKey, yLabel = i18n.axisY, legendId = "") {{
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
  const padL = 64;
  const padR = 14;
  const padT = 14;
  const padB = 46;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#cbd5e1";
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const series = [];
  for (const run of runs) {{
    const time = Array.isArray(run.time) ? run.time : [];
    const values = Array.isArray(run[metricKey]) ? run[metricKey] : [];
    const n = Math.min(time.length, values.length);
    if (n < 1) continue;
    series.push({{
      runIndex: run.runIndex,
      time: time.slice(0, n),
      values: values.slice(0, n),
      scenario: run.scenario || "",
      algorithm: run.algorithm || "",
      scenarioLabel: run.scenarioLabel || "",
      algorithmLabel: run.algorithmLabel || ""
    }});
  }}
  renderRunLegend(legendId, series);

  const drawAxisLabels = () => {{
    ctx.fillStyle = "#334155";
    ctx.font = "12px Segoe UI, Tahoma, Arial";
    ctx.textAlign = "center";
    ctx.fillText(i18n.axisX, padL + (plotW / 2), h - 8);
    ctx.save();
    ctx.translate(16, padT + (plotH / 2));
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();
    ctx.textAlign = "start";
  }};
  drawAxisLabels();

  if (!series.length) {{
    ctx.fillStyle = "#64748b";
    ctx.font = "13px Segoe UI, Tahoma, Arial";
    ctx.fillText(i18n.noData, padL, h / 2);
    return;
  }}

  const allTimes = series.flatMap((item) => item.time);
  const allValues = series.flatMap((item) => item.values);
  let minY = Math.min(...allValues);
  let maxY = Math.max(...allValues);
  if (minY === maxY) {{
    minY = minY - 1;
    maxY = maxY + 1;
  }}
  const minXRaw = Math.min(...allTimes);
  const maxXRaw = Math.max(...allTimes);
  const minX = minXRaw;
  const maxX = maxXRaw === minXRaw ? minXRaw + 1 : maxXRaw;
  const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * plotW;
  const yToPx = (y) => padT + (1 - (y - minY) / (maxY - minY)) * plotH;

  // Axes
  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  // Grid + Y ticks
  const yTicks = 5;
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#475569";
  ctx.font = "11px Segoe UI, Tahoma, Arial";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= yTicks; i += 1) {{
    const ratio = i / yTicks;
    const y = padT + ratio * plotH;
    const yValue = maxY - ratio * (maxY - minY);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.strokeStyle = "#94a3b8";
    ctx.beginPath();
    ctx.moveTo(padL - 4, y);
    ctx.lineTo(padL, y);
    ctx.stroke();
    ctx.strokeStyle = "#e2e8f0";
    ctx.fillText(formatTick(yValue), padL - 7, y);
  }}

  // X ticks + vertical grid
  const xTicks = 6;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= xTicks; i += 1) {{
    const ratio = i / xTicks;
    const x = padL + ratio * plotW;
    const xValue = minX + ratio * (maxX - minX);
    if (i > 0 && i < xTicks) {{
      ctx.strokeStyle = "#f1f5f9";
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, h - padB);
      ctx.stroke();
    }}
    ctx.strokeStyle = "#94a3b8";
    ctx.beginPath();
    ctx.moveTo(x, h - padB);
    ctx.lineTo(x, h - padB + 4);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.fillText(String(Math.round(xValue)), x, h - padB + 6);
  }}

  for (let s = 0; s < series.length; s += 1) {{
    const item = series[s];
    const color = colorForRun(s);
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < item.values.length; i += 1) {{
      const px = xToPx(item.time[i]);
      const py = yToPx(item.values[i]);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
    const lastX = xToPx(item.time[item.time.length - 1]);
    const lastY = yToPx(item.values[item.values.length - 1]);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 3.0, 0, Math.PI * 2);
    ctx.fill();
  }}

  ctx.fillStyle = "#0f172a";
  ctx.font = "12px Segoe UI, Tahoma, Arial";
  ctx.textBaseline = "alphabetic";
}}

function drawDualSeries(canvasId, runs, aKey, bKey, yLabel = i18n.axisY, legendId = "") {{
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
  const padL = 64;
  const padR = 14;
  const padT = 14;
  const padB = 46;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);
  ctx.strokeStyle = "#cbd5e1";
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const series = [];
  for (const run of runs) {{
    const time = Array.isArray(run.time) ? run.time : [];
    const aVals = Array.isArray(run[aKey]) ? run[aKey] : [];
    const bVals = Array.isArray(run[bKey]) ? run[bKey] : [];
    const n = Math.min(time.length, aVals.length, bVals.length);
    if (n < 1) continue;
    series.push({{
      runIndex: run.runIndex,
      time: time.slice(0, n),
      aVals: aVals.slice(0, n),
      bVals: bVals.slice(0, n),
      scenario: run.scenario || "",
      algorithm: run.algorithm || "",
      scenarioLabel: run.scenarioLabel || "",
      algorithmLabel: run.algorithmLabel || ""
    }});
  }}
  renderRunLegend(legendId, series);

  const drawAxisLabels = () => {{
    ctx.fillStyle = "#334155";
    ctx.font = "12px Segoe UI, Tahoma, Arial";
    ctx.textAlign = "center";
    ctx.fillText(i18n.axisX, padL + (plotW / 2), h - 8);
    ctx.save();
    ctx.translate(16, padT + (plotH / 2));
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yLabel, 0, 0);
    ctx.restore();
    ctx.textAlign = "start";
  }};
  drawAxisLabels();

  if (!series.length) {{
    ctx.fillStyle = "#64748b";
    ctx.font = "13px Segoe UI, Tahoma, Arial";
    ctx.fillText(i18n.noData, padL, h / 2);
    return;
  }}
  const allTimes = series.flatMap((item) => item.time);
  const allValues = series.flatMap((item) => item.aVals.concat(item.bVals));
  let minY = Math.min(...allValues);
  let maxY = Math.max(...allValues);
  if (minY === maxY) {{
    minY = minY - 1;
    maxY = maxY + 1;
  }}
  const minXRaw = Math.min(...allTimes);
  const maxXRaw = Math.max(...allTimes);
  const minX = minXRaw;
  const maxX = maxXRaw === minXRaw ? minXRaw + 1 : maxXRaw;
  const xToPx = (x) => padL + ((x - minX) / (maxX - minX)) * plotW;
  const yToPx = (y) => padT + (1 - (y - minY) / (maxY - minY)) * plotH;

  // Axes
  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(padL, padT);
  ctx.lineTo(padL, h - padB);
  ctx.lineTo(w - padR, h - padB);
  ctx.stroke();

  // Grid + Y ticks
  const yTicks = 5;
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#475569";
  ctx.font = "11px Segoe UI, Tahoma, Arial";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= yTicks; i += 1) {{
    const ratio = i / yTicks;
    const y = padT + ratio * plotH;
    const yValue = maxY - ratio * (maxY - minY);
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
    ctx.strokeStyle = "#94a3b8";
    ctx.beginPath();
    ctx.moveTo(padL - 4, y);
    ctx.lineTo(padL, y);
    ctx.stroke();
    ctx.strokeStyle = "#e2e8f0";
    ctx.fillText(formatTick(yValue), padL - 7, y);
  }}

  // X ticks + vertical grid
  const xTicks = 6;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= xTicks; i += 1) {{
    const ratio = i / xTicks;
    const x = padL + ratio * plotW;
    const xValue = minX + ratio * (maxX - minX);
    if (i > 0 && i < xTicks) {{
      ctx.strokeStyle = "#f1f5f9";
      ctx.beginPath();
      ctx.moveTo(x, padT);
      ctx.lineTo(x, h - padB);
      ctx.stroke();
    }}
    ctx.strokeStyle = "#94a3b8";
    ctx.beginPath();
    ctx.moveTo(x, h - padB);
    ctx.lineTo(x, h - padB + 4);
    ctx.stroke();
    ctx.fillStyle = "#475569";
    ctx.fillText(String(Math.round(xValue)), x, h - padB + 6);
  }}

  function drawLine(times, vals, color, dash = []) {{
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash(dash);
    ctx.beginPath();
    let lastPx = padL;
    let lastPy = h - padB;
    for (let i = 0; i < vals.length; i += 1) {{
      const px = xToPx(times[i]);
      const py = yToPx(vals[i]);
      lastPx = px;
      lastPy = py;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(lastPx, lastPy, 3.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.setLineDash([]);
  }}
  for (let s = 0; s < series.length; s += 1) {{
    const item = series[s];
    const color = colorForRun(s);
    drawLine(item.time, item.aVals, color, []);
    drawLine(item.time, item.bVals, color, [7, 4]);
  }}

  ctx.font = "12px Segoe UI, Tahoma, Arial";
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = "#0f172a";
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
  const runs = normalizeRuns(metrics);
  drawSeries("chart-latency", runs, "latency", i18n.latency, "legend-latency");
  drawSeries("chart-throughput", runs, "throughput", i18n.throughput, "legend-throughput");
  drawSeries("chart-load", runs, "avg_load", i18n.avgLoad, "legend-load");
  drawDualSeries(
    "chart-queue-completed",
    runs,
    "queue",
    "completed",
    i18n.queueCompleted,
    "legend-queue-completed"
  );
  renderInsights(data.insights || []);
}}

function renderInsights(items) {{
  const container = document.getElementById("job-insights");
  if (!container) return;
  while (container.firstChild) {{
    container.removeChild(container.firstChild);
  }}
  const values = Array.isArray(items) ? items : [];
  if (!values.length) {{
    const li = document.createElement("li");
    li.textContent = i18n.insightsPlaceholder;
    container.appendChild(li);
    return;
  }}
  for (const item of values) {{
    const li = document.createElement("li");
    li.textContent = String(item);
    container.appendChild(li);
  }}
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
        response = _build_job_data_response(
            parsed,
            self.job_manager,
            payload_builder=_job_payload,
        )
        self._send_route_response(response)

    def _serve_files(self, parsed) -> None:
        response = _build_files_response(parsed, workspace_root=WORKSPACE_ROOT)
        self._send_route_response(response)

    def _serve_download(self, parsed) -> None:
        response = _build_download_response(parsed, workspace_root=WORKSPACE_ROOT)
        self._send_route_response(response)

    def _start_run(self, form: dict[str, list[str]]) -> None:
        lang = _lang_from_form(form)
        command = _build_run_command(form, default_config=DEFAULT_CONFIG)
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

    def _send_route_response(self, response: _RouteResponse) -> None:
        """Send normalized route response payload."""
        self.send_response(int(response.status))
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """Silence routine access logs to keep console output clean."""
        return


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

