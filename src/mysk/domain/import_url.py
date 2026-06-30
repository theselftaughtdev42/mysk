"""Typed wrappers for GitHub repo and skill URLs used during import."""

from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict

_REPO_URL_PARTS = 2
_SKILL_URL_PARTS = 5


class RepoRootUrl(BaseModel):
    """A parsed GitHub repo root URL (owner + repo only, no path)."""

    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Parse a `https://github.com/{owner}/{repo}` URL."""
        parsed = urlparse(raw)
        if parsed.hostname != "github.com":
            msg = (
                f"Only github.com URLs are supported in this version, "
                f"got: {parsed.hostname!r}"
            )
            raise ValueError(msg)
        parts = parsed.path.strip("/").split("/")
        if len(parts) != _REPO_URL_PARTS or not all(parts):
            msg = (
                f"Expected a GitHub repo URL of the form "
                f"https://github.com/{{owner}}/{{repo}}, got: {raw!r}"
            )
            raise ValueError(msg)
        owner, repo = parts
        return cls(owner=owner, repo=repo)

    def trees_api_url(self, ref: str = "HEAD") -> str:
        """Return the GitHub Trees API URL for this repo at *ref*."""
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}"
            f"/git/trees/{ref}?recursive=1"
        )

    def skill_url(self, path: str, ref: str = "HEAD") -> str:
        """Return the GitHub browseable URL for *path* in this repo at *ref*."""
        return f"https://github.com/{self.owner}/{self.repo}/tree/{ref}/{path}"


class ImportUrl(BaseModel):
    """A fully parsed GitHub skill URL (owner, repo, ref, and path to skill dir)."""

    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str
    ref: str
    path: str

    @property
    def skill_dir_name(self) -> str:
        """Return the final path component — the skill directory name."""
        return self.path.rstrip("/").split("/")[-1]

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Parse a `https://github.com/{owner}/{repo}/tree/{ref}/{path}` URL."""
        parsed = urlparse(raw)
        if parsed.hostname != "github.com":
            msg = (
                f"Only github.com URLs are supported in this version, "
                f"got: {parsed.hostname!r}"
            )
            raise ValueError(msg)
        parts = parsed.path.strip("/").split("/")
        # Expected: {owner}/{repo}/tree/{ref}/{path...}
        if len(parts) < _SKILL_URL_PARTS or parts[2] != "tree":
            msg = (
                f"Expected a GitHub URL of the form "
                f"https://github.com/{{owner}}/{{repo}}/tree/{{ref}}/{{path}}, "
                f"got: {raw!r}"
            )
            raise ValueError(msg)
        owner, repo, _, ref, *path_parts = parts
        return cls(owner=owner, repo=repo, ref=ref, path="/".join(path_parts))

    def tarball_url(self) -> str:
        """Return the GitHub API tarball download URL for this skill's ref."""
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/tarball/{self.ref}"
        )
