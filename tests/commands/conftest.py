"""Factory fixtures shared across the command tests.

Setup/monkeypatch-shaped helpers that were previously duplicated at module
scope in individual test files live here as factory fixtures, so call sites no
longer thread `monkeypatch` by hand. Names are command-prefixed wherever a bare
name would otherwise collide in this shared namespace (`run_deploy` vs
`run_refresh`). Pure, non-monkeypatch builders stay as plain functions in the
per-command `_*_support.py` modules instead.
"""

import pytest
from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import deploy as deploy_cmd
from mysk.commands import import_skill as import_cmd
from mysk.commands import refresh_skill as refresh_cmd
from tests.conftest import QuestionaryStub, patch_skill_sources

runner = CliRunner()


def _answer(value: object):
    """Build a questionary-prompt stand-in whose `ask()` returns *value*."""
    return type("Q", (), {"ask": staticmethod(lambda: value)})()


# --- import_skill: questionary prompt mocks ---------------------------------


@pytest.fixture
def mock_select(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that patches `questionary.select` to answer *answer*."""

    def _mock(answer: object) -> None:
        monkeypatch.setattr(
            import_cmd.questionary, "select", lambda *a, **kw: _answer(answer)
        )

    return _mock


@pytest.fixture
def mock_text(monkeypatch: pytest.MonkeyPatch):
    """Return a factory that patches `questionary.text` to answer *answer*."""

    def _mock(answer: str) -> None:
        monkeypatch.setattr(
            import_cmd.questionary, "text", lambda *a, **kw: _answer(answer)
        )

    return _mock


@pytest.fixture
def mock_checkbox(monkeypatch: pytest.MonkeyPatch):
    """Return a factory patching `questionary.checkbox` to answer *answers*.

    The factory returns a dict that captures the `choices` handed to the
    picker, so tests can inspect each choice's disabled state at the CLI seam.
    """

    def _mock(answers: list[str]) -> dict:
        captured: dict = {}

        def fake_checkbox(*a, **kw):
            captured["choices"] = kw.get("choices")
            return _answer(answers)

        monkeypatch.setattr(import_cmd.questionary, "checkbox", fake_checkbox)
        return captured

    return _mock


# --- deploy -----------------------------------------------------------------


@pytest.fixture
def run_deploy(monkeypatch: pytest.MonkeyPatch):
    """Return a helper that patches deploy's sources and invokes `mysk deploy`."""

    def _run(
        targets=(),
        skills=(),
        questionary_stub=None,
        reconcile_fn=None,
        extra_args=(),
        suppress_ensure_dir=True,
    ):
        patch_skill_sources(monkeypatch, deploy_cmd, targets=targets, skills=skills)
        if suppress_ensure_dir:
            monkeypatch.setattr(deploy_cmd, "_ensure_target_dir", lambda path: None)
        if questionary_stub is not None:
            monkeypatch.setattr(deploy_cmd, "questionary", questionary_stub)
        if reconcile_fn is not None:
            monkeypatch.setattr(deploy_cmd, "reconcile_skill", reconcile_fn)
        return runner.invoke(app, ["deploy", *extra_args])

    return _run


@pytest.fixture
def capture_skill_choices(run_deploy):
    """Return a helper mapping each skill choice's name to its disabled reason."""

    def _capture(*, targets, skills, skill_answer=None):
        stub = QuestionaryStub(skill_answer if skill_answer is not None else [])
        run_deploy(targets=targets, skills=skills, questionary_stub=stub)
        skill_choices = stub.choices_for("skill")
        return {choice.value.skill.name: choice.disabled for choice in skill_choices}

    return _capture


# --- refresh_skill ----------------------------------------------------------


@pytest.fixture
def run_refresh(monkeypatch: pytest.MonkeyPatch):
    """Return a helper that patches refresh's confirm/prompts and invokes it."""

    def _run(extra_args=(), confirm_fn=None, questionary_stub=None):
        monkeypatch.setattr(
            refresh_cmd,
            "confirm",
            confirm_fn if confirm_fn is not None else lambda msg, *, yes: True,
        )
        if questionary_stub is not None:
            monkeypatch.setattr(refresh_cmd, "questionary", questionary_stub)
        return runner.invoke(app, ["refresh", *extra_args])

    return _run
