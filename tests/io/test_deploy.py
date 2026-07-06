import logging

from mysk.io.deploy import reconcile_skill, remove_skill


def test_fresh_destination_logs_symlink_creation(tmp_path, caplog):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)

    with caplog.at_level(logging.DEBUG, logger="mysk"):
        reconcile_skill(
            source, target, overwrite=False, skill_library_path=skill_library
        )

    assert any(str(target) in r.message for r in caplog.records)


def test_fresh_destination_creates_symlink_and_returns_deployed(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.outcome == "deployed"
    assert target.is_symlink()
    assert target.resolve() == source


def test_non_symlink_dir_without_overwrite_is_skipped(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)
    (target / "some-file.txt").write_text("existing content")

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.outcome == "skipped"
    assert not target.is_symlink()
    assert (target / "some-file.txt").exists()


def test_non_symlink_dir_without_overwrite_includes_skip_reason(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.reason is not None
    assert "--overwrite" in result.reason


def test_non_symlink_dir_with_overwrite_is_replaced_and_returns_overwritten(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)
    (target / "some-file.txt").write_text("existing content")

    result = reconcile_skill(
        source, target, overwrite=True, skill_library_path=skill_library
    )

    assert result.outcome == "overwritten"
    assert target.is_symlink()
    assert target.resolve() == source


def test_mysk_owned_symlink_is_replaced_and_returns_overwritten(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    old_skill = skill_library / "old-skill"
    old_skill.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(old_skill)

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.outcome == "overwritten"
    assert target.is_symlink()
    assert target.resolve() == source


def test_foreign_symlink_without_overwrite_is_skipped(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    foreign_dir = tmp_path / "foreign"
    foreign_dir.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign_dir)

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.outcome == "skipped"
    assert target.resolve() == foreign_dir


def test_foreign_symlink_skip_reason_mentions_ownership_and_overwrite(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    foreign_dir = tmp_path / "foreign"
    foreign_dir.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign_dir)

    result = reconcile_skill(
        source, target, overwrite=False, skill_library_path=skill_library
    )

    assert result.reason is not None
    assert "not owned by mysk" in result.reason
    assert "--overwrite" in result.reason


def test_foreign_symlink_with_overwrite_is_replaced_and_returns_overwritten(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    source = skill_library / "my-skill"
    source.mkdir()
    foreign_dir = tmp_path / "foreign"
    foreign_dir.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign_dir)

    result = reconcile_skill(
        source, target, overwrite=True, skill_library_path=skill_library
    )

    assert result.outcome == "overwritten"
    assert target.is_symlink()
    assert target.resolve() == source


def test_remove_skill_not_deployed_returns_skipped(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)

    result = remove_skill(target, skill_library_path=skill_library)

    assert result.outcome == "skipped"


def test_remove_skill_mysk_owned_symlink_returns_removed(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    skill_dir = skill_library / "my-skill"
    skill_dir.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(skill_dir)

    result = remove_skill(target, skill_library_path=skill_library)

    assert result.outcome == "removed"
    assert not target.exists()


def test_remove_skill_foreign_symlink_returns_skipped(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    foreign_dir = tmp_path / "foreign"
    foreign_dir.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(foreign_dir)

    result = remove_skill(target, skill_library_path=skill_library)

    assert result.outcome == "skipped"
    assert target.resolve() == foreign_dir


def test_remove_skill_regular_directory_returns_skipped(tmp_path):
    skill_library = tmp_path / "library"
    skill_library.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("---\nname: my-skill\n---")

    result = remove_skill(target, skill_library_path=skill_library)

    assert result.outcome == "skipped"
    assert target.is_dir()
