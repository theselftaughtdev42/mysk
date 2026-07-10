# Skill Operations share a unified Skill Operation Pathway

The Skill Operations (`deploy`, `undeploy`, `cleanup`, `delete`, `mark`, `refresh`) previously diverged in how they handled no-args invocation, skill selection, and confirmation — some prompted unconditionally, some errored on missing args, `mark` silently discarded partial arguments. This settles one Skill Operation Pathway for all six (raised in #103).

See [`docs/diagrams/skill-operations-pathway.md`](../diagrams/skill-operations-pathway.md) for a mermaid flowchart of the resulting Skill Operation Pathway described below.

## Decision

- **Skill Selection**: every Skill Operation accepts a `<skill>` positional (single skill, kept for ergonomic single-skill use), a `--bulk name1,name2,...` flag (explicit list), and an `--all` flag (every eligible skill for that command) — mutually exclusive with each other. `--all` is included on `delete` deliberately, as a "wipe the library and start fresh" escape hatch, rather than withheld as a safety measure; `--yes` is the only guard against an accidental bulk-destructive run.
- **No-args interactive default**: when no Skill Selection is given, every Skill Operation shows a `questionary.checkbox` multi-select over eligible skills, rather than a single-select or (`cleanup`'s previous behavior) a blanket confirm over an implicit "all" set.
- **Picker relevance**: irrelevant entries are shown via `questionary.Choice(disabled=<reason>)` rather than hidden, so the user sees why an item can't be chosen — `deploy` dims already-deployed skills (unless the Deployment Target collision is stale/foreign and `--overwrite` would apply), `undeploy` dims not-deployed skills, `refresh` dims standalone (no-upstream) and `modified: true` skills.
- **Confirmation**: a single `--yes` flag skips the "are you sure?" prompt. The prompt itself is scoped to genuinely destructive/irreversible actions only: `delete`, `cleanup`, `refresh`, and `deploy` (only the `--overwrite`-into-a-real-directory case, which `shutil.rmtree`s existing data — see `src/mysk/io/deploy.py`). `undeploy` and `mark` never confirm, since both are trivially reversible (redeploy, re-mark).
- **`mark` fix**: skill/key/value become independently skippable (matching how `deploy`'s `--agents` and `--skills` already skip independently), replacing the previous all-or-nothing check that silently discarded partial arguments.
- **`import` is excluded** from the Skill Operation Pathway — it introduces a skill from an external source rather than acting on one already in the Skill Library, so there's no meaningful picker or bulk mode for it. `list`/`library` are also excluded — read-only, nothing to confirm or select.

## Considered options

- **Comma-separated list directly in the `<skill>` positional** (`mysk delete foo,bar`) — rejected in favor of an explicit `--bulk` flag: one flag makes bulk (especially bulk-destructive) intent visually obvious at the call site and avoids two competing "give me multiple" dialects across the CLI.
- **`--force` / `--skills` / `--skills-all` naming** — rejected in favor of `--yes` (skip confirmation) and `--bulk` / `--all` (declare a Skill Selection), so each flag name has exactly one meaning across all six commands.

## Consequences

- `deploy`/`undeploy`'s existing `--skills` / `--skills-all` flags are renamed to `--bulk` / `--all`.
- `refresh`'s existing `--all` keeps its name; it gains `--bulk`.
- `cleanup` and `delete` gain no-args interactive pickers where none existed before (`delete`'s `name` argument was previously mandatory; `cleanup` took no Skill Selection input at all).
