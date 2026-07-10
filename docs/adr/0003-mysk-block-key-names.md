# mysk block key names: verbose, with an always-explicit `state` key

The `mysk:` block uses full, readable key names — `state`, `source`, `modified` — rather than abbreviations. Lifecycle is a single mutually-exclusive `state` key, always written explicitly with one of `active`, `experimental`, or `deprecated`. Provenance for imported skills adds `source` (URL) and `modified` (bool).

We chose verbose keys because a token spike using `tiktoken` showed abbreviation buys nothing: each candidate key is a single token in both `o200k_base` and `cl100k_base`, so `state`/`source`/`modified` cost exactly the same as `st`/`src`/`mod` (verbose, abbreviated, and hybrid blocks all measured 33 tokens for the worst-case imported skill). Given zero token savings, readability for the humans and agents that read `SKILL.md` is the deciding factor.

## Considered options

- **Abbreviated keys** (`st`, `src`, `mod`) — rejected: identical token cost, worse readability.
- **Hybrid** (mix of full and short) — rejected: no measurable benefit and inconsistent.
- **Independent boolean lifecycle flags** (`experimental`/`deprecated`) — rejected: lifecycle states are mutually exclusive, so independent booleans permit invalid combinations (e.g. `experimental: true` + `deprecated: true`). A single `state` key makes mutual exclusivity structural.
- **Keyless Active** (omit `state` when Active, defaulting on read) — rejected: it saves ~4 tokens per Active skill but makes the data non-uniform and forces the reader to guess. Writing `state: active` everywhere lets `from_frontmatter` be strict and fail-fast on skills missing a block.

## Consequences

- The `mysk:` block is optional: a skill with no block is not controlled by mysk (ADR-0001).
- When the block *is* present it must carry an explicit `state` (one of `active`, `experimental`, `deprecated`). A present-but-stateless block is malformed: `from_frontmatter` raises.
- Adding a future lifecycle state means adding a `state` value, not a new key.

## Amendment (2026-06-22): `upstream_name` key

A fourth key, `upstream_name`, is added for skills imported with `--rename`. When present it records the skill's original name in the upstream source, allowing Refresh to locate the correct upstream directory even though the local name differs.

`upstream_name` is optional and only meaningful on skills that have an upstream (those that carry `source`). It is absent on standalone skills and on imports where no rename occurred. It is intentionally separate from `modified`: `modified` signals content drift, `upstream_name` signals name drift. A renamed skill with unchanged content correctly has `modified: false` and a non-null `upstream_name`.

## Amendment (2026-07-07): provenance records upstream-presence, not authorship

The `mysk` block deliberately keeps no authorship signal: the only origin distinction it records is whether a skill **has an upstream** (`source is not None`, refreshable) or is **standalone**. "Self-authored" was never actually tracked — it was only inferred from the *absence* of `source`, which mislabels locally-imported skills as authored here; a dedicated `mysk new` creation pathway was considered to make authorship real and deferred as unneeded.
