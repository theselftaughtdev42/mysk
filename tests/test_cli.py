"""Tests for the root CLI app — the logging init wiring."""

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
