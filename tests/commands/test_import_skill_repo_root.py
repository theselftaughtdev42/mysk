import httpx
import respx
from typer.testing import CliRunner

from mysk.cli import app
from mysk.domain.import_url import RepoRootUrl
from tests.commands._import_skill_support import (
    _REPO_ROOT_TARBALL_URL,
    _REPO_ROOT_URL,
    _SKILL_A_MD,
    _SKILL_B_MD,
    _SKILL_MD,
    _disabled_reason,
    _imported_skill_md,
    _make_multi_tarball,
    _make_tarball,
)

runner = CliRunner()


@respx.mock
def test_import_from_repo_root_no_skills_found_errors(library):

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
def test_import_from_repo_root_picks_skill_and_imports(
    library, mock_select, mock_checkbox
):
    mock_checkbox(["my-skill"])
    mock_select("active")

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


@respx.mock
def test_import_from_repo_root_disables_already_imported_same_source(
    library, mock_checkbox
):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        _imported_skill_md("my-skill", root.skill_url("my-skill"))
    )

    captured = mock_checkbox([])
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200,
            json={
                "tree": [
                    {"type": "blob", "path": "my-skill/SKILL.md"},
                    {"type": "blob", "path": "other-skill/SKILL.md"},
                ]
            },
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0, result.output  # empty selection exits
    choices = {c if isinstance(c, str) else c.value: c for c in captured["choices"]}
    assert (
        _disabled_reason(choices["my-skill"])
        == "already imported as 'my-skill' — run: mysk refresh my-skill"
    )
    assert _disabled_reason(choices["other-skill"]) is None


@respx.mock
def test_import_from_repo_root_ignores_standalone_name_match(library, mock_checkbox):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n---\n"
    )

    captured = mock_checkbox([])
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0, result.output  # empty selection, no short-circuit
    (choice,) = captured["choices"]
    assert _disabled_reason(choice) is None  # standalone: still selectable


@respx.mock
def test_import_from_repo_root_tolerates_malformed_library_skill(
    library, mock_checkbox
):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    broken = library / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_text("---\ndescription: missing name\n---\n")
    good = library / "my-skill"
    good.mkdir()
    (good / "SKILL.md").write_text(
        _imported_skill_md("my-skill", root.skill_url("my-skill"))
    )

    captured = mock_checkbox([])
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200,
            json={
                "tree": [
                    {"type": "blob", "path": "my-skill/SKILL.md"},
                    {"type": "blob", "path": "other-skill/SKILL.md"},
                ]
            },
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0, result.output  # empty selection, but no crash
    choices = {c if isinstance(c, str) else c.value: c for c in captured["choices"]}
    assert _disabled_reason(choices["my-skill"]) is not None
    assert _disabled_reason(choices["other-skill"]) is None


@respx.mock
def test_import_from_repo_root_mixed_imports_the_selectable_skill(
    library, mock_select, mock_checkbox
):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    existing = library / "skill-a"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        _imported_skill_md("skill-a", root.skill_url("skill-a"))
    )

    captured = mock_checkbox(["skill-b"])
    mock_select("active")
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200,
            json={
                "tree": [
                    {"type": "blob", "path": "skill-a/SKILL.md"},
                    {"type": "blob", "path": "skill-b/SKILL.md"},
                ]
            },
        )
    )
    respx.get(_REPO_ROOT_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("skill-b", _SKILL_B_MD))
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert (library / "skill-b" / "SKILL.md").exists()
    choices = {c if isinstance(c, str) else c.value: c for c in captured["choices"]}
    assert _disabled_reason(choices["skill-a"]) is not None
    assert _disabled_reason(choices["skill-b"]) is None


@respx.mock
def test_import_from_repo_root_short_circuits_when_all_already_imported(
    library, mock_checkbox
):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    for name in ("skill-a", "skill-b"):
        d = library / name
        d.mkdir()
        (d / "SKILL.md").write_text(_imported_skill_md(name, root.skill_url(name)))

    captured = mock_checkbox([])
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200,
            json={
                "tree": [
                    {"type": "blob", "path": "skill-a/SKILL.md"},
                    {"type": "blob", "path": "skill-b/SKILL.md"},
                ]
            },
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert "choices" not in captured  # picker never shown
    assert "All 2 skills" in result.output
    assert "refresh" in result.output


@respx.mock
def test_import_from_repo_root_disabled_reason_uses_local_renamed_name(
    library, mock_checkbox
):
    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    existing = library / "local-name"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        _imported_skill_md(
            "local-name", root.skill_url("my-skill"), upstream_name="my-skill"
        )
    )

    captured = mock_checkbox([])
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200,
            json={
                "tree": [
                    {"type": "blob", "path": "my-skill/SKILL.md"},
                    {"type": "blob", "path": "other-skill/SKILL.md"},
                ]
            },
        )
    )

    runner.invoke(app, ["import", _REPO_ROOT_URL])

    choices = {c if isinstance(c, str) else c.value: c for c in captured["choices"]}
    assert (
        _disabled_reason(choices["my-skill"])
        == "already imported as 'local-name' — run: mysk refresh local-name"
    )


@respx.mock
def test_import_from_repo_root_imports_multiple_selected_skills(
    library, mock_select, mock_checkbox
):
    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

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
def test_import_from_repo_root_left_aligns_skill_progress_header(
    library, mock_select, mock_checkbox
):
    mock_checkbox(["skill-a", "skill-b"])
    mock_select("active")

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
def test_import_from_repo_root_prompts_rename_on_collision(
    library, mock_select, mock_text, mock_checkbox
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    mock_checkbox(["my-skill"])
    mock_text("my-skill-local")
    mock_select("experimental")

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
def test_import_from_repo_root_skips_skill_when_rename_blank(
    library, mock_text, mock_checkbox
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    mock_checkbox(["my-skill"])
    mock_text("")

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


@respx.mock
def test_import_from_repo_root_exits_on_download_error(library):

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(return_value=httpx.Response(500))

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code != 0


@respx.mock
def test_import_from_repo_root_exits_when_nothing_selected(library, mock_checkbox):
    mock_checkbox([])

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
    library, mock_text, mock_checkbox
):

    existing = library / "my-skill"
    existing.mkdir()
    (existing / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: already here\nmysk:\n  state: active\n"
        "  source: https://other-repo/my-skill\n  modified: false\n---\n"
    )

    mock_checkbox(["my-skill"])
    mock_text("INVALID")

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
    library, mock_text, mock_checkbox
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

    mock_checkbox(["my-skill"])
    mock_text("my-skill-local")

    root = RepoRootUrl.parse(_REPO_ROOT_URL)
    respx.get(root.trees_api_url()).mock(
        return_value=httpx.Response(
            200, json={"tree": [{"type": "blob", "path": "my-skill/SKILL.md"}]}
        )
    )

    result = runner.invoke(app, ["import", _REPO_ROOT_URL])

    assert result.exit_code == 0, result.output
    assert "0 of 1" in result.output
