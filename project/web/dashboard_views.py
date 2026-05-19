"""Dashboard page rendering helpers for the web UI."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Sequence

from project.web.i18n import (
    ALGORITHM_LABELS,
    ALGORITHM_OPTIONS,
    DEFAULT_BATCH_SCENARIOS,
    MODE_LABELS,
    MODE_OPTIONS,
    SCENARIO_LABELS,
    SCENARIO_OPTIONS,
    catalog_label,
    default_select_label,
    tr,
)
from project.web.job_views import job_row_html
from project.web.layout import render_layout
from project.web.routing import language_switcher, with_lang


def build_dashboard_html(
    lang: str,
    jobs: Sequence[object],
    *,
    workspace_root: Path,
    default_config: str,
) -> str:
    """Build full dashboard HTML document."""
    running_rows = [job for job in jobs if getattr(job, "status", "") == "running"]
    recent_rows = list(jobs)[:20]

    running_html = "".join(job_row_html(job, lang) for job in running_rows) or (
        f"<tr><td colspan='7'>{escape(tr(lang, 'no_active_jobs'))}</td></tr>"
    )
    recent_html = "".join(job_row_html(job, lang) for job in recent_rows) or (
        f"<tr><td colspan='7'>{escape(tr(lang, 'no_runs_started'))}</td></tr>"
    )

    mode_options = "".join(
        f"<option value='{escape(mode)}'>{escape(catalog_label(MODE_LABELS, lang, mode, mode))}</option>"
        for mode in MODE_OPTIONS
    )
    algorithm_options = "".join(
        f"<option value='{escape(name)}'>{escape(catalog_label(ALGORITHM_LABELS, lang, name, name) if name else default_select_label(lang))}</option>"
        for name in ALGORITHM_OPTIONS
    )
    scenario_options = "".join(
        f"<option value='{escape(name)}'>{escape(catalog_label(SCENARIO_LABELS, lang, name, name) if name else default_select_label(lang))}</option>"
        for name in SCENARIO_OPTIONS
    )
    compare_default_checked = {"round-robin", "min-load", "greedy"}
    compare_flags = "".join(
        (
            "<label>"
            f"<input type='checkbox' name='compare_algorithms' value='{escape(name)}' "
            f"{'checked' if name in compare_default_checked else ''} /> "
            f"{escape(catalog_label(ALGORITHM_LABELS, lang, name, name))}"
            "</label>"
        )
        for name in ALGORITHM_OPTIONS
        if name
    )
    batch_default_checked = {"static", "peak-load"}
    batch_scenario_flags = "".join(
        (
            "<label>"
            f"<input type='checkbox' name='batch_scenarios' value='{escape(name)}' "
            f"{'checked' if name in batch_default_checked else ''} /> "
            f"{escape(catalog_label(SCENARIO_LABELS, lang, name, name))}"
            "</label>"
        )
        for name in SCENARIO_OPTIONS
        if name
    )
    batch_algorithm_default_checked = {"round-robin", "min-load", "greedy"}
    batch_algorithm_flags = "".join(
        (
            "<label>"
            f"<input type='checkbox' name='batch_algorithms' value='{escape(name)}' "
            f"{'checked' if name in batch_algorithm_default_checked else ''} /> "
            f"{escape(catalog_label(ALGORITHM_LABELS, lang, name, name))}"
            "</label>"
        )
        for name in ALGORITHM_OPTIONS
        if name
    )
    default_compare_count = len(compare_default_checked)
    default_batch_scenario_count = len(DEFAULT_BATCH_SCENARIOS)
    default_batch_algorithm_count = len(batch_algorithm_default_checked)
    switcher = language_switcher(lang, "/")

    body = f"""
<header class="topbar">
  <div>{switcher}</div>
