from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import list as list_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.domain.provenance import Provenance
from mysk.io.skills import SkillLoadResult
from mysk.io.targets import Target

runner = CliRunner()

_ACTIVE_SKILL = SkillLoadResult(
    path=Path("/fake/skills/foo/SKILL.md"),
    skill=Skill(
        name="foo", description="d", mysk=MyskBlock(state=LifecycleState.ACTIVE)
    ),
    schema_error=None,
)
_DEPRECATED_SKILL = SkillLoadResult(
    path=Path("/fake/skills/old/SKILL.md"),
    skill=Skill(
        name="old", description="d", mysk=MyskBlock(state=LifecycleState.DEPRECATED)
    ),
    schema_error=None,
)
_IMPORTED_SKILL = SkillLoadResult(
    path=Path("/fake/skills/ext/SKILL.md"),
    skill=Skill(
        name="ext",
        description="d",
        mysk=MyskBlock(
            state=LifecycleState.ACTIVE,
            provenance=Provenance(source="https://example.com", modified=False),
        ),
    ),
    schema_error=None,
)
_MODIFIED_SKILL = SkillLoadResult(
    path=Path("/fake/skills/mod/SKILL.md"),
    skill=Skill(
        name="mod",
        description="d",
        mysk=MyskBlock(
            state=LifecycleState.ACTIVE,
            provenance=Provenance(source="https://example.com", modified=True),
        ),
    ),
    schema_error=None,
)
_NO_MYSK_BLOCK_SKILL = SkillLoadResult(
    path=Path("/fake/skills/legacy/SKILL.md"),
    skill=None,
    schema_error="missing mysk block",
)
_BAD_SKILL = SkillLoadResult(
    path=Path("/fake/skills/bad/SKILL.md"),
    skill=None,
    schema_error="mysk block missing state",
)
_CLAUDE_TARGET = Target(name="claude", path=Path("/home/user/.claude/skills"))


def _run(monkeypatch, targets=(), skills=(), deployed_fn=None):
    monkeypatch.setattr(list_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(list_cmd, "discover_targets", lambda **_: list(targets))
    monkeypatch.setattr(list_cmd, "load_skills", lambda _: list(skills))
    if deployed_fn is not None:
        monkeypatch.setattr(list_cmd, "is_deployed", deployed_fn)
    return runner.invoke(app, ["list"])


def test_provenance_column_appears_in_list_output(monkeypatch):
    result = _run(monkeypatch, skills=[_ACTIVE_SKILL])
    assert result.exit_code == 0
    assert "Provenance" in result.output


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


def test_no_mysk_block_skill_shows_inline_status(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_NO_MYSK_BLOCK_SKILL],
    )

    assert result.exit_code == 0
    assert "no mysk block" in result.output


def test_malformed_skill_shows_malformed_inline_status(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_BAD_SKILL],
    )

    assert result.exit_code == 0
    assert "malformed" in result.output


def test_self_authored_skill_shows_self_authored_provenance(monkeypatch):
    result = _run(monkeypatch, skills=[_ACTIVE_SKILL])

    assert result.exit_code == 0
    assert "self-authored" in result.output


def test_imported_skill_shows_imported_provenance(monkeypatch):
    result = _run(monkeypatch, skills=[_IMPORTED_SKILL])

    assert result.exit_code == 0
    assert "imported" in result.output


def test_modified_imported_skill_shows_modified_flag_in_provenance(monkeypatch):
    result = _run(monkeypatch, skills=[_MODIFIED_SKILL])

    assert result.exit_code == 0
    assert "imported ⚠ modified" in result.output


def test_malformed_skill_shows_em_dash_for_provenance(monkeypatch):
    result = _run(monkeypatch, skills=[_BAD_SKILL])

    assert result.exit_code == 0
    assert "—" in result.output
