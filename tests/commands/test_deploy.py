from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import deploy as deploy_cmd
from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.deploy import ReconcileResult
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
    targets=(),
    skills=(),
    questionary_stub=None,
    reconcile_fn=None,
    extra_args=(),
    suppress_ensure_dir=True,
):
    monkeypatch.setattr(deploy_cmd, "skill_library", lambda: Path("/fake/skills"))
    monkeypatch.setattr(deploy_cmd, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(deploy_cmd, "load_skills", lambda _: (list(skills), []))
    if suppress_ensure_dir:
        monkeypatch.setattr(deploy_cmd, "_ensure_target_dir", lambda path: None)
    if questionary_stub is not None:
        monkeypatch.setattr(deploy_cmd, "questionary", questionary_stub)
    if reconcile_fn is not None:
        monkeypatch.setattr(deploy_cmd, "reconcile_skill", reconcile_fn)
    return runner.invoke(app, ["deploy", *extra_args])


def test_empty_library_exits_cleanly_without_skill_prompt(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[],
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert "no skills" in result.output.lower()


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
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="deployed"
        ),
        extra_args=["--agents", "claude"],
    )

    assert result.exit_code == 0
    assert not any("target" in m.lower() for m in prompted)
    assert "claude" in result.output
    assert "cursor" not in result.output


def test_bulk_flag_deploys_named_skills_without_showing_skill_prompt(monkeypatch):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["--bulk", "foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert deployed == ["foo"]


def test_skill_positional_deploys_named_skill_without_showing_skill_prompt(
    monkeypatch,
):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert deployed == ["foo"]


def test_all_flag_deploys_every_deployable_skill_without_showing_skill_prompt(
    monkeypatch,
):
    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [_CLAUDE_TARGET])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)
    deployed = []

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        deployed.append(target_path.name)
        return ReconcileResult(outcome="deployed")

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL],
        questionary_stub=stub,
        reconcile_fn=reconcile,
        extra_args=["--all"],
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert sorted(deployed) == ["bar", "foo"]


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
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL, _DEPRECATED_SKILL],
        questionary_stub=stub,
    )

    skill_choices = [
        choice
        for msg, choices in captured_choices.items()
        if "skill" in msg.lower()
        for choice in choices
    ]
    titles = [choice.title for choice in skill_choices]
    assert "foo (active)" in titles
    assert "bar (experimental)" in titles
    assert "wip (deprecated)" in titles


def _capture_skill_choices(monkeypatch, *, targets, skills, skill_answer=None):
    captured_choices = {}
    answers = iter([targets, skill_answer if skill_answer is not None else []])

    def checkbox(message, choices):
        captured_choices[message] = choices
        return SimpleNamespace(ask=lambda: next(answers))

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)

    _run(monkeypatch, targets=targets, skills=skills, questionary_stub=stub)

    skill_choices = next(
        choices for msg, choices in captured_choices.items() if "skill" in msg.lower()
    )
    return {choice.value.skill.name: choice.disabled for choice in skill_choices}


