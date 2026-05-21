"""Job details page rendering helpers for the web UI."""

from __future__ import annotations

from html import escape
import json
from typing import Protocol

from project.web.i18n import chart_line_note, insights_placeholder, insights_title, tr
from project.web.job_views import fmt_dt, status_badge
from project.web.layout import render_layout
from project.web.routing import language_switcher, with_lang


class _JobLike(Protocol):
    """Minimal protocol for rendering job page content."""

    id: str
    status: str
    started_at: object
    finished_at: object
    return_code: object

    def command_text(self) -> str: ...


def build_job_page_html(job: _JobLike, lang: str) -> str:
    """Build full HTML document for job details page with live charts."""
    stop_button = ""
    if job.status == "running":
        stop_button = f"""
<form method="post" action="/stop" style="display:inline;">
  <input type="hidden" name="id" value="{escape(job.id)}" />
  <input type="hidden" name="lang" value="{escape(lang)}" />
  <button type="submit">{escape(tr(lang, "stop_job"))}</button>
</form>
"""
    switcher = language_switcher(
        lang,
        "/job",
        id=job.id,
    )

    body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(tr(lang, "job"))} {escape(job.id)}</h1>
<p><a href="{escape(with_lang('/', lang))}">{escape(tr(lang, "back_dashboard"))}</a> | <a href="{escape(with_lang('/files', lang, path='outputs'))}">{escape(tr(lang, "browse_outputs"))}</a></p>
<div class="card">
  <p>{escape(tr(lang, "status"))}: <span id="job-status">{status_badge(job.status, lang)}</span></p>
  <p>{escape(tr(lang, "started"))}: <code id="job-started">{escape(fmt_dt(job.started_at))}</code></p>
  <p>{escape(tr(lang, "finished"))}: <code id="job-finished">{escape(fmt_dt(job.finished_at))}</code></p>
  <p>{escape(tr(lang, "return_code"))}: <code id="job-rc">{escape(str(job.return_code))}</code></p>
  <p>{escape(tr(lang, "status_details"))}: <code id="job-details">-</code></p>
  <p>{escape(tr(lang, "command"))}:</p>
  <pre id="job-command">{escape(job.command_text())}</pre>
  <p id="job-diagnostics-links"></p>
  {stop_button}
</div>
<div class="chart-grid">
  <section class="card">
    <canvas id="chart-latency" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(chart_line_note(lang, "latency"))}</p>
    <div id="legend-latency" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-throughput" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(chart_line_note(lang, "throughput"))}</p>
    <div id="legend-throughput" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-load" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(chart_line_note(lang, "avg_load"))}</p>
    <div id="legend-load" class="run-legend"></div>
  </section>
  <section class="card">
    <canvas id="chart-queue-completed" class="chart-canvas" width="900" height="260"></canvas>
    <p class="chart-note">{escape(chart_line_note(lang, "queue"))}<br />{escape(chart_line_note(lang, "completed"))}</p>
    <div id="legend-queue-completed" class="run-legend"></div>
  </section>
</div>
<div class="card">
  <h2>{escape(insights_title(lang))}</h2>
  <ul id="job-insights" class="insights-list">
    <li>{escape(insights_placeholder(lang))}</li>
  </ul>
</div>
<div class="card" id="literature-evidence-card">
  <h2>{escape(tr(lang, "literature_evidence_title"))}</h2>
  <p id="literature-evidence-query" class="chart-note">{escape(tr(lang, "literature_query_pending"))}</p>
  <ul id="job-literature-evidence" class="insights-list">
    <li>{escape(tr(lang, "literature_evidence_pending"))}</li>
  </ul>
</div>
<div class="card" id="claims-card">
  <h2>{escape(tr(lang, "claims_title"))}</h2>
  <div class="control-row">
    <label>{escape(tr(lang, "claims_hypothesis_filter"))}
      <select id="claims-hypothesis-filter">
        <option value="">{escape(tr(lang, "claims_all_hypotheses"))}</option>
        <option value="H1">H1</option>
        <option value="H2">H2</option>
        <option value="H3">H3</option>
        <option value="H4">H4</option>
        <option value="H5">H5</option>
      </select>
    </label>
    <label>{escape(tr(lang, "claims_min_confidence"))}
      <input id="claims-confidence-filter" type="number" min="0" max="1" step="0.1" value="0" />
    </label>
    <label class="check-inline">
      <input id="claims-evidence-filter" type="checkbox" />
      {escape(tr(lang, "claims_with_evidence_only"))}
    </label>
  </div>
  <p id="claims-gate-status" class="chart-note"></p>
  <ul id="job-claims" class="insights-list">
    <li>{escape(tr(lang, "claims_pending"))}</li>
  </ul>
