# mysk

A personal collection of agent skills — self-authored or imported — managed and deployed to AI agents via the `mysk` CLI.

## Language

**Skill**:
A directory containing a `SKILL.md` entry point and any supporting files. The directory is the unit of ownership; `SKILL.md` is the entry point, not the skill itself.
_Avoid_: plugin, module, script

**mysk**:
The CLI tool and package name for this project. Manages the skill lifecycle: import, list, deploy, refresh, mark, and deprecate.
_Avoid_: skills.py, the tool, the script

**Skill Library**:
The canonical local directory where all skills are stored, located at `platformdirs.user_data_dir("mysk") / "skills"`. Overridable via the `MYSK_SKILLS_DIR` environment variable. All mysk commands read from and write to the Skill Library; it is independent of any source repository. See ADR-0005.
_Avoid_: skills directory, skills folder, source repo

**Deploy**:
The act of symlinking skills from the Skill Library into selected Deployment Targets via an interactive prompt. The author chooses which targets and which skills; all skills are offered for selection regardless of lifecycle state, shown as `name (state)` so an informed choice can be made.
_Avoid_: install, publish, sync

**Import**:
The operation that brings a skill into the Skill Library for the first time.
_Avoid_: install, add, migrate, download

**Refresh**:
The operation that updates an already-imported skill from its `source` URL.
_Avoid_: update, sync, pull

**Deployment Target**:
An agent-specific directory on the local machine that receives symlinked skills (e.g. `~/.claude/skills`, `~/.cursor/skills`). Targets are auto-discovered by checking whether the agent's home directory exists — no config file is maintained.
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
