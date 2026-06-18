from pathlib import Path

from mysk.io.skills import load_skills


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
