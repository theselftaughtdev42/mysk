import pytest
import pydantic

from mysk.domain import Provenance


def test_default_provenance_is_self_authored():
    assert Provenance().is_imported is False


def test_skill_with_source_is_imported():
    prov = Provenance(source="https://github.com/owner/repo", modified=True)

    assert prov.is_imported is True
    assert prov.source == "https://github.com/owner/repo"
    assert prov.modified is True


def test_provenance_rejects_non_bool_modified():
    with pytest.raises(pydantic.ValidationError):
        Provenance(source="https://x", modified="definitely")
