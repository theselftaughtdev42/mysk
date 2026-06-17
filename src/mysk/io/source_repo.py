from __future__ import annotations

import tomllib
from pathlib import Path


def find_source_repo(start: Path | None = None) -> Path | None:
    """Find the mysk source repo root by walking up from ``start``.

    Authoring commands are only available inside the source clone. The signal
    is a ``pyproject.toml`` declaring ``name = "mysk"`` (ADR-0002); a deployed
    install has no such file on the path, so this returns ``None`` there.
    """
    origin = (start or Path(__file__)).resolve()
    for parent in (origin, *origin.parents):
        pyproject = parent / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            data = tomllib.loads(pyproject.read_text())
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if data.get("project", {}).get("name") == "mysk":
            return parent
    return None
