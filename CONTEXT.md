# my-skills

A personal collection of agent skills — self-authored or imported — managed and deployed to AI agents via the `mysk` CLI.

## Language

**Skill**:
A directory containing a `SKILL.md` entry point and any supporting files. The directory is the unit of ownership; `SKILL.md` is the entry point, not the skill itself.
_Avoid_: plugin, module, script

**mysk**:
The CLI tool (short for my-skills) that manages the skill lifecycle: list, deploy, mark experimental, deprecate, and clean up.
_Avoid_: skills.py, the tool, the script

**Deploy**:
The act of symlinking skills from the local repository into selected Deployment Targets via an interactive prompt. The author chooses which targets and which skills; all skills are offered for selection regardless of lifecycle state, shown as `name (state)` so an informed choice can be made. Covers both initial installation and refresh — there is no separate "update" operation.
_Avoid_: install, publish, sync

**Deployment Target**:
An agent-specific directory on the local machine that receives symlinked skills (e.g. `~/.claude/skills`, `~/.cursor/skills`). Targets are auto-discovered by checking whether the agent's home directory exists — no config file is maintained.
_Avoid_: destination, output directory

**Init**:
A lifecycle state indicating a skill is owned by `mysk` (it has a `mysk` block) but is still being written. Typically a freshly scaffolded skill not yet considered ready for regular use.
_Avoid_: new, scaffold, draft

**Active**:
The primary lifecycle state, indicating a skill is ready for regular use. Active skills are deployed.
_Avoid_: live, enabled, ready, stable

**Experimental**:
A lifecycle state indicating a skill is under active evaluation. It may be self-authored or imported, but is not yet trusted for regular use. Experimental skills are still deployed; they may graduate to active or be deprecated.
_Avoid_: draft, WIP, beta

**Deprecated**:
A lifecycle state indicating a skill is no longer in use. Deprecated skills can be removed from all Deployment Targets via cleanup.
_Avoid_: removed, disabled, archived

**Provenance**:
Whether a skill was self-authored or imported from an external source. Imported skills carry a `source` URL and a `modified` boolean inside the `mysk` frontmatter block.
_Avoid_: origin, attribution

**Source**:
The upstream URL of an imported skill, recorded inside the `mysk` frontmatter block. Used to identify where the skill came from and to enable future refresh from upstream.
_Avoid_: url, link, reference

**Modified**:
A boolean flag inside the `mysk` frontmatter block on imported skills. `false` means the local copy is a clean import and can be safely overwritten. `true` means the skill has been changed locally and requires human review before any upstream refresh.
_Avoid_: changed, customised, forked

**mysk block**:
The `mysk:` frontmatter section in `SKILL.md` that contains all mysk-managed metadata: the skill's lifecycle state and, for imported skills, its provenance (Source and Modified). Its presence is the canonical signal that a skill is owned by `mysk`. Generic fields (`name`, `description`) live outside this block and are readable by any agent. The exact key names are recorded in ADR-0003.
_Avoid_: mysk metadata, mysk config

## Example dialogue

> **Dev**: I want to add a skill I found on GitHub — do I just drop it in `skills/`?
>
> **Owner**: Yes. Add the directory, set `source` to the GitHub URL in the frontmatter, and leave `modified: false`. Run `mysk deploy` and it'll link into every Deployment Target that exists on the machine.
>
> **Dev**: What if I tweak it later?
>
> **Owner**: Flip `modified: true`. That's your signal that the local copy has drifted from upstream and needs manual review if you ever want to refresh it.
>
> **Dev**: And experimental vs active — what's the difference when deploying?
>
> **Owner**: Nothing mechanical — both show up in the deploy prompt. Experimental just means you're still evaluating it. The state is shown next to the name so you know what you're picking.
