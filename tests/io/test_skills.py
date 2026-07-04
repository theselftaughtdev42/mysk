from pathlib import Path

import pytest

from mysk.domain import LifecycleState, MyskBlock, Skill
from mysk.io.skills import (
    CollisionError,
    InstalledSkill,
    check_collision,
    load_skills,
    skill_library,
    skill_library_path,
)


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def test_installed_skill_skill_md_is_dir_slash_skill_md(tmp_path):
    mysk = MyskBlock(state=LifecycleState.ACTIVE)
    skill = Skill(name="foo", description="d", mysk=mysk)
    installed = InstalledSkill(skill=skill, mysk=mysk, dir=tmp_path / "foo")
    assert installed.skill_md == tmp_path / "foo" / "SKILL.md"


def test_empty_directory_returns_empty_tuple(tmp_path):
    assert load_skills(tmp_path) == ([], [])


def test_compliant_skill_is_loaded(tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    installed, errors = load_skills(tmp_path)
    assert len(installed) == 1
    assert errors == []
    r = installed[0]
    assert r.mysk is not None
    assert r.dir == tmp_path / "foo"


def test_manually_placed_skill_sets_schema_error(tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\n")
    installed, errors = load_skills(tmp_path)
    assert installed == []
    assert len(errors) == 1
    assert errors[0].schema_error == "missing mysk block"


def test_malformed_block_sets_schema_error(tmp_path):
    _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  source: https://example.com\n",
    )
    installed, errors = load_skills(tmp_path)
    assert installed == []
    assert len(errors) == 1
    assert errors[0].schema_error is not None


def test_mixed_valid_and_invalid_skills_are_separated(tmp_path):
    _skill(tmp_path, "good", "name: good\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "bad", "name: bad\ndescription: d\n")
    installed, errors = load_skills(tmp_path)
    assert len(installed) == 1
    assert installed[0].dir.name == "good"
    assert len(errors) == 1
    assert errors[0].path.parent.name == "bad"


def test_installed_skills_are_sorted_alphabetically(tmp_path):
    _skill(tmp_path, "zebra", "name: zebra\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "alpha", "name: alpha\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "mango", "name: mango\ndescription: d\nmysk:\n  state: active\n")
    installed, _ = load_skills(tmp_path)
    assert [r.dir.name for r in installed] == ["alpha", "mango", "zebra"]


def test_skill_library_path_defaults_to_dot_mysk_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MYSK_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert skill_library_path() == tmp_path / ".mysk" / "skills"


def test_skill_library_path_env_override_resolves_under_mysk_home(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("MYSK_HOME", str(tmp_path / "custom"))
    assert skill_library_path() == tmp_path / "custom" / "skills"


def test_skill_library_path_does_not_create_directory(monkeypatch, tmp_path):
    home = tmp_path / "nonexistent"
    monkeypatch.setenv("MYSK_HOME", str(home))
    skill_library_path()
    assert not home.exists()


def test_skill_library_defaults_to_dot_mysk_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("MYSK_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert skill_library() == tmp_path / ".mysk" / "skills"


def test_skill_library_env_override_resolves_under_mysk_home(monkeypatch, tmp_path):
    monkeypatch.setenv("MYSK_HOME", str(tmp_path / "custom"))
    assert skill_library() == tmp_path / "custom" / "skills"


def test_skill_library_env_override_expands_user(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MYSK_HOME", "~/my-home")
    assert skill_library() == tmp_path / "my-home" / "skills"


def test_skill_library_env_override_resolves_relative_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MYSK_HOME", "relative-home")
    assert skill_library() == tmp_path / "relative-home" / "skills"


def test_skill_library_creates_directory_when_absent(monkeypatch, tmp_path):
    home = tmp_path / "nested"
    monkeypatch.setenv("MYSK_HOME", str(home))
    assert not home.exists()
    library = skill_library()
    assert library == home / "skills"
    assert library.is_dir()


def test_imported_skill_carries_provenance(tmp_path):
    fm = (
        "name: foo\ndescription: d\nmysk:\n  state: experimental\n  "
        "source: https://example.com\n  modified: false\n"
    )
    _skill(tmp_path, "foo", fm)
    installed, _ = load_skills(tmp_path)
    r = installed[0]
    assert r.mysk.provenance.is_imported
    assert not r.mysk.provenance.modified


def test_modified_imported_skill_carries_modified_flag(tmp_path):
    fm = (
        "name: foo\ndescription: d\nmysk:\n  state: active\n  "
        "source: https://example.com\n  modified: true\n"
    )
    _skill(tmp_path, "foo", fm)
    installed, _ = load_skills(tmp_path)
    assert installed[0].mysk.provenance.modified


_SOURCE_A = "https://github.com/alice/repo"
_SOURCE_B = "https://github.com/bob/repo"


def test_collision_same_name_same_source_suggests_refresh(tmp_path):
    fm = (
        f"name: my-skill\ndescription: d\nmysk:\n"
        f"  state: active\n  source: {_SOURCE_A}\n  modified: false\n"
    )
    _skill(tmp_path, "my-skill", fm)

    with pytest.raises(CollisionError, match="mysk refresh my-skill"):
        check_collision(tmp_path, "my-skill", _SOURCE_A)


def test_collision_same_name_different_source_reports_conflict(tmp_path):
    fm = (
        f"name: my-skill\ndescription: d\nmysk:\n"
        f"  state: active\n  source: {_SOURCE_B}\n  modified: false\n"
    )
    _skill(tmp_path, "my-skill", fm)

    with pytest.raises(CollisionError, match="already exists"):
        check_collision(tmp_path, "my-skill", _SOURCE_A)


def test_collision_self_authored_same_name_reports_conflict(tmp_path):
    _skill(
        tmp_path,
        "my-skill",
        "name: my-skill\ndescription: d\nmysk:\n  state: active\n",
    )

    with pytest.raises(CollisionError, match="already exists"):
        check_collision(tmp_path, "my-skill", _SOURCE_A)


def test_no_collision_when_name_is_free(tmp_path):
    check_collision(tmp_path, "my-skill", _SOURCE_A)  # must not raise


def test_collision_malformed_existing_skill_raises_collision_error(tmp_path):
    # mysk block present but missing required 'state' key
    _skill(
        tmp_path,
        "my-skill",
        "name: my-skill\ndescription: d\nmysk:\n  source: https://example.com\n",
    )

    with pytest.raises(CollisionError, match="malformed"):
        check_collision(tmp_path, "my-skill", None)
