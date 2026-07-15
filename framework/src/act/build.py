##################################
# build.py
#
# Jordan Carlin jcarlin@hmc.edu 11 March 2026
# SPDX-License-Identifier: Apache-2.0
#
# Python-native DAG build executor using graphlib.TopologicalSorter
##################################

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import threading
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from graphlib import TopologicalSorter
from pathlib import Path

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

from act import build_cache
from act.build_types import (
    BuildTask,
    PythonAction,
    SubprocessAction,
    SymlinkAction,
)


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


def _exception_error(task: BuildTask, e: BaseException) -> BuildError:
    """BuildError for a task that raised before producing a return code."""
    return BuildError(task_name=task.name, command=_task_str(task), returncode=-1, output=str(e))


def execute_task(
    task: BuildTask,
    *,
    verbose: bool = False,
    active_pgids: set[int],
    pgids_lock: threading.Lock,
    shutdown_event: threading.Event,
) -> tuple[Path, BuildError | None]:
    """Execute a single build task. Returns (task key, None on success / BuildError on failure)."""
    if verbose:
        print(f"  {_task_str(task)}")
    action = task.action

    if isinstance(action, SubprocessAction):
        try:
            proc = subprocess.Popen(
                action.cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=action.cwd,
                start_new_session=True,  # own process group so killpg reaches children
            )
            pgid = proc.pid  # start_new_session=True makes the child its own group leader
            kill_immediately = False
            with pgids_lock:
                if shutdown_event.is_set():
                    kill_immediately = True
                else:
                    active_pgids.add(pgid)
            if kill_immediately:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(pgid, signal.SIGKILL)
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    proc.kill()
            try:
                stdout, stderr = proc.communicate()
            finally:
                with pgids_lock:
                    active_pgids.discard(pgid)
            if action.stdout_file is not None:
                action.stdout_file.write_text(stderr + stdout)
            if proc.returncode != 0:
                return task.key, BuildError(
                    task_name=task.name,
                    command=_task_str(task),
                    returncode=proc.returncode,
                    output=stderr + stdout,
                    log_file=action.stdout_file,
                )
        except OSError as e:
            return task.key, _exception_error(task, e)

    elif isinstance(action, PythonAction):
        try:
            action.fn(*action.args)
        except Exception as e:  # noqa: BLE001
            return task.key, _exception_error(task, e)

    elif isinstance(action, SymlinkAction):
        try:
            action.dst.unlink(missing_ok=True)
            relative_src = os.path.relpath(action.src, action.dst.parent)
            action.dst.symlink_to(relative_src)
        except OSError as e:
            return task.key, _exception_error(task, e)

    else:
        raise TypeError(f"Unknown build action type: {type(action)}")

    return task.key, None


