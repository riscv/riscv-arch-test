##################################
# act.py
#
# jcarlin@hmc.edu 14 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Main entry point for RISC-V architecture verification framework
##################################

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from act.build import build
from act.build_plan import ConfigData, generate_build_plan
from act.config import load_config
from act.coverreport import print_coverage_summary
from act.parse_test_constraints import generate_test_dict
from act.parse_udb_config import generate_udb_files, get_config_params, get_implemented_extensions
from act.select_tests import select_tests

# CLI interface setup
act_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@act_app.command()
def run_act(
    config_files: Annotated[
        list[Path], typer.Argument(exists=True, file_okay=True, dir_okay=False, help="Path to configuration file(s)")
    ],
    test_dir: Annotated[
        Path, typer.Option("--test-dir", "-t", exists=True, file_okay=False, help="Path to tests directory")
    ] = Path("tests"),
    coverpoint_dir: Annotated[
        Path, typer.Option("--coverpoint-dir", "-c", exists=True, file_okay=False, help="Path to coverpoint directory")
    ] = Path("coverpoints"),
    workdir: Annotated[
        Path | None,
        typer.Option("--workdir", "-w", file_okay=False, help="Path to working directory", show_default="./work"),
    ] = None,
    extensions: Annotated[
        str,
        typer.Option("--extensions", "-e", help="Comma-separated list of extensions to generate tests for"),
    ] = "all",
    exclude: Annotated[
        str,
        typer.Option("--exclude", "-x", help="Comma-separated list of extensions to exclude from test generation"),
    ] = "",
    jobs: Annotated[
        int,
        typer.Option("--jobs", "-j", help="Parallel build jobs (0 = auto-detect CPU count)"),
    ] = 0,
    *,
    coverage: Annotated[bool, typer.Option(help="Enable coverage generation")] = False,
    debug: Annotated[bool, typer.Option(help="Enable debug output (signature objdump and trace files)")] = False,
    fast: Annotated[bool, typer.Option(help="Disable objdump generation for faster builds")] = False,
    keep_going: Annotated[bool, typer.Option("--keep-going", "-k", help="Continue building after failures")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be built without executing")
    ] = False,
) -> None:
    if debug and fast:
        raise typer.BadParameter("--debug and --fast cannot be used together")

    if workdir is None:
        workdir = Path.cwd() / "work"

    if jobs <= 0:
        jobs = os.cpu_count() or 1

    # Generate test list
    full_test_dict = generate_test_dict(test_dir, extensions, exclude)

    configs: list[ConfigData] = []
    for config_file in config_files:
        # Load configuration
        config = load_config(config_file)
        config_dir = workdir / config.udb_config.stem
        config_dir.mkdir(parents=True, exist_ok=True)

        # UDB integration
        generate_udb_files(config.udb_config, config_dir)
        implemented_extensions = get_implemented_extensions(config_dir / "extensions.txt")
        config_params = get_config_params(config.udb_config)

        # Select tests for config
        selected_tests = select_tests(
            full_test_dict, implemented_extensions, config_params, include_priv_tests=config.include_priv_tests
        )
        mxlen = config_params["MXLEN"]
        if not isinstance(mxlen, int):
            raise TypeError(f"MXLEN must be an integer, got {type(mxlen)}: {mxlen!r}")
        configs.append(
            {
                "config": config,
                "xlen": mxlen,
                "e_ext": "E" in implemented_extensions,
                "selected_tests": selected_tests,
            }
        )

    # Generate list of build tasks
    tasks = generate_build_plan(
        configs,
        test_dir.absolute(),
        coverpoint_dir.absolute(),
        workdir.absolute(),
        coverage,
        debug,
        fast,
    )

    # Run all tasks to compile ELFs
    result = build(tasks, jobs=jobs, keep_going=keep_going, dry_run=dry_run)

    # Print summary
    parts = []
    if result.succeeded:
        parts.append(f"{result.succeeded} succeeded")
    if result.skipped:
        parts.append(f"{result.skipped} up-to-date")
    if result.failed:
        parts.append(f"{result.failed} failed")
    print(f"Build complete: {', '.join(parts)}")

    if result.errors:
        print(f"\n{len(result.errors)} task(s) failed:", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error.task_name}", file=sys.stderr)
        sys.exit(1)

    # Always print coverage summaries when coverage is enabled, even if up-to-date
    if coverage:
        for config_data in configs:
            config = config_data["config"]
            overall_summary = workdir.absolute() / config.name / "reports" / "_overall_summary.txt"
            if overall_summary.exists():
                print()
                print_coverage_summary(overall_summary, config.name)


def main() -> None:
    act_app()


if __name__ == "__main__":
    main()
