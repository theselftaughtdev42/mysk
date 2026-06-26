# Skill Library invariant: every skill must have a mysk block

Every skill directory in the Skill Library must contain a `mysk:` frontmatter block. A skill without one is treated as an error, not a valid state.

## Context

Before the import command existed, skills could be "adopted" into mysk management incrementally — a skill with no `mysk:` block was a recognised intermediate state ("unmigrated").

Once the import command was implemented, the only supported path into the Skill Library became `mysk import`. Import always writes a `mysk:` block before anything lands on disk. A skill without a block can therefore only appear if a user manually copied files into the library directory, bypassing the CLI.

## Decision

Treat the absence of a `mysk:` block in a library skill as a schema error.

## Considered options

- **Keep graceful handling** — continue surfacing unmigrated skills as a distinct, non-error state. Rejected: it legitimises a path that the CLI no longer supports and adds complexity to every caller.
- **Raise at load time** — have `load_skills` raise an exception on encountering a missing block. Rejected: too disruptive; `dev list` should still show the offending skill so the user knows what to fix.

## Consequences

`Skill.from_frontmatter` remains permissive (`mysk=None` is allowed) because the import command legitimately reads source skills that have no block yet. The invariant is enforced at the library layer (`load_skills`), not the domain model.
