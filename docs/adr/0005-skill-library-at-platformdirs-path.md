# Skill Library stored at platformdirs user data directory

Imported skills are stored at `platformdirs.user_data_dir("mysk") / "skills"`, overridable via the `MYSK_SKILLS_DIR` environment variable.

## Considered options

- **`~/.mysk/skills/`** — simple, always findable, works on any platform. Non-standard: buries app data in the home root on macOS and Linux, where convention puts it in `~/Library/Application Support/` and `~/.local/share/` respectively.
- **`platformdirs.user_data_dir("mysk") / "skills"`** — follows OS conventions. Resolves to `~/Library/Application Support/mysk/skills/` on macOS and `~/.local/share/mysk/skills/` on Linux. Requires adding `platformdirs` as a runtime dependency (lightweight; already the Python-standard answer to this problem).
- **User-configured path only** — require explicit config before any command works. Rejected: too much friction for the common case; no sensible default.

## Consequences

- All commands resolve the Skill Library via a single `skill_library()` function that returns the platformdirs path (or `MYSK_SKILLS_DIR` override).
- `platformdirs` is added as a runtime dependency.
- `MYSK_SKILLS_DIR` provides an escape hatch for testing and for users who want to manage skills in a version-controlled directory of their own choosing.
