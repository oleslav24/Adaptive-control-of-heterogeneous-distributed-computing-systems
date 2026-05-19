"""Unit tests for web CLI command builder."""

from project.web.commands import build_run_command


def test_build_run_command_defaults() -> None:
    """Empty form builds single-run command with default config."""
    command = build_run_command(
        {},
        default_config="custom.yaml",
        python_executable="python",
    )
    assert command == [
        "python",
        "-m",
        "project.experiments.run",
        "--config",
        "custom.yaml",
    ]


def test_build_run_command_single_with_overrides_and_flags() -> None:
    """Single mode keeps optional switches and scalar overrides."""
    form = {
        "mode": ["single"],
        "config": ["config.yaml"],
        "algorithm": ["greedy"],
        "scenario": ["dynamic-load"],
        "llm_provider": ["mock"],
        "output_dir": ["outputs/test"],
        "log_level": ["DEBUG"],
        "disable_intelligence": ["on"],
        "no_csv": ["true"],
    }
    command = build_run_command(form, python_executable="python")
    assert command == [
        "python",
        "-m",
        "project.experiments.run",
        "--config",
        "config.yaml",
        "--algorithm",
        "greedy",
        "--scenario",
        "dynamic-load",
        "--llm-provider",
        "mock",
        "--output-dir",
        "outputs/test",
        "--log-level",
        "DEBUG",
        "--disable-intelligence",
        "--no-csv",
    ]


def test_build_run_command_compare_filters_and_deduplicates_algorithms() -> None:
    """Compare mode keeps algorithm order, removes duplicates, filters unknown."""
    form = {
        "mode": ["compare"],
        "compare_algorithms": ["round-robin", "min-load", "round-robin", "bad"],
    }
    command = build_run_command(
        form,
        default_config="config.yaml",
        python_executable="python",
    )
    assert command[-3:] == ["--compare", "--compare-algorithms", "round-robin,min-load"]


def test_build_run_command_accepts_carbon_aware_algorithm() -> None:
    """Single mode should pass through carbon-aware algorithm value."""
    command = build_run_command(
        {
            "mode": ["single"],
            "algorithm": ["carbon-aware"],
        },
        python_executable="python",
    )
    assert "--algorithm" in command
    assert command[command.index("--algorithm") + 1] == "carbon-aware"


def test_build_run_command_batch_parses_lists_and_clamps_runs() -> None:
    """Batch mode parses comma-list fallbacks and clamps batch-runs to minimum."""
    form = {
        "mode": ["batch"],
        "batch_scenarios": ["static,peak-load,bad"],
        "batch_algorithms": ["greedy,min-load,unknown"],
        "batch_runs": ["0"],
        "batch_save_runs": ["yes"],
        "batch_keep_adaptive": ["1"],
    }
    command = build_run_command(form, python_executable="python")
    assert "--batch" in command
    assert "--batch-scenarios" in command
    assert "static,peak-load" in command
    assert "--batch-algorithms" in command
    assert "greedy,min-load" in command
    assert "--batch-runs" in command
    assert command[command.index("--batch-runs") + 1] == "1"
    assert "--batch-save-runs" in command
    assert "--batch-keep-adaptive" in command


def test_build_run_command_publication_and_repro_modes() -> None:
    """Publication and repro-check modes append expected switches."""
    publication = build_run_command(
        {
            "mode": ["publication"],
            "study_quick": ["on"],
            "study_seeds": ["101,102"],
        },
        python_executable="python",
    )
    assert publication[-4:] == [
        "--publication-study",
        "--study-quick",
        "--study-seeds",
        "101,102",
    ]

    repro = build_run_command(
        {
            "mode": ["repro-check"],
            "repro_runs": ["1"],
        },
        python_executable="python",
    )
    assert repro[-3:] == ["--repro-check", "--repro-runs", "2"]


def test_build_run_command_carbon_study_mode() -> None:
    """Carbon-study mode should map quick/seeds to dedicated CLI flags."""
    command = build_run_command(
        {
            "mode": ["carbon-study"],
            "study_quick": ["on"],
            "study_seeds": ["55-57"],
        },
        python_executable="python",
    )
    assert command[-4:] == [
        "--carbon-study",
        "--carbon-quick",
        "--carbon-seeds",
        "55-57",
    ]


def test_build_run_command_chapter10_mode() -> None:
    """Chapter10 mode should map shared study fields to chapter10 CLI flags."""
    chapter10 = build_run_command(
        {
            "mode": ["chapter10"],
            "study_quick": ["on"],
            "study_seeds": ["42,43"],
        },
        python_executable="python",
    )
    assert chapter10[-4:] == [
        "--chapter10",
        "--chapter10-quick",
        "--chapter10-seeds",
        "42,43",
    ]


def test_build_run_command_paper_bundle_mode() -> None:
    """Paper-bundle mode should map study fields and bundle name switches."""
    command = build_run_command(
        {
            "mode": ["paper-bundle"],
            "study_quick": ["on"],
            "study_seeds": ["50-52"],
            "paper_bundle_name": ["ase_bundle_v1"],
        },
        python_executable="python",
    )
    assert command[-6:] == [
        "--paper-bundle",
        "--chapter10-quick",
        "--chapter10-seeds",
        "50-52",
        "--paper-bundle-name",
        "ase_bundle_v1",
    ]
