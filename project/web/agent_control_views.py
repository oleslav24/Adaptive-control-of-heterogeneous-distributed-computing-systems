"""HTML view builders for agent control / quality-gate page."""

from __future__ import annotations

from html import escape
import json
from typing import Sequence

from project.web.agent_control import JobControlAssessment
from project.web.layout import render_layout
from project.web.routing import language_switcher, with_lang


def build_agent_control_html(
    *,
    lang: str,
    demo_profile: dict[str, object],
    assessment: JobControlAssessment | None,
    assessment_mode: str,
    requested_job_id: str,
    available_jobs: Sequence[object],
    assessment_message: str,
) -> str:
    """Render `/agent-control` page with demo and real-job assessment modes."""
    text = _page_text(lang)
    switcher = language_switcher(lang, "/agent-control")
    selected_mode = (
        assessment_mode
        if assessment_mode in {"demo", "latest", "latest-terminal", "latest_terminal", "job", "id"}
        else "demo"
    )
    selected_mode = "job" if selected_mode == "id" else selected_mode
    selected_mode = "latest-terminal" if selected_mode == "latest_terminal" else selected_mode

    job_options = "".join(
        (
            f"<option value='{escape(str(getattr(job, 'id', '')))}'>"
            f"{escape(str(getattr(job, 'id', '')))}"
            f" ({escape(str(getattr(job, 'status', 'unknown')))})"
            "</option>"
        )
        for job in list(available_jobs)[:25]
        if str(getattr(job, "id", "")).strip()
    )
    assessment_block = _render_assessment_block(lang, text, assessment, assessment_message)

    body = f"""
<style>
  .ac-grid {{
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 12px;
    margin: 0 14px;
  }}
  .ac-grid-single {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin: 0 14px;
  }}
  .ac-flow {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 6px;
    margin-top: 10px;
  }}
  .ac-flow-node {{
    border: 1px solid #d9e2ec;
    background: #f8fafc;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    font-size: 12px;
    font-weight: 600;
  }}
  .ac-status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border-radius: 999px;
    padding: 4px 10px;
    border: 1px solid #cbd5e1;
    font-size: 12px;
    font-weight: 700;
  }}
  .ac-status-STABLE {{ background: #ecfdf5; color: #166534; border-color: #22c55e; }}
  .ac-status-WARNING {{ background: #fffbeb; color: #92400e; border-color: #f59e0b; }}
  .ac-status-CRITICAL {{ background: #fef2f2; color: #991b1b; border-color: #ef4444; }}
  .ac-status-CONTROLLED_STATE {{ background: #f1f5f9; color: #334155; border-color: #64748b; }}
  .ac-component-list {{ display: grid; gap: 8px; }}
  .ac-component-row {{
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    padding: 8px;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
    align-items: center;
  }}
  .ac-component-title {{ font-weight: 700; font-size: 13px; }}
  .ac-component-desc {{ font-size: 12px; color: #486581; }}
  .ac-toggle {{ width: 20px; height: 20px; }}
  .ac-metric-row {{ margin: 8px 0; }}
  .ac-metric-head {{ display: flex; justify-content: space-between; font-size: 13px; }}
  .ac-metric-bar {{ height: 8px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }}
  .ac-metric-fill {{ height: 100%; border-radius: 999px; }}
  .ac-log {{
    border: 1px solid #d9e2ec;
    background: #f8fafc;
    border-radius: 10px;
    padding: 10px;
    max-height: 240px;
    overflow: auto;
    font-family: Consolas, monospace;
    font-size: 12px;
  }}
  .ac-log-line {{ margin: 4px 0; }}
  .ac-controls {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;
  }}
  .ac-controls button {{ width: 100%; margin-top: 0; }}
  .ac-assess-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }}
  .ac-assess-result {{ margin-top: 10px; }}
  .ac-tag {{
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    border-radius: 999px;
    padding: 3px 8px;
    border: 1px solid #cbd5e1;
    text-transform: uppercase;
  }}
  .ac-tag-pass {{ background: #ecfdf5; color: #166534; border-color: #22c55e; }}
  .ac-tag-fail {{ background: #fef2f2; color: #991b1b; border-color: #ef4444; }}
  .ac-tag-present {{ background: #eff6ff; color: #1d4ed8; border-color: #3b82f6; }}
  .ac-tag-unknown {{ background: #f8fafc; color: #475569; border-color: #94a3b8; }}
  @media (max-width: 1024px) {{
    .ac-grid {{ grid-template-columns: 1fr; }}
    .ac-flow {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ac-controls {{ grid-template-columns: 1fr; }}
    .ac-assess-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1 style="margin: 14px;">{escape(text['title'])}</h1>
<p style="margin: 0 14px 14px 14px; color: #486581;">{escape(text['subtitle'])}</p>
<p style="margin: 0 14px 14px 14px;"><a href="{escape(with_lang('/', lang))}">{escape(text['back_dashboard'])}</a></p>

<div class="ac-grid-single">
  <section class="card">
    <h2>{escape(text['quality_loop'])}</h2>
    <div class="ac-flow">
      <div class="ac-flow-node">{escape(text['flow_task'])}</div>
      <div class="ac-flow-node">{escape(text['flow_agent'])}</div>
      <div class="ac-flow-node">{escape(text['flow_log'])}</div>
      <div class="ac-flow-node">{escape(text['flow_qgate'])}</div>
      <div class="ac-flow-node">{escape(text['flow_verify'])}</div>
      <div class="ac-flow-node">{escape(text['flow_decision'])}</div>
    </div>
  </section>
</div>

<div class="ac-grid">
  <section class="card">
    <h2>{escape(text['demo_title'])}</h2>
    <p class="hint">{escape(text['demo_warning'])}</p>
    <p><span id="ac-status-pill" class="ac-status-pill ac-status-STABLE">STABLE</span></p>
    <p id="ac-status-description" class="hint"></p>
    <div class="ac-controls">
      <button id="ac-run-scenario" type="button">{escape(text['run_scenario'])}</button>
      <button id="ac-disable-next" type="button">{escape(text['disable_next'])}</button>
      <button id="ac-enable-all" type="button">{escape(text['enable_all'])}</button>
      <button id="ac-controlled" type="button">{escape(text['controlled_state'])}</button>
      <button id="ac-reset" type="button">{escape(text['reset'])}</button>
    </div>
  </section>

  <section class="card">
    <h2>{escape(text['real_assessment'])}</h2>
    <form method="get" action="/agent-control" id="ac-assess-form">
      <input type="hidden" name="lang" value="{escape(lang)}" />
      <div class="ac-assess-grid">
        <label>{escape(text['assessment_mode'])}
          <select name="assess" id="ac-assess-mode">
            <option value="demo" {'selected' if selected_mode == 'demo' else ''}>{escape(text['mode_demo'])}</option>
            <option value="latest" {'selected' if selected_mode == 'latest' else ''}>{escape(text['mode_latest'])}</option>
            <option value="latest-terminal" {'selected' if selected_mode == 'latest-terminal' else ''}>{escape(text['mode_latest_terminal'])}</option>
            <option value="job" {'selected' if selected_mode == 'job' else ''}>{escape(text['mode_job'])}</option>
          </select>
        </label>
        <label>{escape(text['job_id'])}
          <input type="text" name="id" id="ac-job-id" value="{escape(requested_job_id)}" list="ac-job-list" />
          <datalist id="ac-job-list">{job_options}</datalist>
        </label>
      </div>
      <button type="submit" style="margin-top:10px;">{escape(text['run_assessment'])}</button>
    </form>
    {assessment_block}
  </section>
</div>

<div class="ac-grid">
  <section class="card">
    <h2>{escape(text['components_title'])}</h2>
    <div id="ac-components" class="ac-component-list"></div>
  </section>

  <section class="card">
    <h2>{escape(text['metrics_title'])}</h2>
    <div id="ac-metrics"></div>
  </section>
</div>

<div class="ac-grid-single">
  <section class="card">
    <h2>{escape(text['events_title'])}</h2>
    <div id="ac-log" class="ac-log"></div>
  </section>
</div>

<script>
(() => {{
  const profile = {json.dumps(demo_profile, ensure_ascii=False)};
  const text = {json.dumps(_client_text(text), ensure_ascii=False)};

  const componentIds = profile.components.map((item) => String(item.id));
  const state = {{
    enabled: Object.fromEntries(componentIds.map((id) => [id, true])),
    controlledState: false,
    status: "STABLE",
    metrics: Object.fromEntries(profile.metrics.map((item) => [item.id, Number(item.baseline || 100)])),
    log: [],
    scenarioRunning: false
  }};

  function nowTime() {{
    const d = new Date();
    const pad = (value) => String(value).padStart(2, "0");
    return `${{pad(d.getHours())}}:${{pad(d.getMinutes())}}:${{pad(d.getSeconds())}}`;
  }}

  function pushLog(level, message) {{
    state.log.push({{ time: nowTime(), level, message }});
    if (state.log.length > 300) state.log = state.log.slice(-300);
    renderLog();
  }}

  function statusClass(status) {{
    if (status === "WARNING") return "ac-status-WARNING";
    if (status === "CRITICAL") return "ac-status-CRITICAL";
    if (status === "CONTROLLED_STATE") return "ac-status-CONTROLLED_STATE";
    return "ac-status-STABLE";
  }}

  function statusExplanation(status) {{
    if (status === "CRITICAL") return text.status_critical;
    if (status === "WARNING") return text.status_warning;
    if (status === "CONTROLLED_STATE") return text.status_controlled;
    return text.status_stable;
  }}

  function metricColor(value) {{
    if (value >= 80) return "#16a34a";
    if (value >= 50) return "#d97706";
    return "#dc2626";
  }}

  function recomputeMetrics() {{
    const next = Object.fromEntries(profile.metrics.map((item) => [item.id, Number(item.baseline || 100)]));
    for (const componentId of componentIds) {{
      if (state.enabled[componentId]) continue;
      const impact = profile.impacts[componentId] || {{}};
      for (const [metricId, dropValue] of Object.entries(impact)) {{
        const prev = Number(next[metricId] || 0);
        next[metricId] = Math.max(0, prev - Number(dropValue));
      }}
    }}

    if (state.controlledState) {{
      const bandMin = Number(profile.controlled_band?.[0] ?? 55);
      const bandMax = Number(profile.controlled_band?.[1] ?? 75);
      for (const metricId of Object.keys(next)) {{
        const value = Number(next[metricId]);
        next[metricId] = Math.max(bandMin, Math.min(bandMax, Math.max(value, bandMin)));
      }}
    }}
    state.metrics = next;
  }}

  function hasCriticalCombo() {{
    const combos = Array.isArray(profile.critical_combos) ? profile.critical_combos : [];
    for (const combo of combos) {{
      if (!Array.isArray(combo) || combo.length < 3) continue;
      if (combo.every((id) => state.enabled[id] === false)) return true;
    }}
    return false;
  }}

  function recomputeStatus() {{
    if (state.controlledState) {{
      state.status = "CONTROLLED_STATE";
      return;
    }}
    const disabledCount = componentIds.filter((id) => !state.enabled[id]).length;
    if (disabledCount === 0) {{
      state.status = "STABLE";
      return;
    }}
    if (hasCriticalCombo() || disabledCount >= 4) {{
      state.status = "CRITICAL";
      return;
    }}
    state.status = "WARNING";
  }}

  function recomputeAll() {{
    recomputeMetrics();
    recomputeStatus();
  }}

  function renderStatus() {{
    const pill = document.getElementById("ac-status-pill");
    const description = document.getElementById("ac-status-description");
    pill.className = `ac-status-pill ${{statusClass(state.status)}}`;
    pill.textContent = state.status;
    description.textContent = statusExplanation(state.status);
  }}

  function renderComponents() {{
    const root = document.getElementById("ac-components");
    root.innerHTML = "";
    for (const component of profile.components) {{
      const id = String(component.id);
      const row = document.createElement("div");
      row.className = "ac-component-row";
      const checked = state.enabled[id] ? "checked" : "";
      const disabled = state.controlledState ? "disabled" : "";
      row.innerHTML = `
        <div>
          <div class="ac-component-title">${{component.name}}</div>
          <div class="ac-component-desc">${{component.description}}</div>
        </div>
        <div>
          <input class="ac-toggle" type="checkbox" data-id="${{id}}" ${{checked}} ${{disabled}} />
        </div>
      `;
      root.appendChild(row);
    }}
    for (const node of root.querySelectorAll("input[type=checkbox][data-id]")) {{
      node.addEventListener("change", () => {{
        if (state.controlledState) {{
          node.checked = Boolean(state.enabled[node.dataset.id]);
          return;
        }}
        const id = String(node.dataset.id || "");
        state.enabled[id] = Boolean(node.checked);
        pushLog(node.checked ? "ok" : "warn", node.checked ? `${{id}}: ${{text.log_enabled}}` : `${{id}}: ${{text.log_disabled}}`);
        recomputeAll();
        render();
      }});
    }}
  }}

  function renderMetrics() {{
    const root = document.getElementById("ac-metrics");
    root.innerHTML = "";
    for (const metric of profile.metrics) {{
      const id = String(metric.id);
      const value = Number(state.metrics[id] || 0);
      const color = metricColor(value);
      const row = document.createElement("div");
      row.className = "ac-metric-row";
      row.innerHTML = `
        <div class="ac-metric-head"><span>${{metric.name}}</span><span style="color:${{color}}">${{Math.round(value)}}%</span></div>
        <div class="ac-metric-bar"><div class="ac-metric-fill" style="width:${{Math.max(0, Math.min(100, value))}}%; background:${{color}}"></div></div>
      `;
      root.appendChild(row);
    }}
  }}

  function renderLog() {{
    const root = document.getElementById("ac-log");
    root.innerHTML = "";
    for (const entry of state.log) {{
      const line = document.createElement("div");
      line.className = "ac-log-line";
      line.textContent = `[${{entry.time}}] [${{String(entry.level || "info").toUpperCase()}}] ${{entry.message}}`;
      root.appendChild(line);
    }}
    root.scrollTop = root.scrollHeight;
  }}

  function render() {{
    renderStatus();
    renderComponents();
    renderMetrics();
  }}

  function disableNext() {{
    if (state.controlledState || state.scenarioRunning) return;
    const order = Array.isArray(profile.disable_order) ? profile.disable_order : componentIds;
    const next = order.find((id) => state.enabled[id]);
    if (!next) return;
    state.enabled[next] = false;
    pushLog("warn", `${{next}}: ${{text.log_disabled}}`);
    recomputeAll();
    render();
  }}

  function enableAll() {{
    if (state.controlledState) {{
      pushLog("info", text.controlled_reset_needed);
      return;
    }}
    for (const id of componentIds) state.enabled[id] = true;
    pushLog("ok", text.all_controls_enabled);
    recomputeAll();
    render();
  }}

  function controlledState() {{
    if (state.controlledState) return;
    state.controlledState = true;
    pushLog("ctrl", text.entered_controlled_state);
    recomputeAll();
    render();
  }}

  function resetAll() {{
    for (const id of componentIds) state.enabled[id] = true;
    state.controlledState = false;
    state.status = "STABLE";
    state.scenarioRunning = false;
    state.log = [];
    recomputeAll();
    pushLog("info", text.reset_done);
    render();
  }}

  function sleep(ms) {{
    return new Promise((resolve) => setTimeout(resolve, ms));
  }}

  async function runScenario() {{
    if (state.scenarioRunning) return;
    if (state.controlledState) {{
      pushLog("info", text.controlled_reset_needed);
      return;
    }}
    state.scenarioRunning = true;
    pushLog("info", text.scenario_started);
    const order = Array.isArray(profile.scenario_disable_order) ? profile.scenario_disable_order : [];
    for (const id of order) {{
      if (!state.enabled[id]) continue;
      state.enabled[id] = false;
      recomputeAll();
      render();
      pushLog("warn", `${{id}}: ${{text.log_disabled}}`);
      await sleep(700);
    }}
    if (state.status === "CRITICAL") {{
      pushLog("crit", text.scenario_critical);
    }}
    pushLog("info", text.scenario_finished);
    state.scenarioRunning = false;
  }}

  document.getElementById("ac-run-scenario")?.addEventListener("click", runScenario);
  document.getElementById("ac-disable-next")?.addEventListener("click", disableNext);
  document.getElementById("ac-enable-all")?.addEventListener("click", enableAll);
  document.getElementById("ac-controlled")?.addEventListener("click", controlledState);
  document.getElementById("ac-reset")?.addEventListener("click", resetAll);

  document.getElementById("ac-assess-mode")?.addEventListener("change", (event) => {{
    const value = String(event.target?.value || "demo");
    const jobInput = document.getElementById("ac-job-id");
    if (!jobInput) return;
    jobInput.disabled = value !== "job";
  }});

  recomputeAll();
  pushLog("info", text.initialized);
  render();

  const modeSelect = document.getElementById("ac-assess-mode");
  const jobInput = document.getElementById("ac-job-id");
  if (modeSelect && jobInput) {{
    jobInput.disabled = String(modeSelect.value || "demo") !== "job";
  }}
}})();
</script>
"""
    return render_layout(text["title"], body, auto_refresh_seconds=0, lang=lang)


