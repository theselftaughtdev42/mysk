# Generic passthrough for non-mysk frontmatter

`Skill` carries an `extra_fields: dict` that collects every frontmatter key that is not `name`, `description`, or `mysk`. These fields are emitted verbatim by `to_frontmatter()` (between `description` and `mysk`), so all commands that rewrite `SKILL.md` preserve them without interpreting them.

## Considered options

- **Typed fields for spec-approved keys** (`license`, `compatibility`, `metadata`, `allowed-tools`) — rejected: can't handle agent-specific extensions (e.g. `disable-model-invocation`) and would require updates every time the agentskills.io spec adds a field.
- **Bypass `Skill` at the IO layer** — have commands merge the mysk block back into the original raw dict instead of going through `to_frontmatter()`. Rejected: `mark` already does this and that inconsistency is what caused the bug; the domain model is the right place to own round-trip fidelity.

## Consequences

`Skill` offers no validation of any extra field — neither spec-defined constraints (e.g. `name` max 64 chars) nor type checking. Zero validation is the policy: mysk carries these fields as opaque data and leaves correctness to the upstream author.

For `refresh` on an unmodified skill, extra fields come from upstream. A local addition to an imported skill without setting `modified: true` will not survive refresh — consistent with the existing contract for `description`.
