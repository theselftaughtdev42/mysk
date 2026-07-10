"""Tests for the root CLI app — the logging init wiring and --version flag."""

from typer.testing import CliRunner

from mysk import cli
from mysk.cli import app
from mysk.commands import library as library_cmd

runner = CliRunner()


def test_root_callback_configures_logging_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "configure_logging", lambda: calls.append(1))
    monkeypatch.setattr(library_cmd, "skill_library_path", lambda: tmp_path / "skills")
    result = runner.invoke(app, ["library"])
    assert result.exit_code == 0
    assert calls == [1]


def test_version_flag_prints_installed_version(monkeypatch):
    monkeypatch.setattr(cli, "version", lambda name: "9.9.9" if name == "mysk" else "")
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == "mysk 9.9.9\n"
