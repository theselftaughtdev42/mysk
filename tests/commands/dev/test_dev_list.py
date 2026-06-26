from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands.dev import list as dev_list_mod

runner = CliRunner()


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def _run(monkeypatch, repo: Path):
    monkeypatch.setattr(dev_list_mod, "skill_library", lambda: repo / "skills")
    return runner.invoke(app, ["dev", "list"])


def test_empty_skills_directory_shows_empty_state(monkeypatch, tmp_path):
    (tmp_path / "skills").mkdir()
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "no skills" in result.output.lower()


def test_skill_name_appears_in_output(monkeypatch, tmp_path):
    _skill(
        tmp_path,
        "my-skill",
        "name: my-skill\ndescription: d\nmysk:\n  state: active\n",
    )
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "my-skill" in result.output


def test_active_skill_shows_active_status(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(monkeypatch, tmp_path)
    assert "active" in result.output


def test_experimental_skill_shows_experimental_status(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: experimental\n")
    result = _run(monkeypatch, tmp_path)
    assert "experimental" in result.output


def test_deprecated_skill_shows_deprecated_status(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: deprecated\n")
    result = _run(monkeypatch, tmp_path)
    assert "deprecated" in result.output


def test_self_authored_skill_shows_self_authored(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(monkeypatch, tmp_path)
    assert "self-authored" in result.output


def test_imported_skill_shows_imported(monkeypatch, tmp_path):
    frontmatter = (
        "name: foo\ndescription: d\nmysk:\n  state: active\n  "
        "source: https://example.com\n  modified: false\n"
    )
    _skill(
        tmp_path,
        "foo",
        frontmatter,
    )
    result = _run(monkeypatch, tmp_path)
    assert "imported" in result.output


def test_modified_imported_skill_shows_modified_flag(monkeypatch, tmp_path):
    frontmatter = (
        "name: foo\ndescription: d\nmysk:\n  state: active\n  "
        "source: https://example.com\n  modified: true\n"
    )
    _skill(
        tmp_path,
        "foo",
        frontmatter,
    )
    result = _run(monkeypatch, tmp_path)
    assert "modified" in result.output


def test_manually_placed_skill_shows_missing_mysk_block(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\n")
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "missing mysk block" in result.output


def test_malformed_skill_shows_malformed(monkeypatch, tmp_path):
    _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  source: https://example.com\n",
    )
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "malformed" in result.output


def test_multiple_skills_are_sorted_alphabetically(monkeypatch, tmp_path):
    _skill(tmp_path, "zebra", "name: zebra\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "alpha", "name: alpha\ndescription: d\nmysk:\n  state: active\n")
    result = _run(monkeypatch, tmp_path)
    assert result.output.index("alpha") < result.output.index("zebra")
