from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import undeploy as undeploy_cmd
from mysk.domain import LifecycleState
from mysk.io.deploy import RemoveResult
from tests.conftest import QuestionaryStub, make_skill, make_target, patch_skill_sources

runner = CliRunner()

_CLAUDE_TARGET = make_target("claude")
_CURSOR_TARGET = make_target("cursor")

_ACTIVE_SKILL = make_skill("foo", state=LifecycleState.ACTIVE)
_EXPERIMENTAL_SKILL = make_skill("bar", state=LifecycleState.EXPERIMENTAL)
_DEPRECATED_SKILL = make_skill("wip", state=LifecycleState.DEPRECATED)


def _run(
    monkeypatch,
    targets=(),
    skills=(),
    questionary_stub=None,
    remove_fn=None,
    is_deployed_fn=None,
    extra_args=(),
):
    patch_skill_sources(monkeypatch, undeploy_cmd, targets=targets, skills=skills)
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


def _capture_skill_choices(monkeypatch, *, targets, skills, is_deployed_fn=None):
    stub = QuestionaryStub([])
    _run(
        monkeypatch,
        targets=targets,
        skills=skills,
        questionary_stub=stub,
        is_deployed_fn=is_deployed_fn,
    )
    skill_choices = stub.choices_for("skill")
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
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "foo: removed" in result.output


def test_agents_flag_targets_named_agents_without_showing_target_prompt(monkeypatch):
    stub = QuestionaryStub([_ACTIVE_SKILL])

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert not any("target" in m.lower() for m in stub.prompted_messages())
    assert "claude" in result.output
    assert "cursor" not in result.output


def test_no_agents_flag_fans_out_to_all_found_targets_and_prints_roster(monkeypatch):
    stub = QuestionaryStub([_ACTIVE_SKILL])
    targets = [_CLAUDE_TARGET, _CURSOR_TARGET]

    result = _run(
        monkeypatch,
        targets=targets,
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    assert result.exit_code == 0
    # no target prompt is shown — only the skill picker
    assert not any("target" in m.lower() for m in stub.prompted_messages())
    # the resolved roster names every found target, before the per-target report
    assert "Undeploying from 2 targets: claude, cursor" in result.output
    # and the skill is removed from every found target
    assert result.output.count("foo: removed") == len(targets)


def test_no_targets_found_exits_before_skill_prompt(monkeypatch):
    stub = QuestionaryStub()

    result = _run(
        monkeypatch,
        targets=[],
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
    )

    assert result.exit_code == 0
    assert "no deployment targets found" in result.output.lower()
    assert stub.prompted_messages() == []


def test_unknown_agent_error_lists_available_target_names(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.stderr
    assert "claude" in result.stderr
    assert "cursor" in result.stderr


def test_skill_positional_removes_named_skill_without_showing_skill_prompt(
    monkeypatch,
):
    stub = QuestionaryStub([_CLAUDE_TARGET])
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
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert removed == ["foo"]


def test_bulk_flag_removes_named_skills_without_showing_skill_prompt(monkeypatch):
    stub = QuestionaryStub([_CLAUDE_TARGET])
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
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert removed == ["foo"]


def test_all_flag_removes_every_deployable_skill_without_showing_skill_prompt(
    monkeypatch,
):
    stub = QuestionaryStub([_CLAUDE_TARGET])
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
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
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


def test_unknown_agent_error_goes_to_stderr(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "claude,nonexistent"],
    )

    assert "nonexistent" in result.stderr


def test_per_target_report_goes_to_stdout(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        remove_fn=lambda t, skill_library_path: RemoveResult(outcome="removed"),
    )

    assert "claude" in result.stdout
    assert "foo: removed" in result.stdout


def test_unknown_skill_name_in_bulk_flag_exits_with_error(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_CLAUDE_TARGET]),
        extra_args=["--bulk", "foo,ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_nothing_selected_at_skill_prompt_exits_cleanly(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([]),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output


def test_skip_reason_is_printed_alongside_outcome(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        remove_fn=lambda t, skill_library_path: RemoveResult(
            outcome="skipped", reason="not deployed"
        ),
    )

    assert "foo: skipped" in result.output
    assert "not deployed" in result.output
