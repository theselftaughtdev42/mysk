# my-skills
Agent skills I have either made myself (less likely) or politely stolen (more likely).

## Usage

List available skills:

```sh
uv run skills.py list
```

Deploy skills to Codex:

```sh
uv run skills.py deploy
```

By default, deployment symlinks each directory in `skills/` into
`$HOME/.agents/skills`. Existing symlinks are replaced, but existing non-symlink
directories are left untouched.

## Acknowledgements
- https://github.com/mattpocock/skills