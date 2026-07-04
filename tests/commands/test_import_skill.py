import io
import tarfile
from pathlib import Path

import httpx
import pytest
import respx
import typer

from mysk.cli import app
from mysk.commands import import_skill as import_cmd
from mysk.commands.import_skill import _import_from_local_path, _resolve_local_name
from mysk.domain.import_url import RepoRootUrl

runner = typer.testing.CliRunner()

_RAW_URL = "https://github.com/alice/cool-skills/tree/main/skills/my-skill"
_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/main"
_REPO_ROOT_URL = "https://github.com/alice/cool-skills"
_REPO_ROOT_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/HEAD"


def _make_tarball(skill_dir_name: str, skill_md: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = skill_md.encode()
        info = tarfile.TarInfo(name=f"repo-abc/{skill_dir_name}/SKILL.md")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


_SKILL_MD = "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"


def _mock_select(answer: str, monkeypatch):
    monkeypatch.setattr(
        import_cmd.questionary,
        "select",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: answer)})(),
    )


def _mock_text(answer: str, monkeypatch):
    monkeypatch.setattr(
        import_cmd.questionary,
        "text",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: answer)})(),
    )


def _mock_checkbox(answers: list[str], monkeypatch):
    monkeypatch.setattr(
        import_cmd.questionary,
        "checkbox",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: answers)})(),
    )


@respx.mock
def test_import_downloads_skill_and_prompts_for_lifecycle(library, monkeypatch):
    _mock_select("active", monkeypatch)
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
def test_import_with_rename_stores_upstream_name(library, monkeypatch):
    _mock_select("experimental", monkeypatch)
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
def test_import_with_rename_rejects_invalid_name(library, monkeypatch):

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "MySkill"])

    assert result.exit_code != 0
    assert not (library / "MySkill").exists()
    assert not (library / "my-skill").exists()


@respx.mock
def test_import_with_rename_fails_on_collision_with_local_name(library, monkeypatch):
    existing = library / "local-name"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: local-name\ndescription: already here\n"
        "mysk:\n  state: active\n---\n"
    )

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "local-name"])

    assert result.exit_code != 0
    assert "local-name" in result.output


def test_import_rename_requires_a_value(library, monkeypatch):

    result = runner.invoke(app, ["import", _RAW_URL, "--rename"])

    assert result.exit_code != 0


@respx.mock
def test_import_prompts_rename_on_collision(library, monkeypatch):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )
    _mock_text("my-skill-local", monkeypatch)
    _mock_select("active", monkeypatch)
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
def test_import_exits_when_collision_rename_blank(library, monkeypatch):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )
    _mock_text("", monkeypatch)

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert (library / "my-skill-local").exists() is False


@respx.mock
def test_import_fails_on_http_error(library, monkeypatch):
    respx.get(_TARBALL_URL).mock(return_value=httpx.Response(404))

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert not (library / "my-skill").exists()


def test_import_rejects_non_github_url(library, monkeypatch):

    result = runner.invoke(
        app, ["import", "https://gitlab.com/a/b/tree/main/skills/foo"]
    )

    assert result.exit_code != 0
    assert "github.com" in result.output.lower()


@respx.mock
def test_import_fails_on_collision_same_source(library, monkeypatch):
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


@respx.mock
def test_import_from_repo_root_no_skills_found_errors(library, monkeypatch):

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "README.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0
    assert "No skills found" in result.output


@respx.mock
def test_import_from_repo_root_picks_skill_and_imports(library, monkeypatch):
    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_select("active", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    tree_payload = {"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(200, json=tree_payload)
    )
    respx.get(_REPO_ROOT_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("my-skill", _SKILL_MD))
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    skill_md = library / "my-skill" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "state: active" in text
    assert "modified: false" in text
    assert "my-skill" in text


def test_import_from_local_path_with_rename_ignores_source_name_mismatch(
    tmp_path, monkeypatch, library
):
    _mock_select("active", monkeypatch)

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
    tmp_path, monkeypatch, library
):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    _mock_text("new-name", monkeypatch)
    _mock_select("active", monkeypatch)

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
    tmp_path, monkeypatch, library
):
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    _mock_text("", monkeypatch)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_with_rename_stores_skill_under_new_name(
    tmp_path, monkeypatch, library
):
    _mock_select("active", monkeypatch)

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


