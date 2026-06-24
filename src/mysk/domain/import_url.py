from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict


class RepoRootUrl(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str

    @classmethod
    def parse(cls, raw: str) -> Self:
        parsed = urlparse(raw)
        if parsed.hostname != "github.com":
            raise ValueError(
                f"Only github.com URLs are supported in this version, "
                f"got: {parsed.hostname!r}"
            )
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(
                f"Expected a GitHub repo URL of the form "
                f"https://github.com/{{owner}}/{{repo}}, got: {raw!r}"
            )
        owner, repo = parts
        return cls(owner=owner, repo=repo)

    def trees_api_url(self, ref: str = "HEAD") -> str:
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}"
            f"/git/trees/{ref}?recursive=1"
        )

    def skill_url(self, path: str, ref: str = "HEAD") -> str:
        return f"https://github.com/{self.owner}/{self.repo}/tree/{ref}/{path}"


class ImportUrl(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str
    ref: str
    path: str

    @property
    def skill_dir_name(self) -> str:
        return self.path.rstrip("/").split("/")[-1]

    @classmethod
    def parse(cls, raw: str) -> Self:
        parsed = urlparse(raw)
        if parsed.hostname != "github.com":
            raise ValueError(
                f"Only github.com URLs are supported in this version, "
                f"got: {parsed.hostname!r}"
            )
        parts = parsed.path.strip("/").split("/")
        # Expected: {owner}/{repo}/tree/{ref}/{path...}
        if len(parts) < 5 or parts[2] != "tree":
            raise ValueError(
                f"Expected a GitHub URL of the form "
                f"https://github.com/{{owner}}/{{repo}}/tree/{{ref}}/{{path}}, "
                f"got: {raw!r}"
            )
        owner, repo, _, ref, *path_parts = parts
        return cls(owner=owner, repo=repo, ref=ref, path="/".join(path_parts))

    def tarball_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.owner}/{self.repo}/tarball/{self.ref}"
        )
