#!/usr/bin/env python3
##################################
# run_tests.py
#
# jcarlin@hmc.edu Jan 2026
# SPDX-License-Identifier: Apache-2.0
#
# Run all ELFs for a spike configuration in parallel
##################################

import argparse
import os
import shlex
import subprocess
import sys
from functools import partial
from multiprocessing import Pool
from pathlib import Path


def run_test(cmd: list[str], log_dir: Path, elf_path: Path) -> bool:
    """Run a single ELF and return (elf_path, passed, exit_code)."""

    # Create log file path
    log_file = log_dir / elf_path.parent.name / elf_path.with_suffix(".log").name
    log_file.parent.mkdir(parents=True, exist_ok=True)

    full_cmd = [*cmd, str(elf_path)]

    with log_file.open("w") as f:
        result = subprocess.run(
            full_cmd, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=5 * 60, check=False
        )

    failed = result.returncode != 0

    if failed:
        print(f"\tTest {elf_path.name} failed with exit code {result.returncode}. See log: {log_file}")

    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all ELF files using the provided command")
    parser.add_argument(
        "command", type=str, help="Command to run each ELF (elf path will be appended). E.g., 'spike --isa=rv64gc'"
    )
    parser.add_argument("elf_dir", type=Path, help="Path to ELF directory (e.g., work/spike-rv64/elfs)")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count(), help="Number of parallel jobs")
    args = parser.parse_args()

    elf_dir = args.elf_dir.resolve()
    log_dir = elf_dir.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Find all ELFs
    elf_files = sorted(elf_dir.rglob("*.elf"))
    if not elf_files:
        print(f"No ELF files found in {elf_dir}")
        sys.exit(1)

    # Partial function with fixed command and log_dir
    cmd = shlex.split(args.command)
    partial_run_test = partial(run_test, cmd, log_dir)

    failed = 0

    for elf in elf_files:
        print(f"\nRunning tests in {elf_dir} with command: {args.command} {elf}:")
    with Pool(args.jobs) as pool:
        for fail_status in pool.imap_unordered(partial_run_test, elf_files):
            if fail_status:
                failed += 1

    if failed:
        print(f"\t{failed} out of {len(elf_files)} tests failed.")
    else:
        print(f"\tAll {len(elf_files)} tests passed.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