</div>
<div class="card" id="carbon-outcomes-card" style="display:none;">
  <h2>{escape(tr(lang, "carbon_outcomes_title"))}</h2>
  <ul id="job-carbon-outcomes" class="insights-list">
    <li>{escape(tr(lang, "carbon_outcomes_pending"))}</li>
  </ul>
</div>
<div class="card">
  <h2>{escape(tr(lang, "log"))}</h2>
  <pre class="log" id="job-log"></pre>
</div>
<script>
const jobId = {json.dumps(job.id)};
const lang = {json.dumps(lang)};
const i18n = {{
  noData: {json.dumps(tr(lang, "no_data_yet"))},
  axisX: (lang === "ru" ? "\\u0412\\u0440\\u0435\\u043c\\u044f (t)" : "Time (t)"),
  axisY: (lang === "ru" ? "\\u0417\\u043d\\u0430\\u0447\\u0435\\u043d\\u0438\\u0435" : "Value"),
  runWord: (lang === "ru" ? "\\u041f\\u0440\\u043e\\u0433\\u043e\\u043d" : "Run"),
  unknown: {json.dumps(tr(lang, "unknown"))},
  insightsPlaceholder: {json.dumps(insights_placeholder(lang))},
  latency: {json.dumps(tr(lang, "latency_avg"))},
  throughput: {json.dumps(tr(lang, "throughput"))},
  avgLoad: {json.dumps(tr(lang, "average_load"))},
  queueCompleted: {json.dumps(tr(lang, "queue_completed"))},
  diagnosticsBundle: {json.dumps(tr(lang, "diagnostics_bundle"))},
  carbonOutcomesPending: {json.dumps(tr(lang, "carbon_outcomes_pending"))},
  carbonBestMethod: {json.dumps(tr(lang, "carbon_best_method"))},
  carbonBaselineMethod: {json.dumps(tr(lang, "carbon_baseline_method"))},
  carbonCo2PerTask: {json.dumps(tr(lang, "carbon_co2_per_task"))},
  carbonCo2Total: {json.dumps(tr(lang, "carbon_co2_total"))},
  carbonLatencyDelta: {json.dumps(tr(lang, "carbon_latency_delta"))},
  carbonThroughputDelta: {json.dumps(tr(lang, "carbon_throughput_delta"))},
  carbonCo2ReductionPct: {json.dumps(tr(lang, "carbon_co2_reduction_pct"))},
  literatureEvidencePending: {json.dumps(tr(lang, "literature_evidence_pending"))},
  literatureEvidenceUnavailable: {json.dumps(tr(lang, "literature_evidence_unavailable"))},
  literatureEvidenceGateFailed: {json.dumps(tr(lang, "literature_evidence_gate_failed"))},
  literatureEvidenceSourceCount: {json.dumps(tr(lang, "literature_evidence_source_count"))},
  literatureEvidenceQuery: {json.dumps(tr(lang, "literature_evidence_query"))},
  claimsPending: {json.dumps(tr(lang, "claims_pending"))},
  claimsGateFailed: {json.dumps(tr(lang, "claims_gate_failed"))},
  claimsNoMatches: {json.dumps(tr(lang, "claims_no_matches"))},
  claimsStatus: {json.dumps(tr(lang, "claims_status"))},
  claimsConfidence: {json.dumps(tr(lang, "claims_confidence"))},
  claimsEvidence: {json.dumps(tr(lang, "claims_evidence"))}
}};

