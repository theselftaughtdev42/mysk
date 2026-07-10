from typer.testing import CliRunner

from mysk.cli import app
from tests.commands._import_skill_support import (
    _SKILL_MD_WITH_EXTRAS,
    _make_local_skill_dir,
)

runner = CliRunner()


def test_import_from_local_dir_errors_when_no_skills_found(tmp_path, library):

    skill_src = tmp_path / "my-collection"
    skill_src.mkdir()

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "No skills found" in result.output


def test_import_from_local_dir_imports_selected_skills(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a" / "SKILL.md").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    text_a = (library / "skill-a" / "SKILL.md").read_text()
    assert "state: active" in text_a
    assert "source:" not in text_a


def test_import_from_local_dir_left_aligns_skill_progress_header(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    header_line = next(line for line in result.output.splitlines() if "skill-a" in line)
    assert header_line.startswith("skill-a")


def test_import_from_local_dir_ignores_rename_flag(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    mock_checkbox(["skill-a"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection), "--rename", "ignored"])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a" / "SKILL.md").exists()
    assert not (library / "ignored").exists()


def test_import_from_local_dir_skips_name_mismatch(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    bad = collection / "skill-a"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\nname: wrong-name\ndescription: a skill\n---\n")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "skill-a").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "Fix the SKILL.md" in result.output


def test_import_from_local_dir_prompts_rename_on_collision(
    tmp_path, library, mock_select, mock_text, mock_checkbox
):

    existing = library / "skill-a"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: original\nmysk:\n  state: active\n---\n"
    )

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    mock_checkbox(["skill-a"])
    mock_text("skill-a-new")
    mock_select("experimental")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a-new" / "SKILL.md").exists()
    text = (library / "skill-a-new" / "SKILL.md").read_text()
    assert "name: skill-a-new" in text
    assert "state: experimental" in text


def test_import_from_local_dir_exits_when_nothing_selected(
    tmp_path, library, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    mock_checkbox([])

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code != 0


def test_import_from_local_dir_skips_skill_when_collision_rename_is_invalid(
    tmp_path, library, mock_select, mock_text, mock_checkbox
):

    existing = library / "skill-a"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: d\nmysk:\n  state: active\n---\n"
    )

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_text("INVALID")
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "INVALID").exists()
    assert (library / "skill-b" / "SKILL.md").exists()


def test_import_from_local_dir_skips_skill_when_collision_rename_also_collides(
    tmp_path, library, mock_select, mock_text, mock_checkbox
):

    for name in ["skill-a", "skill-a-rename"]:
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n---\n"
        )

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_text("skill-a-rename")
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-b" / "SKILL.md").exists()


def test_import_from_local_dir_skips_malformed_skill_md(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()

    bad = collection / "skill-a"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\ndescription: missing name\n---\n")

    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "skill-a").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "malformed" in result.output.lower()


def test_import_from_local_dir_exits_when_lifecycle_selection_cancelled(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    mock_checkbox(["skill-a"])
    mock_select(None)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code != 0


def test_import_from_local_dir_skips_when_collision_rename_blank(
    tmp_path, library, mock_select, mock_text, mock_checkbox
):

    existing = library / "skill-a"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: original\nmysk:\n  state: active\n---\n"
    )

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    mock_checkbox(["skill-a", "skill-b"])
    mock_text("")
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "original" in (library / "skill-a" / "SKILL.md").read_text()
    assert "2 of 2" in result.output


def test_import_from_local_dir_preserves_extra_fields(
    tmp_path, library, mock_select, mock_checkbox
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    skill_dir = collection / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_SKILL_MD_WITH_EXTRAS)

    mock_checkbox(["my-skill"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: MIT" in text
    assert "allowed-tools" in text
