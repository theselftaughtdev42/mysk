"""Low-level deploy/undeploy operations: symlink reconciliation and removal."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from mysk.output import Output

out = Output(__name__)

ActOutcome = Literal["deployed", "overwritten", "removed", "skipped"]


@dataclass
class ActResult:
    """Outcome of acting on a single skill at one Deployment Target.

    The one result type shared by every per-target act — reconcile and remove
    alike — carrying what happened and an optional human-readable reason.
    """

    outcome: ActOutcome
    reason: str | None = field(default=None)


def reconcile_skill(
    source_dir: Path,
    target_path: Path,
    *,
    overwrite: bool,
    skill_library_path: Path,
) -> ActResult:
    """Symlink *source_dir* at *target_path*, handling existing entries.

    Returns an ActResult describing what happened (deployed, overwritten,
    or skipped) and an optional human-readable reason.
    """
    # an existing symlink: replace it, unless it belongs to something else
    if target_path.is_symlink():
        owned_by_mysk = target_path.resolve().is_relative_to(skill_library_path)
        if not owned_by_mysk and not overwrite:
            reason = (
                "symlink exists but is not owned by mysk. Use --overwrite to replace"
            )
            return ActResult(
                outcome="skipped",
                reason=reason,
            )
        out.debug(f"replacing symlink {target_path} → {source_dir}")
        target_path.unlink()
        target_path.symlink_to(source_dir)
        return ActResult(outcome="overwritten")

    # nothing at the target: create the symlink
    if not target_path.exists():
        out.debug(f"creating symlink {target_path} → {source_dir}")
        target_path.symlink_to(source_dir)
        return ActResult(outcome="deployed")

    # a real directory is in the way: replace it only with --overwrite
    if not overwrite:
        return ActResult(
            outcome="skipped",
            reason="directory already exists. Use --overwrite to replace",
        )

    out.debug(f"overwriting directory {target_path} with symlink → {source_dir}")
    shutil.rmtree(target_path)
    target_path.symlink_to(source_dir)
    return ActResult(outcome="overwritten")


def remove_skill(target_path: Path, skill_library_path: Path) -> ActResult:
    """Remove the symlink at *target_path* if it is owned by mysk."""
    if not target_path.exists() and not target_path.is_symlink():
        return ActResult(outcome="skipped", reason="not deployed")

    if target_path.is_symlink():
        owned_by_mysk = target_path.resolve().is_relative_to(skill_library_path)
        if not owned_by_mysk:
            return ActResult(outcome="skipped", reason="not owned by mysk")
        out.debug(f"removing symlink {target_path}")
        target_path.unlink()
        return ActResult(outcome="removed")

    return ActResult(outcome="skipped", reason="not owned by mysk")
