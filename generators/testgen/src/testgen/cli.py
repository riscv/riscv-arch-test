#!/usr/bin/env python3

##################################
# cli.py
#
# Command-line interface for test generation.
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Top-level command-line interface for test generation."""

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.progress import track

from testgen.constants import E_EXTENSION_TESTS
from testgen.generate import generate_priv_test, generate_unpriv_extension_tests
from testgen.io.testplans import get_extensions
from testgen.priv import get_priv_test_extensions

# CLI interface setup
testgen_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, add_completion=False)


@dataclass
class UnprivTask:
    """Task for generating unprivileged tests."""

    xlen: int
    E_ext: bool
    extension: str
    testplan_dir: Path
    output_test_dir: Path


@dataclass
class PrivTask:
    """Task for generating privileged tests."""

    extension: str
    output_test_dir: Path


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
    jobs: Annotated[
        int | None, typer.Option("--jobs", "-j", show_default="number of CPU cores", help="Number of parallel jobs")
    ] = None,
) -> None:
    """
    Generate riscv-arch-test tests.

    For unprivileged tests, uses the CSV testplan files in `testplan_dir`.
    """
    # Set number of parallel jobs to CPU count if not specified
    if jobs is None:
        jobs = os.cpu_count() or 1

    # Get available extensions
    available_unpriv_extensions = get_extensions(testplan_dir)
    available_priv_extensions = get_priv_test_extensions()
    unpriv_ext_list: list[str] = []
    priv_ext_list: list[str] = []

    if extensions == "all":
        unpriv_ext_list = available_unpriv_extensions
        priv_ext_list = available_priv_extensions
    else:
        for ext in extensions.split(","):
            ext = ext.strip()
            if ext in available_unpriv_extensions:
                unpriv_ext_list.append(ext)
            elif ext in available_priv_extensions:
                priv_ext_list.append(ext)
            else:
                raise ValueError(f"Extension {ext} not found in testplans at {testplan_dir}.")

    # Build list of test generation tasks
    tasks: list[UnprivTask | PrivTask] = []

    for xlen in [32, 64]:
        for E_ext in [False, True]:
            for extension in sorted(unpriv_ext_list):
                if E_ext and extension not in E_EXTENSION_TESTS:
                    continue
                tasks.append(UnprivTask(xlen, E_ext, extension, testplan_dir, output_test_dir))

    for extension in sorted(priv_ext_list):
        tasks.append(PrivTask(extension, output_test_dir))

    # Generate all tests in parallel
    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(_dispatch_test_gen, task) for task in tasks]

        # Process completed tasks with progress tracking
        for future in track(futures, description="[cyan]Generating tests...", total=len(futures)):
            future.result()  # Re-raise any exceptions


def _dispatch_test_gen(task: UnprivTask | PrivTask) -> None:
    """Dispatch test generation based on task type."""
    if isinstance(task, UnprivTask):
        generate_unpriv_extension_tests(
            xlen=task.xlen,
            E_ext=task.E_ext,
            extension=task.extension,
            testplan_dir=task.testplan_dir,
            output_test_dir=task.output_test_dir,
        )
    elif isinstance(task, PrivTask):
        generate_priv_test(
            extension=task.extension,
            output_test_dir=task.output_test_dir,
        )
    else:
        raise ValueError("Invalid task type.")


def main() -> None:
    """Entry point for the CLI."""
    testgen_app()


if __name__ == "__main__":
    main()
