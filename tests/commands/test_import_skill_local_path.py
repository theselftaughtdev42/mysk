import pytest
import typer
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands.import_skill import _import_from_local_path
from tests.commands._import_skill_support import (
    _SKILL_MD_WITH_EXTRAS,
)

runner = CliRunner()


def test_import_from_local_path_with_rename_ignores_source_name_mismatch(
    tmp_path, library, mock_select
):
    mock_select("active")

    skill_src = tmp_path / "their-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src), "--rename", "my-name"])

    assert result.exit_code == 0, result.output
    text = (library / "my-name" / "SKILL.md").read_text()
    assert "name: my-name" in text


def test_import_from_local_path_prompts_rename_on_collision(
    tmp_path, library, mock_select, mock_text
):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    mock_text("new-name")
    mock_select("active")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code == 0, result.output
    assert (library / "new-name" / "SKILL.md").exists()
    assert "name: new-name" in (library / "new-name" / "SKILL.md").read_text()


def test_import_from_local_path_exits_when_collision_rename_blank(
    tmp_path, library, mock_text
):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    mock_text("")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_with_rename_stores_skill_under_new_name(
    tmp_path, library, mock_select
):
    mock_select("active")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"
    )

    result = runner.invoke(app, ["import", str(skill_src), "--rename", "new-name"])

    assert result.exit_code == 0, result.output
    skill_md = library / "new-name" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "name: new-name" in text
    assert "state: active" in text
    assert "source:" not in text
    assert "upstream_name:" not in text


def test_import_from_local_path_with_rename_rejects_invalid_name(tmp_path, library):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src), "--rename", "MySkill"])

    assert result.exit_code != 0
    assert not (library / "MySkill").exists()
    assert not (library / "my-skill").exists()


def test_import_from_local_path_with_rename_fails_on_collision(tmp_path, library):

    existing = library / "new-name"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: new-name\ndescription: already here\nmysk:\n  state: active\n---\n"
    )

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src), "--rename", "new-name"])

    assert result.exit_code != 0


def test_import_from_local_path_copies_skill_as_standalone(
    tmp_path, library, mock_select
):
    mock_select("active")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code == 0, result.output
    skill_md = library / "my-skill" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "state: active" in text
    assert "source:" not in text


def test_import_from_local_path_errors_when_name_mismatches_directory(
    tmp_path, library
):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert not (library / "my-skill").exists()


def test_import_from_local_path_errors_on_name_collision(tmp_path, library, mock_text):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: original\nmysk:\n  state: active\n---\n"
    )

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: new version\n---\n"
    )

    mock_text("")
    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_exits_when_collision_rename_is_invalid(
    tmp_path, library, mock_text
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )

    mock_text("INVALID")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: new\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "Error" in result.output


def test_import_from_local_path_exits_when_collision_rename_also_collides(
    tmp_path, library, mock_text
):

    for name in ["my-skill", "my-skill-alt"]:
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n---\n"
        )

    mock_text("my-skill-alt")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: new\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_exits_when_skill_md_missing(tmp_path, library):

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    with pytest.raises(typer.Exit):
        _import_from_local_path(skill_dir)


def test_import_from_local_path_exits_when_skill_md_is_malformed(tmp_path, library):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nmysk:\n  state: active\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


def test_import_from_local_path_exits_when_lifecycle_selection_cancelled(
    tmp_path, library, mock_select
):

    mock_select(None)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: d\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_preserves_extra_fields(tmp_path, library, mock_select):
    mock_select("active")

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(_SKILL_MD_WITH_EXTRAS)

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: MIT" in text
    assert "allowed-tools" in text
