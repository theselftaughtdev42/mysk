from mysk.io.deploy import reconcile_skill


def test_fresh_destination_creates_symlink_and_returns_deployed(tmp_path):
    source = tmp_path / "source" / "my-skill"
    source.mkdir(parents=True)
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)

    result = reconcile_skill(source, target, overwrite=False)

    assert result.outcome == "deployed"
    assert target.is_symlink()
    assert target.resolve() == source


def test_non_symlink_dir_without_overwrite_is_skipped(tmp_path):
    source = tmp_path / "source" / "my-skill"
    source.mkdir(parents=True)
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)
    (target / "some-file.txt").write_text("existing content")

    result = reconcile_skill(source, target, overwrite=False)

    assert result.outcome == "skipped"
    assert not target.is_symlink()
    assert (target / "some-file.txt").exists()


def test_non_symlink_dir_without_overwrite_includes_skip_reason(tmp_path):
    source = tmp_path / "source" / "my-skill"
    source.mkdir(parents=True)
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)

    result = reconcile_skill(source, target, overwrite=False)

    assert result.reason is not None
    assert "--overwrite" in result.reason


def test_non_symlink_dir_with_overwrite_is_replaced_and_returns_overwritten(tmp_path):
    source = tmp_path / "source" / "my-skill"
    source.mkdir(parents=True)
    target = tmp_path / "targets" / "my-skill"
    target.mkdir(parents=True)
    (target / "some-file.txt").write_text("existing content")

    result = reconcile_skill(source, target, overwrite=True)

    assert result.outcome == "overwritten"
    assert target.is_symlink()
    assert target.resolve() == source


def test_existing_symlink_is_replaced_and_returns_overwritten(tmp_path):
    source = tmp_path / "source" / "my-skill"
    source.mkdir(parents=True)
    old_source = tmp_path / "old-source"
    old_source.mkdir()
    target = tmp_path / "targets" / "my-skill"
    target.parent.mkdir(parents=True)
    target.symlink_to(old_source)

    result = reconcile_skill(source, target, overwrite=False)

    assert result.outcome == "overwritten"
    assert target.is_symlink()
    assert target.resolve() == source
