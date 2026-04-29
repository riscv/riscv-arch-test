##################################
# build.py
#
# Jordan Carlin jcarlin@hmc.edu 11 March 2026
# SPDX-License-Identifier: Apache-2.0
#
# Python-native DAG build executor using graphlib.TopologicalSorter
##################################

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text


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

    @property
    def name(self) -> str:
        """Task identity: string form of the primary output path."""
        return str(self.outputs[0])


@dataclass
class BuildError:
    """Information about a failed build task."""

    task_name: str
    command: str
    returncode: int
    output: str
    log_file: Path | None = None  # path to log file (for SubprocessAction with stdout_file)


@dataclass
class BuildResult:
    """Summary of a build execution."""

    succeeded: int = 0
    failed: int = 0
    skipped: int = 0  # up-to-date
    errors: list[BuildError] = field(default_factory=list)


def is_stale(task: BuildTask) -> bool:
    """Check if a task needs to be rebuilt.

    A task is stale if any output is missing or any input is newer than the oldest output.
    Both extra_inputs and deps (as Paths) are checked for staleness.
    Tasks with no outputs are always stale.
    """
    if not task.outputs:
        return True

    # Check if all outputs exist and find oldest output time
    oldest_output_mtime: float | None = None
    for out in task.outputs:
        if not out.exists():
            return True
        mtime = out.stat().st_mtime
        if oldest_output_mtime is None or mtime < oldest_output_mtime:
            oldest_output_mtime = mtime

    assert oldest_output_mtime is not None

    # Check extra_inputs and deps (deps are file paths of predecessor outputs)
    all_inputs = (*task.extra_inputs, *task.deps)
    return any(inp.exists() and inp.stat().st_mtime > oldest_output_mtime for inp in all_inputs)


def execute_task(task: BuildTask, *, verbose: bool = False) -> BuildError | None:
    """Execute a single build task. Returns None on success, BuildError on failure."""
    if verbose:
        print(f"  {_task_str(task)}")
    action = task.action

    if isinstance(action, SubprocessAction):
        try:
            result = subprocess.run(
                action.cmd,
                capture_output=True,
                text=True,
                check=False,  # manual check of returncode below for better error reporting
                cwd=action.cwd,
            )
            if action.stdout_file is not None:
                action.stdout_file.write_text(result.stdout + result.stderr)
            if result.returncode != 0:
                return BuildError(
                    task_name=task.name,
                    command=_task_str(task),
                    returncode=result.returncode,
                    output=result.stderr + result.stdout,
                    log_file=action.stdout_file,
                )
        except OSError as e:
            return BuildError(
                task_name=task.name,
                command=_task_str(task),
                returncode=-1,
                output=str(e),
            )

    elif isinstance(action, PythonAction):
        try:
            action.fn(*action.args)
        except Exception as e:  # noqa: BLE001
            return BuildError(
                task_name=task.name,
                command=_task_str(task),
                returncode=-1,
                output=str(e),
            )

    elif isinstance(action, SymlinkAction):
        try:
            action.dst.unlink(missing_ok=True)
            relative_src = os.path.relpath(action.src, action.dst.parent)
            action.dst.symlink_to(relative_src)
        except OSError as e:
            return BuildError(
                task_name=task.name,
                command=_task_str(task),
                returncode=-1,
                output=str(e),
            )

    else:
        raise TypeError(f"Unknown build action type: {type(action)}")

    return None


def build(
    tasks: list[BuildTask],
    *,
    jobs: int,
    keep_going: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> BuildResult:
    """Execute a DAG of build tasks using TopologicalSorter + ThreadPoolExecutor.

    Args:
        tasks: List of build tasks forming a DAG.
        jobs: Number of parallel workers.
        keep_going: If True, continue building independent tasks after a failure.
        dry_run: If True, print what would be built without executing.
        verbose: If True, print each command as it is issued.

    Returns:
        BuildResult with counts and any errors.
    """
    result = BuildResult()

    if not tasks:
        return result

    # Build task lookup and dependency graph (keyed by primary output path)
    task_map: dict[Path, BuildTask] = {}
    graph: dict[Path, tuple[Path, ...]] = {}
    for task in tasks:
        key = task.outputs[0]
        task_map[key] = task
        graph[key] = task.deps

    # Create all output directories upfront to avoid races
    dirs: set[Path] = set()
    for task in tasks:
        for out in task.outputs:
            dirs.add(out.parent)
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Topological sort with parallel scheduling
    sorter: TopologicalSorter[Path] = TopologicalSorter(graph)

    # Lock graph and throw error if there are cycles
    sorter.prepare()

    # Track failed tasks and their transitive dependents
    failed_tasks: set[Path] = set()

    def _has_failed_dep(key: Path) -> bool:
        """Check if any direct dependency has failed (transitive propagation is handled by the topological ordering)."""
        return any(dep in failed_tasks for dep in task_map[key].deps)

    # Set up status bar for in-flight tasks
    status_text = Text()

    def _update_status(in_flight_keys: dict[Path, Future[BuildError | None]]) -> None:
        """Update the status line to show currently in-flight task names."""
        status_text.truncate(0)
        if not in_flight_keys:
            return
        if len(in_flight_keys) <= 4:
            status_text.append("  " + ", ".join(str(k) for k in in_flight_keys), style="dim")
        else:
            active = min(len(in_flight_keys), jobs)
            oldest = next(iter(in_flight_keys))
            status_text.append(f"  {active} tasks running, oldest: {oldest}", style="dim")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Building..."),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("elapsed:"),
        TimeElapsedColumn(),
    )
    progress_task = progress.add_task("Building", total=len(tasks))

    with (
        Live(Group(progress, status_text), console=progress.console, transient=True) as live,
        ThreadPoolExecutor(max_workers=jobs) as executor,
    ):
        in_flight: dict[Path, Future[BuildError | None]] = {}
        future_to_key: dict[Future[BuildError | None], Path] = {}

        while sorter.is_active():
            # Submit all ready tasks
            for key in sorter.get_ready():
                task = task_map[key]

                # Skip if a dependency failed
                if _has_failed_dep(key):
                    failed_tasks.add(key)
                    result.failed += 1
                    sorter.done(key)
                    progress.advance(progress_task)
                    continue

                # Check staleness
                if not is_stale(task):
                    result.skipped += 1
                    sorter.done(key)
                    progress.advance(progress_task)
                    continue

                # Print task without running it
                if dry_run:
                    live.console.print(f"  {task.name}: {_task_str(task)}")
                    result.skipped += 1
                    sorter.done(key)
                    progress.advance(progress_task)
                    continue

                # Submit task to thread pool
                future = executor.submit(execute_task, task, verbose=verbose)
                in_flight[key] = future
                future_to_key[future] = key

            _update_status(in_flight)

            # If no tasks are running, continue to the next iteration
            if not in_flight:
                continue

            # Wait for at least one task to complete
            done_futures = wait(in_flight.values(), return_when=FIRST_COMPLETED).done

            # Process completed tasks
            for done_future in done_futures:
                key = future_to_key.pop(done_future)
                in_flight.pop(key)
                error = done_future.result()
                if error is not None:
                    result.failed += 1
                    result.errors.append(error)
                    failed_tasks.add(key)
                    _print_failure(live.console, task_map[key], error)
                    if not keep_going:
                        # Cancel remaining tasks
                        executor.shutdown(wait=False, cancel_futures=True)
                        return result
                else:
                    result.succeeded += 1
                sorter.done(key)
                progress.advance(progress_task)

            _update_status(in_flight)

    return result


