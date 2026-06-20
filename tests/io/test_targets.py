from pathlib import Path

from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.targets import Target, discover_targets, is_deployed


def test_target_label_uses_tilde_for_home_relative_paths():
    p = Path.home() / ".claude" / "skills"
    t = Target(name="claude", path=p)
    assert t.label() == "~/.claude/skills (claude)"


def test_target_label_uses_absolute_path_when_not_under_home():
    t = Target(name="claude", path=Path("/var/skills"))
    assert t.label() == "/var/skills (claude)"


def test_discover_targets_returns_only_existing_directories(tmp_path):
    claude = tmp_path / ".claude" / "skills"
    claude.mkdir(parents=True)

    targets = discover_targets(search_root=tmp_path)

    assert len(targets) == 1
    assert targets[0].name == "claude"
    assert targets[0].path == claude


def test_is_deployed_true_when_skill_dir_exists_with_mysk_block(tmp_path):
    skill = Skill(
        name="foo",
        description="d",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
    )
    target = Target(name="claude", path=tmp_path)
    skill_dir = tmp_path / "foo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: foo\ndescription: d\nmysk:\n  state: active\n---\n"
    )

    assert is_deployed(target, skill) is True


def test_is_deployed_false_when_skill_dir_missing(tmp_path):
    skill = Skill(
        name="foo",
        description="d",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
    )
    target = Target(name="claude", path=tmp_path)

    assert is_deployed(target, skill) is False


def test_is_deployed_false_when_skill_dir_exists_but_no_mysk_block(tmp_path):
    skill = Skill(
        name="foo",
        description="d",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
    )
    target = Target(name="claude", path=tmp_path)
    skill_dir = tmp_path / "foo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: foo\ndescription: d\n---\n")

    assert is_deployed(target, skill) is False
