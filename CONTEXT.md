# mysk

A personal collection of agent skills — standalone or linked to an upstream source — managed and deployed to AI agents via the `mysk` CLI.

## Language

**Skill**:
A directory containing a `SKILL.md` entry point and any supporting files. The directory is the unit of ownership; `SKILL.md` is the entry point, not the skill itself.
_Avoid_: plugin, module, script

**mysk**:
The CLI tool and package name for this project. Manages the skill lifecycle: import, list, deploy, refresh, mark, and deprecate.
_Avoid_: skills.py, the tool, the script

**Skill Operations**:
Collective term for the commands that act on one or more skills already in the Skill Library, identified by name: `deploy`, `undeploy`, `cleanup`, `delete`, `mark`, and `refresh`. They share a common interactive-picker/flag interface, following the Skill Operation Pathway — see ADR-0008. Excludes `import` (brings a new skill in, not identified by an existing name) and `list`/`library` (read-only).
_Avoid_: skill management commands, skill commands

**Skill Operation Pathway**:
The shared flow every Skill Operation follows: resolve a Skill Selection via `<skill>`, `--bulk`, or `--all` — or, when none is given, an interactive picker over eligible skills — then, only if the action is destructive, a confirmation gate skippable with `--yes`, then the act itself. See ADR-0008 and `docs/diagrams/skill-operations-pathway.md`.
_Avoid_: pattern, spine, flow

**Skill Selection**:
The set of skills a Skill Operation resolves to act on, via `<skill>`, `--bulk`, `--all`, or the interactive picker. Distinct from Deployment Target, which is *where* an operation acts, not *what* it acts on.
_Avoid_: target, scope

**mysk home**:
The single directory that holds everything mysk owns on disk, located at `~/.mysk` and overridable via the `MYSK_HOME` environment variable. See ADR-0005.
_Avoid_: data dir, app support dir, mysk folder

**Skill Library**:
The canonical local directory where all 'mysk-owned' skills are stored, located at `$MYSK_HOME/skills`. All mysk commands read from and write to the Skill Library.
_Avoid_: skills directory, skills folder, source repo

**Deploy**:
The act of symlinking skills from the Skill Library into Deployment Targets. Targets default to all found targets and are narrowed with `--agents`; skills are curated via `<skill>`/`--bulk`/`--all` or an interactive picker. All skills are offered for selection regardless of lifecycle state, shown as `name (state)` so an informed choice can be made.
_Avoid_: install, publish, sync

**Undeploy**:
The operation that removes skill symlinks from Deployment Targets — all found targets by default, narrowed with `--agents` — without affecting the skill in the Skill Library.
_Avoid_: recall, retract, withdraw, uninstall

**Import**:
The operation that brings a skill into the Skill Library for the first time.
_Avoid_: install, add, migrate, download

**Refresh**:
The operation that updates a skill from its recorded upstream `source` URL. Only skills that have an upstream can be refreshed.
_Avoid_: update, sync, pull

**Deployment Target**:
An agent-specific directory on the local machine that receives symlinked skills (e.g. `~/.claude/skills`, `~/.cursor/skills`). Targets are auto-discovered by checking whether the agent's home directory exists — no config file is maintained. mysk recognizes a fixed vocabulary of *known* agents (claude, cursor, codex); a target is *found* only when that agent's home directory exists. Operations act on the found set and `--agents` narrows within it — naming a known-but-uninstalled agent is a distinct, explained error, not a silent no-op.
_Avoid_: destination, output directory

**Active**:
The primary lifecycle state, indicating a skill is ready for regular use. Active skills are deployed.
_Avoid_: live, enabled, ready, stable

**Experimental**:
A lifecycle state indicating a skill is under active evaluation. It applies regardless of whether the skill has an upstream, and signals the skill is not yet trusted for regular use. Experimental skills are still deployed; they may graduate to active or be deprecated.
_Avoid_: draft, WIP, beta

**Deprecated**:
A lifecycle state indicating a skill is no longer in use. Deprecated skills can be removed from all Deployment Targets via cleanup.
_Avoid_: removed, disabled, archived

**Delete**:
The operation that permanently removes a skill from the Skill Library and unlinks it from all Deployment Targets. Irreversible.
_Avoid_: remove, uninstall, drop