def test_import_from_local_path_with_rename_rejects_invalid_name(
    tmp_path, monkeypatch, library
):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src), "--rename", "MySkill"])

    assert result.exit_code != 0
    assert not (library / "MySkill").exists()
    assert not (library / "my-skill").exists()


def test_import_from_local_path_with_rename_fails_on_collision(
    tmp_path, monkeypatch, library
):

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


def test_import_from_local_path_copies_skill_as_self_authored(
    tmp_path, monkeypatch, library
):
    _mock_select("active", monkeypatch)

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


def test_import_from_local_dir_errors_when_no_skills_found(
    tmp_path, monkeypatch, library
):

    skill_src = tmp_path / "my-collection"
    skill_src.mkdir()

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "No skills found" in result.output


def test_import_from_local_path_errors_when_name_mismatches_directory(
    tmp_path, monkeypatch, library
):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(
        "---\nname: different-name\ndescription: does cool things\n---\n"
    )

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert not (library / "my-skill").exists()


def test_import_from_local_path_errors_on_name_collision(
    tmp_path, monkeypatch, library
):

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

    _mock_text("", monkeypatch)
    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


_SKILL_A_MD = "---\nname: skill-a\ndescription: skill a\n---\n# skill-a\n"
_SKILL_B_MD = "---\nname: skill-b\ndescription: skill b\n---\n# skill-b\n"


def _make_multi_tarball(skills: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for dir_name, content in skills.items():
            data = content.encode()
            info = tarfile.TarInfo(name=f"repo-abc/{dir_name}/SKILL.md")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


@respx.mock
def test_import_from_repo_root_imports_multiple_selected_skills(library, monkeypatch):
    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    tree_payload = {
        "tree": [
            {"type": "blob", "path": "skill-a/SKILL.md"},
            {"type": "blob", "path": "skill-b/SKILL.md"},
        ]
    }
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(200, json=tree_payload)
    )
    tarball = _make_multi_tarball({"skill-a": _SKILL_A_MD, "skill-b": _SKILL_B_MD})
    respx.get(_REPO_ROOT_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=tarball)
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a" / "SKILL.md").exists()
    assert (library / "skill-b" / "SKILL.md").exists()


@respx.mock
def test_import_from_repo_root_left_aligns_skill_progress_header(library, monkeypatch):
    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    tree_payload = {
        "tree": [
            {"type": "blob", "path": "skill-a/SKILL.md"},
            {"type": "blob", "path": "skill-b/SKILL.md"},
        ]
    }
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(200, json=tree_payload)
    )
    tarball = _make_multi_tarball({"skill-a": _SKILL_A_MD, "skill-b": _SKILL_B_MD})
    respx.get(_REPO_ROOT_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=tarball)
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    header_line = next(line for line in result.output.splitlines() if "skill-a" in line)
    assert header_line.startswith("skill-a")


@respx.mock
def test_import_from_repo_root_prompts_rename_on_collision(library, monkeypatch):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_text("my-skill-local", monkeypatch)
    _mock_select("experimental", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )
    respx.get(_REPO_ROOT_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("my-skill", _SKILL_MD))
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    skill_md = library / "my-skill-local" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "name: my-skill-local" in text
    assert "upstream_name: my-skill" in text
    assert "state: experimental" in text


@respx.mock
def test_import_from_repo_root_skips_skill_when_rename_blank(library, monkeypatch):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_text("", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert not (library / "my-skill-v2").exists()
    skill_md = library / "my-skill" / "SKILL.md"
    assert "other-repo" in skill_md.read_text()


def _make_local_skill_dir(
    parent: Path, name: str, description: str = "a skill"
) -> None:
    d = parent / name
    d.mkdir()
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n"
    )


def test_import_from_local_dir_imports_selected_skills(tmp_path, monkeypatch, library):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a" / "SKILL.md").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    text_a = (library / "skill-a" / "SKILL.md").read_text()
    assert "state: active" in text_a
    assert "source:" not in text_a


