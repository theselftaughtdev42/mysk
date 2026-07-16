import io
import logging
import tarfile

import httpx
import pytest
import respx

from mysk.domain.import_url import ImportUrl, RepoRootUrl
from mysk.io.github import (
    DownloadError,
    UpstreamGoneError,
    UpstreamUnreachableError,
    download_skill,
    scan_repo_for_skills,
)

_URL = ImportUrl.parse("https://github.com/alice/cool-skills/tree/main/skills/my-skill")


@respx.mock
def test_download_404_raises_upstream_gone_and_writes_no_files(tmp_path):
    respx.get(_URL.tarball_url()).mock(return_value=httpx.Response(404))

    with pytest.raises(UpstreamGoneError):
        download_skill(_URL, tmp_path / "my-skill")

    assert not (tmp_path / "my-skill").exists()


@respx.mock
@pytest.mark.parametrize("status", [500, 502, 429, 403])
def test_download_transient_status_raises_upstream_unreachable(tmp_path, status):
    respx.get(_URL.tarball_url()).mock(return_value=httpx.Response(status))

    with pytest.raises(UpstreamUnreachableError):
        download_skill(_URL, tmp_path / "my-skill")

    assert not (tmp_path / "my-skill").exists()


@respx.mock
def test_download_dropped_connection_raises_upstream_unreachable(tmp_path):
    respx.get(_URL.tarball_url()).mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(UpstreamUnreachableError):
        download_skill(_URL, tmp_path / "my-skill")

    assert not (tmp_path / "my-skill").exists()


def _make_tarball(skill_path: str, files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel_path, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name=f"repo-abc123/{skill_path}/{rel_path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


_ROOT_URL = RepoRootUrl.parse("https://github.com/alice/cool-skills")


@respx.mock
def test_scan_repo_for_skills_raises_on_truncated_response():
    respx.get(_ROOT_URL.trees_api_url()).mock(
        return_value=httpx.Response(200, json={"truncated": True, "tree": []})
    )

    with pytest.raises(DownloadError, match="truncated"):
        scan_repo_for_skills(_ROOT_URL)


@respx.mock
def test_scan_repo_logs_request_url_and_result_count(caplog):
    tree_payload = {
        "tree": [
            {"type": "tree", "path": "skills/foo"},
            {"type": "blob", "path": "skills/foo/SKILL.md"},
        ]
    }
    respx.get(_ROOT_URL.trees_api_url()).mock(
        return_value=httpx.Response(200, json=tree_payload)
    )
    with caplog.at_level(logging.DEBUG, logger="mysk"):
        scan_repo_for_skills(_ROOT_URL)
    messages = [r.message for r in caplog.records]
    assert any(_ROOT_URL.trees_api_url() in m for m in messages)
    assert any("1" in m for m in messages)


@respx.mock
def test_scan_repo_for_skills_returns_skill_dirs():
    tree_payload = {
        "tree": [
            {"type": "tree", "path": "skills/foo"},
            {"type": "blob", "path": "skills/foo/SKILL.md"},
            {"type": "tree", "path": "skills/bar"},
            {"type": "blob", "path": "skills/bar/SKILL.md"},
            {"type": "blob", "path": "README.md"},
        ]
    }
    respx.get(_ROOT_URL.trees_api_url()).mock(
        return_value=httpx.Response(200, json=tree_payload)
    )

    paths = scan_repo_for_skills(_ROOT_URL)

    assert paths == ["skills/foo", "skills/bar"]


@respx.mock
def test_scan_repo_for_skills_raises_on_http_error():
    respx.get(_ROOT_URL.trees_api_url()).mock(return_value=httpx.Response(500))

    with pytest.raises(DownloadError, match="500"):
        scan_repo_for_skills(_ROOT_URL)


@respx.mock
def test_download_skill_raises_when_skill_path_not_found_in_archive(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"content"
        info = tarfile.TarInfo(name="repo-abc/wrong-path/file.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    respx.get(_URL.tarball_url()).mock(
        return_value=httpx.Response(200, content=buf.getvalue())
    )

    with pytest.raises(UpstreamGoneError, match="Could not find"):
        download_skill(_URL, tmp_path / "my-skill")


@respx.mock
def test_download_skill_raises_upstream_gone_when_archive_has_no_skill_md(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"content"
        info = tarfile.TarInfo(name="repo-abc/skills/my-skill/other.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    respx.get(_URL.tarball_url()).mock(
        return_value=httpx.Response(200, content=buf.getvalue())
    )

    with pytest.raises(UpstreamGoneError, match=r"SKILL\.md"):
        download_skill(_URL, tmp_path / "my-skill")

    assert not (tmp_path / "my-skill").exists()


@respx.mock
def test_download_logs_request_url_and_status(tmp_path, caplog):
    tarball = _make_tarball("skills/my-skill", {"SKILL.md": "x\n"})
    respx.get(_URL.tarball_url()).mock(
        return_value=httpx.Response(200, content=tarball)
    )
    with caplog.at_level(logging.DEBUG, logger="mysk"):
        download_skill(_URL, tmp_path / "my-skill")
    messages = [r.message for r in caplog.records]
    assert any(_URL.tarball_url() in m for m in messages)
    assert any("200" in m for m in messages)


@respx.mock
def test_download_extracts_skill_files(tmp_path):
    tarball = _make_tarball(
        "skills/my-skill",
        {"SKILL.md": "---\nname: my-skill\n---\n# body\n", "helper.py": "pass\n"},
    )
    respx.get(_URL.tarball_url()).mock(
        return_value=httpx.Response(200, content=tarball)
    )

    dest = tmp_path / "my-skill"
    download_skill(_URL, dest)

    assert (dest / "SKILL.md").read_text() == "---\nname: my-skill\n---\n# body\n"
    assert (dest / "helper.py").read_text() == "pass\n"