**Provenance**:
What mysk records about where a skill came from. A skill either **has an upstream** — a `source` URL it can be Refreshed from — or is **standalone**, with no source. mysk does not track authorship; whether a skill has an upstream is the only origin distinction it keeps. The derived predicate is `has_upstream` (`source is not None`).
_Avoid_: origin, attribution, self-authored, imported (as a provenance value)

**Source**:
The upstream URL recorded inside a skill's `mysk` frontmatter block. Its presence is what makes a skill refreshable (has an upstream); it identifies where the skill came from, keys duplicate-import detection, and enables Refresh.
_Avoid_: url, link, reference

**Broken Upstream**:
A skill whose recorded `source` no longer resolves — the repo or ref is gone, or the skill directory (or its `SKILL.md`) has been renamed or deleted within a live repo. A transient network or rate-limit error is not a broken upstream.
_Avoid_: dead link, stale source, orphaned skill

**Repo Slug**:
The compact `owner/repo` identifier of a GitHub repository, e.g. `theselftaughtdev42/mysk`. Accepted as `import` input and shown in `list` as the compact rendering of a skill's Source, hyperlinked to the full URL. Identifies a *repository*. GitHub is assumed — see ADR-0010.
_Avoid_: slug (bare), handle, shorthand, owner/repo string

**Modified**:
A boolean flag inside the `mysk` frontmatter block, meaningful only on skills that have an upstream `source`. `false` means the local content is a clean copy of upstream and can be safely overwritten on Refresh. `true` means the content has been changed locally and requires human review before any upstream Refresh. Structurally inapplicable to standalone skills, which have no upstream to diverge from. Covers content changes only — renames are tracked by `upstream_name`.
_Avoid_: changed, customised, forked

**Upstream Name**:
An optional field inside the `mysk` frontmatter block, present only when a skill was imported with `--rename`. Records the skill's original name in the upstream source so Refresh can correctly identify and fetch the upstream directory even though the local name differs.
_Avoid_: original name, remote name

**Marking**:
A key–value pair applied to a skill via the `mark` command. Valid keys are `status` (sets the lifecycle state) and `modified` (sets the modified flag). One marking is applied per invocation.
_Avoid_: attribute, field, flag, property

**mysk block**:
The `mysk:` frontmatter section in `SKILL.md` that contains all mysk-managed metadata. Its presence is the canonical signal that a skill is owned by `mysk`. Generic fields (`name`, `description`) live outside this block and are readable by any agent. The exact key names are recorded in ADR-0003.
_Avoid_: mysk metadata, mysk config

**Output**:
The per-module facade (`mysk/output.py`), instantiated as `out = Output(__name__)`, that owns both of mysk's output channels — Presentation and Diagnostics. Command and io modules emit through it rather than touching the Rich consoles or `logging` directly. See ADR-0009.
_Avoid_: logger, printer, console wrapper

**Presentation Channel**:
The user-facing half of the Output facade: the verbs `product`/`success`/`note` (stdout) and `warn`/`error` (stderr), rendered through the shared Rich consoles and always shown. Routing and markup discipline follow ADR-0004's stream contract.
_Avoid_: UI output, screen output

**Diagnostics Channel**:
The debugging half of the Output facade: the verbs `debug`/`info`/`exception`, built on stdlib `logging` and hidden unless `MYSK_LOG_LEVEL` is set. Carries breadcrumbs about what mysk did internally (network, filesystem, resolution, decisions) — never user-facing product, warnings, or errors. See ADR-0009.
_Avoid_: verbose output, debug prints, log

## Example dialogue

> **Dev**: I want to add a skill I found on GitHub — how do I get it into mysk?
>
> **Owner**: Run `mysk import <github-url>`. It downloads the skill into the Skill Library, records the source URL, sets `modified: false`, and prompts you for a lifecycle state.
>
> **Dev**: What if there's already a skill with that name?
>
> **Owner**: mysk errors. If the conflict is with a skill from a different source, re-run with `--rename <new-name>` — that imports it under a different local name and records the original as `upstream_name` in the mysk block.
>
> **Dev**: What if I edit the skill locally later?
>
> **Owner**: Flip `modified: true`. That's the signal that the local content has drifted from upstream and needs manual review before you can refresh it.
>
> **Dev**: And experimental vs active — what's the difference when deploying?
>
> **Owner**: Nothing mechanical — both show up in the deploy prompt. Experimental just means you're still evaluating it. The state is shown next to the name so you know what you're picking.
