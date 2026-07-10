import io
import tarfile

import httpx
import respx

from tests.commands._refresh_skill_support import (
    _TARBALL_URL,
    _installed_skill_md,
    _make_tarball,
    _standalone_skill_md,
)


def test_refresh_skill_not_found(library, run_refresh):
    result = run_refresh(extra_args=["no-such-skill"])

    assert result.exit_code != 0
    assert "no-such-skill" in result.output


def test_refresh_error_goes_to_stderr(library, run_refresh):
    result = run_refresh(extra_args=["no-such-skill"])

    assert "no-such-skill" in result.stderr


def test_refresh_standalone_skill_errors(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_standalone_skill_md())

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0
    assert "no upstream" in result.output.lower()


def test_refresh_modified_true_errors(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md(modified=True))

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0
    assert "modified" in result.output.lower()


@respx.mock
def test_refresh_malformed_skill_md_exits_with_error(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  source: https://example.com\n---\n"
    )

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()


def test_refresh_unparseable_source_url_exits_with_error(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: d\nmysk:\n  state: active\n"
        "  source: not-a-valid-github-url\n  modified: false\n---\n"
    )

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0


@respx.mock
def test_refresh_download_error_exits_with_error(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())
    respx.get(_TARBALL_URL).mock(return_value=httpx.Response(500))

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0


@respx.mock
def test_refresh_missing_upstream_skill_md_exits_with_error(library, run_refresh):
    skill_dir = library / "my-skill"
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

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0
    assert "SKILL.md" in result.output


@respx.mock
def test_refresh_malformed_upstream_skill_md_exits_with_error(library, run_refresh):
    skill_dir = library / "my-skill"
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

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code != 0
    assert "malformed" in result.output.lower()
