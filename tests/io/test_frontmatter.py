from mysk.io import frontmatter

SKILL_MD = """---
name: foo
description: does a thing
mysk:
  state: experimental
  source: https://github.com/owner/repo
  modified: true
---
# Foo

Body text here.
"""


def test_read_separates_frontmatter_and_body():
    data, body = frontmatter.read(SKILL_MD)

    assert data["name"] == "foo"
    assert data["mysk"]["state"] == "experimental"
    assert "# Foo" in body


def test_mysk_block_round_trips_without_data_loss():
    data, body = frontmatter.read(SKILL_MD)

    rebuilt = frontmatter.write(data, body)
    data_again, body_again = frontmatter.read(rebuilt)

    assert data_again == data
    assert body_again == body


def test_write_then_read_preserves_arbitrary_data():
    data = {"name": "x", "description": "y", "mysk": {"state": "deprecated"}}
    body = "# Heading\n\ncontent\n"

    data_again, body_again = frontmatter.read(frontmatter.write(data, body))

    assert data_again == data
    assert body_again == body


def test_document_without_frontmatter_is_all_body():
    text = "# No frontmatter here\n\njust prose\n"

    data, body = frontmatter.read(text)

    assert data == {}
    assert body == text
