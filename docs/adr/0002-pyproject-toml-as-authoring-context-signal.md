# pyproject.toml presence as the authoring context signal

The `mysk mark` command (and any future authoring commands) are only available when run from within the source repository, not from a deployed `uv tool install`. To detect this, `mysk` walks up from `__file__` looking for a `pyproject.toml` containing `name = "mysk"`. When `uv tool install` deploys the package, only the wheel contents land in site-packages — no `pyproject.toml` is copied — so the check naturally fails for deployed instances.

## Considered options

- **`skills/` directory presence** — rejected because any directory on the filesystem could accidentally satisfy it; not an intentional signal.
- **Environment variable (`MYSK_REPO=1`)** — rejected because it requires manual setup and can be set anywhere.
- **Hardcoded repo path** — rejected because it breaks on any machine that isn't the original author's.

## Consequences

Authoring commands are silently unavailable in deployed installs. Users who clone the repo and run `uv run mysk mark` get full authoring access without any configuration.
