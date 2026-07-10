"""Pure (non-monkeypatch) helpers and fixtures shared by the import-skill tests.

Fixture-shaped helpers (the questionary mocks) live in `conftest.py`; this
module holds the plain builders and constants that carry no `monkeypatch`.
"""

import io
import tarfile
from pathlib import Path

_RAW_URL = "https://github.com/alice/cool-skills/tree/main/skills/my-skill"
_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/main"
_REPO_ROOT_URL = "https://github.com/alice/cool-skills"
_REPO_ROOT_TARBALL_URL = "https://api.github.com/repos/alice/cool-skills/tarball/HEAD"

_SKILL_MD = "---\nname: my-skill\ndescription: does cool things\n---\n# my-skill\n"
_SKILL_A_MD = "---\nname: skill-a\ndescription: skill a\n---\n# skill-a\n"
_SKILL_B_MD = "---\nname: skill-b\ndescription: skill b\n---\n# skill-b\n"
_SKILL_MD_WITH_EXTRAS = (
    "---\nname: my-skill\ndescription: does cool things\n"
    "license: MIT\nallowed-tools:\n- bash\n---\n# my-skill\n"
)


def _make_tarball(skill_dir_name: str, skill_md: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = skill_md.encode()
        info = tarfile.TarInfo(name=f"repo-abc/{skill_dir_name}/SKILL.md")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _make_multi_tarball(skills: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for dir_name, content in skills.items():
            data = content.encode()
            info = tarfile.TarInfo(name=f"repo-abc/{dir_name}/SKILL.md")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _imported_skill_md(name: str, source: str, upstream_name: str | None = None) -> str:
    extra = f"  upstream_name: {upstream_name}\n" if upstream_name else ""
    return (
        f"---\nname: {name}\ndescription: d\nmysk:\n  state: active\n"
        f"  source: {source}\n  modified: false\n{extra}---\n"
    )


def _disabled_reason(choice) -> str | None:
    return getattr(choice, "disabled", None)


def _make_local_skill_dir(
    parent: Path, name: str, description: str = "a skill"
) -> None:
    d = parent / name
    d.mkdir()
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n"
    )
