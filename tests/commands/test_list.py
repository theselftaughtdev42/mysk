from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import list as list_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.targets import Target

runner = CliRunner()

_ACTIVE_SKILL = Skill(
    name="foo",
    description="d",
    mysk=MyskBlock(state=LifecycleState.ACTIVE),
)
_DEPRECATED_SKILL = Skill(
    name="old",
    description="d",
    mysk=MyskBlock(state=LifecycleState.DEPRECATED),
)
_CLAUDE_TARGET = Target(name="claude", path=Path("/home/user/.claude/skills"))


def _run(monkeypatch, repo=Path("/fake/repo"), targets=(), skills=(), deployed_fn=None):
    monkeypatch.setattr(list_cmd, "find_source_repo", lambda: repo)
    monkeypatch.setattr(list_cmd, "discover_targets", lambda **_: list(targets))
    monkeypatch.setattr(list_cmd, "load_skills", lambda _: list(skills))
    if deployed_fn is not None:
        monkeypatch.setattr(list_cmd, "is_deployed", deployed_fn)
    return runner.invoke(app, ["list"])


def test_exits_with_error_when_source_repo_not_found(monkeypatch):
    result = _run(monkeypatch, repo=None)

    assert result.exit_code != 0
    assert "source repo" in result.output.lower()


def test_deployed_skill_appears_in_table_with_target_label(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s: True,
    )

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "claude" in result.output


def test_undeployed_skill_shows_em_dash_in_deployed_to_column(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s: False,
    )

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "—" in result.output


def test_hint_shown_when_no_deployment_targets_exist(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[],
        skills=[_ACTIVE_SKILL],
    )

    assert result.exit_code == 0
    assert "mysk deploy" in result.output


def test_non_deployable_skill_shows_path_when_deployed(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        deployed_fn=lambda t, s: True,
    )

    assert result.exit_code == 0
    assert "claude" in result.output


def test_non_deployable_skill_shows_em_dash_when_not_deployed(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        deployed_fn=lambda t, s: False,
    )

    assert result.exit_code == 0
    assert "—" in result.output
