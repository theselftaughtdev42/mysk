from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import list as list_cmd
from mysk.domain import LifecycleState
from mysk.io.skills import InstalledSkill, SkillLoadError
from tests.conftest import make_skill, make_target, patch_skill_sources

runner = CliRunner()

_ACTIVE_SKILL = make_skill("foo", state=LifecycleState.ACTIVE)
_DEPRECATED_SKILL = make_skill("old", state=LifecycleState.DEPRECATED)
_IMPORTED_SKILL = make_skill("ext", source="https://example.com")
_LONG_URL_SKILL = make_skill(
    "longurl",
    source="https://github.com/someorg/somerepo/tree/main/skills/some-very-long-skill",
)
_MODIFIED_SKILL = make_skill("mod", source="https://example.com", modified=True)
_GITHUB_NO_REPO_SKILL = make_skill("solo", source="https://github.com/solo")
_NO_MYSK_BLOCK_SKILL = SkillLoadError(
    path=Path("/fake/skills/legacy/SKILL.md"),
    schema_error="missing mysk block",
)
_BAD_SKILL = SkillLoadError(
    path=Path("/fake/skills/bad/SKILL.md"),
    schema_error="mysk block missing state",
)
_CLAUDE_TARGET = make_target("claude")


def _cells(output, name):
    """Return the trimmed cells of the rendered table row whose Name cell is *name*."""
    for line in output.splitlines():
        parts = line.split("│")
        if len(parts) > 1 and parts[1].strip() == name:
            return [p.strip() for p in parts[1:-1]]
    msg = f"no table row for {name!r}"
    raise AssertionError(msg)


def _run(monkeypatch, targets=(), skills=(), deployed_fn=None, args=()):
    installed = [s for s in skills if isinstance(s, InstalledSkill)]
    errors = [s for s in skills if isinstance(s, SkillLoadError)]
    patch_skill_sources(monkeypatch, list_cmd, targets=targets)
    monkeypatch.setattr(list_cmd, "load_skills", lambda _: (installed, errors))
    if deployed_fn is not None:
        monkeypatch.setattr(list_cmd, "is_deployed", deployed_fn)
    return runner.invoke(app, ["list", *args])


def test_has_upstream_column_appears_in_list_output(monkeypatch):
    result = _run(monkeypatch, skills=[_ACTIVE_SKILL])
    assert result.exit_code == 0
    assert "Has Upstream" in result.output


def test_table_goes_to_stdout(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "foo" in result.stdout


def test_deployed_skill_appears_in_table_with_target_label(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "claude" in result.output


def test_undeployed_skill_shows_em_dash_in_deployed_to_column(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: False,
    )

    assert result.exit_code == 0
    assert "foo" in result.output
    assert "—" in result.output


def test_hint_shown_when_no_deployment_targets_exist(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[],
        skills=[_ACTIVE_SKILL],
    )

    assert result.exit_code == 0
    assert "mysk deploy" in result.output


def test_non_deployable_skill_shows_path_when_deployed(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "claude" in result.output


def test_non_deployable_skill_shows_em_dash_when_not_deployed(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_DEPRECATED_SKILL],
        deployed_fn=lambda t, s, lib: False,
    )

    assert result.exit_code == 0
    assert "—" in result.output


def test_no_mysk_block_skill_shows_inline_status(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_NO_MYSK_BLOCK_SKILL],
    )

    assert result.exit_code == 0
    assert "no mysk block" in result.output


def test_malformed_skill_shows_malformed_inline_status(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_BAD_SKILL],
    )

    assert result.exit_code == 0
    assert "malformed" in result.output


def test_standalone_skill_shows_no_in_has_upstream(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "no" in result.output


def test_upstream_skill_shows_yes_in_has_upstream(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_IMPORTED_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "yes" in result.output


def test_modified_column_reflects_modified_state_per_skill(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_MODIFIED_SKILL, _IMPORTED_SKILL, _ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: True,
    )

    assert result.exit_code == 0
    assert "Modified" in result.output
    # column order: Name, Status, Has Upstream, Modified, Deployed To
    assert _cells(result.output, "mod")[3] == "yes"  # upstream, modified
    assert _cells(result.output, "ext")[3] == "no"  # upstream, clean
    assert _cells(result.output, "foo")[3] == "—"  # standalone: not applicable


def test_show_upstream_flag_swaps_has_upstream_for_url_column(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_IMPORTED_SKILL, _ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: False,
        args=["--show-upstream"],
    )

    assert result.exit_code == 0
    assert "Upstream URL" in result.output
    assert "Has Upstream" not in result.output
    # column order: Name, Status, Upstream URL, Modified, Deployed To
    assert _cells(result.output, "ext")[2] == "https://example.com"
    assert _cells(result.output, "foo")[2] == "—"  # standalone: no URL
    # the Modified column is unaffected by the flag
    assert _cells(result.output, "ext")[3] == "no"
    assert _cells(result.output, "foo")[3] == "—"


def test_show_upstream_renders_repo_slug_for_github_source(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_LONG_URL_SKILL, _ACTIVE_SKILL],
        deployed_fn=lambda t, s, lib: False,
        args=["--show-upstream"],
    )

    assert result.exit_code == 0
    # column order: Name, Status, Upstream URL, Modified, Deployed To
    # the full github source is compacted to its owner/repo Repo Slug
    assert _cells(result.output, "longurl")[2] == "someorg/somerepo"
    assert _cells(result.output, "foo")[2] == "—"  # standalone: still no URL


def test_show_upstream_renders_full_url_without_truncation(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_LONG_URL_SKILL],
        deployed_fn=lambda t, s, lib: False,
        args=["--show-upstream"],
    )

    assert result.exit_code == 0
    # a truncated cell would show Rich's ellipsis; the URL must survive in full
    assert "…" not in result.output


def test_upstream_url_cell_renders_a_clickable_hyperlink():
    # the CliRunner console is non-tty and strips hyperlinks, so render the cell
    # through a forced-terminal console to observe the OSC 8 escape a terminal
    # uses to make the URL clickable even when the cell folds across lines
    url = "https://github.com/someorg/somerepo/tree/main/skills/some-very-long-skill"
    console = Console(force_terminal=True, width=200)
    with console.capture() as capture:
        console.print(list_cmd._upstream_url_cell(url))
    rendered = capture.get()

    assert "\x1b]8;" in rendered  # OSC 8 hyperlink sequence
    assert url in rendered  # link target is the full source URL


def test_show_upstream_falls_back_to_full_url_when_source_has_no_repo(monkeypatch):
    result = _run(
        monkeypatch,
        targets=[_CLAUDE_TARGET],
        skills=[_GITHUB_NO_REPO_SKILL],
        deployed_fn=lambda t, s, lib: False,
        args=["--show-upstream"],
    )

    assert result.exit_code == 0
    # a github URL with no repo segment can't compact to owner/repo, so the
    # cell degrades gracefully to the full stored URL rather than crashing
    assert _cells(result.output, "solo")[2] == "https://github.com/solo"


def test_malformed_skill_shows_em_dash_in_upstream_and_modified(monkeypatch):
    result = _run(monkeypatch, targets=[_CLAUDE_TARGET], skills=[_BAD_SKILL])

    assert result.exit_code == 0
    # column order: Name, Status, Has Upstream, Modified, Deployed To
    cells = _cells(result.output, "bad")
    assert cells[2] == "—"  # Has Upstream
    assert cells[3] == "—"  # Modified
