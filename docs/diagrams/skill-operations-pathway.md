# Skill Operation Pathway

Every Skill Operation (`deploy`, `undeploy`, `cleanup`, `delete`, `mark`, `refresh`) funnels through the same three shared functions: Skill Selection resolution, picker construction, and the confirmation gate. This diagram shows that shared Skill Operation Pathway (see `CONTEXT.md` and ADR-0008); per-command variation (relevance/disabled-reason rules, confirmation scope) is summarised in the table below.

```mermaid
flowchart TD
    Start(["mysk &lt;cmd&gt; [&lt;skill&gt;] [--bulk] [--all] [--yes]"]) --> CountCheck{"How many of\n&lt;skill&gt; / --bulk / --all given?"}

    CountCheck -->|"more than one"| ErrMutex["Error:\nmutually exclusive"]

    CountCheck -->|"exactly one"| WhichOne{"Which one?"}
    WhichOne -->|"&lt;skill&gt;"| ValidateSkill{"Skill exists\nin eligible set?"}
    ValidateSkill -->|"no"| ErrUnknown["Error: unknown skill"]
    ValidateSkill -->|"yes"| SelectionSingle["selection = [skill]"]

    WhichOne -->|"--bulk"| ValidateBulk{"All named skills\nexist in eligible set?"}
    ValidateBulk -->|"no"| ErrUnknownBulk["Error: unknown skill(s)"]
    ValidateBulk -->|"yes"| SelectionBulk["selection = bulk list"]

    WhichOne -->|"--all"| SelectionAll["selection = every eligible skill"]

    CountCheck -->|"none given"| Picker["Show questionary.checkbox\nover eligible skills"]
    Picker --> Relevance["Per-skill relevance callback:\nselectable, or disabled + reason"]
    Relevance --> UserSelects["User selects one or more"]
    UserSelects --> SelectionPicked["selection = user's picks"]

    SelectionSingle --> Resolved(["Skill Selection resolved"])
    SelectionBulk --> Resolved
    SelectionAll --> Resolved
    SelectionPicked --> Resolved

    Resolved --> Destructive{"Is this action destructive\n/ irreversible for this selection?\n(delete, cleanup, refresh,\nor deploy --overwrite of a\nreal directory)"}

    Destructive -->|"no"| Act["Act on selection"]

    Destructive -->|"yes"| YesFlag{"--yes given?"}
    YesFlag -->|"yes"| Act
    YesFlag -->|"no"| Confirm{"Show confirmation prompt\n'are you sure?'"}
    Confirm -->|"confirmed"| Act
    Confirm -->|"declined"| Abort["Abort — no changes made"]

    Act --> Done(["Done"])
```

## What varies per command

| Command | `<skill>` positional | Eligible set | Disabled-in-picker reasons | Destructive? (confirm + `--yes`) |
|---|---|---|---|---|
| `deploy` | yes | all skills | "already deployed" (clean collision to every selected target) | only the `--overwrite`-into-real-directory branch |
| `undeploy` | yes | all skills | "not deployed" (to any selected target) | no |
| `cleanup` | **no** — `--bulk`/`--all` only | `state == deprecated` | none — all eligible skills stay selectable | yes, always |
| `delete` | yes | all skills (deliberately unrestricted — `--all` is a "wipe the library" escape hatch) | none | yes, always |
| `mark` | yes | all skills | none | no |
| `refresh` | yes | imported (non-self-authored) skills | "self-authored — nothing to refresh"; "modified — needs review before refresh" | yes, always |

`deploy` and `undeploy` also resolve a Deployment Target (which deployment directory) before resolving the Skill Selection, via their own existing checkbox — unchanged by this PRD. `mark` additionally prompts for `--key`/`--value` independently after skill resolution, once each is missing.
