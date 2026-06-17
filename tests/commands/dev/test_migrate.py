from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands.dev import migrate

runner = CliRunner()


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def _run(monkeypatch, repo: Path, select=lambda paths: paths, extra_args=()):
    monkeypatch.setattr(migrate, "find_source_repo", lambda: repo)
    monkeypatch.setattr(migrate, "_prompt_for_skills", select)
    return runner.invoke(app, ["dev", "migrate", *extra_args])


def test_errors_when_run_outside_the_source_repo(monkeypatch):
    monkeypatch.setattr(migrate, "find_source_repo", lambda: None)
    result = runner.invoke(app, ["dev", "migrate"])
    assert result.exit_code != 0
    assert "source repo" in result.output.lower()


def test_unmigrated_skill_gets_init_block(monkeypatch, tmp_path):
    path = _skill(tmp_path, "foo", "name: foo\ndescription: does a thing\n", body="# Foo\n\nBody stays put.\n")
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    content = path.read_text()
    assert "state: init" in content
    assert "name: foo" in content
    assert "Body stays put." in content


def test_already_compliant_skill_is_left_untouched(monkeypatch, tmp_path):
    path = _skill(tmp_path, "bar", "name: bar\ndescription: ready\nmysk:\n  state: active\n", body="# Bar\n")
    before = path.read_text()
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert path.read_text() == before


def test_extra_frontmatter_keys_survive_migration(monkeypatch, tmp_path):
    path = _skill(tmp_path, "setup", "name: setup\ndescription: scaffolds\ndisable-model-invocation: true\n", body="# Setup\n")
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    content = path.read_text()
    assert "disable-model-invocation: true" in content
    assert "state: init" in content


def test_dry_run_writes_nothing_but_reports_the_diff(monkeypatch, tmp_path):
    path = _skill(tmp_path, "foo", "name: foo\ndescription: does a thing\n", body="# Foo\n")
    before = path.read_text()
    result = _run(monkeypatch, tmp_path, extra_args=("--dry-run",))
    assert result.exit_code == 0
    assert path.read_text() == before
    assert "state: init" in result.output
    assert "would migrate 1" in result.output


def test_unselected_skills_are_skipped(monkeypatch, tmp_path):
    path = _skill(tmp_path, "foo", "name: foo\ndescription: d\n", body="# Foo\n")
    before = path.read_text()
    result = _run(monkeypatch, tmp_path, select=lambda paths: [])
    assert result.exit_code == 0
    assert path.read_text() == before
    assert "skipped 1" in result.output


def test_only_selected_skill_is_migrated(monkeypatch, tmp_path):
    chosen = _skill(tmp_path, "a", "name: a\ndescription: d\n", body="# A\n")
    left = _skill(tmp_path, "b", "name: b\ndescription: d\n", body="# B\n")
    result = _run(monkeypatch, tmp_path, select=lambda paths: [chosen])
    assert result.exit_code == 0
    assert "state: init" in chosen.read_text()
    assert "mysk" not in left.read_text()


def test_summary_counts_across_a_mixed_directory(monkeypatch, tmp_path):
    _skill(tmp_path, "fresh", "name: fresh\ndescription: d\n", body="# F\n")
    _skill(tmp_path, "owned", "name: owned\ndescription: d\nmysk:\n  state: active\n", body="# O\n")
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "migrated 1" in result.output
    assert "already compliant 1" in result.output