let latestClaims = [];
let latestClaimsGate = null;

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
  document.getElementById("job-details").textContent = String(data.status_details || "-");
  document.getElementById("job-command").textContent = data.command;
  const diagEl = document.getElementById("job-diagnostics-links");
  if (diagEl) {{
    const status = String(data.status || "");
    if (status === "failed" || status === "timeout" || status === "stopped") {{
      const href = `/job-bundle?id=${{encodeURIComponent(jobId)}}&lang=${{encodeURIComponent(lang)}}`;
      diagEl.innerHTML = `<a href="${{href}}">${{i18n.diagnosticsBundle}}</a>`;
    }} else {{
      diagEl.textContent = "";
    }}
  }}

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
  renderLiteratureEvidence(
    data.literature_evidence || null,
    data.literature_evidence_gate || null
  );
  latestClaims = Array.isArray(data.claims) ? data.claims : [];
  latestClaimsGate = data.claims_gate || null;
  renderClaims(latestClaims, latestClaimsGate);
  renderCarbonOutcomes(data.carbon_outcomes || null);
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

function _fmtMetric(value, digits = 3, suffix = "") {{
  const num = Number(value);
  if (!Number.isFinite(num)) {{
    return i18n.unknown;
  }}
  return `${{num.toFixed(digits)}}${{suffix}}`;
}}

function renderClaims(claims, gate) {{
  const list = document.getElementById("job-claims");
  const gateEl = document.getElementById("claims-gate-status");
  const hypothesisEl = document.getElementById("claims-hypothesis-filter");
  const confidenceEl = document.getElementById("claims-confidence-filter");
  const evidenceEl = document.getElementById("claims-evidence-filter");
  if (!list || !gateEl) return;
  while (list.firstChild) {{
    list.removeChild(list.firstChild);
  }}

  const gateInfo = (gate && typeof gate === "object") ? gate : null;
  if (gateInfo && gateInfo.ok === false) {{
    const errors = Array.isArray(gateInfo.errors) ? gateInfo.errors.slice(0, 2).join("; ") : "";
    gateEl.textContent = errors ? `${{i18n.claimsGateFailed}} ${{errors}}` : i18n.claimsGateFailed;
  }} else {{
    gateEl.textContent = "";
  }}

  const values = Array.isArray(claims) ? claims : [];
  if (!values.length) {{
    const li = document.createElement("li");
    li.textContent = i18n.claimsPending;
    list.appendChild(li);
    return;
  }}

  const hypothesis = hypothesisEl ? String(hypothesisEl.value || "") : "";
  const minConfidence = confidenceEl ? Number(confidenceEl.value || 0) : 0;
  const evidenceOnly = evidenceEl ? Boolean(evidenceEl.checked) : false;
  const filtered = values.filter((claim) => {{
    const claimHypothesis = String(claim.hypothesis || "");
    const confidence = Number(claim.confidence || 0);
    const evidence = Array.isArray(claim.evidence) ? claim.evidence : [];
    if (hypothesis && claimHypothesis !== hypothesis) return false;
    if (Number.isFinite(minConfidence) && confidence < minConfidence) return false;
    if (evidenceOnly && !evidence.length) return false;
    return true;
  }});

  if (!filtered.length) {{
    const li = document.createElement("li");
    li.textContent = i18n.claimsNoMatches;
    list.appendChild(li);
    return;
  }}

  for (const claim of filtered) {{
    const hypothesisText = String(claim.hypothesis || i18n.unknown);
    const status = String(claim.status || i18n.unknown);
    const confidence = Number(claim.confidence || 0);
    const statement = String(claim.statement || "");
    const evidence = Array.isArray(claim.evidence) ? claim.evidence : [];
    const citations = evidence.slice(0, 3).map((item) => {{
      const articleId = String(item.article_id || i18n.unknown);
      const page = Number.isFinite(Number(item.page)) ? Number(item.page) : "?";
      return `[${{articleId}}, p. ${{page}}]`;
    }}).join(", ");
    const li = document.createElement("li");
    const confidenceText = Number.isFinite(confidence) ? confidence.toFixed(2) : "0.00";
    li.textContent = `${{hypothesisText}} | ${{i18n.claimsStatus}}: ${{status}} | ${{i18n.claimsConfidence}}: ${{confidenceText}} | ${{statement}}${{citations ? " | " + i18n.claimsEvidence + ": " + citations : ""}}`;
    list.appendChild(li);
  }}
}}

