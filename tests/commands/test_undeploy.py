from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import undeploy as undeploy_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.deploy import RemoveResult
from mysk.io.skills import InstalledSkill
from mysk.io.targets import Target

runner = CliRunner()

_CLAUDE_TARGET = Target(name="claude", path=Path("/home/user/.claude/skills"))
_CURSOR_TARGET = Target(name="cursor", path=Path("/home/user/.cursor/skills"))

_ACTIVE = MyskBlock(state=LifecycleState.ACTIVE)
_EXPERIMENTAL = MyskBlock(state=LifecycleState.EXPERIMENTAL)
_DEPRECATED = MyskBlock(state=LifecycleState.DEPRECATED)

_ACTIVE_SKILL = InstalledSkill(
    skill=Skill(name="foo", description="d", mysk=_ACTIVE),
    mysk=_ACTIVE,
    dir=Path("/fake/skills/foo"),
)
_EXPERIMENTAL_SKILL = InstalledSkill(
    skill=Skill(name="bar", description="d", mysk=_EXPERIMENTAL),
    mysk=_EXPERIMENTAL,
    dir=Path("/fake/skills/bar"),
)
_DEPRECATED_SKILL = InstalledSkill(
    skill=Skill(name="wip", description="d", mysk=_DEPRECATED),
    mysk=_DEPRECATED,
    dir=Path("/fake/skills/wip"),
)


def _run(
    monkeypatch,
    targets=(),
    skills=(),
    questionary_stub=None,
    remove_fn=None,
    is_deployed_fn=None,
    extra_args=(),
):
    monkeypatch.setattr(undeploy_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(undeploy_cmd, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(undeploy_cmd, "load_skills", lambda _: (list(skills), []))
    monkeypatch.setattr(
        undeploy_cmd,
        "is_deployed",
        is_deployed_fn if is_deployed_fn is not None else lambda t, s, lib: True,
    )
    if questionary_stub is not None:
        monkeypatch.setattr(undeploy_cmd, "questionary", questionary_stub)
    if remove_fn is not None:
        monkeypatch.setattr(undeploy_cmd, "remove_skill", remove_fn)
    return runner.invoke(app, ["undeploy", *extra_args])


def _make_questionary(target_answer, skill_answer=None):
    answers = iter([target_answer, skill_answer])

    def checkbox(*args, **kwargs):
        return SimpleNamespace(ask=lambda: next(answers))

    return SimpleNamespace(
        checkbox=checkbox,
        Choice=lambda title, value=None: value,
    )


def _capture_skill_choices(monkeypatch, *, targets, skills, is_deployed_fn=None):
    captured_choices = {}
    answers = iter([targets, []])

    def checkbox(message, choices):
        captured_choices[message] = choices
        return SimpleNamespace(ask=lambda: next(answers))

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)

    _run(
        monkeypatch,
        targets=targets,
        skills=skills,
        questionary_stub=stub,
        is_deployed_fn=is_deployed_fn,
    )

    skill_choices = next(
        choices for msg, choices in captured_choices.items() if "skill" in msg.lower()
    )
    return {choice.value.skill.name: choice.disabled for choice in skill_choices}


def test_not_deployed_skill_disabled_with_reason_in_picker(monkeypatch):
    disabled = _capture_skill_choices(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        is_deployed_fn=lambda t, s, lib: s.name == "foo",
    )

    assert disabled["foo"] is None
    assert disabled["bar"] == "not deployed"


def test_no_deployed_skills_in_selected_targets_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        is_deployed_fn=lambda t, s, lib: False,
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert "no skills" in result.output.lower()


def test_summary_printed_per_target_with_outcomes(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET, _CURSOR_TARGET],
            skill_answer=[_ACTIVE_SKILL],
        ),
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "foo: removed" in result.output


def test_agents_flag_targets_named_agents_without_showing_target_prompt(monkeypatch):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_ACTIVE_SKILL])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert not any("target" in m.lower() for m in prompted)
    assert "claude" in result.output
    assert "cursor" not in result.output


def test_skill_positional_removes_named_skill_without_showing_skill_prompt(
    monkeypatch,
):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    removed = []

    def remove(target_path, skill_library_path):
        removed.append(target_path.name)
        return RemoveResult(outcome="removed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        remove_fn=remove,
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert removed == ["foo"]


def test_bulk_flag_removes_named_skills_without_showing_skill_prompt(monkeypatch):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    removed = []

    def remove(target_path, skill_library_path):
        removed.append(target_path.name)
        return RemoveResult(outcome="removed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        remove_fn=remove,
        extra_args=["--bulk", "foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert removed == ["foo"]


def test_all_flag_removes_every_deployable_skill_without_showing_skill_prompt(
    monkeypatch,
):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    removed = []

    def remove(target_path, skill_library_path):
        removed.append(target_path.name)
        return RemoveResult(outcome="removed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        remove_fn=remove,
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert sorted(removed) == ["bar", "foo"]


def test_all_and_bulk_flags_together_exit_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--all", "--bulk", "foo"],
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_unknown_agent_name_in_agents_flag_exits_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "claude,nonexistent"],
    )

    assert result.exit_code == 1
    assert "nonexistent" in result.output


def test_unknown_skill_name_in_bulk_flag_exits_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(target_answer=[_CLAUDE_TARGET]),
        extra_args=["--bulk", "foo,ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_nothing_selected_at_target_prompt_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(target_answer=[]),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output


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


def test_skip_reason_is_printed_alongside_outcome(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET],
            skill_answer=[_ACTIVE_SKILL],
        ),
        remove_fn=lambda t, skill_library_path: RemoveResult(
            outcome="skipped", reason="not deployed"
        ),
    )

    assert "foo: skipped" in result.output
    assert "not deployed" in result.output
