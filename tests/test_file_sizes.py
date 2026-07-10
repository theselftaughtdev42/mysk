"""Enforce a 500-line ceiling on every test module.

Large test files are harder for humans to navigate and cost more tokens for AI
agents to load into context when working on a single scenario. This walks every
`test_*.py` under `tests/` and names every file over the limit, mirroring the
collect-all-violations style of `test_docstring_style.py`. The limit is a hard
one: there is deliberately no per-file exemption mechanism.
"""

from pathlib import Path

_LINE_LIMIT = 500


def _line_count(path: Path) -> int:
    return len(path.read_text().splitlines())


def _test_modules() -> list[Path]:
    return sorted(Path("tests").rglob("test_*.py"))


def test_oversized_file_is_detected(tmp_path: Path) -> None:
    big = tmp_path / "test_big.py"
    big.write_text("x = 1\n" * (_LINE_LIMIT + 1))
    assert _line_count(big) > _LINE_LIMIT


def test_no_test_file_exceeds_line_limit() -> None:
    violations = [
        f"{path} ({_line_count(path)} lines)"
        for path in _test_modules()
        if _line_count(path) > _LINE_LIMIT
    ]
    assert not violations, (
        f"test files over the {_LINE_LIMIT}-line limit — split them "
        f"(see ADR-0010): {violations}"
    )
