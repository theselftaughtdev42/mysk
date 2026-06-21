from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import deploy as deploy_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
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
_EXPERIMENTAL_SKILL = SkillLoadResult(
    path=Path("/fake/skills/bar/SKILL.md"),
    skill=Skill(
        name="bar", description="d", mysk=MyskBlock(state=LifecycleState.EXPERIMENTAL)
    ),
    schema_error=None,
    is_unmigrated=False,
)
_INIT_SKILL = SkillLoadResult(
    path=Path("/fake/skills/wip/SKILL.md"),
    skill=Skill(name="wip", description="d", mysk=MyskBlock(state=LifecycleState.INIT)),
    schema_error=None,
    is_unmigrated=False,
)


def _make_questionary(target_answer, skill_answer=None):
    """Build a questionary stub; checkbox().ask() returns answers in sequence."""
    answers = iter([target_answer, skill_answer])

    def checkbox(*args, **kwargs):
        answer = next(answers)
        return SimpleNamespace(ask=lambda: answer)

    return SimpleNamespace(
        checkbox=checkbox,
        Choice=lambda title, value=None: value,
    )


def _run(
    monkeypatch,
    repo=Path("/fake/repo"),
    targets=(),
    skills=(),
    questionary_stub=None,
    reconcile_fn=None,
):
    monkeypatch.setattr(deploy_cmd, "find_source_repo", lambda: repo)
    monkeypatch.setattr(deploy_cmd, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(deploy_cmd, "load_skills", lambda _: list(skills))
    if questionary_stub is not None:
        monkeypatch.setattr(deploy_cmd, "questionary", questionary_stub)
    if reconcile_fn is not None:
        monkeypatch.setattr(deploy_cmd, "reconcile_skill", reconcile_fn)
    return runner.invoke(app, ["deploy"])


def test_all_skills_with_mysk_block_appear_in_skill_prompt_as_name_state(monkeypatch):
    captured_choices = {}
    answers = iter([[_CLAUDE_TARGET], []])

    def checkbox(message, choices):
        captured_choices[message] = choices
        return SimpleNamespace(ask=lambda: next(answers))

    stub = SimpleNamespace(
        checkbox=checkbox, Choice=lambda title, value=None: (title, value)
    )

    _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL, _INIT_SKILL],
        questionary_stub=stub,
    )

    skill_choices = [
        choice
        for msg, choices in captured_choices.items()
        if "skill" in msg.lower()
        for choice in choices
    ]
    titles = [title for title, _ in skill_choices]
    assert "foo (active)" in titles
    assert "bar (experimental)" in titles
    assert "wip (init)" in titles


def test_summary_printed_per_target_with_outcomes(monkeypatch):
    outcomes = {"foo": "deployed", "bar": "skipped"}

    def reconcile(source_dir, target_path, overwrite):
        return outcomes[target_path.name]

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET, _CURSOR_TARGET],
            skill_answer=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        ),
        reconcile_fn=reconcile,
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "foo: deployed" in result.output
    assert "bar: skipped" in result.output


def test_nothing_selected_at_skill_prompt_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET],
            skill_answer=[],
        ),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output


def test_nothing_selected_at_target_prompt_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(target_answer=[]),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output