def _render_assessment_block(
    lang: str,
    text: dict[str, str],
    assessment: JobControlAssessment | None,
    assessment_message: str,
) -> str:
    """Render static assessment panel for selected job mode."""
    if assessment is None:
        message = assessment_message or text["assessment_pending"]
        return f"<div class='ac-assess-result hint'>{escape(message)}</div>"

    rows = ""
    for signal in assessment.signals:
        evidence = ", ".join(signal.evidence) if signal.evidence else "-"
        rows += (
            "<tr>"
            f"<td>{escape(signal.component_id)}</td>"
            f"<td><span class='ac-tag ac-tag-{escape(signal.state)}'>{escape(signal.state)}</span></td>"
            f"<td>{escape(signal.reason)}</td>"
            f"<td><code>{escape(evidence)}</code></td>"
            "</tr>"
        )

    return (
        "<div class='ac-assess-result'>"
        f"<p><strong>{escape(text['assessment_for'])}:</strong> <code>{escape(assessment.job_id)}</code>"
        f" | <strong>{escape(text['status'])}:</strong> <code>{escape(assessment.job_status)}</code></p>"
        f"{_render_assessment_summary(text, assessment)}"
        f"{_render_assessment_links(lang, text, assessment)}"
        "<table>"
        "<thead><tr>"
        f"<th>{escape(text['component'])}</th>"
        f"<th>{escape(text['signal'])}</th>"
        f"<th>{escape(text['reason'])}</th>"
        f"<th>{escape(text['evidence'])}</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )


def _render_assessment_links(
    lang: str,
    text: dict[str, str],
    assessment: JobControlAssessment,
) -> str:
    """Render practical navigation links for selected assessed job."""
    job_id = str(assessment.job_id)
    job_link = with_lang("/job", lang, id=job_id)
    diagnostics_link = with_lang("/job-diagnostics", lang, id=job_id)
    links = [
        f"<a href='{escape(job_link)}'>{escape(text['open_job'])}</a>",
        f"<a href='{escape(diagnostics_link)}'>{escape(text['open_diagnostics'])}</a>",
    ]
    if str(assessment.job_status).strip().lower() in {"failed", "timeout", "stopped"}:
        bundle_link = with_lang("/job-bundle", lang, id=job_id)
        links.append(f"<a href='{escape(bundle_link)}'>{escape(text['download_bundle'])}</a>")
    return "<p>" + " | ".join(links) + "</p>"


def _render_assessment_summary(text: dict[str, str], assessment: JobControlAssessment) -> str:
    """Render compact summary for real-job assessment signals."""
    summary = assessment.summary
    counts = summary.counts
    failed = ", ".join(summary.failing_components) if summary.failing_components else "-"
    return (
        "<p>"
        f"<strong>{escape(text['overall'])}:</strong> "
        f"<span class='ac-tag ac-tag-{escape(summary.overall_state)}'>{escape(summary.overall_state)}</span> "
        f"| pass={int(counts.get('pass', 0))} "
        f"| fail={int(counts.get('fail', 0))} "
        f"| present={int(counts.get('present', 0))} "
        f"| unknown={int(counts.get('unknown', 0))} "
        f"| <strong>{escape(text['failing_components'])}:</strong> <code>{escape(failed)}</code>"
        "</p>"
    )


def _client_text(text: dict[str, str]) -> dict[str, str]:
    """Subset of localized strings used by client-side demo interactions."""
    keys = {
        "status_stable",
        "status_warning",
        "status_critical",
        "status_controlled",
        "initialized",
        "log_disabled",
        "log_enabled",
        "all_controls_enabled",
        "entered_controlled_state",
        "controlled_reset_needed",
        "reset_done",
        "scenario_started",
        "scenario_finished",
        "scenario_critical",
    }
    return {key: text[key] for key in keys}


def _page_text(lang: str) -> dict[str, str]:
    """Localized strings for agent control page."""
    en = {
        "title": "Agent Control / Quality Gate",
        "subtitle": "Integrated controllability demo for AI-agent execution inside the experimental stand.",
        "back_dashboard": "Back to dashboard",
        "quality_loop": "Quality Control Loop",
        "flow_task": "Task",
        "flow_agent": "AI agent",
        "flow_log": "Action log",
        "flow_qgate": "Quality gate",
        "flow_verify": "Fact check",
        "flow_decision": "Decision",
        "demo_title": "Demo Profile",
        "demo_warning": "Demonstration weights are synthetic and are not empirical validation.",
        "run_scenario": "Run scenario",
        "disable_next": "Disable next",
        "enable_all": "Enable all",
        "controlled_state": "Controlled state",
        "reset": "Reset",
        "real_assessment": "Real-job Assessment",
        "assessment_mode": "Assessment mode",
        "mode_demo": "Demo only",
        "mode_latest": "Assess latest job",
        "mode_latest_terminal": "Assess latest completed job",
        "mode_job": "Assess by job id",
        "job_id": "Job id",
        "run_assessment": "Assess",
        "assessment_pending": "Pick assessment mode and run check.",
        "assessment_for": "Assessment for job",
        "status": "Status",
        "component": "Component",
        "signal": "Signal",
        "reason": "Reason",
        "evidence": "Evidence",
        "overall": "Overall",
        "failing_components": "Failing components",
        "open_job": "Open job page",
        "open_diagnostics": "Open diagnostics",
        "download_bundle": "Download diagnostics bundle",
        "components_title": "Control Components",
        "metrics_title": "Process Metrics",
        "events_title": "Event Log",
        "status_stable": "All controls enabled. Process remains controllable.",
        "status_warning": "Some controls are disabled. Operator attention is required.",
        "status_critical": "Critical combination reached. Move to controlled state.",
        "status_controlled": "Execution is constrained in controlled state until manual decision.",
        "initialized": "Stand initialized. All controls are enabled.",
        "log_disabled": "disabled",
        "log_enabled": "enabled",
        "all_controls_enabled": "All controls are enabled.",
        "entered_controlled_state": "Execution moved to controlled state.",
        "controlled_reset_needed": "Reset is required to exit controlled state.",
        "reset_done": "Stand reset to baseline state.",
        "scenario_started": "Loss-of-control scenario started.",
        "scenario_finished": "Scenario finished.",
        "scenario_critical": "Critical status reached by scenario path.",
    }
    ru = {
        "title": "Управляемость агента / Quality Gate",
        "subtitle": "Интегрированный модуль оценки управляемости ИИ-агента в экспериментальном стенде.",
        "back_dashboard": "Назад к дашборду",
        "quality_loop": "Контур управления качеством",
        "flow_task": "Задание",
        "flow_agent": "ИИ-агент",
        "flow_log": "Журнал действий",
        "flow_qgate": "Quality gate",
        "flow_verify": "Проверка фактов",
        "flow_decision": "Решение",
        "demo_title": "Демо-профиль",
        "demo_warning": "Демонстрационные веса синтетические и не являются эмпирической валидацией.",
        "run_scenario": "Запустить сценарий",
        "disable_next": "Отключить следующий",
        "enable_all": "Включить всё",
        "controlled_state": "Controlled state",
        "reset": "Сброс",
        "real_assessment": "Оценка реального job",
        "assessment_mode": "Режим оценки",
        "mode_demo": "Только демо",
        "mode_latest": "Оценить последний job",
        "mode_latest_terminal": "Оценить последний завершенный job",
        "mode_job": "Оценить по id",
        "job_id": "ID job",
        "run_assessment": "Оценить",
        "assessment_pending": "Выберите режим оценки и запустите проверку.",
        "assessment_for": "Оценка для job",
        "status": "Статус",
        "component": "Компонент",
        "signal": "Сигнал",
        "reason": "Причина",
        "evidence": "Подтверждение",
        "overall": "Итог",
        "failing_components": "Проблемные компоненты",
        "open_job": "Открыть страницу job",
        "open_diagnostics": "Открыть diagnostics",
        "download_bundle": "Скачать diagnostics bundle",
        "components_title": "Контрольные компоненты",
        "metrics_title": "Метрики процесса",
        "events_title": "Журнал событий",
        "status_stable": "Все контроли включены. Процесс управляем.",
        "status_warning": "Часть контролей отключена. Нужен контроль оператора.",
        "status_critical": "Критическая комбинация. Требуется controlled state.",
        "status_controlled": "В controlled state выполнение ограничено до решения оператора.",
        "initialized": "Стенд инициализирован. Все контроли активны.",
        "log_disabled": "отключен",
        "log_enabled": "включен",
        "all_controls_enabled": "Все контроли включены.",
        "entered_controlled_state": "Выполнение переведено в controlled state.",
        "controlled_reset_needed": "Для выхода из controlled state нужен сброс.",
        "reset_done": "Стенд сброшен к базовому состоянию.",
        "scenario_started": "Сценарий потери управляемости запущен.",
        "scenario_finished": "Сценарий завершен.",
        "scenario_critical": "По сценарию достигнут критический статус.",
    }
    return ru if lang == "ru" else en

