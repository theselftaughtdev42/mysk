# Two output channels behind an `Output` facade: Rich presentation + stdlib-logging diagnostics

## Decision

- **One facade, two channels, split by audience — not severity.** `mysk/output.py` defines `Output`, instantiated per module. The routing question is "does a normal user need to see this?" (→ presentation) vs "is this a breadcrumb for debugging?" (→ diagnostics). User-facing warnings and errors are presentation; the diagnostic channel carries diagnostics only.
  - **Presentation** is Rich, always shown, and keeps ADR-0004's stdout/stderr semantic contract and markup discipline — now enforced inside the facade rather than at call sites.
  - **Diagnostics** are stdlib `logging`, hidden unless opted in.
- **Per-module instantiation preserves attribution.** Each module's `Output` wraps its own `logging.getLogger(__name__)`, a child of the single `mysk` logger, so records identify where they came from. A shared single instance would lose this.
- **Enablement is env-var-only: `MYSK_LOG_LEVEL`**, mirroring the `MYSK_HOME` convention. No `--verbose`/`--debug` flag. Default unset → diagnostic channel fully silent.
- **Default-off is structural, not a threshold.** When `MYSK_LOG_LEVEL` is unset, nothing can leak a WARNING+/traceback to stderr uninvited; the emitting handler is attached only when the var is set.
- **`logging` chosen over a pure-Rich diagnostic facade for the httpx payoff.** Standard `logging` can surface httpx's internal request/response lines; a pure-Rich facade structurally cannot see inside httpx.
- **Diagnostics instrument I/O and decisions, not pure computation** — network, filesystem mutations, path/config resolution, and decision branches. Pure `domain/` code stays un-instrumented so well-unit-tested computation doesn't drown the trace.

## Relationship to ADR-0004

ADR-0004 states that *all* command output goes through the two shared Rich consoles. This ADR records a deliberate **carve-out**: the consoles own **user-facing** output; `logging` owns **diagnostics**. The two consoles become internals owned by `Output`; command modules import the facade rather than `mysk.console`. ADR-0004's stdout/stderr semantic contract and markup discipline are preserved, now enforced inside the facade.

## Considered options

- **Route warnings/errors through `logging` too** ("all severities via logging") — rejected: audience-not-severity keeps user-facing warnings/errors coloured and in front of the user regardless of logging config, and keeps the two channels from both claiming "errors".
- **A pure-Rich diagnostic facade** — rejected: it structurally cannot surface httpx's internal HTTP requests, the single biggest debugging payoff.
- **A `--verbose`/`--debug` CLI flag or a boolean `MYSK_DEBUG=1`** — rejected for now: env-var-only mirrors `MYSK_HOME`, and a level knob subsumes a coarse boolean. A flag can be layered on later without breaking the env var.
- **A shared single `Output` instance** — rejected: per-module instantiation is what preserves `getLogger(__name__)` attribution.

## Consequences

- New modules log via a per-module `Output`; diagnostic calls are unguarded (no `if debug:` checks, no env reads at call sites).
- `mysk/console.py` is an internal of `Output`; new code does not import it directly.
- Tests assert presentation on `result.stdout`/`result.stderr` and diagnostics on `caplog` for the `mysk` logger.
- A persistent log file, rotation, and structured/JSON logging are out of scope.
