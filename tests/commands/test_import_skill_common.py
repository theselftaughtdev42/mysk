import io
import tarfile

import httpx
import respx
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands.import_skill import _resolve_local_name
from tests.commands._import_skill_support import (
    _RAW_URL,
    _SKILL_MD,
    _SKILL_MD_WITH_EXTRAS,
    _TARBALL_URL,
    _make_local_skill_dir,
    _make_tarball,
)

runner = CliRunner()


@respx.mock
def test_import_downloads_skill_and_prompts_for_lifecycle(library, mock_select):
    mock_select("active")
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code == 0, result.output
    skill_md = library / "my-skill" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "source: " + _RAW_URL in text
    assert "modified: false" in text
    assert "state: active" in text


@respx.mock
def test_import_with_rename_stores_upstream_name(library, mock_select):
    mock_select("experimental")
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "local-name"])

    assert result.exit_code == 0, result.output
    skill_md = library / "local-name" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "name: local-name" in text
    assert "upstream_name: my-skill" in text
    assert "state: experimental" in text


@respx.mock
def test_import_with_rename_rejects_invalid_name(library):

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "MySkill"])

    assert result.exit_code != 0
    assert not (library / "MySkill").exists()
    assert not (library / "my-skill").exists()


@respx.mock
def test_import_with_rename_fails_on_collision_with_local_name(library):
    existing = library / "local-name"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: local-name\ndescription: already here\n"
        "mysk:\n  state: active\n---\n"
    )

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "local-name"])

    assert result.exit_code != 0
    assert "local-name" in result.output


def test_import_rename_requires_a_value(library):

    result = runner.invoke(app, ["import", _RAW_URL, "--rename"])

    assert result.exit_code != 0


@respx.mock
def test_import_prompts_rename_on_collision(library, mock_select, mock_text):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )
    mock_text("my-skill-local")
    mock_select("active")
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code == 0, result.output
    skill_md = library / "my-skill-local" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "name: my-skill-local" in text
    assert "upstream_name: my-skill" in text


@respx.mock
def test_import_exits_when_collision_rename_blank(library, mock_text):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )
    mock_text("")

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert (library / "my-skill-local").exists() is False


@respx.mock
def test_import_fails_on_http_error(library):
    respx.get(_TARBALL_URL).mock(return_value=httpx.Response(404))

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert not (library / "my-skill").exists()


def test_import_rejects_non_github_url(library):

    result = runner.invoke(
        app, ["import", "https://gitlab.com/a/b/tree/main/skills/foo"]
    )

    assert result.exit_code != 0
    assert "github.com" in result.output.lower()


@respx.mock
def test_import_fails_on_collision_same_source(library):
    existing_dir = library / "my-skill"
    existing_dir.mkdir()
    (existing_dir / "SKILL.md").write_text(
        f"---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        f"  source: {_RAW_URL}\n  modified: false\n---\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("my-skill", _SKILL_MD))
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert "mysk refresh my-skill" in result.output


def test_error_goes_to_stderr(tmp_path, library):
    skill_src = tmp_path / "my-collection"
    skill_src.mkdir()

    result = runner.invoke(app, ["import", str(skill_src)])

    assert "No skills found" in result.stderr


def test_import_summary_and_section_rule_go_to_stdout(
    tmp_path, library, mock_select, mock_checkbox
):
    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    mock_checkbox(["skill-a"])
    mock_select("active")

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert "Imported" in result.stdout
    assert "skill-a" in result.stdout


@respx.mock
def test_import_single_exits_when_collision_rename_is_invalid(library, mock_text):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    mock_text("INVALID")

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_single_exits_when_collision_rename_also_collides(library, mock_text):

    for name in ["my-skill", "my-skill-local"]:
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n---\n"
        )

    mock_text("my-skill-local")

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_single_exits_when_downloaded_skill_has_no_skill_md(library):

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"content"
        info = tarfile.TarInfo(name="repo-abc/skills/my-skill/other.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=buf.getvalue())
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert "SKILL.md" in result.output


@respx.mock
def test_import_single_exits_when_downloaded_skill_md_is_malformed(library):

    bad_md = "---\nmysk:\n  state: active\n---\n# no name or description\n"
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", bad_md)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


@respx.mock
def test_import_single_exits_when_downloaded_skill_name_mismatches_directory(library):

    mismatch_md = "---\nname: different-name\ndescription: d\n---\n# different\n"
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", mismatch_md)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert "does not match" in result.output.lower()


@respx.mock
def test_import_single_exits_when_lifecycle_selection_cancelled(library, mock_select):

    mock_select(None)
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_single_preserves_extra_fields(library, mock_select):
    mock_select("active")
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD_WITH_EXTRAS)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: MIT" in text
    assert "allowed-tools" in text


def test_resolve_local_name_returns_preferred_when_no_collision(tmp_path):
    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="unused")

    assert result == "my-skill"


def test_resolve_local_name_prompts_and_returns_new_name_on_collision(
    tmp_path, mock_text
):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    mock_text("my-skill-renamed")

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result == "my-skill-renamed"


def test_resolve_local_name_returns_none_when_rename_blank(tmp_path, mock_text):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    mock_text("")

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None


def test_resolve_local_name_returns_none_when_new_name_invalid(tmp_path, mock_text):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    mock_text("Not Valid")

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None


def test_resolve_local_name_returns_none_when_new_name_also_collides(
    tmp_path, mock_text
):
    for skill_name in ("my-skill", "other-skill"):
        skill_dir = tmp_path / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: already here\n"
            "mysk:\n  state: active\n---\n"
        )
    mock_text("other-skill")

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None
