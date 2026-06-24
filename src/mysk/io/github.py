import io
import shutil
import tarfile
import tempfile
from pathlib import Path

import httpx

from mysk.domain.import_url import ImportUrl, RepoRootUrl


class DownloadError(Exception):
    pass


def download_skill(url: ImportUrl, dest: Path) -> None:
    """Download the skill at *url* into *dest*, atomically.

    On any failure *dest* is left untouched. Raises DownloadError on HTTP
    errors or network failures.
    """
    response = httpx.get(url.tarball_url(), follow_redirects=True)
    if response.is_error:
        raise DownloadError(
            f"Failed to download {url.tarball_url()!r}: HTTP {response.status_code}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            tar.extractall(tmp_path, filter="data")

        skill_dir = _find_skill_dir(tmp_path, url.skill_dir_name)
        shutil.copytree(skill_dir, dest)


def scan_repo_for_skills(url: RepoRootUrl, ref: str = "HEAD") -> list[str]:
    """Return paths of directories in *url*'s repo that contain a SKILL.md."""
    response = httpx.get(url.trees_api_url(ref))
    if response.is_error:
        raise DownloadError(f"Failed to fetch repo tree: HTTP {response.status_code}")
    payload = response.json()
    if payload.get("truncated"):
        raise DownloadError(
            "Repository tree was truncated by GitHub (too many objects). "
            "Import a specific skill URL instead of the repo root."
        )
    tree = payload.get("tree", [])
    skill_md_paths = [
        entry["path"]
        for entry in tree
        if entry["type"] == "blob" and entry["path"].endswith("/SKILL.md")
    ]
    return [p[: -len("/SKILL.md")] for p in skill_md_paths]


def _find_skill_dir(extracted: Path, skill_dir_name: str) -> Path:
    matches = list(extracted.rglob(skill_dir_name))
    for match in matches:
        if match.is_dir():
            return match
    raise DownloadError(
        f"Could not find skill directory {skill_dir_name!r} in the downloaded archive."
    )
