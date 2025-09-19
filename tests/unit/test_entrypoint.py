"""Tests for package entrypoint and lightweight CLI helpers."""

import importlib.metadata
import runpy
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from commandrex import __main__ as entry
from commandrex.main import app, get_version


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Typer CLI runner for invoking the app."""
    return CliRunner()


def test_entrypoint_invokes_app(monkeypatch):
    """Running the module as a script should invoke the Typer app."""
    called = False

    def fake_app() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("commandrex.main.app", fake_app)

    # run_module executes __main__ with run_name="__main__"
    runpy.run_module("commandrex.__main__", run_name="__main__")

    assert called is True


def test_main_function_delegates_to_app(monkeypatch):
    """Calling entry.main should delegate to the Typer application."""
    fake = MagicMock()
    monkeypatch.setattr(entry, "app", fake)

    entry.main()

    fake.assert_called_once_with()


def test_get_version_default(monkeypatch):
    """When the package metadata is missing, fallback version is returned."""

    def raise_missing(*_, **__):
        raise importlib.metadata.PackageNotFoundError("missing")

    monkeypatch.setattr(importlib.metadata, "version", raise_missing)

    assert get_version() == "0.2"


def test_cli_version_option_uses_get_version(monkeypatch, runner):
    """The --version option should print the resolved version and exit successfully."""
    monkeypatch.setattr("commandrex.main.get_version", lambda: "1.2.3")

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "1.2.3" in result.stdout


def test_cli_help_option_uses_custom_renderer(monkeypatch, runner):
    """The --help flag should invoke the custom help renderer and exit."""
    called = False

    def fake_help() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("commandrex.main.show_main_help", fake_help)

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert called is True
