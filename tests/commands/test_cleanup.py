from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import cleanup as cleanup_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.deploy import RemoveResult
from mysk.io.skills import InstalledSkill
from mysk.io.targets import Target

runner = CliRunner()

_CLAUDE_TARGET = Target(name="claude", path=Path("/home/user/.claude/skills"))
_CURSOR_TARGET = Target(name="cursor", path=Path("/home/user/.cursor/skills"))

_ACTIVE = MyskBlock(state=LifecycleState.ACTIVE)
_DEPRECATED = MyskBlock(state=LifecycleState.DEPRECATED)

_ACTIVE_SKILL = InstalledSkill(
    skill=Skill(name="foo", description="d", mysk=_ACTIVE),
    mysk=_ACTIVE,
    dir=Path("/fake/skills/foo"),
)
_DEPRECATED_SKILL = InstalledSkill(
    skill=Skill(name="wip", description="d", mysk=_DEPRECATED),
    mysk=_DEPRECATED,
    dir=Path("/fake/skills/wip"),
)
_DEPRECATED_SKILL_2 = InstalledSkill(
    skill=Skill(name="baz", description="d", mysk=_DEPRECATED),
    mysk=_DEPRECATED,
    dir=Path("/fake/skills/baz"),
)


def _run(
    monkeypatch,
    targets=(),
    skills=(),
    questionary_stub=None,
    confirm_fn=None,
    remove_fn=None,
    extra_args=(),
):
    monkeypatch.setattr(cleanup_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(cleanup_cmd, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(cleanup_cmd, "load_skills", lambda _: (list(skills), []))
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
    captured = {}

    def checkbox(message, choices):
        captured["message"] = message
        captured["choices"] = choices
        return SimpleNamespace(ask=lambda: [choices[0].value])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    removed = []

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL, _DEPRECATED_SKILL_2],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t.name) or RemoveResult(outcome="removed")
        ),
    )

    assert result.exit_code == 0
    assert all(choice.disabled is None for choice in captured["choices"])
    assert removed == ["wip"]


def test_nothing_selected_at_picker_exits_cleanly(monkeypatch):
    stub = SimpleNamespace(
        checkbox=lambda message, choices: SimpleNamespace(ask=list),
        Choice=lambda title, value=None: value,
    )

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        questionary_stub=stub,
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
            removed.append(t) or RemoveResult(outcome="removed")
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
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
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
        remove_fn=lambda t, skill_library_path: RemoveResult(
            outcome="skipped", reason="not deployed"
        ),
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert "wip: skipped" in result.output
    assert "not deployed" in result.output


def test_bulk_flag_removes_only_named_skills_without_showing_picker(monkeypatch):
    prompted = []
    stub = SimpleNamespace(
        checkbox=lambda message, choices: prompted.append(message),
        Choice=lambda title, value=None: value,
    )
    removed = []

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL, _DEPRECATED_SKILL_2],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t.name) or RemoveResult(outcome="removed")
        ),
        extra_args=["--bulk", "baz"],
    )

    assert result.exit_code == 0
    assert prompted == []
    assert removed == ["baz"]


def test_yes_flag_skips_confirmation(monkeypatch):
    confirm_calls = []
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm_fn=lambda msg, *, yes: confirm_calls.append(yes) or True,
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
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
