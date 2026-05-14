"""Unit tests for server-side web run form validation."""

from pathlib import Path

from project.web.validation import validate_start_run_form


def test_validate_start_run_form_accepts_minimal_valid_payload() -> None:
    """Valid single-run payload should pass without errors."""
    errors = validate_start_run_form(
        {
            "mode": ["single"],
            "config": ["config.yaml"],
        },
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert errors == []


def test_validate_start_run_form_rejects_invalid_mode() -> None:
    """Unknown mode should be reported as validation error."""
    errors = validate_start_run_form(
        {
            "mode": ["bad-mode"],
            "config": ["config.yaml"],
        },
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert any("Invalid mode" in item for item in errors)


def test_validate_start_run_form_rejects_timeout_out_of_bounds() -> None:
    """Timeout should stay within bounded safe range."""
    errors = validate_start_run_form(
        {
            "mode": ["single"],
            "config": ["config.yaml"],
            "job_timeout_seconds": ["1"],
        },
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert any("Job timeout must be between 10 and 86400" in item for item in errors)


def test_validate_start_run_form_rejects_path_escape() -> None:
    """Config path should not escape workspace root."""
    errors = validate_start_run_form(
        {
            "mode": ["single"],
            "config": ["..\\outside-config.yaml"],
        },
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert any("inside workspace" in item for item in errors)


def test_validate_start_run_form_rejects_bad_seed_expression() -> None:
    """Publication mode should reject malformed study seeds expression."""
    errors = validate_start_run_form(
        {
            "mode": ["publication"],
            "config": ["config.yaml"],
            "study_seeds": ["42,a,44"],
        },
        workspace_root=Path(".").resolve(),
        default_config="config.yaml",
    )
    assert any("Study seeds" in item for item in errors)
