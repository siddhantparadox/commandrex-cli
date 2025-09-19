"""Focused tests for the explain command CLI wiring."""

from typer.testing import CliRunner

from commandrex.main import app


def test_explain_requires_command():
    """Explain without arguments should exit with an error message."""
    runner = CliRunner()

    result = runner.invoke(app, ["explain"])

    assert result.exit_code == 1
    assert "No command provided" in result.stdout


def test_explain_rejects_invalid_api_key():
    """Passing an invalid API key should abort before calling the API."""
    runner = CliRunner()

    result = runner.invoke(app, ["explain", "--api-key", "bogus", "ls"])

    assert result.exit_code == 1
    assert "Invalid API key format" in result.stdout
