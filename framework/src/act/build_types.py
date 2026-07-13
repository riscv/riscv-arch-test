##################################
# build_types.py
#
# Jordan Carlin jcarlin@hmc.edu June 2026
# SPDX-License-Identifier: Apache-2.0
#
# Shared data types for the build DAG (actions and tasks).
##################################

"""Build action and task definitions shared by the executor and cache layers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Actions: the work a task performs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubprocessAction:
    """Run a subprocess (shell) command."""

    cmd: list[str]
    stdout_file: Path | None = None  # redirect stdout to file
    cwd: Path | None = None  # working directory for the subprocess


@dataclass(frozen=True)
class PythonAction:
    """Call a Python function directly (avoids subprocess overhead)."""

    fn: Callable[..., None]
    args: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SymlinkAction:
    """Create a symbolic link from src to dst."""

    src: Path
    dst: Path


BuildAction = SubprocessAction | PythonAction | SymlinkAction


# ---------------------------------------------------------------------------
# Tasks: nodes in the build DAG
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildTask:
    """A single node in the build DAG.

    The primary output path (outputs[0]) is used as the task's identity for dependency tracking.
    Dependencies reference tasks by their primary output path. Deps are automatically treated
    as staleness inputs (since they are file paths produced by predecessor tasks), so only
    files NOT produced by other tasks (e.g., source .S files) need to be listed in extra_inputs.
    """

    outputs: tuple[Path, ...]  # Files produced; outputs[0] is the task identity
    action: BuildAction
    extra_inputs: tuple[Path, ...] = ()  # Source files not produced by other tasks (for staleness check)
    deps: tuple[Path, ...] = ()  # Primary output paths of predecessor BuildTasks
    label: str | None = None  # Human-readable name for failure messages (defaults to outputs[0].stem)
    intermediate: bool = False  # Only build if needed for another task

    @property
    def name(self) -> str:
        """Task identity: string form of the primary output path."""
        return str(self.outputs[0])

    @property
    def key(self) -> Path:
        """Primary output path used as this task's graph key."""
        return self.outputs[0]

    def is_deliverable(self, *, clean_intermediates: bool) -> bool:
        """Whether this task's outputs should be kept up to date directly."""
        return not (self.intermediate and clean_intermediates)
