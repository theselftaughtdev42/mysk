import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

DeployOutcome = Literal["deployed", "overwritten", "skipped"]


@dataclass
class ReconcileResult:
    outcome: DeployOutcome
    reason: str | None = field(default=None)


def reconcile_skill(
    source_dir: Path,
    target_path: Path,
    overwrite: bool,
) -> ReconcileResult:
    if target_path.is_symlink():
        target_path.unlink()
        target_path.symlink_to(source_dir)
        return ReconcileResult(outcome="overwritten")

    if not target_path.exists():
        target_path.symlink_to(source_dir)
        return ReconcileResult(outcome="deployed")

    if not overwrite:
        return ReconcileResult(
            outcome="skipped",
            reason="directory already exists. Use --overwrite to replace",
        )

    shutil.rmtree(target_path)
    target_path.symlink_to(source_dir)
    return ReconcileResult(outcome="overwritten")
