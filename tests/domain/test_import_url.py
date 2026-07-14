import pytest

from mysk.domain.import_url import ImportUrl, RepoRootUrl


def test_parse_valid_url():
    url = ImportUrl.parse(
        "https://github.com/alice/cool-skills/tree/main/skills/my-skill"
    )

    assert url.owner == "alice"
    assert url.repo == "cool-skills"
    assert url.ref == "main"
    assert url.path == "skills/my-skill"
    assert url.skill_dir_name == "my-skill"


def test_parse_rejects_non_github_host():
    with pytest.raises(ValueError, match=r"Only github\.com URLs are supported"):
        ImportUrl.parse(
            "https://gitlab.com/alice/cool-skills/tree/main/skills/my-skill"
        )


def test_parse_rejects_malformed_url():
    with pytest.raises(ValueError, match="Expected a GitHub URL of the form"):
        ImportUrl.parse("https://github.com/alice/cool-skills")


def test_repo_root_url_parse_valid():
    url = RepoRootUrl.parse("https://github.com/alice/cool-skills")

    assert url.owner == "alice"
    assert url.repo == "cool-skills"


def test_repo_root_url_parses_repo_slug():
    url = RepoRootUrl.parse("alice/cool-skills")

    assert url.owner == "alice"
    assert url.repo == "cool-skills"


def test_repo_root_url_rejects_slug_with_extra_segments():
    with pytest.raises(ValueError, match="Expected a repo shorthand of the form"):
        RepoRootUrl.parse("alice/cool-skills/skills/foo")


@pytest.mark.parametrize("slug", ["alice/", "/cool-skills"])
def test_repo_root_url_rejects_slug_with_empty_segments(slug):
    with pytest.raises(ValueError, match="Expected a repo shorthand of the form"):
        RepoRootUrl.parse(slug)


def test_repo_root_url_rejects_non_github_host():
    with pytest.raises(ValueError, match=r"Only github\.com URLs are supported"):
        RepoRootUrl.parse("https://gitlab.com/alice/cool-skills")


def test_repo_root_url_rejects_url_with_path():
    with pytest.raises(ValueError, match="Expected a GitHub repo URL of the form"):
        RepoRootUrl.parse("https://github.com/alice/cool-skills/tree/main/skills/foo")


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com//repo",
        "https://github.com/owner/",
    ],
)
def test_repo_root_url_rejects_empty_segments(url):
    with pytest.raises(ValueError, match="Expected a GitHub repo URL of the form"):
        RepoRootUrl.parse(url)
