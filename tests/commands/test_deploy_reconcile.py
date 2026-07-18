from mysk.commands import deploy as deploy_cmd
from mysk.io.deploy import ActResult
from mysk.io.targets import Target
from tests.commands._deploy_support import (
    _ACTIVE_SKILL,
    _CLAUDE_TARGET,
    _CURSOR_TARGET,
    _EXPERIMENTAL_SKILL,
)
from tests.conftest import QuestionaryStub, make_skill


def test_per_target_report_goes_to_stdout(run_deploy):
    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ActResult(
            outcome="deployed"
        ),
    )

    assert "claude" in result.stdout
    assert "foo: deployed" in result.stdout


def test_summary_printed_per_target_with_outcomes(run_deploy):
    outcomes = {
        "foo": ActResult(outcome="deployed"),
        "bar": ActResult(outcome="skipped"),
    }

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        return outcomes[target_path.name]

    result = run_deploy(
        targets=[_CLAUDE_TARGET, _CURSOR_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL, _EXPERIMENTAL_SKILL]),
        reconcile_fn=reconcile,
    )

    assert result.exit_code == 0
    assert "claude" in result.output
    assert "cursor" in result.output
    assert "foo: deployed" in result.output
    assert "bar: skipped" in result.output


def test_overwrite_flag_passes_overwrite_true_to_reconcile(run_deploy):
    captured = {}

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        captured["overwrite"] = overwrite
        return ActResult(outcome="overwritten")

    run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=reconcile,
        extra_args=["--overwrite"],
    )

    assert captured.get("overwrite") is True


def test_without_overwrite_flag_passes_overwrite_false_to_reconcile(run_deploy):
    captured = {}

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        captured["overwrite"] = overwrite
        return ActResult(outcome="skipped")

    run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=reconcile,
    )

    assert captured.get("overwrite") is False


def test_skip_reason_is_printed_alongside_outcome(run_deploy):
    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        return ActResult(
            outcome="skipped",
            reason="directory already exists — use --overwrite to replace",
        )

    result = run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=reconcile,
    )

    assert "foo: skipped" in result.output
    assert "directory already exists" in result.output
    assert "--overwrite" in result.output


def test_existing_target_dir_is_not_reported_as_created(tmp_path, run_deploy):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()  # already exists
    target = Target(name="claude", path=skills_dir)

    result = run_deploy(
        targets=[target],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ActResult(
            outcome="deployed"
        ),
        suppress_ensure_dir=False,
    )

    assert result.exit_code == 0
    assert "Created" not in result.output


def test_missing_skills_dir_is_created_and_reported(tmp_path, run_deploy):
    agent_home = tmp_path / ".claude"
    agent_home.mkdir()
    skills_dir = agent_home / "skills"
    target = Target(name="claude", path=skills_dir)

    result = run_deploy(
        targets=[target],
        skills=[_ACTIVE_SKILL],
        questionary_stub=QuestionaryStub([_ACTIVE_SKILL]),
        reconcile_fn=lambda s, t, o, skill_library_path: ActResult(outcome="deployed"),
        suppress_ensure_dir=False,
    )

    assert skills_dir.is_dir()
    assert "Created" in result.output
    assert ".claude/skills" in result.output


def test_overwrite_into_real_directory_prompts_and_declining_makes_no_changes(
    monkeypatch, tmp_path, run_deploy
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = make_skill("foo", directory=skill_dir)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    real_dir = target_dir / "foo"
    real_dir.mkdir()
    (real_dir / "marker.txt").write_text("still here")

    monkeypatch.setattr(deploy_cmd, "confirm", lambda message, *, yes: False)

    result = run_deploy(
        targets=[target],
        skills=[skill],
        questionary_stub=QuestionaryStub([skill]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: (_ for _ in ()).throw(
            AssertionError("reconcile_skill should not run when declined")
        ),
        extra_args=["--overwrite"],
    )

    assert result.exit_code == 0
    assert "declined" in result.output
    assert real_dir.is_dir()
    assert (real_dir / "marker.txt").exists()
    assert not real_dir.is_symlink()


def test_overwrite_into_real_directory_with_yes_flag_skips_confirmation(
    monkeypatch, tmp_path, run_deploy
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = make_skill("foo", directory=skill_dir)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").mkdir()

    confirm_calls = []
    monkeypatch.setattr(
        deploy_cmd,
        "confirm",
        lambda message, *, yes: confirm_calls.append(yes) or True,
    )

    result = run_deploy(
        targets=[target],
        skills=[skill],
        questionary_stub=QuestionaryStub([skill]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ActResult(
            outcome="overwritten"
        ),
        extra_args=["--overwrite", "--yes"],
    )

    assert result.exit_code == 0
    assert confirm_calls == [True]


def test_overwrite_into_symlink_collision_does_not_prompt(
    monkeypatch, tmp_path, run_deploy
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    old = library / "old"
    old.mkdir()
    skill = make_skill("foo", directory=source)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(old)

    confirm_calls = []
    monkeypatch.setattr(
        deploy_cmd,
        "confirm",
        lambda message, *, yes: confirm_calls.append(1) or True,
    )

    result = run_deploy(
        targets=[target],
        skills=[skill],
        questionary_stub=QuestionaryStub([skill]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ActResult(
            outcome="overwritten"
        ),
        extra_args=["--overwrite"],
    )

    assert result.exit_code == 0
    assert confirm_calls == []


def test_overwrite_into_real_directory_without_overwrite_flag_does_not_prompt(
    monkeypatch, tmp_path, run_deploy
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = make_skill("foo", directory=skill_dir)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").mkdir()

    confirm_calls = []
    monkeypatch.setattr(
        deploy_cmd,
        "confirm",
        lambda message, *, yes: confirm_calls.append(1) or True,
    )

    result = run_deploy(
        targets=[target],
        skills=[skill],
        questionary_stub=QuestionaryStub([skill]),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ActResult(
            outcome="skipped", reason="directory already exists"
        ),
    )

    assert result.exit_code == 0
    assert confirm_calls == []