def build(
    tasks: list[BuildTask],
    *,
    jobs: int,
    cache_root: Path,
    keep_going: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    clean_intermediates: bool = False,
    phase_label: str = "Building",
) -> BuildResult:
    """Execute a DAG of build tasks using TopologicalSorter + ThreadPoolExecutor.

    Args:
        tasks: List of build tasks forming a DAG.
        jobs: Number of parallel workers.
        cache_root: Workdir whose immediate children are config dirs.
        keep_going: If True, continue building independent tasks after a failure.
        dry_run: If True, print what would be built without executing.
        verbose: If True, print each command as it is issued.
        clean_intermediates: If True, intermediate outputs are disposable, so a
            satisfied deliverable will not rebuild them when they are missing. Each
            intermediate's output files (and log) are also deleted as soon as every task that
            consumes them has finished.
        phase_label: Label shown in the transient progress widget (e.g.
            "Building", "Preparing DUT configs"). Trailing "..." is appended.

    Returns:
        BuildResult with counts and any errors.
    """
    result = BuildResult()

    if not tasks:
        return result

    # Process-group tracking so a failure/interrupt can kill in-flight subprocess trees.
    active_pgids: set[int] = set()
    pgids_lock = threading.Lock()
    shutdown_event = threading.Event()

    # Task lookup and dependency graph (keyed by primary output path).
    task_map: dict[Path, BuildTask] = {}
    graph: dict[Path, tuple[Path, ...]] = {}
    for task in tasks:
        task_map[task.key] = task
        graph[task.key] = task.deps

    missing_deps = sorted({dep for task in tasks for dep in task.deps if dep not in task_map})
    if missing_deps:
        raise KeyError(f"Build plan contains dependencies with no producing task: {missing_deps}")

    # Create all output directories upfront to avoid races.
    for task in tasks:
        for out in task.outputs:
            out.parent.mkdir(parents=True, exist_ok=True)

    # Topological sort; prepare() locks the graph and errors on cycles.
    sorter: TopologicalSorter[Path] = TopologicalSorter(graph)
    sorter.prepare()

    # Tasks whose outputs are missing or whose recipe hash no longer matches the cache.
    cache = build_cache.BuildCache(cache_root, task_map, clean_intermediates=clean_intermediates)
    needed_tasks = cache.needed_tasks()

    # Incremental intermediate cleanup: count, per intermediate task, how many tasks consume
    # its outputs. Once every consumer has finished, the intermediate's files are deleted so
    # peak disk usage stays bounded rather than holding all intermediates until the end.
    remaining_consumers: dict[Path, int] = {}
    if clean_intermediates and not dry_run:
        for task in tasks:
            for dep in task.deps:
                dep_task = task_map.get(dep)
                if dep_task is not None and dep_task.intermediate:
                    remaining_consumers[dep] = remaining_consumers.get(dep, 0) + 1

    failed_tasks: set[Path] = set()
    in_flight: dict[Path, Future[tuple[Path, BuildError | None]]] = {}

    # Progress display.
    status_text = Text()
    progress = Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{phase_label}..."),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("elapsed:"),
        TimeElapsedColumn(),
    )
    progress_task = progress.add_task(phase_label, total=len(tasks))

    def retire(key: Path) -> None:
        """Mark a task done, delete any intermediate deps no remaining consumer needs, and
        advance the progress bar."""
        sorter.done(key)
        for dep in task_map[key].deps if remaining_consumers else ():
            count = remaining_consumers.get(dep)
            if count is None:
                continue
            if count > 1:
                remaining_consumers[dep] = count - 1
                continue
            del remaining_consumers[dep]
            dep_task = task_map[dep]
            disposable = [*dep_task.outputs]
            log_file = getattr(dep_task.action, "stdout_file", None)
            if log_file is not None:
                disposable.append(log_file)
            for path in disposable:
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
        progress.advance(progress_task)

    def schedule(key: Path, *, live: Live, executor: ThreadPoolExecutor) -> None:
        """Handle one ready task: skip, print (dry run), or submit it to the pool."""
        task = task_map[key]

        # Skip (but count as a failure) if a dependency failed.
        if any(dep in failed_tasks for dep in task.deps):
            failed_tasks.add(key)
            result.failed += 1
            retire(key)
            return

        # Skip tasks whose outputs are already up to date.
        if key not in needed_tasks:
            result.skipped += 1
            retire(key)
            return

        # Print the task without running it.
        if dry_run:
            live.console.print(f"  {task.name}: {_task_str(task)}")
            result.skipped += 1
            retire(key)
            return

        # Submit task to thread pool if none of the above apply.
        future = executor.submit(
            execute_task,
            task,
            verbose=verbose,
            active_pgids=active_pgids,
            pgids_lock=pgids_lock,
            shutdown_event=shutdown_event,
        )
        in_flight[key] = future

    def kill_active() -> None:
        """Signal shutdown and SIGKILL every in-flight subprocess group."""
        with pgids_lock:
            shutdown_event.set()
            pgids = set(active_pgids)
        for pgid in pgids:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGKILL)

    def record_result(
        done_future: Future[tuple[Path, BuildError | None]], *, live: Live, executor: ThreadPoolExecutor
    ) -> bool:
        """Record the outcome of one finished future. Returns True if the run should abort."""
        exc = done_future.exception()
        if exc is not None:
            # execute_task raised unexpectedly: recover the key and turn it into a BuildError
            # so the build reports a failure and saves its summary instead of crashing the loop.
            key = next(k for k, f in in_flight.items() if f is done_future)
            error = _exception_error(task_map[key], exc)
        else:
            key, error = done_future.result()
        in_flight.pop(key)
        if error is not None:
            result.failed += 1
            result.errors.append(error)
            failed_tasks.add(key)
            _print_failure(live.console, task_map[key], error, verbose=verbose)
            if not keep_going:
                kill_active()
                executor.shutdown(wait=False, cancel_futures=True)
                return True
        else:
            result.succeeded += 1
            cache.record_success(key)
        retire(key)
        return False

    def update_status() -> None:
        """Update the status line to show currently in-flight task names."""
        status_text.truncate(0)
        if not in_flight:
            return
        if len(in_flight) <= 4:
            status_text.append("  " + ", ".join(str(k) for k in in_flight), style="dim")
        else:
            active = min(len(in_flight), jobs)
            oldest = next(iter(in_flight))
            status_text.append(f"  {active} tasks running, oldest: {oldest}", style="dim")

    with (
        Live(Group(progress, status_text), console=progress.console, transient=True) as live,
        ThreadPoolExecutor(max_workers=jobs) as executor,
    ):
        try:
            while sorter.is_active():
                for key in sorter.get_ready():
                    schedule(key, live=live, executor=executor)
                update_status()

                # Nothing in flight means every ready task was handled inline (skipped/failed).
                if not in_flight:
                    continue

                done_futures = wait(in_flight.values(), return_when=FIRST_COMPLETED).done
                for done_future in done_futures:
                    if record_result(done_future, live=live, executor=executor):
                        return result  # fatal failure, abort the run
                update_status()
        except KeyboardInterrupt:
            kill_active()
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            cache.save()
    return result


