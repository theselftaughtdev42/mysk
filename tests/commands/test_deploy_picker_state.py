from mysk.domain import LifecycleState
from mysk.io.targets import Target
from tests.commands._deploy_support import (
    _ACTIVE_SKILL,
    _CLAUDE_TARGET,
    _DEPRECATED_SKILL,
    _EXPERIMENTAL_SKILL,
)
from tests.conftest import QuestionaryStub, make_skill


def test_all_skills_with_mysk_block_appear_in_skill_prompt_as_name_state(run_deploy):
    stub = QuestionaryStub([])

    run_deploy(
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL, _EXPERIMENTAL_SKILL, _DEPRECATED_SKILL],
        questionary_stub=stub,
    )

    titles = [choice.title for choice in stub.choices_for("skill")]
    assert "foo (active)" in titles
    assert "bar (experimental)" in titles
    assert "wip (deprecated)" in titles


def test_skill_cleanly_deployed_to_every_selected_target_is_disabled_in_picker(
    tmp_path, capture_skill_choices
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = make_skill("foo", directory=source)
    # A second, undeployed skill keeps at least one choice selectable, so the
    # picker is still shown instead of being skipped by the all-deployed
    # short-circuit.
    other_source = library / "bar"
    other_source.mkdir()
    other_skill = make_skill(
        "bar", state=LifecycleState.EXPERIMENTAL, directory=other_source
    )
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(source)

    disabled = capture_skill_choices(targets=[target], skills=[skill, other_skill])

    assert disabled["foo"] == "already deployed"
    assert disabled["bar"] is None


def test_skill_with_foreign_symlink_collision_stays_selectable_in_picker(
    tmp_path, capture_skill_choices
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = make_skill("foo", directory=source)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (target_dir / "foo").symlink_to(foreign)

    disabled = capture_skill_choices(targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_with_stale_symlink_collision_stays_selectable_in_picker(
    tmp_path, capture_skill_choices
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    other = library / "old-foo"
    other.mkdir()
    skill = make_skill("foo", directory=source)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(other)

    disabled = capture_skill_choices(targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_not_deployed_anywhere_stays_selectable_in_picker(
    tmp_path, capture_skill_choices
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = make_skill("foo", directory=source)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)

    disabled = capture_skill_choices(targets=[target], skills=[skill])

    assert disabled["foo"] is None


def test_skill_deployed_to_only_one_of_two_selected_targets_stays_selectable(
    tmp_path, capture_skill_choices
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = make_skill("foo", directory=source)
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    cursor_dir = tmp_path / "cursor"
    cursor_dir.mkdir()
    claude_target = Target(name="claude", path=claude_dir)
    cursor_target = Target(name="cursor", path=cursor_dir)
    (claude_dir / "foo").symlink_to(source)

    disabled = capture_skill_choices(
        targets=[claude_target, cursor_target], skills=[skill]
    )

    assert disabled["foo"] is None


def test_all_skills_already_deployed_to_selected_target_skips_picker_and_exits_cleanly(
    tmp_path, run_deploy
):
    library = tmp_path / "library"
    library.mkdir()
    source = library / "foo"
    source.mkdir()
    skill = make_skill("foo", directory=source)
    target_dir = tmp_path / "targets"
    target_dir.mkdir()
    target = Target(name="claude", path=target_dir)
    (target_dir / "foo").symlink_to(source)

    stub = QuestionaryStub([target])

    result = run_deploy(
        targets=[target],
        skills=[skill],
        questionary_stub=stub,
    )

    assert result.exit_code == 0
    assert not any("skill" in m.lower() for m in stub.prompted_messages())
    assert "already deployed" in result.output.lower()
