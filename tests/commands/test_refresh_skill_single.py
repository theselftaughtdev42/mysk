import httpx
import respx

from tests.commands._refresh_skill_support import (
    _SOURCE_URL,
    _TARBALL_URL,
    _UPSTREAM_SKILL_MD,
    _installed_skill_md,
    _make_tarball,
    _standalone_skill_md,
)
from tests.conftest import QuestionaryStub


def test_refresh_no_args_shows_picker_with_disabled_reasons(library, run_refresh):
    (library / "self").mkdir()
    (library / "self" / "SKILL.md").write_text(
        _standalone_skill_md(name="self", description="a standalone skill")
    )
    (library / "dirty").mkdir()
    (library / "dirty" / "SKILL.md").write_text(
        _installed_skill_md(
            name="dirty",
            source="https://github.com/alice/cool-skills/tree/main/skills/dirty",
            modified=True,
        )
    )
    (library / "clean").mkdir()
    (library / "clean" / "SKILL.md").write_text(
        _installed_skill_md(
            name="clean",
            source="https://github.com/alice/cool-skills/tree/main/skills/clean",
        )
    )

    stub = QuestionaryStub([])

    result = run_refresh(questionary_stub=stub)

    assert result.exit_code == 0
    reasons = {c.value.dir.name: c.disabled for c in stub.choices_for("refresh")}
    assert reasons["self"] == "no upstream — nothing to refresh"
    assert reasons["dirty"] == "modified — needs review before refresh"
    assert reasons["clean"] is None


def test_refresh_no_args_nothing_selected_exits_cleanly(library, run_refresh):
    (library / "clean").mkdir()
    (library / "clean" / "SKILL.md").write_text(_installed_skill_md(name="clean"))

    result = run_refresh(questionary_stub=QuestionaryStub([]))

    assert result.exit_code == 0
    assert "Nothing selected." in result.output


@respx.mock
def test_refresh_no_args_picker_refreshes_selected_skill(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    stub = QuestionaryStub(lambda choices: [choices[0].value])

    result = run_refresh(questionary_stub=stub)

    assert result.exit_code == 0, result.output
    assert "Refreshed" in result.output


@respx.mock
def test_refresh_success_message_goes_to_stdout(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = run_refresh(extra_args=["my-skill"])

    assert "Refreshed" in result.stdout


@respx.mock
def test_refresh_clean_updates_skill_directory(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "description: improved description" in text
    assert "state: active" in text
    assert f"source: {_SOURCE_URL}" in text
    assert "modified: false" in text


@respx.mock
def test_refresh_upstream_name_writes_to_local_dir(library, run_refresh):
    skill_dir = library / "local-name"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        _installed_skill_md(name="local-name", upstream_name="my-skill")
    )

    upstream_md = (
        "---\nname: my-skill\ndescription: upstream improved\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = run_refresh(extra_args=["local-name"])

    assert result.exit_code == 0, result.output
    assert (library / "local-name" / "SKILL.md").exists()
    assert not (library / "my-skill").exists()
    text = (library / "local-name" / "SKILL.md").read_text()
    assert "name: local-name" in text
    assert "description: upstream improved" in text
    assert "upstream_name: my-skill" in text


@respx.mock
def test_refresh_no_changes_skips_write_and_confirmation(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _UPSTREAM_SKILL_MD)
        )
    )

    mtime_before = (library / "my-skill" / "SKILL.md").stat().st_mtime

    confirm_calls = []

    def confirm_fn(message, *, yes):
        confirm_calls.append(yes)
        return True

    result = run_refresh(extra_args=["my-skill"], confirm_fn=confirm_fn)

    assert result.exit_code == 0, result.output
    assert "no changes" in result.output.lower()
    assert (library / "my-skill" / "SKILL.md").stat().st_mtime == mtime_before
    assert confirm_calls == []


@respx.mock
def test_refresh_declined_confirmation_leaves_content_unchanged(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = run_refresh(
        extra_args=["my-skill"],
        confirm_fn=lambda message, *, yes: False,
    )

    assert result.exit_code == 0, result.output
    assert "aborted" in result.output.lower()
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "description: does cool things" in text


@respx.mock
def test_refresh_yes_flag_skips_confirmation(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    confirm_calls = []

    def confirm_fn(message, *, yes):
        confirm_calls.append(yes)
        return True

    result = run_refresh(
        extra_args=["my-skill", "--yes"],
        confirm_fn=confirm_fn,
    )

    assert result.exit_code == 0, result.output
    assert confirm_calls == [True]
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "description: improved description" in text


@respx.mock
def test_refresh_updates_and_removes_extra_local_files_when_file_sets_differ(
    library, run_refresh
):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())
    (skill_dir / "extra.py").write_text("# extra file only in local copy\n")

    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", _UPSTREAM_SKILL_MD)
        )
    )

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code == 0, result.output
    assert not (library / "my-skill" / "extra.py").exists()
    assert (library / "my-skill" / "SKILL.md").exists()


@respx.mock
def test_refresh_takes_extra_fields_from_upstream(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_installed_skill_md())

    upstream_md = (
        "---\nname: my-skill\ndescription: improved description\n"
        "license: Apache-2.0\n---\n# my-skill\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/my-skill", upstream_md)
        )
    )

    result = run_refresh(extra_args=["my-skill"])

    assert result.exit_code == 0, result.output
    text = (library / "my-skill" / "SKILL.md").read_text()
    assert "license: Apache-2.0" in text