def test_import_from_local_dir_left_aligns_skill_progress_header(
    tmp_path, monkeypatch, library
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")
    _make_local_skill_dir(collection, "skill-b")

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    header_line = next(line for line in result.output.splitlines() if "skill-a" in line)
    assert header_line.startswith("skill-a")


@respx.mock
def test_import_from_repo_root_exits_on_download_error(library, monkeypatch):

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(return_value=httpx.Response(500))

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_from_repo_root_exits_when_nothing_selected(library, monkeypatch):
    _mock_checkbox([], monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_from_repo_root_skips_skill_when_collision_rename_is_invalid(
    library, monkeypatch
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_text("INVALID", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert "0 of 1" in result.output


@respx.mock
def test_import_from_repo_root_skips_skill_when_collision_rename_also_collides(
    library, monkeypatch
):

    existing1 = library / "my-skill"
    existing1.mkdir()
    (existing1 / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )
    existing2 = library / "my-skill-local"
    existing2.mkdir()
    (existing2 / "SKILL.md").write_text(
        "---\nname: my-skill-local\ndescription: d\nmysk:\n  state: active\n---\n"
    )

    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_text("my-skill-local", monkeypatch)

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert "0 of 1" in result.output


def test_import_from_local_path_exits_when_collision_rename_is_invalid(
    tmp_path, monkeypatch, library
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )

    _mock_text("INVALID", monkeypatch)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: new\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "Error" in result.output


def test_import_from_local_path_exits_when_collision_rename_also_collides(
    tmp_path, monkeypatch, library
):

    for name in ["my-skill", "my-skill-alt"]:
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n---\n"
        )

    _mock_text("my-skill-alt", monkeypatch)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: new\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


def test_import_from_local_path_exits_when_skill_md_missing(
    tmp_path, monkeypatch, library
):

    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()

    with pytest.raises(typer.Exit):
        _import_from_local_path(skill_dir)


def test_import_from_local_path_exits_when_skill_md_is_malformed(
    tmp_path, monkeypatch, library
):

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nmysk:\n  state: active\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


def test_import_from_local_path_exits_when_lifecycle_selection_cancelled(
    tmp_path, monkeypatch, library
):

    _mock_select(None, monkeypatch)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text("---\nname: my-skill\ndescription: d\n---\n")

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code != 0


@respx.mock
def test_import_single_exits_when_collision_rename_is_invalid(library, monkeypatch):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    _mock_text("INVALID", monkeypatch)

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_single_exits_when_collision_rename_also_collides(library, monkeypatch):

    for name in ["my-skill", "my-skill-local"]:
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n---\n"
        )

    _mock_text("my-skill-local", monkeypatch)

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_single_exits_when_downloaded_skill_has_no_skill_md(
    library, monkeypatch
):

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
def test_import_single_exits_when_downloaded_skill_md_is_malformed(
    library, monkeypatch
):

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
def test_import_single_exits_when_downloaded_skill_name_mismatches_directory(
    library, monkeypatch
):

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
def test_import_single_exits_when_lifecycle_selection_cancelled(library, monkeypatch):

    _mock_select(None, monkeypatch)
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _SKILL_MD)
        )
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0


def test_import_from_local_dir_ignores_rename_flag(tmp_path, monkeypatch, library):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    _mock_checkbox(["skill-a"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection), "--rename", "ignored"])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a" / "SKILL.md").exists()
    assert not (library / "ignored").exists()


def test_import_from_local_dir_skips_name_mismatch(tmp_path, monkeypatch, library):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    bad = collection / "skill-a"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\nname: wrong-name\ndescription: a skill\n---\n")
    _make_local_skill_dir(collection, "skill-b")

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "skill-a").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "Fix the SKILL.md" in result.output


