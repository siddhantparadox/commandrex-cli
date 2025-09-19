"""Focused tests for the translate command CLI wiring."""

from typer.testing import CliRunner

from commandrex.main import app


def test_translate_requires_query(monkeypatch):
    """Invoking translate without a query should fail gracefully."""
    runner = CliRunner()

    result = runner.invoke(app, ["translate"])

    assert result.exit_code == 1
    assert "No query provided" in result.stdout


def test_translate_rejects_invalid_api_key(monkeypatch):
    """Invalid --api-key values should trigger an early exit."""
    runner = CliRunner()

    result = runner.invoke(app, ["translate", "--api-key", "invalid", "show", "files"])

    assert result.exit_code == 1
    assert "Invalid API key format" in result.stdout