def test_skill_cleanly_deployed_to_every_selected_target_is_disabled_in_picker(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    # A second, undeployed skill keeps at least one choice selectable, so the
    # picker is still shown instead of being skipped by the all-deployed
    # short-circuit.
    other_source = library / "bar"
    other_source.mkdir()
    other_skill = InstalledSkill(
        skill=Skill(name="bar", description="d", mysk=_EXPERIMENTAL),
        mysk=_EXPERIMENTAL,
        dir=other_source,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(source)

    disabled = _capture_skill_choices(
        monkeypatch, targets=[target], skills=[skill, other_skill]
    )

    assert disabled["foo"] == "already deployed"
    assert disabled["bar"] is None


def test_skill_with_foreign_symlink_collision_stays_selectable_in_picker(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (target_dir / "foo").symlink_to(foreign)

    disabled = _capture_skill_choices(monkeypatch, targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_with_stale_symlink_collision_stays_selectable_in_picker(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    other = library / "old-foo"
    other.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(other)

    disabled = _capture_skill_choices(monkeypatch, targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_not_deployed_anywhere_stays_selectable_in_picker(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)

    disabled = _capture_skill_choices(monkeypatch, targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_deployed_to_only_one_of_two_selected_targets_stays_selectable(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    cursor_dir = tmp_path / "cursor"
    cursor_dir.mkdir()
    claude_target = Target(name="claude", path=claude_dir)
    cursor_target = Target(name="cursor", path=cursor_dir)
    (claude_dir / "foo").symlink_to(source)

    disabled = _capture_skill_choices(
        monkeypatch, targets=[claude_target, cursor_target], skills=[skill]
    )

    assert disabled["foo"] is None


def test_all_skills_already_deployed_to_selected_target_skips_picker_and_exits_cleanly(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(source)

    prompted = []

    def checkbox(message, choices):
        prompted.append(message)
        return SimpleNamespace(ask=lambda: [target])

    stub = SimpleNamespace(checkbox=checkbox, Choice=lambda title, value=None: value)

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[skill],
        questionary_stub=stub,
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in prompted)
    assert "already deployed" in result.output.lower()


def test_summary_printed_per_target_with_outcomes(monkeypatch):
    outcomes = {
        "foo": ReconcileResult(outcome="deployed"),
        "bar": ReconcileResult(outcome="skipped"),
    }

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
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


def test_overwrite_flag_passes_overwrite_true_to_reconcile(monkeypatch):
    captured = {}

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        captured["overwrite"] = overwrite
        return ReconcileResult(outcome="overwritten")

    _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET],
            skill_answer=[_ACTIVE_SKILL],
        ),
        reconcile_fn=reconcile,
        extra_args=["--overwrite"],
    )

    assert captured.get("overwrite") is True


def test_without_overwrite_flag_passes_overwrite_false_to_reconcile(monkeypatch):
    captured = {}

    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        captured["overwrite"] = overwrite
        return ReconcileResult(outcome="skipped")

    _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET],
            skill_answer=[_ACTIVE_SKILL],
        ),
        reconcile_fn=reconcile,
    )

    assert captured.get("overwrite") is False


def test_skip_reason_is_printed_alongside_outcome(monkeypatch):
    def reconcile(source_dir, target_path, overwrite, skill_library_path):
        return ReconcileResult(
            outcome="skipped",
            reason="directory already exists — use --overwrite to replace",
        )

    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[_CLAUDE_TARGET],
            skill_answer=[_ACTIVE_SKILL],
        ),
        reconcile_fn=reconcile,
    )

    assert "foo: skipped" in result.output
    assert "directory already exists" in result.output
    assert "--overwrite" in result.output


def test_existing_target_dir_is_not_reported_as_created(monkeypatch, tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()  # already exists
    target = Target(name="claude", path=skills_dir)

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[_ACTIVE_SKILL],
        ),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="deployed"
        ),
        suppress_ensure_dir=False,
    )

    assert result.exit_code == 0
    assert "Created" not in result.output


def test_missing_skills_dir_is_created_and_reported(monkeypatch, tmp_path):
    agent_home = tmp_path / ".claude"
    agent_home.mkdir()
    skills_dir = agent_home / "skills"
    target = Target(name="claude", path=skills_dir)

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[_ACTIVE_SKILL],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[_ACTIVE_SKILL],
        ),
        reconcile_fn=lambda s, t, o, skill_library_path: ReconcileResult(
            outcome="deployed"
        ),
        suppress_ensure_dir=False,
    )

    assert skills_dir.is_dir()
    assert "Created" in result.output
    assert ".claude/skills" in result.output


def test_overwrite_into_real_directory_prompts_and_declining_makes_no_changes(
    monkeypatch, tmp_path
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=skill_dir,
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    real_dir = target_dir / "foo"
    real_dir.mkdir()
    (real_dir / "marker.txt").write_text("still here")

    monkeypatch.setattr(deploy_cmd, "confirm", lambda message, *, yes: False)

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[skill],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[skill],
        ),
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
    monkeypatch, tmp_path
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=skill_dir,
    )
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

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[skill],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[skill],
        ),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="overwritten"
        ),
        extra_args=["--overwrite", "--yes"],
    )

    assert result.exit_code == 0
    assert confirm_calls == [True]


def test_overwrite_into_symlink_collision_does_not_prompt(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    old = library / "old"
    old.mkdir()
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=source,
    )
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

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[skill],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[skill],
        ),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="overwritten"
        ),
        extra_args=["--overwrite"],
    )

    assert result.exit_code == 0
    assert confirm_calls == []


def test_overwrite_into_real_directory_without_overwrite_flag_does_not_prompt(
    monkeypatch, tmp_path
):
    skill_dir = tmp_path / "library" / "foo"
    skill_dir.mkdir(parents=True)
    skill = InstalledSkill(
        skill=Skill(name="foo", description="d", mysk=_ACTIVE),
        mysk=_ACTIVE,
        dir=skill_dir,
    )
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

    result = _run(
        monkeypatch,
        targets=[target],
        skills=[skill],
        questionary_stub=_make_questionary(
            target_answer=[target],
            skill_answer=[skill],
        ),
        reconcile_fn=lambda s, t, overwrite, skill_library_path: ReconcileResult(
            outcome="skipped", reason="directory already exists"
        ),
    )

    assert result.exit_code == 0
    assert confirm_calls == []
