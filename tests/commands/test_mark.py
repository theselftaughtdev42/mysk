from pathlib import Path

import pytest
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import mark
from mysk.domain import LifecycleState
from tests.conftest import QuestionaryStub

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
    questionary_stub=None,
    prompt_key=None,
    prompt_value=None,
):
    monkeypatch.setattr(mark, "skill_library", lambda: repo / "skills")
    if questionary_stub is not None:
        monkeypatch.setattr(mark, "questionary", questionary_stub)
    if prompt_key is not None:
        monkeypatch.setattr(mark, "_prompt_for_key", prompt_key)
    if prompt_value is not None:
        monkeypatch.setattr(mark, "_prompt_for_value", prompt_value)
    return runner.invoke(app, ["mark", *extra_args])


def test_set_modified_writes_true_on_imported_skill(tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="false"))
    mark.set_skill_modified(path, value=True)
    assert "modified: true" in path.read_text()


def test_set_modified_writes_false_on_imported_skill(tmp_path):
    path = _skill(tmp_path, "foo", _IMPORTED_FM.format(name="foo", modified="true"))
    mark.set_skill_modified(path, value=False)
    assert "modified: false" in path.read_text()


def test_set_modified_raises_for_standalone_skill(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  state: active\n",
    )
    with pytest.raises(ValueError, match="no upstream"):
        mark.set_skill_modified(path, value=True)


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


def test_noninteractive_errors_for_modified_on_standalone(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "modified", "--value", "true"),
    )
    assert result.exit_code != 0
    assert "no upstream" in result.output.lower()


def test_error_goes_to_stderr(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch, tmp_path, extra_args=("foo", "--key", "bogus", "--value", "active")
    )
    assert "unknown key" in result.stderr.lower()


def test_success_confirmation_goes_to_stdout(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "status", "--value", "experimental"),
    )
    assert "marked" in result.stdout.lower()


def test_interactive_exits_cleanly_when_no_skills_selected(monkeypatch, tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(monkeypatch, tmp_path, questionary_stub=QuestionaryStub([]))
    assert result.exit_code == 0


def test_prompt_for_key_returns_chosen_key(monkeypatch):
    monkeypatch.setattr(mark, "questionary", QuestionaryStub("status"))
    assert mark._prompt_for_key() == "status"


def test_prompt_for_value_status_returns_lifecycle_state(monkeypatch):
    monkeypatch.setattr(mark, "questionary", QuestionaryStub(LifecycleState.ACTIVE))
    assert mark._prompt_for_value("status") == LifecycleState.ACTIVE


def test_prompt_for_value_modified_returns_bool(monkeypatch):
    monkeypatch.setattr(mark, "questionary", QuestionaryStub(True))
    assert mark._prompt_for_value("modified") is True


def test_interactive_marks_multiple_skills_with_same_state(monkeypatch, tmp_path):
    foo = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: experimental\n"
    )
    bar = _skill(
        tmp_path, "bar", "name: bar\ndescription: d\nmysk:\n  state: experimental\n"
    )

    stub = QuestionaryStub(lambda choices: [c.value for c in choices])
    result = _run(
        monkeypatch,
        tmp_path,
        questionary_stub=stub,
        prompt_key=lambda: "status",
        prompt_value=lambda key: LifecycleState.DEPRECATED,
    )
    assert result.exit_code == 0
    assert "state: deprecated" in foo.read_text()
    assert "state: deprecated" in bar.read_text()


def test_mark_preserves_extra_fields(tmp_path):
    path = _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nlicense: MIT\nmysk:\n  state: active\n",
    )
    mark.set_skill_lifecycle(path, LifecycleState.EXPERIMENTAL)

    assert "license: MIT" in path.read_text()


def test_skill_only_preselects_skill_and_prompts_key_and_value(monkeypatch, tmp_path):
    path = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n"
    )

    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo",),
        questionary_stub=QuestionaryStub(),
        prompt_key=lambda: "status",
        prompt_value=lambda key: LifecycleState.EXPERIMENTAL,
    )
    assert result.exit_code == 0
    assert "state: experimental" in path.read_text()


def test_skill_and_key_preselects_both_and_prompts_only_value(monkeypatch, tmp_path):
    path = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n"
    )
    prompt_key_calls = []

    def prompt_key():
        prompt_key_calls.append(True)
        return "status"

    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--key", "status"),
        prompt_key=prompt_key,
        prompt_value=lambda key: LifecycleState.EXPERIMENTAL,
    )
    assert result.exit_code == 0
    assert "state: experimental" in path.read_text()
    assert prompt_key_calls == []


def test_bulk_flag_marks_multiple_named_skills_without_prompting(monkeypatch, tmp_path):
    foo = _skill(
        tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: experimental\n"
    )
    bar = _skill(
        tmp_path, "bar", "name: bar\ndescription: d\nmysk:\n  state: experimental\n"
    )
    baz = _skill(
        tmp_path, "baz", "name: baz\ndescription: d\nmysk:\n  state: experimental\n"
    )

    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("--bulk", "foo,bar", "--key", "status", "--value", "active"),
    )
    assert result.exit_code == 0
    assert "state: active" in foo.read_text()
    assert "state: active" in bar.read_text()
    assert "state: experimental" in baz.read_text()


def test_bulk_unknown_skill_errors(monkeypatch, tmp_path):
    (tmp_path / "skills").mkdir()
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("--bulk", "ghost", "--key", "status", "--value", "active"),
    )
    assert result.exit_code == 1
    assert "ghost" in result.output.lower()


def test_all_flag_marks_every_skill(monkeypatch, tmp_path):
    foo = _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    bar = _skill(tmp_path, "bar", "name: bar\ndescription: d\nmysk:\n  state: active\n")

    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("--all", "--key", "status", "--value", "experimental"),
    )
    assert result.exit_code == 0
    assert "state: experimental" in foo.read_text()
    assert "state: experimental" in bar.read_text()


def test_skill_and_bulk_together_exit_with_mutual_exclusivity_error(
    monkeypatch, tmp_path
):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    result = _run(
        monkeypatch,
        tmp_path,
        extra_args=("foo", "--bulk", "foo", "--key", "status", "--value", "active"),
    )
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output.lower()


def test_interactive_modified_warns_and_skips_standalone(monkeypatch, tmp_path):
    imported = _skill(
        tmp_path, "imp", _IMPORTED_FM.format(name="imp", modified="false")
    )
    selfmade = _skill(
        tmp_path,
        "self",
        "name: self\ndescription: d\nmysk:\n  state: active\n",
    )

    stub = QuestionaryStub(lambda choices: [c.value for c in choices])
    result = _run(
        monkeypatch,
        tmp_path,
        questionary_stub=stub,
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
