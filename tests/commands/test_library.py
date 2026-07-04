from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import library as library_cmd

runner = CliRunner()


def test_library_prints_skill_library_path(monkeypatch, tmp_path):
    monkeypatch.setattr(library_cmd, "skill_library_path", lambda: tmp_path / "skills")
    result = runner.invoke(app, ["library"])
    assert result.exit_code == 0
    assert str(tmp_path / "skills") in result.output


def test_library_path_goes_to_stdout(monkeypatch, tmp_path):
    monkeypatch.setattr(library_cmd, "skill_library_path", lambda: tmp_path / "skills")
    result = runner.invoke(app, ["library"])
    assert str(tmp_path / "skills") in result.stdout


def test_library_path_with_brackets_is_printed_verbatim(monkeypatch, tmp_path):
    bracketed = tmp_path / "sk[ill]s"
    monkeypatch.setattr(library_cmd, "skill_library_path", lambda: bracketed)
    result = runner.invoke(app, ["library"])
    assert result.exit_code == 0
    assert str(bracketed) in result.stdout
