import io
import tarfile

import httpx
import respx
from typer.testing import CliRunner

from mysk.cli import app

runner = CliRunner()

_SOURCE_URL = "https://github.com/alice/cool-skills/tree/main/skills/my-skill"
_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/main"

_UPSTREAM_SKILL_MD = (
    "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"
)


def _make_tarball(skill_path: str, skill_md: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = skill_md.encode()
        info = tarfile.TarInfo(name=f"repo-abc/{skill_path}/SKILL.md")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _installed_skill_md(
    name: str = "my-skill",
    description: str = "does cool things",
    state: str = "active",
    source: str = _SOURCE_URL,
    modified: bool = False,
    upstream_name: str | None = None,
) -> str:
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        "mysk:",
        f"  state: {state}",
        f"  source: {source}",
        f"  modified: {'true' if modified else 'false'}",
    ]
    if upstream_name is not None:
        lines.append(f"  upstream_name: {upstream_name}")
    lines += ["---", f"# {name}", ""]
    return "\n".join(lines)


# --- 1. No arguments --------------------------------------------------------


def test_refresh_no_args_exits_with_usage_error():
    result = runner.invoke(app, ["refresh"])

    assert result.exit_code != 0


# --- 2. Skill not found -----------------------------------------------------


def test_refresh_skill_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))

    result = runner.invoke(app, ["refresh", "no-such-skill"])

    assert result.exit_code != 0
    assert "no-such-skill" in result.output


# --- 3. Self-authored skill (no source) -------------------------------------


def test_refresh_self_authored_skill_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: mine\nmysk:\n  state: active\n---\n"
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0
    assert "imported" in result.output.lower()


# --- 4. modified: true guard ------------------------------------------------


def test_refresh_modified_true_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md(modified=True))

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0
    assert "modified" in result.output.lower()


# --- 5. Clean refresh -------------------------------------------------------


@respx.mock
def test_refresh_clean_updates_skill_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code == 0, result.output
    text = (tmp_path / "my-skill" / "SKILL.md").read_text()
    assert "description: improved description" in text
    assert "state: active" in text
    assert f"source: {_SOURCE_URL}" in text
    assert "modified: false" in text


# --- 6. upstream_name lookup ------------------------------------------------


@respx.mock
def test_refresh_upstream_name_writes_to_local_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "local-name"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        _installed_skill_md(name="local-name", upstream_name="my-skill")
    )

    upstream_md = (
        "---\nname: my-skill\ndescription: upstream improved\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = runner.invoke(app, ["refresh", "local-name"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "local-name" / "SKILL.md").exists()
    assert not (tmp_path / "my-skill").exists()
    text = (tmp_path / "local-name" / "SKILL.md").read_text()
    assert "name: local-name" in text
    assert "description: upstream improved" in text
    assert "upstream_name: my-skill" in text


# --- 7. No changes ----------------------------------------------------------


@respx.mock
def test_refresh_no_changes_skips_write(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _UPSTREAM_SKILL_MD)
        )
    )

    mtime_before = (tmp_path / "my-skill" / "SKILL.md").stat().st_mtime

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code == 0, result.output
    assert "no changes" in result.output.lower()
    assert (tmp_path / "my-skill" / "SKILL.md").stat().st_mtime == mtime_before


# --- 8. --all flag ----------------------------------------------------------


def test_refresh_all_and_name_errors():
    result = runner.invoke(app, ["refresh", "--all", "my-skill"])

    assert result.exit_code != 0


def test_refresh_all_no_imported_skills(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: mine\nmysk:\n  state: active\n---\n"
    )

    result = runner.invoke(app, ["refresh", "--all"])

    assert result.exit_code == 0
    assert "no imported" in result.output.lower()


_SOURCE_URL_A = "https://github.com/alice/cool-skills/tree/main/skills/skill-a"
_SOURCE_URL_B = "https://github.com/alice/cool-skills/tree/main/skills/skill-b"


@respx.mock
def test_refresh_all_clean_path(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))

    (tmp_path / "skill-a").mkdir()
    (tmp_path / "skill-a" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-a", source=_SOURCE_URL_A)
    )
    (tmp_path / "skill-b").mkdir()
    (tmp_path / "skill-b" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-b", source=_SOURCE_URL_B)
    )

    upstream_a = "---\nname: skill-a\ndescription: improved a\n---\n# skill-a\n"
    upstream_b = "---\nname: skill-b\ndescription: improved b\n---\n# skill-b\n"
    respx.get(_TARBALL_URL).mock(
        side_effect=[
            httpx.Response(200, content=_make_tarball("skills/skill-a", upstream_a)),
            httpx.Response(200, content=_make_tarball("skills/skill-b", upstream_b)),
        ]
    )

    result = runner.invoke(app, ["refresh", "--all"])

    assert result.exit_code == 0, result.output
    assert "description: improved a" in (tmp_path / "skill-a" / "SKILL.md").read_text()
    assert "description: improved b" in (tmp_path / "skill-b" / "SKILL.md").read_text()


@respx.mock
def test_refresh_malformed_skill_md_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  source: https://example.com\n---\n"
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


def test_refresh_unparseable_source_url_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        "  source: not-a-valid-github-url\n  modified: false\n---\n"
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0


@respx.mock
def test_refresh_download_error_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())
    respx.get(_TARBALL_URL).mock(return_value=httpx.Response(500))

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0


@respx.mock
def test_refresh_missing_upstream_skill_md_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"content"
        info = tarfile.TarInfo(name="repo-abc/skills/my-skill/other.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(200, content=buf.getvalue())
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0
    assert "SKILL.md" in result.output


@respx.mock
def test_refresh_malformed_upstream_skill_md_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    bad_upstream = (
        "---\nname: my-skill\ndescription: d\nmysk:\n  source: bad\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", bad_upstream)
        )
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


@respx.mock
def test_refresh_updates_and_removes_extra_local_files_when_file_sets_differ(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())
    (skill_dir / "extra.py").write_text("# extra file only in local copy\n")

    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _UPSTREAM_SKILL_MD)
        )
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "my-skill" / "extra.py").exists()
    assert (tmp_path / "my-skill" / "SKILL.md").exists()


@respx.mock
def test_refresh_takes_extra_fields_from_upstream(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n"
        "license: Apache-2.0\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = runner.invoke(app, ["refresh", "my-skill"])

    assert result.exit_code == 0, result.output
    text = (tmp_path / "my-skill" / "SKILL.md").read_text()
    assert "license: Apache-2.0" in text


@respx.mock
def test_refresh_all_mixed_modified(tmp_path, monkeypatch):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(tmp_path))

    _source_clean = "https://github.com/alice/cool-skills/tree/main/skills/skill-clean"
    _source_dirty = "https://github.com/alice/cool-skills/tree/main/skills/skill-dirty"

    (tmp_path / "skill-clean").mkdir()
    (tmp_path / "skill-clean" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-clean", source=_source_clean)
    )
    (tmp_path / "skill-dirty").mkdir()
    (tmp_path / "skill-dirty" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-dirty", source=_source_dirty, modified=True)
    )

    upstream_clean = (
        "---\nname: skill-clean\ndescription: updated clean\n---\n# skill-clean\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/skill-clean", upstream_clean)
        )
    )

    result = runner.invoke(app, ["refresh", "--all"])

    assert result.exit_code == 0, result.output
    assert (
        "description: updated clean"
        in (tmp_path / "skill-clean" / "SKILL.md").read_text()
    )
    assert "needs review" in result.output.lower()
    assert "skill-dirty" in result.output