</header>
<h1>{escape(tr(lang, "console_title"))}</h1>
<p>{escape(tr(lang, "workspace"))}: <code>{escape(str(workspace_root))}</code></p>
<div class="grid">
  <section class="card">
    <h2>{escape(tr(lang, "start_experiment"))}</h2>
    <form method="post" action="/run" id="run-form"
      data-default-compare-count="{default_compare_count}"
      data-default-batch-scenario-count="{default_batch_scenario_count}"
      data-default-batch-algorithm-count="{default_batch_algorithm_count}">
      <input type="hidden" name="lang" value="{escape(lang)}" />

      <div class="form-field" data-field="mode">
        <label>{escape(tr(lang, "mode"))}</label>
        <select name="mode">{mode_options}</select>
      </div>

      <div class="form-field" data-field="config_path">
        <label>{escape(tr(lang, "config_path"))}</label>
        <input type="text" name="config" value="{escape(default_config)}" />
      </div>

      <div class="form-field" data-field="algorithm">
        <label>{escape(tr(lang, "algorithm"))}</label>
        <select name="algorithm">{algorithm_options}</select>
      </div>

      <div class="form-field" data-field="scenario">
        <label>{escape(tr(lang, "scenario"))}</label>
        <select name="scenario">{scenario_options}</select>
      </div>

      <div class="form-field" data-field="llm_provider">
        <label>{escape(tr(lang, "llm_provider"))}</label>
        <input type="text" name="llm_provider" value="" placeholder="auto|openai|mock" />
      </div>

      <div class="form-field" data-field="compare_algorithms">
        <label>{escape(tr(lang, "compare_algorithms"))}</label>
        <div class="choice-flags">{compare_flags}</div>
      </div>

      <div class="form-field" data-field="batch_scenarios">
        <label>{escape(tr(lang, "batch_scenarios"))}</label>
        <div class="choice-flags">{batch_scenario_flags}</div>
      </div>

      <div class="form-field" data-field="batch_algorithms">
        <label>{escape(tr(lang, "batch_algorithms"))}</label>
        <div class="choice-flags">{batch_algorithm_flags}</div>
      </div>

      <div class="form-field" data-field="batch_runs">
        <label>{escape(tr(lang, "batch_runs"))}</label>
        <input type="number" name="batch_runs" value="3" min="1" />
      </div>

      <div class="form-field" data-field="repro_runs">
        <label>{escape(tr(lang, "repro_runs"))}</label>
        <input type="number" name="repro_runs" value="3" min="2" />
      </div>

      <div class="form-field" data-field="job_timeout_seconds">
        <label>{escape(tr(lang, "job_timeout_seconds"))}</label>
        <input type="number" name="job_timeout_seconds" value="3600" min="10" max="86400" />
      </div>

      <div class="form-field" data-field="study_seeds">
        <label>{escape(tr(lang, "study_seeds"))}</label>
        <input type="text" name="study_seeds" value="42-71" />
      </div>

      <div class="form-field" data-field="paper_bundle_name">
        <label>{escape(tr(lang, "paper_bundle_name"))}</label>
        <input type="text" name="paper_bundle_name" value="paper_bundle" />
      </div>

      <div class="form-field" data-field="output_dir_override">
        <label>{escape(tr(lang, "output_dir_override"))}</label>
        <input type="text" name="output_dir" value="" placeholder="outputs" />
      </div>

      <div class="form-field" data-field="log_level">
        <label>{escape(tr(lang, "log_level"))}</label>
        <input type="text" name="log_level" value="" placeholder="INFO" />
      </div>

      <div class="checks">
        <label class="check-item" data-check="disable_intelligence"><input type="checkbox" name="disable_intelligence" /> {escape(tr(lang, "disable_intelligence"))}</label>
        <label class="check-item" data-check="disable_llm"><input type="checkbox" name="disable_llm" /> {escape(tr(lang, "disable_llm"))}</label>
        <label class="check-item" data-check="no_plots"><input type="checkbox" name="no_plots" /> {escape(tr(lang, "no_plots"))}</label>
        <label class="check-item" data-check="no_csv"><input type="checkbox" name="no_csv" /> {escape(tr(lang, "no_csv"))}</label>
        <label class="check-item" data-check="batch_save_runs"><input type="checkbox" name="batch_save_runs" /> {escape(tr(lang, "batch_save_runs"))}</label>
        <label class="check-item" data-check="batch_keep_adaptive"><input type="checkbox" name="batch_keep_adaptive" /> {escape(tr(lang, "batch_keep_adaptive"))}</label>
        <label class="check-item" data-check="study_quick"><input type="checkbox" name="study_quick" checked /> {escape(tr(lang, "study_quick"))}</label>
      </div>
      <div class="run-estimator" id="run-estimator">
        <p class="run-estimator-title">{escape(tr(lang, "expected_runs_title"))}</p>
        <p class="hint" id="expected-runs-total">{escape(tr(lang, "expected_runs_title"))}: 1</p>
        <p class="hint" id="expected-runs-formula"></p>
      </div>
      <button type="submit">{escape(tr(lang, "run"))}</button>
    </form>
    <p class="hint">{escape(tr(lang, "mode_mapping"))}: <code>single</code>, <code>compare</code>, <code>batch</code>,
    <code>publication</code>, <code>chapter10</code>, <code>paper-bundle</code>, <code>ab-intelligence</code>, <code>ab-llm</code>, <code>repro-check</code>.</p>
    <script>
    (() => {{
      const form = document.getElementById("run-form");
      if (!form) return;
      const totalEl = document.getElementById("expected-runs-total");
      const formulaEl = document.getElementById("expected-runs-formula");
      if (!totalEl || !formulaEl) return;
      const lang = {json.dumps(lang)};
      const i18n = {{
        title: {json.dumps(tr(lang, "expected_runs_title"))},
        formula: {json.dumps(tr(lang, "expected_runs_formula"))},
        fallback: {json.dumps(tr(lang, "expected_runs_fallback"))},
        defaultLabel: (lang === "ru" ? "РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ" : "default"),
        unknown: {json.dumps(tr(lang, "unknown"))}
      }};

      const defaultCompareCount = Math.max(1, Number(form.dataset.defaultCompareCount || 3));
      const defaultBatchScenarioCount = Math.max(1, Number(form.dataset.defaultBatchScenarioCount || 5));
      const defaultBatchAlgorithmCount = Math.max(1, Number(form.dataset.defaultBatchAlgorithmCount || 3));

      const alwaysFields = new Set([
        "mode",
        "config_path",
        "llm_provider",
        "job_timeout_seconds",
        "output_dir_override",
        "log_level"
      ]);
      const modeFields = {{
        "single": ["algorithm", "scenario"],
        "compare": ["scenario", "compare_algorithms"],
        "batch": ["batch_scenarios", "batch_algorithms", "batch_runs"],
        "publication": ["study_seeds"],
        "paper-bundle": ["study_seeds", "paper_bundle_name"],
        "chapter10": ["study_seeds"],
        "ab-intelligence": ["algorithm", "scenario"],
        "ab-llm": ["algorithm", "scenario"],
        "repro-check": ["algorithm", "scenario", "repro_runs"]
      }};
      const trackedFields = [
        "mode", "config_path", "algorithm", "scenario", "llm_provider",
        "compare_algorithms", "batch_scenarios", "batch_algorithms",
        "batch_runs", "repro_runs", "job_timeout_seconds", "study_seeds",
        "paper_bundle_name", "output_dir_override", "log_level"
      ];

      const alwaysChecks = new Set(["disable_intelligence", "disable_llm", "no_plots", "no_csv"]);
      const modeChecks = {{
        "single": [],
        "compare": [],
        "batch": ["batch_save_runs", "batch_keep_adaptive"],
        "publication": ["study_quick"],
        "paper-bundle": ["study_quick"],
        "chapter10": ["study_quick"],
        "ab-intelligence": [],
        "ab-llm": [],
        "repro-check": []
      }};
      const trackedChecks = [
        "disable_intelligence", "disable_llm", "no_plots", "no_csv",
        "batch_save_runs", "batch_keep_adaptive", "study_quick"
      ];

      function setSectionVisible(node, visible) {{
        if (!node) return;
        node.classList.toggle("is-hidden", !visible);
        const controls = node.querySelectorAll("input, select, textarea");
        for (const control of controls) {{
          if (control.type === "hidden") continue;
          control.disabled = !visible;
        }}
      }}

      function updateModeUI() {{
        const mode = String(form.querySelector('select[name="mode"]')?.value || "single");
        const visibleFields = new Set(alwaysFields);
        for (const key of (modeFields[mode] || [])) {{
          visibleFields.add(key);
        }}
        for (const key of trackedFields) {{
          const nodes = form.querySelectorAll(`[data-field="${{key}}"]`);
          for (const node of nodes) {{
            setSectionVisible(node, visibleFields.has(key));
          }}
        }}

        const visibleChecks = new Set(alwaysChecks);
        for (const key of (modeChecks[mode] || [])) {{
          visibleChecks.add(key);
        }}
        for (const key of trackedChecks) {{
          const nodes = form.querySelectorAll(`[data-check="${{key}}"]`);
          for (const node of nodes) {{
            setSectionVisible(node, visibleChecks.has(key));
          }}
        }}
      }}

      function checkedCount(name) {{
        return form.querySelectorAll(`input[name="${{name}}"]:checked:not(:disabled)`).length;
      }}

      function parseIntSafe(value, fallback, minValue = 1) {{
        const parsed = Number.parseInt(String(value ?? "").trim(), 10);
        if (!Number.isFinite(parsed)) return fallback;
        return Math.max(minValue, parsed);
      }}

      function parseSeeds(raw) {{
        const text = String(raw ?? "").trim();
        if (!text) {{
          const seeds = [];
          for (let seed = 42; seed <= 71; seed += 1) seeds.push(seed);
          return seeds;
        }}
        if (text.includes("-") && !text.includes(",")) {{
          const parts = text.split("-", 2).map((item) => item.trim());
          if (parts.length === 2 && /^\\d+$/.test(parts[0]) && /^\\d+$/.test(parts[1])) {{
            let start = Number.parseInt(parts[0], 10);
            let end = Number.parseInt(parts[1], 10);
            if (end < start) {{
              const tmp = start;
              start = end;
              end = tmp;
            }}
            const seeds = [];
            for (let seed = start; seed <= end; seed += 1) seeds.push(seed);
            return seeds;
          }}
        }}
        const values = [];
        for (const part of text.split(",")) {{
          const cleaned = part.trim();
          if (!/^\\d+$/.test(cleaned)) continue;
          const seed = Number.parseInt(cleaned, 10);
          if (!values.includes(seed)) values.push(seed);
        }}
        if (values.length) return values;
        const fallback = [];
        for (let seed = 42; seed <= 71; seed += 1) fallback.push(seed);
        return fallback;
      }}

      function updateExpectedRuns() {{
        const mode = String(form.querySelector('select[name="mode"]')?.value || "single");
        let total = 1;
        let formula = "";
        let usedFallback = false;

        if (mode === "single") {{
          total = 1;
          formula = "single = 1";
        }} else if (mode === "compare") {{
          const selectedAlgorithms = checkedCount("compare_algorithms");
          const algorithmCount = selectedAlgorithms > 0 ? selectedAlgorithms : defaultCompareCount;
          usedFallback = selectedAlgorithms === 0;
          total = algorithmCount;
          formula = `compare = ${{algorithmCount}}`;
        }} else if (mode === "batch") {{
          const repeats = parseIntSafe(form.querySelector('input[name="batch_runs"]')?.value, 3, 1);
          const selectedScenarios = checkedCount("batch_scenarios");
          const selectedAlgorithms = checkedCount("batch_algorithms");
          const scenarioCount = selectedScenarios > 0 ? selectedScenarios : defaultBatchScenarioCount;
          const algorithmCount = selectedAlgorithms > 0 ? selectedAlgorithms : defaultBatchAlgorithmCount;
          usedFallback = selectedScenarios === 0 || selectedAlgorithms === 0;
          total = repeats * scenarioCount * algorithmCount;
          formula = `batch = ${{repeats}} x ${{scenarioCount}} x ${{algorithmCount}} = ${{total}}`;
        }} else if (mode === "publication" || mode === "chapter10" || mode === "paper-bundle") {{
          const seeds = parseSeeds(form.querySelector('input[name="study_seeds"]')?.value || "");
          const quick = Boolean(form.querySelector('input[name="study_quick"]')?.checked);
          const runsPerSeed = quick ? 25 : 33;
          total = seeds.length * runsPerSeed;
          formula = `${{mode}} = ${{seeds.length}} x ${{runsPerSeed}} = ${{total}}`;
        }} else if (mode === "ab-intelligence" || mode === "ab-llm") {{
          total = 2;
          formula = `${{mode}} = 2`;
        }} else if (mode === "repro-check") {{
          const reproRuns = parseIntSafe(form.querySelector('input[name="repro_runs"]')?.value, 3, 2);
          total = reproRuns;
          formula = `repro-check = ${{reproRuns}}`;
        }} else {{
          total = 1;
          formula = `${{i18n.unknown}} = 1`;
        }}

        totalEl.textContent = `${{i18n.title}}: ${{total}}`;
        formulaEl.textContent = `${{i18n.formula}}: ${{formula}}${{usedFallback ? ` (${{i18n.fallback}})` : ""}}`;
      }}

      function refreshRunUi() {{
        updateModeUI();
        updateExpectedRuns();
      }}

      form.addEventListener("change", refreshRunUi);
      form.addEventListener("input", refreshRunUi);
      refreshRunUi();
    }})();
    </script>
  </section>

  <section class="card">
    <h2>{escape(tr(lang, "quick_links"))}</h2>
    <ul>
      <li><a href="{escape(with_lang('/files', lang, path='outputs'))}">{escape(tr(lang, "browse_outputs"))}</a></li>
      <li><a href="{escape(with_lang('/files', lang, path='docs'))}">{escape(tr(lang, "browse_docs"))}</a></li>
      <li><a href="{escape(with_lang('/files', lang, path='config.yaml'))}">{escape(tr(lang, "open_config"))}</a></li>
      <li><a href="/health">{escape(tr(lang, "health_check"))}</a></li>
    </ul>
  </section>