function renderLiteratureEvidence(payload, gate) {{
  const list = document.getElementById("job-literature-evidence");
  const queryLabel = document.getElementById("literature-evidence-query");
  if (!list || !queryLabel) return;
  while (list.firstChild) {{
    list.removeChild(list.firstChild);
  }}

  const evidence = (payload && typeof payload === "object") ? payload : null;
  const gateInfo = (gate && typeof gate === "object") ? gate : null;
  if (!evidence) {{
    queryLabel.textContent = i18n.literatureEvidenceUnavailable;
    const li = document.createElement("li");
    li.textContent = i18n.literatureEvidencePending;
    list.appendChild(li);
    return;
  }}
  const query = String(evidence.query || "").trim();
  queryLabel.textContent = query
    ? `${{i18n.literatureEvidenceQuery}}: ${{query}}`
    : i18n.literatureEvidenceUnavailable;

  if (!evidence.available) {{
    const li = document.createElement("li");
    li.textContent = `${{i18n.literatureEvidenceUnavailable}} (${{String(evidence.reason || i18n.unknown)}})`;
    list.appendChild(li);
    return;
  }}

  if (gateInfo && !gateInfo.skipped) {{
    const sourceCount = Number(gateInfo.source_count);
    const minSources = Number(gateInfo.min_sources);
    const quality = document.createElement("li");
    quality.textContent = `${{i18n.literatureEvidenceSourceCount}}: ${{sourceCount}} / ${{minSources}}`;
    list.appendChild(quality);
    if (gateInfo.ok === false) {{
      const warn = document.createElement("li");
      warn.textContent = i18n.literatureEvidenceGateFailed;
      list.appendChild(warn);
    }}
  }}

  const items = Array.isArray(evidence.items) ? evidence.items : [];
  if (!items.length) {{
    const li = document.createElement("li");
    li.textContent = i18n.literatureEvidenceUnavailable;
    list.appendChild(li);
    return;
  }}
  for (const item of items) {{
    const articleId = String(item.article_id || i18n.unknown);
    const page = Number.isFinite(Number(item.page)) ? Number(item.page) : 0;
    const title = String(item.title || i18n.unknown);
    const score = Number(item.score);
    const scoreText = Number.isFinite(score) ? score.toFixed(4) : "n/a";
    const snippet = String(item.snippet || "");
    const li = document.createElement("li");
    li.textContent = `[${{articleId}}, p. ${{page}}] ${{title}} (score=${{scoreText}}): ${{snippet}}`;
    list.appendChild(li);
  }}
}}

function renderCarbonOutcomes(payload) {{
  const card = document.getElementById("carbon-outcomes-card");
  const list = document.getElementById("job-carbon-outcomes");
  if (!card || !list) return;
  while (list.firstChild) {{
    list.removeChild(list.firstChild);
  }}

  const item = (payload && typeof payload === "object") ? payload : null;
  if (!item) {{
    card.style.display = "none";
    return;
  }}
  card.style.display = "";
  if (!item.available) {{
    const li = document.createElement("li");
    li.textContent = i18n.carbonOutcomesPending;
    list.appendChild(li);
    return;
  }}

  const lines = [
    `${{i18n.carbonBestMethod}}: ${{String(item.best_method || i18n.unknown)}}`,
    `${{i18n.carbonBaselineMethod}}: ${{String(item.baseline_method || i18n.unknown)}}`,
    `${{i18n.carbonCo2PerTask}}: ${{_fmtMetric(item.co2_per_task_lb, 4, " lb")}}`,
    `${{i18n.carbonCo2Total}}: ${{_fmtMetric(item.co2_total_lb, 2, " lb")}}`,
    `${{i18n.carbonLatencyDelta}}: ${{_fmtMetric(item.latency_delta_vs_baseline, 3)}}`,
    `${{i18n.carbonThroughputDelta}}: ${{_fmtMetric(item.throughput_delta_vs_baseline, 3)}}`,
    `${{i18n.carbonCo2ReductionPct}}: ${{_fmtMetric(item.co2_reduction_vs_baseline_pct, 2, "%")}}`
  ];
  for (const text of lines) {{
    const li = document.createElement("li");
    li.textContent = text;
    list.appendChild(li);
  }}
}}

let pollTimer = null;
const claimsFilterIds = ["claims-hypothesis-filter", "claims-confidence-filter", "claims-evidence-filter"];
for (const filterId of claimsFilterIds) {{
  const element = document.getElementById(filterId);
  if (element) {{
    element.addEventListener("change", () => renderClaims(latestClaims, latestClaimsGate));
  }}
}}
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
    return render_layout(f"{tr(lang, 'job')} {job.id}", body, auto_refresh_seconds=0, lang=lang)
