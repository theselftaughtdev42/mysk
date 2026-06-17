import pytest

from mysk.domain import LifecycleState, MyskBlock, Provenance, Skill
from mysk.io import frontmatter


def test_unmigrated_skill_has_no_mysk_block():
    skill = Skill(name="foo", description="does a thing")

    assert skill.mysk is None


def test_unmigrated_skill_writes_no_mysk_block():
    skill = Skill(name="foo", description="does a thing")

    assert skill.to_frontmatter() == {"name": "foo", "description": "does a thing"}


def test_owned_active_skill_writes_only_state():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
    )

    assert skill.to_frontmatter()["mysk"] == {"state": "active"}


def test_experimental_skill_writes_state():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(state=LifecycleState.EXPERIMENTAL),
    )

    assert skill.to_frontmatter()["mysk"]["state"] == "experimental"


def test_imported_skill_writes_source_and_modified():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(
            state=LifecycleState.EXPERIMENTAL,
            provenance=Provenance(source="https://github.com/owner/repo", modified=True),
        ),
    )

    block = skill.to_frontmatter()["mysk"]

    assert block["source"] == "https://github.com/owner/repo"
    assert block["modified"] is True


def test_clean_import_still_writes_modified_false():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(
            state=LifecycleState.ACTIVE,
            provenance=Provenance(source="https://github.com/owner/repo", modified=False),
        ),
    )

    assert skill.to_frontmatter()["mysk"]["modified"] is False


def test_skill_without_mysk_key_is_unmigrated():
    skill = Skill.from_frontmatter({"name": "foo", "description": "bar"})

    assert skill.mysk is None


def test_existing_mysk_block_without_state_is_rejected():
    with pytest.raises(ValueError):
        Skill.from_frontmatter({"name": "foo", "description": "bar", "mysk": {}})


def test_mysk_block_requires_state():
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        MyskBlock()


def test_reads_owned_active_skill():
    skill = Skill.from_frontmatter(
        {"name": "foo", "description": "bar", "mysk": {"state": "active"}}
    )

    assert skill.mysk.state is LifecycleState.ACTIVE
    assert skill.mysk.provenance.is_imported is False


def test_reads_imported_experimental_skill():
    skill = Skill.from_frontmatter(
        {
            "name": "foo",
            "description": "bar",
            "mysk": {
                "state": "experimental",
                "source": "https://github.com/owner/repo",
                "modified": True,
            },
        }
    )

    assert skill.mysk.state is LifecycleState.EXPERIMENTAL
    assert skill.mysk.provenance.source == "https://github.com/owner/repo"
    assert skill.mysk.provenance.modified is True


def test_unknown_state_value_is_rejected():
    with pytest.raises(ValueError):
        Skill.from_frontmatter(
            {"name": "foo", "description": "bar", "mysk": {"state": "bogus"}}
        )


@pytest.mark.parametrize(
    "skill",
    [
        Skill(name="a", description="d"),
        Skill(name="a", description="d", mysk=MyskBlock(state=LifecycleState.ACTIVE)),
        Skill(name="a", description="d", mysk=MyskBlock(state=LifecycleState.INIT)),
        Skill(
            name="a", description="d", mysk=MyskBlock(state=LifecycleState.DEPRECATED)
        ),
        Skill(
            name="a",
            description="d",
            mysk=MyskBlock(
                state=LifecycleState.EXPERIMENTAL,
                provenance=Provenance(source="https://x/y", modified=False),
            ),
        ),
    ],
)
def test_skill_survives_frontmatter_round_trip(skill):
    assert Skill.from_frontmatter(skill.to_frontmatter()) == skill


def test_skill_survives_full_disk_round_trip():
    skill = Skill(
        name="caveman-review",
        description="Ultra-compressed code review",
        mysk=MyskBlock(
            state=LifecycleState.EXPERIMENTAL,
            provenance=Provenance(source="https://github.com/owner/repo", modified=False),
        ),
    )
    body = "# caveman-review\n\nDo the thing.\n"

    on_disk = frontmatter.write(skill.to_frontmatter(), body)
    data, body_again = frontmatter.read(on_disk)

    assert Skill.from_frontmatter(data) == skill
    assert body_again == body
