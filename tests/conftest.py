"""Shared test support."""

from collections.abc import Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from mysk.domain import LifecycleState, MyskBlock, Provenance, Skill
from mysk.io.skills import InstalledSkill
from mysk.io.targets import Target


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point mysk at a temporary mysk home; return its Skill Library path.

    Sets `MYSK_HOME` to a temp directory so every command resolves the Skill
    Library to `<tmp>/skills`, and returns that (created) path for tests to read
    from and write to.
    """
    monkeypatch.setenv("MYSK_HOME", str(tmp_path))
    skills = tmp_path / "skills"
    skills.mkdir()
    return skills


def make_target(name: str, path: str | None = None) -> Target:
    """Build a Target; defaults to the conventional `/home/user/.<name>/skills`."""
    return Target(name=name, path=Path(path or f"/home/user/.{name}/skills"))


def make_skill(
    name: str,
    *,
    state: LifecycleState = LifecycleState.ACTIVE,
    source: str | None = None,
    modified: bool = False,
    description: str = "d",
    directory: Path | None = None,
) -> InstalledSkill:
    """Build an InstalledSkill with the given lifecycle state and provenance."""
    mysk = MyskBlock(
        state=state, provenance=Provenance(source=source, modified=modified)
    )
    return InstalledSkill(
        skill=Skill(name=name, description=description, mysk=mysk),
        mysk=mysk,
        dir=directory or Path(f"/fake/skills/{name}"),
    )


def patch_skill_sources(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
    *,
    library: Path = Path("/fake/skills"),
    targets: Sequence[Target] = (),
    skills: Sequence[InstalledSkill] = (),
) -> None:
    """Patch the `skill_library`/`discover_targets`/`load_skills` trio on *module*.

    Every command that reads from the Skill Library and Deployment Targets
    fakes these the same way; this collapses that three-line patch to one call.
    """
    monkeypatch.setattr(module, "skill_library", lambda: library)
    monkeypatch.setattr(module, "discover_targets", lambda: list(targets))
    monkeypatch.setattr(module, "load_skills", lambda _: (list(skills), []))


class QuestionaryStub:
    """Fake `questionary` module for driving a command's prompts in tests.

    Construct with the answers each `checkbox`/`select` call should return,
    in the order the Skill Operation Pathway asks them (e.g. targets, then
    skills; or key, then value). An answer may be a callable, invoked with
    the `choices` passed to that prompt, for answers that depend on what was
    offered (e.g. "select the first choice"). Calling a prompt past the last
    queued answer raises AssertionError, so tests asserting a prompt is never
    shown need no extra plumbing — just construct `QuestionaryStub()`.

    Every prompt's `(message, choices)` is recorded in `.calls`, and
    `.choices_for(keyword)` / `.prompted_messages()` cover the two things
    tests commonly need to inspect about what was asked.
    """

    def __init__(self, *answers: object) -> None:
        """Queue *answers*, one per expected `checkbox`/`select` call, in order."""
        self._answers = iter(answers)
        self.calls: list[SimpleNamespace] = []

    @staticmethod
    def Choice(  # noqa: N802 — matches questionary.Choice's constructor shape
        title: str, value: object = None, disabled: str | None = None
    ) -> SimpleNamespace:
        return SimpleNamespace(title=title, value=value, disabled=disabled)

    def _prompt(
        self, message: str, choices: list[Any] | None = None
    ) -> SimpleNamespace:
        self.calls.append(SimpleNamespace(message=message, choices=choices))
        try:
            answer = next(self._answers)
        except StopIteration:
            msg = f"unexpected prompt: {message!r} (no queued answer)"
            raise AssertionError(msg) from None
        if callable(answer):
            answer = answer(choices)
        return SimpleNamespace(ask=lambda: answer)

    def checkbox(
        self, message: str, choices: list[Any] | None = None
    ) -> SimpleNamespace:
        return self._prompt(message, choices)

    def select(self, message: str, choices: list[Any] | None = None) -> SimpleNamespace:
        return self._prompt(message, choices)

    def choices_for(self, keyword: str) -> list[Any]:
        """Return the choices from the first prompt whose message contains *keyword*."""
        return next(
            call.choices
            for call in self.calls
            if keyword.lower() in call.message.lower()
        )

    def prompted_messages(self) -> list[str]:
        """Return every prompt message shown, in order."""
        return [call.message for call in self.calls]
