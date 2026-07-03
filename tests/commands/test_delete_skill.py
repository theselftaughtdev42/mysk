from pathlib import Path

from typer.testing import CliRunner

from mysk.cli import app
from mysk.commands import delete_skill as delete_cmd
from mysk.io.targets import Target
from tests.conftest import QuestionaryStub

runner = CliRunner()


def _make_skill(library: Path, name: str, *, modified: bool = False) -> Path:
    skill_dir = library / name
    skill_dir.mkdir(parents=True)
    source = f"https://github.com/alice/skills/tree/main/skills/{name}"
    mysk_block = (
        f"mysk:\n  state: active\n  source: {source}\n"
        f"  modified: {str(modified).lower()}\n"
    )
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name} skill\n{mysk_block}---\n"
    )
    return skill_dir


def _confirm(answer: bool):
    return lambda message, *, yes: answer


def _capture_confirm(captured: dict, *, answer: bool = True):
    def confirm_fn(message, *, yes):
        captured["message"] = message
        return answer

    return confirm_fn


def _run(
    monkeypatch,
    library,
    targets=(),
    confirm_fn=None,
    questionary_stub=None,
    extra_args=(),
):
    monkeypatch.setenv("MYSK_SKILLS_DIR", str(library))
    monkeypatch.setattr(delete_cmd, "discover_targets", lambda: list(targets))
    if confirm_fn is not None:
        monkeypatch.setattr(delete_cmd, "confirm", confirm_fn)
    if questionary_stub is not None:
        monkeypatch.setattr(delete_cmd, "questionary", questionary_stub)
    return runner.invoke(app, ["delete", *extra_args])


def test_skill_not_found_exits_with_error(monkeypatch, tmp_path):
    result = _run(monkeypatch, library=tmp_path, extra_args=["nonexistent"])

    assert result.exit_code != 0
    assert "nonexistent" in result.output


def test_confirmed_delete_removes_skill_from_library_and_unlinks_deployed_symlinks(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    skill_dir = _make_skill(library, "foo")

    target_skills = tmp_path / "agent" / "skills"
    target_skills.mkdir(parents=True)
    symlink = target_skills / "foo"
    symlink.symlink_to(skill_dir)

    target = Target(name="agent", path=target_skills)

    result = _run(
        monkeypatch,
        library=library,
        targets=[target],
        confirm_fn=_confirm(True),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not (library / "foo").exists()
    assert not symlink.exists()


def test_declined_confirmation_aborts_without_deleting(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_confirm(False),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert (library / "foo").exists()


def test_yes_flag_skips_confirmation_and_deletes(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    confirm_calls = []

    def confirm_fn(message, *, yes):
        confirm_calls.append(yes)
        return True

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=confirm_fn,
        extra_args=["foo", "--yes"],
    )

    assert result.exit_code == 0
    assert confirm_calls == [True]
    assert not (library / "foo").exists()


def test_modified_skill_includes_warning_in_confirmation_message(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo", modified=True)

    captured: dict = {}
    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_capture_confirm(captured),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert "modified" in captured.get("message", "").lower()


def test_skill_with_no_deployments_still_deleted_from_library(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    result = _run(
        monkeypatch,
        library=library,
        targets=[],
        confirm_fn=_confirm(True),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not (library / "foo").exists()


def test_foreign_symlink_in_target_is_left_untouched(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    foreign_skill = tmp_path / "foreign" / "foo"
    foreign_skill.mkdir(parents=True)

    target_skills = tmp_path / "agent" / "skills"
    target_skills.mkdir(parents=True)
    symlink = target_skills / "foo"
    symlink.symlink_to(foreign_skill)

    target = Target(name="agent", path=target_skills)

    result = _run(
        monkeypatch,
        library=library,
        targets=[target],
        confirm_fn=_confirm(True),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not (library / "foo").exists()
    assert symlink.exists()


def test_invalid_name_exits_with_error(monkeypatch, tmp_path):
    result = _run(monkeypatch, library=tmp_path, extra_args=["../escape"])

    assert result.exit_code != 0
    assert "Error" in result.output


def test_skill_dir_without_skill_md_treated_as_unmodified(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "bare").mkdir()

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_confirm(True),
        extra_args=["bare"],
    )

    assert result.exit_code == 0
    assert not (library / "bare").exists()


def test_declined_confirmation_on_bare_dir_leaves_it_in_place(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    (library / "bare").mkdir()

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_confirm(False),
        extra_args=["bare"],
    )

    assert result.exit_code == 0
    assert (library / "bare").exists()


def test_malformed_skill_md_treated_as_unmodified(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    skill_dir = library / "foo"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nnot: valid: yaml: [\n")

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_confirm(True),
        extra_args=["foo"],
    )

    assert result.exit_code == 0
    assert not (library / "foo").exists()


def test_bulk_flag_deletes_multiple_named_skills_after_one_confirmation(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")
    _make_skill(library, "bar", modified=True)
    _make_skill(library, "baz")

    captured: dict = {}
    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_capture_confirm(captured),
        extra_args=["--bulk", "foo,bar"],
    )

    assert result.exit_code == 0
    assert not (library / "foo").exists()
    assert not (library / "bar").exists()
    assert (library / "baz").exists()
    assert "foo" in captured["message"]
    assert "bar" in captured["message"]
    assert "2" in captured["message"]
    assert "warning" in result.output.lower()
    assert "bar" in result.output


def test_all_flag_deletes_every_skill_non_interactively(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")
    _make_skill(library, "bar")

    confirm_calls = []

    def confirm_fn(message, *, yes):
        confirm_calls.append(yes)
        return True

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=confirm_fn,
        extra_args=["--all", "--yes"],
    )

    assert result.exit_code == 0
    assert confirm_calls == [True]
    assert not (library / "foo").exists()
    assert not (library / "bar").exists()


def test_no_args_shows_picker_with_every_skill_selectable(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    skill_names = ["foo", "bar"]
    for name in skill_names:
        _make_skill(library, name)

    stub = QuestionaryStub(lambda choices: [choices[0].value])

    result = _run(
        monkeypatch,
        library=library,
        confirm_fn=_confirm(True),
        questionary_stub=stub,
        extra_args=[],
    )

    choices = stub.choices_for("skill")
    assert result.exit_code == 0
    assert all(choice.disabled is None for choice in choices)
    assert len(choices) == len(skill_names)


def test_no_args_picker_nothing_selected_exits_cleanly(monkeypatch, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    result = _run(
        monkeypatch,
        library=library,
        questionary_stub=QuestionaryStub([]),
        extra_args=[],
    )

    assert result.exit_code == 0
    assert "Nothing selected." in result.output
    assert (library / "foo").exists()


def test_name_and_bulk_together_exit_with_mutual_exclusivity_error(
    monkeypatch, tmp_path
):
    library = tmp_path / "library"
    library.mkdir()
    _make_skill(library, "foo")

    result = _run(
        monkeypatch,
        library=library,
        extra_args=["foo", "--bulk", "foo"],
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output
    assert (library / "foo").exists()
