"""Enforce single-backtick inline code in all docstrings (Google/Markdown style)."""

import ast
import re
from pathlib import Path

_DOUBLE_BACKTICK = re.compile(r"``")
_DOCSTRING_NODES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _has_double_backtick_docstring(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_NODES):
            continue
        doc = ast.get_docstring(node)
        if doc and _DOUBLE_BACKTICK.search(doc):
            return True
    return False


def _py_files() -> list[Path]:
    return sorted([*Path("src").rglob("*.py"), Path("skills.py")])


def test_detection_catches_double_backticks(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('def foo():\n    """Use ``x`` here."""\n')
    assert _has_double_backtick_docstring(bad)


def test_no_double_backticks_in_docstrings() -> None:
    violations = [str(p) for p in _py_files() if _has_double_backtick_docstring(p)]
    assert not violations, (
        f"RST-style double backticks found in docstrings: {violations}"
    )
