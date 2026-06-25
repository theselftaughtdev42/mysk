from pathlib import Path

import pytest

from mysk.io import skills as skills_mod
from mysk.io.skills import CollisionError, check_collision, load_skills, skill_library


def _skill(root: Path, name: str, frontmatter_lines: str, body: str = "") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    path = skill_dir / "SKILL.md"
    path.write_text(f"---\n{frontmatter_lines}---\n{body}")
    return path


def test_empty_directory_returns_empty_list(tmp_path):
    assert load_skills(tmp_path) == []


def test_compliant_skill_is_loaded(tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\nmysk:\n  state: active\n")
    results = load_skills(tmp_path)
    assert len(results) == 1
    r = results[0]
    assert r.skill is not None
    assert r.skill.mysk is not None
    assert r.schema_error is None
    assert not r.is_unmigrated


def test_unmigrated_skill_sets_is_unmigrated(tmp_path):
    _skill(tmp_path, "foo", "name: foo\ndescription: d\n")
    results = load_skills(tmp_path)
    assert len(results) == 1
    r = results[0]
    assert r.is_unmigrated
    assert r.skill is not None
    assert r.skill.mysk is None
    assert r.schema_error is None


def test_malformed_block_sets_schema_error(tmp_path):
    _skill(
        tmp_path,
        "foo",
        "name: foo\ndescription: d\nmysk:\n  source: https://example.com\n",
    )
    results = load_skills(tmp_path)
    assert len(results) == 1
    r = results[0]
    assert r.schema_error is not None
    assert r.skill is None
    assert not r.is_unmigrated


def test_results_are_sorted_alphabetically(tmp_path):
    _skill(tmp_path, "zebra", "name: zebra\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "alpha", "name: alpha\ndescription: d\nmysk:\n  state: active\n")
    _skill(tmp_path, "mango", "name: mango\ndescription: d\nmysk:\n  state: active\n")
    results = load_skills(tmp_path)
    names = [r.path.parent.name for r in results]
    assert names == ["alpha", "mango", "zebra"]


def test_skill_library_defaults_to_platformdirs_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("MYSK_SKILLS_DIR", raising=False)
    monkeypatch.setattr(skills_mod, "user_data_dir", lambda app: str(tmp_path / app))
    assert skill_library() == tmp_path / "mysk" / "skills"


def test_skill_library_env_override_takes_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path / "custom"))
    assert skill_library() == tmp_path / "custom"


def test_skill_library_env_override_expands_user(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MYSK_SKILLS_DIR", "~/my-skills")
    assert skill_library() == tmp_path / "my-skills"


def test_skill_library_creates_directory_when_absent(monkeypatch, tmp_path):
    target = tmp_path / "nested" / "skills"
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(target))
    assert not target.exists()
    assert skill_library() == target
    assert target.is_dir()


def test_imported_skill_carries_provenance(tmp_path):
    frontmatter = (
        "name: foo\ndescription: d\nmysk:\n  state: experimental\n  "
        "source: https://example.com\n  modified: false\n"
    )
    _skill(
        tmp_path,
        "foo",
        frontmatter,
    )
    results = load_skills(tmp_path)
    r = results[0]
    assert r.skill is not None
    assert r.skill.mysk is not None
    assert r.skill.mysk.provenance.is_imported
    assert not r.skill.mysk.provenance.modified


def test_modified_imported_skill_carries_modified_flag(tmp_path):
    frontmatter = (
        "name: foo\ndescription: d\nmysk:\n  state: active\n  "
        "source: https://example.com\n  modified: true\n"
    )
    _skill(
        tmp_path,
        "foo",
        frontmatter,
    )
    results = load_skills(tmp_path)
    r = results[0]
    assert r.skill is not None
    assert r.skill.mysk.provenance.modified


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
