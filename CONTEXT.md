# mysk

A personal collection of agent skills — self-authored or imported — managed and deployed to AI agents via the `mysk` CLI.

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
The operation that updates an already-imported skill from its `source` URL.
_Avoid_: update, sync, pull

**Deployment Target**:
An agent-specific directory on the local machine that receives symlinked skills (e.g. `~/.claude/skills`, `~/.cursor/skills`). Targets are auto-discovered by checking whether the agent's home directory exists — no config file is maintained. mysk recognizes a fixed vocabulary of *known* agents (claude, cursor, codex); a target is *found* only when that agent's home directory exists. Operations act on the found set and `--agents` narrows within it — naming a known-but-uninstalled agent is a distinct, explained error, not a silent no-op.
_Avoid_: destination, output directory

**Active**:
The primary lifecycle state, indicating a skill is ready for regular use. Active skills are deployed.
_Avoid_: live, enabled, ready, stable

**Experimental**:
A lifecycle state indicating a skill is under active evaluation. It may be self-authored or imported, but is not yet trusted for regular use. Experimental skills are still deployed; they may graduate to active or be deprecated.
_Avoid_: draft, WIP, beta

**Deprecated**:
A lifecycle state indicating a skill is no longer in use. Deprecated skills can be removed from all Deployment Targets via cleanup.
_Avoid_: removed, disabled, archived

**Delete**:
The operation that permanently removes a skill from the Skill Library and unlinks it from all Deployment Targets. Irreversible.
_Avoid_: remove, uninstall, drop

**Provenance**:
Whether a skill was self-authored or imported from an external source.
_Avoid_: origin, attribution

**Source**:
The upstream URL of an imported skill, recorded inside the `mysk` frontmatter block. Used to identify where the skill came from and to enable Refresh.
_Avoid_: url, link, reference

**Modified**:
A boolean flag inside the `mysk` frontmatter block on imported skills. `false` means the local content is a clean import and can be safely overwritten on Refresh. `true` means the content has been changed locally and requires human review before any upstream Refresh. Covers content changes only — renames are tracked by `upstream_name`.
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
