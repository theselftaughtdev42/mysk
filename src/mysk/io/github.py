"""GitHub API access: skill tarball download and repo tree scanning."""

import io
import shutil
import tarfile
import tempfile
from pathlib import Path

import httpx

from mysk.domain.import_url import ImportUrl, RepoRootUrl
from mysk.output import Output

out = Output(__name__)


class DownloadError(Exception):
    """Raised when a GitHub download or API request fails."""


class UpstreamGoneError(DownloadError):
    """A recorded upstream that permanently no longer resolves.

    The repo or ref is gone, or the skill directory (or its `SKILL.md`) has
    been renamed or deleted within a live repo.
    """


class UpstreamUnreachableError(DownloadError):
    """A transient failure fetching an upstream.

    A 5xx, 429, or 403 response, or a dropped connection — the upstream may
    still exist and the fetch is worth retrying later.
    """


def download_skill(url: ImportUrl, dest: Path) -> None:
    """Download the skill at *url* into *dest*, atomically.

    On any failure *dest* is left untouched. Raises UpstreamGoneError when the
    upstream permanently no longer resolves (404, or a missing skill directory
    or SKILL.md) and UpstreamUnreachableError on a transient failure (5xx, 429,
    403, or a dropped connection).
    """
    out.debug(f"GET {url.tarball_url()}")
    try:
        response = httpx.get(url.tarball_url(), follow_redirects=True)
    except httpx.HTTPError as exc:
        msg = f"Could not reach {url.tarball_url()!r}: {exc}"
        raise UpstreamUnreachableError(msg) from exc
    out.debug(f"→ HTTP {response.status_code} ({len(response.content)} bytes)")
    if response.is_error:
        target = url.tarball_url()
        if response.status_code == httpx.codes.NOT_FOUND:
            msg = f"Upstream {target!r} no longer exists (HTTP 404)."
            raise UpstreamGoneError(msg)
        msg = f"Could not reach {target!r}: HTTP {response.status_code}."
        raise UpstreamUnreachableError(msg)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as tar:
            tar.extractall(tmp_path, filter="data")

        skill_dir = _find_skill_dir(tmp_path, url.path)
        if not (skill_dir / "SKILL.md").exists():
            msg = (
                f"Upstream skill directory {url.path!r} has no SKILL.md — "
                "it appears to have been renamed or deleted."
            )
            raise UpstreamGoneError(msg)
        out.debug(f"copytree {skill_dir} → {dest}")
        shutil.copytree(skill_dir, dest)


def scan_repo_for_skills(url: RepoRootUrl, ref: str = "HEAD") -> list[str]:
    """Return paths of directories in *url*'s repo that contain a SKILL.md."""
    out.debug(f"GET {url.trees_api_url(ref)}")
    response = httpx.get(url.trees_api_url(ref))
    out.debug(f"→ HTTP {response.status_code}")
    if response.is_error:
        msg = f"Failed to fetch repo tree: HTTP {response.status_code}"
        raise DownloadError(msg)
    payload = response.json()
    if payload.get("truncated"):
        out.debug("repo tree truncated by GitHub — cannot scan repo root")
        msg = (
            "Repository tree was truncated by GitHub (too many objects). "
            "Import a specific skill URL instead of the repo root."
        )
        raise DownloadError(msg)
    tree = payload.get("tree", [])
    skill_md_paths = [
        entry["path"]
        for entry in tree
        if entry["type"] == "blob" and entry["path"].endswith("/SKILL.md")
    ]
    skill_dirs = [p[: -len("/SKILL.md")] for p in skill_md_paths]
    out.debug(f"found {len(skill_dirs)} skill(s) in repo tree")
    return skill_dirs


def _find_skill_dir(extracted: Path, skill_path: str) -> Path:
    # GitHub tarballs nest everything under one top-level dir — descend into
    # it to reach the skill path
    top_dirs = [d for d in extracted.iterdir() if d.is_dir()]
    if len(top_dirs) == 1:
        candidate = top_dirs[0] / skill_path
        if candidate.is_dir():
            return candidate
    msg = f"Could not find skill directory {skill_path!r} in the downloaded archive."
    raise UpstreamGoneError(msg)