def prune_empty_dirs(root: Path) -> None:
    """Remove root and its subdirectories, but only those that are empty (bottom-up).

    With clean_intermediates the build deletes intermediate files as they become unneeded, so
    the tree is normally empty by the end. Pruning empty-only means any unexpected leftover
    file (and its parents) survives and stays visible instead of being silently force-deleted.
    """
    if not root.is_dir():
        return
    for child in sorted(root.rglob("*"), reverse=True):
        if child.is_dir():
            with contextlib.suppress(OSError):
                child.rmdir()
    with contextlib.suppress(OSError):
        root.rmdir()


def _print_failure(console: Console, task: BuildTask, error: BuildError, verbose: bool) -> None:
    """Print a clear, actionable failure block for a failed build task.

    Layout: header (short test name) -> output path -> error output (tail) ->
    optional hint -> log file -> reproduce command. Paths are shown relative
    to CWD when possible. soft_wrap=True keeps long paths intact.
    """
    max_output_lines = 30
    primary = task.outputs[0]
    short_name = task.label or primary.stem  # e.g., "I-add-00.sig" -> "I-add-00"

    console.print()  # blank line separator
    console.print(f"[bold red]✗ FAILED:[/] [bold]{short_name}[/]", soft_wrap=True, highlight=False)
    console.print(f"  [dim]Output: {_short_path(primary)}[/]", soft_wrap=True, highlight=False)

    if error.output:
        console.print("[bold red]  Error output:[/]")
        output_lines = _strip_noise(error.output).strip().splitlines()
        if not verbose and len(output_lines) > max_output_lines:
            # Keep the beginning and end of the error message
            head_count = 10
            omitted = len(output_lines) - max_output_lines
            hint = "see log file" if error.log_file is not None else "re-run with --verbose to see full output"
            for line in output_lines[:head_count]:
                console.print(f"    {line}", soft_wrap=True, highlight=False)
            console.print(f"    [dim]... {omitted} line(s) omitted; {hint} ...[/]")
            output_lines = output_lines[-(max_output_lines - head_count) :]
        for line in output_lines:
            console.print(f"    {line}", soft_wrap=True, highlight=False)
        console.print()  # blank line separator
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
    re.compile(r"^\s*HTIF located at 0x[0-9a-fA-F]+\s*$"),
    re.compile(r"^\s*Entry point: 0x[0-9a-fA-F]+\s*$"),
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
