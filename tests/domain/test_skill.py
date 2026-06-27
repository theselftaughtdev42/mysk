import pytest

from mysk.domain import LifecycleState, MyskBlock, Provenance, Skill
from mysk.io import frontmatter


def test_extra_fields_defaults_to_empty():
    skill = Skill(name="foo", description="does a thing")

    assert skill.extra_fields == {}


def test_from_frontmatter_collects_unknown_keys_into_extra_fields():
    skill = Skill.from_frontmatter(
        {
            "name": "foo",
            "description": "bar",
            "license": "MIT",
            "allowed-tools": ["bash"],
        }
    )

    assert skill.extra_fields == {"license": "MIT", "allowed-tools": ["bash"]}


def test_to_frontmatter_emits_extra_fields_between_description_and_mysk():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
        extra_fields={"license": "MIT"},
    )

    result = skill.to_frontmatter()
    keys = list(result.keys())

    assert result["license"] == "MIT"
    assert keys.index("description") < keys.index("license") < keys.index("mysk")


def test_skill_with_extra_fields_survives_round_trip():
    skill = Skill(
        name="foo",
        description="bar",
        mysk=MyskBlock(state=LifecycleState.ACTIVE),
        extra_fields={"license": "MIT", "allowed-tools": ["bash"]},
    )

    assert Skill.from_frontmatter(skill.to_frontmatter()) == skill


def test_known_keys_excluded_from_extra_fields():
    skill = Skill.from_frontmatter(
        {
            "name": "foo",
            "description": "bar",
            "mysk": {"state": "active"},
            "license": "MIT",
        }
    )

    assert "name" not in skill.extra_fields
    assert "description" not in skill.extra_fields
    assert "mysk" not in skill.extra_fields
    assert skill.extra_fields == {"license": "MIT"}


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
            provenance=Provenance(
                source="https://github.com/owner/repo",
                modified=True,
            ),
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
            provenance=Provenance(
                source="https://github.com/owner/repo", modified=False
            ),
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
        MyskBlock()  # type: ignore[call-arg]


def test_reads_owned_active_skill():
    skill = Skill.from_frontmatter(
        {"name": "foo", "description": "bar", "mysk": {"state": "active"}}
    )

    assert skill.mysk is not None
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

    assert skill.mysk is not None
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
        Skill(
            name="a", description="d", mysk=MyskBlock(state=LifecycleState.EXPERIMENTAL)
        ),
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


def test_renamed_import_writes_upstream_name():
    skill = Skill(
        name="local-name",
        description="bar",
        mysk=MyskBlock(
            state=LifecycleState.ACTIVE,
            provenance=Provenance(
                source="https://github.com/a/b",
                modified=False,
                upstream_name="original-name",
            ),
        ),
    )

    block = skill.to_frontmatter()["mysk"]

    assert block["upstream_name"] == "original-name"


def test_upstream_name_round_trips_through_frontmatter():
    skill = Skill(
        name="local-name",
        description="bar",
        mysk=MyskBlock(
            state=LifecycleState.ACTIVE,
            provenance=Provenance(
                source="https://github.com/a/b",
                modified=False,
                upstream_name="original-name",
            ),
        ),
    )

    assert Skill.from_frontmatter(skill.to_frontmatter()) == skill


def test_skill_survives_full_disk_round_trip():
    skill = Skill(
        name="caveman-review",
        description="Ultra-compressed code review",
        mysk=MyskBlock(
            state=LifecycleState.EXPERIMENTAL,
            provenance=Provenance(
                source="https://github.com/owner/repo", modified=False
            ),
        ),
    )
    body = "# caveman-review\n\nDo the thing.\n"

    on_disk = frontmatter.write(skill.to_frontmatter(), body)
    data, body_again = frontmatter.read(on_disk)

    assert Skill.from_frontmatter(data) == skill
    assert body_again == body
