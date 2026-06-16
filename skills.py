#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).parent
SKILLS_DIR = ROOT / "skills"


def default_skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


def _read_frontmatter(skill: Path) -> dict[str, str]:
    lines = (skill / "SKILL.md").read_text().splitlines()
    result: dict[str, str] = {}
    if not lines or lines[0].strip() != "---":
        return result
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _is_deprecated(skill: Path) -> bool:
    return _read_frontmatter(skill).get("deprecated", "").lower() == "true"


def _is_experimental(skill: Path) -> bool:
    return _read_frontmatter(skill).get("experimental", "").lower() == "true"


def available_skills() -> list[Path]:
    return sorted(
        path
        for path in SKILLS_DIR.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    )


def list_skills(_: argparse.Namespace) -> int:
    for path in available_skills():
        if _is_deprecated(path):
            suffix = "  [deprecated]"
        elif _is_experimental(path):
            suffix = "  [experimental]"
        else:
            suffix = ""
        print(f"{path.name}{suffix}")
    return 0


def deploy_skills(args: argparse.Namespace) -> int:
    dest = args.dest.expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    for skill in available_skills():
        if _is_deprecated(skill):
            print(f"Skipping deprecated skill: {skill.name}")
            continue

        target = dest / skill.name

        if target.exists() or target.is_symlink():
            if not target.is_symlink():
                print(f"Refusing to replace non-symlink: {target}", file=sys.stderr)
                return 1
            target.unlink()

        target.symlink_to(skill.resolve(), target_is_directory=True)
        print(f"Linked {skill.name} -> {target}")

    return 0


def _set_frontmatter_flag(skill: Path, flag: str) -> None:
    skill_md = skill / "SKILL.md"
    lines = skill_md.read_text().splitlines()
    lines.insert(1, f"{flag}: true")
    skill_md.write_text("\n".join(lines) + "\n")


def experimental_skill(args: argparse.Namespace) -> int:
    skill = SKILLS_DIR / args.name
    if not skill.is_dir() or not (skill / "SKILL.md").exists():
        print(f"Unknown skill: {args.name}", file=sys.stderr)
        return 1

    if _is_experimental(skill):
        print(f"{args.name} is already marked as experimental.")
        return 0

    _set_frontmatter_flag(skill, "experimental")
    print(f"Marked {args.name} as experimental.")
    return 0


def deprecate_skill(args: argparse.Namespace) -> int:
    skill = SKILLS_DIR / args.name
    if not skill.is_dir() or not (skill / "SKILL.md").exists():
        print(f"Unknown skill: {args.name}", file=sys.stderr)
        return 1

    if _is_deprecated(skill):
        print(f"{args.name} is already deprecated.")
        return 0

    _set_frontmatter_flag(skill, "deprecated")
    print(f"Marked {args.name} as deprecated.")
    return 0


def cleanup_skills(args: argparse.Namespace) -> int:
    dest = args.dest.expanduser()
    if not dest.exists():
        print(f"Destination does not exist: {dest}", file=sys.stderr)
        return 1

    deprecated = {skill.name for skill in available_skills() if _is_deprecated(skill)}
    removed = 0

    for target in sorted(dest.iterdir()):
        if target.name not in deprecated:
            continue
        if not target.is_symlink():
            print(f"Refusing to remove non-symlink: {target}", file=sys.stderr)
            return 1
        target.unlink()
        print(f"Removed deprecated skill: {target.name}")
        removed += 1

    if removed == 0:
        print("No deprecated skills to clean up.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.set_defaults(func=list_skills)

    deploy_parser = subparsers.add_parser("deploy")
    deploy_parser.add_argument("--dest", type=Path, default=default_skills_dir())
    deploy_parser.set_defaults(func=deploy_skills)

    experimental_parser = subparsers.add_parser("experimental")
    experimental_parser.add_argument("name")
    experimental_parser.set_defaults(func=experimental_skill)

    deprecate_parser = subparsers.add_parser("deprecate")
    deprecate_parser.add_argument("name")
    deprecate_parser.set_defaults(func=deprecate_skill)

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--dest", type=Path, default=default_skills_dir())
    cleanup_parser.set_defaults(func=cleanup_skills)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