def _print_failure(console: Console, task: BuildTask, error: BuildError) -> None:
    """Print a clear, actionable failure block for a failed build task.

    Layout: header (short test name) -> output path -> error output (tail) ->
    optional hint -> log file -> reproduce command. Paths are shown relative
    to CWD when possible. soft_wrap=True keeps long paths intact.
    """
    max_output_lines = 30
    primary = task.outputs[0]
    short_name = primary.stem  # e.g., "I-add-00.sig" -> "I-add-00"

    console.print()  # blank line separator
    console.print(f"[bold red]✗ FAILED:[/] [bold]{short_name}[/]", soft_wrap=True, highlight=False)
    console.print(f"  [dim]Output: {_short_path(primary)}[/]", soft_wrap=True, highlight=False)

    if error.output:
        console.print("[bold red]  Error output:[/]")
        output_lines = _strip_noise(error.output).strip().splitlines()
        if len(output_lines) > max_output_lines:
            omitted = len(output_lines) - max_output_lines
            console.print(f"    [dim]... {omitted} earlier line(s) omitted; see log file ...[/]")
            output_lines = output_lines[-max_output_lines:]
        for line in output_lines:
            console.print(f"    {line}", soft_wrap=True, highlight=False)
    else:
        console.print(f"  [dim](no output captured; exit status {error.returncode})[/]")

    if error.log_file is not None:
        console.print(f"[bold]  Log file:[/] {_short_path(error.log_file)}", soft_wrap=True, highlight=False)

    action = task.action
    if isinstance(action, SubprocessAction):
        console.print("[bold]  Reproduce with:[/]")
        lines = _format_cmd_lines(action.cmd)
        last = len(lines) - 1
        for i, line in enumerate(lines):
            suffix = "" if i == last else " \\"
            indent = "    " if i == 0 else "      "
            console.print(f"{indent}{line}{suffix}", soft_wrap=True, highlight=False)
    else:
        console.print(f"[bold]  Action:[/] {error.command}", soft_wrap=True, highlight=False)


def _short_path(path: Path) -> str:
    """Return path relative to CWD when reasonable, otherwise absolute."""
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return str(path)
    return str(rel)


# Lines matching these patterns are boilerplate from third-party tools.
# Stripped from the FAILED block so the actual error stands out; full output is
# still written to the log file.
_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*using .+ for test-signature output\.\s*$"),
    re.compile(r"^\s*setting signature-granularity to \d+ bytes\s*$"),
)


def _strip_noise(output: str) -> str:
    """Drop boilerplate lines that obscure real errors."""
    if not output:
        return output
    return "\n".join(line for line in output.splitlines() if not any(p.match(line) for p in _NOISE_PATTERNS))


def _format_cmd_lines(cmd: list[str]) -> list[str]:
    """Split a command into readable lines, keeping `--flag value` pairs on one line."""
    lines: list[str] = []
    i = 0
    while i < len(cmd):
        arg = cmd[i]
        # Pair a flag with its value: only if next arg exists, current starts with '-',
        # and current is not already in --flag=value form.
        if arg.startswith("-") and "=" not in arg and i + 1 < len(cmd) and not cmd[i + 1].startswith("-"):
            lines.append(f"{arg} {cmd[i + 1]}")
            i += 2
        else:
            lines.append(arg)
            i += 1
    return lines


def _task_str(task: BuildTask) -> str:
    """Return a string representing the task."""
    action = task.action
    if isinstance(action, SubprocessAction):
        cmd_str = " ".join(action.cmd)
        if action.stdout_file:
            cmd_str += f" > {action.stdout_file} 2>&1"
        return cmd_str
    if isinstance(action, PythonAction):
        return f"{action.fn.__name__}({', '.join(str(a) for a in action.args)})"
    if isinstance(action, SymlinkAction):
        relative_src = os.path.relpath(action.src, action.dst.parent)
        return f"ln -sf {relative_src} {action.dst}"
    return "unknown action"
