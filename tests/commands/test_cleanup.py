from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import cleanup as cleanup_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.deploy import RemoveResult
from mysk.io.skills import SkillLoadResult
from mysk.io.targets import Target

runner = CliRunner()

_CLAUDE_TARGET = Target(name="claude", path=Path("/home/user/.claude/skills"))
_CURSOR_TARGET = Target(name="cursor", path=Path("/home/user/.cursor/skills"))

_ACTIVE_SKILL = SkillLoadResult(
    path=Path("/fake/skills/foo/SKILL.md"),
    skill=Skill(
        name="foo", description="d", mysk=MyskBlock(state=LifecycleState.ACTIVE)
    ),
    schema_error=None,
    is_unmigrated=False,
)
_DEPRECATED_SKILL = SkillLoadResult(
    path=Path("/fake/skills/wip/SKILL.md"),
    skill=Skill(
        name="wip", description="d", mysk=MyskBlock(state=LifecycleState.DEPRECATED)
    ),
    schema_error=None,
    is_unmigrated=False,
)


def _run(monkeypatch, targets=(), skills=(), confirm=True, remove_fn=None):
    monkeypatch.setattr(cleanup_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(cleanup_cmd, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(cleanup_cmd, "load_skills", lambda _: list(skills))
    monkeypatch.setattr(cleanup_cmd, "confirm", lambda msg: confirm)
    if remove_fn is not None:
        monkeypatch.setattr(cleanup_cmd, "remove_skill", remove_fn)
    return runner.invoke(app, ["cleanup"])


def test_no_deprecated_skills_prints_nothing_to_clean_up(monkeypatch):
    result = _run(monkeypatch, targets=[_CLAUDE_TARGET], skills=[_ACTIVE_SKILL])

    assert result.exit_code == 0
    assert "nothing to clean up" in result.output.lower()


def test_confirmation_prompt_shown_to_user(monkeypatch):
    monkeypatch.setattr(cleanup_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(cleanup_cmd, "discover_targets", lambda: [_CLAUDE_TARGET])
    monkeypatch.setattr(cleanup_cmd, "load_skills", lambda _: [_DEPRECATED_SKILL])
    monkeypatch.setattr(
        cleanup_cmd,
        "remove_skill",
        lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    result = runner.invoke(app, ["cleanup"], input="n\n")

    assert result.exit_code == 0
    assert "?" in result.output


def test_user_declines_confirmation_exits_without_removing(monkeypatch):
    removed = []
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm=False,
        remove_fn=lambda t, skill_library_path: (
            removed.append(t) or RemoveResult(outcome="removed")
        ),
    )

    assert result.exit_code == 0
    assert removed == []


def test_deprecated_skill_confirmed_removal_shows_removed_grouped_by_target(
    monkeypatch,
):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm=True,
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "wip: removed" in result.output


def test_deprecated_skill_not_deployed_shows_skipped(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        confirm=True,
        remove_fn=lambda t, skill_library_path: RemoveResult(
            outcome="skipped", reason="not deployed"
        ),
    )

    assert result.exit_code == 0
    assert "wip: skipped" in result.output
    assert "not deployed" in result.output
