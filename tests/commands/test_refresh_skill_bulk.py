import httpx
import respx

from tests.commands._refresh_skill_support import (
    _SOURCE_URL_A,
    _SOURCE_URL_B,
    _TARBALL_URL,
    _installed_skill_md,
    _make_tarball,
    _standalone_skill_md,
)
from tests.conftest import QuestionaryStub


def test_refresh_all_and_name_errors(library, run_refresh):
    result = run_refresh(extra_args=["--all", "my-skill"])

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_refresh_all_no_imported_skills(library, run_refresh):
    skill_dir = library / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(_standalone_skill_md())

    result = run_refresh(extra_args=["--all"])

    assert result.exit_code == 0
    assert "no imported" in result.output.lower()


@respx.mock
def test_refresh_all_clean_path(library, run_refresh):
    (library / "skill-a").mkdir()
    (library / "skill-a" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-a", source=_SOURCE_URL_A)
    )
    (library / "skill-b").mkdir()
    (library / "skill-b" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-b", source=_SOURCE_URL_B)
    )

    upstream_a = "---\nname: skill-a\ndescription: improved a\n---\n# skill-a\n"
    upstream_b = "---\nname: skill-b\ndescription: improved b\n---\n# skill-b\n"
    respx.get(_TARBALL_URL).mock(
        side_effect=[
            httpx.Response(200, content=_make_tarball("skills/skill-a", upstream_a)),
            httpx.Response(200, content=_make_tarball("skills/skill-b", upstream_b)),
        ]
    )

    result = run_refresh(extra_args=["--all"])

    assert result.exit_code == 0, result.output
    assert "description: improved a" in (library / "skill-a" / "SKILL.md").read_text()
    assert "description: improved b" in (library / "skill-b" / "SKILL.md").read_text()


@respx.mock
def test_refresh_all_mixed_modified(library, run_refresh):
    _source_clean = "https://github.com/alice/cool-skills/tree/main/skills/skill-clean"
    _source_dirty = "https://github.com/alice/cool-skills/tree/main/skills/skill-dirty"

    (library / "skill-clean").mkdir()
    (library / "skill-clean" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-clean", source=_source_clean)
    )
    (library / "skill-dirty").mkdir()
    (library / "skill-dirty" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-dirty", source=_source_dirty, modified=True)
    )

    upstream_clean = (
        "---\nname: skill-clean\ndescription: updated clean\n---\n# skill-clean\n"
    )
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/skill-clean", upstream_clean)
        )
    )

    result = run_refresh(extra_args=["--all"])

    assert result.exit_code == 0, result.output
    assert (
        "description: updated clean"
        in (library / "skill-clean" / "SKILL.md").read_text()
    )
    assert "needs review" in result.output.lower()
    assert "skill-dirty" in result.output


@respx.mock
def test_refresh_bulk_flag_refreshes_named_subset_without_picker(library, run_refresh):
    (library / "skill-a").mkdir()
    (library / "skill-a" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-a", source=_SOURCE_URL_A)
    )
    (library / "skill-b").mkdir()
    (library / "skill-b" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-b", source=_SOURCE_URL_B)
    )

    upstream_a = "---\nname: skill-a\ndescription: improved a\n---\n# skill-a\n"
    respx.get(_TARBALL_URL).mock(
        return_value=httpx.Response(
            200, content=_make_tarball("skills/skill-a", upstream_a)
        )
    )

    stub = QuestionaryStub()

    result = run_refresh(
        extra_args=["--bulk", "skill-a"],
        questionary_stub=stub,
    )

    assert result.exit_code == 0, result.output
    assert stub.prompted_messages() == []
    assert "description: improved a" in (library / "skill-a" / "SKILL.md").read_text()
    assert (
        "description: does cool things"
        in (library / "skill-b" / "SKILL.md").read_text()
    )


def test_refresh_bulk_unknown_skill_errors(library, run_refresh):
    (library / "skill-a").mkdir()
    (library / "skill-a" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-a", source=_SOURCE_URL_A)
    )

    result = run_refresh(extra_args=["--bulk", "ghost"])

    assert result.exit_code == 1
    assert "ghost" in result.output


def test_refresh_bulk_standalone_skill_name_errors(library, run_refresh):
    (library / "self").mkdir()
    (library / "self" / "SKILL.md").write_text(_standalone_skill_md(name="self"))

    result = run_refresh(extra_args=["--bulk", "self"])

    assert result.exit_code == 1
    assert "self" in result.output


def test_refresh_name_and_bulk_together_exit_with_mutual_exclusivity_error(
    library, run_refresh
):
    (library / "skill-a").mkdir()
    (library / "skill-a" / "SKILL.md").write_text(
        _installed_skill_md(name="skill-a", source=_SOURCE_URL_A)
    )

    result = run_refresh(extra_args=["skill-a", "--bulk", "skill-a"])

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output
