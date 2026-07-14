# A Repo Slug (`owner/repo`) assumes GitHub

## Decision

A bare **Repo Slug** — the compact `owner/repo` form accepted as `import` input and shown in `list` — carries no host and silently resolves to GitHub. `mysk import owner/repo` expands to `https://github.com/owner/repo` and runs the existing repo-root scan; the slug never names GitLab, Codeberg, or any other host.

This deepens the tool's existing "only github.com is supported in this version" stance (see the host check in `RepoRootUrl.parse` / `ImportUrl.parse`): a full URL at least names its host, whereas a slug bakes GitHub in as an unstated default.

## Considered options

- **Bare `owner/repo` means GitHub (chosen)** — matches how users already think and talk about repos (`theselftaughtdev42/mysk`), and optimises the dominant use case: "grab skills from this GitHub repo." The convenience is the whole point of the `/` stance (issue #151); a host would be pure ceremony on every import.
- **Require an explicit host prefix (e.g. `gh:owner/repo`)** — rejected: it taxes today's only supported host to preserve a symmetry that does not yet exist, defeating the shorthand's reason to exist. Explicitness has no payoff while GitHub is the sole host.

## Consequences

- The slug is **input and display sugar only** — it is expanded to a full GitHub URL at the input boundary and compressed only for display. The stored `Source` stays a full URL, so this ADR changes no schema and requires no migration.
- **Forward path when multi-host support arrives:** `owner/repo` stays GitHub for backward compatibility, and other hosts require an explicit host prefix. The GitHub default is never silently repointed — existing slugs keep resolving where they always did.
- Non-GitHub hosts remain unsupported; the slug hardens the GitHub assumption rather than relaxing it. Relaxing it is the subject of that future multi-host work, not this decision.