def test_import_from_local_dir_prompts_rename_on_collision(
    tmp_path, monkeypatch, library
):

    existing = library / "skill-a"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: original\nmysk:\n  state: active\n---\n"
    )

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    _mock_checkbox(["skill-a"], monkeypatch)
    _mock_text("skill-a-new", monkeypatch)
    _mock_select("experimental", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-a-new" / "SKILL.md").exists()
    text = (library / "skill-a-new" / "SKILL.md").read_text()
    assert "name: skill-a-new" in text
    assert "state: experimental" in text


def test_import_from_local_dir_exits_when_nothing_selected(
    tmp_path, monkeypatch, library
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    _mock_checkbox([], monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code != 0


def test_import_from_local_dir_skips_skill_when_collision_rename_is_invalid(
    tmp_path, monkeypatch, library
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

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_text("INVALID", monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "INVALID").exists()
    assert (library / "skill-b" / "SKILL.md").exists()


def test_import_from_local_dir_skips_skill_when_collision_rename_also_collides(
    tmp_path, monkeypatch, library
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

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_text("skill-a-rename", monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-b" / "SKILL.md").exists()


def test_import_from_local_dir_skips_malformed_skill_md(tmp_path, monkeypatch, library):

    collection = tmp_path / "my-collection"
    collection.mkdir()

    bad = collection / "skill-a"
    bad.mkdir()
    (bad / "SKILL.md").write_text("---\ndescription: missing name\n---\n")

    _make_local_skill_dir(collection, "skill-b")

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert not (library / "skill-a").exists()
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "malformed" in result.output.lower()


def test_import_from_local_dir_exits_when_lifecycle_selection_cancelled(
    tmp_path, monkeypatch, library
):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    _make_local_skill_dir(collection, "skill-a")

    _mock_checkbox(["skill-a"], monkeypatch)
    _mock_select(None, monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code != 0


def test_import_from_local_dir_skips_when_collision_rename_blank(
    tmp_path, monkeypatch, library
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

    _mock_checkbox(["skill-a", "skill-b"], monkeypatch)
    _mock_text("", monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    assert (library / "skill-b" / "SKILL.md").exists()
    assert "original" in (library / "skill-a" / "SKILL.md").read_text()
    assert "2 of 2" in result.output


_SKILL_MD_WITH_EXTRAS = (
    "---\nname: my-skill\ndescription: does cool things\n"
    "license: MIT\nallowed-tools:\n- bash\n---\n# my-skill\n"
)


@respx.mock
def test_import_single_preserves_extra_fields(library, monkeypatch):
    _mock_select("active", monkeypatch)
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


def test_import_from_local_path_preserves_extra_fields(tmp_path, monkeypatch, library):
    _mock_select("active", monkeypatch)

    skill_src = tmp_path / "my-skill"
    skill_src.mkdir()
    (skill_src / "SKILL.md").write_text(_SKILL_MD_WITH_EXTRAS)

    result = runner.invoke(app, ["import", str(skill_src)])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: MIT" in text
    assert "allowed-tools" in text


def test_import_from_local_dir_preserves_extra_fields(tmp_path, monkeypatch, library):

    collection = tmp_path / "my-collection"
    collection.mkdir()
    skill_dir = collection / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_SKILL_MD_WITH_EXTRAS)

    _mock_checkbox(["my-skill"], monkeypatch)
    _mock_select("active", monkeypatch)

    result = runner.invoke(app, ["import", str(collection)])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: MIT" in text
    assert "allowed-tools" in text


def test_resolve_local_name_returns_preferred_when_no_collision(tmp_path):
    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="unused")

    assert result == "my-skill"


def test_resolve_local_name_prompts_and_returns_new_name_on_collision(
    tmp_path, monkeypatch
):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    _mock_text("my-skill-renamed", monkeypatch)

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result == "my-skill-renamed"


def test_resolve_local_name_returns_none_when_rename_blank(tmp_path, monkeypatch):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    _mock_text("", monkeypatch)

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None


def test_resolve_local_name_returns_none_when_new_name_invalid(tmp_path, monkeypatch):
    existing = tmp_path / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n---\n"
    )
    _mock_text("Not Valid", monkeypatch)

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None


def test_resolve_local_name_returns_none_when_new_name_also_collides(
    tmp_path, monkeypatch
):
    for skill_name in ("my-skill", "other-skill"):
        skill_dir = tmp_path / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: already here\n"
            "mysk:\n  state: active\n---\n"
        )
    _mock_text("other-skill", monkeypatch)

    result = _resolve_local_name(tmp_path, "my-skill", None, prompt="Enter a new name:")

    assert result is None
