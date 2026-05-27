#!/usr/bin/env python3

##################################
# cli.py
#
# Command-line interface for test generation.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Top-level command-line interface for test generation."""

from __future__ import annotations

import fnmatch
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from testgen.constants import E_EXTENSION_TESTS
from testgen.generate import (
    generate_all_priv_vector_tests,
    generate_priv_test,
    generate_unpriv_extension_tests,
    generate_unpriv_vector_extension,
    list_priv_vector_extensions,
    list_unpriv_vector_extensions,
)
from testgen.io.testplans import get_extensions
from testgen.priv import get_priv_test_extensions

# CLI interface setup
testgen_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, add_completion=False)


@dataclass
class UnprivTask:
    """Task for generating unprivileged tests."""

    xlen: int
    E_ext: bool
    testsuite: str
    testplan_dir: Path
    output_test_dir: Path


@dataclass
class PrivTask:
    """Task for generating privileged tests."""

    testsuite: str
    output_test_dir: Path


@dataclass
class UnprivVectorTask:
    """Task for generating one (xlen, extension) pair of unpriv vector tests."""

    xlen: int
    extension: str


@dataclass
class PrivVectorTask:
    """Coarse task that runs the priv vector generator for all priv vector extensions."""


@testgen_app.command()
def generate_all_tests(
    testplan_dir: Annotated[
        Path, typer.Argument(exists=True, file_okay=False, help="Directory containing testplan CSV files")
    ],
    output_test_dir: Annotated[
        Path, typer.Option("--output_test_dir", "-o", file_okay=False, help="Directory to output generated tests")
    ] = Path("tests"),
    extensions: Annotated[
        str, typer.Option("--extensions", "-e", help="Comma-separated list of extensions to generate tests for")
    ] = "all",
    exclude: Annotated[
        str, typer.Option("--exclude", "-x", help="Comma-separated list of extensions to exclude from test generation")
    ] = "",
    jobs: Annotated[
        int,
        typer.Option("--jobs", "-j", help="Parallel build jobs (0 = auto-detect CPU count)"),
    ] = 0,
) -> None:
    """
    Generate riscv-arch-test tests.

    For unprivileged tests, uses the CSV testplan files in `testplan_dir`.
    """
    # Set number of parallel jobs to CPU count if not specified
    if jobs <= 0:
        jobs = os.cpu_count() or 1

    # Get available extensions
    available_unpriv_extensions = get_extensions(testplan_dir)
    available_priv_extensions = get_priv_test_extensions()
    available_unpriv_vector_extensions = list_unpriv_vector_extensions()
    available_priv_vector_extensions = list_priv_vector_extensions()
    unpriv_ext_list: list[str] = []
    priv_ext_list: list[str] = []
    unpriv_vec_ext_list: list[str] = []
    priv_vec_ext_list: list[str] = []

    if extensions == "all":
        unpriv_ext_list = available_unpriv_extensions
        priv_ext_list = available_priv_extensions
        unpriv_vec_ext_list = list(available_unpriv_vector_extensions)
        priv_vec_ext_list = list(available_priv_vector_extensions)
    else:
        # Support glob-style patterns (e.g. ``Vx*``) so the Makefile
        # ``EXTENSIONS=Vx*,Vls*,Vf*,ExceptionsV*`` invocation matches every
        # per-SEW variant exposed by the vector generators.
        requested = [e.strip() for e in extensions.split(",") if e.strip()]

        def _match(patterns: list[str], available: list[str]) -> list[str]:
            seen: set[str] = set()
            picked: list[str] = []
            for pat in patterns:
                for name in available:
                    if name in seen:
                        continue
                    if fnmatch.fnmatchcase(name, pat) or name == pat:
                        picked.append(name)
                        seen.add(name)
            return picked

        unpriv_ext_list = _match(requested, available_unpriv_extensions)
        priv_ext_list = _match(requested, available_priv_extensions)
        unpriv_vec_ext_list = _match(requested, available_unpriv_vector_extensions)
        priv_vec_ext_list = _match(requested, available_priv_vector_extensions)

        # Anything that matched nothing at all gets the historical warning so
        # handwritten-only extensions still surface in build logs.
        matched_any = (
            set(unpriv_ext_list) | set(priv_ext_list)
            | set(unpriv_vec_ext_list) | set(priv_vec_ext_list)
        )
        for pat in requested:
            if any(fnmatch.fnmatchcase(n, pat) or n == pat for n in matched_any):
                continue
            print(
                f"Extension {pat} not found in unpriv testplans at {testplan_dir} or priv test generators. This is normal for handwritten tests."
            )

    # Handle extension exclusions (also glob-aware)
    if exclude:
        excl_pats = [e.strip() for e in exclude.split(",") if e.strip()]

        def _drop(lst: list[str]) -> list[str]:
            return [n for n in lst if not any(fnmatch.fnmatchcase(n, p) or n == p for p in excl_pats)]

        unpriv_ext_list = _drop(unpriv_ext_list)
        priv_ext_list = _drop(priv_ext_list)
        unpriv_vec_ext_list = _drop(unpriv_vec_ext_list)
        priv_vec_ext_list = _drop(priv_vec_ext_list)

    # Build list of test generation tasks
    tasks: list[UnprivTask | PrivTask | UnprivVectorTask | PrivVectorTask] = []

    for xlen in [32, 64]:
        for E_ext in [False, True]:
            for testsuite in sorted(unpriv_ext_list):
                if E_ext and testsuite not in E_EXTENSION_TESTS:
                    continue
                tasks.append(UnprivTask(xlen, E_ext, testsuite, testplan_dir, output_test_dir))

    tasks.extend(PrivTask(testsuite, output_test_dir) for testsuite in sorted(priv_ext_list))

    # Vector dispatch. Each (xlen, ext) pair is its own unpriv worker; the priv
    # generator drives every priv vector extension end-to-end internally so it
    # is dispatched as a single coarse task only when at least one priv vector
    # extension was requested. Keeping it coarse-grained matches the legacy
    # `make vector-testgen-priv` behaviour exactly (same seed reset / file
    # ordering) so byte-for-byte diffs against the prior generator hold.
    for xlen in [32, 64]:
        for extension in sorted(unpriv_vec_ext_list):
            tasks.append(UnprivVectorTask(xlen, extension))
    if priv_vec_ext_list:
        # The priv generator currently iterates its own xlens/extensions list
        # internally rather than accepting a filter. Until that's refactored,
        # any request for a priv vector extension triggers the full sweep.
        tasks.append(PrivVectorTask())

    # Generate all tests in parallel
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(_dispatch_test_gen, task) for task in tasks]

        with _progress("Generating tests...") as progress:
            task_id = progress.add_task("generate", total=len(futures))
            for future in as_completed(futures):
                future.result()  # Re-raise any exceptions
                progress.advance(task_id)

    rprint(f"[bold green]✓ Generated {len(tasks)} test suite(s)[/]")


def _progress(description: str) -> Progress:
    """Construct the standard project progress display."""
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[cyan]{description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TextColumn("elapsed:"),
        TimeElapsedColumn(),
        transient=True,
    )


def _dispatch_test_gen(task: UnprivTask | PrivTask | UnprivVectorTask | PrivVectorTask) -> None:
    """Dispatch test generation based on task type."""
    if isinstance(task, UnprivTask):
        generate_unpriv_extension_tests(
            xlen=task.xlen,
            E_ext=task.E_ext,
            testsuite=task.testsuite,
            testplan_dir=task.testplan_dir,
            output_test_dir=task.output_test_dir,
        )
    elif isinstance(task, PrivTask):
        generate_priv_test(
            testsuite=task.testsuite,
            output_test_dir=task.output_test_dir,
        )
    elif isinstance(task, UnprivVectorTask):
        generate_unpriv_vector_extension(xlen=task.xlen, extension=task.extension)
    elif isinstance(task, PrivVectorTask):
        generate_all_priv_vector_tests()
    else:
        raise TypeError("Invalid task type.")


def main() -> None:
    """Entry point for the CLI."""
    testgen_app()


if __name__ == "__main__":
    main()
