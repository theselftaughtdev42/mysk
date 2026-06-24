import io
import tarfile

import httpx
import respx
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import import_skill as import_cmd
from mysk.domain.import_url import RepoRootUrl

runner = CliRunner()

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


def _mock_select_sequence(answers: list[str], monkeypatch):
    answers_iter = iter(answers)

    def _select(*a, **kw):
        val = next(answers_iter)
        return type("Q", (), {"ask": staticmethod(lambda v=val: v)})()

    monkeypatch.setattr(import_cmd.questionary, "select", _select)


def _mock_checkbox(answers: list[str], monkeypatch):
    monkeypatch.setattr(
        import_cmd.questionary,
        "checkbox",
        lambda *a, **kw: type("Q", (), {"ask": staticmethod(lambda: answers)})(),
    )


@respx.mock
def test_import_downloads_skill_and_prompts_for_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    _mock_select("active", monkeypatch)
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("my-skill", _SKILL_MD))
    )

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code == 0, result.output
    skill_md = tmp_path / "my-skill" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "source: " + _RAW_URL in text
    assert "modified: false" in text
    assert "state: active" in text


@respx.mock
def test_import_with_rename_stores_upstream_name(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    _mock_select("experimental", monkeypatch)
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=_make_tarball("my-skill", _SKILL_MD))
    )

    result = runner.invoke(app, ["import", _RAW_URL, "--rename", "local-name"])

    assert result.exit_code == 0, result.output
    skill_md = tmp_path / "local-name" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "name: local-name" in text
    assert "upstream_name: my-skill" in text
    assert "state: experimental" in text


@respx.mock
def test_import_fails_on_http_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    respx.get(_TARBALL_URL).mock(return_value=httpx.Response(404))

    result = runner.invoke(app, ["import", _RAW_URL])

    assert result.exit_code != 0
    assert not (tmp_path / "my-skill").exists()


def test_import_rejects_non_github_url(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))

    result = runner.invoke(
        app, ["import", "https://gitlab.com/a/b/tree/main/skills/foo"]
    )

    assert result.exit_code != 0
    assert "github.com" in result.output.lower()


@respx.mock
def test_import_fails_on_collision_same_source(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    existing_dir = tmp_path / "my-skill"
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
def test_import_from_repo_root_no_skills_found_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))

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
def test_import_from_repo_root_picks_skill_and_imports(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
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
    skill_md = tmp_path / "my-skill" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text()
    assert "state: active" in text
    assert "modified: false" in text
    assert "my-skill" in text


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
def test_import_from_repo_root_imports_multiple_selected_skills(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
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
    assert (tmp_path / "skill-a" / "SKILL.md").exists()
    assert (tmp_path / "skill-b" / "SKILL.md").exists()
