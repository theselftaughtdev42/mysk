from mysk.io.deploy import ReconcileResult
from tests.commands._deploy_support import (
    _ACTIVE_SKILL,
    _CLAUDE_TARGET,
    _CURSOR_TARGET,
    _EXPERIMENTAL_SKILL,
)
from tests.conftest import QuestionaryStub


def test_empty_library_exits_cleanly_without_skill_prompt(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[],
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert "no skills" in result.output.lower()


def test_agents_flag_targets_named_agents_without_showing_target_prompt(run_deploy):
    stub = QuestionaryStub([_ACTIVE_SKILL])

    result = run_deploy(
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="deployed"
        ),
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert not any("target" in m.lower() for m in stub.prompted_messages())
    assert "claude" in result.output
    assert "cursor" not in result.output


def test_no_agents_flag_fans_out_to_all_found_targets_and_prints_roster(run_deploy):
    stub = QuestionaryStub([_ACTIVE_SKILL])
    targets = [_CLAUDE_TARGET, _CURSOR_TARGET]

    result = run_deploy(
        targets=targets,
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="deployed"
        ),
    )

    assert result.exit_code == 0
    # no target prompt is shown — only the skill picker
    assert not any("target" in m.lower() for m in stub.prompted_messages())
    # the resolved roster names every found target, before the per-target report
    assert "Deploying to 2 targets: claude, cursor" in result.output
    # and the skill lands in every found target
    assert result.output.count("foo: deployed") == len(targets)


def test_no_targets_found_exits_before_skill_prompt(run_deploy):
    stub = QuestionaryStub()

    result = run_deploy(
        targets=[],
        skills=[_ACTIVE_SKILL],
        questionary_stub=stub,
    )

    assert result.exit_code == 0
    assert "no deployment targets found" in result.output.lower()
    assert stub.prompted_messages() == []


def test_unknown_agent_error_lists_available_target_names(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.stderr
    assert "claude" in result.stderr
    assert "cursor" in result.stderr


def test_bulk_flag_deploys_named_skills_without_showing_skill_prompt(run_deploy):
    stub = QuestionaryStub([_CLAUDE_TARGET])
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["--bulk", "foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert deployed == ["foo"]


def test_skill_positional_deploys_named_skill_without_showing_skill_prompt(run_deploy):
    stub = QuestionaryStub([_CLAUDE_TARGET])
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert deployed == ["foo"]


def test_all_flag_deploys_every_deployable_skill_without_showing_skill_prompt(
    run_deploy,
):
    stub = QuestionaryStub([_CLAUDE_TARGET])
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert sorted(deployed) == ["bar", "foo"]


def test_all_and_bulk_flags_together_exit_with_error(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--all", "--bulk", "foo"],
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_unknown_agent_name_in_agents_flag_exits_with_error(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "claude,nonexistent"],
    )

    assert result.exit_code == 1
    assert "nonexistent" in result.output


def test_unknown_skill_name_in_bulk_flag_exits_with_error(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_CLAUDE_TARGET]),
        extra_args=["--bulk", "foo,ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_unknown_agent_error_goes_to_stderr(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        extra_args=["--agents", "claude,nonexistent"],
    )

    assert "nonexistent" in result.stderr


def test_selection_error_goes_to_stderr(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_CLAUDE_TARGET]),
        extra_args=["--bulk", "foo,ghost"],
    )

    assert result.exit_code == 1
    assert "ghost" in result.stderr


def test_nothing_selected_at_skill_prompt_exits_cleanly(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([]),
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output
