from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands.dev import mark
from mysk.domain import LifecycleState

runner = CliRunner()


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def _run(monkeypatch, repo: Path, extra_args=(), prompt_skills=None, prompt_state=None):
    monkeypatch.setattr(mark, "find_source_repo", lambda: repo)
    if prompt_skills is not None:
        monkeypatch.setattr(mark, "_prompt_for_skills", prompt_skills)
    if prompt_state is not None:
        monkeypatch.setattr(mark, "_prompt_for_state", prompt_state)
    return runner.invoke(app, ["dev", "mark", *extra_args])


def test_set_lifecycle_updates_existing_mysk_block(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: init\n",
        body="# Foo\n",
    )
    mark.set_skill_lifecycle(path, LifecycleState.EXPERIMENTAL)
    assert "state: experimental" in path.read_text()


def test_set_lifecycle_active_writes_state_active(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: experimental\n",
        body="# Foo\n",
    )
    mark.set_skill_lifecycle(path, LifecycleState.ACTIVE)
    assert "state: active" in path.read_text()


def test_errors_when_run_outside_source_repo(monkeypatch):
    monkeypatch.setattr(mark, "find_source_repo", lambda: None)
    result = runner.invoke(app, ["dev", "mark"])
    assert result.exit_code != 0
    assert "source repo" in result.output.lower()


def test_noninteractive_sets_state_by_name_and_status(monkeypatch, tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: init\n",
        body="# Foo\n",
    )
    result = _run(monkeypatch, tmp_path, extra_args=("foo", "--status", "experimental"))
    assert result.exit_code == 0
    assert "state: experimental" in path.read_text()


def test_noninteractive_errors_for_unmigrated_skill(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\n")
    result = _run(monkeypatch, tmp_path, extra_args=("foo", "--status", "experimental"))
    assert result.exit_code != 0
    assert "not a migrated skill" in result.output.lower()


def test_skill_choice_title_includes_current_state(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: experimental\n",
    )
    assert mark._choice_title(path) == "foo (experimental)"


def test_interactive_marks_multiple_skills_with_same_state(monkeypatch, tmp_path):
    foo = _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: init\n")
    bar = _skill(tmp_path, "bar", "name: bar\ndescription: d\nmysk:\n  state: init\n")
    result = _run(
        monkeypatch,
        tmp_path,
        prompt_skills=lambda skills: [foo, bar],
        prompt_state=lambda: LifecycleState.DEPRECATED,
    )
    assert result.exit_code == 0
    assert "state: deprecated" in foo.read_text()
    assert "state: deprecated" in bar.read_text()
