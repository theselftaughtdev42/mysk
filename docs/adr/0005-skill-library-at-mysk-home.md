# Skill Library stored under the mysk home directory at `~/.mysk`

Everything mysk owns on disk lives under a single **mysk home** directory at `~/.mysk`, overridable via the `MYSK_HOME` environment variable. The Skill Library is `<mysk home>/skills` (i.e. `~/.mysk/skills` by default).

mysk claims exactly one entry in the user's home directory. The Skill Library is the only artifact today; any future config, state, or cache lives under the same root rather than being scattered across separate OS directories.

## Considered options

- **`~/.mysk/` (chosen)** — one hidden entry in the home directory, holding everything mysk owns. Simple, always findable, works on any platform. Bounds mysk's home-directory footprint to a single entry instead of spreading across data/config/cache dirs.
- **`platformdirs.user_data_dir("mysk") / "skills"`** — follows OS conventions, resolving to `~/Library/Application Support/mysk/skills/` on macOS and `~/.local/share/mysk/skills/` on Linux. Rejected: the location is awkward to reach and edit by hand — and the Skill Library is a directory of user-editable files, so hand-access is a first-class use.

## Consequences

- All commands resolve the Skill Library via a single `skill_library()` function that returns `<mysk home>/skills`, where the mysk home is `~/.mysk` (or the `MYSK_HOME` override).
- `MYSK_HOME` overrides the whole mysk home directory, not the Skill Library alone; skills always resolve to `<MYSK_HOME>/skills`. `MYSK_HOME` provides an escape hatch for testing and for users who want to keep mysk's data in a directory of their own choosing.