</div>

<section class="card">
  <h2>{escape(tr(lang, "running_jobs"))}</h2>
  <table>
    <thead>
      <tr><th>{escape(tr(lang, "id"))}</th><th>{escape(tr(lang, "status"))}</th><th>{escape(tr(lang, "started"))}</th><th>{escape(tr(lang, "finished"))}</th><th>{escape(tr(lang, "rc"))}</th><th>{escape(tr(lang, "command"))}</th><th>{escape(tr(lang, "actions"))}</th></tr>
    </thead>
    <tbody>{running_html}</tbody>
  </table>
</section>

<section class="card">
  <h2>{escape(tr(lang, "recent_jobs"))}</h2>
  <table>
    <thead>
      <tr><th>{escape(tr(lang, "id"))}</th><th>{escape(tr(lang, "status"))}</th><th>{escape(tr(lang, "started"))}</th><th>{escape(tr(lang, "finished"))}</th><th>{escape(tr(lang, "rc"))}</th><th>{escape(tr(lang, "command"))}</th><th>{escape(tr(lang, "actions"))}</th></tr>
    </thead>
    <tbody>{recent_html}</tbody>
  </table>
</section>
"""
    return render_layout(tr(lang, "console_title"), body, auto_refresh_seconds=0, lang=lang)
