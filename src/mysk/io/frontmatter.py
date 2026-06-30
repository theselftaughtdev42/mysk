"""SKILL.md frontmatter parsing and serialisation (YAML between `---` fences)."""

import yaml

_FENCE = "---"


def read(text: str) -> tuple[dict, str]:
    """Split a SKILL.md into its YAML frontmatter dict and the remaining body.

    Schema-agnostic: returns whatever keys the frontmatter contains. A document
    with no leading `---` fence is treated as all body with empty frontmatter.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FENCE:
        return {}, text

    for index in range(1, len(lines)):
        if lines[index].strip() == _FENCE:
            raw = "".join(lines[1:index])
            body = "".join(lines[index + 1 :])
            return yaml.safe_load(raw) or {}, body

    return {}, text


def write(data: dict, body: str) -> str:
    """Render a frontmatter dict and body back into a SKILL.md string.

    Inverse of `read`: `read(write(data, body))` returns the same data and body.
    Key order is preserved and long values (e.g. source URLs) are never wrapped.
    String values are normalized (trailing whitespace stripped) so that YAML
    encoding artefacts like folded-scalar trailing newlines don't produce ugly
    quoted scalars in the output.
    """
    rendered = yaml.safe_dump(
        _normalize(data),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=10**9,
    )
    return f"{_FENCE}\n{rendered}{_FENCE}\n{body}"


def _normalize(data: dict) -> dict[str, object]:
    result: dict[str, object] = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = v.rstrip()
        elif isinstance(v, dict):
            result[k] = _normalize(v)
        else:
            result[k] = v
    return result
