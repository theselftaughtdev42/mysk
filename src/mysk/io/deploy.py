"""Low-level deploy/undeploy operations: symlink reconciliation and removal."""

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DeployOutcome = Literal["deployed", "overwritten", "skipped"]
RemoveOutcome = Literal["removed", "skipped"]


@dataclass
class ReconcileResult:
    """Result of a single skill reconciliation attempt."""

    outcome: DeployOutcome
    reason: str | None = field(default=None)


def reconcile_skill(
    source_dir: Path,
    target_path: Path,
    *,
    overwrite: bool,
    skill_library_path: Path,
) -> ReconcileResult:
    """Symlink *source_dir* at *target_path*, handling existing entries.

    Returns a ReconcileResult describing what happened (deployed, overwritten,
    or skipped) and an optional human-readable reason.
    """
    # an existing symlink: replace it, unless it belongs to something else
    if target_path.is_symlink():
        owned_by_mysk = target_path.resolve().is_relative_to(skill_library_path)
        if not owned_by_mysk and not overwrite:
            reason = (
                "symlink exists but is not owned by mysk. Use --overwrite to replace"
            )
            return ReconcileResult(
                outcome="skipped",
                reason=reason,
            )
        target_path.unlink()
        target_path.symlink_to(source_dir)
        return ReconcileResult(outcome="overwritten")

    # nothing at the target: create the symlink
    if not target_path.exists():
        target_path.symlink_to(source_dir)
        return ReconcileResult(outcome="deployed")

    # a real directory is in the way: replace it only with --overwrite
    if not overwrite:
        return ReconcileResult(
            outcome="skipped",
            reason="directory already exists. Use --overwrite to replace",
        )

    shutil.rmtree(target_path)
    target_path.symlink_to(source_dir)
    return ReconcileResult(outcome="overwritten")


@dataclass
class RemoveResult:
    """Result of a single skill removal attempt."""

    outcome: RemoveOutcome
    reason: str | None = field(default=None)


def remove_skill(target_path: Path, skill_library_path: Path) -> RemoveResult:
    """Remove the symlink at *target_path* if it is owned by mysk."""
    if not target_path.exists() and not target_path.is_symlink():
        return RemoveResult(outcome="skipped", reason="not deployed")

    if target_path.is_symlink():
        owned_by_mysk = target_path.resolve().is_relative_to(skill_library_path)
        if not owned_by_mysk:
            return RemoveResult(outcome="skipped", reason="not owned by mysk")
        target_path.unlink()
        return RemoveResult(outcome="removed")

    return RemoveResult(outcome="skipped", reason="not owned by mysk")
