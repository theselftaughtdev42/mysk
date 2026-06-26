from pathlib import Path

import pytest
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import mark
from mysk.domain import LifecycleState

runner = CliRunner()

_IMPORTED_FM = (
    "name: {name}\ndescription: d\nmysk:\n"
    "  state: active\n  source: https://example.com\n  modified: {modified}\n"
)


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def _run(
    monkeypatch,
    repo: Path,
    extra_args=(),
    prompt_skills=None,
    prompt_key=None,
    prompt_value=None,
):
    monkeypatch.setattr(mark, "skill_library", lambda: repo / "skills")
    if prompt_skills is not None:
        monkeypatch.setattr(mark, "_prompt_for_skills", prompt_skills)
    if prompt_key is not None:
        monkeypatch.setattr(mark, "_prompt_for_key", prompt_key)
    if prompt_value is not None:
        monkeypatch.setattr(mark, "_prompt_for_value", prompt_value)
    return runner.invoke(app, ["mark", *extra_args])


def test_set_modified_writes_true_on_imported_skill(tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="false"))
    mark.set_skill_modified(path, True)
    assert "modified: true" in path.read_text()


def test_set_modified_writes_false_on_imported_skill(tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="true"))
    mark.set_skill_modified(path, False)
    assert "modified: false" in path.read_text()


def test_set_modified_raises_for_self_authored_skill(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: active\n",
    )
    with pytest.raises(ValueError, match="self-authored"):
        mark.set_skill_modified(path, True)


def test_set_lifecycle_updates_existing_mysk_block(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: active\n",
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


def test_interactive_with_no_skills_exits_cleanly_without_prompting(
    monkeypatch, tmp_path
):
    (tmp_path / "skills").mkdir()
    result = _run(monkeypatch, tmp_path)
    assert result.exit_code == 0
    assert "no skills" in result.output.lower()


def test_noninteractive_sets_state_with_key_value(monkeypatch, tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: active\n",
        body="# Foo\n",
    )
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "status", "--value", "experimental"),
    )
    assert result.exit_code == 0
    assert "state: experimental" in path.read_text()


def test_noninteractive_errors_for_manually_placed_skill(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\n")
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "status", "--value", "experimental"),
    )
    assert result.exit_code != 0
    assert "missing mysk block" in result.output.lower()


def test_noninteractive_errors_when_skill_not_found(monkeypatch, tmp_path):
    (tmp_path / "skills").mkdir()
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("ghost", "--key", "status", "--value", "active"),
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_skill_choice_title_includes_current_state(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: experimental\n",
    )
    assert mark._choice_title(path) == "foo (experimental)"


def test_noninteractive_errors_for_invalid_status_value(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch, tmp_path, extra_args=("foo", "--key", "status", "--value", "bogus")
    )
    assert result.exit_code != 0
    assert "unknown status" in result.output.lower()


def test_noninteractive_errors_for_unknown_key(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch, tmp_path, extra_args=("foo", "--key", "bogus", "--value", "active")
    )
    assert result.exit_code != 0
    assert "unknown key" in result.output.lower()


def test_noninteractive_sets_modified_true_on_imported_skill(monkeypatch, tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="false"))
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "modified", "--value", "true"),
    )
    assert result.exit_code == 0
    assert "modified: true" in path.read_text()


def test_noninteractive_sets_modified_case_insensitive(monkeypatch, tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="false"))
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "modified", "--value", "TRUE"),
    )
    assert result.exit_code == 0
    assert "modified: true" in path.read_text()


def test_noninteractive_errors_for_invalid_modified_value(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="false"))
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "modified", "--value", "maybe"),
    )
    assert result.exit_code != 0
    assert "invalid value for modified" in result.output.lower()


def test_noninteractive_errors_for_modified_on_self_authored(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "modified", "--value", "true"),
    )
    assert result.exit_code != 0
    assert "self-authored" in result.output.lower()


def test_interactive_exits_cleanly_when_no_skills_selected(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(monkeypatch, tmp_path, prompt_skills=lambda skills: [])
    assert result.exit_code == 0


def test_prompt_for_skills_returns_chosen_paths(tmp_path, monkeypatch):
    path = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n"
    )
    monkeypatch.setattr(
        mark.questionary,
        "checkbox",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: [path])})(),
    )
    assert mark._prompt_for_skills([path]) == [path]


def test_prompt_for_skills_returns_empty_list_when_nothing_chosen(
    tmp_path, monkeypatch
):
    path = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n"
    )
    monkeypatch.setattr(
        mark.questionary,
        "checkbox",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: None)})(),
    )
    assert mark._prompt_for_skills([path]) == []


def test_prompt_for_key_returns_chosen_key(monkeypatch):
    monkeypatch.setattr(
        mark.questionary,
        "select",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: "status")})(),
    )
    assert mark._prompt_for_key() == "status"


def test_prompt_for_value_status_returns_lifecycle_state(monkeypatch):
    monkeypatch.setattr(
        mark.questionary,
        "select",
        lambda *a, **kw: type(
            "Q", (), {"ask": staticmethod(lambda: LifecycleState.ACTIVE)}
        )(),
    )
    assert mark._prompt_for_value("status") == LifecycleState.ACTIVE


def test_prompt_for_value_modified_returns_bool(monkeypatch):
    monkeypatch.setattr(
        mark.questionary,
        "select",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: True)})(),
    )
    assert mark._prompt_for_value("modified") is True


def test_interactive_marks_multiple_skills_with_same_state(monkeypatch, tmp_path):
    foo = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: experimental\n"
    )
    bar = _skill(
        tmp_path, "bar", "name: bar\ndescription: d\nmysk:\n  state: experimental\n"
    )
    result = _run(
        monkeypatch,
        tmp_path,
        prompt_skills=lambda skills: [foo, bar],
        prompt_key=lambda: "status",
        prompt_value=lambda key: LifecycleState.DEPRECATED,
    )
    assert result.exit_code == 0
    assert "state: deprecated" in foo.read_text()
    assert "state: deprecated" in bar.read_text()


def test_interactive_modified_warns_and_skips_self_authored(monkeypatch, tmp_path):
    imported = _skill(
        tmp_path, "imp", _IMPORTED_FM.format(name="imp", modified="false")
    )
    selfmade = _skill(
        tmp_path,
        "self",
        "name: self\ndescription: d\nmysk:\n  state: active\n",
    )
    result = _run(
        monkeypatch,
        tmp_path,
        prompt_skills=lambda skills: [imported, selfmade],
        prompt_key=lambda: "modified",
        prompt_value=lambda key: True,
    )
    assert result.exit_code == 0
    assert "modified: true" in imported.read_text()
    assert "self" in result.output.lower()
    assert (
        "modified: false" not in selfmade.read_text()
        or "modified" not in selfmade.read_text()
    )
