from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import cleanup as cleanup_cmd
from mysk.domain import LifecycleState
from mysk.io.deploy import ActResult
from tests.conftest import QuestionaryStub, make_skill, make_target, patch_skill_sources

runner = CliRunner()

_CLAUDE_TARGET = make_target("claude")
_CURSOR_TARGET = make_target("cursor")

_ACTIVE_SKILL = make_skill("foo", state=LifecycleState.ACTIVE)
_DEPRECATED_SKILL = make_skill("wip", state=LifecycleState.DEPRECATED)
_DEPRECATED_SKILL_2 = make_skill("baz", state=LifecycleState.DEPRECATED)


def _run(
    monkeypatch,
    targets=(),
    skills=(),
    questionary_stub=None,
    confirm_fn=None,
    remove_fn=None,
    extra_args=(),
):
    patch_skill_sources(monkeypatch, cleanup_cmd, targets=targets, skills=skills)
    monkeypatch.setattr(
        cleanup_cmd,
        "confirm",
        confirm_fn if confirm_fn is not None else lambda msg, *, yes: True,
    )
    if questionary_stub is not None:
        monkeypatch.setattr(cleanup_cmd, "questionary", questionary_stub)
    if remove_fn is not None:
        monkeypatch.setattr(cleanup_cmd, "remove_skill", remove_fn)
    return runner.invoke(app, ["cleanup", *extra_args])


def test_no_deprecated_skills_prints_nothing_to_clean_up(monkeypatch):
    result = _run(monkeypatch, targets=[_CLAUDE_TARGET], skills=[_ACTIVE_SKILL])

    assert result.exit_code == 0
    assert "nothing to clean up" in result.output.lower()


def test_no_args_picker_shows_all_deprecated_skills_selectable(monkeypatch):
    stub = QuestionaryStub(lambda choices: [choices[0].value])
    removed = []

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL, _DEPRECATED_SKILL_2],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t.name) or ActResult(outcome="removed")
        ),
    )

    assert result.exit_code == 0
    assert all(choice.disabled is None for choice in stub.choices_for("clean"))
    assert removed == ["wip"]


def test_nothing_selected_at_picker_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        questionary_stub=QuestionaryStub([]),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output


def test_all_flag_user_declines_confirmation_exits_without_removing(monkeypatch):
    removed = []
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm_fn=lambda msg, *, yes: False,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t) or ActResult(outcome="removed")
        ),
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert removed == []


def test_all_flag_confirmed_removal_shows_removed_grouped_by_target(
    monkeypatch,
):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_DEPRECATED_SKILL],
        remove_fn=lambda t, skill_library_path: ActResult(outcome="removed"),
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "wip: removed" in result.output


def test_all_flag_deprecated_skill_not_deployed_shows_skipped(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        remove_fn=lambda t, skill_library_path: ActResult(
            outcome="skipped", reason="not deployed"
        ),
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert "wip: skipped" in result.output
    assert "not deployed" in result.output


def test_bulk_flag_removes_only_named_skills_without_showing_picker(monkeypatch):
    stub = QuestionaryStub()
    removed = []

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL, _DEPRECATED_SKILL_2],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t.name) or ActResult(outcome="removed")
        ),
        extra_args=["--bulk", "baz"],
    )

    assert result.exit_code == 0
    assert stub.prompted_messages() == []
    assert removed == ["baz"]


def test_yes_flag_skips_confirmation(monkeypatch):
    confirm_calls = []
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm_fn=lambda msg, *, yes: confirm_calls.append(yes) or True,
        remove_fn=lambda t, skill_library_path: ActResult(outcome="removed"),
        extra_args=["--all", "--yes"],
    )

    assert result.exit_code == 0
    assert confirm_calls == [True]


def test_unknown_skill_name_in_bulk_flag_exits_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        extra_args=["--bulk", "ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_selection_error_goes_to_stderr(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        extra_args=["--bulk", "ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.stderr


def test_per_target_report_goes_to_stdout(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        remove_fn=lambda t, skill_library_path: ActResult(outcome="removed"),
        extra_args=["--all"],
    )

    assert "claude" in result.stdout
    assert "wip: removed" in result.stdout


def test_non_deprecated_skill_name_in_bulk_flag_exits_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _DEPRECATED_SKILL],
        extra_args=["--bulk", "foo"],
    )

    assert result.exit_code == 1
    assert "foo" in result.output


def test_all_and_bulk_flags_together_exit_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        extra_args=["--all", "--bulk", "wip"],
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output
