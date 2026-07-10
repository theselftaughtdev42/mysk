import pydantic
import pytest

from mysk.domain import Provenance


def test_default_provenance_has_no_upstream():
    assert Provenance().has_upstream is False


def test_provenance_with_source_has_upstream():
    prov = Provenance(source="https://github.com/owner/repo", modified=True)

    assert prov.has_upstream is True
    assert prov.source == "https://github.com/owner/repo"
    assert prov.modified is True


def test_provenance_rejects_non_bool_modified():
    with pytest.raises(pydantic.ValidationError):
        Provenance(source="https://x", modified="definitely")


def test_provenance_stores_upstream_name():
    prov = Provenance(source="https://github.com/a/b", upstream_name="original-name")

    assert prov.upstream_name == "original-name"


def test_provenance_upstream_name_defaults_to_none():
    assert Provenance().upstream_name is None
