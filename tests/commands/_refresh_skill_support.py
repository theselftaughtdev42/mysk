"""Pure (non-monkeypatch) helpers and constants shared by the refresh tests.

The `run_refresh` fixture that drives the command lives in `conftest.py`; this
module holds the plain tarball/SKILL.md builders and URL constants.
"""

import io
import tarfile

_SOURCE_URL = "https://github.com/alice/cool-skills/tree/main/skills/my-skill"
_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/main"

_UPSTREAM_SKILL_MD = (
    "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"
)

_SOURCE_URL_A = "https://github.com/alice/cool-skills/tree/main/skills/skill-a"
_SOURCE_URL_B = "https://github.com/alice/cool-skills/tree/main/skills/skill-b"


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


def _standalone_skill_md(name: str = "my-skill", description: str = "mine") -> str:
    return (
        f"---\nname: {name}\ndescription: {description}\nmysk:\n  state: active\n---\n"
    )
